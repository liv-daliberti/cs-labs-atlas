"""Step 3: LINEAGE.md from the effect tables. usage: lineage_report.py [--out <file>]   (default ai-writing/diversity/reports/LINEAGE.md of this checkout)"""
import argparse
import glob
import json
import time

import pandas as pd

import lineage_common as L

MEAS = {'sa': 'student-advisor similarity', 'cd': 'distance from lab centroid', 'ss': 'student-student similarity (lab-year)'}


def fmt(r, nd=4):
    if pd.isna(r['beta']):
        return 'n/a'
    return f"{r['beta']:+.{nd}f} [{r['lo']:+.{nd}f}, {r['hi']:+.{nd}f}]"


def table(df):
    cols = list(df.columns)
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    out += ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in df.itertuples(index=False)]
    return '\n'.join(out)


def _rng(x, nd=4):
    return f'{x.min():+.{nd}f} to {x.max():+.{nd}f}'


def answer(eff):
    ab = eff[(eff['kind'] == 'abstract') & (eff['group'] == 'all') & (eff['v'] == 'orig')]
    out = ['**Numbers below come from the tables of this report; each bullet is generated, so a re-run on new data rewrites them.**\n']
    for st, label in (('candidate', 'candidate links (the large sample)'), ('verified', 'verified links (the thin sample)')):
        for m, nm in (('sa', 'student-advisor similarity'), ('ss', 'student-student similarity')):
            d = ab[(ab['set'] == st) & (ab['m'] == m)]
            p = d[d['design'] == 'post'].set_index('model')
            pl = d[d['design'].str.startswith('placebo')].groupby('model')['beta'].agg(['min', 'max'])
            if p.empty:
                continue
            neg = int((p['hi'] < 0).sum())
            posi = int((p['lo'] > 0).sum())
            outside = int(((p['lo'] > pl['max'].reindex(p.index)) | (p['hi'] < pl['min'].reindex(p.index))).sum())
            out.append(f"- **{nm}, {label}, abstracts, {len(p)} models.** Post-2023 change inside labs {_rng(p['beta'])}; interval wholly below zero in {neg} models, wholly above in {posi}; "
                       f"placebo breaks (2019-2021) {_rng(pl[['min', 'max']].to_numpy())}; the post interval lies wholly outside the placebo range in {outside} of {len(p)} models.")
    d = ab[(ab['set'] == 'all') & (ab['m'] == 'sa')]
    for expo in ('ai_share', 'flag_abstract'):
        q = d[d['design'] == f'dose_post:{expo}']
        r = d[d['design'] == f'dose_pre:{expo}']
        if len(q):
            out.append(f"- **AI dose, student-advisor similarity, abstracts, exposure `{expo}`.** Among 2023-2025 papers the coefficient (0 to 1 exposure, lab and year fixed effects) is {_rng(q['beta'])} across {len(q)} models, "
                       f"interval excluding zero in {int(((q['lo'] > 0) | (q['hi'] < 0)).sum())}; the 2017-2021 placebo is {_rng(r['beta'])} with every interval including zero in {int(((r['lo'] <= 0) & (r['hi'] >= 0)).sum())} of {len(r)} models.")
    gp = eff[(eff['kind'] == 'abstract') & (eff['set'] == 'all') & (eff['group'] == 'all') & (eff['v'] == 'gap') & (eff['design'] == 'post')]
    if len(gp):
        og = eff[(eff['kind'] == 'abstract') & (eff['set'] == 'all') & (eff['group'] == 'all') & (eff['v'] == 'orig') & (eff['design'] == 'post')].set_index(['model', 'm'])['beta']
        share = gp.set_index(['model', 'm'])['beta'] / og.reindex(gp.set_index(['model', 'm']).index)
        out.append(f"- **Wording.** The post effect on the all-AI rewrites of the same papers is almost the same as on the originals: the gap (the part carried by wording) is {_rng(gp['beta'])} in cosine units "
                   f"(median |gap| / |effect| = {share.abs().median():.2f} over model x measure; ratios are unstable where the effect is near zero). Convergence or divergence that is there after rewriting is content, not wording.")
    out.append('- **Reading of the 2026-11-05 run (hand-written; check it against the bullets above after a re-run).** Students\' abstracts after 2023 are slightly less similar to their advisor\'s recent work and sit slightly further from the lab centroid in most models (not SPECTER2-base), but the pre-2022 trend runs the same way, '
               'so the post break is not distinguishable from the existing drift at the pooled level. What does stand out from the placebo is the dose: within 2023-2025, a student paper with more AI-flagged text sits further from the advisor, consistently across models, and about as strongly after rewriting (content, not wording). '
               'It is an association between papers of the same lab and year, not a causal effect: students who use AI may differ in topic or career stage.\n')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(L.AIW / 'diversity' / 'reports' / 'LINEAGE.md'))
    a = ap.parse_args()
    eff = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(L.RUN / 'effects_*.parquet')))], ignore_index=True)
    yr = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(L.RUN / 'yearly_*.parquet')))], ignore_index=True)
    cov = pd.read_csv(L.RUN / 'coverage.csv')
    build = json.load(open(L.RUN / 'build.json'))
    eff['m'] = eff['measure'].str.split(':').str[0]
    eff['v'] = eff['measure'].str.split(':').str[1]
    eff['b'] = eff.apply(fmt, axis=1)
    md = []
    md.append('# Advisor-student lineage: do students\' papers converge on their advisor\'s and on each other\'s?\n')
    md.append(f"Generated {time.strftime('%Y-%m-%d', time.gmtime())} by `ai-writing/lineage/` (`lineage_build.py`, `lineage_run.py`, `lineage_report.py`; tables in `{L.RUN}`). "
              f"Link snapshot: `{build['hier']}`, taken {build['snapshot_time']}; a release was rebuilding the packages at that time. Detector table: `{L.AI_TABLE.name}` (v1 abstract + v2 passage detector). "
              "**Years 2017-2025 only (no 2026); post = 2023-2025, 2022 dropped from the pre/post contrast as the transition year.**\n")
    abs_ = eff[eff['kind'] == 'abstract']
    sp = abs_[(abs_['set'] == 'all') & (abs_['group'] == 'all') & (abs_['design'] == 'post') & (abs_['v'] == 'orig')]
    md.append('## Answer (plain language)\n')
    md.append(answer(eff))
    md.append('## Method\n')
    md.append("- **Unit.** A (PI, student) pair. The student's papers are the links in `student_papers` (status `verified`; `candidate` links are reported separately, and `all` is both). "
              "The PI's papers are the strict lab papers (`lab_papers`: the PI is on the byline; the study-labs-are-strict rule). Only papers with an embedding are used.\n"
              "- **Student-advisor similarity (`sa`).** For a student paper of year t: the PI's lab papers of t-3..t-1, those the student co-authored removed (by linked work and by byline name), "
              f"the pool drawn down to {L.M_POOL} papers (size-matched, mean over {L.REPS} draws; pairs with fewer are dropped), then the mean cosine of the {L.K_NN} nearest. "
              "**Distance from the lab centroid (`cd`)** is 1 - cos(paper, centroid of the same pool). **Student-student similarity (`ss`)** is a lab-year measure: the mean pairwise cosine of 4 papers of 4 different students "
              "(distinct papers; 30 draws; labs with at least 4 students publishing that year).\n"
              "- **Estimator.** Lab fixed effect, Post = 2023-2025 against 2017-2021 (2022 dropped); each student has total weight 1 (weight 1 / number of the student's papers in the window), so prolific students do not dominate; "
              "interval = 2.5/97.5 percentiles of a cluster bootstrap over labs (1,000 draws). The lab-year `ss` table has equal lab-year weights. "
              "**Placebo:** the same contrast inside 2017-2021 with breaks at 2019, 2020 and 2021. **Dose:** within 2023-2025 (and, as placebo, within 2017-2021 where the dose is detector noise), "
              "the measure on the student paper's own `ai_share` (full-text passage share; scored papers only) or `flag_abstract` (abstract detector; all papers), with lab and year fixed effects "
              "(residuals computed once, the bootstrap reweights labs: a close approximation).\n"
              "- **Wording control.** The same measures on the all-AI rewritten abstracts (`<model>__allai`), both corpora restricted to the same papers and centred on that common set; "
              "the gap column is original minus all-AI, estimated as one regression of the difference, so its interval is exact for the paired design. A convergence that appears in the original and not in the rewrite is wording; "
              "one that survives in both is content.\n")
    md.append('## Coverage\n')
    c = cov[cov['status'].isin(['verified', 'candidate'])].copy()
    md.append('Student-paper links with a paper year of 2017-2025 and an embedded paper; `papers` are distinct papers.\n')
    md.append(table(c[['status', 'school', 'pairs', 'students', 'phd_students', 'labs', 'papers', 'links']]) + '\n')
    md.append(f"Verified links exist only for Princeton, CMU, EPFL and MIT; at the other five schools every link is a `candidate`. Pairs actually entering a measure are fewer (a student paper needs {L.M_POOL} PI papers in the previous 3 years): "
              "see the `n` and `n_students` columns of `effects_*.parquet`.\n")
    ns = abs_[(abs_['group'] == 'all') & (abs_['design'] == 'post') & (abs_['v'] == 'orig') & (abs_['m'] == 'sa') & (abs_['model'] == 'specter2_proximity')][['set', 'n', 'n_students', 'n_labs']]
    md.append('Papers (student-paper rows), students and labs in the Post contrast of `sa` (specter2_proximity abstracts):\n')
    md.append(table(ns) + '\n')

    def headline(kind, st, v='orig', designs=('post',)):
        d = eff[(eff['kind'] == kind) & (eff['set'] == st) & (eff['group'] == 'all') & (eff['v'] == v) & (eff['design'].isin(designs))]
        return d

    def models_table(kind, st):
        rows = []
        for model in sorted(eff[eff['kind'] == kind]['model'].unique()):
            row = {'model': model}
            for m in MEAS:
                dd = eff[(eff['kind'] == kind) & (eff['model'] == model) & (eff['set'] == st) & (eff['group'] == 'all') & (eff['m'] == m) & (eff['v'] == 'orig')]
                p = dd[dd['design'] == 'post']
                pl = dd[dd['design'].str.startswith('placebo')]['beta']
                if p.empty:
                    row[m + ' post'] = 'n/a'
                    continue
                row[m + ' post'] = p.iloc[0]['b']
                row[m + ' placebo range'] = f"{pl.min():+.4f} to {pl.max():+.4f}" if len(pl) else 'n/a'
                row[m + ' outside?'] = 'yes' if (p.iloc[0]['lo'] > pl.max() or p.iloc[0]['hi'] < pl.min()) else 'no'
            rows.append(row)
        return pd.DataFrame(rows)
    md.append('## 1. Pre/post 2023 inside labs, with placebo breaks\n')
    md.append('`sa` and `ss`: positive = more alike; `cd`: positive = further from the lab centroid. Post effect = 2023-2025 minus 2017-2021 within lab (cosine units). '
              '"placebo range" = the smallest and largest of the three placebo estimates (breaks 2019-2021 inside 2017-2021); "outside?" = the post interval lies wholly beyond that range.\n')
    for st, label in (('verified', 'Verified links'), ('candidate', 'Candidate links (reported separately)')):
        md.append(f'### Abstracts, {label}\n')
        md.append(table(models_table('abstract', st)) + '\n')
    md.append('### Full text, verified and candidate\n')
    for st in ('verified', 'candidate'):
        t = models_table('fulltext', st)
        if len(t):
            md.append(f'*{st}*\n')
            md.append(table(t) + '\n')
    md.append('## 2. Interaction with AI dose\n')
    md.append('Coefficient of the measure on the student paper\'s AI exposure, 0 to 1, with lab and year fixed effects. Post: papers of 2023-2025. Placebo: papers of 2017-2021 (exposure = detector noise). '
              'Verified and candidate links pooled (`all`) because the verified sample is thin; per-set tables are in `effects_*.parquet`.\n')
    rows = []
    for kind in ('abstract', 'fulltext'):
        for model in sorted(eff[eff['kind'] == kind]['model'].unique()):
            for m in ('sa', 'cd'):
                for expo in ('ai_share', 'flag_abstract'):
                    dd = eff[(eff['kind'] == kind) & (eff['model'] == model) & (eff['set'] == 'all') & (eff['group'] == 'all') & (eff['m'] == m) & (eff['v'] == 'orig')]
                    p, q = dd[dd['design'] == f'dose_post:{expo}'], dd[dd['design'] == f'dose_pre:{expo}']
                    if len(p) and len(q):
                        rows.append({'kind': kind, 'model': model, 'measure': m, 'exposure': expo, 'post (2023-25)': p.iloc[0]['b'], 'n': int(p.iloc[0]['n']), 'placebo (2017-21)': q.iloc[0]['b']})
    md.append(table(pd.DataFrame(rows)) + '\n')
    md.append('## 3. Wording control: original against all-AI rewritten abstracts\n')
    md.append('Post effect (all links) on the original abstracts, on the all-AI rewrites of the same papers, and the gap (original minus rewrite = the part carried by wording).\n')
    rows = []
    for model in sorted(abs_['model'].unique()):
        for m in MEAS:
            dd = abs_[(abs_['model'] == model) & (abs_['set'] == 'all') & (abs_['group'] == 'all') & (abs_['m'] == m) & (abs_['design'] == 'post')]
            g = {r.v: r.b for r in dd.itertuples()}
            if len(g) == 3:
                rows.append({'model': model, 'measure': m, 'original': g['orig'], 'all-AI': g['allai'], 'gap (wording)': g['gap']})
    md.append(table(pd.DataFrame(rows)) + '\n')
    md.append('Dose in 2023-2025 (coefficient on the abstract-flag exposure, `all` links), original, rewrite and gap:\n')
    rows = []
    for model in sorted(abs_['model'].unique()):
        for m in ('sa', 'cd'):
            for expo in ('flag_abstract', 'ai_share'):
                dd = abs_[(abs_['model'] == model) & (abs_['set'] == 'all') & (abs_['group'] == 'all') & (abs_['m'] == m) & (abs_['design'] == f'dose_post:{expo}')]
                g = {r.v: r.b for r in dd.itertuples()}
                if len(g) == 3:
                    rows.append({'model': model, 'measure': m, 'exposure': expo, 'original': g['orig'], 'all-AI': g['allai'], 'gap (wording)': g['gap']})
    md.append(table(pd.DataFrame(rows)) + '\n')
    md.append('## 4. By school and by student role\n')
    md.append('Post effect on `sa` (all links, original abstracts), per school and per role, for two models; groups with too few labs are n/a. PhD = students whose records list a PhD role; other = undergraduates, masters, postdocs, visitors and others with a stated role (unspecified roles left out).\n')
    rows = []
    for model in ('specter2_proximity', 'bge_m3'):
        for m in ('sa', 'cd'):
            dd = abs_[(abs_['model'] == model) & (abs_['set'] == 'all') & (abs_['m'] == m) & (abs_['v'] == 'orig') & (abs_['design'] == 'post') & (abs_['group'] != 'all')]
            for r in dd.itertuples():
                rows.append({'model': model, 'measure': m, 'group': r.group, 'post': r.b, 'n': int(r.n), 'students': r.n_students, 'labs': r.n_labs})
    md.append(table(pd.DataFrame(rows)) + '\n')
    md.append('## 5. Yearly means (specter2_proximity abstracts, student-weighted; all links)\n')
    y = yr[(yr['model'] == 'specter2_proximity') & (yr['kind'] == 'abstract') & (yr['set'] == 'all')].pivot_table(index='year', columns='measure', values='mean').round(4).reset_index()
    md.append(table(y) + '\n')
    md.append('Early years are composed differently (the PI history window is shorter in 2017-2018 and students are earlier in their career); the regressions use lab fixed effects, the raw means are descriptive.\n')
    md.append('## What changes with the final inputs\n')
    md.append("- **Final paper set (release 20261105i) and links.** Re-snapshot the hierarchy (`LINEAGE_HIER`), rebuild the universe and embeddings for new papers, then `run_all.sh`. The `verified` share is what matters: today only Princeton, CMU, EPFL and MIT have verified links, "
              "so the headline sample is small (1,085 students in the specter2_proximity Post contrast); every additional verified link tightens the intervals in section 1. Students without a role record stay `unspecified`.\n"
              "- **Detector v3.** Only section 2 (dose) and the `dose_*` rows depend on it: point `LINEAGE_AI` at the v3 table (`paper_id`, `ai_share`, `flag_abstract`). Sections 1, 3 (post effect) and 4 do not.\n"
              "- **Main/appendix split.** The full-text vectors are whole-body embeddings (the dose study's); when the section-split main body is embedded, rerun with the new containers (`MODELS_FT` in `lineage_common.py`); abstracts are unaffected.\n")
    md.append('## Re-running\n')
    md.append("```\n# paths: LINEAGE_HIER (a hierarchy snapshot or the live packages), LINEAGE_OUT, LINEAGE_TAG, LINEAGE_AI (detector table: v3 later)\n"
              "cd <code>/ai-writing/lineage\nexport LINEAGE_HIER=<snapshot dir or $CS_ATLAS_HIERARCHY> LINEAGE_TAG=<release id>\n"
              "python lineage_build.py                       # links (12 s)\nsbatch --array=0-12%6 lineage.slurm            # 13 (model, kind) tasks, ~3-10 min each\n"
              "python lineage_report.py                      # LINEAGE.md\n```\nOne command: `ai-writing/lineage/run_all.sh` (build, submit, wait with `tools/slurm_wait.py`, report).\n")
    open(a.out, 'w').write('\n'.join(md))
    L.log(wrote=a.out)


if __name__ == '__main__':
    main()
