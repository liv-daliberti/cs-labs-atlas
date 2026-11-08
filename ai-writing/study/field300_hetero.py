"""Field-300 heterogeneity across institutions (owner 2026-11-08): GRAS tier, country, region, English-speaking country (institution country), institution size.

  field300_hetero.py run [--models specter2_proximity,scincl]

From the institution x year sufficient statistics stored by field300_analyze.py (work/stats/*.npz) and the SAME bootstrap draws as the headline tables
(institutions resampled within GRAS tier), for every group g of every dimension:
  change(g) = period value post (2023-25) minus pre (2016-22) of the measure restricted to the institutions of g (ratio measures: ratio of sums; pair measures: pairs
              inside g), placebo(g) = 2019-21 minus 2016-18;
  contrast  = change(g) - change(complement of g)   (tier/region/country/size groups; English-speaking vs the rest is the one contrast of its dimension)
            + Q4 - Q1 of size (the trend contrast).
Intervals are percentile intervals of the draws; p = normal-approximation p from the bootstrap standard error (percentile p-values floor at 1/(B+1), too coarse for Holm); Holm and Benjamini-Hochberg over the PRIMARY family (primary outcomes x all contrasts). The number of
contrasts is written to tables/f300_hetero_family.json. Names and surnames are never used; English-speaking = OpenAlex institution country in {US, GB, CA, AU, NZ, IE}.
"""
import argparse
import json

import numpy as np
import pandas as pd

import field300_analyze as A
import field300_common as F
import field300_stats as FS
import study_labstats as LS

PRIMARY = ['abs_flag', 'llm_topic', 'emb_within_specter2_proximity_raw', 'emb_cross_specter2_proximity_raw', 'entropy_subfield', 'jsd_subfield']
MIN_COUNTRY_INST = 10


def dimensions(inst):
    """{dimension: {group: bool mask over the 300 institutions}} and the contrast list [(dimension, group, comparator)] (comparator None = the complement)."""
    dims = {}
    dims['tier'] = {t: (inst['tier'] == t).to_numpy() for t, _, _ in F.TIERS}
    dims['region'] = {r: (inst['region'] == r).to_numpy() for r in sorted(inst['region'].unique())}
    cc = inst['cc'].value_counts()
    dims['country'] = {c: (inst['cc'] == c).to_numpy() for c in cc.index[cc >= MIN_COUNTRY_INST]}
    dims['english'] = {'English-speaking country': inst['english'].to_numpy(), 'other countries': ~inst['english'].to_numpy()}
    dims['size'] = {q: (inst['size_q'] == q).to_numpy() for q in ['Q1 small', 'Q2', 'Q3', 'Q4 large']}
    cons = []
    for dname, gs in dims.items():
        for g in gs:
            if dname == 'english':
                if g == 'English-speaking country':
                    cons.append((dname, g, 'other countries'))
            else:
                cons.append((dname, g, None))
    cons.append(('size', 'Q4 large', 'Q1 small'))
    return dims, cons


def load_measures(models):
    sdir = F.work_dir() / 'stats'
    ms = {}
    for name in ['abs_flag', 'llm_topic', 'entropy_subfield', 'entropy_topic'] + [f'emb_within_{m}_raw' for m in models]:
        f = sdir / f'{name}.npz'
        if f.exists():
            z = np.load(f)
            ms[name] = ('ratio', z['S'], z['N'])
    for name in ['jsd_subfield', 'jsd_topic'] + [f'emb_cross_{m}_raw' for m in models]:
        f = sdir / f'{name}.npz'
        if f.exists():
            z = np.load(f)
            ms[name] = ('pair', z['D'], z['M'])
    return ms


_YEAR_CACHE = {}


def year_draws(a, b, W, mask, t):
    """Pair-measure draws of one year for the institutions in `mask`, cached (the four periods of effects() share years)."""
    key = (id(a), t, mask.tobytes())
    if key not in _YEAR_CACHE:
        _YEAR_CACHE[key] = FS.pair_draws(W, a[t], b[t], mask, mask) if b[t].sum() > 100 else np.full(W.shape[0], np.nan)
    return _YEAR_CACHE[key]


