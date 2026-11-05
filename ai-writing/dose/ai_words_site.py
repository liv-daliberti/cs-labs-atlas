"""AI marker words for the site (owner 2026-11-05): the vocabulary that surged with ChatGPT, next to the detector.

  ai_words_site.py count     per-paper marker-word counts (abstract: every universe paper with an abstract; full text: where usable)
  ai_words_site.py liang     Liang et al. mixture estimate per school and year, with its calibration -> work/liang.parquet
  ai_words_site.py assemble  site JSON -> <out>/words/words.json and words/word_curves.json   (needs count and liang)
  ai_words_site.py spot N    N random papers with their abstract and the marker words found, for reading checks -> work/spotcheck.txt

Word lists (studies/homogenization/lit/kobak_reference/):
  all379   Kobak et al. 2024's 379 "style words" (kobak_2024_style_words.csv); the list holds common words (this, these, their, into,
           research, using), so its raw rate has a large baseline and is read as an excess over the pre-2023 baseline.
  core     the part of all379 whose PubMed document frequency rose at least 3-fold, 2024 against the mean of 2020-2022 (Kobak et al.'s
           yearly-counts.csv.gz, normalised by the number of abstracts); chosen from PubMed, never from the atlas, so the atlas trend is not
           selected on itself. The shares of papers using >= 1 and >= 3 marker words, and the words-versus-detector comparison, use core.
Text surface: the abstract alone (title excluded); full texts are cut at their last "References" heading and stripped of URLs, e-mail
addresses and DOIs. Tokens are lower-case letter runs (an apostrophe-s is dropped); a word counts only as written, so the list's own
inflections count (delve, delves, delved, delving) and others (elucidated) do not.
Schools: a paper counts for every school of its `schools` field and once under "all", as ai_hist.json does. Years 2016-2025: never 2026.

Detector side: ONE config point, DETECTOR (below): the frame the AI pages' ai_hist.json is built from (ai_pages.py frame -> frame.parquet).
A detector v3 swaps in by pointing CS_ATLAS_AI_DETECTOR_FRAME at its frame (same columns) or by editing DETECTOR_COLS.
"""
import argparse
import json
import os
import random
import re
import sqlite3
import sys
import zlib
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

import dcommon as D
import excess as E

YEARS = list(range(2016, D.LAST_FULL_YEAR + 1))
PRE = [y for y in YEARS if y <= 2022]
POST = [y for y in YEARS if y >= 2023]
GROUPS = ['all'] + D.SCHOOLS
KOBAK = D.P.HOMOGENIZATION_STUDY / 'lit' / 'kobak_reference'
WORK = Path(os.environ.get('CS_ATLAS_WORDS_WORK', D.P.ROOT / 'scratch' / 'ai-words-20261105' / 'work'))
OUT = Path(os.environ.get('CS_ATLAS_WORDS_OUT', D.P.ROOT / 'scratch' / 'ai-site-data-words-20261105'))
DETECTOR = Path(os.environ.get('CS_ATLAS_AI_DETECTOR_FRAME', D.RESULTS / 'ai_pages' / 'frame.parquet'))
# detector columns, as dose_site.py reads them: dose = cal where present else share; abstract-only papers use the abstract flag
DETECTOR_COLS = dict(dose='ai_share', dose_cal='ai_share_cal', abstract_flag='flag_abstract', abstract_p='p_ai_abstract')
CUTOFFS = [10, 25, 50]
CORE_RATIO = 3.0
FAMILIES = {   # inflections of one word, as the list spells them; a family counts abstracts containing ANY of its forms (not a sum of the forms)
    'delve': ['delve', 'delved', 'delves', 'delving'], 'showcase': ['showcased', 'showcases', 'showcasing'],
    'underscore': ['underscore', 'underscored', 'underscores', 'underscoring'], 'intricate': ['intricate', 'intricately', 'intricacies'],
    'pivotal': ['pivotal'], 'unveil': ['unveil', 'unveiled', 'unveiling', 'unveils'], 'meticulous': ['meticulous', 'meticulously'],
    'emphasize': ['emphasises', 'emphasising', 'emphasize', 'emphasizes', 'emphasizing'], 'highlight': ['highlight', 'highlighting', 'highlights'],
    'leverage': ['leverages', 'leveraging'], 'enhance': ['enhance', 'enhanced', 'enhancements', 'enhances', 'enhancing'],
    'elucidate': ['elucidate', 'elucidates', 'elucidating'], 'pinpoint': ['pinpoint', 'pinpointed', 'pinpointing'],
    'surpass': ['surpass', 'surpassed', 'surpasses', 'surpassing'], 'exhibit': ['exhibit', 'exhibited', 'exhibiting', 'exhibits'],
    'harness': ['harness', 'harnesses', 'harnessing'], 'foster': ['fostering', 'fosters'], 'bolster': ['bolster', 'bolstered', 'bolstering'],
}
MIN_TOK = 40

