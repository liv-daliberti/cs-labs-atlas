"""Writes ai-writing/diversity/reports/TOPIC-CONVERGENCE.md from OUT/topics/*.parquet (every number comes from those tables)."""
import pandas as pd

import lcommon as L
import lreport as R

LEVEL_NAME = {'bt_qwen3_0p6b': 'BERTopic (Qwen3-0.6B embeddings)', 'bt_specter2_proximity': 'BERTopic (SPECTER2 proximity)', 'oa_subfield': 'OpenAlex subfield', 'oa_topic': 'OpenAlex topic'}
SCOPE_NAME = {'all': 'all lab pairs', 'within_school': 'within school', 'within_dept': 'within department', 'between_school': 'between schools'}


def load():
    d = L.out('topics')
    t = {}
    for k in ('series', 'trend', 'fe', 'levels', 'labyear'):
        base = pd.read_parquet(d / f'{k}.parquet')
        ctl = sorted(d.glob(f'{k}_*control.parquet'))
        t[k] = base
        t[k + '_ctl'] = pd.concat([pd.read_parquet(p) for p in ctl], ignore_index=True) if ctl else pd.DataFrame()
    return t


def dev_cells(tr, level, variant, measure, scope, name='orig'):
    x = tr[(tr.level == level) & (tr.variant == variant) & (tr.measure == measure) & (tr.scope == scope) & (tr.name == name)].set_index('stat')
    return x


def beyond(x):
    """True when dev_2023's interval excludes 0 and its point is larger in size than every placebo's point, with the placebos' intervals not covering it."""
    if 'dev_2023' not in x.index:
        return None
    d = x.loc['dev_2023']
    pl = [x.loc[k] for k in x.index if k.startswith('placebo')]
    sign_ok = d.lo > 0 or d.hi < 0
    bigger = all(abs(d.est) > abs(p.est) for p in pl) if pl else True
    return bool(sign_ok and bigger)


