"""Question 2: the distribution over cited works by citing year, for all lab papers and for AI-flagged vs not -- is its
spread ("variance") going down?

Citing papers: analyze.Data (>= 5 references in the source). Cells: citing year 2016-2026 x {all, flagged, not flagged}
(flagged = ai_share >= 0.25; before 2023 only 'all'). Every cell is DRAWS equal-size random draws of N citing papers
(N = 60, small enough for the smallest post-2022 flagged cell), pooled citations rarefied to T = 15 N, so neither group nor
year size moves the measures. Measures of one draw:
  analyze.Data.measures   H_work, gini, distinct (distribution over works); H_venue, H_field; top1; age; recent; ...
  sd_year                 SD of the cited works' publication years over the pooled resolved citations
  sd_lc                   SD of the cited works' age-adjusted log(1 + cited_by_count) (spread in popularity)
  iqr_year                interquartile range of the cited publication years
Per-paper spread (paper_measures*.parquet from within.py): mean per-paper year_sd and lc_sd per cell, bootstrap over papers.
-> results/dist_by_year_<src>.csv (cell x measure: mean, lo, hi over draws), results/dist_by_year_trend_<src>.csv (linear
   trend per year of each measure for 'all', 2016-2025, with the 2.5-97.5 percentiles of the per-draw slope)
usage: dist_by_year.py [--source oa|s2]
"""
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
RES, DATA = HERE / 'results', HERE / 'data'
SEED, DRAWS, N = 20261022, 500, 60
MEAS = ['H_work', 'gini', 'distinct', 'H_venue', 'H_field', 'top1', 'logcbc_adj', 'age', 'recent', 'canon', 'sd_year', 'iqr_year', 'sd_lc']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--source', default='oa'); src = ap.parse_args().source
    import analyze as A
    D = A.Data(src)
    y, a = D.C.year.values, D.C.ai_share.values
    rows, store = [], {}
    for yy in range(2016, 2027):
        for g in ('all', 'flagged', 'not'):
            if g != 'all' and yy < 2023:
                continue
            m = (y == yy) & (True if g == 'all' else (a >= 0.25) if g == 'flagged' else (a < 0.25))
            idx = np.flatnonzero(m)
            if len(idx) < N:
                continue
            rng = np.random.default_rng(SEED + yy * 10 + ('all', 'flagged', 'not').index(g))
            out = []
            for _ in range(DRAWS):
                pick = rng.choice(idx, N, replace=False)
                r = D.measures(pick, 15 * N, rng)
                e = D.refs(pick); w = D.ref[e]; ok = D.resolved[w]
                yrs = D.wyear[w[ok]]; lc = D.wlc_adj[w[ok]]
                r['sd_year'] = float(np.nanstd(yrs)); r['sd_lc'] = float(np.nanstd(lc))
                q = np.nanpercentile(yrs, [25, 75]); r['iqr_year'] = float(q[1] - q[0])
                out.append(r)
            df = pd.DataFrame(out); store[(yy, g)] = df
            for k in MEAS:
                v = df[k].values.astype(float)
                rows.append(dict(year=yy, group=g, papers=len(idx), N=N, measure=k, mean=np.nanmean(v), lo=np.nanpercentile(v, 2.5),
                                 hi=np.nanpercentile(v, 97.5)))
    R = pd.DataFrame(rows)
    # per-paper spread from within.py
    sfx = '' if src == 'oa' else f'_{src}'
    P = pd.read_parquet(DATA / f'paper_measures{sfx}.parquet')
    rng = np.random.default_rng(SEED)
    pp = []
    for yy in range(2016, 2027):
        for g in ('all', 'flagged', 'not'):
            if g != 'all' and yy < 2023:
                continue
            d = P[(P.year == yy) & ((P.ai_share >= 0) if g == 'all' else (P.ai_share >= 0.25) if g == 'flagged' else (P.ai_share < 0.25))]
            for k in ('year_sd', 'lc_sd'):
                v = d[k].dropna().values
                if len(v) < 30:
                    continue
                bs = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(500)]
                pp.append(dict(year=yy, group=g, papers=len(v), N=None, measure=f'pp_{k}', mean=v.mean(), lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5)))
    R = pd.concat([R, pd.DataFrame(pp)])
    R.to_csv(RES / f'dist_by_year_{src}.csv', index=False)
    # linear trend 2016-2025 for 'all': slope per year, per draw index
    yrs = [yy for yy in range(2016, 2026) if (yy, 'all') in store]
    tr = []
    for k in MEAS:
        M = np.array([store[(yy, 'all')][k].values for yy in yrs])  # years x draws
        x = np.array(yrs) - np.mean(yrs)
        sl = (x[:, None] * (M - M.mean(0))).sum(0) / (x ** 2).sum()
        pre = np.array([store[(yy, 'all')][k].values for yy in yrs if yy <= 2022]).mean(0)
        post = np.array([store[(yy, 'all')][k].values for yy in yrs if yy >= 2023]).mean(0)
        tr.append(dict(measure=k, slope_per_year=np.nanmean(sl), lo=np.nanpercentile(sl, 2.5), hi=np.nanpercentile(sl, 97.5),
                       mean_2016_2022=np.nanmean(pre), mean_2023_2025=np.nanmean(post), diff=np.nanmean(post - pre),
                       diff_lo=np.nanpercentile(post - pre, 2.5), diff_hi=np.nanpercentile(post - pre, 97.5)))
    T = pd.DataFrame(tr); T.to_csv(RES / f'dist_by_year_trend_{src}.csv', index=False)
    with pd.option_context('display.width', 220):
        print(T.round(4).to_string(index=False))
    print(json.dumps(dict(done=src, cells=int(R.groupby(['year', 'group']).ngroups))))


if __name__ == '__main__':
    main()
