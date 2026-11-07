# Full-text selection: inverse-probability weights and what they change

Generated 2026-11-06T00:20:08Z by `ai-writing/labstudy/ipw_report.py` (`ipw.py fit`, `ipw_rerun.py`); tables in `ai-writing/data/labstudy/ipw` (git-ignored). Years 2016-2025, no 2026. Intervals: bootstrap over labs (a paper's first lab), 100 replicates for the regression re-runs, 200 for the yearly rates.

## Answer

- **Who has a full text.** 65,751 of 101,304 lab papers (2016-2025, Georgia Tech excluded: no full text at all) have a scored full text (64.9%). Selection is strong on open access (closed-access papers 12% of the full-text set against 27% of all papers), on publisher (arXiv DOI prefix 22% against 16%; IEEE 18% against 23%), school and year. The cross-fitted model separates the two sets well (AUC 0.85 logistic, 0.89 boosting).
- **Balance.** The largest standardised mean difference (SMD) over 155 covariate columns falls from 0.380 to 0.085 (logit model, the table's); 0 columns stay above the 0.1 target. Effective sample size 48,651 of 65,751 (74%); weights trimmed to [0.65, 4.32] (1st-99th percentile of the selected), mean 1.
- **Headline rates.** Share of papers with `ai_share` >= 0.25: 2024 0.110 unweighted vs 0.105 weighted; 2025 0.242 vs 0.246 (section 3: the two intervals overlap in 10 of 10 years).
**Where conclusions change.** Paper level: weighting flips the sign of the post-2022 dose-novelty coefficient in 1 of 26 model-design cells and moves an interval across 0 in 2 (section 4 lists them); lab level: sign differs in 0 of 35 model-outcome cells and the zero-status in 4 (section 5). The all-papers abstract-flag estimates are shown next to them.

## 1. The selection and the model

Outcome S = the paper has a usable local full text that the passage detector scored (`ai_share` not null). Population = every lab paper of the universe, 2016-2025 (strict labs), 120,119 papers (101,304 with school in the model). Covariates: year, school, venue type (OpenAlex `source_type`), work type, OpenAlex OA status and `is_oa`, DOI prefix (publisher key; the 40 most frequent, rest pooled), OpenAlex field and subfield, log team size, log citations, log references, number of labs. Cross-fitted (5 folds) HistGradientBoosting and a one-hot logistic regression with year x school interactions; the table's model is the one with the smaller maximum SMD after weighting (**logit**; both propensities are in the table).

Full-text coverage by school (share of papers 2016-2025 with a scored full text):

| school | papers | scored full text |
|---|---|---|
| berkeley | 11,893 | 63.9% |
| cmu | 22,514 | 68.0% |
| epfl | 11,701 | 65.5% |
| gatech | 18,815 | 0.0% |
| michigan | 10,792 | 52.3% |
| mit | 17,320 | 65.4% |
| princeton | 7,731 | 68.3% |
| stanford | 15,535 | 67.0% |
| uchicago | 3,818 | 65.7% |

By year (Georgia Tech excluded): 2016 54%; 2017 56%; 2018 59%; 2019 61%; 2020 63%; 2021 66%; 2022 69%; 2023 71%; 2024 73%; 2025 72%.

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
| 2016 | 0.0009 [0.0002, 0.0018] | 0.0010 [0.0002, 0.0021] | 0.0094 [0.0085, 0.0103] | 0.0091 [0.0082, 0.0104] |
| 2017 | 0.0002 [0.0000, 0.0007] | 0.0003 [0.0000, 0.0010] | 0.0089 [0.0083, 0.0097] | 0.0096 [0.0086, 0.0105] |
| 2018 | 0.0009 [0.0000, 0.0019] | 0.0008 [0.0000, 0.0018] | 0.0098 [0.0091, 0.0106] | 0.0103 [0.0095, 0.0111] |
| 2019 | 0.0008 [0.0002, 0.0017] | 0.0010 [0.0002, 0.0021] | 0.0098 [0.0090, 0.0107] | 0.0101 [0.0089, 0.0114] |
| 2020 | 0.0015 [0.0007, 0.0028] | 0.0022 [0.0008, 0.0039] | 0.0107 [0.0098, 0.0117] | 0.0110 [0.0099, 0.0122] |
| 2021 | 0.0014 [0.0006, 0.0022] | 0.0022 [0.0007, 0.0038] | 0.0121 [0.0112, 0.0129] | 0.0125 [0.0114, 0.0135] |
| 2022 | 0.0015 [0.0006, 0.0025] | 0.0019 [0.0006, 0.0035] | 0.0129 [0.0121, 0.0137] | 0.0135 [0.0124, 0.0148] |
| 2023 | 0.0291 [0.0243, 0.0342] | 0.0297 [0.0239, 0.0359] | 0.0353 [0.0329, 0.0380] | 0.0348 [0.0321, 0.0379] |
| 2024 | 0.1101 [0.1000, 0.1204] | 0.1054 [0.0966, 0.1156] | 0.0858 [0.0809, 0.0909] | 0.0834 [0.0784, 0.0887] |
| 2025 | 0.2423 [0.2263, 0.2616] | 0.2456 [0.2289, 0.2621] | 0.1539 [0.1471, 0.1622] | 0.1540 [0.1465, 0.1625] |

By school, 2025 (share of papers with ai_share >= 0.25):

| school | scored papers | unweighted | IPW |
|---|---|---|---|
| berkeley | 1036 | 0.219 [0.179, 0.264] | 0.228 [0.183, 0.275] |
| cmu | 1976 | 0.270 [0.241, 0.298] | 0.272 [0.244, 0.304] |
| epfl | 1036 | 0.270 [0.224, 0.321] | 0.278 [0.227, 0.332] |
| michigan | 789 | 0.276 [0.229, 0.324] | 0.282 [0.228, 0.325] |
| mit | 1345 | 0.193 [0.163, 0.223] | 0.191 [0.162, 0.224] |
| princeton | 751 | 0.205 [0.128, 0.274] | 0.217 [0.132, 0.285] |
| stanford | 1510 | 0.267 [0.234, 0.299] | 0.266 [0.228, 0.304] |
| uchicago | 352 | 0.162 [0.112, 0.227] | 0.149 [0.098, 0.195] |

## 4. Paper level: AI share against novelty (k = 3, scope all), weighted against unweighted against abstract-based

Coefficient of `nov_nn_cap` on the exposure (per unit, 0 -> 1) with a lab-bootstrap interval. `ft / unw` and `ft / IPW`: papers with a scored full text, exposure `ai_share`; `abs_all`: every paper with an abstract, exposure = its abstract flag (no full-text selection); `ft flag`: the abstract flag on the full-text papers (separates sample from exposure). Pooled = year + school + topic FE with controls; within-lab = lab x year FE. Pre = 2017-2021 placebo (the exposure there is detector noise).

| model | novelty from | design | post: ft / unw | post: ft / IPW | post: abs_all | post: ft flag / unw | post: ft flag / IPW | pre placebo: ft / unw | pre placebo: ft / IPW |
|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | abstract | pooled | -0.0033 [-0.0074, +0.0014] | -0.0033 [-0.0083, +0.0010] | -0.0007 [-0.0023, +0.0009] | -0.0008 [-0.0023, +0.0009] | -0.0006 [-0.0024, +0.0010] | +0.0137 [-0.0069, +0.0339] | +0.0192 [-0.0073, +0.0414] |
| bge_m3 | abstract | withinlab | -0.0013 [-0.0072, +0.0045] | -0.0016 [-0.0090, +0.0047] | -0.0001 [-0.0015, +0.0014] | -0.0002 [-0.0020, +0.0014] | -0.0001 [-0.0020, +0.0015] | +0.0208 [+0.0007, +0.0446] | +0.0264 [+0.0012, +0.0518] |
| bge_m3 | fulltext | pooled | +0.0272 [+0.0202, +0.0343] | +0.0261 [+0.0188, +0.0328] | -0.0007 [-0.0023, +0.0009] | -0.0008 [-0.0023, +0.0009] | -0.0006 [-0.0024, +0.0010] | +0.0141 [-0.0069, +0.0357] | +0.0143 [-0.0115, +0.0376] |
| bge_m3 | fulltext | withinlab | +0.0248 [+0.0179, +0.0323] | +0.0246 [+0.0180, +0.0322] | -0.0001 [-0.0015, +0.0014] | -0.0002 [-0.0020, +0.0014] | -0.0001 [-0.0020, +0.0015] | +0.0125 [-0.0161, +0.0418] | +0.0171 [-0.0208, +0.0459] |
| gte_qwen2_1p5b | abstract | pooled | +0.0048 [-0.0014, +0.0113] | +0.0061 [-0.0002, +0.0123] | +0.0012 [-0.0006, +0.0032] | +0.0001 [-0.0023, +0.0024] | +0.0005 [-0.0021, +0.0030] | +0.0146 [-0.0140, +0.0441] | +0.0366 [-0.0045, +0.0721] |
| gte_qwen2_1p5b | abstract | withinlab | +0.0062 [-0.0002, +0.0135] | +0.0074 [-0.0001, +0.0145] | +0.0008 [-0.0009, +0.0028] | +0.0007 [-0.0018, +0.0028] | +0.0006 [-0.0020, +0.0023] | +0.0287 [-0.0084, +0.0610] | +0.0455 [+0.0016, +0.0823] |
| gte_qwen2_1p5b | fulltext | pooled | +0.0240 [+0.0152, +0.0308] | +0.0233 [+0.0143, +0.0300] | +0.0012 [-0.0006, +0.0032] | +0.0001 [-0.0023, +0.0024] | +0.0005 [-0.0021, +0.0030] | +0.0277 [-0.0028, +0.0567] | +0.0436 [+0.0041, +0.0777] |
| gte_qwen2_1p5b | fulltext | withinlab | +0.0222 [+0.0154, +0.0303] | +0.0216 [+0.0152, +0.0290] | +0.0008 [-0.0009, +0.0028] | +0.0007 [-0.0018, +0.0028] | +0.0006 [-0.0020, +0.0023] | +0.0329 [-0.0026, +0.0583] | +0.0452 [+0.0046, +0.0824] |
| nomic_v15 | abstract | pooled | +0.0080 [+0.0027, +0.0133] | +0.0053 [-0.0011, +0.0101] | +0.0012 [-0.0003, +0.0028] | +0.0017 [-0.0006, +0.0034] | +0.0011 [-0.0015, +0.0028] | +0.0449 [+0.0132, +0.0668] | +0.0597 [+0.0217, +0.0836] |
| nomic_v15 | abstract | withinlab | +0.0086 [+0.0025, +0.0150] | +0.0061 [-0.0012, +0.0139] | +0.0007 [-0.0010, +0.0026] | +0.0013 [-0.0007, +0.0030] | +0.0005 [-0.0016, +0.0022] | +0.0479 [+0.0201, +0.0675] | +0.0586 [+0.0226, +0.0779] |
| nomic_v15 | fulltext | pooled | +0.0219 [+0.0126, +0.0284] | +0.0197 [+0.0109, +0.0265] | +0.0012 [-0.0003, +0.0028] | +0.0017 [-0.0006, +0.0034] | +0.0011 [-0.0015, +0.0028] | +0.0588 [+0.0330, +0.0919] | +0.0753 [+0.0375, +0.1125] |
| nomic_v15 | fulltext | withinlab | +0.0210 [+0.0133, +0.0280] | +0.0190 [+0.0120, +0.0256] | +0.0007 [-0.0010, +0.0026] | +0.0013 [-0.0007, +0.0030] | +0.0005 [-0.0016, +0.0022] | +0.0646 [+0.0293, +0.0917] | +0.0735 [+0.0356, +0.1063] |
| qwen3_0p6b | abstract | pooled | +0.0012 [-0.0053, +0.0088] | +0.0001 [-0.0072, +0.0071] | -0.0008 [-0.0027, +0.0013] | -0.0020 [-0.0046, +0.0006] | -0.0018 [-0.0043, +0.0008] | +0.0394 [+0.0053, +0.0628] | +0.0469 [-0.0050, +0.0730] |
| qwen3_0p6b | abstract | withinlab | +0.0067 [-0.0016, +0.0148] | +0.0067 [-0.0017, +0.0152] | +0.0009 [-0.0010, +0.0031] | +0.0001 [-0.0027, +0.0035] | +0.0004 [-0.0024, +0.0038] | +0.0567 [+0.0222, +0.0883] | +0.0687 [+0.0275, +0.0975] |
| qwen3_0p6b | fulltext | pooled | +0.0027 [-0.0071, +0.0111] | +0.0021 [-0.0084, +0.0106] | -0.0008 [-0.0027, +0.0013] | -0.0020 [-0.0046, +0.0006] | -0.0018 [-0.0043, +0.0008] | +0.0001 [-0.0346, +0.0340] | +0.0138 [-0.0304, +0.0446] |
| qwen3_0p6b | fulltext | withinlab | +0.0039 [-0.0057, +0.0142] | +0.0017 [-0.0093, +0.0115] | +0.0009 [-0.0010, +0.0031] | +0.0001 [-0.0027, +0.0035] | +0.0004 [-0.0024, +0.0038] | -0.0136 [-0.0539, +0.0225] | -0.0046 [-0.0504, +0.0248] |
| scincl | abstract | pooled | +0.0177 [+0.0103, +0.0254] | +0.0164 [+0.0089, +0.0236] | +0.0042 [+0.0025, +0.0063] | +0.0046 [+0.0019, +0.0071] | +0.0052 [+0.0025, +0.0078] | -0.0007 [-0.0344, +0.0313] | +0.0112 [-0.0255, +0.0444] |
| scincl | abstract | withinlab | +0.0108 [+0.0033, +0.0208] | +0.0091 [+0.0018, +0.0177] | +0.0018 [-0.0003, +0.0042] | +0.0022 [-0.0008, +0.0051] | +0.0013 [-0.0018, +0.0041] | +0.0343 [-0.0089, +0.0644] | +0.0422 [-0.0060, +0.0775] |
| specter2_base | abstract | pooled | -0.0081 [-0.0149, -0.0004] | -0.0083 [-0.0143, -0.0016] | -0.0047 [-0.0064, -0.0026] | -0.0049 [-0.0070, -0.0025] | -0.0049 [-0.0074, -0.0023] | +0.0048 [-0.0183, +0.0275] | +0.0212 [-0.0070, +0.0476] |
| specter2_base | abstract | withinlab | -0.0084 [-0.0167, +0.0006] | -0.0089 [-0.0177, +0.0004] | -0.0048 [-0.0066, -0.0024] | -0.0048 [-0.0073, -0.0023] | -0.0052 [-0.0078, -0.0025] | +0.0332 [-0.0085, +0.0675] | +0.0491 [+0.0051, +0.0822] |
| specter2_base | fulltext | pooled | +0.0200 [+0.0120, +0.0261] | +0.0179 [+0.0093, +0.0252] | -0.0047 [-0.0064, -0.0026] | -0.0049 [-0.0070, -0.0025] | -0.0049 [-0.0074, -0.0023] | +0.0147 [-0.0125, +0.0418] | +0.0292 [-0.0105, +0.0657] |
| specter2_base | fulltext | withinlab | +0.0208 [+0.0123, +0.0289] | +0.0198 [+0.0122, +0.0279] | -0.0048 [-0.0066, -0.0024] | -0.0048 [-0.0073, -0.0023] | -0.0052 [-0.0078, -0.0025] | +0.0462 [+0.0046, +0.0821] | +0.0576 [+0.0136, +0.1001] |
| specter2_proximity | abstract | pooled | +0.0008 [-0.0059, +0.0074] | -0.0005 [-0.0068, +0.0058] | -0.0007 [-0.0023, +0.0013] | -0.0008 [-0.0026, +0.0015] | -0.0010 [-0.0030, +0.0014] | +0.0220 [-0.0008, +0.0428] | +0.0343 [+0.0093, +0.0586] |
| specter2_proximity | abstract | withinlab | -0.0082 [-0.0149, -0.0004] | -0.0094 [-0.0171, -0.0010] | -0.0027 [-0.0045, -0.0010] | -0.0027 [-0.0055, -0.0002] | -0.0036 [-0.0064, -0.0010] | +0.0528 [+0.0148, +0.0913] | +0.0652 [+0.0229, +0.1060] |
| specter2_proximity | fulltext | pooled | +0.0285 [+0.0203, +0.0357] | +0.0264 [+0.0175, +0.0336] | -0.0007 [-0.0023, +0.0013] | -0.0008 [-0.0026, +0.0015] | -0.0010 [-0.0030, +0.0014] | +0.0390 [+0.0120, +0.0651] | +0.0514 [+0.0146, +0.0823] |
| specter2_proximity | fulltext | withinlab | +0.0243 [+0.0168, +0.0329] | +0.0233 [+0.0159, +0.0311] | -0.0027 [-0.0045, -0.0010] | -0.0027 [-0.0055, -0.0002] | -0.0036 [-0.0064, -0.0010] | +0.0670 [+0.0247, +0.0980] | +0.0783 [+0.0369, +0.1143] |

Weighting changes the sign of the post-2022 coefficient in 1 of 26 model-design cells and changes whether its interval excludes 0 in 2; the largest shift is 0.0028 (novelty sd about 0.07).
- nomic_v15 (abstract novelty, pooled): unweighted +0.0080 [+0.0027, +0.0133] -> IPW +0.0053 [-0.0011, +0.0101].
- nomic_v15 (abstract novelty, withinlab): unweighted +0.0086 [+0.0025, +0.0150] -> IPW +0.0061 [-0.0012, +0.0139].
- specter2_proximity (abstract novelty, pooled): unweighted +0.0008 [-0.0059, +0.0074] -> IPW -0.0005 [-0.0068, +0.0058].

## 5. Lab level: difference-in-differences with the dose from unweighted, IPW-weighted and abstract-flag exposure

`did` = post-2022 (2023-2025) x lab dose on a lab-year outcome with lab and year FE, per unit of dose (0 -> 1), bootstrap over labs; `placebo B` = the same on 2016-2021 with the break at B. Outcomes are the size-matched (5 papers) abstract-embedding measures of dose_lab.py. Dose kinds: `unweighted` = mean `ai_share` of the lab's scored 2023-25 papers (>= 4); `ipw` = the Hajek-weighted mean; `abstract_flag` = flagged-abstract share (all papers).

| model | outcome | did: unweighted dose | did: IPW dose | did: abstract-flag dose | placebos 2019/20/21 (unweighted) | placebos (IPW) |
|---|---|---|---|---|---|---|
| bge_m3 | disp | +0.035 [+0.001, +0.069] | +0.031 [-0.003, +0.060] | +0.019 [+0.006, +0.032] | +0.009, +0.023, +0.023 | +0.001, +0.015, +0.017 |
| bge_m3 | h_oa | +0.256 [-0.079, +0.637] | +0.238 [-0.120, +0.613] | +0.201 [+0.011, +0.405] | -0.045, +0.056, +0.460 | -0.045, +0.028, +0.408 |
| bge_m3 | mpd | +0.070 [+0.005, +0.133] | +0.061 [-0.003, +0.117] | +0.035 [+0.010, +0.061] | +0.018, +0.043, +0.046 | +0.003, +0.027, +0.033 |
| bge_m3 | nov_all | -0.001 [-0.022, +0.019] | -0.004 [-0.025, +0.018] | +0.002 [-0.008, +0.011] | +0.012, -0.006, -0.017 | +0.009, -0.009, -0.021 |
| bge_m3 | vendi | +0.150 [-0.139, +0.409] | +0.125 [-0.137, +0.359] | +0.152 [+0.071, +0.267] | +0.074, +0.229, +0.107 | +0.024, +0.170, +0.081 |
| gte_qwen2_1p5b | disp | +0.027 [-0.018, +0.079] | +0.019 [-0.023, +0.067] | +0.023 [+0.006, +0.042] | -0.017, +0.011, +0.018 | -0.029, -0.001, +0.010 |
| gte_qwen2_1p5b | h_oa | +0.256 [-0.079, +0.637] | +0.238 [-0.120, +0.613] | +0.201 [+0.011, +0.405] | -0.045, +0.056, +0.460 | -0.045, +0.028, +0.408 |
| gte_qwen2_1p5b | mpd | +0.047 [-0.034, +0.140] | +0.033 [-0.043, +0.117] | +0.038 [+0.007, +0.073] | -0.027, +0.020, +0.034 | -0.048, -0.000, +0.020 |
| gte_qwen2_1p5b | nov_all | -0.029 [-0.062, +0.006] | -0.031 [-0.063, +0.007] | -0.005 [-0.021, +0.009] | -0.017, -0.028, -0.038 | -0.024, -0.036, -0.044 |
| gte_qwen2_1p5b | vendi | +0.180 [-0.181, +0.526] | +0.129 [-0.198, +0.457] | +0.203 [+0.077, +0.344] | -0.166, +0.087, +0.026 | -0.243, +0.006, -0.022 |
| nomic_v15 | disp | +0.061 [+0.014, +0.109] | +0.053 [+0.007, +0.098] | +0.032 [+0.011, +0.054] | +0.014, +0.037, +0.037 | -0.001, +0.023, +0.026 |
| nomic_v15 | h_oa | +0.256 [-0.079, +0.637] | +0.238 [-0.120, +0.613] | +0.201 [+0.011, +0.405] | -0.045, +0.056, +0.460 | -0.045, +0.028, +0.408 |
| nomic_v15 | mpd | +0.109 [+0.026, +0.201] | +0.095 [+0.011, +0.176] | +0.056 [+0.017, +0.095] | +0.028, +0.066, +0.068 | +0.001, +0.043, +0.048 |
| nomic_v15 | nov_all | +0.020 [-0.007, +0.044] | +0.016 [-0.008, +0.042] | +0.008 [-0.003, +0.020] | +0.012, -0.003, -0.024 | +0.006, -0.009, -0.027 |
| nomic_v15 | vendi | +0.369 [-0.023, +0.713] | +0.313 [-0.049, +0.618] | +0.259 [+0.132, +0.411] | +0.067, +0.280, +0.183 | -0.030, +0.184, +0.126 |
| qwen3_0p6b | disp | +0.017 [-0.020, +0.061] | +0.013 [-0.022, +0.054] | +0.014 [-0.002, +0.034] | -0.001, +0.025, +0.022 | -0.010, +0.016, +0.016 |
| qwen3_0p6b | h_oa | +0.256 [-0.079, +0.637] | +0.238 [-0.120, +0.613] | +0.201 [+0.011, +0.405] | -0.045, +0.056, +0.460 | -0.045, +0.028, +0.408 |
| qwen3_0p6b | mpd | +0.030 [-0.038, +0.109] | +0.022 [-0.043, +0.097] | +0.023 [-0.008, +0.060] | +0.001, +0.048, +0.043 | -0.016, +0.032, +0.032 |
| qwen3_0p6b | nov_all | -0.023 [-0.062, +0.014] | -0.024 [-0.067, +0.014] | -0.007 [-0.022, +0.009] | -0.008, -0.019, -0.030 | -0.011, -0.025, -0.033 |
| qwen3_0p6b | vendi | +0.089 [-0.226, +0.384] | +0.061 [-0.250, +0.331] | +0.140 [+0.040, +0.272] | +0.049, +0.226, +0.071 | -0.018, +0.156, +0.047 |
| scincl | disp | +0.074 [+0.014, +0.142] | +0.066 [+0.005, +0.127] | +0.040 [+0.013, +0.067] | +0.007, +0.044, +0.054 | -0.007, +0.031, +0.043 |
| scincl | h_oa | +0.256 [-0.079, +0.637] | +0.238 [-0.120, +0.613] | +0.201 [+0.011, +0.405] | -0.045, +0.056, +0.460 | -0.045, +0.028, +0.408 |
| scincl | mpd | +0.120 [+0.017, +0.233] | +0.104 [-0.003, +0.205] | +0.063 [+0.018, +0.108] | +0.019, +0.074, +0.096 | -0.004, +0.054, +0.078 |
| scincl | nov_all | +0.020 [-0.017, +0.058] | +0.017 [-0.018, +0.055] | +0.005 [-0.011, +0.019] | +0.013, -0.002, -0.023 | +0.008, -0.006, -0.024 |
| scincl | vendi | +0.495 [+0.033, +0.993] | +0.423 [-0.005, +0.886] | +0.289 [+0.111, +0.469] | -0.002, +0.265, +0.167 | -0.089, +0.181, +0.110 |
| specter2_base | disp | +0.074 [+0.012, +0.143] | +0.065 [+0.008, +0.129] | +0.038 [+0.010, +0.063] | -0.005, +0.020, +0.038 | -0.016, +0.010, +0.028 |
| specter2_base | h_oa | +0.256 [-0.079, +0.637] | +0.238 [-0.120, +0.613] | +0.201 [+0.011, +0.405] | -0.045, +0.056, +0.460 | -0.045, +0.028, +0.408 |
| specter2_base | mpd | +0.125 [+0.024, +0.237] | +0.109 [+0.008, +0.213] | +0.062 [+0.013, +0.104] | -0.002, +0.034, +0.069 | -0.020, +0.018, +0.053 |
| specter2_base | nov_all | -0.021 [-0.056, +0.014] | -0.020 [-0.053, +0.016] | -0.013 [-0.027, +0.003] | -0.010, -0.015, -0.034 | -0.017, -0.019, -0.035 |
| specter2_base | vendi | +0.401 [-0.038, +0.832] | +0.348 [-0.053, +0.743] | +0.236 [+0.050, +0.383] | -0.128, +0.099, +0.083 | -0.191, +0.039, +0.038 |
| specter2_proximity | disp | +0.062 [+0.012, +0.119] | +0.055 [+0.004, +0.104] | +0.033 [+0.006, +0.056] | +0.003, +0.028, +0.029 | -0.008, +0.018, +0.022 |
| specter2_proximity | h_oa | +0.256 [-0.079, +0.637] | +0.238 [-0.120, +0.613] | +0.201 [+0.011, +0.405] | -0.045, +0.056, +0.460 | -0.045, +0.028, +0.408 |
| specter2_proximity | mpd | +0.108 [+0.012, +0.203] | +0.094 [+0.002, +0.177] | +0.055 [+0.009, +0.096] | +0.009, +0.047, +0.054 | -0.011, +0.031, +0.041 |
| specter2_proximity | nov_all | -0.011 [-0.039, +0.015] | -0.010 [-0.039, +0.016] | -0.006 [-0.022, +0.012] | +0.000, +0.001, -0.032 | -0.007, -0.002, -0.033 |
| specter2_proximity | vendi | +0.361 [-0.008, +0.731] | +0.320 [-0.022, +0.637] | +0.226 [+0.053, +0.371] | -0.024, +0.193, +0.046 | -0.090, +0.133, +0.021 |

IPW dose against unweighted dose: sign differs in 0 of 35 model-outcome cells; interval-excludes-0 status differs in 4.

- bge_m3 disp: unweighted +0.035 [+0.001, +0.069] -> IPW +0.031 [-0.003, +0.060].
- bge_m3 mpd: unweighted +0.070 [+0.005, +0.133] -> IPW +0.061 [-0.003, +0.117].
- scincl mpd: unweighted +0.120 [+0.017, +0.233] -> IPW +0.104 [-0.003, +0.205].
- scincl vendi: unweighted +0.495 [+0.033, +0.993] -> IPW +0.423 [-0.005, +0.886].

## 6. The weights table (reusable)

`ai-writing/data/labstudy/ipw/ipw_weights.parquet` (path from `lcommon.IPW_TABLE`, `LABSTUDY_IPW_TABLE` overrides), one row per universe paper, keyed by `paper_id` (atlas id `atl:w:...`, else `oa:<W id>`): `in_ft`, `p_ft` (cross-fitted propensity of the table's model), `p_ft_gbm`, `p_ft_logit`, `w_ft_raw` (stabilised, untrimmed), `w_ft` (stabilised, trimmed, mean 1 among selected; **use this**); the same for the abstract (`*_abs`, degenerate: do not use). NaN for papers outside the model (Georgia Tech) and for `w_*` of papers without full text. Use: `df.merge(pd.read_parquet(IPW_TABLE)[["paper_id","w_ft"]], on="paper_id")` and pass `w_ft` as a regression weight or in a Hajek mean on full-text papers; detector v3 reuses it unchanged (the selection is the availability of text, not the score) until the final paper set changes the population: then `labstudy/run_all.sh ipw` refits it.

## Not done and caveats

- IPW corrects selection on the listed covariates only (missing at random given them). Selection on unobservables (a paper whose PDF exists because its authors put it on arXiv *because* it is machine-friendly) is not addressed; the balance check cannot see it.
- The weights are held fixed in the bootstrap (weight-estimation error is not propagated); the intervals are therefore slightly too narrow for the weighted columns.
- Georgia Tech (no full text) is outside every weighted result. Full-text embeddings for Qwen3-Embedding-4B were not built, so it is absent.
