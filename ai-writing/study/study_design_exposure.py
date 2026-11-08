"""Design 2: exposure differences. A continuous difference-in-differences on the PI panel, with event studies.

  study_design_exposure.py --id 2026-11-08   -> <results>/designs/tables/exposure_did.csv, exposure_event.csv, exposure_summary.csv

Model: y_it = a_i + g_{school(i),t} + b * E_i * post_t + e_it (PI fixed effects, school x year effects, clusters = PIs, CR1). E_i is a time-invariant PI exposure measured on the PI's
2016-2022 papers only and z-scored across PIs, so b is the post-2023 change in the outcome per one SD of exposure. The event study replaces post by one coefficient per year (2022 = 0);
the pre-trend test is a joint Wald test that the 2016-2021 coefficients are zero.
Exposures (see study_design_prep.py):
  (a) style distance   -(mean detector-v3 passage z over the PI's 2016-2022 main-body passages): how far the lab's pre-ChatGPT writing sits from the style the detector reads as LLM.
                       Second measure, detector-free: -(mean Kobak style-word rate of the pre-2023 abstracts). Expected sign: positive (farther labs move more).
  (b) language exposure  share of the PI team's authors with no affiliation institution in ANGLO (US GB CA AU NZ IE), from OpenAlex affiliations (an institution-country fact; names are never used
                       and nothing is inferred about any person's language). Reported as an association with that limitation.
Field control: school x year plus the PI's modal OpenAlex subfield x year effects (fe school_topic_year).
Cross-fit sensitivity: the exposure is computed on one random half of the pre papers and the outcome uses only the other half in the pre years (removes the mechanical link between a PI's
exposure noise and its pre outcome). Placebo: a fake break at 2020 with exposures measured on 2016-2019 papers, years 2016-2021. Sensitivity: partial schools excluded; year effects instead of
school x year effects; the wide English set; the unique-team share.
"""
import argparse

import numpy as np
import pandas as pd

import study_common as C
import study_fe as FE

OUTCOMES = [('heavy_main', 'Heavy-AI main body'), ('abs_flag', 'Abstract flag')]
EXPOSURES = {  # key -> (table column, sign, label)
    'style_distance': ('style_z', -1.0, 'Style distance from LLM (detector passage score)'),
    'kobak_distance': ('kobak_abs', -1.0, 'Style distance from LLM (Kobak abstract words)'),
    'lang_share': ('lang_share', 1.0, 'Non-English-country affiliation share (pooled)'),
    'lang_share_paper': ('lang_share_paper', 1.0, 'Non-English-country affiliation share (mean per paper)'),
    'lang_share_wide': ('lang_share_wide', 1.0, 'Non-English-country affiliation share (wide English set)'),
    'lang_share_team': ('lang_share_team', 1.0, 'Non-English-country share of distinct team members'),
}
MIN_PAPERS = {'style_z': 'n_style', 'kobak_abs': 'n_kobak', 'lang_share': 'n_lang', 'lang_share_paper': 'n_lang', 'lang_share_wide': 'n_lang', 'lang_share_team': 'n_lang'}


def design_matrix(d, E_cols, brk, fe, event):
    """Columns: exposure x post (or x year dummies, 2022 = 0), plus year (or school x year) dummies with one reference per school; names list."""
    yr = d['year'].to_numpy()
    cols, names = [], []
    for e in E_cols:
        ev = d[e].to_numpy(float)
        if event:
            for y in sorted(set(yr) - {2022}):
                cols.append(ev * (yr == y)); names.append(f'{e}:y{y}')
        else:
            cols.append(ev * (yr >= brk)); names.append(f'{e}:post')
    nE = len(cols)
    years = sorted(set(yr))
    ref = max(y for y in years if y < brk)         # the last pre year is the reference of the year effects
    if fe in ('school_year', 'school_topic_year'):
        for s in sorted(d['school'].unique()):
            m = (d['school'] == s).to_numpy()
            for y in years:
                if y != ref:
                    cols.append((m & (yr == y)).astype(float)); names.append(f'sy:{s}:{y}')
    else:
        for y in years:
            if y != ref:
                cols.append((yr == y).astype(float)); names.append(f'y:{y}')
    if fe == 'school_topic_year':        # PI's modal subfield x year effects as well: the exposure effect is then within subfield
        for s in sorted(d['pi_sub'].unique()):
            m = (d['pi_sub'] == s).to_numpy()
            for y in years:
                if y != ref:
                    cols.append((m & (yr == y)).astype(float)); names.append(f'ty:{s}:{y}')
    return np.column_stack(cols), names, nE