URL = re.compile(r'(?:https?://|ftp://|www\.)\S+|\b[\w.+-]+@[\w-]+\.[\w.-]+|\b(?:doi|arxiv)\s*:\s*\S+|\b10\.\d{4,9}/\S+', re.I)
REFHEAD = re.compile(r'\b(?:R\s?EFERENCES|References|REFERENCES|Bibliography|BIBLIOGRAPHY|Literature Cited|Works Cited)\b')
REFLIST = re.compile(r'\[1\]\s+[A-Z][^\[]{20,400}\[2\]')
REFWHY = re.compile(r'\[1\]|\b(?:19|20)\d\d\b|arXiv|et al')


def clean_abstract(t):
    t = re.sub(r'<[^>]+>', ' ', str(t or ''))
    t = re.sub(r'^\s*(?:abstract|summary)\s*[:.\-—]?\s*', '', t, flags=re.I)
    return URL.sub(' ', t)


def clean_fulltext(body):
    """The body without its reference list. Bodies are single-line extracted text, so a heading is a capitalised "References"-like word in the
    back 70% that is followed within 400 characters by a year, "[1]", "arXiv" or "et al"; with no heading, the first "[1] Name ... [2]" run."""
    n = len(body)
    cut = None
    for m in REFHEAD.finditer(body):
        if m.start() > 0.3 * n and REFWHY.search(body, m.end(), m.end() + 400):
            cut = m.start()
    if cut is None:
        m = REFLIST.search(body, int(0.3 * n))
        cut = m.start() if m else None
    if cut is not None:
        body = body[:cut]
    return URL.sub(' ', body), cut is not None


def toks(text):
    out = []
    for t in E.tokens(str(text).replace('’', "'")):
        out.append(t[:-2] if t.endswith("'s") else t)
    return out


def word_lists():
    all379 = [w.strip().lower() for w in (KOBAK / 'kobak_2024_style_words.csv').read_text().splitlines()[1:] if w.strip()]
    d = pd.read_csv(KOBAK / 'yearly-counts.csv.gz', index_col=0)
    d = d[~d.index.duplicated()]
    n = d.loc['the']                                    # abstracts per year (the word "the" is in almost every one)
    p = d / n
    ratio = (p['2024'] / p[['2020', '2021', '2022']].mean(axis=1)).reindex(all379)
    core = [w for w in all379 if ratio[w] >= CORE_RATIO]
    return all379, core, {w: float(ratio[w]) for w in all379}


def paper_meta():
    fr = pd.read_parquet(DETECTOR)
    fr = fr[fr['year'].between(YEARS[0], YEARS[-1])]
    cols = ['paper_id', 'year', 'schools'] + [c for c in DETECTOR_COLS.values() if c in fr.columns]
    fr = fr[cols].copy()
    fr['schools'] = fr['schools'].map(lambda v: [x for x in str(v).split(',') if x in D.SCHOOLS])    # comma-joined, as ai_pages.py frame writes it
    return fr.reset_index(drop=True)


