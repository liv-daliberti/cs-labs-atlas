"""Data for the two site pages (owner 2026-11-04, Part D): the page has a slider t (1%..100% of a paper's paragraphs flagged) and recomputes every number
in the browser from histograms. Small JSON files in ai-writing/diversity/site-data/ (README.md there has the schema).

  dose_site.py [--out DIR]     needs the container and `dose_validate.py --recalibrate` already run
ai_hist.json         per school ("all" counts each paper once) and year 2016-2026: 101-bin histograms of the dose (count, sum), abstract-only counts, bootstrap bands
ai_position.json     flagged-passage share by position decile, per paper-dose bin
labs_ai_hist_<school>.json[.gz]   per lab-year with >= 5 full-text papers: sparse 101-bin histogram (count, sum)
Binning rule (`dose_bin`): a paper with dose x (ai_share_cal where it exists, else ai_share) is in bin floor(100 x + 1e-9), bin 100 holding exactly 1.0, so bin b
is [b%, (b+1)%) and "paper is AI at cutoff t percent" (x >= t/100) is exactly "bin >= t". ai_share_cal is the share of passages flagged at the 1%-FPR threshold, recut
for any school or field whose 2016-2021 flagged share failed the check (the recut groups are listed in the file). Both counts and sums are of full-text papers only.
Abstract-only papers (no usable full text) are stored apart as (n, flagged by the v1 abstract rule): a page toggle, constant across t.
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np

import dcommon as D
import dose_stats as S

NB = 101
PARTIAL = 2026
MIN_LAB = 5
CI_T = (1, 5, 10, 25, 50, 75, 100)
YEARS = range(2016, 2027)


def dose_of(df):
    return df['ai_share_cal'].where(df['ai_share_cal'].notna(), df['ai_share'])


def dose_bin(x):
    """Bin index 0..100 of dose shares (array-like); NaN stays -1."""
    x = np.asarray(x, float)
    b = np.floor(100 * x + 1e-9)
    return np.where(np.isnan(x), -1, np.minimum(b, 100)).astype(int)


def hist(dose):
    """(counts[101], sums[101]) of the dose values."""
    d = np.asarray(dose, float)
    d = d[~np.isnan(d)]
    b = dose_bin(d)
    return np.bincount(b, minlength=NB), np.bincount(b, weights=d, minlength=NB)


def at_cutoff(counts, sums, t):
    """From a histogram: (n >= t, share >= t, mean dose among them, median dose among them) for cutoff t in percent (bin >= t)."""
    counts, sums = np.asarray(counts), np.asarray(sums)
    n_all = counts.sum()
    n = counts[t:].sum()
    if n == 0:
        return int(n), (0.0 if n_all else float('nan')), float('nan'), float('nan')
    cum = np.cumsum(counts[t:])
    mb = t + int(np.searchsorted(cum, (n + 1) / 2))
    return int(n), float(n / n_all), float(sums[t:].sum() / n), float(sums[mb] / counts[mb])


def explode(df):
    d = df.explode('schools').rename(columns={'schools': 'school'})
    return d[d['school'].isin(D.SCHOOLS)]


def cell_bands(g):
    """Cluster (first lab) bootstrap intervals of the share >= t among full-text papers at CI_T: {t: [lo, hi]}."""
    if len(g) < 20:
        return {}
    bins = dose_bin(dose_of(g))
    out = {}
    for t in CI_T:
        _, lo, hi = S.boot_ratio((bins >= t).astype(float), np.ones(len(g)), clusters=g['lab0'].fillna('none').to_numpy(), B=300, seed=t)
        out[str(t)] = [round(lo, 5), round(hi, 5)]
    return out


def histograms(df, bands=True):
    d = explode(df)
    out = {}
    for s in ['all'] + D.SCHOOLS:
        g_all = df if s == 'all' else d[d['school'] == s]
        years = {}
        for y in YEARS:
            g = g_all[g_all['year'] == y]
            if g.empty:
                continue
            ft = g[g['ai_share'].notna()]
            ab = g[g['ai_share'].isna() & g['p_ai_abstract'].notna()]
            c, sm = hist(dose_of(ft))
            cell = dict(partial=y == PARTIAL, n_ft=int(len(ft)), hist=c.tolist(), sum=[round(float(v), 4) for v in sm],
                        abstract_only=dict(n=int(len(ab)), flagged=int(ab['flag_abstract'].sum())), papers=int(len(g)))
            if y <= 2021:
                oos = ft[~ft['trained_on']] if 'trained_on' in ft else ft
                c2, s2 = hist(dose_of(oos))
                cell['hist_out_of_sample'] = c2.tolist()
                cell['sum_out_of_sample'] = [round(float(v), 4) for v in s2]
            if bands:
                cell['band'] = cell_bands(ft)
            years[str(y)] = cell
        out[s] = years
    return out


def position(df, passages, cuts):
    """Flagged passage share by position decile, per paper-dose bin: {school: {period: {flagged: [101][10], total: [101][10]}}} for 2016-2021 and 2023-2026 papers.
    A passage is flagged at its paper's own cut (the recalibrated one where a group needed it)."""
    p = passages.merge(df[['paper_id', 'year', 'schools', 'ai_share', 'ai_share_cal']], on='paper_id')
    p['dose'] = dose_of(p)
    p['bin'] = dose_bin(p['dose'])
    n = p.groupby('paper_id')['pidx'].transform('max') + 1
    p['pos'] = np.minimum((p['pidx'] / n * 10).astype(int), 9)
    p['flag'] = p['p'].to_numpy() >= p['paper_id'].map(cuts).to_numpy()
    out = {}
    for s in ['all'] + D.SCHOOLS:
        q = p if s == 'all' else p[p['schools'].map(lambda x, s=s: s in x)]
        res = {}
        for name, years in (('pre', range(2016, 2022)), ('post', range(2023, 2027))):
            z = q[q['year'].isin(years)]
            tot = np.zeros((NB, 10), int); fl = np.zeros((NB, 10), int)
            if len(z):
                np.add.at(tot, (z['bin'].to_numpy(), z['pos'].to_numpy()), 1)
                np.add.at(fl, (z['bin'].to_numpy(), z['pos'].to_numpy()), z['flag'].to_numpy().astype(int))
            res[name] = dict(flagged=fl.tolist(), total=tot.tolist())
        out[s] = res
    return out


