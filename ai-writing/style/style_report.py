"""Step 3: STYLE-HOMOGENIZATION.md from the tables. usage: style_report.py [--out <file>]"""
import argparse
import json
import time

import pandas as pd

import style_common as S

T = S.RUN / 'tables'


def tab(df):
    cols = list(df.columns)
    return '\n'.join(['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)] + ['| ' + ' | '.join(str(v) for v in r) + ' |' for r in df.itertuples(index=False)])


def iv(r, e='effect', nd=4):
    return f"{r[e]:+.{nd}f} [{r['lo']:+.{nd}f}, {r['hi']:+.{nd}f}]"


def rd(name, kind):
    p = T / f'{name}_{kind}.csv'
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def effects_table(df, strat_col='stratum', space='resid', metrics=('disp', 'conv')):
    rows = []
    for st, g in df[df['space'] == space].groupby(strat_col):
        row = {strat_col: st}
        for mt in metrics:
            p = g[(g['metric'] == mt) & (g['design'] == 'post')]
            pl = g[(g['metric'] == mt) & g['design'].str.startswith('placebo')]
            if p.empty:
                continue
            r = p.iloc[0]
            row[f'{mt} post'] = f"{iv(r)} ({r['rel'] * 100:+.1f}%)"
            row[f'{mt} placebo range'] = f"{pl['effect'].min():+.4f} to {pl['effect'].max():+.4f}"
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(S.AIW / 'diversity' / 'reports' / 'STYLE-HOMOGENIZATION.md'))
    a = ap.parse_args()
    meta = {k: json.load(open(T / f'meta_{k}.json')) for k in ('abstract', 'fulltext') if (T / f'meta_{k}.json').exists()}
    md = ['# Do papers sound more alike? Writing-style homogenization, apart from topic\n',
          f"Generated {time.strftime('%Y-%m-%d', time.gmtime())} by `ai-writing/style/` (`style_features.py`, `style_extract.py`, `style_analyze.py`, `style_report.py`; tables in `{T}`). "
          "**Years 2016-2025 only (no 2026); post = 2023-2025, pre = 2016-2022.** Detector table: " + f"`{S.AI_TABLE.name}`. Full-text body: `{S.FT_DB.name}` = **today's stored body (Introduction to References, pdftotext, 60 pages); the section-split main body (`agent/fulltext-sections`) has not landed, so full-text numbers are on that body and will move when it does.**\n"]
    ab, ft = rd('corpus', 'abstract'), rd('corpus', 'fulltext')
    md.append('## Answer (plain language)\n')
    md.append('Bullets are generated from the tables; the closing reading is hand-written for the 2026-11-05 run.\n')
    for kind, df in (('abstract', ab), ('fulltext', ft)):
        if df.empty:
            continue
        for space in ('resid', 'raw'):
            g = df[df['space'] == space]
            p = {m: g[(g['metric'] == m) & (g['design'] == 'post')].iloc[0] for m in ('disp', 'conv')}
            pl = {m: g[(g['metric'] == m) & g['design'].str.startswith('placebo')]['effect'] for m in ('disp', 'conv')}
            md.append(f"- **{kind}, {'topic removed' if space == 'resid' else 'raw style'}:** dispersion of style vectors changes by {iv(p['disp'])} ({p['disp']['rel'] * 100:+.1f}% of its pre level) "
                      f"after 2022 (placebo breaks {pl['disp'].min():+.4f} to {pl['disp'].max():+.4f}); distance to the 2016-2021 corpus centroid {iv(p['conv'])} ({p['conv']['rel'] * 100:+.1f}%; placebo {pl['conv'].min():+.4f} to {pl['conv'].max():+.4f}).")
    ad = rd('ai_diff', 'abstract')
    if not ad.empty:
        for sp in ('resid', 'raw'):
            g = ad[(ad['space'] == sp) & (ad['metric'] == 'disp')]
            if len(g) == 2:
                p, q = g[g['design'] == 'post'].iloc[0], g[g['design'] == 'placebo2019-21'].iloc[0]
                md.append(f"- **AI link ({'topic removed' if sp == 'resid' else 'raw'}, abstracts):** detector-flagged papers of 2023-2025 have a dispersion {iv(p, 'diff')} ({p['rel'] * 100:+.1f}%) against not-flagged papers of the same year; "
                          f"the same contrast for 'flagged' papers of 2019-2021 (false positives, a placebo) is {iv(q, 'diff')}.")
    al = rd('allai', 'abstract')
    if not al.empty:
        g = al[(al['space'] == 'resid') & (al['metric'] == 'disp') & (al['design'] == 'post')].set_index('variant')
        lv = al[(al['space'] == 'resid') & (al['metric'] == 'disp') & (al['design'] == 'post')].set_index('variant')['pre_level']
        md.append(f"- **All-AI upper bound (abstracts, same papers):** rewriting every abstract lowers the pre-period dispersion from {lv['orig']:.3f} to {lv['allai']:.3f} ({(lv['allai'] / lv['orig'] - 1) * 100:+.1f}%), "
                  f"and its post change is {iv(g.loc['allai'])} against {iv(g.loc['orig'])} for the originals (gap {iv(g.loc['gap'])}).")
    md.append("\n**Reading (hand-written, 2026-11-05 run; recheck after a re-run).** Papers do not sound more alike across the corpus: after 2022 the spread of style vectors goes *up* by about 3% (topic removed), "
              "while the distance to the 2016-2021 centroid goes up by about 4.5%; both are several times the placebo breaks inside 2016-2021. The movement is a common drift (Kobak words +0.5 sd, longer words, higher MTLD, fewer `the`/`of`/`is`) of unequal size across papers, "
              "so the corpus spreads along that direction instead of collapsing. Uniformity shows only inside the AI-flagged group: flagged papers of 2023-2025 are about 6-7% less dispersed than unflagged papers of the same years, while the 2019-2021 'flagged' false positives are, if anything, more dispersed. "
              "The all-AI rewrite is the bound: AI wording alone is about 5% less dispersed than human wording and its dispersion grows only a third as much, so AI wording does not explain the corpus-wide rise in spread (content of the drift: the same words everywhere, adopted to different degrees). "
              "Lab level: labs with more flagged abstracts spread more after 2023 (slope +0.05 per unit, interval above zero), the placebo slope is about zero.\n")
    md.append('## Method\n')
    md.append("- **Features per text** (`style_features.py`): sentence length mean and standard deviation; MTLD (threshold 0.72, forward and backward; first 5,000 tokens; NaN under 50 tokens, those papers are dropped); mean word length and share of 7+ letter words; Flesch reading ease and Flesch-Kincaid grade; "
              "punctuation per 1,000 characters (comma, semicolon, colon, parenthesis, dash, quote, question mark, percent, slash); hedging words per 1,000 words; the Kobak et al. (2024) style-word rate (one feature among ~140); "
              "frequencies of 117 function words. **No POS n-gram profile: spaCy and its model are not in the study environment (the nltk tagger data are absent too), so it was skipped.**\n"
              "- **Space.** Each feature is z-scored on 2016-2022 papers and winsorized at 4 sd; the scalar block and the function-word block get equal total weight; Euclidean distance. **Topic removed (`resid`):** each feature is regressed (OLS, 2016-2022 papers) on OpenAlex subfield dummies "
              f"and 32 principal components of the abstract embedding ({list(meta.values())[0]['topic_model'] if meta else 'specter2_proximity'}); the residual is used. Fitting on the pre-period keeps the post-period shift out of the topic model. `raw` is the same without that step.\n"
              "- **Measures.** Per stratum and year, size-matched draws (1,000 papers for the corpus, 500 for full text, 150 for school/field strata with at least 300 papers a year, 20 per lab-period) from a bootstrap of the stratum's papers, 100 draws: "
              "dispersion = mean distance to the draw's centroid, mpd = mean pairwise distance (in the tables' `mpd` rows), convergence = mean distance to the 2016-2021 corpus centroid. Effect = mean of 2023-2025 minus mean of 2016-2022; placebo = the same inside 2016-2021 with breaks at 2019, 2020, 2021. "
              "Intervals are 2.5/97.5 percentiles over the draws. Lab level: labs with at least 20 papers in both periods, mean change across labs with a bootstrap over labs, and the slope of the change on the lab's post-period flagged share.\n"
              "- **AI link.** Flagged = `flag_abstract` (abstract detector) for abstracts, `ai_share >= 0.25` for full text; 60-paper draws per year; effect = flagged minus not-flagged, mean over 2023-2025; the placebo uses 2019-2021 (flagged there are false positives). Flagged and not-flagged are not matched on school or field; the topic-removed space handles content only.\n"
              "- **All-AI rewrite.** `allai/` (Qwen2.5-7B polish, 97,940 filter-kept abstracts); features of the rewrite use the original corpus's means and sds and the original paper's topic fit, so the comparison is on the same papers.\n")
    md.append('## 1. Which features moved (all papers, post 2023-2025 minus pre, in sd units of the 2016-2022 spread)\n')
    fs = rd('feature_shift', 'abstract')
    if not fs.empty:
        r = fs[fs['what'] == 'post_minus_pre_raw'].copy()
        r['abs'] = r['delta'].abs()
        rr = fs[fs['what'] == 'post_minus_pre_resid'].set_index('feature')
        sr = fs[fs['what'] == 'sd_ratio_post_over_pre'].set_index('feature')['delta']
        al_ = fs[fs['what'] == 'allai_minus_orig'].set_index('feature')['delta'] if (fs['what'] == 'allai_minus_orig').any() else None
        top = r.sort_values('abs', ascending=False).head(14)
        rows = [{'feature': x.feature, 'raw shift': f"{x.delta:+.3f} [{x.lo:+.3f}, {x.hi:+.3f}]", 'topic removed': f"{rr.loc[x.feature, 'delta']:+.3f}", 'sd post / pre': f"{sr[x.feature]:.2f}",
                 'rewrite shift': (f"{al_[x.feature]:+.3f}" if al_ is not None else '')} for x in top.itertuples()]
        md.append('Abstracts, the 14 largest shifts (of ~140 features); the last column is what an all-AI rewrite does to the same feature (original corpus, sd units).\n')
        md.append(tab(pd.DataFrame(rows)) + '\n')
    for kind in ('abstract', 'fulltext'):
        df = rd('corpus', kind)
        if df.empty:
            continue
        md.append(f'## 2. Dispersion and convergence, whole corpus: {kind}\n')
        md.append(f"{meta[kind]['papers']:,} papers with all features ({meta[kind]['pre']:,} pre, {meta[kind]['post']:,} post). Effect in style-space units (percent of the pre level in brackets).\n")
        for sp, label in (('resid', 'topic removed'), ('raw', 'raw')):
            t = df[df['space'] == sp]
            rows = []
            for dsg in ('post', 'placebo2019', 'placebo2020', 'placebo2021'):
                row = {'contrast': dsg}
                for mt in ('disp', 'mpd', 'conv'):
                    g = t[(t['design'] == dsg) & (t['metric'] == mt)]
                    if len(g):
                        row[mt] = f"{iv(g.iloc[0])} ({g.iloc[0]['rel'] * 100:+.1f}%)"
                rows.append(row)
            md.append(f'*{label}*\n')
            md.append(tab(pd.DataFrame(rows)) + '\n')
        sr = rd('corpus_series', kind)
        if len(sr):
            s2 = sr[sr['space'] == 'resid'][['year', 'disp', 'mpd', 'conv']].round(4)
            md.append('Yearly means (topic removed):\n')
            md.append(tab(s2) + '\n')
        for nm, lab in (('school', 'school'), ('field', 'OpenAlex field')):
            d = rd(nm, kind)
            if len(d):
                md.append(f'By {lab} ({kind}, topic removed; strata with fewer than 300 papers in some year are left out):\n')
                md.append(tab(effects_table(d)) + '\n')
    if not ad.empty:
        md.append('## 3. Detector-flagged against not-flagged papers (abstracts)\n')
        rows = []
        for r in ad.itertuples():
            rows.append({'space': r.space, 'contrast': r.design, 'years': r.years, 'metric': r.metric, 'flagged minus not': f"{r.diff:+.4f} [{r.lo:+.4f}, {r.hi:+.4f}]", 'relative': f"{r.rel * 100:+.1f}%"})
        md.append(tab(pd.DataFrame(rows)) + '\n')
        ft_ad = rd('ai_diff', 'fulltext')
        if len(ft_ad):
            md.append('Full text (flagged = at least a quarter of passages flagged):\n')
            md.append(tab(pd.DataFrame([{'space': r.space, 'contrast': r.design, 'years': r.years, 'metric': r.metric, 'flagged minus not': f"{r.diff:+.4f} [{r.lo:+.4f}, {r.hi:+.4f}]", 'relative': f"{r.rel * 100:+.1f}%"} for r in ft_ad.itertuples()])) + '\n')
    if not al.empty:
        md.append('## 4. All-AI rewrite: an upper bound on how uniform AI style makes papers\n')
        rows = []
        for r in al[al['design'].isin(['post'])].itertuples():
            rows.append({'space': r.space, 'variant': r.variant, 'metric': r.metric, 'pre level': f"{r.pre_level:.3f}", 'post - pre': f"{r.effect:+.4f} [{r.lo:+.4f}, {r.hi:+.4f}]"})
        md.append('Same 97,940 papers, original against all-AI wording; `gap` = original minus rewrite. Pre level of the gap = how much more dispersed the human wording is.\n')
        md.append(tab(pd.DataFrame(rows)) + '\n')
        s2 = rd('allai_series', 'abstract')
        s2 = s2[s2['space'] == 'resid'].pivot_table(index='year', columns='variant', values='disp').round(4).reset_index()
        md.append('Dispersion by year, topic removed:\n')
        md.append(tab(s2) + '\n')
    lab = rd('lab', 'abstract')
    if len(lab):
        md.append('## 5. Inside labs (abstracts)\n')
        md.append('Labs with at least 20 papers in both periods, 20-paper draws. `change` = mean over labs of (later period minus earlier); post = 2023-2025 minus 2016-2022; placebo2019 = 2019-2021 minus 2016-2018. `slope` = change per unit of the lab\'s later-period flagged-abstract share.\n')
        md.append(tab(pd.DataFrame([{'space': r.space, 'contrast': r.design, 'metric': r.metric, 'labs': r.labs, 'change': f"{r.change:+.4f} [{r.lo:+.4f}, {r.hi:+.4f}]", 'slope on dose': f"{r.dose_slope:+.3f} [{r.slope_lo:+.3f}, {r.slope_hi:+.3f}]"} for r in lab.itertuples()])) + '\n')
    md.append('## What changes with the final inputs\n')
    md.append("- **Final paper set (release 20261105i).** More or fewer papers per school-year; the features are recomputed for new abstracts and full texts only if you rerun `extract` after the texts DB is rebuilt (chunks are keyed by row offsets, so delete `RUN/parts` when the paper list changes). Strata thresholds (300 papers a year) decide which schools and fields appear.\n"
              "- **Detector v3.** Only the AI-link section (flagged vs not, lab slope) and the 0.25 full-text threshold depend on the detector: set `STYLE_AI` to the v3 table (columns `paper_id`, `ai_share`, `flag_abstract`). Dispersion, convergence and the all-AI bound do not use it.\n"
              "- **Main/appendix split (`agent/fulltext-sections`).** Point `STYLE_FULLTEXT_DB` at the texts DB holding the section-split main body (same `fulltext(paper_id, body, usable)` table); full-text features and every full-text number then follow. Today's body includes appendices and, with the extraction's 60-page cap, may include acknowledgements.\n"
              "- **POS profile.** Add it when spaCy `en_core_web_sm` is installed in the study environment (a new block in `style_features.py`).\n")
    md.append('## Re-running\n')
    md.append("```\ncd <code>/ai-writing/style\nexport STYLE_TAG=<release id>  [STYLE_AI=<detector parquet: v3>]  [STYLE_FULLTEXT_DB=<texts db with the section-split main body>]\n"
              "sbatch style.slurm extract abstract; sbatch style.slurm extract allai; sbatch style.slurm extract fulltext     # features, resumable, a few minutes\n"
              "sbatch style.slurm analyze abstract; sbatch style.slurm analyze fulltext\npython style_report.py\n```\nOne command: `ai-writing/style/run_all.sh`.\n")
    text = '\n'.join(md)
    open(a.out, 'w').write(text)
    S.C.log(wrote=a.out)


if __name__ == '__main__':
    main()