# --------------------------------------------------------------------------------------------- count

def _count_chunk(args):
    lo, hi = args
    words = word_lists()[0]
    idx = {w: i for i, w in enumerate(words)}
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    rows = []
    for pid, body in db.execute('select paper_id, body from fulltext where usable = 1 and rowid >= ? and rowid < ?', (lo, hi)):
        if body:
            txt, cutf = clean_fulltext(zlib.decompress(body).decode('utf-8', 'ignore'))
            t = toks(txt)
        else:
            t, cutf = [], False
        c = Counter(w for w in t if w in idx)
        rows.append((pid, len(t), sum(c.values()), [(idx[w], k) for w, k in c.items()], cutf))
    return rows


def run_count(jobs):
    WORK.mkdir(parents=True, exist_ok=True)
    all379, core, _ = word_lists()
    idx = {w: i for i, w in enumerate(all379)}
    core_cols = np.array([idx[w] for w in core])
    meta = paper_meta()
    keep = set(meta['paper_id'])
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    ab = {}
    for pid, a in db.execute('select paper_id, abstract from abstracts'):
        if pid in keep and a and a.strip():
            t = toks(clean_abstract(a))
            c = Counter(w for w in t if w in idx)
            ab[pid] = (len(t), [(idx[w], k) for w, k in c.items()])
    hi = db.execute('select max(rowid) from fulltext').fetchone()[0]
    db.close()
    D.log(abstracts=len(ab), words=len(all379), core=len(core))
    step = 500
    ft, ncut = {}, 0
    with ProcessPoolExecutor(jobs) as ex:
        for part in ex.map(_count_chunk, [(lo, lo + step) for lo in range(0, hi + 1, step)]):
            for pid, n, k, items, cutf in part:
                if pid in keep:
                    ft[pid] = (n, items)
                    ncut += cutf
    D.log(fulltexts=len(ft), reference_list_cut=ncut)
    ids = meta['paper_id'].tolist()

    def matrix(src):
        rows, cols, vals = [], [], []
        for r, pid in enumerate(ids):
            if pid in src:
                for j, k in src[pid][1]:
                    rows.append(r); cols.append(j); vals.append(k)
        return sp.csr_matrix((vals, (rows, cols)), shape=(len(ids), len(all379)), dtype=np.int32)

    for name, src in (('abs', ab), ('ft', ft)):
        m = matrix(src)
        sp.save_npz(WORK / f'counts_{name}.npz', m)
        has = np.array([pid in src for pid in ids])
        ntok = np.array([src[pid][0] if pid in src else 0 for pid in ids])
        pd.DataFrame(dict(paper_id=ids, has=has, ntok=ntok, k379=np.asarray(m.sum(1)).ravel(), kcore=np.asarray(m[:, core_cols].sum(1)).ravel())).to_parquet(WORK / f'papers_{name}.parquet', index=False)
    D.log(counted=len(ids), work=str(WORK))


# --------------------------------------------------------------------------------------------- liang

