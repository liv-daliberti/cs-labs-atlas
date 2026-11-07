# Full-text selection: inverse-probability weights and what they change

Generated 2026-11-06T03:42:07Z by `ai-writing/labstudy/ipw_report.py` (`ipw.py fit`, `ipw_rerun.py`); tables in `ai-writing/data/labstudy/ipw` (git-ignored). Years 2016-2025, no 2026. Intervals: bootstrap over labs (a paper's first lab), 100 replicates for the regression re-runs, 200 for the yearly rates.

## Answer

- **Who has a full text.** 65,751 of 101,304 lab papers (2016-2025, Georgia Tech excluded: no full text at all) have a scored full text (64.9%). Selection is strong on open access (closed-access papers 12% of the full-text set against 27% of all papers), on publisher (arXiv DOI prefix 22% against 16%; IEEE 18% against 23%), school and year. The cross-fitted model separates the two sets well (AUC 0.85 logistic, 0.89 boosting).
- **Balance.** The largest standardised mean difference (SMD) over 155 covariate columns falls from 0.380 to 0.085 (logit model, the table's); 0 columns stay above the 0.1 target. Effective sample size 48,651 of 65,751 (74%); weights trimmed to [0.65, 4.32] (1st-99th percentile of the selected), mean 1.
- **Headline rates.** Share of papers with `ai_share` >= 0.25: 2024 0.154 unweighted vs 0.148 weighted; 2025 0.269 vs 0.269 (section 3: the two intervals overlap in 10 of 10 years).
**Where conclusions change.** Paper level: weighting flips the sign of the post-2022 dose-novelty coefficient in 1 of 26 model-design cells and moves an interval across 0 in 1 (section 4 lists them); lab level: sign differs in 0 of 35 model-outcome cells and the zero-status in 11 (section 5). The all-papers abstract-flag estimates are shown next to them.

## 1. The selection and the model

Outcome S = the paper has a usable local full text that the passage detector scored (`ai_share` not null). Population = every lab paper of the universe, 2016-2025 (strict labs), 120,119 papers (101,304 with school in the model). Covariates: year, school, venue type (OpenAlex `source_type`), work type, OpenAlex OA status and `is_oa`, DOI prefix (publisher key; the 40 most frequent, rest pooled), OpenAlex field and subfield, log team size, log citations, log references, number of labs. Cross-fitted (5 folds) HistGradientBoosting and a one-hot logistic regression with year x school interactions; the table's model is the one with the smaller maximum SMD after weighting (**logit**; both propensities are in the table).

Full-text coverage by school (share of papers 2016-2025 with a scored full text):

| school | papers | scored full text |
|---|---|---|
| berkeley | 11,893 | 70.1% |
| cmu | 22,514 | 73.0% |
| epfl | 11,701 | 70.6% |
| gatech | 18,815 | 41.0% |
| michigan | 10,792 | 55.3% |
| mit | 17,320 | 71.1% |
| princeton | 7,731 | 73.4% |
| stanford | 15,535 | 71.9% |
| uchicago | 3,818 | 71.8% |

By year (Georgia Tech excluded): 2016 59%; 2017 61%; 2018 64%; 2019 67%; 2020 70%; 2021 72%; 2022 73%; 2023 75%; 2024 77%; 2025 76%.

**Positivity.** Share of papers with an estimated probability below 0.05: 1.0%, below 0.02: 0.15%. Georgia Tech has no full text (probability 0): its papers have no weights (NaN) and no full-text measure; every re-run below is therefore on the eight other schools. The abstract-availability table (`p_abs`, `w_abs`) is a degenerate case (AUC 0.97): papers without an OpenAlex record have no abstract and no covariates, so the weights cannot balance them (max SMD stays 0.26); **use `w_ft` only**.

## 2. Covariate balance (standardised mean differences against the whole population)

| covariate (dummy or standardised numeric) | all papers | full-text, unweighted | full-text, weighted | SMD before | SMD after |
|---|---|---|---|---|---|
| oa_status_closed | 0.268 | 0.121 | 0.235 | -0.380 | -0.085 |
| is_oa | 0.723 | 0.869 | 0.755 | +0.368 | +0.081 |
| oa_status_green | 0.451 | 0.550 | 0.471 | +0.199 | +0.040 |
| doi_prefix_10.48550 | 0.160 | 0.222 | 0.168 | +0.158 | +0.020 |
| oa_field_Engineering | 0.214 | 0.160 | 0.195 | -0.139 | -0.048 |
| oa_subfield_Electrical and Electronic Engineering | 0.061 | 0.034 | 0.050 | -0.131 | -0.052 |
| oa_field_Computer Science | 0.454 | 0.518 | 0.474 | +0.128 | +0.039 |
| doi_prefix_10.1109 | 0.231 | 0.180 | 0.209 | -0.127 | -0.055 |
| oa_subfield_Artificial Intelligence | 0.214 | 0.259 | 0.223 | +0.107 | +0.023 |
| work_type_preprint | 0.206 | 0.249 | 0.217 | +0.102 | +0.026 |
| source_type_repository | 0.227 | 0.270 | 0.239 | +0.100 | +0.029 |
| doi_prefix_none | 0.052 | 0.034 | 0.052 | -0.086 | +0.001 |
| cited_log | 2.189 | 2.326 | 2.229 | +0.085 | +0.025 |
| work_type_book-chapter | 0.015 | 0.007 | 0.013 | -0.080 | -0.021 |

Columns with |SMD| > 0.1: 10 before, 0 after (of 155). Boosting alternative: max 0.380 before, 0.088 after (ESS 43,283).

Year x school cells: largest absolute gap between the weighted full-text share of a cell and the population share 0.0020 (unweighted 0.0036). Calibration by propensity decile (observed / predicted full-text rate): 0.10/0.11; 0.21/0.25; 0.41/0.40; 0.59/0.57; 0.75/0.71; 0.83/0.80; 0.87/0.86; 0.90/0.90; 0.91/0.93; 0.93/0.97.

## 3. Dose rates: unweighted against weighted

| year | share >= 0.25, unweighted | share >= 0.25, IPW | mean ai_share, unweighted | mean ai_share, IPW |
|---|---|---|---|---|
| 2016 | 0.0002 [0.0000, 0.0009] | 0.0001 [0.0000, 0.0006] | 0.0022 [0.0019, 0.0025] | 0.0022 [0.0018, 0.0027] |
| 2017 | 0.0002 [0.0000, 0.0006] | 0.0003 [0.0000, 0.0010] | 0.0021 [0.0018, 0.0024] | 0.0021 [0.0018, 0.0026] |
| 2018 | 0.0002 [0.0000, 0.0005] | 0.0001 [0.0000, 0.0004] | 0.0024 [0.0021, 0.0027] | 0.0025 [0.0021, 0.0028] |
| 2019 | 0.0003 [0.0000, 0.0008] | 0.0003 [0.0000, 0.0006] | 0.0025 [0.0021, 0.0028] | 0.0024 [0.0021, 0.0028] |
| 2020 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | 0.0024 [0.0021, 0.0027] | 0.0024 [0.0020, 0.0028] |
| 2021 | 0.0001 [0.0000, 0.0005] | 0.0001 [0.0000, 0.0004] | 0.0031 [0.0027, 0.0034] | 0.0031 [0.0027, 0.0034] |
| 2022 | 0.0012 [0.0005, 0.0020] | 0.0015 [0.0005, 0.0025] | 0.0043 [0.0039, 0.0047] | 0.0044 [0.0038, 0.0049] |
| 2023 | 0.0370 [0.0322, 0.0428] | 0.0357 [0.0308, 0.0417] | 0.0313 [0.0286, 0.0344] | 0.0303 [0.0276, 0.0334] |
| 2024 | 0.1541 [0.1418, 0.1671] | 0.1476 [0.1355, 0.1605] | 0.1014 [0.0943, 0.1085] | 0.0981 [0.0911, 0.1055] |
| 2025 | 0.2695 [0.2499, 0.2890] | 0.2688 [0.2482, 0.2879] | 0.1707 [0.1607, 0.1811] | 0.1697 [0.1590, 0.1808] |

By school, 2025 (share of papers with ai_share >= 0.25):

| school | scored papers | unweighted | IPW |
|---|---|---|---|
| berkeley | 1035 | 0.232 [0.186, 0.289] | 0.238 [0.190, 0.301] |
| cmu | 1974 | 0.309 [0.274, 0.343] | 0.305 [0.268, 0.340] |
| epfl | 1032 | 0.309 [0.258, 0.362] | 0.312 [0.259, 0.368] |
| michigan | 789 | 0.297 [0.254, 0.341] | 0.307 [0.258, 0.355] |
| mit | 1343 | 0.224 [0.191, 0.255] | 0.213 [0.178, 0.248] |
| princeton | 750 | 0.204 [0.129, 0.282] | 0.217 [0.143, 0.288] |
| stanford | 1507 | 0.295 [0.254, 0.333] | 0.287 [0.238, 0.324] |
| uchicago | 350 | 0.186 [0.125, 0.246] | 0.176 [0.114, 0.235] |

## 4. Paper level: AI share against novelty (k = 3, scope all), weighted against unweighted against abstract-based

Coefficient of `nov_nn_cap` on the exposure (per unit, 0 -> 1) with a lab-bootstrap interval. `ft / unw` and `ft / IPW`: papers with a scored full text, exposure `ai_share`; `abs_all`: every paper with an abstract, exposure = its abstract flag (no full-text selection); `ft flag`: the abstract flag on the full-text papers (separates sample from exposure). Pooled = year + school + topic FE with controls; within-lab = lab x year FE. Pre = 2017-2021 placebo (the exposure there is detector noise).

| model | novelty from | design | post: ft / unw | post: ft / IPW | post: abs_all | post: ft flag / unw | post: ft flag / IPW | pre placebo: ft / unw | pre placebo: ft / IPW |
|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | abstract | pooled | -0.0036 [-0.0070, +0.0003] | -0.0042 [-0.0084, +0.0003] | -0.0007 [-0.0023, +0.0009] | -0.0006 [-0.0022, +0.0008] | -0.0006 [-0.0023, +0.0011] | -0.0162 [-0.0660, +0.0382] | +0.0260 [-0.0218, +0.0909] |
| bge_m3 | abstract | withinlab | -0.0004 [-0.0047, +0.0041] | -0.0023 [-0.0075, +0.0027] | -0.0001 [-0.0015, +0.0014] | +0.0006 [-0.0015, +0.0025] | -0.0000 [-0.0020, +0.0016] | -0.0095 [-0.0774, +0.0252] | +0.0177 [-0.0510, +0.0773] |
| bge_m3 | fulltext | pooled | +0.0157 [+0.0106, +0.0204] | +0.0145 [+0.0082, +0.0204] | -0.0007 [-0.0023, +0.0009] | -0.0006 [-0.0022, +0.0008] | -0.0006 [-0.0023, +0.0011] | +0.1337 [+0.0618, +0.1811] | +0.1118 [+0.0425, +0.1713] |
| bge_m3 | fulltext | withinlab | +0.0148 [+0.0085, +0.0209] | +0.0139 [+0.0079, +0.0193] | -0.0001 [-0.0015, +0.0014] | +0.0006 [-0.0015, +0.0025] | -0.0000 [-0.0020, +0.0016] | +0.1202 [+0.0635, +0.1807] | +0.1164 [+0.0601, +0.1676] |
| gte_qwen2_1p5b | abstract | pooled | +0.0021 [-0.0030, +0.0067] | +0.0018 [-0.0046, +0.0077] | +0.0012 [-0.0006, +0.0032] | +0.0001 [-0.0016, +0.0020] | +0.0005 [-0.0020, +0.0028] | -0.0131 [-0.0654, +0.0607] | +0.0366 [-0.0360, +0.1181] |
| gte_qwen2_1p5b | abstract | withinlab | +0.0040 [-0.0020, +0.0095] | +0.0026 [-0.0039, +0.0087] | +0.0008 [-0.0009, +0.0028] | +0.0008 [-0.0010, +0.0029] | +0.0005 [-0.0020, +0.0022] | +0.0049 [-0.0674, +0.0603] | +0.0592 [-0.0110, +0.1386] |
| gte_qwen2_1p5b | fulltext | pooled | +0.0146 [+0.0091, +0.0199] | +0.0140 [+0.0066, +0.0198] | +0.0012 [-0.0006, +0.0032] | +0.0001 [-0.0016, +0.0020] | +0.0005 [-0.0020, +0.0028] | +0.0699 [-0.0032, +0.1288] | +0.0415 [-0.0355, +0.1028] |
| gte_qwen2_1p5b | fulltext | withinlab | +0.0150 [+0.0089, +0.0222] | +0.0140 [+0.0083, +0.0211] | +0.0008 [-0.0009, +0.0028] | +0.0008 [-0.0010, +0.0029] | +0.0005 [-0.0020, +0.0022] | +0.0803 [+0.0117, +0.1402] | +0.0999 [+0.0175, +0.1728] |
| nomic_v15 | abstract | pooled | +0.0040 [-0.0012, +0.0081] | +0.0024 [-0.0029, +0.0066] | +0.0012 [-0.0003, +0.0028] | +0.0017 [+0.0001, +0.0034] | +0.0011 [-0.0013, +0.0028] | -0.0097 [-0.0581, +0.0425] | +0.0191 [-0.0320, +0.0974] |
| nomic_v15 | abstract | withinlab | +0.0054 [+0.0004, +0.0115] | +0.0037 [-0.0029, +0.0096] | +0.0007 [-0.0010, +0.0026] | +0.0015 [-0.0006, +0.0035] | +0.0005 [-0.0016, +0.0023] | -0.0149 [-0.0747, +0.0291] | +0.0053 [-0.0685, +0.0718] |
| nomic_v15 | fulltext | pooled | +0.0154 [+0.0102, +0.0212] | +0.0130 [+0.0057, +0.0189] | +0.0012 [-0.0003, +0.0028] | +0.0017 [+0.0001, +0.0034] | +0.0011 [-0.0013, +0.0028] | +0.0834 [+0.0085, +0.1365] | +0.0579 [-0.0086, +0.1350] |
| nomic_v15 | fulltext | withinlab | +0.0168 [+0.0108, +0.0234] | +0.0143 [+0.0082, +0.0202] | +0.0007 [-0.0010, +0.0026] | +0.0015 [-0.0006, +0.0035] | +0.0005 [-0.0016, +0.0023] | +0.0871 [+0.0096, +0.1538] | +0.0903 [+0.0237, +0.1701] |
| qwen3_0p6b | abstract | pooled | -0.0015 [-0.0063, +0.0039] | -0.0038 [-0.0101, +0.0018] | -0.0008 [-0.0027, +0.0013] | -0.0020 [-0.0039, +0.0002] | -0.0018 [-0.0043, +0.0007] | -0.0269 [-0.0844, +0.0349] | +0.0201 [-0.0445, +0.0737] |
| qwen3_0p6b | abstract | withinlab | +0.0027 [-0.0030, +0.0109] | +0.0014 [-0.0047, +0.0078] | +0.0009 [-0.0010, +0.0031] | +0.0004 [-0.0018, +0.0027] | +0.0004 [-0.0024, +0.0038] | -0.0062 [-0.0794, +0.0455] | +0.0203 [-0.0589, +0.0869] |
| qwen3_0p6b | fulltext | pooled | -0.0013 [-0.0100, +0.0047] | -0.0021 [-0.0094, +0.0046] | -0.0008 [-0.0027, +0.0013] | -0.0020 [-0.0039, +0.0002] | -0.0018 [-0.0043, +0.0007] | +0.0335 [-0.0618, +0.0998] | +0.0062 [-0.0936, +0.0992] |
| qwen3_0p6b | fulltext | withinlab | +0.0010 [-0.0061, +0.0081] | -0.0010 [-0.0103, +0.0067] | +0.0009 [-0.0010, +0.0031] | +0.0004 [-0.0018, +0.0027] | +0.0004 [-0.0024, +0.0038] | +0.0325 [-0.0675, +0.1063] | +0.0334 [-0.0569, +0.1257] |
| scincl | abstract | pooled | +0.0141 [+0.0089, +0.0175] | +0.0129 [+0.0075, +0.0183] | +0.0042 [+0.0025, +0.0063] | +0.0044 [+0.0025, +0.0066] | +0.0052 [+0.0024, +0.0078] | -0.0378 [-0.0931, +0.0257] | -0.0069 [-0.0684, +0.0849] |
| scincl | abstract | withinlab | +0.0101 [+0.0038, +0.0164] | +0.0080 [+0.0026, +0.0153] | +0.0018 [-0.0003, +0.0042] | +0.0021 [-0.0006, +0.0044] | +0.0013 [-0.0016, +0.0041] | -0.0148 [-0.0993, +0.0444] | +0.0384 [-0.0475, +0.1277] |
| specter2_base | abstract | pooled | -0.0075 [-0.0125, -0.0031] | -0.0095 [-0.0148, -0.0039] | -0.0047 [-0.0064, -0.0026] | -0.0050 [-0.0064, -0.0028] | -0.0049 [-0.0074, -0.0024] | -0.0456 [-0.1022, +0.0198] | -0.0189 [-0.0909, +0.0598] |
| specter2_base | abstract | withinlab | -0.0070 [-0.0134, -0.0019] | -0.0095 [-0.0170, -0.0009] | -0.0048 [-0.0066, -0.0024] | -0.0050 [-0.0078, -0.0027] | -0.0052 [-0.0080, -0.0027] | -0.0179 [-0.0875, +0.0389] | +0.0090 [-0.0862, +0.0999] |
| specter2_base | fulltext | pooled | +0.0109 [+0.0056, +0.0161] | +0.0089 [+0.0016, +0.0141] | -0.0047 [-0.0064, -0.0026] | -0.0050 [-0.0064, -0.0028] | -0.0049 [-0.0074, -0.0024] | +0.0329 [-0.0348, +0.0851] | +0.0160 [-0.0634, +0.0704] |
| specter2_base | fulltext | withinlab | +0.0125 [+0.0062, +0.0189] | +0.0107 [+0.0041, +0.0166] | -0.0048 [-0.0066, -0.0024] | -0.0050 [-0.0078, -0.0027] | -0.0052 [-0.0080, -0.0027] | +0.0790 [-0.0077, +0.1566] | +0.0905 [-0.0060, +0.1608] |
| specter2_proximity | abstract | pooled | -0.0008 [-0.0059, +0.0029] | -0.0034 [-0.0085, +0.0025] | -0.0007 [-0.0023, +0.0013] | -0.0009 [-0.0025, +0.0014] | -0.0010 [-0.0031, +0.0014] | -0.0350 [-0.0808, +0.0232] | +0.0145 [-0.0447, +0.0958] |
| specter2_proximity | abstract | withinlab | -0.0078 [-0.0136, -0.0019] | -0.0107 [-0.0167, -0.0040] | -0.0027 [-0.0045, -0.0010] | -0.0030 [-0.0056, -0.0007] | -0.0037 [-0.0065, -0.0011] | -0.0270 [-0.1094, +0.0502] | +0.0058 [-0.0840, +0.1093] |
| specter2_proximity | fulltext | pooled | +0.0174 [+0.0112, +0.0227] | +0.0154 [+0.0078, +0.0213] | -0.0007 [-0.0023, +0.0013] | -0.0009 [-0.0025, +0.0014] | -0.0010 [-0.0031, +0.0014] | +0.0611 [-0.0090, +0.1117] | +0.0493 [-0.0496, +0.1058] |
| specter2_proximity | fulltext | withinlab | +0.0151 [+0.0092, +0.0229] | +0.0134 [+0.0067, +0.0203] | -0.0027 [-0.0045, -0.0010] | -0.0030 [-0.0056, -0.0007] | -0.0037 [-0.0065, -0.0011] | +0.0814 [+0.0070, +0.1620] | +0.1039 [-0.0008, +0.1738] |

Weighting changes the sign of the post-2022 coefficient in 1 of 26 model-design cells and changes whether its interval excludes 0 in 1; the largest shift is 0.0028 (novelty sd about 0.07).
- nomic_v15 (abstract novelty, withinlab): unweighted +0.0054 [+0.0004, +0.0115] -> IPW +0.0037 [-0.0029, +0.0096].
- qwen3_0p6b (fulltext novelty, withinlab): unweighted +0.0010 [-0.0061, +0.0081] -> IPW -0.0010 [-0.0103, +0.0067].

## 5. Lab level: difference-in-differences with the dose from unweighted, IPW-weighted and abstract-flag exposure

`did` = post-2022 (2023-2025) x lab dose on a lab-year outcome with lab and year FE, per unit of dose (0 -> 1), bootstrap over labs; `placebo B` = the same on 2016-2021 with the break at B. Outcomes are the size-matched (5 papers) abstract-embedding measures of dose_lab.py. Dose kinds: `unweighted` = mean `ai_share` of the lab's scored 2023-25 papers (>= 4); `ipw` = the Hajek-weighted mean; `abstract_flag` = flagged-abstract share (all papers).

| model | outcome | did: unweighted dose | did: IPW dose | did: abstract-flag dose | placebos 2019/20/21 (unweighted) | placebos (IPW) |
|---|---|---|---|---|---|---|
| bge_m3 | disp | +0.032 [+0.015, +0.049] | +0.026 [+0.004, +0.047] | +0.019 [+0.006, +0.032] | +0.013, +0.017, +0.016 | +0.004, +0.011, +0.010 |
| bge_m3 | h_oa | +0.333 [+0.085, +0.574] | +0.230 [-0.117, +0.510] | +0.201 [+0.011, +0.405] | +0.068, +0.122, +0.370 | -0.024, +0.002, +0.249 |
| bge_m3 | mpd | +0.063 [+0.029, +0.097] | +0.052 [+0.008, +0.090] | +0.035 [+0.010, +0.061] | +0.023, +0.030, +0.031 | +0.008, +0.020, +0.020 |
| bge_m3 | nov_all | +0.008 [-0.006, +0.026] | +0.006 [-0.008, +0.025] | +0.002 [-0.008, +0.011] | +0.014, -0.003, -0.007 | +0.007, -0.009, -0.016 |
| bge_m3 | vendi | +0.178 [+0.006, +0.318] | +0.135 [-0.096, +0.310] | +0.152 [+0.071, +0.267] | +0.122, +0.169, +0.087 | +0.029, +0.117, +0.064 |
| gte_qwen2_1p5b | disp | +0.028 [+0.002, +0.050] | +0.015 [-0.017, +0.046] | +0.023 [+0.006, +0.042] | -0.003, +0.011, +0.010 | -0.020, -0.000, -0.001 |
| gte_qwen2_1p5b | h_oa | +0.333 [+0.085, +0.574] | +0.230 [-0.117, +0.510] | +0.201 [+0.011, +0.405] | +0.068, +0.122, +0.370 | -0.024, +0.002, +0.249 |
| gte_qwen2_1p5b | mpd | +0.050 [-0.000, +0.089] | +0.025 [-0.032, +0.079] | +0.038 [+0.007, +0.073] | -0.006, +0.019, +0.018 | -0.034, -0.000, -0.003 |
| gte_qwen2_1p5b | nov_all | -0.018 [-0.044, +0.007] | -0.027 [-0.051, +0.000] | -0.005 [-0.021, +0.009] | -0.013, -0.024, -0.035 | -0.023, -0.034, -0.044 |
| gte_qwen2_1p5b | vendi | +0.208 [-0.009, +0.404] | +0.110 [-0.154, +0.368] | +0.203 [+0.077, +0.344] | -0.036, +0.090, +0.018 | -0.181, -0.006, -0.064 |
| nomic_v15 | disp | +0.058 [+0.028, +0.085] | +0.047 [+0.011, +0.084] | +0.032 [+0.011, +0.054] | +0.021, +0.031, +0.023 | +0.004, +0.019, +0.011 |
| nomic_v15 | h_oa | +0.333 [+0.085, +0.574] | +0.230 [-0.117, +0.510] | +0.201 [+0.011, +0.405] | +0.068, +0.122, +0.370 | -0.024, +0.002, +0.249 |
| nomic_v15 | mpd | +0.104 [+0.053, +0.150] | +0.084 [+0.020, +0.151] | +0.056 [+0.017, +0.095] | +0.038, +0.053, +0.043 | +0.008, +0.033, +0.020 |
| nomic_v15 | nov_all | +0.030 [+0.008, +0.050] | +0.021 [+0.003, +0.047] | +0.008 [-0.003, +0.020] | +0.011, -0.002, -0.014 | +0.004, -0.009, -0.022 |
| nomic_v15 | vendi | +0.392 [+0.136, +0.612] | +0.306 [+0.009, +0.596] | +0.259 [+0.132, +0.411] | +0.140, +0.237, +0.125 | +0.003, +0.140, +0.055 |
| qwen3_0p6b | disp | +0.016 [-0.008, +0.038] | +0.007 [-0.021, +0.040] | +0.014 [-0.002, +0.034] | +0.005, +0.022, +0.015 | -0.006, +0.013, +0.005 |
| qwen3_0p6b | h_oa | +0.333 [+0.085, +0.574] | +0.230 [-0.117, +0.510] | +0.201 [+0.011, +0.405] | +0.068, +0.122, +0.370 | -0.024, +0.002, +0.249 |
| qwen3_0p6b | mpd | +0.028 [-0.018, +0.071] | +0.011 [-0.044, +0.071] | +0.023 [-0.008, +0.060] | +0.009, +0.041, +0.029 | -0.011, +0.025, +0.010 |
| qwen3_0p6b | nov_all | -0.009 [-0.036, +0.020] | -0.016 [-0.040, +0.014] | -0.007 [-0.022, +0.009] | -0.007, -0.018, -0.027 | -0.013, -0.023, -0.029 |
| qwen3_0p6b | vendi | +0.104 [-0.093, +0.287] | +0.046 [-0.201, +0.299] | +0.140 [+0.040, +0.272] | +0.098, +0.189, +0.066 | -0.012, +0.103, -0.009 |
| scincl | disp | +0.070 [+0.036, +0.102] | +0.055 [+0.007, +0.103] | +0.040 [+0.013, +0.067] | +0.011, +0.037, +0.037 | -0.001, +0.028, +0.024 |
| scincl | h_oa | +0.333 [+0.085, +0.574] | +0.230 [-0.117, +0.510] | +0.201 [+0.011, +0.405] | +0.068, +0.122, +0.370 | -0.024, +0.002, +0.249 |
| scincl | mpd | +0.114 [+0.055, +0.167] | +0.086 [+0.010, +0.164] | +0.063 [+0.018, +0.108] | +0.019, +0.058, +0.062 | +0.003, +0.047, +0.042 |
| scincl | nov_all | +0.023 [-0.002, +0.054] | +0.019 [-0.006, +0.050] | +0.005 [-0.011, +0.019] | +0.012, +0.002, -0.008 | +0.001, -0.007, -0.023 |
| scincl | vendi | +0.469 [+0.187, +0.714] | +0.359 [+0.041, +0.726] | +0.289 [+0.111, +0.469] | +0.031, +0.217, +0.122 | -0.062, +0.149, +0.032 |
| specter2_base | disp | +0.070 [+0.033, +0.101] | +0.053 [+0.010, +0.098] | +0.038 [+0.010, +0.063] | +0.002, +0.020, +0.020 | -0.010, +0.011, +0.012 |
| specter2_base | h_oa | +0.333 [+0.085, +0.574] | +0.230 [-0.117, +0.510] | +0.201 [+0.011, +0.405] | +0.068, +0.122, +0.370 | -0.024, +0.002, +0.249 |
| specter2_base | mpd | +0.116 [+0.056, +0.170] | +0.087 [+0.011, +0.162] | +0.062 [+0.013, +0.104] | +0.004, +0.031, +0.036 | -0.013, +0.019, +0.021 |
| specter2_base | nov_all | -0.007 [-0.033, +0.025] | -0.014 [-0.038, +0.015] | -0.013 [-0.027, +0.003] | -0.005, -0.008, -0.023 | -0.020, -0.020, -0.036 |
| specter2_base | vendi | +0.399 [+0.092, +0.626] | +0.289 [-0.019, +0.617] | +0.236 [+0.050, +0.383] | -0.050, +0.119, +0.044 | -0.144, +0.048, -0.023 |
| specter2_proximity | disp | +0.063 [+0.030, +0.087] | +0.043 [+0.004, +0.083] | +0.033 [+0.006, +0.056] | +0.008, +0.027, +0.022 | -0.003, +0.017, +0.010 |
| specter2_proximity | h_oa | +0.333 [+0.085, +0.574] | +0.230 [-0.117, +0.510] | +0.201 [+0.011, +0.405] | +0.068, +0.122, +0.370 | -0.024, +0.002, +0.249 |
| specter2_proximity | mpd | +0.108 [+0.049, +0.149] | +0.072 [+0.004, +0.142] | +0.055 [+0.009, +0.096] | +0.013, +0.043, +0.039 | -0.005, +0.027, +0.016 |
| specter2_proximity | nov_all | -0.002 [-0.028, +0.025] | -0.009 [-0.031, +0.021] | -0.006 [-0.022, +0.012] | -0.000, +0.000, -0.020 | -0.012, -0.007, -0.034 |
| specter2_proximity | vendi | +0.381 [+0.137, +0.564] | +0.254 [-0.048, +0.542] | +0.226 [+0.053, +0.371] | +0.029, +0.197, +0.077 | -0.054, +0.126, -0.012 |

IPW dose against unweighted dose: sign differs in 0 of 35 model-outcome cells; interval-excludes-0 status differs in 11.

- bge_m3 h_oa: unweighted +0.333 [+0.085, +0.574] -> IPW +0.230 [-0.117, +0.510].
- bge_m3 vendi: unweighted +0.178 [+0.006, +0.318] -> IPW +0.135 [-0.096, +0.310].
- gte_qwen2_1p5b disp: unweighted +0.028 [+0.002, +0.050] -> IPW +0.015 [-0.017, +0.046].
- gte_qwen2_1p5b h_oa: unweighted +0.333 [+0.085, +0.574] -> IPW +0.230 [-0.117, +0.510].
- nomic_v15 h_oa: unweighted +0.333 [+0.085, +0.574] -> IPW +0.230 [-0.117, +0.510].
- qwen3_0p6b h_oa: unweighted +0.333 [+0.085, +0.574] -> IPW +0.230 [-0.117, +0.510].
- scincl h_oa: unweighted +0.333 [+0.085, +0.574] -> IPW +0.230 [-0.117, +0.510].
- specter2_base h_oa: unweighted +0.333 [+0.085, +0.574] -> IPW +0.230 [-0.117, +0.510].
- specter2_base vendi: unweighted +0.399 [+0.092, +0.626] -> IPW +0.289 [-0.019, +0.617].
- specter2_proximity h_oa: unweighted +0.333 [+0.085, +0.574] -> IPW +0.230 [-0.117, +0.510].
- specter2_proximity vendi: unweighted +0.381 [+0.137, +0.564] -> IPW +0.254 [-0.048, +0.542].

## 6. The weights table (reusable)

`ai-writing/data/labstudy/ipw/ipw_weights.parquet` (path from `lcommon.IPW_TABLE`, `LABSTUDY_IPW_TABLE` overrides), one row per universe paper, keyed by `paper_id` (atlas id `atl:w:...`, else `oa:<W id>`): `in_ft`, `p_ft` (cross-fitted propensity of the table's model), `p_ft_gbm`, `p_ft_logit`, `w_ft_raw` (stabilised, untrimmed), `w_ft` (stabilised, trimmed, mean 1 among selected; **use this**); the same for the abstract (`*_abs`, degenerate: do not use). NaN for papers outside the model (Georgia Tech) and for `w_*` of papers without full text. Use: `df.merge(pd.read_parquet(IPW_TABLE)[["paper_id","w_ft"]], on="paper_id")` and pass `w_ft` as a regression weight or in a Hajek mean on full-text papers; detector v3 reuses it unchanged (the selection is the availability of text, not the score) until the final paper set changes the population: then `labstudy/run_all.sh ipw` refits it.

## Not done and caveats

- IPW corrects selection on the listed covariates only (missing at random given them). Selection on unobservables (a paper whose PDF exists because its authors put it on arXiv *because* it is machine-friendly) is not addressed; the balance check cannot see it.
- The weights are held fixed in the bootstrap (weight-estimation error is not propagated); the intervals are therefore slightly too narrow for the weighted columns.
- Georgia Tech (no full text) is outside every weighted result. Full-text embeddings for Qwen3-Embedding-4B were not built, so it is absent.

