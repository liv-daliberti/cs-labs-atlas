# What AI-flagged lab papers cite

Written 2026-10-28 from `ai-writing/citations/` (CSVs in `results/`, figures in `figures/`). The downloads are complete: OpenAlex 593,156 of 610,141 cited works (the other 16,985 are deleted or merged ids), S2 reference lists 37,277 found and 4,114 not in S2.

## Methods

**Citing papers:** 43,220 paragraph-scored lab papers, 2016-2026.

**AI groups:**
- *flagged*: `ai_share >= 0.25` from detector_v2.
- *some*: `0 < ai_share < 0.25`.
- *none*: `ai_share = 0`.
- "Unflagged" means some + none.

**Reference lists** (a paper needs at least 5 references in the source):
- OpenAlex (`fetch.py`): publisher deposits.
- Semantic Scholar (`s2fetch.py`): parsed from PDFs.
- S2 is the primary source because it covers flagged papers better. Everything is computed on both.

**Pooled measures** (`analyze.py`): 1,000 equal-size draws per cell, 2.5-97.5 percentiles over draws. The year x group draw size is N = 91 (S2) or 69 (OpenAlex), which is the whole 2023-flagged cell, so that cell has no interval of its own.

**Per-paper regressions** (`within.py`):
- Model: y = b*flagged + g*log(references) + lab x year fixed effects. A paper of k labs enters once per lab with weight 1/k.
- 1,000 lab-cluster bootstrap resamples.
- Variants: year fixed effects only (raw); subfield x year; lab x year x citing subfield; one citing year at a time; a 2016-22 placebo on false-positive dose (per 10 points).

**Distribution by year** (`dist_by_year.py`): 500 draws of 60 citing papers per citing year x group. Measures: entropy and Gini over cited works (900 citations rarefied), spread of cited years (pooled SD and IQR, per-paper SD).

**Published vs preprint** (`build.py`):
- OpenAlex `pubclass`: published if a location is a journal, conference or book, or if the work is Crossref-registered with a publisher type. Otherwise preprint-only if a repository location or type = preprint.
- `preprint_s2`: as above, but arXiv records that S2 places at a venue count as published.
- S2's own rule on S2 lists.

**AI-written cited works:**
- v1 abstract detector on every cited work published 2022 or later with a 50-word abstract, plus a 30k calibration sample from 2016-21 (`score.py`, `q2.py`). The lab-paper check reproduces v1 exactly: 2,878 of 2,878 agree.
- Full-text passage detector (v2):
  - **Sample:** a citation-weighted sample of open full texts of cited non-corpus works (`ftsample.py`), drawn per cited-year {2016-21, 2023, 2024, 2025, 2026} x {published, preprint-only} stratum.
  - **Sources:** arXiv v1 from the GCS bulk bucket, PMC OA on S3, and open PDFs on allowed hosts with robots.txt honoured. No paywalls, logins or arxiv.org.
  - **Usable text:** at least 1,000 body words and the title on page 1.
  - **Scoring:** 14,516 texts, scored by `v2score.py` with the final 'all' model and its threshold. A work is flagged when `ai_share >= 0.25`.
  - **Corpus lab papers:** the 19,266 corpus lab papers that are cited use their own paragraph score.
  - **Estimand:** share of citations (`q2v2.py`).

## Coverage (`results/coverage.csv`)

Columns:
- **OA >= 5 / S2 >= 5**: share of papers with a list of at least 5 references.
- **OA refs fetched**: share of OpenAlex references with a fetched cited work.
- **2023+ refs with v1 / v2 score**: OpenAlex references to works published 2023 or later whose cited work has a v1 abstract score, or a v2 full-text score.

| citing year | group | papers | OA >= 5 | S2 >= 5 | either | OA refs fetched | 2023+ refs with v1 score | 2023+ refs with v2 score |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2016-22 | unflagged | 24,612 | 86.3% | 69.7% | 93.9% | 96.8% | n/a | n/a |
| 2023 | flagged | 137 | 50.4% | 66.4% | 83.9% | 98.4% | 83.4% | 47.4% |
| 2023 | unflagged | 4,480 | 66.5% | 72.2% | 88.7% | 97.6% | 87.6% | 53.0% |
| 2024 | flagged | 536 | 45.5% | 74.3% | 84.5% | 97.5% | 90.0% | 46.8% |
| 2024 | unflagged | 4,263 | 57.1% | 69.6% | 82.3% | 97.7% | 88.0% | 48.1% |
| 2025 | flagged | 1,117 | 47.6% | 73.9% | 80.8% | 98.8% | 84.3% | 38.5% |
| 2025 | unflagged | 3,571 | 50.6% | 68.9% | 78.7% | 98.7% | 85.2% | 44.9% |
| 2026 | flagged | 786 | 26.7% | 75.1% | 81.9% | 99.6% | 80.2% | 41.0% |
| 2026 | unflagged | 3,689 | 20.2% | 78.4% | 83.2% | 99.4% | 82.5% | 43.5% |

