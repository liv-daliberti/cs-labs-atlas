"""Experiment B step 3: score every version's passages and abstract with a detector (GPU, resumable). The detector is a PARAMETER.

  rv_score.py --detector v2 --shard I --nshards N [--tag T]
--detector v2   ai-writing/detector_v2 (threshold 1% passage FPR by design: V2_THRESHOLD; strict cut 0.5); the model and threshold are read from its files
--detector v3   ai-writing/detector_v3/models/all/model + results/all/metrics.json (keys `threshold`, optional `abstain_low`, `strict`); RV_V3_MODEL / RV_V3_METRICS override.
                The model must be a ModernBERT sequence classifier with the v2 head layout (dose_score.predict_v2 pooling); swap the function in DETECTORS if v3 differs.
inputs   DATA/revision.sqlite texts (rv_fetch.py merge): body (zlib) and abstract of every v1 / final text; passages as detector_v2/v2common.passages + norm
outputs  DATA/parts/<detector>/<tag>-<i>.passages.parquet (arxiv_id, role, pidx, words, p) and .abstracts.parquet (arxiv_id, role, text_hash, p_abs_v1, p_abs_det);
         DATA/parts/<detector>/detector.json (thresholds in use). A text whose hash is already in a part is skipped, so a re-run scores only the delta.
The abstract is scored by the legacy abstract detector v1 (calibrated for abstracts at its 1% threshold, as the dose study) and by the chosen detector on the abstract alone
(not calibrated for abstracts: robustness only).
"""
import argparse
import hashlib
import json
import os
import sqlite3
import time
import zlib

import numpy as np
import pandas as pd

import rv_common as C

PASSAGE_CAP = 100
CHUNK = int(os.environ.get('RV_CHUNK', '250'))      # texts per written part (a timed-out shard keeps its finished chunks)


def detector_spec(name):
    if name == 'v2':
        return dict(model=C.V2_MODEL, threshold=C.V2_THRESHOLD, strict=0.5, abstain_low=None)
    if name == 'v3':
        model = os.environ.get('RV_V3_MODEL') or str(C.V3_DIR / 'models' / 'all' / 'model')
        mj = os.environ.get('RV_V3_METRICS') or str(C.V3_DIR / 'results' / 'operating_point.json')
        if not (os.path.isdir(model) and os.path.exists(mj)):
            raise SystemExit(f'detector v3 not available: need {model} and {mj} (or RV_V3_MODEL / RV_V3_METRICS)')
        m = json.load(open(mj))
        # v3 passage score = z (log-odds, detector_v3/score_sections.py); flag = z >= thr_z (0.3% calibration false-alarm rate); strict = z >= 0 (P(AI) >= 0.5);
        # passages that abstain (under `abstain_words` words or mid-sentence-capital share above `midcap_cut`) are neither stored nor counted.
        return dict(model=model, threshold=m['thr_z'], strict=0.0, abstain_low=None, abstain_words=m['abstain_words'], midcap_cut=m['midcap_cut'], score='z')
    raise SystemExit(f'unknown detector {name}')


def parts_dir(det):
    return C.DATA / 'parts' / det


def done_keys(det):
    seen = set()
    for f in parts_dir(det).glob('*.abstracts.parquet'):
        t = pd.read_parquet(f, columns=['arxiv_id', 'role', 'text_hash'])
        seen |= set(zip(t['arxiv_id'], t['role'], t['text_hash']))
    return seen