def run_liang(boot, min_docs, vocab_size):
    import hashlib
    from dose_excess_run import held_out
    aiw = D.MAIN_AIW
    src = {s['key']: s for s in map(json.loads, open(aiw / 'sources.jsonl'))}
    ai = [g for f in sorted(aiw.glob('generated-*.jsonl')) for g in map(json.loads, open(f)) if g['key'] in src and len(g['text'].split()) >= 40]
    ai_tr = [D.norm1(g['text']) for g in ai if not held_out(g['key'])]
    ai_te = [D.norm1(g['text']) for g in ai if held_out(g['key'])]
    hum_te = [D.norm1(s['abstract']) for k, s in src.items() if held_out(k)]
    te_hash = {hashlib.sha1(t[:300].encode()).hexdigest() for t in hum_te}
    meta = paper_meta().set_index('paper_id')
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    rows = [(p, D.norm1(a)) for p, a in db.execute('select paper_id, abstract from abstracts') if p in meta.index and a and len(a.split()) >= 50]
    db.close()
    D.log(liang_abstracts=len(rows), ai_train=len(ai_tr), ai_test=len(ai_te), human_test=len(hum_te))
    tk = {p: E.tokens(t) for p, t in rows}
    year = {p: int(meta.at[p, 'year']) for p, _ in rows}
    hum_tr = [tk[p] for p, t in rows if 2016 <= year[p] <= 2021 and hashlib.sha1(t[:300].encode()).hexdigest() not in te_hash]
    ai_tr_t = [E.tokens(t) for t in ai_tr]
    vocab = E.build_vocab(hum_tr + ai_tr_t, size=vocab_size)
    model = E.LiangMixture(E.occurrence_matrix(hum_tr, vocab), E.occurrence_matrix(ai_tr_t, vocab))
    Xh, Xl = E.occurrence_matrix([E.tokens(t) for t in hum_te], vocab), E.occurrence_matrix([E.tokens(t) for t in ai_te], vocab)
    cal = pd.DataFrame(E.calibration(model, Xh, Xl, alphas=(0, .02, .05, .1, .25, .5, .75, 1.0), n=min(1000, Xh.shape[0])), columns=['alpha_true', 'alpha_hat'])
    D.log(calibration=cal.round(3).values.tolist())
    pid = [p for p, _ in rows]
    X = E.occurrence_matrix([tk[p] for p in pid], vocab)
    yr = np.array([year[p] for p in pid])
    sch = [set(meta.at[p, 'schools']) for p in pid]
    out = []
    for s in GROUPS:
        for y in YEARS:
            m = (yr == y) & (np.ones(len(pid), bool) if s == 'all' else np.array([s in x for x in sch]))
            if m.sum() >= min_docs:
                a, lo, hi = model.estimate(X[np.where(m)[0]], boot=boot, seed=y)
                out.append(dict(school=s, year=y, n=int(m.sum()), alpha=a, lo=lo, hi=hi))
        D.log(school=s, cells=len(out))
    WORK.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_parquet(WORK / 'liang.parquet', index=False)
    cal.to_parquet(WORK / 'liang_calibration.parquet', index=False)
    D.log(liang=len(out), train=dict(human=len(hum_tr), llm=len(ai_tr_t), vocab=len(vocab)))


# --------------------------------------------------------------------------------------------- assemble

def r4(v, k=4):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), k)


def pooled_rate(k, n):
    return 1000.0 * k.sum() / n.sum() if n.sum() else None


def boot_rate(k, n, B=200, seed=0):
    """95% bootstrap interval over papers of the token-pooled rate per 1,000 tokens."""
    if len(k) < 20:
        return None, None
    rng = np.random.default_rng(seed)
    ix = rng.integers(0, len(k), (B, len(k)))
    rates = 1000.0 * k[ix].sum(1) / np.maximum(n[ix].sum(1), 1)
    return float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))


def dets(meta, key):
    """Per-paper detector flag at cutoff t (percent) as the AI pages count it with abstract-only papers included, plus the dose."""
    c = DETECTOR_COLS
    dose = meta[c['dose_cal']].where(meta[c['dose_cal']].notna(), meta[c['dose']])
    has_ft = meta[c['dose']].notna()
    ab_only = ~has_ft & meta[c['abstract_p']].notna()
    flags = {}
    for t in CUTOFFS + [key]:
        bins = np.floor(100 * dose.fillna(0).to_numpy() + 1e-9)
        f = np.where(has_ft, bins >= t, np.where(ab_only, meta[c['abstract_flag']].fillna(0) > 0, False))
        flags[t] = f
    return dose, has_ft.to_numpy(), ab_only.to_numpy(), flags


