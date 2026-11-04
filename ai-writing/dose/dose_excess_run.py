"""Run the detector-free cross-checks on the universe (CPU; Slurm).

  dose_excess_run.py kobak [-j N]   Kobak et al. style-word rate per 1,000 tokens, per paper, abstract and full text
                                  -> AI_SCORES/parts/kobak.parquet  paper_id, kobak_abs, ntok_abs, kobak_ft, ntok_ft
  dose_excess_run.py liang          Liang et al. mixture estimate of the LLM-modified fraction of abstracts, per school and year
                                  -> AI_SCORES/results/liang_alpha.parquet (school, year, n, alpha, lo, hi), liang_calibration.parquet
Training text for the mixture: human = every universe abstract of 2016-2021 except the held-out sources; LLM = the rewrites of the training half of the
sources (ai-writing/generated-*.jsonl: polish and outline versions by Qwen2.5-3B/7B/72B and Llama-3.3-70B). The held-out half calibrates the estimator.
"""
import argparse
import hashlib
import json
import sqlite3
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import dcommon as D
import excess as E

KOBAK_WORDS = D.P.HOMOGENIZATION_STUDY / 'lit' / 'kobak_reference' / 'kobak_2024_style_words.csv'


def kobak_words():
    return {w.strip().lower() for w in KOBAK_WORDS.read_text().splitlines()[1:] if w.strip()}


def _ft_chunk(args):
    lo, hi = args
    words = kobak_words()
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    out = []
    for pid, body in db.execute('select paper_id, body from fulltext where usable = 1 and rowid >= ? and rowid < ?', (lo, hi)):
        toks = E.tokens(zlib.decompress(body).decode('utf-8', 'ignore')) if body else []
        out.append((pid, 1000.0 * sum(t in words for t in toks) / len(toks) if toks else float('nan'), len(toks)))
    return out


def run_kobak(jobs):
    words = kobak_words()
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    ab = {pid: (E.kobak_rate(t + ' ' + a, words), len(E.tokens(t + ' ' + a))) for pid, t, a in db.execute('select paper_id, title, abstract from abstracts')}
    hi = db.execute('select max(rowid) from fulltext').fetchone()[0]
    db.close()
    D.log(kobak_abstracts=len(ab), words=len(words))
    step = 500
    with ProcessPoolExecutor(jobs) as ex:
        ft = {pid: (r, n) for part in ex.map(_ft_chunk, [(lo, lo + step) for lo in range(0, hi + 1, step)]) for pid, r, n in part}
    ids = sorted(set(ab) | set(ft))
    df = pd.DataFrame(dict(paper_id=ids,
                           kobak_abs=[ab.get(i, (np.nan, 0))[0] for i in ids], ntok_abs=[ab.get(i, (np.nan, 0))[1] for i in ids],
                           kobak_ft=[ft.get(i, (np.nan, 0))[0] for i in ids], ntok_ft=[ft.get(i, (np.nan, 0))[1] for i in ids]))
    out = D.PARTS / 'kobak.parquet'
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    D.log(kobak=len(df), path=str(out))


def held_out(key):
    return int(hashlib.sha1(f'liang|{key}'.encode()).hexdigest()[:8], 16) % 2 == 0


def run_liang(boot, min_docs, vocab_size):
    aiw = D.MAIN_AIW
    src = {s['key']: s for s in map(json.loads, open(aiw / 'sources.jsonl'))}
    ai = [g for f in sorted(aiw.glob('generated-*.jsonl')) for g in map(json.loads, open(f)) if g['key'] in src and len(g['text'].split()) >= 40]
    ai_tr = [D.norm1(g['text']) for g in ai if not held_out(g['key'])]
    ai_te = [D.norm1(g['text']) for g in ai if held_out(g['key'])]
    hum_te = [D.norm1(s['abstract']) for k, s in src.items() if held_out(k)]
    te_hash = {hashlib.sha1(t[:300].encode()).hexdigest() for t in hum_te}
    uni = sqlite3.connect(f'file:{D.UNIVERSE_DB}?mode=ro', uri=True)
    meta = {p: (s, y) for p, s, y in uni.execute('select paper_id, home_school, year from papers')}
    uni.close()
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True)
    rows = [(p, D.norm1(a)) for p, a in db.execute('select paper_id, abstract from abstracts') if p in meta and a and len(a.split()) >= 50]
    db.close()
    D.log(liang_abstracts=len(rows), ai_train=len(ai_tr), ai_test=len(ai_te), human_test=len(hum_te))
    toks = {p: E.tokens(t) for p, t in rows}
    hum_tr = [toks[p] for p, t in rows if 2016 <= (meta[p][1] or 0) <= 2021 and hashlib.sha1(t[:300].encode()).hexdigest() not in te_hash]
    ai_tr_t = [E.tokens(t) for t in ai_tr]
    vocab = E.build_vocab(hum_tr + ai_tr_t, size=vocab_size)
    model = E.LiangMixture(E.occurrence_matrix(hum_tr, vocab), E.occurrence_matrix(ai_tr_t, vocab))
    Xh, Xl = E.occurrence_matrix([E.tokens(t) for t in hum_te], vocab), E.occurrence_matrix([E.tokens(t) for t in ai_te], vocab)
    cal = pd.DataFrame(E.calibration(model, Xh, Xl, n=min(1000, Xh.shape[0])), columns=['alpha_true', 'alpha_hat'])
    D.log(calibration=cal.round(3).values.tolist())
    pid = [p for p, _ in rows]
    X = E.occurrence_matrix([toks[p] for p in pid], vocab)
    school = np.array([meta[p][0] for p in pid]); year = np.array([meta[p][1] for p in pid])
    out = []
    for s in ['all'] + D.SCHOOLS:
        for y in range(2016, 2027):
            m = (year == y) & ((school == s) if s != 'all' else True)
            if m.sum() >= min_docs:
                a, lo, hi = model.estimate(X[np.where(m)[0]], boot=boot, seed=y)
                out.append(dict(school=s, year=y, n=int(m.sum()), alpha=a, lo=lo, hi=hi))
    res = D.RESULTS
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_parquet(res / 'liang_alpha.parquet', index=False)
    cal.to_parquet(res / 'liang_calibration.parquet', index=False)
    D.log(liang=len(out))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['kobak', 'liang'])
    ap.add_argument('-j', type=int, default=14)
    ap.add_argument('--boot', type=int, default=200)
    ap.add_argument('--min-docs', type=int, default=100)
    ap.add_argument('--vocab', type=int, default=5000)
    a = ap.parse_args()
    run_kobak(a.j) if a.cmd == 'kobak' else run_liang(a.boot, a.min_docs, a.vocab)
