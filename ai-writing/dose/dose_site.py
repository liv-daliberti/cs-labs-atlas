"""Data for the two site pages (owner 2026-11-04, Part D): small JSON files in ai-writing/diversity/site-data/ (README.md there has the schema).

  dose_site.py [--out DIR]     needs the container, dose_validate.py --recalibrate already run
how_much_ai.json       per year x school (and overall): papers, flagged AI / not, shares, baseline-adjusted share with a 95% interval
given_ai.json          among AI-flagged full-text papers: mean / median / deciles of ai_share, a histogram, the position profile of flagged passages
labs_ai_amount.json    per lab and year with >= 5 papers: mean ai_share (shrunk toward the school-year mean), n, flags
Definitions. A paper is "AI" when ai_share_cal >= 0.25 (full text; ai_share_cal is the share of passages flagged at the 1%-FPR threshold, recut for any school or
field whose 2016-2021 flagged share failed the check) and, when there is no full text, when its v1 abstract flag is set. Both series are also given on their own.
The baseline is the same definition's 2016-2021 rate in the same school (out-of-sample papers only); adjusted = observed - baseline, interval from the two binomial errors.
Sections are not recoverable (the stored body is one text from the Introduction to the References); the position profile bins passages by their relative position.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import dcommon as D

THRESH = 0.25
PARTIAL = 2026
MIN_LAB = 5


def ai_flags(df):
    """(primary flag, full-text flag, abstract flag) as float series with NaN where not available."""
    dose = df['ai_share_cal'].where(df['ai_share_cal'].notna(), df['ai_share'])
    ft = (dose >= THRESH).astype(float).where(dose.notna())
    ab = df['flag_abstract']
    return ft.where(ft.notna(), ab), ft, ab


def wilson_se(k, n):
    p = k / n if n else np.nan
    return np.sqrt(p * (1 - p) / n) if n else np.nan


def cell(flags):
    f = flags.dropna()
    n = len(f)
    return dict(n=int(n), flagged=int(f.sum()), not_flagged=int(n - f.sum()), share=float(f.mean()) if n else None)


def how_much(df, base_years=range(2016, 2022)):
    d = df.explode('schools').rename(columns={'schools': 'school'})
    d = d[d['school'].isin(D.SCHOOLS)]
    out = {}
    for name, col in (('primary', 0), ('fulltext', 1), ('abstract', 2)):
        d = d.assign(_f=ai_flags(d)[col])
        series = {}
        for s in ['all'] + D.SCHOOLS:
            g = df if s == 'all' else d[d['school'] == s]
            f = ai_flags(g)[col]
            base_mask = g['year'].isin(base_years) & (~g['trained_on'] if 'trained_on' in g else True)
            b = f[base_mask].dropna()
            bn, bp = len(b), (b.mean() if len(b) else np.nan)
            rows = []
            for y in range(2016, 2027):
                c = cell(f[g['year'] == y])
                if c['n']:
                    adj = c['share'] - bp
                    se = float(np.sqrt(wilson_se(c['flagged'], c['n']) ** 2 + (wilson_se(b.sum(), bn) ** 2 if bn else 0)))
                    c.update(year=y, partial=y == PARTIAL, baseline=float(bp) if bn else None, baseline_n=int(bn),
                             adjusted=float(adj), adj_lo=float(adj - 1.96 * se), adj_hi=float(adj + 1.96 * se))
                    rows.append(c)
            series[s] = rows
        out[name] = series
    return dict(definition=dict(primary='ai_share_cal >= 0.25 where full text exists, else the abstract flag', threshold=THRESH, partial_year=PARTIAL,
                                baseline_years=[2016, 2021]), series=out)


def given_ai(df, passages):
    d = df[df['ai_share'].notna()].copy()
    d['dose'] = d['ai_share_cal'].where(d['ai_share_cal'].notna(), d['ai_share'])
    d = d[d['dose'] >= THRESH].explode('schools').rename(columns={'schools': 'school'})
    d = d[d['school'].isin(D.SCHOOLS)]
    res = {}
    for s in ['all'] + D.SCHOOLS:
        g = d if s == 'all' else d[d['school'] == s]
        rows = []
        for y in range(2016, 2027):
            x = g[g['year'] == y]['dose']
            if len(x) >= 1:
                h, _ = np.histogram(x, bins=np.linspace(THRESH, 1.0, 16))
                rows.append(dict(year=y, n=int(len(x)), partial=y == PARTIAL, mean=float(x.mean()), median=float(x.median()),
                                 deciles=[float(v) for v in np.quantile(x, np.linspace(0.1, 0.9, 9))], hist_edges=[float(v) for v in np.linspace(THRESH, 1.0, 16)], hist=[int(v) for v in h]))
        res[s] = rows
    p = passages.merge(df[['paper_id', 'year']], on='paper_id')
    p = p[p['year'] >= 2023]
    n = p.groupby('paper_id')['pidx'].transform('max') + 1
    p['pos'] = np.minimum((p['pidx'] / n * 10).astype(int), 9)
    thr = D.V2_THRESHOLD
    prof = p.assign(f=p['p'] >= thr).groupby('pos')['f'].mean()
    return dict(threshold=THRESH, by_school_year=res, position_profile=dict(note='share of passages flagged by relative position in the body (decile 0 = start), papers of 2023-2026; '
                                                                                'sections (abstract, intro, ...) are not recoverable from the stored text', deciles=[float(v) for v in prof.reindex(range(10)).fillna(0)]))


def labs(df, lp):
    d = lp[['paper_id', 'lab_id', 'school', 'lab_name', 'pi']].merge(df[['paper_id', 'year', 'ai_share', 'ai_share_cal']], on='paper_id')
    d['dose'] = d['ai_share_cal'].where(d['ai_share_cal'].notna(), d['ai_share'])
    d = d.dropna(subset=['dose'])
    g = d.groupby(['school', 'lab_id', 'lab_name', 'pi', 'year'])['dose'].agg(n='size', mean='mean', median='median').reset_index()
    sy = d.groupby(['school', 'year'])['dose'].mean().rename('school_mean').reset_index()
    g = g.merge(sy, on=['school', 'year'])
    k = 5.0   # shrinkage: weight n / (n + k) on the lab mean, the rest on the school-year mean
    g['shrunk'] = (g['n'] * g['mean'] + k * g['school_mean']) / (g['n'] + k)
    g['small'] = g['n'] < MIN_LAB
    keep = g[~g['small']]
    return dict(min_papers=MIN_LAB, shrinkage_k=k, note='labs with < 5 scored papers in a year are omitted', rows=[
        dict(school=r.school, lab_id=r.lab_id, lab=r.lab_name, pi=r.pi, year=int(r.year), n=int(r.n), mean=float(r.mean), median=float(r.median), shrunk=float(r.shrunk))
        for r in keep.itertuples()])


def run(out):
    import dose_data as DD
    df = DD.paper_table()
    ps = DD.passages(set(df.loc[df['ai_share'].notna(), 'paper_id']))
    _, lp = DD.universe()
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in (('how_much_ai', how_much(df)), ('given_ai', given_ai(df, ps)), ('labs_ai_amount', labs(df, lp))):
        obj['generated'] = D.now()
        (out / f'{name}.json').write_text(json.dumps(obj, separators=(',', ':')))
        D.log(wrote=str(out / f'{name}.json'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(D.AIW / 'diversity' / 'site-data'))
    run(Path(ap.parse_args().out))
