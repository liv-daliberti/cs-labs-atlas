"""Analysis 2: before/after by lab (staggered-adoption event study) of AI wording against lab-level novelty, dispersion and topic outcomes.

  event_study.py adoption         lab-year doses and each lab's adoption year under the pre-registered specs   -> OUT/event/{dose,adoption}.parquet
  event_study.py control          lab-year geometry on the original and all-AI rewritten abstracts (wording control)  -> OUT/event/control_geometry.parquet
  event_study.py outcomes         lab-year outcome panel (long)                                                -> OUT/event/outcomes.parquet
  event_study.py estimate [--headline-only] [-j N]   Callaway-Sant'Anna event studies, pre-trend tests, permutation placebo, TWFE comparison -> OUT/event/results.parquet
  event_study.py all              the four steps in order
Adoption rule, thresholds, outcomes and estimator are fixed in preregistration.json (read here, never edited by a run). Lab bootstrap B (default 300).
"""
import argparse
import json
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import frame as FR
import lcommon as L

PRE = json.loads((L.HERE / 'preregistration.json').read_text())
YEARS = L.YEARS
TY = {y: i for i, y in enumerate(YEARS)}
MIN_SCORED = PRE['adoption']['min_scored_per_lab_year']
EV_LEADS = [-5, -4, -3, -2]
EV_POST = [0, 1, 2]
BOOT = 300


# ------------------------------------------------------------------ doses and adoption
def lab_year_dose(df, lp):
    w = L.load_weights('w_ft')
    d = lp[['paper_id', 'lab_id', 'year']].merge(df[['paper_id', 'ai_share', 'flag_abstract', 'has_abstract']], on='paper_id', how='left')
    d['w'] = d['paper_id'].map(w) if w is not None else np.nan
    sc = d[d['ai_share'].notna()].copy()
    sc['ge25'] = (sc['ai_share'] >= 0.25).astype(float)
    sc['ge10'] = (sc['ai_share'] >= 0.10).astype(float)
    g = sc.groupby(['lab_id', 'year'])
    t = g.agg(n_scored=('ai_share', 'size'), share_ge25=('ge25', 'mean'), share_ge10=('ge10', 'mean'), mean_share=('ai_share', 'mean')).reset_index()
    sw = sc[sc['w'].notna()].copy()
    sw['wx'] = sw['w'] * sw['ge25']
    gw = sw.groupby(['lab_id', 'year']).agg(sw=('w', 'sum'), swx=('wx', 'sum')).reset_index()
    gw['share_ge25_ipw'] = gw['swx'] / gw['sw']
    t = t.merge(gw[['lab_id', 'year', 'share_ge25_ipw']], on=['lab_id', 'year'], how='left')
    ab = d[d['flag_abstract'].notna()].groupby(['lab_id', 'year']).agg(n_abs=('flag_abstract', 'size'), abs_flag=('flag_abstract', 'mean')).reset_index()
    t = t.merge(ab, on=['lab_id', 'year'], how='outer')
    npap = d.groupby(['lab_id', 'year']).size().rename('n_papers').reset_index()
    return t.merge(npap, on=['lab_id', 'year'], how='right')


def adoption_spec(dose, spec, cfg):
    metric, k, sus = cfg['metric'], cfg['k'], cfg['sustain_years']
    nmin_col = 'n_abs' if metric == 'abs_flag' else 'n_scored'
    d = dose.copy()
    valid = d[nmin_col].fillna(0) >= MIN_SCORED
    d['m'] = np.where(valid, d[metric], np.nan)
    fl = PRE['adoption']['floor_window']
    base = d[d['year'].between(*fl)]['m'].dropna()
    floor, sd = float(base.mean()), float(base.std())
    thr = floor + k * sd
    d['exceed'] = d['m'] > thr
    wide = d.pivot(index='lab_id', columns='year', values='exceed')
    mv = d.pivot(index='lab_id', columns='year', values='m')
    last = YEARS[-1]
    rows = []
    for lab in wide.index:
        ex = {y: (bool(wide.loc[lab, y]) if pd.notna(wide.loc[lab, y]) else None) for y in YEARS if y in wide.columns}
        g = None
        for y in YEARS:
            if y + sus - 1 > last:
                break
            if all(ex.get(y + j) is True for j in range(sus)):
                g = y
                break
        if g is not None:
            st = 'adopter'
        elif sus > 1 and ex.get(last) is True:
            st = 'censored'
        elif any(v is not None for v in ex.values()):
            st = 'never_unsustained' if any(v for v in ex.values()) else 'never'
        else:
            st = 'insufficient'
        rows.append(dict(lab_id=lab, spec=spec, adopt_year=g, status=st))
    out = pd.DataFrame(rows)
    out.attrs.update(floor=floor, sd=sd, thr=thr)
    return out, dict(spec=spec, metric=metric, k=k, sustain=sus, floor=floor, sd=sd, threshold=thr)