def spearman(a, b):
    from scipy.stats import spearmanr
    r = spearmanr(a, b)
    return float(r.statistic if hasattr(r, 'statistic') else r[0])


def run_assemble():
    from scipy.stats import pearsonr
    all379, core, ratio = word_lists()
    meta = paper_meta()
    pa, pf = pd.read_parquet(WORK / 'papers_abs.parquet'), pd.read_parquet(WORK / 'papers_ft.parquet')
    assert (pa['paper_id'].to_numpy() == meta['paper_id'].to_numpy()).all() and (pf['paper_id'].to_numpy() == meta['paper_id'].to_numpy()).all()
    Ca, Cf = sp.load_npz(WORK / 'counts_abs.npz').tocsr(), sp.load_npz(WORK / 'counts_ft.npz').tocsr()
    idx = {w: i for i, w in enumerate(all379)}
    core_cols = np.array([idx[w] for w in core])
    yr = meta['year'].to_numpy()
    sch = {s: np.array([s in x for x in meta['schools']]) for s in D.SCHOOLS}
    sch['all'] = np.ones(len(meta), bool)
    dose, has_ft, ab_only, flags = dets(meta, 25)

    has_a = pa['has'].to_numpy() & (pa['ntok'].to_numpy() >= MIN_TOK)
    has_f = pf['has'].to_numpy() & (pf['ntok'].to_numpy() >= MIN_TOK)
    na, ka, kc = pa['ntok'].to_numpy(), pa['k379'].to_numpy(), pa['kcore'].to_numpy()
    nf, kfa, kfc = pf['ntok'].to_numpy(), pf['k379'].to_numpy(), pf['kcore'].to_numpy()

    def cell_stats(mask, n, k379, kcore, shares):
        d = dict(n=int(mask.sum()), tokens=int(n[mask].sum()), rate=r4(pooled_rate(k379[mask], n[mask])), core_rate=r4(pooled_rate(kcore[mask], n[mask])))
        if mask.sum():
            lo, hi = boot_rate(k379[mask], n[mask], seed=1); d['lo'], d['hi'] = r4(lo), r4(hi)
            lo, hi = boot_rate(kcore[mask], n[mask], seed=2); d['core_lo'], d['core_hi'] = r4(lo), r4(hi)
        if shares:
            d['share1'], d['share3'] = r4((kcore[mask] >= 1).mean()) if mask.sum() else None, r4((kcore[mask] >= 3).mean()) if mask.sum() else None
        return d

    trend = {}
    for source, (has, n, k379, kcore, shares) in {'abstract': (has_a, na, ka, kc, True), 'fulltext': (has_f, nf, kfa, kfc, False)}.items():
        trend[source] = {}
        for g in GROUPS:
            trend[source][g] = {}
            for y in YEARS:
                m = has & sch[g] & (yr == y)
                if m.any():
                    trend[source][g][str(y)] = cell_stats(m, n, k379, kcore, shares)
    baseline = {}
    for source, (has, n, k379, kcore) in {'abstract': (has_a, na, ka, kc), 'fulltext': (has_f, nf, kfa, kfc)}.items():
        baseline[source] = {}
        for g in GROUPS:
            m = has & sch[g] & np.isin(yr, PRE)
            baseline[source][g] = dict(n=int(m.sum()), rate=r4(pooled_rate(k379[m], n[m])), core_rate=r4(pooled_rate(kcore[m], n[m])),
                                       share1=r4((kcore[m] >= 1).mean()) if m.any() and source == 'abstract' else None,
                                       share3=r4((kcore[m] >= 3).mean()) if m.any() and source == 'abstract' else None)

    # per-word document counts (abstracts): words.df[word][group] = [count per year]; denominators docs[group] = [abstracts per year]
    docs = {g: [int((has_a & sch[g] & (yr == y)).sum()) for y in YEARS] for g in GROUPS}
    Cb = (Ca > 0).astype(np.int32).tocsc()
    curves = {}
    for w in all379:
        col = Cb[:, idx[w]].toarray().ravel()
        curves[w] = {g: [int((col[has_a & sch[g] & (yr == y)]).sum()) for y in YEARS] for g in GROUPS}
    fam = {}
    for f, members in FAMILIES.items():
        assert all(m in idx for m in members), f
        col = (Cb[:, [idx[m] for m in members]].sum(axis=1).A1 > 0)
        fam[f] = dict(words=members, df={g: [int(col[has_a & sch[g] & (yr == y)].sum()) for y in YEARS] for g in GROUPS})
    # word table, all schools and each school: baseline document share 2016-2022, last-year share, excess ratio (smoothed by 0.5 counts)
    py = [YEARS.index(y) for y in PRE]
    ly = len(YEARS) - 1
    wtab = {}
    for g in GROUPS:
        nb, nl = sum(docs[g][i] for i in py), docs[g][ly]
        rows = []
        for w in all379:
            kb, kl = sum(curves[w][g][i] for i in py), curves[w][g][ly]
            pb, pl = kb / nb if nb else None, kl / nl if nl else None
            rows.append(dict(word=w, base=r4(pb, 5), last=r4(pl, 5), k_base=kb, k_last=kl, ratio=r4(((kl + .5) / (nl + 1)) / ((kb + .5) / (nb + 1)), 3) if nb and nl else None,
                             pubmed=r4(ratio[w], 2), core=w in set(core)))
        wtab[g] = dict(n_base=nb, n_last=nl, rows=rows)

    # Liang
    lg = pd.read_parquet(WORK / 'liang.parquet')
    lcal = pd.read_parquet(WORK / 'liang_calibration.parquet')
    liang = {g: {} for g in GROUPS}
    for r in lg.itertuples():
        if r.year in YEARS:
            liang[r.school][str(r.year)] = dict(n=int(r.n), alpha=r4(r.alpha), lo=r4(r.lo), hi=r4(r.hi))
    calib = [dict(true=r4(a), hat=r4(h), err=r4(h - a)) for a, h in zip(lcal['alpha_true'], lcal['alpha_hat'])]

    # --- marker words versus detector, paper level
    ok = has_a & (na >= MIN_TOK)
    rate_c = np.where(na > 0, 1000.0 * kc / np.maximum(na, 1), np.nan)
    rate_a = np.where(na > 0, 1000.0 * ka / np.maximum(na, 1), np.nan)
    rate_fc = np.where(nf > 0, 1000.0 * kfc / np.maximum(nf, 1), np.nan)
    dosev = dose.to_numpy()
    # words flag: the smallest number of core words in the abstract whose 2016-2021 rate is at most 5%
    pre21 = ok & np.isin(yr, range(2016, 2022))
    k_flag = next((k for k in (1, 2, 3, 4) if (kc[pre21] >= k).mean() <= 0.05), 4)
    wflag = ok & (kc >= k_flag)
    corr = {}
    for label, yrs in (('2016-2022', PRE), ('2023-2025', POST)):
        m = ok & has_ft & np.isin(yr, yrs) & np.isfinite(dosev)
        mf = m & has_f
        corr[label] = dict(
            n=int(m.sum()),
            abstract_core_vs_dose=dict(pearson=r4(pearsonr(rate_c[m], dosev[m])[0]), spearman=r4(spearman(rate_c[m], dosev[m]))),
            abstract_all379_vs_dose=dict(pearson=r4(pearsonr(rate_a[m], dosev[m])[0]), spearman=r4(spearman(rate_a[m], dosev[m]))),
            fulltext_core_vs_dose=dict(n=int(mf.sum()), pearson=r4(pearsonr(rate_fc[mf], dosev[mf])[0]), spearman=r4(spearman(rate_fc[mf], dosev[mf]))))
    by_year_corr = {}
    for y in YEARS:
        m = ok & has_ft & (yr == y) & np.isfinite(dosev)
        by_year_corr[str(y)] = dict(n=int(m.sum()), spearman=r4(spearman(rate_c[m], dosev[m])) if m.sum() > 30 else None)
    flagged = {}
    recon = {}
    for t in CUTOFFS:
        f = flags[t]
        flagged[str(t)] = {}
        recon[str(t)] = {}
        for label, yrs in (('2016-2022', PRE), ('2023-2025', POST)):
            m = ok & np.isin(yr, yrs)
            dm, nm = m & f, m & ~f
            flagged[str(t)][label] = dict(
                flagged=dict(n=int(dm.sum()), core_rate=r4(pooled_rate(kc[dm], na[dm])), rate=r4(pooled_rate(ka[dm], na[dm])), share1=r4((kc[dm] >= 1).mean()) if dm.any() else None),
                not_flagged=dict(n=int(nm.sum()), core_rate=r4(pooled_rate(kc[nm], na[nm])), rate=r4(pooled_rate(ka[nm], na[nm])), share1=r4((kc[nm] >= 1).mean()) if nm.any() else None))
        for y in YEARS:
            m = ok & (yr == y)
            both, det_only = int((m & f & wflag).sum()), int((m & f & ~wflag).sum())
            words_only, neither = int((m & ~f & wflag).sum()), int((m & ~f & ~wflag).sum())
            recon[str(t)][str(y)] = [both, det_only, words_only, neither]
    # agreement statistics at the default cutoff, 2023-2025 and 2016-2021
    agree = {}
    for label, yrs in (('2016-2021', range(2016, 2022)), ('2023-2025', POST)):
        m = ok & np.isin(yr, list(yrs))
        for t in CUTOFFS:
            a, b = flags[t][m], wflag[m]
            n11, n10, n01, n00 = (a & b).sum(), (a & ~b).sum(), (~a & b).sum(), (~a & ~b).sum()
            n = n11 + n10 + n01 + n00
            po = (n11 + n00) / n
            pe = ((n11 + n10) * (n11 + n01) + (n00 + n01) * (n00 + n10)) / n ** 2
            phi_den = np.sqrt(float((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)))
            agree.setdefault(label, {})[str(t)] = dict(n=int(n), detector_flagged=int(n11 + n10), words_flagged=int(n11 + n01), both=int(n11), agreement=r4(po), kappa=r4((po - pe) / (1 - pe)),
                                                       phi=r4((n11 * n00 - n10 * n01) / phi_den if phi_den else None),
                                                       p_words_given_detector=r4(n11 / (n11 + n10)) if n11 + n10 else None, p_words_given_not=r4(n01 / (n01 + n00)) if n01 + n00 else None)
    # detector flagged share by year (all schools) at the stored cutoffs, from the frame the AI pages use: the page cross-checks it against ai_hist.json
    det_check = {str(t): {str(y): r4(float(flags[t][(yr == y)].mean())) for y in YEARS} for t in CUTOFFS}
    det_n = {str(y): int(((yr == y) & (has_ft | ab_only)).sum()) for y in YEARS}

    meta_out = dict(generated=D.now(), last_year=D.LAST_FULL_YEAR, years=[YEARS[0], YEARS[-1]], groups=GROUPS, cutoffs=CUTOFFS,
                    lists=dict(all379=len(all379), core=len(core), core_rule=f'PubMed document frequency 2024 / mean 2020-2022 >= {CORE_RATIO:g} (Kobak et al. 2024 yearly counts)'),
                    text_surface='abstract alone; full texts cut at their last References heading; URLs, e-mail addresses and DOIs removed; lower-case letter tokens',
                    baseline_years=[PRE[0], PRE[-1]], min_tokens=MIN_TOK, words_flag=dict(core_words_at_least=k_flag, pre2022_rate=r4((kc[pre21] >= k_flag).mean())),
                    detector=dict(frame=DETECTOR.name, columns=DETECTOR_COLS, rule='ai_hist.json rule: dose = ai_share_cal else ai_share (full text); abstract flag for abstract-only papers'),
                    liang=dict(vocab=5000, train='2016-2021 universe abstracts (human) vs rewrites of the training half of the sources (LLM); calibration on the held-out half',
                               boot=200), schools_note='a paper counts for each of its schools and once under all')
    words_json = dict(meta=meta_out, core=core, trend=trend, baseline=baseline, liang=liang, liang_calibration=calib, word_table=wtab,
                      detector_vs_words=dict(correlation=corr, correlation_by_year=by_year_corr, flagged=flagged, reconciliation=recon, reconciliation_cells=['both', 'detector_only', 'words_only', 'neither'],
                                             agreement=agree, detector_check=det_check, detector_n=det_n))
    curves_json = dict(meta=dict(generated=meta_out['generated'], years=[YEARS[0], YEARS[-1]], groups=GROUPS, note='df[word][group][year index] = abstracts containing the word; docs[group] = abstracts counted'),
                       docs=docs, df=curves, families=fam, core=core)
    o = OUT / 'words'
    o.mkdir(parents=True, exist_ok=True)
    for name, obj in (('words.json', words_json), ('word_curves.json', curves_json)):
        raw = json.dumps(obj, separators=(',', ':'), allow_nan=False).encode()
        (o / name).write_bytes(raw)
        D.log(wrote=str(o / name), bytes=len(raw))


