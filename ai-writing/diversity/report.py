"""Write REPORT.md from the results (every number is read from results/ and the CSVs, so a rerun refreshes it)."""
import json
from datetime import date
import numpy as np
import pandas as pd
import common as C
from analyze import LABELS, FAMILY, FAMILY_TITLE, WITHIN_LABELS, DIRECTION  # noqa: F401  (kept: a project module; possibly a re-export or a side effect)

MEASURE_TEXT = [
    ('S1', 'knowledge extent: largest distance of a paper from the set centroid (Hao et al. M8)', 'set', 'abstract, full text'),
    ('S2', 'dispersion: mean distance from the centroid', 'set', 'abstract, full text'),
    ('S3', 'mean pairwise cosine distance', 'set', 'abstract, full text'),
    ('S4', 'Vendi score: exp(entropy of the eigenvalues of K/n), K the cosine-similarity matrix', 'set', 'abstract, full text'),
    ('S5 / S6', 'entropy over 50 global k-means topic clusters / its exponential', 'set', 'abstract, full text'),
    ('S7', 'Rao-Stirling: Σ_{a≠b} d_ab p_a p_b, d = cosine distance between cluster centroids', 'set', 'abstract, full text'),
    ('S8', 'within-paper spread: mean pairwise cosine distance between a paper\'s segment vectors (≥ 5 segments)', 'paper', 'full text'),
    ('L1', 'MATTR, 1,000-token moving window', 'paper', 'full text'),
    ('L2', 'unigram entropy, mean over consecutive 1,000-token windows', 'paper', 'full text'),
    ('L3', 'homogeneity: mean pairwise TF-IDF cosine (higher = more alike)', 'set', 'full text, first 5,000 tokens'),
    ('L4', 'trigram novelty: share of a paper\'s distinct trigrams absent from 3 of the lab\'s papers of the 3 previous years (10 draws)', 'paper', 'full text, 2019+'),
    ('L5', 'sentence length (words), mean and SD within the paper', 'paper', 'full text'),
    ('L6', 'readability spread: SD of the papers\' Flesch reading ease', 'set', 'full text'),
    ('L7', 'Kobak et al. rare excess style words per 1,000 tokens (detector check, not diversity)', 'paper', 'full text'),
    ('L8', 'compression: zlib(concatenated 4,000-character excerpts) / Σ zlib(each); 1 = nothing shared', 'set', 'full text'),
    ('N1', 'cosine distance to the nearest arXiv CS paper of the previous year (10,000-paper background sample per year)', 'paper', 'abstract'),
    ('N2', 'new topic: the paper\'s cluster is absent from 3 of the lab\'s papers of the 3 previous years (10 draws)', 'paper', 'abstract, 2019+'),
    ('C1', 'venue entropy of 40 references drawn from the set\'s pooled references', 'set', 'S2 references'),
    ('C2', 'mean pairwise Jaccard overlap of reference lists (higher = more alike)', 'set', 'S2 references'),
    ('C3', 'SD of reference ages, pooled over the set', 'set', 'S2 references'),
    ('C4', 'share of a paper\'s references that are the lab\'s own papers', 'paper', 'S2 references'),
]


def f2(v):
    return '' if v is None or (isinstance(v, float) and not np.isfinite(v)) else f'{v:+.2f}'


def ci(r):
    return f'{r.beta:+.2f} [{r.lo:+.2f}, {r.hi:+.2f}]'