def build_adoption():
    df, lp, labs = FR.load()
    dose = lab_year_dose(df, lp)
    L.write_atomic(dose, L.out('event', 'dose.parquet'))
    outs, info = [], []
    for spec, cfg in PRE['adoption']['specs'].items():
        o, i = adoption_spec(dose, spec, cfg)
        outs.append(o)
        i.update(o['status'].value_counts().to_dict())
        i['cohorts'] = json.dumps(o[o['status'] == 'adopter']['adopt_year'].value_counts().sort_index().to_dict())
        info.append(i)
        L.log(step='adoption', **i)
    L.write_atomic(pd.concat(outs, ignore_index=True), L.out('event', 'adoption.parquet'))
    L.write_atomic(pd.DataFrame(info), L.out('event', 'adoption_info.parquet'))


# ------------------------------------------------------------------ outcomes
def control_geometry(models=('specter2_proximity', 'qwen3_0p6b', 'bge_m3'), m=5, reps=100):
    import allai_analyze as AA
    import dose_lab as DL
    import novelty as N
    _, lp, _ = FR.load()
    rows = []
    for model in models:
        papers, _, Xo, Xa, _, _ = AA.load_pair(model, 'polish')
        mu = Xo.mean(0)
        Zo, _ = N.center_normalize(Xo, mu)
        Za, _ = N.center_normalize(Xa, mu)
        pid = list(papers['paper_id'])
        lps = lp[lp['paper_id'].isin(set(pid))][['paper_id', 'lab_id', 'year']]
        for name, Z in (('orig', Zo), ('ai', Za)):
            p = DL.lab_year_panel(Z, pid, lps, None, m, reps, seed=0)
            for meas in ('disp', 'mpd', 'vendi'):
                rows.append(p[['lab_id', 'year', meas]].rename(columns={meas: 'value'}).assign(outcome=f'{meas}|{model}', source='ctl_' + name))
        L.log(step='control_geometry', model=model, papers=len(pid))
    L.write_atomic(pd.concat(rows, ignore_index=True), L.out('event', 'control_geometry.parquet'))