def write_atomic(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.tmp-' + path.name)
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def import_v2(want, a):
    """Stored copies, detector v2: the dose study's passage scores (AI_SCORES) of the same texts, relabelled with the arXiv id and role `stored`."""
    import dcommon as D
    db = sqlite3.connect(f'file:{D.DB}?mode=ro', uri=True)
    ids = list(want)
    pas, ab = [], []
    for i in range(0, len(ids), 500):
        q = ','.join('?' * len(ids[i:i + 500]))
        pas.append(pd.read_sql(f'select paper_id, pidx, words, p from passages where paper_id in ({q})', db, params=ids[i:i + 500]))
        ab.append(pd.read_sql(f'select paper_id, p_ai_abstract as p_abs_v1, p_v2_abstract as p_abs_det, n_passages, body_words from papers where paper_id in ({q})', db, params=ids[i:i + 500]))
    db.close()
    pas, ab = pd.concat(pas), pd.concat(ab)
    pas['arxiv_id'] = pas['paper_id'].map(lambda p: want[p][0]); pas['role'] = 'stored'
    ab['arxiv_id'] = ab['paper_id'].map(lambda p: want[p][0]); ab['role'] = 'stored'; ab['text_hash'] = 'dose-' + ab['paper_id']
    d = parts_dir('v2')
    write_atomic(pas[['arxiv_id', 'role', 'pidx', 'words', 'p']], d / f'{a.tag}-stored.passages.parquet')
    write_atomic(ab[['arxiv_id', 'role', 'text_hash', 'n_passages', 'body_words', 'p_abs_v1', 'p_abs_det']], d / f'{a.tag}-stored.abstracts.parquet')
    (d / 'detector.json').write_text(json.dumps(dict(detector='v2', threshold=C.V2_THRESHOLD, strict=0.5, abstain_low=None, v1_threshold=D.V1_THRESHOLD, model=str(C.V2_MODEL))))
    C.log(step='imported stored v2 scores', papers=len(ab), passages=len(pas))


def import_v3(want, a, spec):
    """Stored copies, detector v3: the v3 container's MAIN-body passage scores (AI_SCORES = the v3 container, dose/dose_build_v3.py) of the same texts, relabelled with the arXiv id."""
    import dcommon as D
    db = sqlite3.connect(f'file:{D.DB}?mode=ro', uri=True)
    ids = list(want)
    pas, ab = [], []
    for i in range(0, len(ids), 500):
        q = ','.join('?' * len(ids[i:i + 500]))
        pas.append(pd.read_sql(f'select paper_id, pidx, words, p from passages where paper_id in ({q})', db, params=ids[i:i + 500]))
        ab.append(pd.read_sql(f'select paper_id, p_ai_abstract as p_abs_v1, n_passages, body_words from papers where paper_id in ({q})', db, params=ids[i:i + 500]))
    db.close()
    pas, ab = pd.concat(pas), pd.concat(ab)
    ab = ab[ab['n_passages'].notna()]
    pas = pas[pas['paper_id'].isin(set(ab['paper_id']))]
    pas['arxiv_id'] = pas['paper_id'].map(lambda p: want[p][0]); pas['role'] = 'stored'
    ab['arxiv_id'] = ab['paper_id'].map(lambda p: want[p][0]); ab['role'] = 'stored'; ab['text_hash'] = 'dose3-' + ab['paper_id']; ab['p_abs_det'] = np.nan
    d = parts_dir('v3')
    write_atomic(pas[['arxiv_id', 'role', 'pidx', 'words', 'p']], d / f'{a.tag}-stored.passages.parquet')
    write_atomic(ab[['arxiv_id', 'role', 'text_hash', 'n_passages', 'body_words', 'p_abs_v1', 'p_abs_det']], d / f'{a.tag}-stored.abstracts.parquet')
    (d / 'detector.json').write_text(json.dumps(dict(detector='v3', threshold=spec['threshold'], strict=spec['strict'], abstain_low=None, v1_threshold=D.V1_THRESHOLD, model=str(spec['model']),
                                                     score='z', condition='main body only, abstained passages excluded')))
    C.log(step='imported stored v3 scores', papers=len(ab), passages=len(pas))


def sections_main(text):
    """Main body of an arXiv full text for detector v3 (fulltext_sections.split_text: Introduction to references/appendix); the text itself when the split finds nothing."""
    import importlib.util
    path = os.environ.get('RV_SECTIONS_PY') or '/n/fs/resemble/homogenizing-science/worktrees/fulltext-sections/ai-writing/fulltext_sections.py'
    spec = importlib.util.spec_from_file_location('fulltext_sections', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    main = m.split_text(text)['main']
    return main if len(main.split()) >= 200 else text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detector', default='v2', choices=['v2', 'v3'])
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--tag', default=time.strftime('%Y%m%d'))
    ap.add_argument('--source', default='versions', choices=['versions', 'stored'],
                    help='versions: the fetched arXiv v1/final texts; stored: the lab papers\' stored full texts of the kind-S plan (role `stored`)')
    ap.add_argument('--import-v2', action='store_true', help='stored + v2 only: copy the dose study\'s existing scores instead of scoring again (same detector, same splitter)')
    a = ap.parse_args()
    spec = detector_spec(a.detector)
    seen = done_keys(a.detector)
    rows = []
    if a.source == 'stored':
        import sqlite3 as sq
        pl = sq.connect(f'file:{C.DB}?mode=ro', uri=True)
        want = {pid: (aid, title) for aid, pid, title in pl.execute("select arxiv_id, paper_id, title from plan where kind = 'S'")}
        pl.close()
        if a.import_v2:
            return import_v2(want, a)
        if a.detector == 'v3':
            return import_v3(want, a, spec)
        tx = sq.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
        ab = dict(tx.execute('select paper_id, abstract from abstracts'))
        for pid, body in tx.execute('select paper_id, body from fulltext where usable = 1'):
            if pid not in want or int(hashlib.md5(want[pid][0].encode()).hexdigest(), 16) % a.nshards != a.shard:
                continue
            b = zlib.decompress(body).decode('utf-8', 'ignore')
            h = hashlib.sha1(((ab.get(pid) or '') + '|' + b).encode('utf-8', 'ignore')).hexdigest()[:16]
            if (want[pid][0], 'stored', h) not in seen:
                rows.append((want[pid][0], 'stored', want[pid][1] or '', ab.get(pid), b, h))
        tx.close()
    else:
        db = sqlite3.connect(f'file:{C.DB}?mode=ro', uri=True, timeout=600)
        titles = dict(db.execute('select arxiv_id, title from plan'))
        for aid, role, abstract, body in db.execute('select arxiv_id, role, abstract, body from texts'):
            if int(hashlib.md5(aid.encode()).hexdigest(), 16) % a.nshards != a.shard:
                continue
            b = zlib.decompress(body).decode('utf-8', 'ignore') if body else ''
            h = hashlib.sha1(((abstract or '') + '|' + b).encode('utf-8', 'ignore')).hexdigest()[:16]
            if (aid, role, h) in seen:
                continue
            rows.append((aid, role, titles.get(aid) or '', abstract, b, h))
        db.close()
    C.log(step='todo', shard=a.shard, texts=len(rows), already=len(seen), detector=a.detector)
    if not rows:
        return
    for k in range(0, len(rows), CHUNK):
        score_rows(rows[k:k + CHUNK], a, spec, f'{a.tag}-{a.shard}-c{k // CHUNK}')


def score_rows(rows, a, spec, part):
    """Score a chunk of texts and write it as one part (resumable: a finished chunk's text hashes are skipped on re-run)."""
    import dcommon as D
    import dose_score as DS
    import v2common as V
    pid, prole, pidx, words, ptext = [], [], [], [], []
    n_abst = {}
    v3 = a.detector == 'v3'
    for aid, role, _t, _a, b, _h in rows:
        body = sections_main(b) if (v3 and b) else b
        for i, t in enumerate(V.passages(body, cap=PASSAGE_CAP) if body else []):
            w = len(t.split())
            if v3 and (w < spec['abstain_words'] or V.quality(t)['midcap'] > spec['midcap_cut']):      # the v3 abstain rule: not scored, not counted
                n_abst[(aid, role)] = n_abst.get((aid, role), 0) + 1
                continue
            pid.append(aid); prole.append(role); pidx.append(i); words.append(w); ptext.append(V.norm(t))
    t0 = time.time()
    ab = [(i, r) for i, r in enumerate(rows) if r[3]]
    if v3:
        import importlib.util
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        sp = importlib.util.spec_from_file_location('detector_v2_predict', str(C.MAIN_AIW / 'detector_v2' / 'detector.py'))
        D2 = importlib.util.module_from_spec(sp); sp.loader.exec_module(D2)
        tok = AutoTokenizer.from_pretrained(spec['model'])
        det = AutoModelForSequenceClassification.from_pretrained(spec['model']).cuda().eval()
        pp = D2.predict(det, tok, ptext, bs=128) if ptext else np.zeros(0)
        p = np.log(np.clip(pp, 1e-300, None)) - np.log(np.clip(1 - pp, 1e-300, None))      # z, as score_sections.py
        m, dtype = DS.load_models([('v1', D.V1_MODEL / 'model')])
        p_v1 = DS.predict_v1(*m['v1'], dtype, [D.text1(r[2], r[3]) for _, r in ab]) if ab else np.zeros(0)
        p_det = np.full(len(ab), np.nan)
    else:
        m, dtype = DS.load_models([('det', spec['model']), ('v1', D.V1_MODEL / 'model')])
        p = DS.predict_v2(*m['det'], dtype, ptext) if ptext else np.zeros(0)
        p_v1 = DS.predict_v1(*m['v1'], dtype, [D.text1(r[2], r[3]) for _, r in ab]) if ab else np.zeros(0)
        p_det = DS.predict_v2(*m['det'], dtype, [V.norm(r[3]) for _, r in ab]) if ab else np.zeros(0)
    pas = pd.DataFrame(dict(arxiv_id=pid, role=prole, pidx=np.array(pidx, np.int32), words=np.array(words, np.int32), p=p))
    absd = pd.DataFrame(dict(arxiv_id=[r[0] for r in rows], role=[r[1] for r in rows], text_hash=[r[5] for r in rows]))
    npass = pd.Series([f'{x}|{y}' for x, y in zip(pid, prole)]).value_counts()
    absd['n_passages'] = [int(npass.get(f'{r[0]}|{r[1]}', 0)) for r in rows]
    absd['body_words'] = [len(r[4].split()) for r in rows]
    absd['n_abstained'] = [int(n_abst.get((r[0], r[1]), 0)) for r in rows]
    absd['p_abs_v1'] = np.nan; absd['p_abs_det'] = np.nan
    for (i, _), v1, dt in zip(ab, p_v1, p_det):
        absd.loc[i, 'p_abs_v1'] = v1; absd.loc[i, 'p_abs_det'] = dt
    d = parts_dir(a.detector)
    write_atomic(pas, d / f'{part}.passages.parquet')
    write_atomic(absd, d / f'{part}.abstracts.parquet')   # last: its hashes mark the shard done
    (d / 'detector.json').write_text(json.dumps(dict(detector=a.detector, threshold=spec['threshold'], strict=spec['strict'], abstain_low=spec['abstain_low'],
                                                     v1_threshold=D.V1_THRESHOLD, model=str(spec['model']),
                                                     **({'score': 'z', 'condition': 'main body only (fulltext_sections.split_text), abstained passages excluded'} if v3 else {}))))
    C.log(step='done', part=part, shard=a.shard, texts=len(rows), passages=len(ptext), minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    main()
