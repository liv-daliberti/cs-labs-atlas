"""Experiment A analyses: coverage, trends by school, pre/post-2023 within labs (with placebo breaks), and the relation to a paper's AI dose.

  cn_analysis.py coverage | trends | lab | paper | all        -> DATA/results/*.parquet  (cn_report.py renders them)
Re-uses the dose study's frame (dose_analysis.build_frame: scores, topic, team size, venue type, open access, first lab), designs (dose_analysis.designs) and lab DiD
(dose_lab.did_table), so the controls are the dose report's: year/school/OpenAlex-topic FE, log team size, venue type, open-access status, topic x year FE, lab x year FE,
LLM-topic exclusion, plus log(number of references) here (the measures depend on reference-list length). Every estimate is per unit of exposure (ai_share 0 -> 1) with a
95% interval clustered by lab (cluster bootstrap over labs for the headline rows). 2026 is in no table: LAST_YEAR = 2025.
Outcome direction: z_p10, z_med higher = more conventional (lower = more atypical, novel); cd higher = more consolidating (lower = more disruptive); rs_sub, h_venue higher =
more diverse references; jac, cos higher = more reference overlap inside the lab (more homogeneous).
"""
import argparse

import numpy as np
import pandas as pd

import cn_common as C
import dcommon as D
import dose_analysis as A
import dose_lab as L
import dose_reg as R

MEASURES = ['z_p10', 'z_med', 'cd1', 'cd_av', 'rs_sub', 'rs_field', 'h_venue', 'h_sub']
HEAD = ['z_p10', 'z_med', 'cd1', 'cd_av', 'rs_sub', 'h_venue']
LAB_Y = ['z_p10', 'z_med', 'cd1', 'cd_av', 'rs_sub', 'h_venue', 'jac', 'cos', 'jac_prev', 'cos_prev']
CONTROLS = A.CONTROLS + ['log_refs']
MIN_CITES_FULL = 3


def frame():
    df = A.build_frame()
    m = pd.read_parquet(C.RESULTS / 'paper_measures.parquet').drop(columns=['oa_id', 'home_school'])
    df = df.merge(m, on='paper_id', how='left', suffixes=('', '_m'))
    df = df[df['year'].between(C.FIRST_YEAR, C.LAST_YEAR)].copy()
    df['log_refs'] = np.log1p(df['n_refs_m'].fillna(0)) if 'n_refs_m' in df else np.log1p(df['n_refs'].fillna(0))
    return df


def cmd_coverage(df):
    rows = []
    for (s, y), g in list(df.groupby(['school', 'year'])) + [(('all', y), g) for y, g in df.groupby('year')]:
        n = len(g)
        nr = 'n_refs_m' if 'n_refs_m' in g else 'n_refs'
        rows.append(dict(school=s, year=int(y), papers=n, refs5=float((g[nr] >= 5).mean()), meta=float((g['n_refs_meta'] >= 5).mean()), z=float(g['z_p10'].notna().mean()),
                         cd1=float(g['cd1'].notna().mean()), cd3=float(g['cd3'].notna().mean()), cd5=float(g['cd5'].notna().mean()), rs=float(g['rs_sub'].notna().mean()),
                         mean_refs=float(g.loc[g[nr] >= 1, nr].mean())))
    pd.DataFrame(rows).to_parquet(C.RESULTS / 'coverage.parquet', index=False)


def mean_ci(x):
    x = x.dropna()
    if len(x) < 5:
        return np.nan, np.nan, np.nan, len(x)
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    return float(m), float(m - 1.96 * se), float(m + 1.96 * se), len(x)


def cmd_trends(df):
    rows = []
    for key, g in [((s, y), gg) for (s, y), gg in df.groupby(['school', 'year'])] + [(('all', y), gg) for y, gg in df.groupby('year')]:
        for m in MEASURES + ['cd2', 'cd3', 'cd5', 'ref_age_med']:
            mean, lo, hi, n = mean_ci(g[m])
            rows.append(dict(school=key[0], year=int(key[1]), measure=m, mean=mean, lo=lo, hi=hi, n=n))
    pd.DataFrame(rows).to_parquet(C.RESULTS / 'trends.parquet', index=False)