def build_outcomes():
    df, lp, labs = FR.load()
    rows = []
    res = L.Path(L.P.AI_SCORES) / 'results'
    for model in L.MODELS_ABS:
        p = res / f'labyear_{model}_abstract.parquet'
        if not p.exists():
            continue
        t = pd.read_parquet(p)
        for meas in ('disp', 'mpd', 'vendi', 'h_oa', 'h_bt'):
            if meas in t and t[meas].notna().any():
                nm = f'{meas}|{model}' if meas not in ('h_oa',) else 'h_oa'
                if meas == 'h_oa' and model != 'specter2_proximity':
                    continue
                rows.append(t[['lab_id', 'year', meas]].rename(columns={meas: 'value'}).assign(outcome=nm, source='main'))
    import pyarrow.dataset as pds
    for model in L.MODELS_ABS:
        p = L.EMB / 'results' / f'novelty_{model}_abstract.parquet'
        if not p.exists():
            continue
        t = pds.dataset(p).to_table(columns=['paper_id', 'k', 'n_ref', 'nov_nn_cap'], filter=(pds.field('scope') == 'all') & pds.field('k').isin([1, 3, 5])).to_pandas()
        t = t[t['n_ref'] >= 100].merge(lp[['paper_id', 'lab_id', 'year']], on='paper_id')
        g = t.groupby(['lab_id', 'year', 'k'])['nov_nn_cap'].agg(['mean', 'size']).reset_index()
        g = g[g['size'] >= 3]
        for k, d in g.groupby('k'):
            rows.append(d[['lab_id', 'year', 'mean']].rename(columns={'mean': 'value'}).assign(outcome=f'nov{k}|{model}', source='main'))
    td = L.out('topics')
    for level in ('bt_qwen3_0p6b', 'oa_topic'):
        for cand in (td / 'labyear.parquet', td / f'labyear_{level}.parquet'):
            if cand.exists():
                ly = pd.read_parquet(cand)
                ly = ly[(ly['level'] == level) & (ly['variant'] == 'main')]
                if len(ly):
                    for meas in ('dist_centroid', 'dist_pre_centroid', 'mass_llm', 'entropy'):
                        if meas == 'mass_llm' and level == 'oa_topic':
                            continue
                        rows.append(ly[['lab_id', 'year', meas]].rename(columns={meas: 'value'}).assign(outcome=f'{meas}|{level}', source='main'))
                    break
    cg = L.out('event', 'control_geometry.parquet')
    if cg.exists():
        rows.append(pd.read_parquet(cg))
    for cand in sorted(td.glob('labyear*control*.parquet')):
        ly = pd.read_parquet(cand)
        ly = ly[ly['variant'] == 'control']
        for (level, name), d in ly.groupby(['level', 'name']):
            for meas in ('dist_centroid', 'mass_llm'):
                rows.append(d[['lab_id', 'year', meas]].rename(columns={meas: 'value'}).assign(outcome=f'{meas}|{level}', source='ctl_' + name))
    o = pd.concat(rows, ignore_index=True).dropna(subset=['value'])
    o = o[o['year'].between(YEARS[0], YEARS[-1])]
    # paired gap (ai - orig) for the wording control
    a = o[o['source'] == 'ctl_ai'].set_index(['lab_id', 'year', 'outcome'])['value']
    b = o[o['source'] == 'ctl_orig'].set_index(['lab_id', 'year', 'outcome'])['value']
    gap = (a - b).dropna().rename('value').reset_index().assign(source='ctl_gap')
    o = pd.concat([o, gap], ignore_index=True)
    L.write_atomic(o, L.out('event', 'outcomes.parquet'))
    L.log(step='outcomes', rows=len(o), outcomes=int(o['outcome'].nunique()), sources=o['source'].value_counts().to_dict())


# ------------------------------------------------------------------ Callaway-Sant'Anna
def cs_cells(Y, G, controls='never'):
    """Group-time ATTs. Y (N, T) with NaN, G (N,) adoption year (0 = control). Returns list of (g, t, att, n_treated_cell)."""
    out = []
    for g in np.unique(G[G > 0]):
        if g - 1 not in TY:
            continue
        b = TY[g - 1]
        tr = G == g
        for t in YEARS:
            if t == g - 1:
                continue
            j = TY[t]
            d = Y[:, j] - Y[:, b]
            ok = np.isfinite(d)
            ctl = (G == 0) if controls == 'never' else ((G == 0) | (G > max(t, g)))
            a, c = d[tr & ok], d[ctl & ok]
            if len(a) < 1 or len(c) < 2:
                continue
            out.append((int(g), int(t), float(a.mean() - c.mean()), len(a)))
    return out


def aggregate(cells):
    """theta(e) dict e -> (est, n), the overall post ATT and the e=0..2 average."""
    by = {}
    for g, t, att, n in cells:
        by.setdefault(t - g, []).append((att, n))
    theta = {e: (sum(a * n for a, n in v) / sum(n for _, n in v), sum(n for _, n in v)) for e, v in by.items()}
    post = [(att, n) for g, t, att, n in cells if t >= g]
    overall = sum(a * n for a, n in post) / sum(n for _, n in post) if post else np.nan
    d02 = [(att, n) for g, t, att, n in cells if 0 <= t - g <= 2]
    dyn = sum(a * n for a, n in d02) / sum(n for _, n in d02) if d02 else np.nan
    return theta, overall, dyn


