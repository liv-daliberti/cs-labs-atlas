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


def detector_spec(name):
    if name == 'v2':
        return dict(model=C.V2_MODEL, threshold=C.V2_THRESHOLD, strict=0.5, abstain_low=None)
    if name == 'v3':
        model = os.environ.get('RV_V3_MODEL') or str(C.V3_DIR / 'models' / 'all' / 'model')
        mj = os.environ.get('RV_V3_METRICS') or str(C.V3_DIR / 'results' / 'all' / 'metrics.json')
        if not (os.path.isdir(model) and os.path.exists(mj)):
            raise SystemExit(f'detector v3 not available: need {model} and {mj} (or RV_V3_MODEL / RV_V3_METRICS)')
        m = json.load(open(mj))
        return dict(model=model, threshold=m['threshold'], strict=m.get('strict', 0.5), abstain_low=m.get('abstain_low'))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detector', default='v2', choices=['v2', 'v3'])
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--tag', default=time.strftime('%Y%m%d'))
    a = ap.parse_args()
    spec = detector_spec(a.detector)
    import dcommon as D
    import dose_score as DS
    import v2common as V
    seen = done_keys(a.detector)
    db = sqlite3.connect(f'file:{C.DB}?mode=ro', uri=True, timeout=600)
    rows = []
    for aid, role, abstract, body, title in db.execute('select t.arxiv_id, t.role, t.abstract, t.body, p.title from texts t join plan p using (arxiv_id)'):
        if int(hashlib.md5(aid.encode()).hexdigest(), 16) % a.nshards != a.shard:
            continue
        b = zlib.decompress(body).decode('utf-8', 'ignore') if body else ''
        h = hashlib.sha1(((abstract or '') + '|' + b).encode('utf-8', 'ignore')).hexdigest()[:16]
        if (aid, role, h) in seen:
            continue
        rows.append((aid, role, title or '', abstract, b, h))
    db.close()
    C.log(step='todo', shard=a.shard, texts=len(rows), already=len(seen), detector=a.detector)
    if not rows:
        return
    pid, prole, pidx, words, ptext = [], [], [], [], []
    for aid, role, _t, _a, b, _h in rows:
        for i, t in enumerate(V.passages(b, cap=PASSAGE_CAP) if b else []):
            pid.append(aid); prole.append(role); pidx.append(i); words.append(len(t.split())); ptext.append(V.norm(t))
    m, dtype = DS.load_models([('det', spec['model']), ('v1', D.V1_MODEL / 'model')])
    t0 = time.time()
    p = DS.predict_v2(*m['det'], dtype, ptext) if ptext else np.zeros(0)
    ab = [(i, r) for i, r in enumerate(rows) if r[3]]
    p_v1 = DS.predict_v1(*m['v1'], dtype, [D.text1(r[2], r[3]) for _, r in ab]) if ab else np.zeros(0)
    p_det = DS.predict_v2(*m['det'], dtype, [V.norm(r[3]) for _, r in ab]) if ab else np.zeros(0)
    pas = pd.DataFrame(dict(arxiv_id=pid, role=prole, pidx=np.array(pidx, np.int32), words=np.array(words, np.int32), p=p))
    absd = pd.DataFrame(dict(arxiv_id=[r[0] for r in rows], role=[r[1] for r in rows], text_hash=[r[5] for r in rows]))
    npass = pd.Series([f'{x}|{y}' for x, y in zip(pid, prole)]).value_counts()
    absd['n_passages'] = [int(npass.get(f'{r[0]}|{r[1]}', 0)) for r in rows]
    absd['body_words'] = [len(r[4].split()) for r in rows]
    absd['p_abs_v1'] = np.nan; absd['p_abs_det'] = np.nan
    for (i, _), v1, dt in zip(ab, p_v1, p_det):
        absd.loc[i, 'p_abs_v1'] = v1; absd.loc[i, 'p_abs_det'] = dt
    d = parts_dir(a.detector)
    write_atomic(pas, d / f'{a.tag}-{a.shard}.passages.parquet')
    write_atomic(absd, d / f'{a.tag}-{a.shard}.abstracts.parquet')   # last: its hashes mark the shard done
    (d / 'detector.json').write_text(json.dumps(dict(detector=a.detector, threshold=spec['threshold'], strict=spec['strict'], abstain_low=spec['abstain_low'],
                                                     v1_threshold=D.V1_THRESHOLD, model=str(spec['model']))))
    C.log(step='done', shard=a.shard, texts=len(rows), passages=len(ptext), minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    main()
