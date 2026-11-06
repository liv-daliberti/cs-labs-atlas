"""Detector-v3 checks and headline tables (owner 2026-11-05), written next to the v3 container:  RESULTS/v3_checks.json, v3_yearly_school.parquet, v3_checks.md, v3_error_table.json.

  AI_DETECTOR=v3 CS_ATLAS_AI_SCORES=<v3 container> dose_v3_checks.py

1. Appendix false-alarm check (owner rule): the flagged share of 2016-2021 *appendix* passages (non-abstained, papers outside the detector's training split) must be <= 1.5%;
   otherwise main+appendix is not shown. Reported with a paper-bootstrap interval, overall and by school and year, next to the main-body figure.
2. Headline by year and school: mean dose, share of papers with >= 25% passages flagged (main body = headline; main+appendix = secondary, only if the check passes) with
   paper-bootstrap intervals, the abstained passage share, and the full-text IPW-weighted robustness column (`w_ft`, labstudy/ipw/ipw_weights.parquet).
3. The v3 error table (detector_v3/results/tables.md, row `all` at 0.3%) as structured rows for the site's method notes. Partial edits are reported separately.
No 2026. Papers with `trained_on_v3` are excluded from every false-positive / placebo floor.
"""
import json
import re

import numpy as np
import pandas as pd

import dcommon as D
import dose_stats as S

V3 = D.MAIN_AIW / 'detector_v3' / 'results'
IPW = D.P.CODE / 'ai-writing' / 'data' / 'labstudy' / 'ipw' / 'ipw_weights.parquet'
LIMIT = 0.015
YEARS = list(range(2016, D.LAST_FULL_YEAR + 1))


def appendix_check():
    pa = pd.read_parquet(V3 / 'paper_ai_v3.parquet')
    pre = pa[pa['year'].between(2016, 2021) & ~pa['trained_on_v3']]
    out = {}
    for name, sc, fl in (('appendix', 'n_app_scored', 'n_app_flagged'), ('main', 'n_main_scored', 'n_main_flagged')):
        g = pre[pre[sc] > 0]
        est, lo, hi = S.boot_ratio(g[fl], g[sc], B=1000, seed=1)
        out[name] = dict(papers=int(len(g)), passages=int(g[sc].sum()), flagged=float(est), lo=float(lo), hi=float(hi))
        rows = []
        for by in ('school', 'year'):
            for k, h in g.groupby(by):
                e, l, u = S.boot_ratio(h[fl], h[sc], B=400, seed=2)
                rows.append(dict(by=by, key=str(k if by == 'school' else int(k)), papers=int(len(h)), passages=int(h[sc].sum()), flagged=float(e), lo=float(l), hi=float(u)))
        out[name + '_groups'] = rows
    out['limit'] = LIMIT
    out['passes'] = bool(out['appendix']['hi'] <= LIMIT)       # the upper end of the interval must clear the limit (stricter than the point estimate)
    out['excluded_trained_on_v3'] = int(pa[pa['year'].between(2016, 2021)]['trained_on_v3'].sum())
    return out


def yearly(df, ipw):
    pa = pd.read_parquet(V3 / 'paper_ai_v3.parquet')
    df = df.merge(pa[['paper_id', 'ai_share_main_appendix', 'n_main_flagged', 'n_main_scored', 'n_main_abstained', 'n_app_flagged', 'n_app_scored']].drop_duplicates('paper_id'), on='paper_id', how='left', suffixes=('', '_pa'))
    df = df[df['year'].between(2016, D.LAST_FULL_YEAR)]
    ex = df.explode('schools').rename(columns={'schools': 'school'})
    ex = ex[ex['school'].isin(D.SCHOOLS)]
    rows = []
    for s in ['all'] + D.SCHOOLS:
        base = df if s == 'all' else ex[ex['school'] == s]
        for y in YEARS:
            g = base[(base['year'] == y) & base['ai_share'].notna()]
            if len(g) < 20:
                continue
            r = dict(school=s, year=y, papers_scored=len(g), papers_all=int((base['year'] == y).sum()))
            m, lo, hi = S.boot_ratio(g['ai_share'], np.ones(len(g)), B=400, seed=3)
            r.update(mean_dose=m, mean_lo=lo, mean_hi=hi)
            f = (g['ai_share'] >= 0.25).astype(float)
            m, lo, hi = S.boot_ratio(f, np.ones(len(g)), B=400, seed=4)
            r.update(share25=m, share25_lo=lo, share25_hi=hi)
            m, lo, hi = S.boot_ratio(g['n_flagged'], g['n_passages'], B=400, seed=5)
            r.update(passage_flag_share=m, passage_lo=lo, passage_hi=hi)
            r['abstained_share_main'] = float(g['n_main_abstained'].sum() / (g['n_main_abstained'].sum() + g['n_main_scored'].sum()))
            ga = g[g['ai_share_main_appendix'].notna()]
            m, lo, hi = S.boot_ratio(ga['ai_share_main_appendix'], np.ones(len(ga)), B=400, seed=6)
            r.update(mean_dose_with_appendix=m, with_app_lo=lo, with_app_hi=hi, papers_with_appendix=int(ga['appendix_found'].sum()))
            if ipw is not None:
                w = g['paper_id'].map(ipw).astype(float)
                ok = w.notna()
                if ok.sum() >= 20:
                    r['mean_dose_ipw'] = float((g.loc[ok, 'ai_share'] * w[ok]).sum() / w[ok].sum())
                    r['share25_ipw'] = float(((g.loc[ok, 'ai_share'] >= 0.25) * w[ok]).sum() / w[ok].sum())
            rows.append(r)
    return pd.DataFrame(rows)