def stat_vector(Y, G, controls):
    cells = cs_cells(Y, G, controls)
    theta, overall, dyn = aggregate(cells)
    es = EV_LEADS + [-1] + EV_POST
    vec = {e: (theta[e][0] if e in theta else (0.0 if e == -1 else np.nan)) for e in es}
    lead_es = [e for e in EV_LEADS + [-1] if np.isfinite(vec[e])]
    slope = np.nan
    if len(lead_es) >= 3:
        x = np.array(lead_es, float)
        yv = np.array([vec[e] for e in lead_es])
        slope = float(((x - x.mean()) * (yv - yv.mean())).sum() / ((x - x.mean()) ** 2).sum())
    return vec, overall, dyn, slope, {e: theta[e][1] for e in theta}


def wald(est, boots):
    """Joint test that the leads are zero: est (k,), boots (B, k); bootstrap covariance, pseudo-inverse."""
    ok = np.isfinite(est) & np.isfinite(boots).all(0)
    if ok.sum() < 1:
        return np.nan, np.nan, 0
    e, bt = est[ok], boots[:, ok]
    V = np.atleast_2d(np.cov(bt.T))
    w, U = np.linalg.eigh(V)
    keep = w > 1e-10 * w.max()
    z = U[:, keep].T @ e
    stat = float((z ** 2 / w[keep]).sum())
    from scipy import stats
    return stat, float(1 - stats.chi2.cdf(stat, keep.sum())), int(keep.sum())


def run_one(args):
    """One (outcome, source, spec, sample): CS event study with lab bootstrap, pre-trend tests, permutation placebo (headline only), TWFE comparison (headline only)."""
    outcome, source, spec, sample, Y, G, labs_ids, headline, B, nperm = args
    N = len(G)
    rng = np.random.default_rng(L.SEED + zlib.crc32(f'{outcome}|{source}|{spec}|{sample}'.encode()) % 1000003)
    controls = 'nyt' if sample == 'nyt' else 'never'
    vec, overall, dyn, slope, ncell = stat_vector(Y, G, controls)
    es = EV_LEADS + [-1] + EV_POST
    bt = {e: [] for e in es}
    bo, bd, bs = [], [], []
    for _ in range(B):
        ix = rng.integers(0, N, N)
        v, o, d, s, _ = stat_vector(Y[ix], G[ix], controls)
        for e in es:
            bt[e].append(v[e])
        bo.append(o); bd.append(d); bs.append(s)
    rows = []
    base = dict(outcome=outcome, source=source, spec=spec, sample=sample, n_labs=N, n_treated=int((G > 0).sum()), n_control=int((G == 0).sum()))

    def ci(est, arr):
        a = np.asarray(arr, float)
        a = a[np.isfinite(a)]
        if len(a) < 30 or not np.isfinite(est):
            return est, np.nan, np.nan
        return est, float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))
    for e in es:
        est, lo, hi = ci(vec[e], bt[e])
        rows.append(dict(base, kind='event', e=e, est=est, lo=lo, hi=hi, n_cell=ncell.get(e, 0)))
    for k, est, arr in (('overall_att', overall, bo), ('dyn_att_0_2', dyn, bd), ('pretrend_slope', slope, bs)):
        e_, lo, hi = ci(est, arr)
        rows.append(dict(base, kind='stat', stat=k, est=e_, lo=lo, hi=hi))
    lead_est = np.array([vec[e] for e in EV_LEADS])
    lead_b = np.array([bt[e] for e in EV_LEADS]).T
    st, p, df_ = wald(lead_est, lead_b)
    rows.append(dict(base, kind='stat', stat='pretrend_wald', est=st, lo=p, hi=df_))          # lo carries the p-value, hi the degrees of freedom
    if headline and nperm:
        elig = np.arange(N)
        obs = overall
        null = []
        for _ in range(nperm):
            Gp = G.copy()
            Gp[elig] = rng.permutation(G[elig])
            null.append(stat_vector(Y, Gp, controls)[1])
        null = np.array(null)
        null = null[np.isfinite(null)]
        if len(null) > 20 and np.isfinite(obs):
            rows.append(dict(base, kind='perm', stat='perm_p_two_sided', est=float((np.abs(null) >= abs(obs)).mean()), lo=float(np.percentile(null, 2.5)), hi=float(np.percentile(null, 97.5))))
    if headline:
        rows += twfe_rows(base, Y, G, labs_ids)
    return rows


