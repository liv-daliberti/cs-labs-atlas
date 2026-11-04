"""Does fp16 (RTX 2080 Ti has no bf16) reproduce the bf16 A5000 detector scores?  Run with DOSE_AMP=fp16 on a 2080 Ti lane.

  check_precision.py [--papers 150] [--abstracts 2000]
Re-scores a sample of already scored papers (stored bf16 parts) and writes AI_SCORES/results/precision_check_<gpu>.json: for the passage model and the v1 abstract
model the Pearson correlation of the logits, the largest absolute logit difference, and the share of texts whose flag at the production threshold changes.
The 2080 lanes are used for detector scoring only if the flag change is below 0.5% and the logit correlation above 0.999.
"""
import argparse
import json
import sqlite3
import zlib

import numpy as np
import pandas as pd

import dcommon as D
import dose_score as DS


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1 - 1e-12)
    return np.log(p / (1 - p))


def compare(old, new, thr):
    a, b = logit(old), logit(new)
    return dict(n=int(len(a)), logit_corr=float(np.corrcoef(a, b)[0, 1]), max_abs_logit_diff=float(np.abs(a - b).max()), flag_change=float(((np.asarray(old) >= thr) != (np.asarray(new) >= thr)).mean()))


def run(n_papers, n_abs):
    import torch
    import v2common as V
    gpu = torch.cuda.get_device_name(0).replace(' ', '_')
    ps = pd.concat([pd.read_parquet(f) for f in sorted((D.PARTS / 'fulltext').glob('*.passages.parquet'))[:1]])
    papers = sorted(ps['paper_id'].unique())[:n_papers]
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True)
    texts, old = [], []
    for pid in papers:
        body = zlib.decompress(db.execute('select body from fulltext where paper_id = ?', (pid,)).fetchone()[0]).decode('utf-8', 'ignore')
        stored = ps[ps['paper_id'] == pid].sort_values('pidx')['p'].to_numpy()
        for t, p in zip(V.passages(body), stored):
            texts.append(V.norm(t)); old.append(p)
    ab = pd.concat([pd.read_parquet(f) for f in sorted((D.PARTS / 'abstract').glob('*.parquet'))[:1]]).head(n_abs)
    rows = {r[0]: r for r in db.execute(f'select paper_id, title, abstract from abstracts where paper_id in ({",".join("?" * len(ab))})', list(ab['paper_id']))}
    m, dtype = DS.load_models([('v1', D.V1_MODEL / 'model'), ('v2', D.V2_MODEL)])
    out = dict(gpu=gpu, amp=DS.AMP,
               passages=compare(old, DS.predict_v2(*m['v2'], dtype, texts), D.V2_THRESHOLD),
               abstracts=compare(ab['p_v1'], DS.predict_v1(*m['v1'], dtype, [D.text1(rows[p][1], rows[p][2]) for p in ab['paper_id']]), D.V1_THRESHOLD))
    out['ok'] = all(out[k]['flag_change'] < 0.005 and out[k]['logit_corr'] > 0.999 for k in ('passages', 'abstracts'))
    D.RESULTS.mkdir(parents=True, exist_ok=True)
    (D.RESULTS / f'precision_check_{gpu}_{DS.AMP}.json').write_text(json.dumps(out, indent=1))
    D.log(**out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--papers', type=int, default=150)
    ap.add_argument('--abstracts', type=int, default=2000)
    a = ap.parse_args()
    run(a.papers, a.abstracts)