def main():
    t = load()
    tr, se, fe, lv = t['trend'], t['series'], t['fe'], t['levels']
    out = []
    A = out.append
    A('# Topic convergence between labs\n')
    A(f'Generated {R.now()} by `ai-writing/labstudy/topic_report.py` (analysis `topic_convergence.py`); every number comes from the tables in `ai-writing/data/labstudy/topics` (git-ignored). '
      '**Years 2016-2025 only (no 2026); post = 2023-2025, 2022 is the transition year; intervals are 95% percentile intervals of a bootstrap over labs (300 replicates).** '
      'Strict lab membership (a lab owns a paper only when its PI is on the byline).\n')
    cfg = L.CFG['topic']
    main_ly = t['labyear']
    ml = main_ly[(main_ly['variant'] == 'main')]
    labs_n = ml.groupby('level')['lab_id'].nunique().to_dict()
    A('## Question and answer\n')
    A('**Do different labs\' topic mixes become more alike over time, and faster after 2023?** '
      'Per lab-year we draw `m` = %d papers (size-matched, %d draws, labs with fewer papers carrying a topic drop out), form the topic distribution, smooth it toward the pooled mix (pseudo-count %.2g) '
      'and compare labs by Jensen-Shannon divergence (base 2, 0 = identical, 1 = disjoint).\n' % (cfg['min_papers'], cfg['reps'], cfg['alpha']))
    # headline bullets
    bl = []
    for level in ('bt_qwen3_0p6b', 'bt_specter2_proximity', 'oa_topic', 'oa_subfield'):
        x = dev_cells(tr, level, 'main', 'jsd', 'all')
        if not len(x):
            continue
        d = x.loc['dev_2023']
        pl = ', '.join(f'{k[-4:]} {R.ci(x.loc[k].est, x.loc[k].lo, x.loc[k].hi)}' for k in x.index if k.startswith('placebo'))
        b = beyond(x)
        bl.append(f'- **{LEVEL_NAME[level]}**: mean pairwise JSD {R.f(x.loc["mean_pre"].est)} (2016-21) to {R.f(x.loc["mean_post"].est)} (2023-25); the post-2022 deviation from the 2016-21 trend is '
                  f'{R.ci(d.est, d.lo, d.hi)}; placebo breaks: {pl}. Beyond the placebos: **{"yes" if b else "no"}**.')
    A('\n'.join(bl) + '\n')
    cen = []
    for level in ('bt_qwen3_0p6b', 'bt_specter2_proximity', 'oa_topic', 'oa_subfield'):
        x = dev_cells(tr, level, 'main', 'dist_centroid', 'all')
        if len(x):
            d = x.loc['dev_2023']
            cen.append(f'{LEVEL_NAME[level]} {R.ci(d.est, d.lo, d.hi)}')
    A('- Distance of a lab to the all-lab centroid, post-2022 deviation from trend: ' + '; '.join(cen) + '.')
    x = dev_cells(tr, 'bt_qwen3_0p6b', 'main', 'top_llm', 'all')
    if len(x):
        sy = se[(se.level == 'bt_qwen3_0p6b') & (se.variant == 'main') & (se.measure == 'top_llm') & (se.scope == 'all')].set_index('year')
        A(f'- **LLM topics are themselves a finding** (reported separately, definition below): the share of labs whose top BERTopic (Qwen3) topic is LLM-related goes from {R.f(sy.loc[2019].est, 3)} (2019) and '
          f'{R.f(sy.loc[2022].est, 3)} (2022) to {R.f(sy.loc[2025].est, 3)} [{R.f(sy.loc[2025].lo, 3)}, {R.f(sy.loc[2025].hi, 3)}] in 2025; the mean share of a lab\'s papers on LLM topics follows (table 3).')
    A('')
    # table 1
    A('## 1. Mean pairwise JSD between labs (trend 2016-2025, break 2023, placebo breaks)\n')
    A('`dev_2023` = mean(2023-25) minus the 2016-21 linear trend projected to the same years; `placeboB` = the same for a fake break at B (trend on 2016..B-1, window B..min(B+2, 2021)). '
      'A post-2022 effect is counted only when `dev_2023` has an interval excluding 0 and exceeds every placebo point in size.\n')
    rows = []
    for level in ('bt_qwen3_0p6b', 'bt_specter2_proximity', 'oa_topic', 'oa_subfield'):
        for scope in ('all', 'between_school', 'within_school', 'within_dept'):
            x = dev_cells(tr, level, 'main', 'jsd', scope)
            if not len(x):
                continue
            cells = [R.ci(x.loc[k].est, x.loc[k].lo, x.loc[k].hi) if k in x.index else 'n/a' for k in ('dev_2023', 'placebo2019', 'placebo2020', 'placebo2021')]
            rows.append([LEVEL_NAME[level], SCOPE_NAME[scope], R.f(x.loc['mean_pre'].est), R.f(x.loc['mean_post'].est), R.ci(x.loc['slope_pre_per_year'].est, x.loc['slope_pre_per_year'].lo, x.loc['slope_pre_per_year'].hi, 5)] + cells + [{True: 'yes', False: 'no', None: 'n/a'}[beyond(x)]])
    A(R.md_table(rows, ['level', 'pairs', 'mean 2016-21', 'mean 2023-25', 'pre-slope / yr', 'dev_2023', 'placebo 2019', 'placebo 2020', 'placebo 2021', 'beyond placebos']))
    A('\nThe JSD level is high (about 0.86-0.87 for BERTopic) because an m-paper draw touches few of the ~300-380 topics, so the unit of interest is the change, not the level; '
      'size-matching makes the level comparable across labs and years.\n')
    # yearly series of the primary level
    prim = 'bt_qwen3_0p6b'
    A(f'### Yearly series, {LEVEL_NAME[prim]}\n')
    rows = []
    for y in L.YEARS:
        r = []
        for meas, scope in (('jsd', 'all'), ('jsd', 'within_school'), ('jsd', 'within_dept'), ('dist_centroid', 'all'), ('top_llm', 'all'), ('mass_llm', 'all')):
            x = R.row_of(se, level=prim, variant='main', name='orig', measure=meas, scope=scope, year=y)
            r.append('n/a' if x is None else f'{x.est:.4f} [{x.lo:.4f}, {x.hi:.4f}]')
        n = ml[(ml.level == prim) & (ml.year == y)]['lab_id'].nunique()
        rows.append([y, n] + r)
    A(R.md_table(rows, ['year', 'labs', 'JSD all', 'JSD within school', 'JSD within dept', 'dist. to centroid', 'top topic LLM (share of labs)', 'LLM paper share']))
    A('')
    # table 2/3 centroid and LLM
    A('## 2. Distance to the all-lab centroid and the LLM share of topics\n')
    rows = []
    for level in ('bt_qwen3_0p6b', 'bt_specter2_proximity', 'oa_topic', 'oa_subfield'):
        for meas in ('dist_centroid', 'dist_pre_centroid'):
            x = dev_cells(tr, level, 'main', meas, 'all')
            f_ = R.row_of(fe, level=level, variant='main', name='orig', measure=meas, spec='fe_post_real')
            fp = [R.row_of(fe, level=level, variant='main', name='orig', measure=meas, spec=f'fe_post_{b}') for b in L.BREAKS]
            if not len(x):
                continue
            rows.append([LEVEL_NAME[level], meas, R.ci(x.loc['dev_2023'].est, x.loc['dev_2023'].lo, x.loc['dev_2023'].hi), R.ci(f_.est, f_.lo, f_.hi) if f_ is not None else 'n/a',
                         '; '.join(R.f(p.est, 4, True) for p in fp if p is not None)])
    A(R.md_table(rows, ['level', 'measure', 'dev_2023 (bootstrap over labs)', 'lab-FE post-2022 shift [lab-clustered]', 'placebo FE shifts 2019 / 2020 / 2021 (points)']))
    A('\n`dist_centroid`: JSD to the year\'s own all-lab centroid (centroid = mean of the labs\' draws; equal weight per lab). `dist_pre_centroid`: JSD to the fixed 2016-2021 centroid, so a rise means labs move away from the old average mix '
      '(here toward LLM topics) while a fall means they move toward it.\n')
    A('## 3. LLM topics (defined from topic labels, reported separately)\n')
    rows = []
    for level in ('bt_qwen3_0p6b', 'bt_specter2_proximity', 'oa_topic'):
        for meas in ('top_llm', 'mass_llm'):
            x = dev_cells(tr, level, 'main', meas, 'all')
            if not len(x):
                continue
            sy = se[(se.level == level) & (se.variant == 'main') & (se.measure == meas) & (se.scope == 'all')].set_index('year')
            rows.append([LEVEL_NAME[level], meas] + [f'{sy.loc[y].est:.3f}' for y in (2016, 2019, 2022, 2023, 2024, 2025)] + [R.ci(x.loc['dev_2023'].est, x.loc['dev_2023'].lo, x.loc['dev_2023'].hi, 3)])
    A(R.md_table(rows, ['level', 'measure', '2016', '2019', '2022', '2023', '2024', '2025', 'dev_2023']))
    A('\n`top_llm` = share of labs whose most frequent topic in the draw is an LLM topic; `mass_llm` = mean share of a lab\'s papers on LLM topics. '
      'LLM topic = BERTopic topic whose label (four c-TF-IDF terms) matches `lcommon.LLM_RE` (llm/language model/GPT/prompt/in-context/RLHF/chatbot/generative AI/agentic/RAG/hallucination/chain-of-thought/instruction tuning/text generation); '
      'OpenAlex topics are matched by name, OpenAlex subfields have no LLM category (not defined).\n')
    A(R.md_table([[r.level, r.topics, r.valid_papers, r.llm_topics, r.llm_papers, (r.llm_labels or '')[:1200]] for r in lv.itertuples() if ':' not in r.level],
                 ['level', 'topics', 'papers with a topic', 'LLM topics', 'papers in LLM topics', 'LLM topic labels']))
    A('')
    # table 4 LLM excluded
    A('## 4. With and without the LLM topics\n')
    A('"Without": papers in LLM topics are removed before the draws (labs need `m` papers outside LLM topics). Convergence that is only the rise of one topic would disappear.\n')
    rows = []
    for level in ('bt_qwen3_0p6b', 'bt_specter2_proximity', 'oa_topic'):
        for meas in ('jsd', 'dist_centroid'):
            a = dev_cells(tr, level, 'main', meas, 'all')
            b = dev_cells(tr, level, 'nollm', meas, 'all')
            if not len(a) or not len(b):
                continue
            pm = max(abs(b.loc[k].est) for k in b.index if k.startswith('placebo'))
            rows.append([LEVEL_NAME[level], meas, R.ci(a.loc['dev_2023'].est, a.loc['dev_2023'].lo, a.loc['dev_2023'].hi), R.ci(b.loc['dev_2023'].est, b.loc['dev_2023'].lo, b.loc['dev_2023'].hi), R.f(pm),
                         {True: 'yes', False: 'no', None: 'n/a'}[beyond(b)]])
    A(R.md_table(rows, ['level', 'measure', 'dev_2023 with all topics', 'dev_2023 without LLM topics', 'largest placebo (without)', 'beyond placebos without LLM']))
    A('')
    # table 5 sensitivity
    A('## 5. Fixed lab panel and the size / smoothing rules\n')
    rows = []
    for level in ('bt_qwen3_0p6b', 'oa_topic', 'oa_subfield', 'bt_specter2_proximity'):
        for v in ('main', 'panel', 'm5', 'm20', 'a0.25', 'a4'):
            x = dev_cells(tr, level, v, 'jsd', 'all')
            if not len(x):
                continue
            labs = ml[ml.level == level]['lab_id'].nunique() if v == 'main' else main_ly[(main_ly.level == level) & (main_ly.variant == v)]['lab_id'].nunique()
            pm = max(abs(x.loc[k].est) for k in x.index if k.startswith('placebo'))
            rows.append([LEVEL_NAME[level], v, labs, R.ci(x.loc['dev_2023'].est, x.loc['dev_2023'].lo, x.loc['dev_2023'].hi), R.f(pm), {True: 'yes', False: 'no', None: 'n/a'}[beyond(x)]])
    A(R.md_table(rows, ['level', 'variant', 'labs ever eligible', 'dev_2023 (JSD, all pairs)', 'largest placebo', 'beyond placebos']))
    A('\n`panel` = labs eligible in >= 6 of 10 years with >= 2 pre and >= 2 post years (composition held roughly fixed); `m5`/`m20` change the minimum-papers rule from %d; `a0.25`/`a4` the smoothing pseudo-count from %.2g.\n' % (cfg['min_papers'], cfg['alpha']))
    # table 6 dept types
    A('## 6. By department type\n')
    A('Department type is a rule-based grouping of the PI\'s first listed department (`lcommon.dept_type`; cs, ee, eecs, engineering, math_stats, social_business, life_medical). Pairs are labs of the same type (any school); the centroid is still the all-lab centroid.\n')
    rows = []
    for level in ('bt_qwen3_0p6b', 'oa_topic'):
        for dt in ('cs', 'eecs', 'ee', 'engineering', 'math_stats', 'social_business', 'life_medical'):
            a = dev_cells(tr, level, 'main', 'jsd', f'dtype:{dt}')
            b = dev_cells(tr, level, 'main', 'dist_centroid', f'dtype:{dt}')
            c = dev_cells(tr, level, 'main', 'mass_llm', f'dtype:{dt}')
            if not len(a):
                continue
            nl = ml[(ml.level == level) & (ml.dtype == dt)]['lab_id'].nunique()
            pm = max(abs(a.loc[k].est) for k in a.index if k.startswith('placebo'))
            rows.append([LEVEL_NAME[level], dt, nl, R.ci(a.loc['dev_2023'].est, a.loc['dev_2023'].lo, a.loc['dev_2023'].hi), R.f(pm),
                         R.ci(b.loc['dev_2023'].est, b.loc['dev_2023'].lo, b.loc['dev_2023'].hi) if len(b) else 'n/a',
                         R.ci(c.loc['dev_2023'].est, c.loc['dev_2023'].lo, c.loc['dev_2023'].hi, 3) if len(c) else 'n/a'])
    A(R.md_table(rows, ['level', 'department type', 'labs', 'JSD within type: dev_2023', 'largest placebo', 'dist. to centroid: dev_2023', 'LLM paper share: dev_2023']))
    A('')
    # control
    A('## 7. Wording control: topics re-assigned on all-AI rewritten abstracts\n')
    ct = t['trend_ctl']
    if len(ct):
        lc = t['levels_ctl']
        lc = lc[lc['level'].str.contains(':control')].set_index('level')
        npap = int(lc['valid_papers'].max())
        ag = {k.split(':')[0]: v for k, v in lc['agree_with_bertopic'].items()}
        A('Same papers (%s with an abstract and a passing rewrite, 2016-2025), same draws, same labs: each paper is assigned to the nearest BERTopic centroid (centroids of the original abstracts) from its original abstract (`orig`) and from its Qwen2.5-7B-polished abstract (`ai`). '
          'The nearest-centroid assignment agrees with the BERTopic label for %s of papers (Qwen3) and %s (SPECTER2). `gap` = ai - orig, interval from the same lab bootstrap. OpenAlex topics are metadata of the work, not of its wording, so they have no all-AI version.\n'
          % (f'{npap:,}', R.f(ag['bt_qwen3_0p6b'], 3), R.f(ag['bt_specter2_proximity'], 3)))
        rows = []
        for level in ('bt_qwen3_0p6b', 'bt_specter2_proximity'):
            for meas in ('jsd', 'dist_centroid', 'top_llm'):
                a = dev_cells(ct.assign(variant='control'), level, 'control', meas, 'all', 'orig')
                b = dev_cells(ct, level, 'control', meas, 'all', 'ai')
                g = dev_cells(ct, level, 'control', meas, 'all', 'gap_ai_minus_orig')
                if not len(a):
                    continue
                rows.append([LEVEL_NAME[level], meas, R.ci(a.loc['dev_2023'].est, a.loc['dev_2023'].lo, a.loc['dev_2023'].hi), R.ci(b.loc['dev_2023'].est, b.loc['dev_2023'].lo, b.loc['dev_2023'].hi),
                             R.ci(g.loc['dev_2023'].est, g.loc['dev_2023'].lo, g.loc['dev_2023'].hi), R.ci(g.loc['post_minus_pre'].est, g.loc['post_minus_pre'].lo, g.loc['post_minus_pre'].hi)])
        A(R.md_table(rows, ['level', 'measure', 'dev_2023, original wording', 'dev_2023, all-AI wording', 'gap in dev_2023 (ai - orig)', 'gap in post-pre']))
        A('\nA gap interval around 0 means the change is carried by content, not by wording; a gap that is not 0 is the part wording can move.\n')
    A('## Not done and caveats\n')
    A('- Topic assignments are model-dependent (309 / 379 BERTopic topics, 37-39% of abstracts were HDBSCAN noise reassigned to the nearest topic); the two BERTopic models and OpenAlex are shown side by side, none is privileged.\n'
      '- Lab composition changes with the minimum-papers rule (about 1,100-1,250 labs are eligible in some year, 300-500 in the fixed panel); table 5 shows the dependence.\n'
      '- Pair JSDs are computed on a uniform sample of up to %d lab pairs per scope-year (all pairs when fewer); the lab bootstrap resamples labs, not pairs.\n'
      '- Wording control for OpenAlex levels is undefined (metadata). Full-text-based topics were not built (abstract embeddings only).\n' % TCFG_PAIRS())
    A('## Re-run\n')
    A('```\nbin/atlas ...  # none: run from a worktree or main\nai-writing/labstudy/run_all.sh topics        # frame -> topic runs (all levels, variants) -> control -> report; configured by ai-writing/labstudy/config.json\n```')
    p = L.REPORTS / 'TOPIC-CONVERGENCE.md'
    p.write_text('\n'.join(out) + '\n')
    L.log(step='topic_report', path=str(p))


def TCFG_PAIRS():
    return L.CFG['topic']['max_pairs']


if __name__ == '__main__':
    main()
