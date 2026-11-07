# Before/after by lab: a staggered-adoption event study of AI wording

Generated 2026-11-06T00:23:16Z by `ai-writing/labstudy/event_report.py` (`event_study.py`); tables in `ai-writing/data/labstudy/event` (git-ignored). Thresholds, outcomes and estimator were **pre-registered** in `ai-writing/labstudy/preregistration.json` (committed before any run). **Years 2016-2025 only; a lab's adoption year is the first year it exceeds the threshold for two consecutive years (so 2025 alone cannot confirm one).** Intervals are 95% percentile intervals of a bootstrap over labs (300 replicates, everything recomputed). Strict labs.

## Answer

- **Adoption.** Under the primary rule (share of a lab-year's scored papers with `ai_share` >= 0.25 above the 2016-21 floor 0.0008 + 3 SD = threshold 0.037, sustained 2 years) 359 labs adopt (cohorts {"2021.0": 1, "2022.0": 1, "2023.0": 101, "2024.0": 256}), 1432 never exceed it, 103 exceed it without sustaining, 354 exceed it only in 2025 (censored, left out), 0 have too few scored papers. Adoption is concentrated in 2023-2024 by construction of the data (the floor is the pre-ChatGPT noise), so the design has two real cohorts and few usable leads: that limits what a pre-trend test can show.
- **Overall ATT of adoption on the headline outcomes** (Callaway-Sant'Anna, never-adopter controls, post-adoption years): mpd (specter2_proximity) +0.0090 [-0.0006, +0.0199] (pre-trend p = 0.657); disp (specter2_proximity) +0.0054 [-0.0009, +0.0112] (pre-trend p = 0.699); vendi (specter2_proximity) +0.0381 [-0.0034, +0.0753] (pre-trend p = 0.430); nov3 (specter2_proximity) -0.0065 [-0.0100, -0.0022] (pre-trend p = 0.001); OpenAlex-topic entropy (h_oa) +0.0309 [-0.0264, +0.0849] (pre-trend p = 0.688); dist_centroid (bt_qwen3_0p6b) -0.0062 [-0.0122, +0.0001] (pre-trend p = 0.429).
- **Pre-trends.** The joint test that the leads (e = -5..-2) are zero rejects at 5% for 16 of 52 outcomes (main source, primary spec); with that many tests about 3 would reject by chance. Details per outcome in the grid below. Timing is not exogenous: adopters are larger labs (pre-2023 papers SMD +0.69) and more LLM-active before 2023 (LLM-text share 2021-22 SMD +0.20) than never-adopters, although among 2023+ adopters the year is unrelated to that share (rho -0.01); every ATT here is an association with adoption, not a causal effect of AI wording.
- **Wording control.** mpd (specter2_proximity): original +0.0075 [-0.0041, +0.0184], gap (ai - orig) -0.0011 [-0.0026, +0.0005]; disp (specter2_proximity): original +0.0044 [-0.0013, +0.0112], gap (ai - orig) -0.0006 [-0.0015, +0.0004]; dist_centroid (bt_qwen3_0p6b): original -0.0093 [-0.0147, -0.0031], gap (ai - orig) +0.0000 [-0.0027, +0.0026] (section 5).

## 1. Adoption definitions (pre-registered) and what they select

| spec | metric | k SD | years sustained | floor (2016-21) | SD | threshold | adopters | never | exceeded, unsustained | censored (2025 only) | cohorts (year: labs) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_primary | share_ge25 | 3 | 2 | 0.0008 | 0.0122 | 0.0373 | 359 | 1432 | 103 | 354 | {"2021.0": 1, "2022.0": 1, "2023.0": 101, "2024.0": 256} |
| S2_k2 | share_ge25 | 2 | 2 | 0.0008 | 0.0122 | 0.0251 | 365 | 1431 | 102 | 350 | {"2021.0": 1, "2022.0": 1, "2023.0": 109, "2024.0": 254} |
| S3_k5 | share_ge25 | 5 | 2 | 0.0008 | 0.0122 | 0.0616 | 340 | 1443 | 105 | 360 | {"2021.0": 1, "2022.0": 1, "2023.0": 79, "2024.0": 259} |
| S4_ge10 | share_ge10 | 3 | 2 | 0.0128 | 0.0510 | 0.1658 | 515 | 1241 | 148 | 344 | {"2016.0": 1, "2017.0": 2, "2018.0": 4, "2019.0": 3, "2020.0": 3, "2022.0": 7, "2023.0": 151, "2024.0": 344} |
| S5_mean | mean_share | 3 | 2 | 0.0102 | 0.0135 | 0.0506 | 482 | 1297 | 111 | 358 | {"2016.0": 1, "2019.0": 2, "2020.0": 2, "2022.0": 5, "2023.0": 125, "2024.0": 347} |
| S6_abstract | abs_flag | 3 | 2 | 0.0196 | 0.0590 | 0.1965 | 460 | 1002 | 269 | 517 | {"2016.0": 1, "2017.0": 2, "2018.0": 2, "2019.0": 2, "2020.0": 6, "2021.0": 4, "2022.0": 7, "2023.0": 94, "2024.0": 342} |
| S7_ipw | share_ge25_ipw | 3 | 2 | 0.0010 | 0.0155 | 0.0474 | 343 | 1444 | 103 | 358 | {"2021.0": 1, "2022.0": 1, "2023.0": 88, "2024.0": 253} |
| S8_one_year | share_ge25 | 3 | 1 | 0.0008 | 0.0122 | 0.0373 | 816 | 1432 | 0 | 0 | {"2016.0": 4, "2017.0": 1, "2018.0": 4, "2019.0": 4, "2020.0": 8, "2021.0": 9, "2022.0": 9, "2023.0": 154, "2024.0": 315, "2025.0": 308} |

Georgia Tech has no full text, so it has no adoption year in specs using full-text scores (S6 uses the abstract flag and covers it). A lab-year needs >= 3 scored papers (>= 3 abstracts for S6). The floor window precedes ChatGPT, so adoptions dated before 2023 are detector noise (reported, not removed; `post2022` sample drops them).

## 2. Headline outcomes: event-time effects

`e` = years since adoption; the base year is e = -1 (zero by construction). Leads e <= -2 test pre-trends; e >= 0 are effects. Estimate [interval]; the outcome sd (over lab-years) is in the header table.

| outcome | sd | treated labs | control labs | e=-5 | e=-4 | e=-3 | e=-2 | e=0 | e=1 | e=2 |
|---|---|---|---|---|---|---|---|---|---|---|
| mpd (specter2_proximity) | 0.1184 | 359 | 1535 | +0.004 [-0.013, +0.021] | +0.008 [-0.007, +0.023] | +0.007 [-0.005, +0.022] | +0.009 [-0.004, +0.022] | +0.007 [-0.003, +0.019] | +0.010 [-0.004, +0.024] | +0.019 [-0.001, +0.040] |
| disp (specter2_proximity) | 0.0675 | 359 | 1535 | +0.002 [-0.007, +0.012] | +0.004 [-0.004, +0.012] | +0.004 [-0.004, +0.012] | +0.005 [-0.002, +0.011] | +0.004 [-0.004, +0.011] | +0.006 [-0.002, +0.013] | +0.010 [-0.003, +0.022] |
| vendi (specter2_proximity) | 0.4474 | 359 | 1535 | -0.002 [-0.066, +0.068] | +0.029 [-0.020, +0.086] | +0.014 [-0.045, +0.067] | +0.039 [-0.008, +0.087] | +0.032 [-0.017, +0.075] | +0.043 [-0.010, +0.094] | +0.054 [-0.030, +0.130] |
| nov3 (specter2_proximity) | 0.0511 | 359 | 1535 | +0.013 [+0.007, +0.019] | +0.007 [+0.001, +0.012] | +0.002 [-0.002, +0.008] | +0.003 [-0.001, +0.008] | -0.002 [-0.006, +0.002] | -0.009 [-0.013, -0.004] | -0.011 [-0.019, -0.003] |
| OpenAlex-topic entropy (h_oa) | 0.4788 | 359 | 1535 | -0.032 [-0.112, +0.049] | +0.019 [-0.049, +0.087] | +0.007 [-0.052, +0.069] | +0.010 [-0.052, +0.065] | +0.037 [-0.022, +0.095] | +0.031 [-0.039, +0.101] | +0.010 [-0.106, +0.109] |
| dist_centroid (bt_qwen3_0p6b) | 0.0323 | 359 | 1535 | +0.006 [-0.002, +0.014] | +0.005 [-0.001, +0.011] | +0.002 [-0.003, +0.008] | +0.002 [-0.003, +0.007] | -0.004 [-0.010, +0.002] | -0.006 [-0.013, +0.001] | -0.014 [-0.024, -0.000] |

Summary statistics (primary spec; `perm p` = share of 200 random reassignments of the adoption years with an overall ATT at least as large in size; TWFE = two-way fixed-effects estimate on the same sample, which staggered adoption can bias):

| outcome | overall ATT | ATT in sd | ATT e=0..2 | pre-trend slope / yr | Wald p (leads) | perm p | TWFE static |
|---|---|---|---|---|---|---|---|
| mpd (specter2_proximity) | +0.0090 [-0.0006, +0.0199] | +0.08 | +0.0095 [-0.0004, +0.0206] | -0.00077 [-0.00476, +0.00366] | 0.657 (df 4) | 0.215 | +0.0069 [-0.0031, +0.0170] |
| disp (specter2_proximity) | +0.0054 [-0.0009, +0.0112] | +0.08 | +0.0057 [-0.0005, +0.0115] | -0.00034 [-0.00300, +0.00183] | 0.699 (df 4) | 0.260 | +0.0042 [-0.0015, +0.0100] |
| vendi (specter2_proximity) | +0.0381 [-0.0034, +0.0753] | +0.09 | +0.0397 [-0.0020, +0.0772] | +0.00142 [-0.01569, +0.01705] | 0.430 (df 4) | 0.215 | +0.0353 [-0.0044, +0.0750] |
| nov3 (specter2_proximity) | -0.0065 [-0.0100, -0.0022] | -0.13 | -0.0063 [-0.0098, -0.0021] | -0.00305 [-0.00450, -0.00148] | 0.001 (df 4) | 0.005 | -0.0095 [-0.0131, -0.0060] |
| OpenAlex-topic entropy (h_oa) | +0.0309 [-0.0264, +0.0849] | +0.06 | +0.0310 [-0.0264, +0.0852] | +0.00559 [-0.01592, +0.02547] | 0.688 (df 4) | 0.410 | +0.0225 [-0.0245, +0.0695] |
| dist_centroid (bt_qwen3_0p6b) | -0.0062 [-0.0122, +0.0001] | -0.19 | -0.0062 [-0.0122, +0.0001] | -0.00151 [-0.00329, +0.00037] | 0.429 (df 4) | 0.085 | -0.0106 [-0.0158, -0.0055] |

## 3. All outcomes (primary spec S1, original embeddings)

| outcome | treated | controls | overall ATT | in sd | pre-trend slope / yr | Wald p | ATT interval |
|---|---|---|---|---|---|---|---|
| disp (bge_m3) | 359 | 1535 | +0.0035 [+0.0001, +0.0074] | +0.09 | -0.00016 [-0.00168, +0.00119] | 0.248 | excl 0 |
| disp (gte_qwen2_1p5b) | 359 | 1535 | +0.0036 [-0.0017, +0.0090] | +0.07 | -0.00069 [-0.00258, +0.00121] | 0.476 | incl 0 |
| disp (nomic_v15) | 359 | 1535 | +0.0047 [-0.0005, +0.0107] | +0.08 | -0.00016 [-0.00240, +0.00184] | 0.826 | incl 0 |
| disp (qwen3_0p6b) | 359 | 1535 | +0.0016 [-0.0024, +0.0072] | +0.03 | -0.00032 [-0.00202, +0.00127] | 0.773 | incl 0 |
| disp (scincl) | 359 | 1535 | +0.0056 [-0.0002, +0.0116] | +0.07 | -0.00057 [-0.00315, +0.00197] | 0.738 | incl 0 |
| disp (specter2_base) | 359 | 1535 | +0.0061 [+0.0001, +0.0136] | +0.08 | +0.00021 [-0.00251, +0.00235] | 0.872 | excl 0 |
| disp (specter2_proximity) | 359 | 1535 | +0.0054 [-0.0009, +0.0112] | +0.08 | -0.00034 [-0.00300, +0.00183] | 0.699 | incl 0 |
| dist_centroid (bt_qwen3_0p6b) | 359 | 1535 | -0.0062 [-0.0122, +0.0001] | -0.19 | -0.00151 [-0.00329, +0.00037] | 0.429 | incl 0 |
| dist_centroid (oa_topic) | 359 | 1535 | -0.0055 [-0.0109, +0.0000] | -0.12 | -0.00235 [-0.00427, -0.00046] | 0.200 | incl 0 |
| dist_pre_centroid (bt_qwen3_0p6b) | 359 | 1535 | +0.0044 [+0.0010, +0.0087] | +0.20 | +0.00099 [-0.00020, +0.00212] | 0.558 | excl 0 |
| dist_pre_centroid (oa_topic) | 359 | 1535 | +0.0018 [-0.0023, +0.0059] | +0.05 | -0.00076 [-0.00227, +0.00082] | 0.768 | incl 0 |
| entropy (bt_qwen3_0p6b) | 359 | 1535 | -0.0658 [-0.1376, +0.0113] | -0.11 | -0.01199 [-0.04784, +0.02872] | 0.815 | incl 0 |
| entropy (oa_topic) | 359 | 1535 | -0.0263 [-0.0999, +0.0500] | -0.05 | +0.00186 [-0.02560, +0.03435] | 0.560 | incl 0 |
| h_bt (qwen3_0p6b) | 359 | 1535 | -0.0043 [-0.0505, +0.0454] | -0.01 | -0.00504 [-0.02164, +0.01378] | 0.767 | incl 0 |
| h_bt (specter2_proximity) | 359 | 1535 | +0.0516 [+0.0045, +0.1015] | +0.09 | -0.00564 [-0.02732, +0.01236] | 0.374 | excl 0 |
| OpenAlex-topic entropy (h_oa) | 359 | 1535 | +0.0309 [-0.0264, +0.0849] | +0.06 | +0.00559 [-0.01592, +0.02547] | 0.688 | incl 0 |
| mass_llm (bt_qwen3_0p6b) | 359 | 1535 | +0.0227 [+0.0034, +0.0427] | +0.26 | +0.00301 [-0.00030, +0.00600] | 0.028 | excl 0 |
| mpd (bge_m3) | 359 | 1535 | +0.0067 [-0.0010, +0.0133] | +0.09 | -0.00039 [-0.00340, +0.00224] | 0.299 | incl 0 |
| mpd (gte_qwen2_1p5b) | 359 | 1535 | +0.0062 [-0.0021, +0.0154] | +0.06 | -0.00154 [-0.00512, +0.00184] | 0.384 | incl 0 |
| mpd (nomic_v15) | 359 | 1535 | +0.0082 [-0.0004, +0.0166] | +0.08 | -0.00047 [-0.00387, +0.00317] | 0.818 | incl 0 |
| mpd (qwen3_0p6b) | 359 | 1535 | +0.0028 [-0.0053, +0.0118] | +0.03 | -0.00077 [-0.00431, +0.00212] | 0.725 | incl 0 |
| mpd (scincl) | 359 | 1535 | +0.0086 [-0.0036, +0.0194] | +0.06 | -0.00096 [-0.00601, +0.00412] | 0.788 | incl 0 |
| mpd (specter2_base) | 359 | 1535 | +0.0099 [-0.0034, +0.0212] | +0.08 | +0.00012 [-0.00465, +0.00427] | 0.883 | incl 0 |
| mpd (specter2_proximity) | 359 | 1535 | +0.0090 [-0.0006, +0.0199] | +0.08 | -0.00077 [-0.00476, +0.00366] | 0.657 | incl 0 |
| nov1 (bge_m3) | 359 | 1535 | -0.0065 [-0.0095, -0.0038] | -0.21 | -0.00132 [-0.00237, -0.00026] | 0.024 | excl 0 |
| nov1 (gte_qwen2_1p5b) | 359 | 1535 | -0.0101 [-0.0141, -0.0059] | -0.22 | -0.00353 [-0.00492, -0.00205] | 0.000 | excl 0 |
| nov1 (nomic_v15) | 359 | 1535 | -0.0058 [-0.0095, -0.0022] | -0.15 | -0.00175 [-0.00327, -0.00041] | 0.116 | excl 0 |
| nov1 (qwen3_0p6b) | 359 | 1535 | -0.0098 [-0.0138, -0.0058] | -0.21 | -0.00163 [-0.00349, +0.00002] | 0.040 | excl 0 |
| nov1 (scincl) | 359 | 1535 | -0.0037 [-0.0077, +0.0006] | -0.08 | -0.00327 [-0.00492, -0.00162] | 0.000 | incl 0 |
| nov1 (specter2_base) | 359 | 1535 | -0.0076 [-0.0122, -0.0032] | -0.15 | -0.00308 [-0.00488, -0.00148] | 0.005 | excl 0 |
| nov1 (specter2_proximity) | 359 | 1535 | -0.0093 [-0.0133, -0.0043] | -0.18 | -0.00316 [-0.00489, -0.00156] | 0.002 | excl 0 |
| nov3 (bge_m3) | 359 | 1535 | -0.0035 [-0.0062, -0.0004] | -0.12 | -0.00092 [-0.00208, +0.00007] | 0.275 | excl 0 |
| nov3 (gte_qwen2_1p5b) | 359 | 1535 | -0.0085 [-0.0124, -0.0047] | -0.19 | -0.00242 [-0.00402, -0.00089] | 0.014 | excl 0 |
| nov3 (nomic_v15) | 359 | 1535 | -0.0010 [-0.0040, +0.0020] | -0.03 | -0.00148 [-0.00284, -0.00004] | 0.229 | incl 0 |
| nov3 (qwen3_0p6b) | 359 | 1535 | -0.0064 [-0.0103, -0.0019] | -0.15 | -0.00116 [-0.00254, +0.00032] | 0.168 | excl 0 |
| nov3 (scincl) | 359 | 1535 | -0.0027 [-0.0066, +0.0018] | -0.06 | -0.00285 [-0.00459, -0.00113] | 0.017 | incl 0 |
| nov3 (specter2_base) | 359 | 1535 | -0.0048 [-0.0088, -0.0010] | -0.10 | -0.00326 [-0.00493, -0.00176] | 0.003 | excl 0 |
| nov3 (specter2_proximity) | 359 | 1535 | -0.0065 [-0.0100, -0.0022] | -0.13 | -0.00305 [-0.00450, -0.00148] | 0.001 | excl 0 |
| nov5 (bge_m3) | 359 | 1535 | -0.0029 [-0.0057, +0.0000] | -0.10 | -0.00032 [-0.00137, +0.00063] | 0.026 | incl 0 |
| nov5 (gte_qwen2_1p5b) | 359 | 1535 | -0.0070 [-0.0108, -0.0032] | -0.16 | -0.00141 [-0.00284, -0.00014] | 0.001 | excl 0 |
| nov5 (nomic_v15) | 359 | 1535 | -0.0025 [-0.0058, +0.0009] | -0.06 | -0.00039 [-0.00162, +0.00098] | 0.266 | incl 0 |
| nov5 (qwen3_0p6b) | 359 | 1535 | -0.0047 [-0.0081, -0.0012] | -0.11 | -0.00069 [-0.00225, +0.00088] | 0.049 | excl 0 |
| nov5 (scincl) | 359 | 1535 | -0.0017 [-0.0059, +0.0027] | -0.04 | -0.00074 [-0.00241, +0.00080] | 0.096 | incl 0 |
| nov5 (specter2_base) | 359 | 1535 | -0.0031 [-0.0074, +0.0008] | -0.06 | -0.00114 [-0.00286, +0.00028] | 0.021 | incl 0 |
| nov5 (specter2_proximity) | 359 | 1535 | -0.0044 [-0.0082, -0.0005] | -0.09 | -0.00147 [-0.00284, +0.00021] | 0.004 | excl 0 |
| vendi (bge_m3) | 359 | 1535 | +0.0243 [+0.0014, +0.0480] | +0.09 | +0.00159 [-0.00931, +0.01186] | 0.100 | excl 0 |
| vendi (gte_qwen2_1p5b) | 359 | 1535 | +0.0327 [-0.0080, +0.0717] | +0.09 | -0.00032 [-0.01514, +0.01337] | 0.245 | incl 0 |
| vendi (nomic_v15) | 359 | 1535 | +0.0382 [-0.0008, +0.0757] | +0.09 | +0.00423 [-0.01180, +0.01918] | 0.475 | incl 0 |
| vendi (qwen3_0p6b) | 359 | 1535 | +0.0178 [-0.0089, +0.0520] | +0.05 | +0.00188 [-0.01033, +0.01550] | 0.503 | incl 0 |
| vendi (scincl) | 359 | 1535 | +0.0446 [-0.0074, +0.0940] | +0.08 | +0.00097 [-0.01721, +0.01943] | 0.589 | incl 0 |
| vendi (specter2_base) | 359 | 1535 | +0.0410 [-0.0049, +0.0900] | +0.09 | +0.00482 [-0.01355, +0.02316] | 0.606 | incl 0 |
| vendi (specter2_proximity) | 359 | 1535 | +0.0381 [-0.0034, +0.0753] | +0.09 | +0.00142 [-0.01569, +0.01705] | 0.430 | incl 0 |

## 4. Sensitivity: adoption definition and control group

| outcome | spec / sample | treated | controls | overall ATT | Wald p |
|---|---|---|---|---|---|
| mpd (specter2_proximity) | S1_primary | 359 | 1535 | +0.0090 [-0.0006, +0.0199] | 0.657 |
| mpd (specter2_proximity) | S2_k2 | 365 | 1533 | +0.0093 [-0.0002, +0.0198] | 0.615 |
| mpd (specter2_proximity) | S3_k5 | 340 | 1548 | +0.0106 [-0.0016, +0.0222] | 0.522 |
| mpd (specter2_proximity) | S4_ge10 | 515 | 1389 | -0.0020 [-0.0145, +0.0083] | 0.872 |
| mpd (specter2_proximity) | S5_mean | 482 | 1408 | +0.0040 [-0.0091, +0.0173] | 0.624 |
| mpd (specter2_proximity) | S6_abstract | 460 | 1271 | +0.0177 [+0.0074, +0.0293] | 0.235 |
| mpd (specter2_proximity) | S7_ipw | 343 | 1547 | +0.0118 [-0.0006, +0.0220] | 0.554 |
| mpd (specter2_proximity) | S8_one_year | 816 | 1432 | +0.0058 [-0.0054, +0.0150] | 0.957 |
| mpd (specter2_proximity) | S1 / not-yet-treated controls | 359 | 1535 | +0.0097 [-0.0017, +0.0205] | 0.616 |
| mpd (specter2_proximity) | S1 / post-2022 adopters only | 357 | 1535 | +0.0100 [-0.0007, +0.0208] | 0.705 |
| mpd (specter2_proximity) | S1 / controls never exceed (added after registration) | 359 | 1432 | +0.0090 [-0.0010, +0.0226] | 0.640 |
| disp (specter2_proximity) | S1_primary | 359 | 1535 | +0.0054 [-0.0009, +0.0112] | 0.699 |
| disp (specter2_proximity) | S2_k2 | 365 | 1533 | +0.0056 [+0.0002, +0.0115] | 0.624 |
| disp (specter2_proximity) | S3_k5 | 340 | 1548 | +0.0062 [-0.0005, +0.0124] | 0.608 |
| disp (specter2_proximity) | S4_ge10 | 515 | 1389 | -0.0010 [-0.0073, +0.0051] | 0.829 |
| disp (specter2_proximity) | S5_mean | 482 | 1408 | +0.0027 [-0.0037, +0.0094] | 0.644 |
| disp (specter2_proximity) | S6_abstract | 460 | 1271 | +0.0098 [+0.0028, +0.0167] | 0.232 |
| disp (specter2_proximity) | S7_ipw | 343 | 1547 | +0.0069 [+0.0005, +0.0133] | 0.479 |
| disp (specter2_proximity) | S8_one_year | 816 | 1432 | +0.0035 [-0.0024, +0.0088] | 0.941 |
| disp (specter2_proximity) | S1 / not-yet-treated controls | 359 | 1535 | +0.0058 [+0.0009, +0.0120] | 0.535 |
| disp (specter2_proximity) | S1 / post-2022 adopters only | 357 | 1535 | +0.0060 [+0.0004, +0.0122] | 0.675 |
| disp (specter2_proximity) | S1 / controls never exceed (added after registration) | 359 | 1432 | +0.0054 [-0.0010, +0.0115] | 0.682 |
| vendi (specter2_proximity) | S1_primary | 359 | 1535 | +0.0381 [-0.0034, +0.0753] | 0.430 |
| vendi (specter2_proximity) | S2_k2 | 365 | 1533 | +0.0394 [-0.0053, +0.0772] | 0.374 |
| vendi (specter2_proximity) | S3_k5 | 340 | 1548 | +0.0418 [-0.0008, +0.0906] | 0.514 |
| vendi (specter2_proximity) | S4_ge10 | 515 | 1389 | -0.0086 [-0.0502, +0.0352] | 0.638 |
| vendi (specter2_proximity) | S5_mean | 482 | 1408 | +0.0246 [-0.0205, +0.0675] | 0.513 |
| vendi (specter2_proximity) | S6_abstract | 460 | 1271 | +0.0535 [+0.0033, +0.1074] | 0.287 |
| vendi (specter2_proximity) | S7_ipw | 343 | 1547 | +0.0463 [+0.0021, +0.0896] | 0.365 |
| vendi (specter2_proximity) | S8_one_year | 816 | 1432 | +0.0287 [-0.0088, +0.0640] | 0.990 |
| vendi (specter2_proximity) | S1 / not-yet-treated controls | 359 | 1535 | +0.0414 [+0.0011, +0.0833] | 0.350 |
| vendi (specter2_proximity) | S1 / post-2022 adopters only | 357 | 1535 | +0.0416 [+0.0036, +0.0823] | 0.521 |
| vendi (specter2_proximity) | S1 / controls never exceed (added after registration) | 359 | 1432 | +0.0386 [-0.0016, +0.0858] | 0.536 |
| nov3 (specter2_proximity) | S1_primary | 359 | 1535 | -0.0065 [-0.0100, -0.0022] | 0.001 |
| nov3 (specter2_proximity) | S2_k2 | 365 | 1533 | -0.0058 [-0.0103, -0.0015] | 0.003 |
| nov3 (specter2_proximity) | S3_k5 | 340 | 1548 | -0.0073 [-0.0108, -0.0025] | 0.013 |
| nov3 (specter2_proximity) | S4_ge10 | 515 | 1389 | -0.0056 [-0.0092, -0.0010] | 0.002 |
| nov3 (specter2_proximity) | S5_mean | 482 | 1408 | -0.0067 [-0.0104, -0.0026] | 0.003 |
| nov3 (specter2_proximity) | S6_abstract | 460 | 1271 | -0.0045 [-0.0083, -0.0003] | 0.875 |
| nov3 (specter2_proximity) | S7_ipw | 343 | 1547 | -0.0070 [-0.0109, -0.0027] | 0.010 |
| nov3 (specter2_proximity) | S8_one_year | 816 | 1432 | -0.0061 [-0.0092, -0.0029] | 0.015 |
| nov3 (specter2_proximity) | S1 / not-yet-treated controls | 359 | 1535 | -0.0063 [-0.0104, -0.0023] | 0.001 |
| nov3 (specter2_proximity) | S1 / post-2022 adopters only | 357 | 1535 | -0.0061 [-0.0100, -0.0019] | 0.001 |
| nov3 (specter2_proximity) | S1 / controls never exceed (added after registration) | 359 | 1432 | -0.0065 [-0.0107, -0.0028] | 0.001 |
| OpenAlex-topic entropy (h_oa) | S1_primary | 359 | 1535 | +0.0309 [-0.0264, +0.0849] | 0.688 |
| OpenAlex-topic entropy (h_oa) | S2_k2 | 365 | 1533 | +0.0279 [-0.0246, +0.0798] | 0.676 |
| OpenAlex-topic entropy (h_oa) | S3_k5 | 340 | 1548 | +0.0199 [-0.0385, +0.0792] | 0.835 |
| OpenAlex-topic entropy (h_oa) | S4_ge10 | 515 | 1389 | +0.0314 [-0.0249, +0.0844] | 0.733 |
| OpenAlex-topic entropy (h_oa) | S5_mean | 482 | 1408 | +0.0163 [-0.0289, +0.0752] | 0.613 |
| OpenAlex-topic entropy (h_oa) | S6_abstract | 460 | 1271 | +0.0054 [-0.0543, +0.0687] | 0.516 |
| OpenAlex-topic entropy (h_oa) | S7_ipw | 343 | 1547 | +0.0265 [-0.0251, +0.0784] | 0.824 |
| OpenAlex-topic entropy (h_oa) | S8_one_year | 816 | 1432 | +0.0194 [-0.0259, +0.0667] | 0.457 |
| OpenAlex-topic entropy (h_oa) | S1 / not-yet-treated controls | 359 | 1535 | +0.0315 [-0.0176, +0.0822] | 0.708 |
| OpenAlex-topic entropy (h_oa) | S1 / post-2022 adopters only | 357 | 1535 | +0.0321 [-0.0205, +0.0859] | 0.695 |
| OpenAlex-topic entropy (h_oa) | S1 / controls never exceed (added after registration) | 359 | 1432 | +0.0287 [-0.0246, +0.0780] | 0.798 |
| dist_centroid (bt_qwen3_0p6b) | S1_primary | 359 | 1535 | -0.0062 [-0.0122, +0.0001] | 0.429 |
| dist_centroid (bt_qwen3_0p6b) | S2_k2 | 365 | 1533 | -0.0069 [-0.0124, -0.0016] | 0.285 |
| dist_centroid (bt_qwen3_0p6b) | S3_k5 | 340 | 1548 | -0.0053 [-0.0104, -0.0002] | 0.265 |
| dist_centroid (bt_qwen3_0p6b) | S4_ge10 | 515 | 1389 | -0.0078 [-0.0129, -0.0024] | 0.109 |
| dist_centroid (bt_qwen3_0p6b) | S5_mean | 482 | 1408 | -0.0060 [-0.0114, -0.0015] | 0.084 |
| dist_centroid (bt_qwen3_0p6b) | S6_abstract | 460 | 1271 | -0.0034 [-0.0093, +0.0030] | 0.723 |
| dist_centroid (bt_qwen3_0p6b) | S7_ipw | 343 | 1547 | -0.0060 [-0.0110, -0.0006] | 0.282 |
| dist_centroid (bt_qwen3_0p6b) | S8_one_year | 816 | 1432 | -0.0065 [-0.0116, -0.0017] | 0.322 |
| dist_centroid (bt_qwen3_0p6b) | S1 / not-yet-treated controls | 359 | 1535 | -0.0059 [-0.0116, -0.0004] | 0.578 |
| dist_centroid (bt_qwen3_0p6b) | S1 / post-2022 adopters only | 357 | 1535 | -0.0062 [-0.0120, -0.0010] | 0.339 |
| dist_centroid (bt_qwen3_0p6b) | S1 / controls never exceed (added after registration) | 359 | 1432 | -0.0071 [-0.0124, -0.0005] | 0.620 |

## 5. Wording control (all-AI rewritten abstracts)

Geometry and topic outcomes recomputed on the Qwen2.5-7B-polished version of every abstract (same papers, same lab-years, same draws) and the event study run on the original (`orig`), the rewritten (`ai`), and their paired difference (`gap` = ai - orig). If adoption were associated with wording alone the `ai` ATT would be the same as `orig` and `gap` ~ 0 would not distinguish; the informative reading is the opposite: if the `orig` ATT is carried by content, it persists in `ai` and `gap` is about 0. Novelty has no per-paper all-AI table, so it is not part of the control.

| outcome | ATT original wording | ATT all-AI wording | gap (ai - orig) | gap pre-trend Wald p |
|---|---|---|---|---|
| disp (bge_m3) | +0.0027 [-0.0011, +0.0065] | +0.0025 [-0.0009, +0.0060] | -0.0002 [-0.0007, +0.0005] | 0.638 |
| disp (qwen3_0p6b) | +0.0014 [-0.0032, +0.0061] | +0.0040 [-0.0006, +0.0088] | +0.0027 [+0.0004, +0.0044] | 0.115 |
| disp (specter2_proximity) | +0.0044 [-0.0013, +0.0112] | +0.0039 [-0.0027, +0.0105] | -0.0006 [-0.0015, +0.0004] | 0.953 |
| dist_centroid (bt_qwen3_0p6b) | -0.0093 [-0.0147, -0.0031] | -0.0093 [-0.0161, -0.0038] | +0.0000 [-0.0027, +0.0026] | 0.531 |
| dist_centroid (bt_specter2_proximity) | -0.0062 [-0.0120, +0.0001] | -0.0062 [-0.0120, -0.0007] | +0.0000 [-0.0022, +0.0020] | 0.381 |
| mass_llm (bt_qwen3_0p6b) | +0.0221 [-0.0021, +0.0463] | +0.0218 [-0.0001, +0.0437] | -0.0002 [-0.0086, +0.0084] | 0.689 |
| mass_llm (bt_specter2_proximity) | +0.0408 [+0.0123, +0.0633] | +0.0381 [+0.0164, +0.0613] | -0.0027 [-0.0089, +0.0035] | 0.371 |
| mpd (bge_m3) | +0.0054 [-0.0020, +0.0122] | +0.0050 [-0.0019, +0.0123] | -0.0004 [-0.0015, +0.0007] | 0.590 |
| mpd (qwen3_0p6b) | +0.0025 [-0.0074, +0.0119] | +0.0073 [-0.0024, +0.0159] | +0.0048 [+0.0010, +0.0086] | 0.125 |
| mpd (specter2_proximity) | +0.0075 [-0.0041, +0.0184] | +0.0064 [-0.0059, +0.0188] | -0.0011 [-0.0026, +0.0005] | 0.910 |
| vendi (bge_m3) | +0.0192 [-0.0084, +0.0481] | +0.0195 [-0.0103, +0.0504] | +0.0004 [-0.0038, +0.0052] | 0.777 |
| vendi (qwen3_0p6b) | +0.0166 [-0.0215, +0.0523] | +0.0366 [-0.0016, +0.0767] | +0.0200 [+0.0086, +0.0342] | 0.094 |
| vendi (specter2_proximity) | +0.0342 [-0.0146, +0.0803] | +0.0313 [-0.0106, +0.0753] | -0.0029 [-0.0105, +0.0045] | 0.959 |

## 6. Is adoption timing endogenous?

Adopters (primary spec) against labs that never exceed the threshold, on features measured before 2023. SMD = standardised mean difference (adopters - controls).

| feature | adopters | never-adopters | SMD | n adopters | n controls |
|---|---|---|---|---|---|
| n_pre | 79.569 | 36.403 | +0.69 | 327 | 1388 |
| llm_share_2021_22 | 0.037 | 0.019 | +0.20 | 325 | 1159 |
| llm_share_change | 0.026 | 0.012 | +0.19 | 263 | 985 |

Among 2023+ adopters, Spearman correlation of adoption year with the lab's share of LLM-text papers in 2021-22: rho = -0.009 (p = 0.8770, n = 323); negative means labs already writing about LLMs adopt earlier.

Share of labs that adopt, by department type: cs 19% of 1044; ee 15% of 207; eecs 23% of 149; engineering 19% of 216; life_medical 40% of 30; math_stats 10% of 83; other 30% of 27; social_business 16% of 136; unknown 0% of 2.

## Not done and caveats

- **Identification.** Adoption is detected from the lab's own papers, so it is correlated with lab size and with early engagement in LLM topics; never-adopters are mostly small labs. The ATT compares adopters with never-adopters after differencing out the lab and the base year; it does not remove a differential trend that starts at adoption (e.g. a lab moving to LLM topics and to AI-polished text together). Treat it as an association with the timing of adoption.
- **Few leads.** Nearly all adopters adopt in 2023-2024, so e = -5..-2 draw on 2017-2022 with two cohorts; the Wald test has limited power, and a non-rejection is weak evidence of parallel trends.
- Heterogeneity-robust estimator is Callaway-Sant'Anna without covariates (Sun-Abraham not run); TWFE is shown only for comparison. Outcomes are size-matched on 5 papers (geometry) or >= 3 papers (novelty), so small lab-years drop out of the panel.