def did(d, y, E, brk=2023, fe='school_year', w=None):
    """Fit the interaction (post) and event-study models for one or several exposure columns of d (pi_key, school, year, y, E...)."""
    E_cols = [E] if isinstance(E, str) else list(E)
    d = d.dropna(subset=[y] + E_cols)
    codes = pd.factorize(d['pi_key'])[0]
    wt = None if w is None else d[w].to_numpy(float)
    yy = d[y].to_numpy(float)
    cl = d['pi_key'].to_numpy()
    X, names, nE = design_matrix(d, E_cols, brk, fe, event=False)
    r = FE.fit(yy, X, codes, cl, wt, None, names)
    rows = []
    for t in FE.table(r):
        if t['term'].endswith(':post'):
            rows.append(dict(t, exposure=t['term'].split(':')[0], n_obs=int(len(d)), n_pis=int(d['pi_key'].nunique())))
    Xe, enames, nEe = design_matrix(d, E_cols, brk, fe, event=True)
    re = FE.fit(yy, Xe, codes, cl, wt, None, enames)
    ev = []
    for t in FE.table(re):
        if ':y' in t['term'] and not t['term'].startswith(('sy:', 'y:', 'ty:')):
            e, yr = t['term'].split(':y')
            ev.append(dict(t, exposure=e, year=int(yr)))
    ev = pd.DataFrame(ev)
    pre_p, slopes = {}, {}
    for e in E_cols:
        idx = [i for i, nm in enumerate(enames) if nm.startswith(e + ':y') and int(nm.split(':y')[1]) < brk - 1]
        pre_p[e] = FE.wald(re['beta'], re['cov'], idx)[2] if len(idx) >= 2 else float('nan')
    # linear pre-trend: exposure x (year - last pre year) on the pre years only
    pre = d[d['year'] < brk]
    for e in E_cols:
        if pre['pi_key'].nunique() > 30:
            c = pd.factorize(pre['pi_key'])[0]
            Xp, pn, _ = design_matrix(pre, [e], brk, fe, event=False)
            slope = (pre['year'].to_numpy(float) - (brk - 1)) * pre[e].to_numpy(float)
            rp = FE.fit(pre[y].to_numpy(float), np.column_stack([slope, Xp[:, 1:]]), c, pre['pi_key'].to_numpy(), None if w is None else pre[w].to_numpy(float), None, ['slope'] + pn[1:])
            t = FE.table(rp)[0]
            slopes[e] = t
    for r_ in rows:
        r_['pretrend_p'] = pre_p.get(r_['exposure'])
        s = slopes.get(r_['exposure'])
        if s:
            r_.update(pretrend_slope=s['est'], pretrend_slope_lo=s['lo'], pretrend_slope_hi=s['hi'])
    first = E_cols[0]
    return dict(rows=rows, did=[r_ for r_ in rows if r_['exposure'] == first][0], event=ev[ev['exposure'] == first].rename(columns={'est': 'est'}) if len(ev) else ev,
                event_all=ev, pretrend_p=pre_p[first])


def zscore(s):
    sd = s.std()
    return (s - s.mean()) / (sd if sd > 0 else 1.0)