def lab_hists(df, lp):
    d = lp[['paper_id', 'lab_id', 'school', 'lab_name', 'pi']].merge(df[['paper_id', 'year', 'ai_share', 'ai_share_cal']], on='paper_id')
    d['dose'] = dose_of(d)
    d = d.dropna(subset=['dose'])
    out = {s: [] for s in D.SCHOOLS}
    for (s, lab, name, pi, y), g in d.groupby(['school', 'lab_id', 'lab_name', 'pi', 'year']):
        if len(g) < MIN_LAB or s not in out:
            continue
        c, sm = hist(g['dose'])
        nz = np.nonzero(c)[0]
        out[s].append(dict(lab_id=lab, lab=name, pi=pi, year=int(y), n=int(len(g)), bins=nz.tolist(), counts=c[nz].tolist(), sums=[round(float(v), 4) for v in sm[nz]]))
    return out


def write_json(path, obj):
    raw = json.dumps(obj, separators=(',', ':'))
    if len(raw) > 1_500_000:
        with gzip.open(str(path) + '.gz', 'wt') as f:
            f.write(raw)
        Path(str(path)).unlink(missing_ok=True)
        return str(path) + '.gz'
    Path(path).write_text(raw)
    Path(str(path) + '.gz').unlink(missing_ok=True)
    return str(path)


def group_cuts():
    import sqlite3
    db = sqlite3.connect(f'file:{D.DB}?mode=ro', uri=True)
    rows = db.execute("select \"group\", value from thresholds where name = 'paragraph_v2_group'").fetchall()
    db.close()
    return {tuple(g.split(':', 1)): v for g, v in rows}


def run(out):
    import dose_data as DD
    import dose_validate as V
    df = DD.paper_table()
    df['field_grp'] = V.field_groups(df)
    first = DD.universe()[1].drop_duplicates('paper_id').set_index('paper_id')['lab_id']
    df['lab0'] = df['paper_id'].map(first)
    cuts_by_group = group_cuts()
    cuts = V.paper_cuts(df, cuts_by_group)
    ps = DD.passages(set(df.loc[df['ai_share'].notna(), 'paper_id']))
    out.mkdir(parents=True, exist_ok=True)
    meta = dict(generated=D.now(), bins=NB, bin_rule='bin = floor(100*dose + 1e-9), bin 100 = exactly 1.0; AI at cutoff t percent <=> bin >= t', partial_year=PARTIAL,
                global_threshold=D.V2_THRESHOLD, recalibrated_groups={f'{k[0]}:{k[1]}': v for k, v in cuts_by_group.items()}, ci_cutoffs=list(CI_T),
                ci_method='bootstrap over labs (300 draws, 95% percentile) of the share >= t among full-text papers; with abstract-only papers included use Wilson from counts',
                default_cutoff=25, ticks=[10, 25, 50])
    D.log(wrote=write_json(out / 'ai_hist.json', dict(meta=meta, series=histograms(df))))
    D.log(wrote=write_json(out / 'ai_position.json', dict(meta=meta, position_bins=10, series=position(df, ps, cuts))))
    for s, rows in lab_hists(df, DD.universe()[1]).items():
        D.log(wrote=write_json(out / f'labs_ai_hist_{s}.json', dict(meta=dict(generated=meta['generated'], min_papers=MIN_LAB, bin_rule=meta['bin_rule']), labs=rows)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(D.AIW / 'diversity' / 'site-data'))
    run(Path(ap.parse_args().out))