def lab_panel(df):
    _, lp = C.universe_papers()
    lp = lp[lp['year'].between(C.FIRST_YEAR, C.LAST_YEAR)]
    cols = ['paper_id', 'ai_share', 'flag_abstract', *[m for m in LAB_Y if m in df]]
    pl = lp[['paper_id', 'lab_id', 'year']].merge(df[cols], on='paper_id', how='left')
    g = pl.groupby(['lab_id', 'year'])
    out = g.agg(n_papers=('paper_id', 'size'), ai_share_lt=('ai_share', 'mean'), n_scored=('ai_share', 'count')).reset_index()
    for m in (m for m in LAB_Y if m in df):
        t = g[m].agg(['mean', 'count']).reset_index().rename(columns={'mean': m, 'count': f'n_{m}'})
        t.loc[t[f'n_{m}'] < 2, m] = np.nan   # a lab-year mean of one paper is not a lab measure
        out = out.merge(t[['lab_id', 'year', m]], on=['lab_id', 'year'], how='left')
    out.loc[out['n_scored'] < 2, 'ai_share_lt'] = np.nan
    ov = pd.read_parquet(C.RESULTS / 'lab_overlap.parquet')[['lab_id', 'year', 'jac', 'cos', 'jac_prev', 'cos_prev', 'n_prev']]
    out = out.drop(columns=[c for c in ('jac', 'cos', 'jac_prev', 'cos_prev') if c in out]).merge(ov, on=['lab_id', 'year'], how='left')
    pl2 = lp[['paper_id', 'lab_id', 'year']].merge(df[['paper_id', 'ai_share', 'flag_abstract']], on='paper_id', how='left')
    return out.merge(L.lab_exposure(pl2), on='lab_id', how='left')


def cmd_lab(df, boot):
    panel = lab_panel(df)
    panel.to_parquet(C.RESULTS / 'labyear_panel.parquet', index=False)
    outs = []
    for y in LAB_Y:
        if y not in panel or panel[y].notna().sum() < 100:
            continue
        for dose in ('dose', 'abs_dose'):
            t = L.did_table(panel, y, dose, boot=boot)
            outs.append(t)
        outs.append(pd.DataFrame([L.within_lab_year(panel, y, boot=boot)]))
        # lab-level change without any dose: mean of (post minus pre) over labs, as the plain pre/post contrast of the outcome
    pd.concat(outs, ignore_index=True).to_parquet(C.RESULTS / 'did_citation.parquet', index=False)
    C.log(step='lab', rows=sum(len(o) for o in outs), lab_years=len(panel))


def prepost_labs(panel):
    """Within-lab change: lab FE + year FE + Post_t on lab-years, no dose (2022 dropped): the average post-2023 shift of each outcome within labs, and the placebo breaks."""
    rows = []
    for y in LAB_Y:
        if y not in panel:
            continue
        d = panel.dropna(subset=[y])
        d = d[(d['year'] <= 2021) | d['year'].isin(C.POST_YEARS)].copy()
        d['post'] = d['year'].isin(C.POST_YEARS).astype(float)
        est, lo, hi = R.boot_fit(d, y, 'post', 'lab_id', fe=['lab_id'], nested=['lab_id'], B=100, seed=1)
        rows.append(dict(outcome=y, spec='post2023_vs_2016_21', beta=est, lo=lo, hi=hi, n=len(d), labs=d['lab_id'].nunique(), sd=float(d[y].std())))
        pre = panel.dropna(subset=[y]); pre = pre[pre['year'] <= 2021].copy()
        for b in L.BREAKS:
            pre['post'] = (pre['year'] >= b).astype(float)
            est, lo, hi = R.boot_fit(pre, y, 'post', 'lab_id', fe=['lab_id'], nested=['lab_id'], B=100, seed=1)
            rows.append(dict(outcome=y, spec=f'placebo{b}', beta=est, lo=lo, hi=hi, n=len(pre), labs=pre['lab_id'].nunique(), sd=float(pre[y].std())))
    return pd.DataFrame(rows)


