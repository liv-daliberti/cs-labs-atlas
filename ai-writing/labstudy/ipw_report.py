"""Writes ai-writing/diversity/reports/FULLTEXT-SELECTION-IPW.md from OUT/ipw/*.parquet and the weights table."""
import json

import numpy as np
import pandas as pd

import frame as FR
import lcommon as L
import lreport as R


def sig(lo, hi):
    return 'excl0' if (lo > 0 or hi < 0) else 'incl0'


def main():
    d = L.out('ipw')
    meta = json.loads((d / 'ipw_meta.json').read_text())
    ft = meta['tables']['ft']
    ab = meta['tables']['abs']
    w = pd.read_parquet(L.IPW_TABLE)
    df, lp, labs = FR.load()
    bal = pd.read_parquet(d / 'balance.parquet')
    rates = pd.read_parquet(d / 'rates.parquet')
    out = []
    A = out.append
    A('# Full-text selection: inverse-probability weights and what they change\n')
    A(f'Generated {R.now()} by `ai-writing/labstudy/ipw_report.py` (`ipw.py fit`, `ipw_rerun.py`); tables in `ai-writing/data/labstudy/ipw` (git-ignored). Years 2016-2025, no 2026. Intervals: bootstrap over labs (a paper\'s first lab), 100 replicates for the regression re-runs, 200 for the yearly rates.\n')
    A('## Answer\n')
    r25 = rates[(rates.group == 'all') & (rates.year == 2025)].set_index('measure')
    r24 = rates[(rates.group == 'all') & (rates.year == 2024)].set_index('measure')
    bb = bal[(bal.tag == 'ft') & (bal.model == ft['model'])].set_index('covariate')
    def mean_of(c):
        return (bb.loc[c, 'mean_all'], bb.loc[c, 'mean_sel']) if c in bb.index else (np.nan, np.nan)
    cl, ar, ie = mean_of('oa_status_closed'), mean_of('doi_prefix_10.48550'), mean_of('doi_prefix_10.1109')
    above_after = int((bb.smd_after.abs() > L.CFG['ipw']['smd_target']).sum())
    A(f'- **Who has a full text.** {ft["n_selected"]:,} of {ft["n"]:,} lab papers (2016-2025, Georgia Tech excluded: no full text at all) have a scored full text ({100 * ft["selected_share"]:.1f}%). '
      f'Selection is strong on open access (closed-access papers {100 * cl[1]:.0f}% of the full-text set against {100 * cl[0]:.0f}% of all papers), on publisher (arXiv DOI prefix {100 * ar[1]:.0f}% against {100 * ar[0]:.0f}%; IEEE {100 * ie[1]:.0f}% against {100 * ie[0]:.0f}%), school and year. '
      f'The cross-fitted model separates the two sets well (AUC {ft["logit_auc"]:.2f} logistic, {ft["gbm_auc"]:.2f} boosting).')
    A(f'- **Balance.** The largest standardised mean difference (SMD) over {len(bb)} covariate columns falls from {ft[ft["model"] + "_max_before"]:.3f} to {ft[ft["model"] + "_max_after"]:.3f} ({ft["model"]} model, the table\'s); '
      f'{above_after} columns stay above the 0.1 target. Effective sample size {ft["ess"]:,.0f} of {ft["n_selected"]:,} ({100 * ft["ess_share"]:.0f}%); weights trimmed to [{ft["trim_cuts"][0]:.2f}, {ft["trim_cuts"][1]:.2f}] (1st-99th percentile of the selected), mean 1.')
    ov = 0
    tot = 0
    for y in L.YEARS:
        rr = rates[(rates.group == 'all') & (rates.year == y) & rates.measure.isin(['share_ge25_unw', 'share_ge25_ipw'])].set_index('measure')
        tot += 1
        ov += int(max(rr.loc['share_ge25_unw'].lo, rr.loc['share_ge25_ipw'].lo) <= min(rr.loc['share_ge25_unw'].hi, rr.loc['share_ge25_ipw'].hi))
    A(f'- **Headline rates.** Share of papers with `ai_share` >= 0.25: 2024 {R.f(r24.loc["share_ge25_unw"].est, 3)} unweighted vs {R.f(r24.loc["share_ge25_ipw"].est, 3)} weighted; 2025 {R.f(r25.loc["share_ge25_unw"].est, 3)} vs {R.f(r25.loc["share_ge25_ipw"].est, 3)} '
      f'(section 3: the two intervals overlap in {ov} of {tot} years).')
    A('- CONCL_PLACEHOLDER')
    A('')
    A('## 1. The selection and the model\n')
    A('Outcome S = the paper has a usable local full text that the passage detector scored (`ai_share` not null). Population = every lab paper of the universe, 2016-2025 (strict labs), %s papers (%s with school in the model). Covariates: year, school, venue type (OpenAlex `source_type`), work type, OpenAlex OA status and `is_oa`, DOI prefix (publisher key; the 40 most frequent, rest pooled), OpenAlex field and subfield, log team size, log citations, log references, number of labs. '
      'Cross-fitted (5 folds) HistGradientBoosting and a one-hot logistic regression with year x school interactions; the table\'s model is the one with the smaller maximum SMD after weighting (**%s**; both propensities are in the table).\n' % (f'{meta["frame_rows"]:,}', f'{ft["n"]:,}', ft['model']))
    cov = df.assign(S=df['has_ft']).groupby('home_school').agg(papers=('paper_id', 'size'), full_text=('S', 'mean')).reset_index()
    A('Full-text coverage by school (share of papers 2016-2025 with a scored full text):\n')
    A(R.md_table([[r.home_school, f'{r.papers:,}', f'{100 * r.full_text:.1f}%'] for r in cov.itertuples()], ['school', 'papers', 'scored full text']))
    cy = df[df.home_school != 'gatech'].assign(S=lambda x: x['has_ft']).groupby('year').agg(papers=('paper_id', 'size'), full_text=('S', 'mean')).reset_index()
    A('\nBy year (Georgia Tech excluded): ' + '; '.join(f'{int(r.year)} {100 * r.full_text:.0f}%' for r in cy.itertuples()) + '.\n')
    A('**Positivity.** Share of papers with an estimated probability below 0.05: %.1f%%, below 0.02: %.2f%%. Georgia Tech has no full text (probability 0): its papers have no weights (NaN) and no full-text measure; every re-run below is therefore on the eight other schools. '
      'The abstract-availability table (`p_abs`, `w_abs`) is a degenerate case (AUC %.2f): papers without an OpenAlex record have no abstract and no covariates, so the weights cannot balance them (max SMD stays %.2f); **use `w_ft` only**.\n' %
      (100 * ft['share_p_below_0p05'], 100 * ft['share_p_below_0p02'], ab['logit_auc'], ab[f'{ab["model"]}_max_after']))
    A('## 2. Covariate balance (standardised mean differences against the whole population)\n')
    b = bal[(bal.tag == 'ft') & (bal.model == ft['model'])].copy()
    b['abs0'] = b['smd_before'].abs()
    top = b.sort_values('abs0', ascending=False).head(14)
    A(R.md_table([[r.covariate, f'{r.mean_all:.3f}', f'{r.mean_sel:.3f}', f'{r.mean_sel_w:.3f}', f'{r.smd_before:+.3f}', f'{r.smd_after:+.3f}'] for r in top.itertuples()],
                 ['covariate (dummy or standardised numeric)', 'all papers', 'full-text, unweighted', 'full-text, weighted', 'SMD before', 'SMD after']))
    A('\nColumns with |SMD| > 0.1: %d before, %d after (of %d). Boosting alternative: max %.3f before, %.3f after (ESS %s).\n' % ((b.smd_before.abs() > 0.1).sum(), (b.smd_after.abs() > 0.1).sum(), len(b), ft['gbm_max_before'], ft['gbm_max_after'], f'{ft["gbm_ess"]:,.0f}'))
    cc = pd.read_parquet(d / 'cell_check_ft.parquet')
    A('Year x school cells: largest absolute gap between the weighted full-text share of a cell and the population share %.4f (unweighted %.4f). Calibration by propensity decile (observed / predicted full-text rate): ' %
      ((cc.sel_weighted - cc['pop']).abs().max(), (cc.sel_unweighted - cc['pop']).abs().max()) + '; '.join(f'{r.observed:.2f}/{r.predicted:.2f}' for r in pd.read_parquet(d / 'calibration_ft.parquet').itertuples()) + '.\n')
    A('## 3. Dose rates: unweighted against weighted\n')
    rows = []
    for y in L.YEARS:
        r = rates[(rates.group == 'all') & (rates.year == y)].set_index('measure')
        rows.append([y] + [R.ci(r.loc[k].est, r.loc[k].lo, r.loc[k].hi, 4, False) for k in ('share_ge25_unw', 'share_ge25_ipw', 'mean_unw', 'mean_ipw')])
    A(R.md_table(rows, ['year', 'share >= 0.25, unweighted', 'share >= 0.25, IPW', 'mean ai_share, unweighted', 'mean ai_share, IPW']))
    A('\nBy school, 2025 (share of papers with ai_share >= 0.25):\n')
    rows = []
    for s in sorted(df.home_school.unique()):
        r = rates[(rates.group == 'school:' + s) & (rates.year == 2025)].set_index('measure')
        if len(r):
            rows.append([s, int(r.loc['share_ge25_unw'].n), R.ci(r.loc['share_ge25_unw'].est, r.loc['share_ge25_unw'].lo, r.loc['share_ge25_unw'].hi, 3, False), R.ci(r.loc['share_ge25_ipw'].est, r.loc['share_ge25_ipw'].lo, r.loc['share_ge25_ipw'].hi, 3, False)])
    A(R.md_table(rows, ['school', 'scored papers', 'unweighted', 'IPW']))
    A('')
    pr = pd.read_parquet(d / 'paper_rerun.parquet')
    A('## 4. Paper level: AI share against novelty (k = 3, scope all), weighted against unweighted against abstract-based\n')
    A('Coefficient of `nov_nn_cap` on the exposure (per unit, 0 -> 1) with a lab-bootstrap interval. `ft / unw` and `ft / IPW`: papers with a scored full text, exposure `ai_share`; `abs_all`: every paper with an abstract, exposure = its abstract flag (no full-text selection); `ft flag`: the abstract flag on the full-text papers (separates sample from exposure). Pooled = year + school + topic FE with controls; within-lab = lab x year FE. Pre = 2017-2021 placebo (the exposure there is detector noise).\n')
    rows, changes = [], []
    for (model, nk), g in pr[pr.exposure == 'ai_share'].groupby(['model', 'nov_kind']):
        for design in ('pooled', 'withinlab'):
            r = {}
            for lab_, q in (('ft / unw', dict(exposure='ai_share', sample='ft', weighting='unw')), ('ft / IPW', dict(exposure='ai_share', sample='ft', weighting='ipw')),
                            ('abs_all', dict(exposure='flag_abstract', sample='abs_all', weighting='unw')), ('ft flag / unw', dict(exposure='flag_abstract', sample='ft', weighting='unw')),
                            ('ft flag / IPW', dict(exposure='flag_abstract', sample='ft', weighting='ipw'))):
                for per in ('post', 'pre'):
                    x = R.row_of(pr, model=model, nov_kind=('abstract' if lab_ in ('abs_all', 'ft flag / unw', 'ft flag / IPW') else nk), period=per, design=design, **q)
                    r[(lab_, per)] = x
            def cell(k):
                x = r.get(k)
                return 'n/a' if x is None else R.ci(x.beta, x.lo, x.hi, 4)
            rows.append([model, nk, design] + [cell((l_, 'post')) for l_ in ('ft / unw', 'ft / IPW', 'abs_all', 'ft flag / unw', 'ft flag / IPW')] + [cell(('ft / unw', 'pre')), cell(('ft / IPW', 'pre'))])
            a, bq = r.get(('ft / unw', 'post')), r.get(('ft / IPW', 'post'))
            if a is not None and bq is not None and np.isfinite(a.lo) and np.isfinite(bq.lo):
                changes.append((model, nk, design, np.sign(a.beta) != np.sign(bq.beta), sig(a.lo, a.hi) != sig(bq.lo, bq.hi), bq.beta - a.beta, a, bq))
    A(R.md_table(rows, ['model', 'novelty from', 'design', 'post: ft / unw', 'post: ft / IPW', 'post: abs_all', 'post: ft flag / unw', 'post: ft flag / IPW', 'pre placebo: ft / unw', 'pre placebo: ft / IPW']))
    nflip = sum(c[3] for c in changes)
    nsig = sum(c[4] for c in changes)
    A(f'\nWeighting changes the sign of the post-2022 coefficient in {nflip} of {len(changes)} model-design cells and changes whether its interval excludes 0 in {nsig}; the largest shift is {max((abs(c[5]) for c in changes), default=0):.4f} (novelty sd about 0.07).')
    for c in changes:
        if c[3] or c[4]:
            A(f'- {c[0]} ({c[1]} novelty, {c[2]}): unweighted {R.ci(c[6].beta, c[6].lo, c[6].hi)} -> IPW {R.ci(c[7].beta, c[7].lo, c[7].hi)}.')
    A('')
    lr = pd.read_parquet(d / 'lab_rerun.parquet')
    A('## 5. Lab level: difference-in-differences with the dose from unweighted, IPW-weighted and abstract-flag exposure\n')
    A('`did` = post-2022 (2023-2025) x lab dose on a lab-year outcome with lab and year FE, per unit of dose (0 -> 1), bootstrap over labs; `placebo B` = the same on 2016-2021 with the break at B. Outcomes are the size-matched (5 papers) abstract-embedding measures of dose_lab.py. Dose kinds: `unweighted` = mean `ai_share` of the lab\'s scored 2023-25 papers (>= 4); `ipw` = the Hajek-weighted mean; `abstract_flag` = flagged-abstract share (all papers).\n')
    rows, lchg = [], []
    for (model, outc), g in lr[lr.spec.isin(['did', 'placebo2019', 'placebo2020', 'placebo2021'])].groupby(['model', 'outcome']):
        cells = []
        for dk in ('unweighted', 'ipw', 'abstract_flag'):
            x = g[(g.dose_kind == dk) & (g.spec == 'did')]
            cells.append('n/a' if not len(x) else R.ci(x.iloc[0].beta, x.iloc[0].lo, x.iloc[0].hi, 3))
        pl = g[(g.dose_kind == 'ipw') & g.spec.str.startswith('placebo')]
        pu = g[(g.dose_kind == 'unweighted') & g.spec.str.startswith('placebo')]
        x1 = g[(g.dose_kind == 'unweighted') & (g.spec == 'did')]
        x2 = g[(g.dose_kind == 'ipw') & (g.spec == 'did')]
        if len(x1) and len(x2) and np.isfinite(x1.iloc[0].lo) and np.isfinite(x2.iloc[0].lo):
            lchg.append((model, outc, np.sign(x1.iloc[0].beta) != np.sign(x2.iloc[0].beta), sig(x1.iloc[0].lo, x1.iloc[0].hi) != sig(x2.iloc[0].lo, x2.iloc[0].hi), x1.iloc[0], x2.iloc[0]))
        rows.append([model, outc] + cells + [', '.join(R.f(v, 3, True) for v in pu.sort_values('spec').beta), ', '.join(R.f(v, 3, True) for v in pl.sort_values('spec').beta)])
    A(R.md_table(rows, ['model', 'outcome', 'did: unweighted dose', 'did: IPW dose', 'did: abstract-flag dose', 'placebos 2019/20/21 (unweighted)', 'placebos (IPW)']))
    A(f'\nIPW dose against unweighted dose: sign differs in {sum(c[2] for c in lchg)} of {len(lchg)} model-outcome cells; interval-excludes-0 status differs in {sum(c[3] for c in lchg)}.\n')
    for c in lchg:
        if c[2] or c[3]:
            A(f'- {c[0]} {c[1]}: unweighted {R.ci(c[4].beta, c[4].lo, c[4].hi, 3)} -> IPW {R.ci(c[5].beta, c[5].lo, c[5].hi, 3)}.')
    A('')
    A('## 6. The weights table (reusable)\n')
    A('`ai-writing/data/labstudy/ipw/ipw_weights.parquet` (path from `lcommon.IPW_TABLE`, `LABSTUDY_IPW_TABLE` overrides), one row per universe paper, keyed by `paper_id` (atlas id `atl:w:...`, else `oa:<W id>`): '
      '`in_ft`, `p_ft` (cross-fitted propensity of the table\'s model), `p_ft_gbm`, `p_ft_logit`, `w_ft_raw` (stabilised, untrimmed), `w_ft` (stabilised, trimmed, mean 1 among selected; **use this**); the same for the abstract (`*_abs`, degenerate: do not use). '
      'NaN for papers outside the model (Georgia Tech) and for `w_*` of papers without full text. Use: `df.merge(pd.read_parquet(IPW_TABLE)[["paper_id","w_ft"]], on="paper_id")` and pass `w_ft` as a regression weight or in a Hajek mean on full-text papers; detector v3 reuses it unchanged '
      '(the selection is the availability of text, not the score) until the final paper set changes the population: then `labstudy/run_all.sh ipw` refits it.\n')
    A('## Not done and caveats\n')
    A('- IPW corrects selection on the listed covariates only (missing at random given them). Selection on unobservables (a paper whose PDF exists because its authors put it on arXiv *because* it is machine-friendly) is not addressed; the balance check cannot see it.\n'
      '- The weights are held fixed in the bootstrap (weight-estimation error is not propagated); the intervals are therefore slightly too narrow for the weighted columns.\n'
      '- Georgia Tech (no full text) is outside every weighted result. Full-text embeddings for Qwen3-Embedding-4B were not built, so it is absent.\n')
    txt = '\n'.join(out)
    concl = conclusions(changes, lchg, nflip, nsig)
    txt = txt.replace('- CONCL_PLACEHOLDER', concl)
    p = L.REPORTS / 'FULLTEXT-SELECTION-IPW.md'
    p.write_text(txt + '\n')
    L.log(step='ipw_report', path=str(p))


def conclusions(changes, lchg, nflip, nsig):
    n = len(changes)
    return (f'**Where conclusions change.** Paper level: weighting flips the sign of the post-2022 dose-novelty coefficient in {nflip} of {n} model-design cells and moves an interval across 0 in {nsig} (section 4 lists them); '
            f'lab level: sign differs in {sum(c[2] for c in lchg)} of {len(lchg)} model-outcome cells and the zero-status in {sum(c[3] for c in lchg)} (section 5). The all-papers abstract-flag estimates are shown next to them.')


if __name__ == '__main__':
    main()