def twfe_rows(base, Y, G, labs_ids):
    import dose_reg as R
    N, T = Y.shape
    d = pd.DataFrame({'lab_id': np.repeat(labs_ids, T), 'year': np.tile(YEARS, N), 'y': Y.ravel(), 'g': np.repeat(G, T)})
    d = d.dropna(subset=['y'])
    d['e'] = np.where(d['g'] > 0, d['year'] - d['g'], np.nan)
    cols = []
    for e in EV_LEADS + EV_POST:
        d[f'e{e}'] = (d['e'] == e).astype(float)
        cols.append(f'e{e}')
    d['far'] = (d['e'] < min(EV_LEADS)).astype(float)
    d['late'] = (d['e'] > max(EV_POST)).astype(float)
    d['post'] = (d['e'] >= 0).astype(float)
    cols += ['far', 'late']
    rows = []
    r = R.fit(d, 'y', cols, fe=['lab_id', 'year'], cluster='lab_id')
    for e in EV_LEADS + EV_POST:
        b, s = r['coefs'].get(f'e{e}', np.nan), r['ses'].get(f'e{e}', np.nan)
        rows.append(dict(base, kind='twfe_event', e=e, est=b, lo=b - 1.96 * s, hi=b + 1.96 * s))
    r2 = R.fit(d, 'y', 'post', fe=['lab_id', 'year'], cluster='lab_id')
    rows.append(dict(base, kind='twfe_static', stat='post', est=r2['beta'], lo=r2['lo'], hi=r2['hi']))
    return rows


# ------------------------------------------------------------------ estimate
HEADLINE = ['mpd|specter2_proximity', 'disp|specter2_proximity', 'vendi|specter2_proximity', 'nov3|specter2_proximity', 'h_oa', 'dist_centroid|bt_qwen3_0p6b']


def wide_of(o, labs_all):
    w = o.pivot_table(index='lab_id', columns='year', values='value', aggfunc='mean').reindex(index=labs_all, columns=YEARS)
    return w.to_numpy(float)


def estimate(headline_only=False, jobs=12, boot=BOOT, nperm=200):
    ad = pd.read_parquet(L.out('event', 'adoption.parquet'))
    o = pd.read_parquet(L.out('event', 'outcomes.parquet'))
    labs_all = np.array(sorted(set(o['lab_id']) | set(ad['lab_id'])))
    tasks = []
    outcomes = sorted(o['outcome'].unique())
    if headline_only:
        outcomes = [x for x in outcomes if x in HEADLINE]
    for spec in ad['spec'].unique():
        a = ad[ad['spec'] == spec].set_index('lab_id')
        for outcome in outcomes:
            if spec != 'S1_primary' and outcome not in HEADLINE:
                continue
            for source in sorted(o[o['outcome'] == outcome]['source'].unique()):
                samples = ['primary']
                if spec == 'S1_primary' and outcome in HEADLINE and source == 'main':
                    samples += ['nyt', 'post2022', 'strict_never']
                for sample in samples:
                    st = a['status'].reindex(labs_all)
                    gy = a['adopt_year'].reindex(labs_all)
                    keep = st.isin(['adopter', 'never', 'never_unsustained'])
                    if sample == 'strict_never':
                        keep = st.isin(['adopter', 'never'])
                    elif sample == 'post2022':
                        keep = keep & ~((st == 'adopter') & (gy < L.CFG['post_start']))
                    elif sample == 'nyt':
                        keep = st.isin(['adopter', 'never', 'never_unsustained'])
                    sel = np.where(keep.to_numpy())[0]
                    oo = o[(o['outcome'] == outcome) & (o['source'] == source)]
                    Yw = wide_of(oo, labs_all)[sel]
                    G = np.where(st.iloc[sel] == 'adopter', gy.iloc[sel].fillna(0), 0).astype(int)
                    if (G > 0).sum() < 5 or (G == 0).sum() < 10:
                        continue
                    tasks.append((outcome, source, spec, sample, Yw, G, labs_all[sel], outcome in HEADLINE and source == 'main' and spec == 'S1_primary', boot, nperm))
    L.log(step='event_tasks', n=len(tasks))
    rows = []
    with ProcessPoolExecutor(jobs) as ex:
        for r in ex.map(run_one, tasks, chunksize=1):
            rows += r
    res = pd.DataFrame(rows)
    L.write_atomic(res, L.out('event', 'results.parquet' if not headline_only else 'results_headline.parquet'))
    L.log(step='event_done', rows=len(res), tasks=len(tasks))