# --------------------------------------------------------------------------------------------- spot check

def run_spot(n, seed):
    all379, core, _ = word_lists()
    ws, cs = set(all379), set(core)
    meta = paper_meta()
    pa = pd.read_parquet(WORK / 'papers_abs.parquet')
    ids = pa.loc[pa['has'], 'paper_id'].tolist()
    random.Random(seed).shuffle(ids)
    # stratify: half from 2024-2025, half from 2016-2019
    yr = dict(zip(meta['paper_id'], meta['year']))
    pick = [p for p in ids if yr[p] >= 2024][:n // 2] + [p for p in ids if yr[p] <= 2019][:n - n // 2]
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    lines = []
    row = pa.set_index('paper_id')
    pick += [p for p in ids if row.at[p, 'kcore'] >= 2 and p not in pick][:n // 2]   # plus papers that do use marker words
    for p in pick:
        a = db.execute('select abstract from abstracts where paper_id = ?', (p,)).fetchone()[0]
        t = toks(clean_abstract(a))
        found = Counter(w for w in t if w in ws)
        lines.append(f'### {p} year={yr[p]} stored: ntok={int(row.at[p, "ntok"])} k379={int(row.at[p, "k379"])} kcore={int(row.at[p, "kcore"])}')
        lines.append(f'recount: ntok={len(t)} k379={sum(found.values())} kcore={sum(v for w, v in found.items() if w in cs)} found={dict(found)}')
        lines.append('RAW: ' + re.sub(r'\s+', ' ', a))
        lines.append('')
    (WORK / 'spotcheck.txt').write_text('\n'.join(lines))
    D.log(spot=len(pick), path=str(WORK / 'spotcheck.txt'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['count', 'liang', 'assemble', 'spot'])
    ap.add_argument('arg', nargs='?', type=int, default=20)
    ap.add_argument('-j', type=int, default=14)
    ap.add_argument('--boot', type=int, default=200)
    ap.add_argument('--min-docs', type=int, default=100)
    ap.add_argument('--vocab', type=int, default=5000)
    ap.add_argument('--seed', type=int, default=20261105)
    a = ap.parse_args()
    {'count': lambda: run_count(a.j), 'liang': lambda: run_liang(a.boot, a.min_docs, a.vocab), 'assemble': run_assemble, 'spot': lambda: run_spot(a.arg, a.seed)}[a.cmd]()
    sys.stdout.flush()