def period(kind, a, b, W, mask, years):
    """Draws (B+1,) of the measure on the institutions in `mask` for the mean/pooled value over `years`."""
    idx = [y - LS.YEARS[0] for y in years]
    if kind == 'ratio':
        with np.errstate(all='ignore'):
            return (W * mask) @ a[:, idx].sum(1) / ((W * mask) @ b[:, idx].sum(1))
    v = np.stack([year_draws(a, b, W, mask, t) for t in idx], 1)
    with np.errstate(all='ignore'):
        return np.nanmean(v, axis=1)


def effects(kind, a, b, W, mask):
    """(change draws, placebo draws) of a group: post minus pre and (2019-21) minus (2016-18)."""
    ch = period(kind, a, b, W, mask, LS.POST) - period(kind, a, b, W, mask, LS.PRE)
    pl = period(kind, a, b, W, mask, [2019, 2020, 2021]) - period(kind, a, b, W, mask, [2016, 2017, 2018])
    return ch, pl


def summ(x):
    lo, hi = LS.ci(x[1:])
    return float(x[0]), lo, hi


def cmd_run(a):
    inst = A.institutions()
    W = A.draws(inst)
    models = a.models.split(',')
    ms = load_measures(models)
    dims, cons = dimensions(inst)
    grows, crows = [], []
    for name, (kind, x, y) in ms.items():
        eff = {}
        for dname, gs in dims.items():
            for g, m in gs.items():
                if m.sum() < 5:
                    continue
                eff[(dname, g)] = (effects(kind, x, y, W, m), effects(kind, x, y, W, ~m))
                (ch, pl), _ = eff[(dname, g)]
                e, lo, hi = summ(ch)
                pe, plo, phi = summ(pl)
                grows.append(dict(measure=name, dimension=dname, group=g, n_inst=int(m.sum()), change=e, lo=lo, hi=hi, placebo=pe, placebo_lo=plo, placebo_hi=phi,
                                  pre=float(period(kind, x, y, W, m, LS.PRE)[0]), post=float(period(kind, x, y, W, m, LS.POST)[0])))
        for dname, g, comp in cons:
            if (dname, g) not in eff:
                continue
            (ch, pl), (chr_, plr) = eff[(dname, g)]
            if comp is not None:
                if (dname, comp) not in eff:
                    continue
                (chr_, plr), _ = eff[(dname, comp)]
            d, dp = ch - chr_, pl - plr
            e, lo, hi = summ(d)
            pe, plo, phi = summ(dp)
            crows.append(dict(measure=name, dimension=dname, group=g, versus=comp or 'complement', diff=e, lo=lo, hi=hi, p=FS.boot_p(d[1:], e), placebo_diff=pe,
                              placebo_lo=plo, placebo_hi=phi, primary=name in PRIMARY))
    g = pd.DataFrame(grows)
    c = pd.DataFrame(crows)
    fam = c['primary'] & c['p'].notna()
    c['holm'] = np.nan
    c['bh'] = np.nan
    c.loc[fam, 'holm'] = FS.holm(c.loc[fam, 'p'].to_numpy())
    c.loc[fam, 'bh'] = FS.bh(c.loc[fam, 'p'].to_numpy())
    c['holm_survives'] = c['holm'] < 0.05
    c['bh_survives'] = c['bh'] < 0.05
    tab, _ = A.out_dirs()
    g.to_csv(tab / 'f300_hetero_groups.csv', index=False)
    c.to_csv(tab / 'f300_hetero_contrasts.csv', index=False)
    fj = dict(primary_outcomes=[m for m in PRIMARY if m in ms], contrasts_per_outcome=len(cons), primary_family=int(fam.sum()), all_contrasts=len(c),
              holm_survivors=int(c['holm_survives'].sum()), bh_survivors=int(c['bh_survives'].sum()), groups_per_dimension={k: len(v) for k, v in dims.items()})
    (tab / 'f300_hetero_family.json').write_text(json.dumps(fj, indent=1))
    print(json.dumps(fj), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run'])
    ap.add_argument('--models', default='specter2_proximity')
    cmd_run(ap.parse_args())