The gap is at the paper level and only in OpenAlex: flagged papers are more often arXiv-only. Once a list exists, references resolve at 97.5-99.6% in both groups, and S2 covers flagged papers as well as unflagged ones. The two sources agree in sign and size on every main contrast.

## (1) How works cited by AI-flagged papers differ, by year

Pooled, flagged minus none (`results/s2_diffs.csv`, `results/oa_diffs.csv`):

| measure (S2) | 2023 | 2024 | 2025 |
|---|---|---|---|
| mean reference age (years) | -2.79 [-3.84, -1.75] | -3.29 [-4.53, -2.05] | -3.45 [-4.95, -2.01] |
| share of refs <= 2 years old | +0.144 [0.107, 0.177] | +0.153 [0.086, 0.218] | +0.145 [0.078, 0.211] |
| age-adjusted log(1 + citations) | +0.41 [0.19, 0.64] | +0.51 [0.20, 0.82] | +0.46 [0.16, 0.79] |
| share of refs in top 1% of their year | +0.047 [0.017, 0.073] | +0.067 [0.028, 0.107] | +0.055 [0.015, 0.097] |
| coverage, S2 >= 5 (flagged / unflagged) | 66% / 72% | 74% / 70% | 74% / 69% |

- **OpenAlex:** age -2.6 / -3.2 / -3.5 years, recent share +0.135 / +0.105 / +0.107, popularity about half the S2 size. Coverage (OA >= 5, flagged / unflagged): 50% / 67%, 46% / 57%, 48% / 51%.
- **Dose-response, 2023-26** (year mix matched): the recent share rises from 0.20 at zero dose to 0.31 at 25-50% dose. S2: 25-50% minus 0 is +0.115 [0.073, 0.155]. The 2016-22 false-positive dose bins are flat (-0.027 [-0.086, +0.034]).
- **By school** (2024-26, S2 recent share, flagged minus not; every interval excludes 0): Princeton +0.12, MIT +0.08, Berkeley +0.08, CMU +0.06, EPFL +0.04.
- **By field:** CS +0.07 [0.03, 0.11]; other fields +0.05 [0.02, 0.08].
- **Composition:** about 70% of the raw gap is composition. Year fixed effects alone give -2.1 years of reference age; lab x year fixed effects give -0.72 years.

## (2) The distribution over cited works: is its variance going down?

Files: `results/dist_by_year*`, `figures/citations_spread_by_year.png`.

**All lab papers, 2016-2025** (slope per year):
- Entropy over cited works: S2 +0.0003 [-0.0019, +0.0024]; OpenAlex +0.0009 [-0.0003, +0.0022].
- Gini: S2 -0.0002 [-0.0016, +0.0012]; OpenAlex -0.0006 [-0.0015, +0.0002].
- No narrowing in which works are cited. The measure is near its ceiling, since 97-99% of 900 citations go to distinct works.
- IQR of cited years: S2 -0.24 / year [-0.41, -0.05] (about 9.1 -> 7.8 years); OpenAlex -0.10 [-0.29, +0.10].
- The sources disagree on this trend and on the venue-entropy trend, so the lab-wide trend is unsettled.

**Flagged vs unflagged papers (S2):**

| | 2023 | 2024 | 2025 |
|---|---|---|---|
| per-paper SD of cited years | 7.7 [6.7, 8.8] vs 9.3 [9.1, 9.5] | 7.1 [6.7, 7.6] vs 9.2 [9.1, 9.4] | 7.7 [7.4, 8.0] vs 9.5 [9.3, 9.7] |
| pooled IQR of cited years | 5.0 vs 7.9 | 5.8 vs 7.9 | 6.0 vs 8.5 |

- OpenAlex gives the same pattern.
- **Concentration on the same works:** pooled Gini is higher for flagged papers: +0.017 [0.001, 0.030] (2023), +0.020 [0.001, 0.039] (2024), +0.011 [-0.006, +0.028] (2025). Within lab and year this disappears: entropy +0.008 [-0.020, +0.038] (S2), +0.031 [0.008, 0.056] (OpenAlex).
- **Within-lab SD of cited years:** -0.70 [-1.09, -0.34] (S2), -0.34 [-0.97, +0.22] (OpenAlex). Placebo: +0.38 per 10 points, the opposite sign.
- **Reading:** the variance that falls is in when the cited work was published, not which works are cited.

## (3) How many cited works are themselves AI-written

Full-text detector (`results/q2v2_strata.csv`, `q2v2_coverage.csv`, `q2v2_bias.csv`); v1 abstract detector in `results/q2_by_cited_year.csv`.

