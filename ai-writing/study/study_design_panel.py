"""Design 1: PI panel with author fixed effects. Within-PI change in each outcome after 2023 against before, with the long-running trend controlled.

  study_design_panel.py --id 2026-11-08   -> <results>/designs/tables/panel_fe.csv (+ parquet), panel_fe_event.csv

Outcomes (one row per paper x PI, or PI x year): heavy-AI main-body share (ai_share_main >= 0.25, detector v3, detector-training papers out), abstract flag (v1 detector), distance to the leave-PI-out
school-year centroid (SPECTER2 proximity), and within-lab mean pairwise distance (PI-year cells of >= 5 papers, weighted by papers).
Model: y_it = a_i + [trend] + b * post_t + e_it, a_i the PI's own fixed effect, clusters = PIs (CR1, t quantiles on G-1 df). Specs:
  S0 PI FE + post                         the naive within-PI change (long-running trend NOT controlled)
  S1 PI FE + common linear trend + a dummy per post year   one calendar slope for everyone; with a dummy for every post year the slope comes from the pre years only
  S2 PI FE + PI-specific linear trend + a dummy per post year   the headline: each PI's own pre-2023 slope is extrapolated; post_avg = mean of the three post-year departures from it
                                            (a single post dummy would let the post-period ramp bend the trend: tried first, it cut the heavy-AI effect to a third)
  S3 PI FE + year dummies (2022 = 0)      the event-time path, with the pre-trend visible; it cannot separate ChatGPT from a calendar trend by itself
Year effects are not identified together with `post` (every PI shares one break date), so identification of a ChatGPT effect rests on the functional form of the pre-trend (S1/S2); the
exposure designs (study_design_exposure.py) add cross-PI variation in exposure and then year effects ARE identified.
Samples: all 12 schools; excl_partial (no harvard/jhu/washu); balanced1 (PIs with an outcome in both pre 2016-22 and post 2023-25); balanced3 (>= 3 outcomes in each).
Placebo: a fake break at 2020 on years 2016-2021 (post = 2020-2021), same specs S0-S2; its balanced samples are defined on the fake periods.
"""
import argparse

import numpy as np
import pandas as pd

import study_common as C
import study_fe as FE

OUTCOMES = [  # name, source ('paper'|'pi_year'), column, label
    ('heavy_main', 'paper', 'heavy_main', 'Heavy-AI main body (share of papers)'),
    ('abs_flag', 'paper', 'abs_flag', 'Abstract flag'),
    ('within_lab_distance', 'pi_year', 'mpd', 'Within-lab embedding distance'),
    ('school_centroid_distance', 'paper', 'dist_centroid', 'Distance to school centroid'),
]
YEARS = list(range(C.FIRST, C.LAST + 1))


def load(snap_id):
    work = C.results_dir(snap_id) / 'designs' / 'work'
    dp = pd.read_parquet(work / 'design_papers.parquet')
    pm = pd.read_parquet(work / 'pi_year_mpd.parquet')
    return dp, pm


def samples(df, brk):
    """name -> boolean mask over df rows. Balanced samples depend on the (real or fake) break."""
    pre = df['year'] <= (brk - 1)
    post = df['year'] >= brk
    n_pre = df[pre].groupby('pi_key').size()
    n_post = df[post].groupby('pi_key').size()
    cnt = pd.concat([n_pre.rename('pre'), n_post.rename('post')], axis=1).fillna(0)
    b1 = set(cnt.index[(cnt.pre >= 1) & (cnt.post >= 1)])
    b3 = set(cnt.index[(cnt.pre >= 3) & (cnt.post >= 3)])
    part = df['school'].isin(C.PARTIAL)
    return {'all': pd.Series(True, index=df.index), 'excl_partial': ~part, 'balanced1': df['pi_key'].isin(b1), 'balanced3': df['pi_key'].isin(b3)}


