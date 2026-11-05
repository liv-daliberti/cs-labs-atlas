"""Analysis 3, part 2: the full-text dose and diversity results again with the IPW weights, next to the unweighted and the abstract-based (all-papers) ones.

  ipw_rerun.py rates                       yearly share of papers with ai_share >= 0.25 and mean ai_share, unweighted and weighted (lab bootstrap)       -> OUT/ipw/rates.parquet
  ipw_rerun.py paper [-j N] [--boot B]     paper-level dose -> novelty (scope all, k = 3, nov_nn_cap): pooled and within-lab designs, post and the pre-period placebo -> OUT/ipw/paper_rerun.parquet
  ipw_rerun.py lab   [-j N] [--boot B]     lab-level DiD / placebo breaks with the dose from unweighted, IPW-weighted and abstract-flag exposure                -> OUT/ipw/lab_rerun.parquet
  ipw_rerun.py all
Samples: `ft` = papers with scored full text (the dose is only defined there) unweighted and IPW-weighted; `abs_all` = every paper with an abstract and its abstract flag
(no full-text selection). Novelty is read from the full-text embeddings (where they exist) or the abstract embeddings of the same papers. The paper-level designs are
those of dose_analysis.py (pooled: year + school + OpenAlex topic FE with team size, venue type and OA status controls; withinlab: lab x year FE), the same
cluster bootstrap over labs; the weights are held fixed in the bootstrap (weight-estimation error not propagated).
"""
import argparse
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import frame as FR
import lcommon as L