def diagnostics():
    """Endogeneity of adoption timing: adopters vs never-adopters and early vs late on pre-period features; Spearman of adoption year against the pre-2023 LLM-text share."""
    from scipy import stats
    df, lp, labs = FR.load()
    ad = pd.read_parquet(L.out('event', 'adoption.parquet'))
    a = ad[(ad['spec'] == 'S1_primary') & ad['status'].isin(['adopter', 'never', 'never_unsustained'])].merge(labs, on='lab_id', how='left')
    d = lp[['paper_id', 'lab_id', 'year']].merge(df[['paper_id', 'llm_text', 'has_abstract']], on='paper_id')
    pre = d[d['year'] <= 2022]
    feat = pre.groupby('lab_id').agg(n_pre=('paper_id', 'size'))
    feat['llm_share_2021_22'] = d[d['year'].between(2021, 2022) & d['has_abstract']].groupby('lab_id')['llm_text'].mean()
    feat['llm_share_2016_19'] = d[d['year'].between(2016, 2019) & d['has_abstract']].groupby('lab_id')['llm_text'].mean()
    feat['llm_share_change'] = feat['llm_share_2021_22'] - feat['llm_share_2016_19']
    a = a.merge(feat, left_on='lab_id', right_index=True, how='left')
    a['adopter'] = (a['status'] == 'adopter').astype(int)
    rows = []
    for c in ('n_pre', 'llm_share_2021_22', 'llm_share_change'):
        x, y = a[a['adopter'] == 1][c].dropna(), a[a['adopter'] == 0][c].dropna()
        sd = np.sqrt((x.var() + y.var()) / 2)
        rows.append(dict(feature=c, adopters=float(x.mean()), controls=float(y.mean()), smd=float((x.mean() - y.mean()) / sd) if sd > 0 else np.nan, n_adopt=len(x), n_ctl=len(y)))
    t = a[(a['adopter'] == 1) & (a['adopt_year'] >= 2023)].dropna(subset=['llm_share_2021_22'])
    rho, p = stats.spearmanr(t['adopt_year'], t['llm_share_2021_22']) if len(t) > 10 else (np.nan, np.nan)
    rows.append(dict(feature='spearman(adoption year, llm_share_2021_22) among 2023+ adopters', adopters=float(rho), controls=np.nan, smd=np.nan, n_adopt=len(t), n_ctl=float(p)))
    sh = a.groupby('dept_type').agg(labs=('lab_id', 'size'), adopt_share=('adopter', 'mean')).reset_index()
    sc = a.groupby('school').agg(labs=('lab_id', 'size'), adopt_share=('adopter', 'mean')).reset_index()
    L.write_atomic(pd.DataFrame(rows), L.out('event', 'diag_features.parquet'))
    L.write_atomic(sh, L.out('event', 'diag_dept.parquet'))
    L.write_atomic(sc, L.out('event', 'diag_school.parquet'))
    L.log(step='event_diag', rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['adoption', 'control', 'outcomes', 'estimate', 'diagnostics', 'all', 'report'])
    ap.add_argument('--headline-only', action='store_true')
    ap.add_argument('--boot', type=int, default=BOOT)
    ap.add_argument('--perm', type=int, default=200)
    ap.add_argument('-j', type=int, default=12)
    a = ap.parse_args()
    if a.cmd in ('adoption', 'all'):
        build_adoption()
    if a.cmd in ('control', 'all'):
        control_geometry()
    if a.cmd in ('outcomes', 'all'):
        build_outcomes()
    if a.cmd in ('estimate', 'all'):
        estimate(a.headline_only, a.j, a.boot, a.perm)
    if a.cmd in ('diagnostics', 'all'):
        diagnostics()
    if a.cmd == 'report':
        import event_report
        event_report.main()


if __name__ == '__main__':
    main()