def fit_specs(df, y, brk, w=None, events=True):
    """Fit S0-S3, S2e on df (pi_key, year, y [, w]); returns (rows, event rows)."""
    d = df[df['year'] <= (2025 if brk == 2023 else brk + 1)].copy()
    d = d[d[y].notna()]
    if d['pi_key'].nunique() < 30:
        return [], []
    codes = pd.factorize(d['pi_key'])[0]
    yr = d['year'].to_numpy(float)
    post = (d['year'] >= brk).to_numpy(float)
    wt = None if w is None else d[w].to_numpy(float)
    yy = d[y].to_numpy(float)
    cl = d['pi_key'].to_numpy()
    base = dict(n_obs=int(len(d)), n_pis=int(d['pi_key'].nunique()),
                pre_mean=float(np.average(yy[post == 0], weights=None if wt is None else wt[post == 0])),
                post_mean=float(np.average(yy[post == 1], weights=None if wt is None else wt[post == 1])))
    # PIs that can contribute: more than one observation (S0), and observations in both periods for post to vary within PI
    both = d.groupby('pi_key')['year'].agg(lambda s: (s < brk).any() and (s >= brk).any())
    base['n_pis_both_periods'] = int(both.sum())
    rows, ev = [], []

    def add(spec, r, terms):
        for t in FE.table(r):
            if t['term'] in terms:
                rows.append(dict(base, spec=spec, term=t['term'], est=t['est'], se=t['se'], lo=t['lo'], hi=t['hi']))
    c = (yr - (brk - 1))
    r = FE.fit(yy, post[:, None], codes, cl, wt, None, ['post']); add('S0_pi_fe', r, {'post'})
    # S1/S2: one dummy per post year, so the trend is estimated from the pre years only (a single post dummy would let the post-period ramp bend the trend)
    pys = sorted(set(d.loc[d['year'] >= brk, 'year'].astype(int)))
    Xp = np.column_stack([(d['year'] == x).to_numpy(float) for x in pys])
    avg = np.full(len(pys), 1.0 / len(pys))
    for spec, extra, t_ in (('S1_common_trend', c[:, None], None), ('S2_pi_trend', None, yr)):
        X = Xp if extra is None else np.column_stack([Xp, extra])
        names = [f'y{x}' for x in pys] + ([] if extra is None else ['trend'])
        r = FE.fit(yy, X, codes, cl, wt, t_, names)
        cvec = np.concatenate([avg, np.zeros(X.shape[1] - len(pys))])
        rows.append(dict(base, spec=spec, term='post_avg', **FE.lincom(r, cvec)))
        for t in FE.table(r):
            if t['term'] in names[:len(pys)]:
                ev.append(dict(base, spec=spec + '_event', **t))
    if brk == 2023 and events:
        ys = [x for x in YEARS if x != 2022]
        Xe = np.column_stack([(d['year'] == x).to_numpy(float) for x in ys])
        r = FE.fit(yy, Xe, codes, cl, wt, None, [f'y{x}' for x in ys])
        for t in FE.table(r):
            ev.append(dict(base, spec='S3_event', **t))
        pre_idx = [i for i, x in enumerate(ys) if x < 2022]
        st, df_, p = FE.wald(r['beta'], r['cov'], pre_idx)
        ev.append(dict(base, spec='S3_event', term='pretrend_wald', est=st, se=float(df_), lo=np.nan, hi=np.nan, p=p))
    return rows, ev


def run(snap_id):
    dp, pm = load(snap_id)
    out, evs = [], []
    for name, src, col, label in OUTCOMES:
        base = dp if src == 'paper' else pm
        base = base.assign(y=base[col].astype(float))
        w = None if src == 'paper' else 'n'
        for brk, tag in ((2023, 'real'), (2020, 'fake2020')):
            d = base[base['year'].between(C.FIRST, C.LAST if brk == 2023 else 2021)]
            dn = d.dropna(subset=['y'])
            for sname, mask in samples(dn, brk).items():
                dd = dn[mask]
                rows, ev = fit_specs(dd, 'y', brk, w)
                for r in rows + ev:
                    r.update(outcome=name, label=label, sample=sname, brk=tag)
                out += rows
                evs += ev
        # IPW sensitivity for the full-text outcome: papers weighted by the full-text selection weight
        if name == 'heavy_main':
            d = base[base['year'].between(C.FIRST, C.LAST) & base['w_ft'].notna()].dropna(subset=['y'])
            rows, ev = fit_specs(d, 'y', 2023, 'w_ft', events=False)
            for r in rows:
                r.update(outcome=name, label=label, sample='all_ipw', brk='real')
            out += rows
    tab = pd.DataFrame(out)
    evt = pd.DataFrame(evs)
    T = C.results_dir(snap_id) / 'designs' / 'tables'
    T.mkdir(parents=True, exist_ok=True)
    for nm, df in (('panel_fe', tab), ('panel_fe_event', evt)):
        df.to_csv(T / f'{nm}.csv', index=False)
        df.to_parquet(T / f'{nm}.parquet')
        print(nm, df.shape, flush=True)
    return tab, evt


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    run(ap.parse_args().id)
