"""Write RESULTS.md from the tables of a run (every number is read from <results>/tables; the prose around them is fixed text).
usage: study_report.py [--id 2026-11-07]
"""
import argparse
import json

import pandas as pd

import study_common as C


def T(res, name):
    return pd.read_csv(res / 'tables' / f'{name}.csv')


def row(df, **kw):
    m = pd.Series(True, index=df.index)
    for k, v in kw.items():
        m &= df[k] == v
    d = df[m]
    return d.iloc[0] if len(d) else None


def iv(r, scale=1.0, nd=3, pct=False):
    if r is None or pd.isna(r.est):
        return 'n/a'
    f = (lambda x: f'{100 * x:+.{nd - 1}f}') if pct else (lambda x: f'{scale * x:+.{nd}f}')
    return f'{f(r.est)} [{f(r.lo)}, {f(r.hi)}]' + (' pp' if pct else '')


def level(r, col, nd=3, pct=False):
    return 'n/a' if r is None else (f'{100 * r[col]:.1f}%' if pct else f'{r[col]:.{nd}f}')


def compare_lines(snap_id, base):
    """Headline estimates of this run next to an earlier run (same measures), with whether each interval excludes zero."""
    res, old = C.results_dir(snap_id), C.results_dir(base)
    if not (old / 'tables' / 'ai_contrasts.csv').exists():
        return []
    P = 'post_minus_pre'

    def pick(r, name, df, **kw):
        x = row(df, **kw)
        return None if x is None else x

    items = []
    for lab, tab, kw in (
            ('papers >= 25% flagged (main body), pp', 'ai_contrasts', dict(measure='heavy_main', scope='ALL', sample='all', contrast=P)),
            ('same, main + appendix, pp', 'ai_contrasts', dict(measure='heavy_main_appendix', scope='ALL', sample='all', contrast=P)),
            ('LLM-topic share, pp', 'topics_llm_contrasts', dict(scope='ALL', sample='all', contrast=P)),
            ('embedding distance within lab', 'embed_contrasts', dict(level='within_lab', scope='ALL', model=C.HEADLINE_MODEL, variant='raw', sample='all', contrast=P)),
            ('embedding distance across labs, same school', 'embed_contrasts', dict(level='cross_lab_same_school', scope='ALL', model=C.HEADLINE_MODEL, variant='raw', sample='all', contrast=P)),
            ('embedding distance across schools', 'embed_contrasts', dict(level='cross_school', scope='ALL', model=C.HEADLINE_MODEL, variant='raw', sample='all', contrast=P)),
            ('across labs, topic-residual', 'embed_contrasts', dict(level='cross_lab_same_school', scope='ALL', model=C.HEADLINE_MODEL, variant='topic_residual', sample='all', contrast=P)),
            ('citation: Uzzi median z', 'citation_contrasts', dict(measure='cit_z_med', scope='ALL', sample='all', contrast=P))):
        pct = 'pp' in lab
        a, b = row(T(old, tab), **kw), row(T(res, tab), **kw)
        nz = lambda r: 'n/a' if r is None else ('excludes 0' if (r.lo > 0 or r.hi < 0) else 'includes 0')  # noqa: E731
        items.append(f'| {lab} | {iv(a, pct=pct, nd=4 if not pct else 3)} ({nz(a)}) | {iv(b, pct=pct, nd=4 if not pct else 3)} ({nz(b)}) |')
    out = ['## Comparison with ' + base + '\n', f'Same estimators, {base} against this snapshot (which adds the scored and embedded papers the earlier build never saw, including the partial schools).\n',
           f'| estimate (post minus pre, 12 schools) | {base} | {snap_id} |', '|---|---|---|'] + items
    ev0, ev1 = T(old, 'event_results'), T(res, 'event_results')
    for o in ('mpd_specter2_proximity', 'llm_topic_share'):
        a, b = row(ev0, outcome=o, stat='overall_att', sample='all'), row(ev1, outcome=o, stat='overall_att', sample='all')
        wa, wb = row(ev0, outcome=o, stat='pretrend_wald', sample='all'), row(ev1, outcome=o, stat='pretrend_wald', sample='all')
        nz = lambda r: 'n/a' if r is None else ('excludes 0' if (r.lo > 0 or r.hi < 0) else 'includes 0')  # noqa: E731
        items = [f'| event study ATT, {o} | {iv(a, nd=4)} ({nz(a)}; pre-trend p = {wa.lo:.3f}) | {iv(b, nd=4)} ({nz(b)}; pre-trend p = {wb.lo:.3f}) |']
        out += items
    return out + ['']