Columns:
- **share of citations to flagged works**: Wilson 95% interval.
- **with corpus lab papers**: the same share with the corpus's own cited lab papers added.
- **v1 abstract (per work)**: share of works flagged by the v1 abstract detector.
- **citations covered**: share of the stratum's citations that the sample covers.

| cited year, class | texts | share of citations to flagged works | with corpus lab papers | v1 abstract (per work) | citations covered |
|---|---:|---|---:|---:|---:|
| 2016-21 preprint (floor) | 2,498 | 0.0% [0.0, 0.15] | 0.0% | 1.5% | 39% |
| 2016-21 published (floor) | 2,502 | 0.36% [0.19, 0.68] | 0.3% | 2.4% | 6% |
| 2023 preprint | 1,185 | 9.5% [7.9, 11.3] | 8.5% | 18.7% | 77% |
| 2023 published | 2,502 | 3.2% [2.6, 4.0] | 3.2% | 8.4% | 28% |
| 2024 preprint | 545 | 24.6% [21.2, 28.4] | 23.1% | 26.4% | 48% |
| 2024 published | 2,501 | 17.4% [16.0, 19.0] | 15.9% | 25.1% | 31% |
| 2025 preprint | 134 | 34.3% [26.8, 42.7] | 33.3% | 37.8% | 80% |
| 2025 published | 2,371 | 31.0% [29.2, 32.9] | 29.1% | 40.1% | 55% |
| 2026 preprint / published | 22 / 256 | 18% / 30.5% | | | |

**Bias check:** the sample's v1 abstract flag rate matches its whole stratum (2024 published 24.6% vs 26.3%; 2025 published 38.9% vs 41.6%). The sample over-represents arXiv-hosted works (about 53% vs 33%) and more-cited works. About half the "published" texts are arXiv v1 preprints (`results/q2v2_versions.csv`).

**Citing side** (`results/q2v2_citing.csv`): share of a group's references to scored 2023+ works that go to flagged works, lab-cluster bootstrap.

| citing year | flagged papers | none | flagged, above what the cited-year x class mix predicts | coverage, 2023+ refs with v2 score (flagged / unflagged) |
|---|---|---|---|---|
| 2023 | 13.6% [3.6, 24.7] | 1.2% | +6.0 [-4.2, +17.1] | 47% / 53% |
| 2024 | 16.8% [12.4, 20.6] | 2.9% | +7.7 [3.4, 11.3] | 47% / 48% |
| 2025 | 19.5% [16.5, 22.5] | 7.2% | +5.6 [2.9, 8.4] | 39% / 45% |

- **Within lab** (lab x year fixed effects, `results/q2v2_within.csv`): flagged papers' cited-AI share is +5.5 points [3.2, 7.8]. With the cited-year mix removed it is +5.0 [2.5, 7.2]. The v1 abstract detector gives +5.6 [3.9, 7.2].

## (4) Published (peer-reviewed) vs preprints

**Citing side**, preprint-only share of references, flagged minus none:
- S2: +1.3 [-0.4, +2.8] (2023), +2.9 [0.1, 5.7] (2024), +2.1 [-1.0, +5.2] (2025).
- OpenAlex rules: within +/-1 point, with intervals spanning 0.
- Within lab, 2023-26: S2 +0.3 [-0.4, +0.9], OpenAlex -0.3 [-0.9, +0.3].
- Within lab per year (S2): +2.1 [0.4, 4.0] (2023), +2.4 [1.5, 3.3] (2024), +0.8 [0.0, 1.6] (2025).
- Placebo: -0.4 to -1.0 points per 10 points.

**The level depends on the rule** (unflagged papers, 2024): OpenAlex `preprint` 7.5%, `preprint_s2` 4.0%, S2's own rule 7.8%. The two sources trend in opposite directions: OpenAlex falls to 1-2% in 2026 because its 2026 lists are mostly publisher deposits, while S2 rises from 6.4% to 15%. Only within-source contrasts are claimed.

**Cited side:** preprint-only works were more often AI-flagged than published ones in 2023 (9.5% vs 3.2%) and 2024 (24.6% vs 17.4%); they converge in 2025 (34% vs 31%).

## (5) Within-lab controls

Files: `results/within_lab.csv` (OpenAlex), `results/within_lab_s2.csv` (S2). Coefficient on *flagged* with a 95% lab-bootstrap interval.