def paper_rows(d, y, expo, period, extra):
    d = d.copy()
    d['lab_year'] = d['lab0'].astype(str) + '|' + d['year'].astype(str)
    rows = []
    kw = dict(cluster='lab0')

    def row(sub, design, **k):
        out, _ = A.fit_row(sub, y, expo, design, dict(measure=y, exposure=expo, period=period, **extra), **k, **kw)
        rows.append(out)
    row(d, 'raw', fe=['year'])
    row(d, 'pooled', controls=CONTROLS, fe=['year', 'school', 'topic'])
    row(d, 'topicyear', controls=CONTROLS, fe=['topic_year', 'school'])
    row(d[~d['llm_topic']], 'nollm', controls=CONTROLS, fe=['year', 'school', 'topic'])
    row(d, 'withinlab', controls=CONTROLS, fe=['lab_year'])
    row(d[d['n_refs'] >= 15] if 'n_refs' in d else d, 'refs15', controls=CONTROLS, fe=['year', 'school', 'topic'])
    return rows


def cmd_paper(df, boot):
    rows = []
    periods = {'post': range(2023, C.LAST_YEAR + 1), 'pre': range(2017, 2022)}
    for period, years in periods.items():
        for expo in ('ai_share', 'flag_abstract'):
            d0 = df[df['year'].isin(years) & df[expo].notna()]
            if period == 'pre':
                d0 = d0[~d0['trained_on'].fillna(False).astype(bool)]   # detector-v2 training negatives are not out-of-sample
            for y in HEAD:
                d = d0[d0[y].notna()]
                if len(d) < 300:
                    continue
                rows += paper_rows(d, y, expo, period, {})
    out = pd.DataFrame(rows)
    # headline cluster bootstrap over labs: pooled and within-lab, ai_share
    hb = []
    for period, years in periods.items():
        d0 = df[df['year'].isin(years) & df['ai_share'].notna()].copy()
        if period == 'pre':
            d0 = d0[~d0['trained_on'].fillna(False).astype(bool)]
        d0['lab_year'] = d0['lab0'].astype(str) + '|' + d0['year'].astype(str)
        for y in HEAD:
            d = d0[d0[y].notna()]
            for design, fe, nested in (('pooled', ['year', 'school', 'topic'], []), ('withinlab', ['lab_year'], ['lab_year'])):
                est, lo, hi = R.boot_fit(d, y, 'ai_share', 'lab0', controls=CONTROLS, fe=fe, nested=nested, B=boot, seed=3)
                hb.append(dict(measure=y, exposure='ai_share', period=period, design=design, beta=est, lo=lo, hi=hi, n=len(d), y_sd=float(d[y].std()),
                               method='cluster bootstrap over labs'))
    out.to_parquet(C.RESULTS / 'paper_dose.parquet', index=False)
    pd.DataFrame(hb).to_parquet(C.RESULTS / 'paper_dose_boot.parquet', index=False)
    C.log(step='paper', fits=len(out), boot=len(hb))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['coverage', 'trends', 'lab', 'paper', 'all'])
    ap.add_argument('--boot', type=int, default=200)
    a = ap.parse_args()
    C.RESULTS.mkdir(parents=True, exist_ok=True)
    F = frame()
    D.log(step='frame', rows=len(F))
    if a.cmd in ('coverage', 'all'):
        cmd_coverage(F)
    if a.cmd in ('trends', 'all'):
        cmd_trends(F)
    if a.cmd in ('lab', 'all'):
        cmd_lab(F, a.boot)
        prepost_labs(pd.read_parquet(C.RESULTS / 'labyear_panel.parquet')).to_parquet(C.RESULTS / 'prepost_labs.parquet', index=False)
    if a.cmd in ('paper', 'all'):
        cmd_paper(F, a.boot)
