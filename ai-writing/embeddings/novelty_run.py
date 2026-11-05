"""Novelty tables for one model and text kind (abstract vectors, or the full-text per-paper mean).

  novelty_run.py --model M [--kind abstract|fulltext]
-> results/novelty_<M>_<kind>.parquet           one row per (scope, scope_id, paper, k): n_ref, nov_max, nov_nn, and the size-matched *_cap columns
   results/novelty_trend_<M>_<kind>.parquet     mean by year with a 95% cluster-bootstrap interval (clusters = the paper's first lab)
   results/novelty_contrast_<M>_<kind>.parquet  post (2023-2025) minus pre (2017-2022) with the interval
Scopes: all papers, each school (a paper counts in every school it belongs to), each department (school|dept), each lab. See novelty.py for the maths.
Rows enter the trend and contrast tables when the pool holds at least MIN_REF papers (all / school 100, department 20, lab 5): a 2017 paper
compared with the previous year of a tiny lab says little. Year 2016 has no earlier pool (the packages start in 2016) and stays out.
"""
import argparse

import numpy as np
import pandas as pd

import ecommon as C
import emb_load as L
import measures as M
import novelty as N

KS = (1, 3, 5)
MEASURES = ('nov_max', 'nov_nn', 'nov_max_cap', 'nov_nn_cap')
MIN_REF = {'all': 100, 'school': 100, 'dept': 20, 'lab': 5}
PRE_YEARS = range(2017, 2023)


def device():
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else None
    except ImportError:
        return None


def run(model, kind):
    papers, lp = L.universe()
    ids, X, meta = L.vectors(model, kind)
    row = {p: i for i, p in enumerate(ids)}
    papers = papers[papers['paper_id'].isin(row)].reset_index(drop=True)
    Z, _ = N.center_normalize(X[[row[p] for p in papers['paper_id']]])
    pos = {p: i for i, p in enumerate(papers['paper_id'])}
    years = papers['year'].to_numpy()
    mem = L.memberships(lp[lp['paper_id'].isin(pos)])
    mem['idx'] = mem['paper_id'].map(pos)
    scopes = [('all', 'all', np.arange(len(papers)))]
    for (scope, sid), g in mem.groupby(['scope', 'scope_id']):
        scopes.append((scope, sid, g['idx'].to_numpy()))
    C.log(model=model, kind=kind, papers=len(papers), scopes=len(scopes), device=device())
    r = N.novelty_scopes(Z, years, scopes, ks=KS, nn=5, cap=2000, seed=C.SEED, dev=device())
    out = pd.DataFrame(dict(scope=r['scope'], scope_id=r['scope_id'], paper_id=papers['paper_id'].to_numpy()[r['paper'].astype(int)], year=years[r['paper'].astype(int)],
                            k=r['k'].astype(int), n_ref=r['n_ref'].astype(int), nov_max=r['nov_max'].astype(np.float32), nov_nn=r['nov_nn'].astype(np.float32),
                            n_ref_cap=r['n_ref_cap'].astype(int), nov_max_cap=r['nov_max_cap'].astype(np.float32), nov_nn_cap=r['nov_nn_cap'].astype(np.float32)))
    C.RESULTS.mkdir(parents=True, exist_ok=True)
    tag = f'{model}_{kind}'
    out.to_parquet(C.RESULTS / f'novelty_{tag}.parquet', index=False)
    first_lab = lp.sort_values('lab_id').drop_duplicates('paper_id').set_index('paper_id')['lab_id']
    out['cluster'] = out['paper_id'].map(first_lab).fillna('none')
    trend, contrast = [], []
    for scope in ('all', 'school', 'dept', 'lab'):
        d = out[(out['scope'] == scope) & (out['n_ref'] >= MIN_REF[scope])]
        groups = [(sid, g) for sid, g in d.groupby('scope_id')] if scope == 'school' else [('all' if scope == 'all' else 'pooled', d)]
        for sid, g0 in groups:
            for k, g in g0.groupby('k'):
                for meas in MEASURES:
                    v = g[meas].to_numpy()
                    for y, (m, lo, hi, n) in M.mean_by_year(v, g['year'].to_numpy(), g['cluster'].to_numpy(), reps=300).items():
                        trend.append(dict(model=model, kind=kind, scope=scope, scope_id=sid, k=int(k), measure=meas, year=y, mean=m, lo=lo, hi=hi, n=n))
                    sel = g['year'].isin(list(PRE_YEARS) + list(range(2023, 2026))).to_numpy()
                    if sel.sum() > 50:
                        est, lo, hi, nc = M.diff_ci(v[sel], g['cluster'].to_numpy()[sel], (g['year'].to_numpy()[sel] >= 2023), reps=500)
                        contrast.append(dict(model=model, kind=kind, scope=scope, scope_id=sid, k=int(k), measure=meas, diff=est, lo=lo, hi=hi, clusters=nc,
                                             mean_pre=float(np.nanmean(v[sel][g['year'].to_numpy()[sel] < 2023])), mean_post=float(np.nanmean(v[sel][g['year'].to_numpy()[sel] >= 2023])),
                                             n=int(sel.sum())))
    pd.DataFrame(trend).to_parquet(C.RESULTS / f'novelty_trend_{tag}.parquet', index=False)
    pd.DataFrame(contrast).to_parquet(C.RESULTS / f'novelty_contrast_{tag}.parquet', index=False)
    C.log(novelty=tag, rows=len(out), trend_rows=len(trend), contrast_rows=len(contrast), revision=(meta or {}).get('revision'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True); ap.add_argument('--kind', default='abstract', choices=['abstract', 'fulltext'])
    a = ap.parse_args()
    run(a.model, a.kind)