| measure | raw S2 | lab x year S2 | lab x year OpenAlex | lab x year x subfield OpenAlex | 2016-22 placebo per 10 points (OpenAlex) |
|---|---|---|---|---|---|
| reference age (years) | -2.14 | -0.72 [-1.04, -0.43] | -0.76 [-1.24, -0.31] | -0.96 [-1.63, -0.31] | +0.43 [0.14, 0.77] |
| share <= 2 years old | +0.066 | +0.038 [0.025, 0.051] | +0.053 [0.034, 0.070] | +0.062 [0.040, 0.084] | -0.008 [-0.017, +0.003] |
| age-adjusted log citations | +0.24 | +0.064 [0.019, 0.110] | +0.063 [0.011, 0.117] | +0.033 [-0.036, +0.098] | -0.041 [-0.086, +0.004] |
| top-1% share | +0.032 | +0.009 [0.003, 0.016] | +0.006 [-0.001, +0.012] | +0.004 [-0.007, +0.013] | -0.008 [-0.013, -0.004] |
| canonicality | +0.046 | +0.006 [-0.020, +0.032] | +0.008 [-0.013, +0.028] | +0.004 [-0.030, +0.034] | -0.034 [-0.057, -0.012] |
| SD of cited years | -1.88 | -0.70 [-1.09, -0.34] | -0.34 [-0.97, +0.22] | -0.60 [-1.46, +0.22] | +0.38 [0.06, 0.71] |
| papers / labs | | 13,080 / 832 | 8,527 / 748 | 5,909 / 648 | 20,726 / 848 |

**Per year** (S2 lab x year; OpenAlex in brackets):

| year | share <= 2 years old | reference age (years) |
|---|---|---|
| 2023 | +0.111 [0.066, 0.154] (OA +0.109) | -1.27 [-2.05, -0.45] |
| 2024 | +0.087 [0.062, 0.110] (OA +0.063) | -1.20 [-1.67, -0.71] |
| 2025 | +0.048 [0.031, 0.065] (OA +0.049) | -0.87 [-1.25, -0.48] |

**Paired draws** (each flagged paper paired with an unflagged paper of the same lab and year): recent share +0.035 [0.002, 0.068] (S2), +0.053 [0.028, 0.080] (OpenAlex).

## (6) Figure: publication years of cited works, 2022-2025

File: `figures/cited_years_by_ai.png`, data in `results/cited_years_by_ai.csv`. Per paper, whichever of S2 and OpenAlex has more references with a known year; each paper weighted equally.

| citing year | group | papers with a list / scored | median reference age | share of refs <= 2 years old |
|---|---|---|---|---|
| 2022 | not AI-detected | 3,655 / 3,988 | 6.14 [6.02, 6.28] | 0.262 |
| 2022 | AI-detected | 6 / 12 | too few | |
| 2023 | not AI-detected | 4,009 / 4,480 | 6.29 [6.15, 6.43] | 0.253 |
| 2023 | AI-detected | 115 / 137 | 4.03 [3.54, 4.53] | 0.384 [0.346, 0.421] |
| 2024 | not AI-detected | 3,526 / 4,263 | 6.41 [6.26, 6.57] | 0.251 |
| 2024 | AI-detected | 456 / 536 | 4.32 [4.06, 4.60] | 0.367 [0.347, 0.388] |
| 2025 | not AI-detected | 2,833 / 3,571 | 6.80 [6.60, 7.01] | 0.268 |
| 2025 | AI-detected | 912 / 1,117 | 4.75 [4.52, 4.96] | 0.360 [0.346, 0.375] |

4-5% of AI-detected papers' references predate 2000, vs 9% for the rest.

## Caveats

- **Coverage:** see the table above.
- **The flag is a detector output:**
  - On held-out 2016-21 lab passages it flags 0.98%.
  - Detection on passages from the generators it was trained on is 95.6-99.8%; paraphrased text 90%.
  - It was not tested on GPT-4-class or Claude text.
  - On cited 2016-21 works it flags 0.36% of published and 0% of preprints.
  - Shares are a lower bound if unseen generators are missed.
- **Composition:** lab x year fixed effects do not remove differences between projects within a lab. The citing-subfield variant is a partial check.
- **Small cells:** the 2023-flagged cell is small, the 2024/2025 preprint and 2026 strata of the full-text sample are small, and 2026 is a partial year (not interpreted).

## Files

| script | output |
|---|---|
| `build.py` | `data/*.parquet` |
| `coverage.py` | `results/coverage.csv` |
| `analyze.py` | `results/{oa,s2}_{cells,diffs,sample_sizes}.csv` |
| `within.py` | `results/within_lab{,_s2}.csv` |
| `dist_by_year.py` | `results/dist_by_year{,_trend}_{oa,s2}.csv` |
| `score.py` + `q2.py` | `results/q2_*` |
| `ftsample.py` + `v2score.py` + `q2v2.py` | `results/q2v2_*`, `results/ft_frame.csv` |
| `cited_years_by_ai.py` | `figures/cited_years_by_ai.png` |
| `figures.py` | `figures/citations_main.png`, `citations_measures_{oa,s2}.png`, `citations_spread_by_year.png` |

Caches are in `/n/fs/resemble/homogenizing-science/cache/citations/`.