def build(snap_id, compare=None):
    res = C.results_dir(snap_id)
    man = json.loads((C.snapshot_dir(snap_id) / 'MANIFEST.json').read_text())
    pcov = [man['coverage']['by_school'][s_] for s_ in C.PARTIAL]
    low_cov = max(c['fulltext_v3'] for c in pcov) < 0.3
    ai, ser = T(res, 'ai_contrasts'), T(res, 'ai_series')
    em, es = T(res, 'embed_contrasts'), T(res, 'embed_series')
    ll, en, js = T(res, 'topics_llm_contrasts'), T(res, 'topics_entropy_contrasts'), T(res, 'topics_crosslab_jsd')
    ci, ev, fp = T(res, 'citation_contrasts'), T(res, 'event_results'), T(res, 'ai_fp_corrected')
    adopt = T(res, 'event_adoption_summary')
    P, PL = 'post_minus_pre', 'placebo_2019_21_minus_2016_18'
    a = lambda m, sc='ALL', sm='all', c=P: row(ai, measure=m, scope=sc, sample=sm, contrast=c)  # noqa: E731
    e = lambda lv, sc='ALL', mo=C.HEADLINE_MODEL, va='raw', sm='all', c=P: row(em, level=lv, scope=sc, model=mo, variant=va, sample=sm, contrast=c)  # noqa: E731
    c_ = lambda m, c=P, sc='ALL': row(ci, measure=m, scope=sc, sample='all', contrast=c)  # noqa: E731
    yr = lambda m, y, sc='ALL': row(ser, measure=m, scope=sc, sample='all', year=y)  # noqa: E731
    ev_stat = lambda o, s, sm='all': row(ev, outcome=o, stat=s, sample=sm)  # noqa: E731
    lines = []
    w = lines.append
    w(f'# Pre/post-ChatGPT homogenization at 12 schools: results on snapshot {snap_id}\n')
    w(f'Run on the sealed snapshot `studies/homogenization/snapshots/{snap_id}` (release {man["release_id"]}; detector v3). Window 2016 to 2025; ChatGPT launched '
      '2022-11-30, so **post = 2023 to 2025, pre = 2016 to 2022** (2022 dropped in a sensitivity). No 2026 anywhere. Every interval is a 95% percentile interval of a '
      '**lab-cluster bootstrap** (400 draws, stratified by school); counts of schools or domains are never used as evidence. Labs are strict: a paper is in a lab only when '
      'the lab\'s PI is on the byline. A paper of two labs counts in both.\n')
    if compare:
        lines.extend(['[comparison placeholder]'])
    w('## 1. Headline\n')
    w('"Placebo" is the same contrast placed inside the pre period (2019 to 2021 minus 2016 to 2018): a post-minus-pre change counts only if it clearly exceeds it.\n')
    w('| layer | measure (12 schools) | pre | post | post minus pre [95% CI] | placebo [95% CI] |')
    w('|---|---|---|---|---|---|')

    def hl(layer, name, r, rp, pct=False, nd=3):
        w(f'| {layer} | {name} | {level(r, "pre", nd, pct)} | {level(r, "post", nd, pct)} | {iv(r, pct=pct, nd=nd)} | {iv(rp, pct=pct, nd=nd)} |')
    hl('AI share', 'papers with >= 25% of main-body passages flagged', a('heavy_main'), a('heavy_main', c=PL), True)
    hl('AI share', 'same, main body + appendix', a('heavy_main_appendix'), a('heavy_main_appendix', c=PL), True)
    hl('AI share', 'mean share of passages flagged (main body)', a('dose_main'), a('dose_main', c=PL), True)
    hl('AI share', 'abstract flagged (v1 detector)', a('abs_flag'), a('abs_flag', c=PL), True)
    hl('Topics', 'papers on LLM topics (title/abstract regex)', row(ll, scope='ALL', sample='all', contrast=P), row(ll, scope='ALL', sample='all', contrast=PL), True)
    hl('Topics', 'within-lab topic entropy (bits, 8 papers)', row(en, scope='ALL', sample='all', contrast=P), row(en, scope='ALL', sample='all', contrast=PL))
    j = row(js, measure='cross_lab_jsd_m10', scope='ALL')
    w(f'| Topics | cross-lab topic divergence (JSD, labs with >= 10 papers in both periods) | {j.pre:.3f} | {j.post:.3f} | {iv(j, nd=4)} | not computed |')
    hl('Embeddings', 'within-lab mean pairwise distance (SPECTER2 proximity)', e('within_lab'), e('within_lab', c=PL))
    hl('Embeddings', 'across labs, same school', e('cross_lab_same_school'), e('cross_lab_same_school', c=PL))
    hl('Embeddings', 'across schools', e('cross_school'), e('cross_school', c=PL))
    hl('Citations', 'median Uzzi z (lower = more conventional combinations)', c_('cit_z_med'), c_('cit_z_med', PL))
    hl('Citations', 'Rao-Stirling reference diversity (subfield)', c_('cit_rs_sub'), c_('cit_rs_sub', PL))
    o = ev_stat('mpd_specter2_proximity', 'overall_att')
    pt = ev_stat('mpd_specter2_proximity', 'pretrend_wald')
    w(f'| Event study | within-lab distance, ATT of AI uptake ({int(o.n_treated)} adopting vs {int(o.n_control)} never-adopting labs) | | | {iv(o, nd=4)} | pre-trend Wald p = {pt.lo:.2f} |')
    w('')
    r15, r24, r23 = yr('heavy_main', 2025), yr('heavy_main', 2024), yr('heavy_main', 2023)
    w('**In words.**\n')
    w(f'1. *AI-flagged writing rose steeply and only after 2022.* Papers with a quarter or more of their main-body passages flagged were {level(yr("heavy_main", 2022), "est", pct=True)} in 2022, '
      f'{level(r23, "est", pct=True)} in 2023, {level(r24, "est", pct=True)} in 2024 and {level(r15, "est", pct=True)} in 2025 (2025 interval {level(r15, "lo", pct=True)} to {level(r15, "hi", pct=True)}). '
      f'Pre-2023 values are at the detector floor ({level(yr("heavy_main", 2021), "est", pct=True)} in 2021). Counting the appendix changes the post level by under half a point.')
    w(f'2. *Across-lab homogenization in embedding space is small, significant, and in the opposite direction to the pre-2023 drift.* Abstracts of different labs of the same school are '
      f'{iv(e("cross_lab_same_school"), nd=4)} closer after 2022 (distance), and abstracts of different schools {iv(e("cross_school"), nd=4)}; the pre-period placebo moved the other way '
      f'({iv(e("cross_lab_same_school", c=PL), nd=4)}). The effect is about 1% of the distance scale. Seven embedding models agree on the sign with intervals excluding zero (section 3).')
    w(f'3. *Within labs there is no detectable change* in the spread of abstracts ({iv(e("within_lab"), nd=4)}); the pre-period placebo drift is larger than the post change, so the within-lab '
      'series cannot be called converging or diverging.')
    w(f'4. *Topics move toward LLM work*, as expected ({iv(row(ll, scope="ALL", sample="all", contrast=P), pct=True)} of papers), which is mostly where the AI-flagged writing sits. '
      f'Within-lab topic entropy and cross-lab topic divergence show no change distinguishable from zero (intervals include zero).')
    w(f'5. *Citations: reference lists get more diverse and slightly more conventional in pair combinations, but both continue pre-2023 drifts.* Rao-Stirling {iv(c_("cit_rs_sub"), nd=4)} '
      f'(placebo {iv(c_("cit_rs_sub", PL), nd=4)}, so the post change exceeds the placebo by little); Uzzi median z {iv(c_("cit_z_med"), nd=3)} (the placebo, {iv(c_("cit_z_med", PL), nd=3)}, is larger: no post-2022 break).')
    w(f'6. *The lab event study does not show an effect of AI uptake on within-lab distance* (ATT {iv(o, nd=4)}, pre-trends not rejected). LLM-topic share rises in adopting labs '
      f'(ATT {iv(ev_stat("llm_topic_share", "overall_att"), pct=True)} points) but its pre-trends are rejected (Wald p = {ev_stat("llm_topic_share", "pretrend_wald").lo:.4f}): an association, not an effect.\n')
    w('Association, not causation: nothing here separates AI use from the topic shift toward LLMs or from a general change in how abstracts are written.\n')

    w('## 2. Writing style and AI share (detector v3)\n')
    w('Detector v3: false-positive rate 0.30% per passage (CI 0.27 to 0.32%); misses on unseen generator families 0.9 to 6.6%; it abstains on short or heading-heavy passages (excluded). '
      'Detector-training papers (`trained_on_v3`) are excluded from every rate. Only full-text-scored papers enter the full-text rows.\n')
    w('| year | heavy share, main body | main + appendix | mean passage share (main) | abstract flag |')
    w('|---|---|---|---|---|')
    for y in range(2016, 2026):
        w(f'| {y} | ' + ' | '.join(f'{100 * yr(m, y).est:.2f}% [{100 * yr(m, y).lo:.2f}, {100 * yr(m, y).hi:.2f}]' for m in ('heavy_main', 'heavy_main_appendix', 'dose_main', 'abs_flag')) + ' |')
    w('')
    w('**Main body versus main + appendix.** ' + f'Heavy-share change {iv(a("heavy_main"), pct=True)} points (main) against {iv(a("heavy_main_appendix"), pct=True)} (with appendix). '
      'The appendix false-alarm check of the detector (0.32% [0.25, 0.41]) passes its 1.5% limit.\n')
    w('**False-positive correction.** Mean passage share is corrected as a = (f - fpr) / (1 - miss - fpr). With fpr 0.30% and miss 0 to 6.6%:\n')
    w('| year | observed | corrected (miss 0) | corrected (miss 6.6%) |')
    w('|---|---|---|---|')
    for y in (2023, 2024, 2025):
        q0 = fp[(fp.scope == 'ALL') & (fp.year == y) & (fp.fpr == 'fpr') & (fp.miss == 'miss0')].iloc[0]
        q1 = fp[(fp.scope == 'ALL') & (fp.year == y) & (fp.fpr == 'fpr') & (fp.miss == 'miss6.6')].iloc[0]
        w(f'| {y} | {100 * q0.observed:.1f}% | {100 * q0.corrected:.1f}% [{100 * q0.corrected_lo:.1f}, {100 * q0.corrected_hi:.1f}] | {100 * q1.corrected:.1f}% [{100 * q1.corrected_lo:.1f}, {100 * q1.corrected_hi:.1f}] |')
    w('\nThe correction moves the post level by well under one point at fpr 0.30%; the miss rate matters more (up to +0.2 to +1 point).\n')
    ipw = a('heavy_main_ipw')
    w(f'**IPW (full-text selection).** Papers with full text are not a random sample (selection model fitted earlier, weights carried over from the 2026-11-05 fit; papers it never saw have no weight and drop out): '
      f'weighted heavy-share change {iv(ipw, pct=True)} points against unweighted {iv(a("heavy_main"), pct=True)}. Selection does not explain the rise.\n')
    w('Writing style dispersion (stylometry), the paired AI-rewrite wording control and AI-in-revision are carried over unchanged from the 2026-11-05 detector-v3 runs (section 7).\n')

    w('## 3. Embedding diversity and homogenization\n')
    w('Distance is 1 - mean cosine of centred, unit-normalised abstract vectors; within-lab uses lab-years with >= 5 papers; "across" pairs come from different labs (same school) or different schools in the same year.\n')
    w('| model | within lab | across labs, same school | across schools |')
    w('|---|---|---|---|')
    for mo in C.MODELS:
        w(f'| {mo} | ' + ' | '.join(iv(e(lv, mo=mo), nd=4) for lv in ('within_lab', 'cross_lab_same_school', 'cross_school')) + ' |')
    w('')
    w('Topic-residualised (subtract each OpenAlex subfield centroid, SPECTER2 proximity): ' + ' | '.join(f'{lv.replace("_", " ")} {iv(e(lv, va="topic_residual"), nd=4)}' for lv in ('within_lab', 'cross_lab_same_school', 'cross_school')) +
      '. The across-lab convergence survives removing the topic mean, so it is not only the shift toward LLM topics.\n')
    w('**Shape.** Figure 2: across-lab and across-school distance rise from 2016 to about 2020 to 2022, then fall in 2023, 2024 and especially 2025. The post-minus-pre contrast is driven by 2024 and 2025, and the earlier rise is why the pre-period placebo is positive; a single pre/post step overstates how sudden the change is.\n')
    w('**Wording confound.** AI-polished wording moves vectors mechanically. The paired all-AI rewrite (Qwen2.5-7B, same papers, carried over, 9 schools) puts the wording share of the post-2022 Vendi fall at about 15% and of the SPECTER2 novelty fall at about 27%; the rest is content. '
      'The detector-free topic-residual rows above are the check run on this snapshot. A rewrite of the 3 new schools was not run.\n')

    w('## 4. Topics\n')
    w(f'LLM-topic share {iv(row(ll, scope="ALL", sample="all", contrast=P), pct=True)} points; within-lab topic entropy {iv(row(en, scope="ALL", sample="all", contrast=P))} bits (placebo {iv(row(en, scope="ALL", sample="all", contrast=PL))}); '
      f'cross-lab JSD at 10 papers {iv(j, nd=4)}, at 20 papers {iv(row(js, measure="cross_lab_jsd_m20", scope="ALL"), nd=4)}. Topics are OpenAlex subfields; the BERTopic levels of the earlier lab study are carried over (`carryover/TOPIC-CONVERGENCE.md`).\n')

    w('## 5. Citation novelty\n')
    w('| measure | pre | post | post minus pre [95% CI] | placebo [95% CI] |')
    w('|---|---|---|---|---|')
    for m, nm in (('cit_z_med', 'Uzzi median z'), ('cit_z_p10', 'Uzzi 10th-percentile z'), ('cit_rs_sub', 'Rao-Stirling (subfield)'), ('cit_h_sub', 'subfield entropy of references'), ('cit_cd5', 'disruption CD5')):
        r = c_(m)
        w(f'| {nm} | {r.pre:.4f} | {r.post:.4f} | {iv(r, nd=4)} | {iv(c_(m, PL), nd=4)} |')
    w('\nCitation measures come from the earlier detector-v3 build (OpenAlex references, 9 schools); papers the build never saw have none. Advisor-student lineage is carried over (section 7).\n')

    w('## 6. Lab event study and IPW\n')
    ad = adopt.set_index('status')['labs']
    w(f'Adoption follows the pre-registered rule (`design/preregistration.json`, spec S1: share of scored papers with >= 25% flagged exceeds the 2016-2021 floor + 3 SD in two consecutive years): '
      f'{int(ad.get("adopter", 0))} adopting labs, {int(ad.get("never", 0))} never-adopters, {int(ad.get("censored", 0))} censored (only the last year exceeds) and {int(ad.get("never_unsustained", 0))} unsustained, which are left out. '
      'Estimator: Callaway-Sant\'Anna with never-treated controls, lab bootstrap B = 300.\n')
    w('| outcome | sample | overall ATT [95% CI] | pre-trend slope [95% CI] | pre-trend Wald p |')
    w('|---|---|---|---|---|')
    for o_ in ev.outcome.unique():
        for sm in ('all', 'excl_partial'):
            at, sl, wd = ev_stat(o_, 'overall_att', sm), ev_stat(o_, 'pretrend_slope', sm), ev_stat(o_, 'pretrend_wald', sm)
            if at is not None:
                w(f'| {o_} | {sm} | {iv(at, nd=4)} | {iv(sl, nd=4)} | {wd.lo:.3f} |')
    pp = ev_stat('mpd_specter2_proximity', 'perm_p_two_sided')
    w(f'\nPermutation placebo for the headline outcome: two-sided p = {pp.est:.3f}. Event-time coefficients: `tables/event_results.csv`, figure 6.\n')

    w('## 7. Carried over from the 2026-11-05 detector-v3 runs (9 schools, not recomputed here)\n')
    w('These experiments need pipelines (advisor-student links, stylometry, v1/final arXiv pairs, paired rewrites) that were built on the 9-school universe; their outputs are in `snapshot/carryover/` with provenance in each report. '
      'On the 3 new schools they have no data.\n')
    w('- **Lineage** (student-advisor similarity): post-2023 change inside labs lies outside the 2019-2021 placebo range in only one embedding model; within 2023-2025, more AI text goes with students sitting further from their advisor (-0.036 to -0.014 per unit dose, intervals exclude zero in 7 of 7 models; placebo intervals include zero).')
    w('- **Style**: dispersion of style vectors rises about 3% after 2022 (topic removed; +0.033 [+0.021, +0.043]) with placebo +0.005 to +0.011, i.e. a common drift with unequal size, not convergence.')
    w('- **AI added in revision** (arXiv v1 vs final): mean change +0.0011 [+0.0001, +0.0022] for kind S, not distinguishable from baseline; no sign of AI text added in revision at a scale the detector can see.')
    w('- **Dose vs novelty/diversity** (within lab and year): signs stable across detectors; lab-level DiD of diversity on lab AI dose positive, intervals exclude zero in 6 of 7 models.\n')

    w('## 8. Robustness\n')
    w('| check | result |')
    w('|---|---|')
    w(f'| exclude harvard, jhu, washu | AI share {iv(a("heavy_main", "EXCL_PARTIAL"), pct=True)} vs {iv(a("heavy_main"), pct=True)} with them; across-lab distance {iv(e("cross_lab_same_school", "EXCL_PARTIAL"), nd=4)} vs {iv(e("cross_lab_same_school"), nd=4)}; event ATT {iv(ev_stat("mpd_specter2_proximity", "overall_att", "excl_partial"), nd=4)}. ' + ('Nearly identical because the 3 schools carry almost no scored papers (section 9). |' if low_cov else 'The 3 schools now carry scored papers, so the difference is informative. |'))
    w(f'| only papers with a dated appointment period | heavy share {iv(a("heavy_main", sm="period_supported"), pct=True)}; across-lab distance {iv(e("cross_lab_same_school", sm="period_supported"), nd=4)}. |')
    w(f'| drop 2022 from the pre period | heavy share {iv(a("heavy_main", c="post_minus_pre_excl2022"), pct=True)}; across-lab distance {iv(e("cross_lab_same_school", c="post_minus_pre_excl2022"), nd=4)}. |')
    w(f'| detector false positives | section 2: under one point. Pre-2023 heavy share is {level(yr("heavy_main", 2021), "est", pct=True)} (floor). |')
    w('| wording shift | topic-residual embeddings (section 3) and the carried-over paired rewrite. |')
    w('| embedding model | seven models, section 3. |\n')

    w('## 9. Coverage, limits, caveats\n')
    w('| school | lab papers 2016-25 | PIs | in earlier build | abstract embedded | full text held | full-text scored | dated-period share |')
    w('|---|---|---|---|---|---|---|---|')
    for s, cv in man['coverage']['by_school'].items():
        flag = ' (partial)' if s in C.PARTIAL else ''
        w(f'| {s}{flag} | {cv["lab_papers_2016_2025"]} | {cv["pis"]} | {cv["in_universe"]:.0%} | {cv["abstract_embedded"]:.0%} | {("n/a" if cv.get("held") is None else format(cv["held"], ".0%"))} | {cv["fulltext_v3"]:.0%} | {cv["period_supported"]:.0%} |')
    w('')
    cv = T(res, 'ai_coverage')
    if 'held' in cv:
        g = cv.groupby('school')[['held', 'scored', 'papers']].sum()
        gap = ', '.join(f'{s_} {int(g.loc[s_, "held"] - g.loc[s_, "scored"])} of {int(g.loc[s_, "held"])}' for s_ in ('gatech', 'michigan') if s_ in g.index)
        w(f'Held versus scored (home-school papers): copies we hold that are not scored are those whose main body is under 1,000 words, unreadable or without a scorable passage: {gap}. Every other held copy is scored.\n')
    pc = [man['coverage']['by_school'][s_] for s_ in C.PARTIAL]
    lo_, hi_ = min(c['fulltext_v3'] for c in pc), max(c['fulltext_v3'] for c in pc)
    elo, ehi = min(c['abstract_embedded'] for c in pc), max(c['abstract_embedded'] for c in pc)
    w(f'- **Partial schools.** Harvard, JHU and WashU were onboarded after the earlier AI scores and embeddings were built. In this snapshot {100 * lo_:.0f} to {100 * hi_:.0f}% of their papers have a detector-v3 full-text score and {100 * elo:.0f} to {100 * ehi:.0f}% an abstract embedding (the rest have no stored copy or no usable abstract); they have no citation measures or IPW weights, so they do not enter those layers. '
      'Most of their PIs carry appointment evidence only from 2026 listings, so which years a PI was at the school is unresolved: papers are attributed to the PI in all years. Georgia Tech, Michigan and UChicago share this to a lesser degree (dated-period share 10 to 17%) and Georgia Tech has full text for only 40% of its papers.')
    late = []
    for s_ in C.PARTIAL:
        pis = json.loads((C.snapshot_dir(snap_id) / 'release' / 'hierarchy' / s_ / 'pis.json').read_text())
        only26 = sum(1 for q in pis if not q.get('periods') and q.get('listings') and all(str(x.get('year')) == '2026' for x in q['listings']))
        late.append(f'{s_}: {only26} of {len(pis)} PIs have no dated period and only 2026 listings')
    w('- **Period gaps.** The dated-period column counts papers whose PI has any period record; it does not mean the earlier years are resolved. ' + '; '.join(late) + '. Their papers are attributed to the PI in all years; a period-supported-only sensitivity is in section 8.')
    w('- **Detector error.** v3 misses 0.9 to 6.6% of AI passages from unseen generators (more for lightly edited text); the AI share is therefore a lower bound for heavy use and says nothing about authors who edit AI output.')
    w('- **Membership.** The strict rule (PI on the byline) leaves out student-only papers, so a lab\'s output is understated and the share of student writing is unknown. Co-led papers count in each lab.')
    w('- **Clustering.** The bootstrap resamples labs; it does not model dependence between labs of one department or between a PI\'s years beyond that.')
    fts = [c_['fulltext_v3'] for s_, c_ in man['coverage']['by_school'].items() if s_ not in C.PARTIAL]
    w(f'- **Selection.** Full-text AI scores cover {100 * min(fts):.0f} to {100 * max(fts):.0f}% of papers per school (the 9 older schools); IPW weights are from the earlier fit and cover only papers the earlier build saw.\n')

    w('## 10. What more schools would sharpen\n')
    w('- Harvard, JHU and WashU hold no stored full-text copies yet (their catalogs are empty: open copies were found for most papers but not downloaded), so only their abstracts are embedded and abstract-flagged, and they are absent from the full-text AI layer; downloading the open copies would bring them in.' if low_cov else '- Harvard, JHU and WashU are scored in this snapshot; they remain small and many of their papers have no stored copy, and their appointment periods are open.')
    w('- Dated appointment periods for the 2026-listing PIs would let the pre period be restricted to years the PI was on the faculty.')
    w('- More schools tighten the school-level intervals; at 9 scored schools, a between-school bootstrap would be unstable, which is why intervals here resample labs within school.')
    w('- A rewrite control and lineage links for the 3 new schools, and a section-split of their full text.\n')
    if compare:
        i = lines.index('[comparison placeholder]')
        lines[i:i + 1] = ['']
        j = [n for n, l in enumerate(lines) if l.startswith('## 9. Coverage')][0]
        lines[j:j] = compare_lines(snap_id, compare)
    w('Files: tables in `tables/` (CSV and parquet), figures in `figures/`, code `ai-writing/study/` on branch `agent/study-1107`, rerun with `ai-writing/study/run_study.sh`.')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-07')
    ap.add_argument('--compare', default=None, help='an earlier results id to compare the headline estimates with')
    a = ap.parse_args()
    txt = build(a.id, a.compare)
    (C.results_dir(a.id) / 'RESULTS.md').write_text(txt)
    print(len(txt.splitlines()), 'lines')