def run(snap_id):
    work = C.results_dir(snap_id) / 'designs' / 'work'
    dp = pd.read_parquet(work / 'design_papers.parquet')
    ex = pd.read_parquet(work / 'pi_exposure.parquet')
    rows, evs, summ = [], [], []

    def exposure_frame(window, split, key):
        col, sign, _ = EXPOSURES[key]
        e = ex[(ex['window'] == window) & (ex['split'] == split) & (ex[MIN_PAPERS[col]] >= 3)][['pi_key', col]].dropna()
        e['E'] = zscore(sign * e[col])
        return e[['pi_key', 'E']].rename(columns={'E': key})

    for okey, olabel in OUTCOMES:
        base = dp[dp[okey].notna()]
        for key in EXPOSURES:
            for cfg in ('main', 'crossfit', 'placebo2020'):
                window, split, brk, last = {'main': ('pre', 'all', 2023, C.LAST), 'crossfit': ('pre', 'half0', 2023, C.LAST), 'placebo2020': ('pre19', 'all', 2020, 2021)}[cfg]
                e = exposure_frame(window, split, key)
                d = base[base['year'] <= last].merge(e, on='pi_key', how='inner')
                if cfg == 'crossfit':
                    d = d[(d['year'] >= 2023) | (d['half'] == 1)]
                if cfg == 'placebo2020':
                    d = d[d['year'] >= 2016]
                for sample in ('all', 'excl_partial'):
                    dd = d if sample == 'all' else d[~d['school'].isin(C.PARTIAL)]
                    for fe in ('school_year', 'year', 'school_topic_year'):
                        if dd['pi_key'].nunique() < 50 or (fe != 'school_year' and cfg != 'main'):
                            continue
                        res = did(dd, okey, key, brk, fe)
                        for r in res['rows']:
                            r.update(outcome=okey, outcome_label=olabel, cfg=cfg, sample=sample, fe=fe, brk='fake2020' if brk == 2020 else 'real')
                            rows.append(r)
                        if cfg in ('main', 'crossfit', 'placebo2020') and sample == 'all' and fe == 'school_year':
                            ev = res['event_all'].assign(outcome=okey, cfg=cfg, sample=sample, fe=fe)
                            evs.append(ev)
        # joint model (horse race), main config, school x year
        for pair in (('style_distance', 'lang_share'), ('kobak_distance', 'lang_share')):
            e = exposure_frame('pre', 'all', pair[0]).merge(exposure_frame('pre', 'all', pair[1]), on='pi_key')
            d = base.merge(e, on='pi_key')
            res = did(d, okey, list(pair), 2023, 'school_year')
            for r in res['rows']:
                r.update(outcome=okey, outcome_label=olabel, cfg='joint:' + '+'.join(pair), sample='all', fe='school_year', brk='real')
                rows.append(r)
    for key in EXPOSURES:
        e = ex[(ex['window'] == 'pre') & (ex['split'] == 'all')]
        col = EXPOSURES[key][0]
        e = e[e[MIN_PAPERS[col]] >= 3]
        g = e.groupby('school')[col].agg(['count', 'mean', 'std']).reset_index().assign(exposure=key)
        summ.append(g)
    e = ex[(ex['window'] == 'pre') & (ex['split'] == 'all')].set_index('pi_key')
    corr = e[['style_z', 'kobak_abs', 'lang_share', 'lang_share_team']].corr(method='spearman')
    T = C.results_dir(snap_id) / 'designs' / 'tables'
    T.mkdir(parents=True, exist_ok=True)
    out = {'exposure_did': pd.DataFrame(rows), 'exposure_event': pd.concat(evs, ignore_index=True), 'exposure_summary': pd.concat(summ, ignore_index=True),
           'exposure_corr': corr.reset_index()}
    for nm, df in out.items():
        df.to_csv(T / f'{nm}.csv', index=False)
        df.to_parquet(T / f'{nm}.parquet')
        print(nm, df.shape, flush=True)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    run(ap.parse_args().id)
