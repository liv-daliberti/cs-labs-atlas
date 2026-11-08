"""The AI-share layer for the site (owner 2026-11-07: publish only this layer): ai/ai_share.json from a study run's tables.

reads   <results>/tables/{ai_series,ai_contrasts,ai_fp_corrected,ai_coverage}.csv and <snapshot>/ai/v3_error_table.json, MANIFEST.json
writes  <out>/ai_share.json   (default <results>/site/; copy it into the folder named by make_release.py --ai-site-data)
Shape: {meta, series: {scope: {measure: [{year, est, lo, hi, n}]}}, contrasts: {scope: {measure: {...}}}, corrected: [...], coverage: [...], error_table}.
Shares are fractions (0-1). Scopes: `all` (every school with scored text; the partial schools have almost none) and each school. Years 2016-2025 only.
Convergence and event-study results are NOT in this file (owner decision).
usage: study_ai_share.py [--id 2026-11-07] [--out DIR]
"""
import argparse
import json
import time

import pandas as pd

import study_common as C

MEASURES = ['heavy_main', 'heavy_main_appendix', 'dose_main', 'dose_main_appendix']


def num(x):
    return None if pd.isna(x) else round(float(x), 6)


def build(tables, snapshot, release_id, snap_id, man_cov=None):
    ser = tables['ai_series']
    ser = ser[(ser['sample'] == 'all') & ser.measure.isin(MEASURES) & (ser.year <= C.LAST)]
    con = tables['ai_contrasts']
    con = con[(con['sample'] == 'all') & con.measure.isin(MEASURES)]
    scope_name = lambda s: 'all' if s == 'ALL' else s  # noqa: E731
    out_s, out_c = {}, {}
    for (sc, m), g in ser[ser.scope.isin(['ALL'] + C.SCHOOLS)].groupby(['scope', 'measure']):
        g = g.sort_values('year')
        if g['n'].sum() < 100:
            continue
        out_s.setdefault(scope_name(sc), {})[m] = [dict(year=int(r.year), est=num(r.est), lo=num(r.lo), hi=num(r.hi), n=int(r.n)) for r in g.itertuples()]
    for (sc, m), g in con[con.scope.isin(['ALL'] + C.SCHOOLS)].groupby(['scope', 'measure']):
        if scope_name(sc) not in out_s or m not in out_s[scope_name(sc)]:
            continue
        a = g[g.contrast == 'post_minus_pre']
        b = g[g.contrast == 'placebo_2019_21_minus_2016_18']
        if a.empty:
            continue
        a, b = a.iloc[0], (b.iloc[0] if len(b) else None)
        out_c.setdefault(scope_name(sc), {})[m] = dict(pre=num(a.pre), post=num(a.post), est=num(a.est), lo=num(a.lo), hi=num(a.hi),
                                                       placebo_est=num(b.est) if b is not None else None, placebo_lo=num(b.lo) if b is not None else None,
                                                       placebo_hi=num(b.hi) if b is not None else None)
    fp = tables['ai_fp_corrected']
    fp = fp[(fp.scope == 'ALL') & (fp.fpr == 'fpr') & (fp.year >= 2023) & (fp.year <= C.LAST)]
    corrected = []
    for y, g in fp.groupby('year'):
        z, h = g[g.miss == 'miss0'].iloc[0], g[g.miss == 'miss6.6'].iloc[0]
        corrected.append(dict(year=int(y), observed=num(z.observed), miss0=num(z.corrected), miss0_lo=num(z.corrected_lo), miss0_hi=num(z.corrected_hi),
                              miss6_6=num(h.corrected), miss6_6_lo=num(h.corrected_lo), miss6_6_hi=num(h.corrected_hi)))
    cov = tables['ai_coverage']
    cov = cov[cov.year.between(C.FIRST, C.LAST)]
    coverage = []
    for s in C.SCHOOLS:
        g = cov[cov.school == s]
        n, k = int(g.papers.sum()), int(g.scored.sum())
        h = int(g.held.sum()) if 'held' in g else None
        coverage.append(dict(school=s, papers=n, held_fulltext=h, scored_fulltext=k, held_share=round(h / n, 4) if (n and h is not None) else None,
                             share=round(k / n, 4) if n else None, partial=s in C.PARTIAL))
    et = json.loads((snapshot / 'ai' / 'v3_error_table.json').read_text())
    meta = dict(schema=1, snapshot=snap_id, release=release_id, detector='v3', last_year=C.LAST, first_year=C.FIRST, post_start=C.POST_START,
                generated=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                ci_method='95% percentile interval of a lab-cluster bootstrap (400 draws, resampled within school); a paper of two labs counts in both',
                conditions={'heavy': 'share of papers with at least 25% of scored main-body passages flagged', 'dose': 'mean share of scored passages flagged',
                            'main': 'main body only', 'main_appendix': 'main body plus appendix (section split of the full text)'},
                exclusions='detector-training papers (trained_on_v3) and abstained passages are excluded',
                note='Partial-coverage schools (harvard, jhu, washu) were onboarded after the scores were built; their scored share is in coverage.')
    return dict(meta=meta, series=out_s, contrasts=out_c, corrected=corrected, coverage=coverage, error_table=et)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-07')
    ap.add_argument('--out')
    a = ap.parse_args()
    res, snap = C.results_dir(a.id), C.snapshot_dir(a.id)
    tables = {n: pd.read_csv(res / 'tables' / f'{n}.csv') for n in ('ai_series', 'ai_contrasts', 'ai_fp_corrected', 'ai_coverage')}
    man = json.loads((snap / 'MANIFEST.json').read_text())
    d = build(tables, snap, man['release_id'], a.id)
    out = C.Path(a.out) if a.out else res / 'site'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'ai_share.json').write_text(json.dumps(d, separators=(',', ':')))
    print(json.dumps({'written': str(out / 'ai_share.json'), 'scopes': sorted(d['series'])}))


if __name__ == '__main__':
    main()