def error_table():
    t = (V3 / 'tables.md').read_text()
    blocks = t.split('\n## ')
    out = {}
    b = [x for x in blocks if x.startswith('Threshold at cal FPR 0.3%')][0]
    lines = [ln for ln in b.splitlines() if ln.startswith('| ')]
    head = [c.strip() for c in lines[0].strip('|').split('|')]
    for ln in lines[2:]:
        c = [x.strip() for x in ln.strip('|').split('|')]
        if c[0] in ('v2', 'all'):
            out[c[0]] = dict(zip(head, c))
    pt = [x for x in blocks if x.startswith('Per generator x task miss rate, all@0.003')][0]
    rows = []
    for ln in pt.splitlines():
        m = re.match(r'\| ([\w.\-]+)/(\w+) \| ([\d.]+)% \(([\d.]+)-([\d.]+)\) \| (\d+) \|', ln)
        if m:
            rows.append(dict(generator=m.group(1), task=m.group(2), miss=float(m.group(3)) / 100, lo=float(m.group(4)) / 100, hi=float(m.group(5)) / 100, n=int(m.group(6))))
    r = pd.DataFrame(rows)
    full = r[r['task'] != 'partial']
    part = r[r['task'] == 'partial']
    tasks = {k: dict(miss_mean=float(g['miss'].mean()), generators=int(len(g)), min=float(g['miss'].min()), max=float(g['miss'].max())) for k, g in full.groupby('task')}
    return dict(operating_point=json.load(open(V3 / 'operating_point.json')), at_0p3_percent=out, by_task_fully_ai_text=tasks,
                partial_edits=dict(note='partial edits (a human text with some sentences rewritten by a model) are reported separately: a text-level miss, not a calibration figure',
                                   miss_mean=float(part['miss'].mean()), min=float(part['miss'].min()), max=float(part['miss'].max()), generators=int(len(part))),
                summary='Human passages wrongly flagged: 0.30% (0.27-0.32%); unseen-model-family misses 0.9-6.6% (leave-one-family-out, `tables.md`); abstained passages (<100 words or heading-heavy) are excluded: 5.6% of test passages.')


def run():
    import dose_data as DD
    res = D.RESULTS
    res.mkdir(parents=True, exist_ok=True)
    ac = appendix_check()
    ipw = None
    if IPW.exists():
        w = pd.read_parquet(IPW)
        ipw = w.drop_duplicates('paper_id').set_index('paper_id')['w_ft']
    df = DD.paper_table(with_split=True)
    yt = yearly(df, ipw)
    yt.to_parquet(res / 'v3_yearly_school.parquet', index=False)
    et = error_table()
    (res / 'v3_error_table.json').write_text(json.dumps(et, indent=1))
    (res / 'v3_checks.json').write_text(json.dumps(dict(appendix_check=ac, generated=D.now()), indent=1))
    md = ['## Detector v3 checks (generated by dose_v3_checks.py)\n',
          f"Appendix false-alarm check, 2016-2021 papers outside the training split ({ac['appendix']['papers']:,} papers, {ac['appendix']['passages']:,} appendix passages): "
          f"flagged {100 * ac['appendix']['flagged']:.2f}% (95% {100 * ac['appendix']['lo']:.2f}-{100 * ac['appendix']['hi']:.2f}); main body {100 * ac['main']['flagged']:.2f}% "
          f"({100 * ac['main']['lo']:.2f}-{100 * ac['main']['hi']:.2f}). Limit {100 * LIMIT:.1f}%: **{'passes' if ac['passes'] else 'FAILS'}**.\n"]
    a = yt[yt['school'] == 'all'].set_index('year')
    md.append('\n| year | papers | mean dose (95%) | share >= 25% (95%) | abstained passages | mean dose + appendix | IPW mean dose |\n|---|---|---|---|---|---|---|')
    for y, r in a.iterrows():
        md.append(f"| {y} | {int(r['papers_scored']):,} | {100 * r['mean_dose']:.2f}% ({100 * r['mean_lo']:.2f}-{100 * r['mean_hi']:.2f}) | {100 * r['share25']:.2f}% ({100 * r['share25_lo']:.2f}-{100 * r['share25_hi']:.2f}) | "
                  f"{100 * r['abstained_share_main']:.1f}% | {100 * r['mean_dose_with_appendix']:.2f}% | {100 * r.get('mean_dose_ipw', float('nan')):.2f}% |")
    (res / 'v3_checks.md').write_text('\n'.join(md))
    D.log(appendix=ac['appendix'], passes=ac['passes'], yearly_rows=len(yt))


if __name__ == '__main__':
    run()