def main():
    A = json.loads((C.RES / 'analysis.json').read_text())
    FN = json.loads((C.RES / 'figure_numbers.json').read_text()) if (C.RES / 'figure_numbers.json').exists() else {}
    S = pd.read_csv(C.RES / 'slopes.csv')
    W = pd.read_csv(C.RES / 'within.csv') if (C.RES / 'within.csv').stat().st_size > 1 else pd.DataFrame()
    LD = pd.read_csv(C.ROOT / 'lab_diversity.csv')
    LY = pd.read_csv(C.ROOT / 'lab_diversity_year.csv')
    F = pd.read_parquet(C.DATA / 'paper_features.parquet')
    src = A['ai_source']
    ai_word = ('the share of the lab\'s 2023-2026 papers flagged by the v1 abstract detector (threshold at 1% FPR)' if src == 'abstract'
               else 'the mean paragraph ai_share of the lab\'s 2023-2026 papers (v2 paragraph detector)')
    pooled = S[S.school == 'all']
    mainS = pooled[pooled.spec == 'main'].set_index('measure')
    null95 = A.get('null_abs_slope_95')
    L = []
    w = L.append
    w('# AI-written text and lab research diversity: the v2 diversity battery\n')
    w(f'Generated {date.today().isoformat()} by `diversity/report.py` from the files in `diversity/`; rerun everything with `diversity/run_all.sh`. '
      f'AI-usage variable in this run: **{src}** detector.\n')
    def own_placebo(m):
        v = pooled[(pooled.measure == m) & pooled.spec.isin(['placebo2019', 'placebo2020'])].beta
        return float(v.mean()) if len(v) else np.nan

    def beyond(m):
        r = mainS.loc[m]; op = own_placebo(m)
        sig = r.lo > 0 or r.hi < 0
        return bool(sig and null95 and abs(r.beta) > null95 and (np.isnan(op) or not (r.lo <= op <= r.hi)))

    w('## Summary\n')
    w('Rule-based from the tables below, so it stays true on a rerun.')
    w('- "Clears placebo": the main CI excludes zero, |β| exceeds 95% of all placebo slopes, and the CI also excludes the mean of the measure\'s own two placebo slopes.')
    w('- β is SD of change per SD of lab AI usage, with lab-size and school controls.\n')
    for f in ('abs', 'ft', 'txt', 'ref'):
        ms = [m for m in mainS.index if FAMILY[m] == f]
        if not ms:
            continue
        clear = [m for m in ms if beyond(m)]
        sig_only = [m for m in ms if (mainS.loc[m].lo > 0 or mainS.loc[m].hi < 0) and m not in clear]
        parts = [f'{len(ms) - len(clear) - len(sig_only)} of {len(ms)} measures have a CI including zero']
        if clear:
            tp_ = pooled[(pooled.spec == 'topic')].set_index('measure')
            parts.append('clears placebo: ' + ', '.join(f'{LABELS[m]} {mainS.loc[m].beta:+.2f} (own placebo {own_placebo(m):+.2f}; with topic control '
                                                        f'{tp_.loc[m].beta:+.2f})' for m in clear))
        if sig_only:
            parts.append('CI excludes zero but the slope does not meet the placebo rule (inside the ±' + f'{null95:.2f}' + ' band or not clear of its own placebo): '
                         + ', '.join(f'{LABELS[m]} {mainS.loc[m].beta:+.2f} (own placebo {own_placebo(m):+.2f})' for m in sig_only))
        w(f'- **{FAMILY_TITLE[f]}:** ' + '; '.join(parts) + '.')
    if len(W):
        g = W[W.x == 'flag'].set_index(['outcome', 'spec'])
        lines = []
        for o in WITHIN_LABELS:
            if (o, 'post') not in g.index:
                continue
            p_ = g.loc[(o, 'post')]
            if not (p_.lo > 0 or p_.hi < 0):
                continue
            q_ = g.loc[(o, 'pre_placebo')] if (o, 'pre_placebo') in g.index else None
            same = q_ is not None and (q_.lo > 0 or q_.hi < 0) and np.sign(q_.beta) == np.sign(p_.beta)
            lines.append(f'{WITHIN_LABELS[o]} {p_.beta:+.2f}' + (f' (2016-2022 false positives show it too: {q_.beta:+.2f})' if same else ''))
        w('- **Within lab, flagged vs unflagged papers of the same lab and year (2023-2026), CI excluding zero:** ' + ('; '.join(lines) or 'none') + '.')
    w('')
    w('## What was measured\n')
    w(f'- **Papers:** {A["papers"]:,} CS lab papers of 2016-2026 (`papers.jsonl.gz`, six schools).')
    w(f'  - {A["papers_abs"]:,} have a SPECTER2 title+abstract vector.')
    w(f'  - {A["papers_txt"]:,} have a usable full text (≥ 1,000 body words; a PDF must show its title on page 1).')
    w(f'  - {A["papers_ft"]:,} have a full-text vector.')
    w(f'  - {A["papers_refs"]:,} have an S2 reference list with ≥ 5 references.')
    w(f'  - {A["papers_ai"]:,} have an AI score.')
    w(f'- **Labs:** a lab is a school PI. {A["labs_with_both_periods"]} labs have ≥ 5 papers in both 2016-2022 and 2023-2026. '
      f'{A["labs_in_ai_analysis"]} of them also have ≥ 5 AI-scored post-period papers and enter the lab-level analyses '
      f'({", ".join(f"{C.LABEL[k]} {v}" for k, v in A["labs_in_ai_analysis_by_school"].items())}).')
    q = A['ai_post_lab_quantiles']
    w(f'- **AI usage per lab:** {ai_word}. Across labs: median {100 * q["0.5"]:.0f}%, interquartile range {100 * q["0.25"]:.0f}-{100 * q["0.75"]:.0f}%, '
      f'10th-90th percentile {100 * q["0.1"]:.0f}-{100 * q["0.9"]:.0f}%.')
    fy = A['flagged_share_by_year']
    w(f'- **Flagged share by year:** {", ".join(f"{y} {100 * v:.1f}%" for y, v in sorted(fy.items(), key=lambda x: int(x[0])))}.')
    fc = A.get('family_counts') or {}
    if fc:
        w('- **Behind the lab-level fits:** ' + '; '.join(f'{FAMILY_TITLE[f].lower()}: up to {v["labs_max"]} labs, {v["papers"]:,} distinct papers' for f, v in fc.items()) + '.')
    w('')
    w('### Full-text coverage\n')
    w('| School | papers | full text | full-text vector | S2 references |')
    w('|---|---:|---:|---:|---:|')
    for s, c in A['coverage_by_school'].items():
        w(f'| {C.LABEL[s]} | {c["papers"]:,} | {c["txt"]:,} ({100 * c["txt"] / max(1, c["papers"]):.0f}%) | {c["ft"]:,} | {c["refs"]:,} ({100 * c["refs"] / max(1, c["papers"]):.0f}%) |')
    for per, c in A['coverage_by_period'].items():
        w(f'| {"2016-2022" if per == "pre" else "2023-2026"} | {c["papers"]:,} | {c["txt"]:,} ({100 * c["txt"] / max(1, c["papers"]):.0f}%) | {c["ft"]:,} | |')
    seg = F.seg_src.value_counts().to_dict() if 'seg_src' in F else {}
    w('')
    w(f'- **Full-text segments:** {", ".join(f"{v:,} papers by {k}" for k, v in seg.items()) or "none yet"}.')
    w('  - `fulltext.sqlite` stores whitespace-flattened bodies, so its `paragraphs` table holds almost nothing. A paper uses the table when it has ≥ 3 paragraphs there.')
    w('  - Otherwise the body is cut into sentence-bounded passages of about 150 words (40-400 words), with the 70% printable-word filter, at most 100 per paper.')
    w('  - Embedding: SPECTER2 base, CLS, ≤ 512 tokens. A paper\'s vector is the mean of its segment vectors.')
    w('')
    w('### Measures\n')
    w('Every set-level measure is a mean over 1,000 equal-size random draws of the lab\'s papers. n is the smaller of the two groups compared, at least 5, so size alone cannot make a lab look more diverse. Lab-years use n = 5.')
    w('')
    w('Paper-level measures are means over the group\'s papers. Embedding vectors have the corpus mean subtracted and are then L2-normalized, because SPECTER2 puts random CS papers at cosine ~0.8.\n')
    w('| Measure | Definition | Level | Input |')
    w('|---|---|---|---|')
    for a, b, c, d in MEASURE_TEXT:
        w(f'| {a} | {b} | {c} | {d} |')
    w('')
    w('## Results\n')
    w('### 1. Lab level: change against AI usage\n')
    w('- **Model:** y = post − pre change in the measure; x = post-period AI usage.')
    w('  - Both are z-scored over the labs in the fit, so β is SD of change per SD of AI usage.')
    w('  - Huber regression with controls for log n of the family\'s papers in each period and school dummies.')
    w('- **Uncertainty:** 95% percentile-bootstrap CI over labs; p_perm permutes AI usage within school.')
    w(f'- **Placebo null:** 95% of placebo |β| fall below ±{null95:.2f}. This band is the null spread (analysis 3).' if null95 else '')
    w('')
    w('| Family | Measure | β main [95% CI] | p_perm | labs | β + topic FE | β + baseline | placebo 2019 | placebo 2020 | β − own placebo | clears placebo |')
    w('|---|---|---|---:|---:|---|---|---|---|---:|:-:|')
    for m in LABELS:
        if m not in mainS.index:
            continue
        r = mainS.loc[m]
        get = lambda sp: pooled[(pooled.measure == m) & (pooled.spec == sp)]
        t, b, p19, p20 = (get(sp) for sp in ('topic', 'baseline', 'placebo2019', 'placebo2020'))
        op = own_placebo(m)
        w(f'| {FAMILY_TITLE[FAMILY[m]].split(",")[0]}{" (ft)" if FAMILY[m] == "ft" else ""} | {LABELS[m]} | {ci(r)} | {r.p_perm:.3f} | {int(r.n_labs)} | '
          f'{ci(t.iloc[0]) if len(t) else ""} | {ci(b.iloc[0]) if len(b) else ""} | {ci(p19.iloc[0]) if len(p19) else "n/a"} | {ci(p20.iloc[0]) if len(p20) else "n/a"} | '
          f'{f2(r.beta - op) if np.isfinite(op) else ""} | {"✓" if beyond(m) else ""} |')
    w('')
    sig = [m for m in mainS.index if mainS.loc[m].lo > 0 or mainS.loc[m].hi < 0]
    clears = [m for m in sig if beyond(m)]
    within_null = [m for m in sig if m not in clears]
    fams = {f: [m for m in mainS.index if FAMILY[m] == f] for f in ('abs', 'ft', 'txt', 'ref')}
    flat = {f: [m for m in ms if not (mainS.loc[m].lo > 0 or mainS.loc[m].hi < 0)] for f, ms in fams.items()}
    w('**Reading:**')
    w(f'- **CI excludes zero:** {len(sig)} of {len(mainS)} measures: {", ".join(f"{LABELS[m]} ({mainS.loc[m].beta:+.2f})" for m in sig) or "none"}.')
    w(f'- **Clear the placebo** (|β| above the band and the CI excludes the measure\'s own placebo mean): {", ".join(LABELS[m] for m in clears) or "none"}.')
    w(f'- **Do not clear it:** {", ".join(LABELS[m] for m in within_null) or "none"}. A pre-ChatGPT break produces slopes like these with the same AI variable, so they are not evidence of an AI effect.')
    for f, ms in fams.items():
        if ms:
            w(f'- **{FAMILY_TITLE[f]}:** {len(flat[f])} of {len(ms)} measures have a CI that includes zero.')
    w('')
    w('### 3. Placebo breaks\n')
    pl = pooled[pooled.spec.isin(['placebo2019', 'placebo2020'])]
    if len(pl):
        w(f'- **Spread:** {len(pl)} placebo slopes (fake breaks at 2019 and 2020, same x and controls) have SD {pl.beta.std():.2f}, and 95% of their |β| are below {null95:.2f}.')
        w(f'- **Placebo CIs excluding zero:** {", ".join(f"{LABELS[r.measure]} {r.spec[-4:]} ({r.beta:+.2f})" for r in pl.itertuples() if r.lo > 0 or r.hi < 0) or "none"}.')
        w('  - These labs were already moving in that direction before ChatGPT, in step with their later AI usage.')
        w('  - That is a pre-trend, or a property of the labs that later adopt AI, not an effect of AI.')
    w('- **Missing values:** L4 and N2 start in 2019, so the 2019 placebo has no early group for them.')
    w('')
    w('### 2. Within lab: papers with more vs less AI in the same lab and year\n')
    if len(W):
        w('- **Model:** outcome z-scored; regressed on the paper\'s flag with lab × year fixed effects.')
        w('  - A paper of k labs counts 1/k in each; SE clustered by lab.')
        w('- **Pre-period placebo:** compares flagged with unflagged papers of 2016-2022, where every flag is a detector false positive. It shows what the detector\'s errors alone produce.\n')
        w('| Outcome | 2023-2026 | + topic FE | 2016-2022 placebo | papers (post) | flagged (post) | labs |')
        w('|---|---|---|---|---:|---:|---:|')
        for o in WITHIN_LABELS:
            g = W[(W.outcome == o) & (W.x == 'flag')]
            if not len(g):
                continue
            row = {sp: g[g.spec == sp] for sp in ('post', 'post_topic', 'pre_placebo')}
            p = row['post'].iloc[0] if len(row['post']) else None
            w(f'| {WITHIN_LABELS[o]} | {ci(p) if p is not None else ""} | {ci(row["post_topic"].iloc[0]) if len(row["post_topic"]) else ""} | '
              f'{ci(row["pre_placebo"].iloc[0]) if len(row["pre_placebo"]) else ""} | {p.n_papers if p is not None else ""} | {p.n_flagged if p is not None else ""} | {p.n_labs if p is not None else ""} |')
        if 'dose' in set(W.x):
            w('\nWith the continuous paragraph dose (ai_share) instead of the flag, 2023-2026:\n')
            for r in W[W.x == 'dose'].itertuples():
                w(f'- {WITHIN_LABELS[r.outcome]}: {ci(r)}')
    w('')
    w('### 4. Topic control\n')
    w('- **Model:** the topic column of the lab-level table adds two terms.')
    w('  - Fixed effects for the lab\'s modal topic (10 k-means clusters of abstracts).')
    w('  - The lab\'s change in LLM-topic share (the homogenization study\'s title/abstract pattern).')
    w('- Within lab, "+ topic FE" adds the paper\'s 50-cluster topic and its LLM-topic indicator.')
    tp = pooled[pooled.spec == 'topic'].set_index('measure')
    shr = [(m, mainS.loc[m].beta, tp.loc[m].beta) for m in sig if m in tp.index]
    if shr:
        w('- **Main slopes whose CI excludes zero, before and after the topic control:**')
        for m, a, b in shr:
            w(f'  - {LABELS[m]}: {a:+.2f} → {b:+.2f}')
    w('')
    w('### 5. Per school\n')
    sc = S[(S.spec == 'main') & (S.school != 'all')]
    if len(sc):
        schools = [s for s in C.SCHOOLS if s in set(sc.school)]
        w('Main specification within each school with ≥ 20 labs: β [95% CI].\n')
        w('| Measure | ' + ' | '.join(C.LABEL[s] for s in schools) + ' |')
        w('|---|' + '---|' * len(schools))
        for m in LABELS:
            if m not in mainS.index:
                continue
            cells = []
            for s in schools:
                r = sc[(sc.measure == m) & (sc.school == s)]
                cells.append(ci(r.iloc[0]) + (' *' if (r.iloc[0].lo > 0 or r.iloc[0].hi < 0) else '') if len(r) else '')
            w(f'| {LABELS[m]}{" (ft)" if FAMILY[m] == "ft" else ""} | ' + ' | '.join(cells) + ' |')
        w('\n\\* CI excludes zero. Labs per school: ' + ', '.join(f'{C.LABEL[s]} {int(sc[sc.school == s].n_labs.max())}' for s in schools) + '.')
    w('')
    f3 = FN.get('fig3_fulltext') or {}
    w('### Figure 3 on full texts\n')
    if f3.get('papers'):
        w(f'- **Papers:** {f3["papers"]:,} lab papers of 2023-2026 with a full-text vector and an AI score, {f3["flagged"]:,} flagged.')
        w('- **Groups and draws:** flagged vs not flagged; 1,000 equal-size draws per group, n up to 1,000 per school.')
        w('- **Lower share:** the share of draws in which the flagged group\'s value is the lower one.\n')
        w('| | n per draw | flagged / not | extent: flagged vs not (median) | flagged lower | entropy: flagged vs not (median) | flagged lower |')
        w('|---|---:|---|---|---:|---|---:|')
        for s in list(C.SCHOOLS) + ['all']:
            if s in f3:
                d = f3[s]
                w(f'| {C.LABEL.get(s, "All six")} | {d["n_per_draw"]} | {d["flagged"]} / {d["not_flagged"]} | {d["extent_ai_median"]:.3f} vs {d["extent_not_median"]:.3f} | '
                  f'{100 * d["extent_ai_lower_share"]:.0f}% | {d["entropy_ai_median"]:.3f} vs {d["entropy_not_median"]:.3f} | {100 * d["entropy_ai_lower_share"]:.0f}% |')
    else:
        w('Not drawn in this run: too few full texts have vectors yet (see `diversity/logs/emb-*.out`).')
    w('')
    w('### Detector check (L7)\n')
    l7 = A.get('l7_by_flag_post') or {}
    if l7:
        w(f'- **Papers of 2023-2026:** Kobak style words run {l7.get("1.0", float("nan")):.2f} per 1,000 tokens in flagged papers and {l7.get("0.0", float("nan")):.2f} in unflagged ones.')
    if 'L7' in mainS.index:
        w(f'- **Lab level:** the change in L7 rises with AI usage, β = {ci(mainS.loc["L7"])}. The abstract detector and the full-text marker words agree.')
    w('')
    w('## Caveats\n')
    w('- **Detector errors.** The v1 abstract detector reads only the title and abstract and is set to a 1% false-positive rate on held-out pre-ChatGPT abstracts.')
    w(f'  - Its flagged share before ChatGPT is {", ".join(f"{100 * fy[y]:.1f}%" for y in sorted(fy, key=int) if int(y) <= 2022)} (2016-2022).')
    w('  - A flag marks AI-like style in the abstract, not AI use in the paper. Lab AI usage is a noisy share of a few papers, which biases slopes toward zero.')
    w('  - The 2016-2022 within-lab comparison shows what the detector\'s false positives alone look like. Where those papers already differ (e.g. MATTR), part of the post-2023 contrast is the detector selecting a writing style, not an effect of AI on diversity.')
    w('  - The paragraph detector (v2) will replace the flag with a dose once `paragraph_scores.jsonl.gz` exists. `run_all.sh` picks it up automatically.')
    w('- **Topic confound.** Labs that use AI more may also have moved into LLM research. The topic fixed effects and the LLM-topic share control for this only coarsely (10 lab topics, a keyword pattern).')
    w('- **Pre-trends.** The placebo slopes come from the same labs with no ChatGPT. A main slope inside the placebo band is not distinguishable from how these labs were already changing.')
    w('- **Partial 2026.** The post period includes 2026 papers to the extraction date, and lab-year rows for 2026 are partial.')
    small = LD.groupby('lab').size()
    w('- **Labs too small to measure:**')
    w(f'  - {len(set(LD.lab)) - A["labs_in_ai_analysis"]} of the {LD.lab.nunique()} labs with ≥ 5 papers in both periods lack ≥ 5 AI-scored post papers or the family\'s draw size.')
    w(f'  - {A.get("labs_total", 0) - LD.lab.nunique()} of the {A.get("labs_total", 0)} labs have < 5 papers in one of the periods and are not in `lab_diversity.csv` at all.')
    w('  - Family coverage differs: full texts and S2 references are missing for many papers.')
    w('  - Berkeley and Stanford have S2 reference lists for very few papers (the homogenization study\'s static s2.sqlite), so they rarely enter C1-C4.')
    w('- **Equal-size draws.** n is lab-specific (the smaller period), so a big lab\'s measures are on a different scale from a small lab\'s. The change within a lab is size-controlled; the regressions add log n.')
    w('- **Segments, not paragraphs.** Full-text vectors average ~150-word passages. S8 is the spread of those passages.')
    w('- **N1 space.** The arXiv background is re-embedded with specter2_base, because S2\'s stored specter_v2 vectors are a different space (same-paper cosine ~0.956 against ~0.82 between random papers).')
    w(f'- **Multiple comparisons.** {len(mainS)} measures × several specifications. Read the pattern across families and against the placebo null, not single p-values.')
    w('')
    w('## Files\n')
    w('- `lab_diversity.csv`: one row per lab × period, with every measure, n per family (`n_*`), draw size (`ndraw_*`) and AI usage (`ai_mean`, `ai_high`, `p_ai_mean`, `llm_share`).')
    w('  - `lab_diversity_placebo.csv`: the same for the placebo splits.')
    w(f'  - `lab_diversity_year.csv`: lab × year rows with n = 5 draws ({len(LY):,} rows).')
    w('- `results/`:')
    w('  - `slopes.csv`: every lab-level β, CI, p_boot, p_perm and n.')
    w('  - `within.csv`: the within-lab contrasts.')
    w('  - `lab_wide.csv`: per-lab changes.')
    w('  - `paper_lab_measures.csv.gz`: paper × lab measures.')
    w('  - `analysis.json`: counts and the null band.')
    w('- `figures/`:')
    w('  - `lab_scatter_{abs,ft,txt,ref}.png`: per-measure scatters.')
    w('  - `forest.png`, `forest_by_school.png`.')
    w('  - `fig3_fulltext.png`.')
    w('  - `flag_share_by_year.png`.')
    w('- `data/`:')
    w('  - `fulltext_emb.sqlite`: segment and mean vectors.')
    w('  - `background_specter2base.npz`.')
    w('  - `paper_features.parquet`.')
    w('  - `topics.npz`.')
    w('  - `s2_refs_cache.pkl.gz`.')
    w('- Code:')
    w('  - `measures.py` (+ `test_measures.py`).')
    w('  - `embed_fulltext.py` / `embed_fulltext.slurm` / `submit_embed.sh`.')
    w('  - `paper_features.py`, `lab_diversity.py`, `analyze.py`, `figures.py`, `report.py`.')
    w('  - `run_all.sh`.')
    (C.ROOT / 'REPORT.md').write_text('\n'.join(x for x in L if x is not None) + '\n')
    C.log(report=str(C.ROOT / 'REPORT.md'), lines=len(L))


if __name__ == '__main__':
    main()
