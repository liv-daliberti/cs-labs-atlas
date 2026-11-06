# Before/after by lab: a staggered-adoption event study of AI wording

Generated 2026-11-06T03:42:07Z by `ai-writing/labstudy/event_report.py` (`event_study.py`); tables in `ai-writing/data/labstudy/event` (git-ignored). Thresholds, outcomes and estimator were **pre-registered** in `ai-writing/labstudy/preregistration.json` (committed before any run). **Years 2016-2025 only; a lab's adoption year is the first year it exceeds the threshold for two consecutive years (so 2025 alone cannot confirm one).** Intervals are 95% percentile intervals of a bootstrap over labs (300 replicates, everything recomputed). Strict labs.

## Answer

- **Adoption.** Under the primary rule (share of a lab-year's scored papers with `ai_share` >= 0.25 above the 2016-21 floor 0.0000 + 3 SD = threshold 0.006, sustained 2 years) 500 labs adopt (cohorts {"2022.0": 4, "2023.0": 183, "2024.0": 313}), 1258 never exceed it, 144 exceed it without sustaining, 346 exceed it only in 2025 (censored, left out), 0 have too few scored papers. Adoption is concentrated in 2023-2024 by construction of the data (the floor is the pre-ChatGPT noise), so the design has two real cohorts and few usable leads: that limits what a pre-trend test can show.
- **Overall ATT of adoption on the headline outcomes** (Callaway-Sant'Anna, never-adopter controls, post-adoption years): mpd (specter2_proximity) +0.0059 [-0.0060, +0.0163] (pre-trend p = 0.930); disp (specter2_proximity) +0.0036 [-0.0029, +0.0100] (pre-trend p = 0.920); vendi (specter2_proximity) +0.0221 [-0.0153, +0.0610] (pre-trend p = 0.937); nov3 (specter2_proximity) -0.0071 [-0.0105, -0.0038] (pre-trend p = 0.002); OpenAlex-topic entropy (h_oa) +0.0204 [-0.0316, +0.0716] (pre-trend p = 0.279); dist_centroid (bt_qwen3_0p6b) -0.0134 [-0.0190, -0.0074] (pre-trend p = 0.043).
- **Pre-trends.** The joint test that the leads (e = -5..-2) are zero rejects at 5% for 15 of 52 outcomes (main source, primary spec); with that many tests about 3 would reject by chance. Details per outcome in the grid below. Timing is not exogenous: adopters are larger labs (pre-2023 papers SMD +0.72) and more LLM-active before 2023 (LLM-text share 2021-22 SMD +0.24) than never-adopters, although among 2023+ adopters the year is unrelated to that share (rho -0.10); every ATT here is an association with adoption, not a causal effect of AI wording.
- **Wording control.** mpd (specter2_proximity): original +0.0049 [-0.0059, +0.0168], gap (ai - orig) +0.0004 [-0.0011, +0.0023]; disp (specter2_proximity): original +0.0031 [-0.0043, +0.0094], gap (ai - orig) +0.0003 [-0.0008, +0.0012]; dist_centroid (bt_qwen3_0p6b): original -0.0157 [-0.0218, -0.0088], gap (ai - orig) -0.0007 [-0.0035, +0.0022] (section 5).

## 1. Adoption definitions (pre-registered) and what they select

| spec | metric | k SD | years sustained | floor (2016-21) | SD | threshold | adopters | never | exceeded, unsustained | censored (2025 only) | cohorts (year: labs) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_primary | share_ge25 | 3 | 2 | 0.0000 | 0.0020 | 0.0059 | 500 | 1258 | 144 | 346 | {"2022.0": 4, "2023.0": 183, "2024.0": 313} |
| S2_k2 | share_ge25 | 2 | 2 | 0.0000 | 0.0020 | 0.0039 | 500 | 1258 | 144 | 346 | {"2022.0": 4, "2023.0": 183, "2024.0": 313} |
| S3_k5 | share_ge25 | 5 | 2 | 0.0000 | 0.0020 | 0.0098 | 500 | 1258 | 144 | 346 | {"2022.0": 4, "2023.0": 183, "2024.0": 313} |
| S4_ge10 | share_ge10 | 3 | 2 | 0.0029 | 0.0252 | 0.0784 | 681 | 1064 | 172 | 331 | {"2017.0": 1, "2019.0": 1, "2022.0": 13, "2023.0": 286, "2024.0": 380} |
| S5_mean | mean_share | 3 | 2 | 0.0035 | 0.0064 | 0.0227 | 712 | 1027 | 176 | 333 | {"2019.0": 1, "2022.0": 12, "2023.0": 303, "2024.0": 396} |
| S6_abstract | abs_flag | 3 | 2 | 0.0196 | 0.0590 | 0.1965 | 460 | 1002 | 269 | 517 | {"2016.0": 1, "2017.0": 2, "2018.0": 2, "2019.0": 2, "2020.0": 6, "2021.0": 4, "2022.0": 7, "2023.0": 94, "2024.0": 342} |
| S7_ipw | share_ge25_ipw | 3 | 2 | 0.0002 | 0.0083 | 0.0250 | 430 | 1399 | 118 | 301 | {"2022.0": 2, "2023.0": 145, "2024.0": 283} |
| S8_one_year | share_ge25 | 3 | 1 | 0.0000 | 0.0020 | 0.0059 | 990 | 1258 | 0 | 0 | {"2016.0": 1, "2017.0": 2, "2019.0": 2, "2021.0": 1, "2022.0": 10, "2023.0": 240, "2024.0": 421, "2025.0": 313} |

Georgia Tech has no full text, so it has no adoption year in specs using full-text scores (S6 uses the abstract flag and covers it). A lab-year needs >= 3 scored papers (>= 3 abstracts for S6). The floor window precedes ChatGPT, so adoptions dated before 2023 are detector noise (reported, not removed; `post2022` sample drops them).

## 2. Headline outcomes: event-time effects

`e` = years since adoption; the base year is e = -1 (zero by construction). Leads e <= -2 test pre-trends; e >= 0 are effects. Estimate [interval]; the outcome sd (over lab-years) is in the header table.

| outcome | sd | treated labs | control labs | e=-5 | e=-4 | e=-3 | e=-2 | e=0 | e=1 | e=2 |
|---|---|---|---|---|---|---|---|---|---|---|
| mpd (specter2_proximity) | 0.1184 | 500 | 1402 | -0.006 [-0.021, +0.011] | -0.003 [-0.018, +0.012] | -0.001 [-0.015, +0.013] | -0.004 [-0.015, +0.006] | -0.001 [-0.012, +0.010] | +0.007 [-0.007, +0.020] | +0.019 [-0.002, +0.039] |
| disp (specter2_proximity) | 0.0675 | 500 | 1402 | -0.003 [-0.012, +0.007] | -0.001 [-0.009, +0.007] | -0.001 [-0.007, +0.008] | -0.002 [-0.008, +0.003] | -0.000 [-0.007, +0.006] | +0.004 [-0.004, +0.012] | +0.011 [-0.001, +0.023] |
| vendi (specter2_proximity) | 0.4474 | 500 | 1402 | -0.028 [-0.095, +0.026] | -0.013 [-0.068, +0.041] | -0.010 [-0.065, +0.040] | -0.009 [-0.052, +0.031] | +0.004 [-0.036, +0.056] | +0.025 [-0.024, +0.074] | +0.056 [-0.015, +0.136] |
| nov3 (specter2_proximity) | 0.0511 | 500 | 1402 | +0.011 [+0.004, +0.016] | +0.009 [+0.004, +0.015] | +0.003 [-0.002, +0.006] | +0.004 [+0.000, +0.007] | -0.004 [-0.007, +0.000] | -0.009 [-0.014, -0.004] | -0.011 [-0.017, -0.004] |
| OpenAlex-topic entropy (h_oa) | 0.4788 | 500 | 1402 | -0.068 [-0.136, +0.005] | -0.056 [-0.124, +0.018] | -0.060 [-0.117, -0.000] | -0.034 [-0.093, +0.019] | +0.016 [-0.037, +0.070] | +0.023 [-0.042, +0.089] | +0.024 [-0.072, +0.125] |
| dist_centroid (bt_qwen3_0p6b) | 0.0323 | 500 | 1402 | +0.008 [+0.000, +0.015] | +0.008 [+0.003, +0.013] | +0.006 [+0.001, +0.011] | +0.004 [-0.000, +0.008] | -0.008 [-0.013, -0.003] | -0.012 [-0.019, -0.005] | -0.029 [-0.040, -0.017] |

Summary statistics (primary spec; `perm p` = share of 200 random reassignments of the adoption years with an overall ATT at least as large in size; TWFE = two-way fixed-effects estimate on the same sample, which staggered adoption can bias):

| outcome | overall ATT | ATT in sd | ATT e=0..2 | pre-trend slope / yr | Wald p (leads) | perm p | TWFE static |
|---|---|---|---|---|---|---|---|
| mpd (specter2_proximity) | +0.0059 [-0.0060, +0.0163] | +0.05 | +0.0056 [-0.0062, +0.0161] | +0.00103 [-0.00287, +0.00506] | 0.930 (df 4) | 0.405 | +0.0089 [-0.0003, +0.0182] |
| disp (specter2_proximity) | +0.0036 [-0.0029, +0.0100] | +0.05 | +0.0034 [-0.0031, +0.0099] | +0.00054 [-0.00192, +0.00259] | 0.920 (df 4) | 0.355 | +0.0051 [-0.0002, +0.0105] |
| vendi (specter2_proximity) | +0.0221 [-0.0153, +0.0610] | +0.05 | +0.0212 [-0.0159, +0.0595] | +0.00599 [-0.00709, +0.02136] | 0.937 (df 4) | 0.415 | +0.0399 [+0.0037, +0.0762] |
| nov3 (specter2_proximity) | -0.0071 [-0.0105, -0.0038] | -0.14 | -0.0070 [-0.0104, -0.0037] | -0.00265 [-0.00410, -0.00102] | 0.002 (df 4) | 0.000 | -0.0105 [-0.0138, -0.0072] |
| OpenAlex-topic entropy (h_oa) | +0.0204 [-0.0316, +0.0716] | +0.04 | +0.0200 [-0.0321, +0.0700] | +0.01581 [-0.00168, +0.03517] | 0.279 (df 4) | 0.475 | +0.0426 [-0.0018, +0.0869] |
| dist_centroid (bt_qwen3_0p6b) | -0.0134 [-0.0190, -0.0074] | -0.42 | -0.0134 [-0.0190, -0.0074] | -0.00195 [-0.00359, -0.00020] | 0.043 (df 4) | 0.000 | -0.0151 [-0.0198, -0.0104] |

## 3. All outcomes (primary spec S1, original embeddings)

| outcome | treated | controls | overall ATT | in sd | pre-trend slope / yr | Wald p | ATT interval |
|---|---|---|---|---|---|---|---|
| disp (bge_m3) | 500 | 1402 | +0.0023 [-0.0011, +0.0061] | +0.06 | +0.00026 [-0.00113, +0.00167] | 0.895 | incl 0 |
| disp (gte_qwen2_1p5b) | 500 | 1402 | +0.0015 [-0.0026, +0.0070] | +0.03 | +0.00024 [-0.00175, +0.00201] | 0.999 | incl 0 |
| disp (nomic_v15) | 500 | 1402 | +0.0045 [-0.0013, +0.0098] | +0.08 | +0.00065 [-0.00143, +0.00252] | 0.940 | incl 0 |
| disp (qwen3_0p6b) | 500 | 1402 | -0.0004 [-0.0046, +0.0043] | -0.01 | +0.00081 [-0.00072, +0.00241] | 0.881 | incl 0 |
| disp (scincl) | 500 | 1402 | +0.0035 [-0.0044, +0.0095] | +0.04 | +0.00011 [-0.00275, +0.00297] | 0.790 | incl 0 |
| disp (specter2_base) | 500 | 1402 | +0.0038 [-0.0044, +0.0110] | +0.05 | +0.00128 [-0.00133, +0.00396] | 0.594 | incl 0 |
| disp (specter2_proximity) | 500 | 1402 | +0.0036 [-0.0029, +0.0100] | +0.05 | +0.00054 [-0.00192, +0.00259] | 0.920 | incl 0 |
| dist_centroid (bt_qwen3_0p6b) | 500 | 1402 | -0.0134 [-0.0190, -0.0074] | -0.42 | -0.00195 [-0.00359, -0.00020] | 0.043 | excl 0 |
| dist_centroid (oa_topic) | 500 | 1402 | -0.0078 [-0.0128, -0.0032] | -0.16 | -0.00273 [-0.00444, -0.00076] | 0.047 | excl 0 |
| dist_pre_centroid (bt_qwen3_0p6b) | 500 | 1402 | +0.0037 [+0.0005, +0.0076] | +0.17 | +0.00135 [-0.00010, +0.00254] | 0.286 | excl 0 |
| dist_pre_centroid (oa_topic) | 500 | 1402 | +0.0021 [-0.0017, +0.0057] | +0.06 | -0.00051 [-0.00183, +0.00088] | 0.952 | incl 0 |
| entropy (bt_qwen3_0p6b) | 500 | 1402 | -0.0483 [-0.1249, +0.0223] | -0.08 | -0.01620 [-0.05100, +0.02369] | 0.363 | incl 0 |
| entropy (oa_topic) | 500 | 1402 | -0.0459 [-0.1264, +0.0433] | -0.08 | +0.01358 [-0.01806, +0.04480] | 0.034 | incl 0 |
| h_bt (qwen3_0p6b) | 500 | 1402 | -0.0153 [-0.0649, +0.0332] | -0.03 | +0.00027 [-0.01730, +0.01929] | 0.360 | incl 0 |
| h_bt (specter2_proximity) | 500 | 1402 | +0.0207 [-0.0250, +0.0741] | +0.04 | +0.00273 [-0.01674, +0.02227] | 0.610 | incl 0 |
| OpenAlex-topic entropy (h_oa) | 500 | 1402 | +0.0204 [-0.0316, +0.0716] | +0.04 | +0.01581 [-0.00168, +0.03517] | 0.279 | incl 0 |
| mass_llm (bt_qwen3_0p6b) | 500 | 1402 | +0.0311 [+0.0086, +0.0499] | +0.36 | +0.00361 [+0.00062, +0.00651] | 0.029 | excl 0 |
| mpd (bge_m3) | 500 | 1402 | +0.0044 [-0.0025, +0.0118] | +0.06 | +0.00060 [-0.00215, +0.00270] | 0.889 | incl 0 |
| mpd (gte_qwen2_1p5b) | 500 | 1402 | +0.0023 [-0.0070, +0.0112] | +0.02 | +0.00045 [-0.00320, +0.00363] | 0.999 | incl 0 |
| mpd (nomic_v15) | 500 | 1402 | +0.0081 [-0.0015, +0.0172] | +0.08 | +0.00125 [-0.00203, +0.00482] | 0.913 | incl 0 |
| mpd (qwen3_0p6b) | 500 | 1402 | -0.0011 [-0.0101, +0.0083] | -0.01 | +0.00150 [-0.00153, +0.00422] | 0.903 | incl 0 |
| mpd (scincl) | 500 | 1402 | +0.0056 [-0.0054, +0.0181] | +0.04 | +0.00041 [-0.00384, +0.00466] | 0.824 | incl 0 |
| mpd (specter2_base) | 500 | 1402 | +0.0062 [-0.0043, +0.0188] | +0.05 | +0.00216 [-0.00227, +0.00646] | 0.654 | incl 0 |
| mpd (specter2_proximity) | 500 | 1402 | +0.0059 [-0.0060, +0.0163] | +0.05 | +0.00103 [-0.00287, +0.00506] | 0.930 | incl 0 |
| nov1 (bge_m3) | 500 | 1402 | -0.0062 [-0.0090, -0.0030] | -0.20 | -0.00126 [-0.00226, -0.00032] | 0.020 | excl 0 |
| nov1 (gte_qwen2_1p5b) | 500 | 1402 | -0.0106 [-0.0146, -0.0066] | -0.23 | -0.00322 [-0.00452, -0.00174] | 0.000 | excl 0 |
| nov1 (nomic_v15) | 500 | 1402 | -0.0033 [-0.0068, +0.0004] | -0.08 | -0.00160 [-0.00300, -0.00038] | 0.104 | incl 0 |
| nov1 (qwen3_0p6b) | 500 | 1402 | -0.0110 [-0.0151, -0.0071] | -0.24 | -0.00080 [-0.00233, +0.00057] | 0.847 | excl 0 |
| nov1 (scincl) | 500 | 1402 | -0.0033 [-0.0079, +0.0003] | -0.07 | -0.00306 [-0.00494, -0.00159] | 0.002 | incl 0 |
| nov1 (specter2_base) | 500 | 1402 | -0.0087 [-0.0122, -0.0049] | -0.17 | -0.00243 [-0.00396, -0.00087] | 0.038 | excl 0 |
| nov1 (specter2_proximity) | 500 | 1402 | -0.0093 [-0.0130, -0.0055] | -0.18 | -0.00256 [-0.00390, -0.00113] | 0.016 | excl 0 |
| nov3 (bge_m3) | 500 | 1402 | -0.0035 [-0.0064, -0.0006] | -0.12 | -0.00086 [-0.00185, +0.00006] | 0.197 | excl 0 |
| nov3 (gte_qwen2_1p5b) | 500 | 1402 | -0.0102 [-0.0140, -0.0068] | -0.23 | -0.00235 [-0.00369, -0.00075] | 0.018 | excl 0 |
| nov3 (nomic_v15) | 500 | 1402 | -0.0016 [-0.0051, +0.0020] | -0.04 | -0.00131 [-0.00239, -0.00009] | 0.185 | incl 0 |
| nov3 (qwen3_0p6b) | 500 | 1402 | -0.0088 [-0.0127, -0.0046] | -0.20 | -0.00062 [-0.00221, +0.00091] | 0.213 | excl 0 |
| nov3 (scincl) | 500 | 1402 | -0.0040 [-0.0072, +0.0011] | -0.08 | -0.00267 [-0.00416, -0.00093] | 0.025 | incl 0 |
| nov3 (specter2_base) | 500 | 1402 | -0.0063 [-0.0101, -0.0020] | -0.13 | -0.00285 [-0.00430, -0.00143] | 0.001 | excl 0 |
| nov3 (specter2_proximity) | 500 | 1402 | -0.0071 [-0.0105, -0.0038] | -0.14 | -0.00265 [-0.00410, -0.00102] | 0.002 | excl 0 |
| nov5 (bge_m3) | 500 | 1402 | -0.0033 [-0.0062, -0.0007] | -0.11 | -0.00020 [-0.00118, +0.00066] | 0.210 | excl 0 |
| nov5 (gte_qwen2_1p5b) | 500 | 1402 | -0.0089 [-0.0134, -0.0052] | -0.20 | -0.00127 [-0.00249, -0.00012] | 0.027 | excl 0 |
| nov5 (nomic_v15) | 500 | 1402 | -0.0024 [-0.0059, +0.0009] | -0.06 | +0.00006 [-0.00117, +0.00146] | 0.501 | incl 0 |
| nov5 (qwen3_0p6b) | 500 | 1402 | -0.0060 [-0.0095, -0.0025] | -0.14 | -0.00051 [-0.00197, +0.00087] | 0.333 | excl 0 |
| nov5 (scincl) | 500 | 1402 | -0.0045 [-0.0082, +0.0002] | -0.09 | -0.00094 [-0.00244, +0.00044] | 0.117 | incl 0 |
| nov5 (specter2_base) | 500 | 1402 | -0.0072 [-0.0106, -0.0032] | -0.15 | -0.00097 [-0.00247, +0.00051] | 0.074 | excl 0 |
| nov5 (specter2_proximity) | 500 | 1402 | -0.0080 [-0.0115, -0.0041] | -0.16 | -0.00142 [-0.00274, +0.00017] | 0.014 | excl 0 |
| vendi (bge_m3) | 500 | 1402 | +0.0129 [-0.0121, +0.0375] | +0.05 | +0.00251 [-0.00666, +0.01197] | 0.879 | incl 0 |
| vendi (gte_qwen2_1p5b) | 500 | 1402 | +0.0125 [-0.0269, +0.0546] | +0.03 | +0.00484 [-0.00838, +0.01837] | 0.951 | incl 0 |
| vendi (nomic_v15) | 500 | 1402 | +0.0313 [-0.0098, +0.0715] | +0.08 | +0.00905 [-0.00360, +0.02206] | 0.658 | incl 0 |
| vendi (qwen3_0p6b) | 500 | 1402 | +0.0029 [-0.0318, +0.0366] | +0.01 | +0.00884 [-0.00501, +0.02069] | 0.728 | incl 0 |
| vendi (scincl) | 500 | 1402 | +0.0241 [-0.0160, +0.0716] | +0.05 | +0.00579 [-0.01110, +0.02494] | 0.824 | incl 0 |
| vendi (specter2_base) | 500 | 1402 | +0.0177 [-0.0287, +0.0587] | +0.04 | +0.01192 [-0.00704, +0.03006] | 0.594 | incl 0 |
| vendi (specter2_proximity) | 500 | 1402 | +0.0221 [-0.0153, +0.0610] | +0.05 | +0.00599 [-0.00709, +0.02136] | 0.937 | incl 0 |

## 4. Sensitivity: adoption definition and control group

| outcome | spec / sample | treated | controls | overall ATT | Wald p |
|---|---|---|---|---|---|
| mpd (specter2_proximity) | S1_primary | 500 | 1402 | +0.0059 [-0.0060, +0.0163] | 0.930 |
| mpd (specter2_proximity) | S2_k2 | 500 | 1402 | +0.0059 [-0.0054, +0.0163] | 0.946 |
| mpd (specter2_proximity) | S3_k5 | 500 | 1402 | +0.0059 [-0.0048, +0.0159] | 0.931 |
| mpd (specter2_proximity) | S4_ge10 | 681 | 1236 | +0.0073 [-0.0036, +0.0170] | 0.582 |
| mpd (specter2_proximity) | S5_mean | 712 | 1203 | +0.0100 [-0.0015, +0.0231] | 0.354 |
| mpd (specter2_proximity) | S6_abstract | 460 | 1271 | +0.0177 [+0.0074, +0.0293] | 0.235 |
| mpd (specter2_proximity) | S7_ipw | 430 | 1517 | -0.0006 [-0.0118, +0.0091] | 0.961 |
| mpd (specter2_proximity) | S8_one_year | 990 | 1258 | +0.0085 [-0.0004, +0.0180] | 0.461 |
| mpd (specter2_proximity) | S1 / not-yet-treated controls | 500 | 1402 | +0.0056 [-0.0048, +0.0151] | 0.749 |
| mpd (specter2_proximity) | S1 / post-2022 adopters only | 496 | 1402 | +0.0046 [-0.0065, +0.0151] | 0.949 |
| mpd (specter2_proximity) | S1 / controls never exceed (added after registration) | 500 | 1258 | +0.0087 [-0.0026, +0.0184] | 0.908 |
| disp (specter2_proximity) | S1_primary | 500 | 1402 | +0.0036 [-0.0029, +0.0100] | 0.920 |
| disp (specter2_proximity) | S2_k2 | 500 | 1402 | +0.0036 [-0.0024, +0.0094] | 0.920 |
| disp (specter2_proximity) | S3_k5 | 500 | 1402 | +0.0036 [-0.0027, +0.0101] | 0.932 |
| disp (specter2_proximity) | S4_ge10 | 681 | 1236 | +0.0040 [-0.0036, +0.0106] | 0.598 |
| disp (specter2_proximity) | S5_mean | 712 | 1203 | +0.0057 [-0.0019, +0.0119] | 0.392 |
| disp (specter2_proximity) | S6_abstract | 460 | 1271 | +0.0098 [+0.0028, +0.0167] | 0.232 |
| disp (specter2_proximity) | S7_ipw | 430 | 1517 | -0.0001 [-0.0063, +0.0048] | 0.960 |
| disp (specter2_proximity) | S8_one_year | 990 | 1258 | +0.0049 [-0.0008, +0.0104] | 0.296 |
| disp (specter2_proximity) | S1 / not-yet-treated controls | 500 | 1402 | +0.0035 [-0.0028, +0.0090] | 0.778 |
| disp (specter2_proximity) | S1 / post-2022 adopters only | 496 | 1402 | +0.0029 [-0.0033, +0.0095] | 0.927 |
| disp (specter2_proximity) | S1 / controls never exceed (added after registration) | 500 | 1258 | +0.0052 [-0.0005, +0.0111] | 0.860 |
| vendi (specter2_proximity) | S1_primary | 500 | 1402 | +0.0221 [-0.0153, +0.0610] | 0.937 |
| vendi (specter2_proximity) | S2_k2 | 500 | 1402 | +0.0221 [-0.0197, +0.0633] | 0.934 |
| vendi (specter2_proximity) | S3_k5 | 500 | 1402 | +0.0221 [-0.0195, +0.0604] | 0.951 |
| vendi (specter2_proximity) | S4_ge10 | 681 | 1236 | +0.0213 [-0.0214, +0.0640] | 0.663 |
| vendi (specter2_proximity) | S5_mean | 712 | 1203 | +0.0372 [-0.0106, +0.0772] | 0.660 |
| vendi (specter2_proximity) | S6_abstract | 460 | 1271 | +0.0535 [+0.0033, +0.1074] | 0.287 |
| vendi (specter2_proximity) | S7_ipw | 430 | 1517 | -0.0004 [-0.0336, +0.0456] | 0.934 |
| vendi (specter2_proximity) | S8_one_year | 990 | 1258 | +0.0324 [-0.0074, +0.0678] | 0.322 |
| vendi (specter2_proximity) | S1 / not-yet-treated controls | 500 | 1402 | +0.0220 [-0.0152, +0.0702] | 0.684 |
| vendi (specter2_proximity) | S1 / post-2022 adopters only | 496 | 1402 | +0.0173 [-0.0263, +0.0538] | 0.937 |
| vendi (specter2_proximity) | S1 / controls never exceed (added after registration) | 500 | 1258 | +0.0341 [-0.0086, +0.0778] | 0.916 |
| nov3 (specter2_proximity) | S1_primary | 500 | 1402 | -0.0071 [-0.0105, -0.0038] | 0.002 |
| nov3 (specter2_proximity) | S2_k2 | 500 | 1402 | -0.0071 [-0.0100, -0.0034] | 0.007 |
| nov3 (specter2_proximity) | S3_k5 | 500 | 1402 | -0.0071 [-0.0110, -0.0033] | 0.003 |
| nov3 (specter2_proximity) | S4_ge10 | 681 | 1236 | -0.0066 [-0.0105, -0.0024] | 0.000 |
| nov3 (specter2_proximity) | S5_mean | 712 | 1203 | -0.0088 [-0.0121, -0.0049] | 0.008 |
| nov3 (specter2_proximity) | S6_abstract | 460 | 1271 | -0.0045 [-0.0083, -0.0003] | 0.875 |
| nov3 (specter2_proximity) | S7_ipw | 430 | 1517 | -0.0069 [-0.0106, -0.0033] | 0.005 |
| nov3 (specter2_proximity) | S8_one_year | 990 | 1258 | -0.0058 [-0.0090, -0.0025] | 0.016 |
| nov3 (specter2_proximity) | S1 / not-yet-treated controls | 500 | 1402 | -0.0069 [-0.0102, -0.0034] | 0.003 |
| nov3 (specter2_proximity) | S1 / post-2022 adopters only | 496 | 1402 | -0.0071 [-0.0104, -0.0032] | 0.005 |
| nov3 (specter2_proximity) | S1 / controls never exceed (added after registration) | 500 | 1258 | -0.0067 [-0.0108, -0.0026] | 0.004 |
| OpenAlex-topic entropy (h_oa) | S1_primary | 500 | 1402 | +0.0204 [-0.0316, +0.0716] | 0.279 |
| OpenAlex-topic entropy (h_oa) | S2_k2 | 500 | 1402 | +0.0204 [-0.0408, +0.0779] | 0.328 |
| OpenAlex-topic entropy (h_oa) | S3_k5 | 500 | 1402 | +0.0204 [-0.0334, +0.0697] | 0.278 |
| OpenAlex-topic entropy (h_oa) | S4_ge10 | 681 | 1236 | +0.0057 [-0.0454, +0.0647] | 0.109 |
| OpenAlex-topic entropy (h_oa) | S5_mean | 712 | 1203 | +0.0184 [-0.0446, +0.0874] | 0.623 |
| OpenAlex-topic entropy (h_oa) | S6_abstract | 460 | 1271 | +0.0054 [-0.0543, +0.0687] | 0.516 |
| OpenAlex-topic entropy (h_oa) | S7_ipw | 430 | 1517 | -0.0030 [-0.0540, +0.0454] | 0.814 |
| OpenAlex-topic entropy (h_oa) | S8_one_year | 990 | 1258 | +0.0175 [-0.0268, +0.0680] | 0.088 |
| OpenAlex-topic entropy (h_oa) | S1 / not-yet-treated controls | 500 | 1402 | +0.0164 [-0.0339, +0.0730] | 0.186 |
| OpenAlex-topic entropy (h_oa) | S1 / post-2022 adopters only | 496 | 1402 | +0.0177 [-0.0330, +0.0677] | 0.475 |
| OpenAlex-topic entropy (h_oa) | S1 / controls never exceed (added after registration) | 500 | 1258 | +0.0226 [-0.0372, +0.0786] | 0.321 |
| dist_centroid (bt_qwen3_0p6b) | S1_primary | 500 | 1402 | -0.0134 [-0.0190, -0.0074] | 0.043 |
| dist_centroid (bt_qwen3_0p6b) | S2_k2 | 500 | 1402 | -0.0134 [-0.0192, -0.0077] | 0.100 |
| dist_centroid (bt_qwen3_0p6b) | S3_k5 | 500 | 1402 | -0.0134 [-0.0193, -0.0080] | 0.054 |
| dist_centroid (bt_qwen3_0p6b) | S4_ge10 | 681 | 1236 | -0.0116 [-0.0161, -0.0065] | 0.003 |
| dist_centroid (bt_qwen3_0p6b) | S5_mean | 712 | 1203 | -0.0140 [-0.0187, -0.0089] | 0.066 |
| dist_centroid (bt_qwen3_0p6b) | S6_abstract | 460 | 1271 | -0.0034 [-0.0093, +0.0030] | 0.723 |
| dist_centroid (bt_qwen3_0p6b) | S7_ipw | 430 | 1517 | -0.0100 [-0.0156, -0.0047] | 0.291 |
| dist_centroid (bt_qwen3_0p6b) | S8_one_year | 990 | 1258 | -0.0139 [-0.0200, -0.0071] | 0.153 |
| dist_centroid (bt_qwen3_0p6b) | S1 / not-yet-treated controls | 500 | 1402 | -0.0128 [-0.0186, -0.0067] | 0.125 |
| dist_centroid (bt_qwen3_0p6b) | S1 / post-2022 adopters only | 496 | 1402 | -0.0136 [-0.0197, -0.0074] | 0.074 |
| dist_centroid (bt_qwen3_0p6b) | S1 / controls never exceed (added after registration) | 500 | 1258 | -0.0155 [-0.0227, -0.0083] | 0.279 |

## 5. Wording control (all-AI rewritten abstracts)

Geometry and topic outcomes recomputed on the Qwen2.5-7B-polished version of every abstract (same papers, same lab-years, same draws) and the event study run on the original (`orig`), the rewritten (`ai`), and their paired difference (`gap` = ai - orig). If adoption were associated with wording alone the `ai` ATT would be the same as `orig` and `gap` ~ 0 would not distinguish; the informative reading is the opposite: if the `orig` ATT is carried by content, it persists in `ai` and `gap` is about 0. Novelty has no per-paper all-AI table, so it is not part of the control.

| outcome | ATT original wording | ATT all-AI wording | gap (ai - orig) | gap pre-trend Wald p |
|---|---|---|---|---|
| disp (bge_m3) | +0.0023 [-0.0014, +0.0063] | +0.0022 [-0.0015, +0.0062] | -0.0001 [-0.0007, +0.0005] | 0.941 |
| disp (qwen3_0p6b) | +0.0005 [-0.0048, +0.0057] | +0.0029 [-0.0026, +0.0082] | +0.0024 [+0.0002, +0.0041] | 0.246 |
| disp (specter2_proximity) | +0.0031 [-0.0043, +0.0094] | +0.0033 [-0.0026, +0.0108] | +0.0003 [-0.0008, +0.0012] | 0.969 |
| dist_centroid (bt_qwen3_0p6b) | -0.0157 [-0.0218, -0.0088] | -0.0164 [-0.0235, -0.0097] | -0.0007 [-0.0035, +0.0022] | 0.346 |
| dist_centroid (bt_specter2_proximity) | -0.0139 [-0.0194, -0.0088] | -0.0115 [-0.0175, -0.0058] | +0.0024 [+0.0001, +0.0047] | 0.141 |
| mass_llm (bt_qwen3_0p6b) | +0.0473 [+0.0237, +0.0712] | +0.0495 [+0.0260, +0.0682] | +0.0021 [-0.0079, +0.0115] | 0.439 |
| mass_llm (bt_specter2_proximity) | +0.0469 [+0.0203, +0.0714] | +0.0502 [+0.0225, +0.0780] | +0.0033 [-0.0006, +0.0080] | 0.847 |
| mpd (bge_m3) | +0.0044 [-0.0033, +0.0112] | +0.0042 [-0.0028, +0.0106] | -0.0001 [-0.0015, +0.0010] | 0.918 |
| mpd (qwen3_0p6b) | +0.0007 [-0.0094, +0.0090] | +0.0050 [-0.0048, +0.0139] | +0.0043 [+0.0004, +0.0082] | 0.248 |
| mpd (specter2_proximity) | +0.0049 [-0.0059, +0.0168] | +0.0053 [-0.0065, +0.0160] | +0.0004 [-0.0011, +0.0023] | 0.929 |
| vendi (bge_m3) | +0.0169 [-0.0058, +0.0456] | +0.0173 [-0.0069, +0.0455] | +0.0004 [-0.0036, +0.0050] | 0.963 |
| vendi (qwen3_0p6b) | +0.0095 [-0.0237, +0.0467] | +0.0255 [-0.0065, +0.0626] | +0.0160 [+0.0031, +0.0293] | 0.095 |
| vendi (specter2_proximity) | +0.0218 [-0.0212, +0.0656] | +0.0222 [-0.0211, +0.0685] | +0.0004 [-0.0067, +0.0082] | 0.798 |

## 6. Is adoption timing endogenous?

Adopters (primary spec) against labs that never exceed the threshold, on features measured before 2023. SMD = standardised mean difference (adopters - controls).

| feature | adopters | never-adopters | SMD | n adopters | n controls |
|---|---|---|---|---|---|
| n_pre | 78.341 | 34.155 | +0.72 | 449 | 1272 |
| llm_share_2021_22 | 0.038 | 0.015 | +0.24 | 447 | 1045 |
| llm_share_change | 0.026 | 0.011 | +0.20 | 357 | 900 |

Among 2023+ adopters, Spearman correlation of adoption year with the lab's share of LLM-text papers in 2021-22: rho = -0.103 (p = 0.0306, n = 443); negative means labs already writing about LLMs adopt earlier.

Share of labs that adopt, by department type: cs 28% of 1050; ee 22% of 200; eecs 30% of 160; engineering 26% of 209; life_medical 40% of 30; math_stats 12% of 85; other 28% of 29; social_business 18% of 137; unknown 0% of 2.

## Not done and caveats

- **Identification.** Adoption is detected from the lab's own papers, so it is correlated with lab size and with early engagement in LLM topics; never-adopters are mostly small labs. The ATT compares adopters with never-adopters after differencing out the lab and the base year; it does not remove a differential trend that starts at adoption (e.g. a lab moving to LLM topics and to AI-polished text together). Treat it as an association with the timing of adoption.
- **Few leads.** Nearly all adopters adopt in 2023-2024, so e = -5..-2 draw on 2017-2022 with two cohorts; the Wald test has limited power, and a non-rejection is weak evidence of parallel trends.
- Heterogeneity-robust estimator is Callaway-Sant'Anna without covariates (Sun-Abraham not run); TWFE is shown only for comparison. Outcomes are size-matched on 5 papers (geometry) or >= 3 papers (novelty), so small lab-years drop out of the panel.