CONTROLS = ['team_log', 'venue_type', 'oa_status']
FT_MODELS = ['specter2_base', 'specter2_proximity', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']
_DF = None


def analysis_frame():
    df, lp, _ = FR.load()
    first = lp.drop_duplicates('paper_id').set_index('paper_id')['lab_id']
    df = df.copy()
    df['lab0'] = df['paper_id'].map(first)
    df['school'] = df['home_school']
    df['team_log'] = np.log(df['n_authors'].fillna(df['n_authors'].median()).clip(lower=1))
    df['venue_type'] = df['source_type'].fillna('unknown').astype(str)
    df['oa_status'] = df['oa_status'].fillna('unknown').astype(str)
    df['topic'] = df['oa_topic'].fillna('none')
    w = L.load_weights('w_ft')
    df['w'] = df['paper_id'].map(w) if w is not None else np.nan
    return df


# ------------------------------------------------------------------ yearly rates
def rates(boot=200):
    df = analysis_frame()
    d = df[df['ai_share'].notna() & df['w'].notna() & df['lab0'].notna()].copy()
    d['ge25'] = (d['ai_share'] >= 0.25).astype(float)
    labs, inv = np.unique(d['lab0'], return_inverse=True)
    rng = np.random.default_rng(L.SEED)
    rows = []
    groups = {'all': np.ones(len(d), bool)}
    for s in sorted(d['school'].unique()):
        groups['school:' + s] = (d['school'] == s).to_numpy()
    for gname, gm in groups.items():
        for y in L.YEARS:
            m = gm & (d['year'] == y).to_numpy()
            if m.sum() < 30:
                continue
            x, w, lab = d['ge25'].to_numpy()[m], d['w'].to_numpy()[m], inv[m]
            a, wa = d['ai_share'].to_numpy()[m], w
            est = dict(share_ge25_unw=x.mean(), share_ge25_ipw=(w * x).sum() / w.sum(), mean_unw=a.mean(), mean_ipw=(wa * a).sum() / wa.sum())
            bs = {k: [] for k in est}
            # cluster bootstrap over labs: multiplicity per lab
            ul = np.unique(lab)
            pos = {l: i for i, l in enumerate(ul)}
            li = np.array([pos[l] for l in lab])
            for _ in range(boot):
                mult = rng.multinomial(len(ul), np.full(len(ul), 1 / len(ul)))[li].astype(float)
                if mult.sum() == 0:
                    continue
                bs['share_ge25_unw'].append((mult * x).sum() / mult.sum())
                bs['share_ge25_ipw'].append((mult * w * x).sum() / (mult * w).sum())
                bs['mean_unw'].append((mult * a).sum() / mult.sum())
                bs['mean_ipw'].append((mult * wa * a).sum() / (mult * wa).sum())
            for k, v in est.items():
                rows.append(dict(group=gname, year=y, measure=k, est=float(v), lo=float(np.percentile(bs[k], 2.5)), hi=float(np.percentile(bs[k], 97.5)), n=int(m.sum())))
    L.write_atomic(pd.DataFrame(rows), L.out('ipw', 'rates.parquet'))
    # whole-population comparator: abstract flag share (all papers with an abstract), by year
    a = df[df['flag_abstract'].notna()].groupby('year')['flag_abstract'].agg(['mean', 'size']).reset_index()
    L.write_atomic(a, L.out('ipw', 'abstract_flag_rate.parquet'))
    L.log(step='ipw_rates', rows=len(rows))


# ------------------------------------------------------------------ paper level
def paper_task(args):
    import dose_analysis as A
    import dose_reg as R
    model, nov_kind, expo, sample, weighting, B = args
    df = _DF
    nov = A.novelty_rows(model, nov_kind, 'all', ks=(3,))
    if nov is None:
        return []
    nov = nov[nov['k'] == 3]
    base = df.merge(nov[['paper_id', 'n_ref', 'nov_nn_cap']], on='paper_id')
    base['cl'] = base['lab0'].astype(str)
    base['lab_year'] = base['lab0'].astype(str) + '|' + base['year'].astype(str)
    base = base[base[expo].notna() & base['nov_nn_cap'].notna() & base['lab0'].notna()]
    if sample == 'ft':
        base = base[base['ai_share'].notna()]
        if weighting == 'ipw':
            base = base[base['w'].notna()]
    w = 'w' if weighting == 'ipw' else None
    rows = []
    for period, years in (('post', L.POST), ('pre', list(range(2017, 2022)))):
        d = base[base['year'].isin(years)]
        if len(d) < 300:
            continue
        for design, fe, nested in (('pooled', ['year', 'school', 'topic'], []), ('withinlab', ['lab_year'], ['lab_year'])):
            est, lo, hi = R.boot_fit(d, 'nov_nn_cap', expo, 'cl', controls=CONTROLS if design == 'pooled' else CONTROLS, fe=fe, nested=nested, weights=w, B=B, seed=3)
            rows.append(dict(model=model, nov_kind=nov_kind, exposure=expo, sample=sample, weighting=weighting, period=period, design=design, beta=est, lo=lo, hi=hi, n=len(d),
                             y_sd=float(d['nov_nn_cap'].std())))
    L.log(step='ipw_paper', model=model, nov_kind=nov_kind, expo=expo, sample=sample, weighting=weighting, rows=len(rows))
    return rows


def paper(jobs, boot):
    global _DF
    _DF = analysis_frame()
    tasks = []
    for m in L.MODELS_ABS:
        kinds = ['abstract'] + (['fulltext'] if m in FT_MODELS else [])
        for kind in kinds:
            for w in ('unw', 'ipw'):
                tasks.append((m, kind, 'ai_share', 'ft', w, boot))
        tasks.append((m, 'abstract', 'flag_abstract', 'abs_all', 'unw', boot))
        tasks.append((m, 'abstract', 'flag_abstract', 'ft', 'unw', boot))      # abstract flag on the full-text sample (separates sample from exposure)
        tasks.append((m, 'abstract', 'flag_abstract', 'ft', 'ipw', boot))
    with ProcessPoolExecutor(jobs) as ex:
        res = [r for rr in ex.map(paper_task, tasks) for r in rr]
    L.write_atomic(pd.DataFrame(res), L.out('ipw', 'paper_rerun.parquet'))
    L.log(step='ipw_paper_done', rows=len(res))


# ------------------------------------------------------------------ lab level
def lab_task(args):
    import dose_lab as DL
    model, B = args
    p = L.Path(L.P.AI_SCORES) / 'results' / f'labyear_{model}_abstract.parquet'
    if not p.exists():
        return []
    panel = pd.read_parquet(p)
    dose = _DOSE
    panel = panel.drop(columns=[c for c in ('dose_ipw',) if c in panel]).merge(dose[['lab_id', 'dose_ipw', 'dose_unw']], on='lab_id', how='left')
    rows = []
    for y in ('disp', 'mpd', 'vendi', 'h_oa', 'nov_all'):
        if y not in panel:
            continue
        for dname, col in (('unweighted', 'dose_unw'), ('ipw', 'dose_ipw'), ('abstract_flag', 'abs_dose')):
            t = DL.did_table(panel, y, dose=col, boot=B)
            rows.append(t.assign(model=model, dose_kind=dname))
    L.log(step='ipw_lab', model=model)
    return rows


def lab(jobs, boot):
    global _DOSE
    df = analysis_frame()
    _, lp, _ = FR.load()
    d = lp[['paper_id', 'lab_id', 'year']].merge(df[['paper_id', 'ai_share', 'w']], on='paper_id')
    d = d[d['year'].isin(L.POST) & d['ai_share'].notna()]
    g = d.groupby('lab_id')
    t = pd.DataFrame({'dose_unw': g['ai_share'].mean(), 'n_scored': g.size()})
    dw = d[d['w'].notna()].assign(wa=lambda x: x['w'] * x['ai_share']).groupby('lab_id').agg(sw=('w', 'sum'), swa=('wa', 'sum'))
    t['dose_ipw'] = dw['swa'] / dw['sw']
    t.loc[t['n_scored'] < 4, ['dose_unw', 'dose_ipw']] = np.nan
    _DOSE = t.reset_index()
    with ProcessPoolExecutor(jobs) as ex:
        res = [x for rr in ex.map(lab_task, [(m, boot) for m in L.MODELS_ABS]) for x in rr]
    L.write_atomic(pd.concat(res, ignore_index=True), L.out('ipw', 'lab_rerun.parquet'))
    L.log(step='ipw_lab_done', rows=sum(len(r) for r in res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['rates', 'paper', 'lab', 'all'])
    ap.add_argument('--boot', type=int, default=100)
    ap.add_argument('-j', type=int, default=12)
    a = ap.parse_args()
    if a.cmd in ('rates', 'all'):
        rates()
    if a.cmd in ('paper', 'all'):
        paper(a.j, a.boot)
    if a.cmd in ('lab', 'all'):
        lab(a.j, a.boot)


if __name__ == '__main__':
    main()
