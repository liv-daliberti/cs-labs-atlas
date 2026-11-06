"""Writes ai-writing/diversity/reports/LAB-EVENT-STUDY.md from OUT/event/*.parquet."""
import json

import numpy as np
import pandas as pd

import event_study as ES
import lcommon as L
import lreport as R

HEAD = ES.HEADLINE


def nice(o):
    m, _, mod = o.partition('|')
    return {'h_oa': 'OpenAlex-topic entropy (h_oa)'}.get(o, f'{m} ({mod})' if mod else m)


def main():
    d = L.out('event')
    res = pd.read_parquet(d / 'results.parquet')
    ad = pd.read_parquet(d / 'adoption.parquet')
    info = pd.read_parquet(d / 'adoption_info.parquet')
    outc = pd.read_parquet(d / 'outcomes.parquet')
    sd = outc[outc.source == 'main'].groupby('outcome')['value'].std()
    sdc = outc.groupby(['source', 'outcome'])['value'].std()
    diagf = pd.read_parquet(d / 'diag_features.parquet')
    diagd = pd.read_parquet(d / 'diag_dept.parquet')
    prereg = json.loads((L.HERE / 'preregistration.json').read_text())
    out = []
    A = out.append
    A('# Before/after by lab: a staggered-adoption event study of AI wording\n')
    A(f'Generated {R.now()} by `ai-writing/labstudy/event_report.py` (`event_study.py`); tables in `ai-writing/data/labstudy/event` (git-ignored). Thresholds, outcomes and estimator were **pre-registered** in `ai-writing/labstudy/preregistration.json` (committed before any run). '
      '**Years 2016-2025 only; a lab\'s adoption year is the first year it exceeds the threshold for two consecutive years (so 2025 alone cannot confirm one).** Intervals are 95% percentile intervals of a bootstrap over labs (300 replicates, everything recomputed). Strict labs.\n')
    prim = res[(res.spec == 'S1_primary') & (res['sample'] == 'primary')]
    # --- coverage
    i1 = info[info.spec == 'S1_primary'].iloc[0]
    A('## Answer\n')
    st = ad[ad.spec == 'S1_primary']['status'].value_counts().to_dict()
    A(f'- **Adoption.** Under the primary rule (share of a lab-year\'s scored papers with `ai_share` >= 0.25 above the 2016-21 floor {R.f(i1.floor, 4)} + 3 SD = threshold {R.f(i1.threshold, 3)}, sustained 2 years) {st.get("adopter", 0)} labs adopt '
      f'(cohorts {i1.cohorts}), {st.get("never", 0)} never exceed it, {st.get("never_unsustained", 0)} exceed it without sustaining, {st.get("censored", 0)} exceed it only in 2025 (censored, left out), {st.get("insufficient", 0)} have too few scored papers. '
      'Adoption is concentrated in 2023-2024 by construction of the data (the floor is the pre-ChatGPT noise), so the design has two real cohorts and few usable leads: that limits what a pre-trend test can show.')
    h = prim[(prim.source == 'main') & prim.outcome.isin(HEAD)]
    bits = []
    for o in HEAD:
        x = h[(h.outcome == o) & (h.kind == 'stat') & (h.stat == 'overall_att')]
        w = h[(h.outcome == o) & (h.kind == 'stat') & (h.stat == 'pretrend_wald')]
        if len(x):
            r, p = x.iloc[0], w.iloc[0] if len(w) else None
            bits.append(f'{nice(o)} {R.ci(r.est, r.lo, r.hi, 4)} (pre-trend p = {R.f(p.lo, 3) if p is not None else "n/a"})')
    A('- **Overall ATT of adoption on the headline outcomes** (Callaway-Sant\'Anna, never-adopter controls, post-adoption years): ' + '; '.join(bits) + '.')
    allp = prim[(prim.source == 'main') & (prim.kind == 'stat') & (prim.stat == 'pretrend_wald')]
    rej = int((allp.lo < 0.05).sum())
    A(f'- **Pre-trends.** The joint test that the leads (e = -5..-2) are zero rejects at 5% for {rej} of {len(allp)} outcomes (main source, primary spec); with that many tests about {0.05 * len(allp):.0f} would reject by chance. Details per outcome in the grid below. '
      'Timing is not exogenous: see the diagnostics section (labs that already published on LLM topics before 2023 adopt first), so every ATT here is an association with adoption timing, not a causal effect of AI wording.')
    A('- CTL_PLACEHOLDER')
    A('')
    # --- adoption table
    A('## 1. Adoption definitions (pre-registered) and what they select\n')
    rows = []
    for r in info.itertuples():
        rows.append([r.spec, r.metric, r.k, r.sustain, R.f(r.floor, 4), R.f(r.sd, 4), R.f(r.threshold, 4), int(np.nan_to_num(getattr(r, 'adopter', 0))), int(np.nan_to_num(getattr(r, 'never', 0))), int(np.nan_to_num(getattr(r, 'never_unsustained', 0))), int(np.nan_to_num(getattr(r, 'censored', 0))), r.cohorts])
    A(R.md_table(rows, ['spec', 'metric', 'k SD', 'years sustained', 'floor (2016-21)', 'SD', 'threshold', 'adopters', 'never', 'exceeded, unsustained', 'censored (2025 only)', 'cohorts (year: labs)']))
    A('\nGeorgia Tech has no full text, so it has no adoption year in specs using full-text scores (S6 uses the abstract flag and covers it). A lab-year needs >= 3 scored papers (>= 3 abstracts for S6). The floor window precedes ChatGPT, so adoptions dated before 2023 are detector noise (reported, not removed; `post2022` sample drops them).\n')
    # --- headline
    A('## 2. Headline outcomes: event-time effects\n')
    A('`e` = years since adoption; the base year is e = -1 (zero by construction). Leads e <= -2 test pre-trends; e >= 0 are effects. Estimate [interval]; the outcome sd (over lab-years) is in the header table.\n')
    rows = []
    for o in HEAD:
        x = prim[(prim.source == 'main') & (prim.outcome == o)]
        if not len(x):
            continue
        ev = x[x.kind == 'event'].set_index('e')
        r = [nice(o), R.f(sd.get(o, np.nan), 4), int(x.n_treated.iloc[0]), int(x.n_control.iloc[0])]
        for e in ES.EV_LEADS + [0, 1, 2]:
            r.append(R.ci(ev.loc[e].est, ev.loc[e].lo, ev.loc[e].hi, 3) if e in ev.index and np.isfinite(ev.loc[e].est) else 'n/a')
        rows.append(r)
    A(R.md_table(rows, ['outcome', 'sd', 'treated labs', 'control labs'] + [f'e={e}' for e in ES.EV_LEADS + [0, 1, 2]]))
    A('')
    A('Summary statistics (primary spec; `perm p` = share of 200 random reassignments of the adoption years with an overall ATT at least as large in size; TWFE = two-way fixed-effects estimate on the same sample, which staggered adoption can bias):\n')
    rows = []
    for o in HEAD:
        x = prim[(prim.source == 'main') & (prim.outcome == o)]
        if not len(x):
            continue
        g = lambda k, kind='stat': x[(x.kind == kind) & (x.stat == k)]  # noqa: E731
        def c(k, kind='stat', dd=4):
            y = g(k, kind)
            return R.ci(y.iloc[0].est, y.iloc[0].lo, y.iloc[0].hi, dd) if len(y) else 'n/a'
        w = g('pretrend_wald')
        pp = g('perm_p_two_sided', 'perm')
        rows.append([nice(o), c('overall_att'), f'{c("overall_att")[:0]}{R.f(R.row_of(x, kind="stat", stat="overall_att").est / sd.get(o, np.nan), 2, True) if len(g("overall_att")) else "n/a"}', c('dyn_att_0_2'), c('pretrend_slope', dd=5),
                     f'{R.f(w.iloc[0].lo, 3)} (df {int(w.iloc[0].hi)})' if len(w) else 'n/a', R.f(pp.iloc[0].est, 3) if len(pp) else 'n/a', c('post', 'twfe_static')])
    A(R.md_table(rows, ['outcome', 'overall ATT', 'ATT in sd', 'ATT e=0..2', 'pre-trend slope / yr', 'Wald p (leads)', 'perm p', 'TWFE static']))
    A('')
    # --- grid
    A('## 3. All outcomes (primary spec S1, original embeddings)\n')
    rows = []
    for o in sorted(prim[prim.source == 'main'].outcome.unique()):
        x = prim[(prim.source == 'main') & (prim.outcome == o) & (prim.kind == 'stat')]
        a = x[x.stat == 'overall_att']
        w = x[x.stat == 'pretrend_wald']
        if not len(a):
            continue
        sl = x[x.stat == 'pretrend_slope']
        r = a.iloc[0]
        rows.append([nice(o), int(r.n_treated), int(r.n_control), R.ci(r.est, r.lo, r.hi, 4), R.f(r.est / sd.get(o, np.nan), 2, True), R.ci(sl.iloc[0].est, sl.iloc[0].lo, sl.iloc[0].hi, 5) if len(sl) else 'n/a',
                     R.f(w.iloc[0].lo, 3) if len(w) else 'n/a', 'excl 0' if (r.lo > 0 or r.hi < 0) else 'incl 0'])
    A(R.md_table(rows, ['outcome', 'treated', 'controls', 'overall ATT', 'in sd', 'pre-trend slope / yr', 'Wald p', 'ATT interval']))
    A('')
    # --- sensitivity
    A('## 4. Sensitivity: adoption definition and control group\n')
    rows = []
    for o in HEAD:
        for spec in prereg['adoption']['specs']:
            x = res[(res.outcome == o) & (res.source == 'main') & (res.spec == spec) & (res['sample'] == 'primary') & (res.kind == 'stat')]
            a, w = x[x.stat == 'overall_att'], x[x.stat == 'pretrend_wald']
            if len(a):
                rows.append([nice(o), spec, int(a.iloc[0].n_treated), int(a.iloc[0].n_control), R.ci(a.iloc[0].est, a.iloc[0].lo, a.iloc[0].hi, 4), R.f(w.iloc[0].lo, 3) if len(w) else 'n/a'])
        for sample in ('nyt', 'post2022', 'strict_never'):
            x = res[(res.outcome == o) & (res.source == 'main') & (res.spec == 'S1_primary') & (res['sample'] == sample) & (res.kind == 'stat')]
            a, w = x[x.stat == 'overall_att'], x[x.stat == 'pretrend_wald']
            if len(a):
                rows.append([nice(o), 'S1 / ' + {'nyt': 'not-yet-treated controls', 'post2022': 'post-2022 adopters only', 'strict_never': 'controls never exceed (added after registration)'}[sample], int(a.iloc[0].n_treated), int(a.iloc[0].n_control),
                             R.ci(a.iloc[0].est, a.iloc[0].lo, a.iloc[0].hi, 4), R.f(w.iloc[0].lo, 3) if len(w) else 'n/a'])
    A(R.md_table(rows, ['outcome', 'spec / sample', 'treated', 'controls', 'overall ATT', 'Wald p']))
    A('')
    # --- control
    A('## 5. Wording control (all-AI rewritten abstracts)\n')
    A('Geometry and topic outcomes recomputed on the Qwen2.5-7B-polished version of every abstract (same papers, same lab-years, same draws) and the event study run on the original (`orig`), the rewritten (`ai`), and their paired difference (`gap` = ai - orig). '
      'If adoption were associated with wording alone the `ai` ATT would be the same as `orig` and `gap` ~ 0 would not distinguish; the informative reading is the opposite: if the `orig` ATT is carried by content, it persists in `ai` and `gap` is about 0. Novelty has no per-paper all-AI table, so it is not part of the control.\n')
    rows, ctl_note = [], []
    for o in sorted(res[res.source.str.startswith('ctl')].outcome.unique()):
        cells = []
        for s in ('ctl_orig', 'ctl_ai', 'ctl_gap'):
            x = res[(res.outcome == o) & (res.source == s) & (res.spec == 'S1_primary') & (res['sample'] == 'primary') & (res.kind == 'stat') & (res.stat == 'overall_att')]
            cells.append(R.ci(x.iloc[0].est, x.iloc[0].lo, x.iloc[0].hi, 4) if len(x) else 'n/a')
        w = res[(res.outcome == o) & (res.source == 'ctl_gap') & (res.spec == 'S1_primary') & (res.kind == 'stat') & (res.stat == 'pretrend_wald')]
        rows.append([nice(o)] + cells + [R.f(w.iloc[0].lo, 3) if len(w) else 'n/a'])
    A(R.md_table(rows, ['outcome', 'ATT original wording', 'ATT all-AI wording', 'gap (ai - orig)', 'gap pre-trend Wald p']))
    A('')
    # --- diagnostics
    A('## 6. Is adoption timing endogenous?\n')
    A('Adopters (primary spec) against labs that never exceed the threshold, on features measured before 2023. SMD = standardised mean difference (adopters - controls).\n')
    rows = []
    for r in diagf.itertuples():
        if r.feature.startswith('spearman'):
            continue
        rows.append([r.feature, R.f(r.adopters, 3), R.f(r.controls, 3), R.f(r.smd, 2, True), int(r.n_adopt), int(r.n_ctl)])
    A(R.md_table(rows, ['feature', 'adopters', 'never-adopters', 'SMD', 'n adopters', 'n controls']))
    sp = diagf[diagf.feature.str.startswith('spearman')].iloc[0]
    A(f'\nAmong 2023+ adopters, Spearman correlation of adoption year with the lab\'s share of LLM-text papers in 2021-22: rho = {R.f(sp.adopters, 3, True)} (p = {R.f(sp.n_ctl, 4)}, n = {int(sp.n_adopt)}); negative means labs already writing about LLMs adopt earlier.\n')
    A('Share of labs that adopt, by department type: ' + '; '.join(f'{r.dept_type} {100 * r.adopt_share:.0f}% of {r.labs}' for r in diagd.itertuples()) + '.\n')
    A('## Not done and caveats\n')
    A('- **Identification.** Adoption is detected from the lab\'s own papers, so it is correlated with lab size and with early engagement in LLM topics; never-adopters are mostly small labs. The ATT compares adopters with never-adopters after differencing out the lab and the base year; it does not remove a differential trend that starts at adoption (e.g. a lab moving to LLM topics and to AI-polished text together). Treat it as an association with the timing of adoption.\n'
      '- **Few leads.** Nearly all adopters adopt in 2023-2024, so e = -5..-2 draw on 2017-2022 with two cohorts; the Wald test has limited power, and a non-rejection is weak evidence of parallel trends.\n'
      '- Heterogeneity-robust estimator is Callaway-Sant\'Anna without covariates (Sun-Abraham not run); TWFE is shown only for comparison. Outcomes are size-matched on 5 papers (geometry) or >= 3 papers (novelty), so small lab-years drop out of the panel.\n')
    txt = '\n'.join(out)
    # control sentence
    ctl_bits = []
    for o in ('mpd|specter2_proximity', 'disp|specter2_proximity', 'dist_centroid|bt_qwen3_0p6b'):
        x = res[(res.outcome == o) & (res.source == 'ctl_gap') & (res.spec == 'S1_primary') & (res.kind == 'stat') & (res.stat == 'overall_att')]
        y = res[(res.outcome == o) & (res.source == 'ctl_orig') & (res.spec == 'S1_primary') & (res.kind == 'stat') & (res.stat == 'overall_att')]
        if len(x) and len(y):
            ctl_bits.append(f'{nice(o)}: original {R.ci(y.iloc[0].est, y.iloc[0].lo, y.iloc[0].hi)}, gap (ai - orig) {R.ci(x.iloc[0].est, x.iloc[0].lo, x.iloc[0].hi)}')
    txt = txt.replace('- CTL_PLACEHOLDER', '- **Wording control.** ' + '; '.join(ctl_bits) + ' (section 5).')
    p = L.REPORTS / 'LAB-EVENT-STUDY.md'
    p.write_text(txt + '\n')
    L.log(step='event_report', path=str(p))


if __name__ == '__main__':
    main()
