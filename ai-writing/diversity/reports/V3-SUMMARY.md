# Every AI-detection result, rerun on detector v3 (v2 and v3 side by side)

Owner decision 2026-11-05: "rescore everything with v3". **v3 shares are not comparable in level with v2 shares**: v3 flags at a 0.3% false-alarm threshold (v2: 1%), abstains on passages under 100 words or heading-heavy (5.6% of test passages; excluded, with their share shown), and scores the main body only. Compare direction, not level. Headline condition: **main body only**; intervals are 95%; 2026 is in no series; detector-training papers (`trained_on_v3`) are out of every false-alarm floor and placebo.

**Detector v3 error table** (`detector_v3/results/tables.md`): human passages wrongly flagged 0.30% (0.27-0.32%); misses on model families never seen in training 0.9-6.6% (leave-one-family-out; Qwen the hardest); partial edits (a human text with some sentences rewritten) are missed far more often (about 10-47% by generator) and are reported separately, not folded into the calibration figure.

**Appendix false-alarm check** (2016-2021 appendix passages, papers outside the training split, 4,728 papers / 38,097 passages): flagged 0.32% [0.25, 0.41]; main body 0.35% [0.33, 0.37]. Limit 1.5%: **passes**, so main + appendix is shown as the secondary condition (one column below).

## 1. How much AI, by year and school

Papers with a scored full text (share of passages flagged >= 25% is the "AI paper" cut of the site pages), all schools, home-school papers; v2 = 1% threshold, whole body; v3 = main body, 0.3% threshold.

| year | v2: papers >= 25% flagged | v3: papers >= 25% flagged | v2: mean dose | v3: mean dose | v3 abstained passages | v3 mean dose, main + appendix |
|---|---|---|---|---|---|---|
| 2016 | 0.09% [0.02, 0.18] (n=4,431) | 0.02% [0.00, 0.06] (n=5,173) | 0.94% [0.86, 1.02] | 0.22% [0.20, 0.25] | 2.5% | 0.22% |
| 2017 | 0.02% [0.00, 0.06] (n=4,902) | 0.03% [0.00, 0.09] (n=5,858) | 0.89% [0.83, 0.96] | 0.23% [0.20, 0.26] | 2.4% | 0.23% |
| 2018 | 0.09% [0.02, 0.15] (n=5,851) | 0.01% [0.00, 0.04] (n=6,943) | 0.98% [0.92, 1.04] | 0.25% [0.23, 0.28] | 2.6% | 0.25% |
| 2019 | 0.08% [0.02, 0.17] (n=5,982) | 0.03% [0.00, 0.07] (n=7,278) | 0.98% [0.92, 1.05] | 0.26% [0.23, 0.29] | 2.6% | 0.25% |
| 2020 | 0.15% [0.08, 0.26] (n=6,505) | 0.00% [0.00, 0.00] (n=8,090) | 1.07% [0.99, 1.15] | 0.27% [0.24, 0.29] | 2.7% | 0.27% |
| 2021 | 0.14% [0.07, 0.23] (n=7,071) | 0.02% [0.00, 0.06] (n=8,546) | 1.21% [1.13, 1.29] | 0.33% [0.30, 0.36] | 2.7% | 0.33% |
| 2022 | 0.15% [0.06, 0.25] (n=6,692) | 0.13% [0.05, 0.20] (n=7,925) | 1.29% [1.22, 1.36] | 0.46% [0.42, 0.50] | 2.8% | 0.46% |
| 2023 | 2.91% [2.56, 3.27] (n=7,467) | 3.98% [3.56, 4.33] (n=8,912) | 3.53% [3.36, 3.71] | 3.30% [3.09, 3.49] | 2.9% | 3.27% |
| 2024 | 11.01% [10.36, 11.64] (n=8,055) | 16.47% [15.70, 17.24] (n=9,603) | 8.58% [8.26, 8.90] | 10.77% [10.38, 11.14] | 3.2% | 10.55% |
| 2025 | 24.23% [23.44, 25.12] (n=8,795) | 28.17% [27.34, 29.11] (n=10,300) | 15.39% [15.00, 15.81] | 17.79% [17.36, 18.23] | 3.4% | 17.40% |

By school (home papers):

| school (home) | v2 2025: >= 25% flagged | v3 2025: >= 25% flagged | v3 n | v3 2023 | v3 2024 |
|---|---|---|---|---|---|
| berkeley | 21.9% [19.5, 24.1] (n=1036) | 22.9% [20.7, 25.2] | 1100 | 4.5% [3.3, 6.0] | 15.2% [13.1, 17.5] |
| cmu | 27.0% [25.2, 28.8] (n=1976) | 31.2% [29.5, 33.3] | 2132 | 5.2% [4.3, 6.3] | 18.7% [17.0, 20.4] |
| epfl | 27.0% [24.2, 29.8] (n=1036) | 30.5% [27.8, 33.3] | 1106 | 4.8% [3.4, 6.1] | 17.8% [15.6, 20.1] |
| gatech | n=0, too few | 38.6% [35.4, 41.6] | 958 | 5.6% [4.3, 6.9] | 23.9% [21.3, 26.6] |
| michigan | 27.6% [24.5, 30.9] (n=789) | 30.3% [27.6, 33.5] | 821 | 4.6% [3.0, 6.4] | 16.9% [14.5, 19.5] |
| mit | 19.3% [17.0, 21.5] (n=1345) | 22.3% [20.1, 24.2] | 1455 | 2.6% [1.9, 3.5] | 11.3% [9.7, 13.1] |
| princeton | 20.5% [17.7, 23.7] (n=751) | 20.5% [17.9, 23.8] | 774 | 1.1% [0.5, 2.3] | 12.1% [10.0, 14.6] |
| stanford | 26.7% [24.2, 28.8] (n=1510) | 30.1% [27.9, 32.5] | 1586 | 3.3% [2.4, 4.2] | 15.1% [13.4, 17.0] |
| uchicago | 16.2% [12.5, 20.5] (n=352) | 18.5% [14.7, 22.4] | 368 | 1.5% [0.3, 2.6] | 14.4% [11.3, 18.0] |


## 2. Dose versus novelty and diversity (paper level)

Coefficient of embedding novelty (size-matched, k = 3, scope all) on ai_share, 0 -> 1, cluster bootstrap over labs, 2023-2025 (post) and the 2017-2021 placebo (v3: papers outside the detector training split only).

| model | design | v2 post | v3 post | v2 placebo 2017-21 | v3 placebo 2017-21 (out of sample) | direction |
|---|---|---|---|---|---|---|
| bge_m3 | pooled | -0.0033 [-0.0075, +0.0015] | -0.0036 [-0.0072, +0.0005] | +0.0137 [-0.0076, +0.0326] | -0.0162 [-0.0630, +0.0301] | same sign, v3 includes 0 |
| bge_m3 | withinlab | -0.0013 [-0.0068, +0.0043] | -0.0004 [-0.0049, +0.0046] | +0.0208 [-0.0019, +0.0446] | -0.0095 [-0.0714, +0.0298] | same sign, v3 includes 0 |
| gte_qwen2_1p5b | pooled | +0.0048 [-0.0018, +0.0116] | +0.0021 [-0.0031, +0.0072] | +0.0146 [-0.0138, +0.0452] | -0.0131 [-0.0746, +0.0513] | same sign, v3 includes 0 |
| gte_qwen2_1p5b | withinlab | +0.0062 [-0.0007, +0.0136] | +0.0040 [-0.0014, +0.0105] | +0.0287 [-0.0058, +0.0619] | +0.0049 [-0.0720, +0.0647] | same sign, v3 includes 0 |
| nomic_v15 | pooled | +0.0080 [+0.0024, +0.0133] | +0.0040 [-0.0007, +0.0088] | +0.0449 [+0.0184, +0.0695] | -0.0097 [-0.0549, +0.0403] | same sign, v3 includes 0 |
| nomic_v15 | withinlab | +0.0086 [+0.0024, +0.0151] | +0.0054 [+0.0002, +0.0117] | +0.0479 [+0.0187, +0.0724] | -0.0149 [-0.0755, +0.0333] | same sign, v3 excludes 0 |
| qwen3_0p6b | pooled | +0.0012 [-0.0057, +0.0082] | -0.0015 [-0.0063, +0.0037] | +0.0394 [+0.0108, +0.0691] | -0.0269 [-0.0828, +0.0375] | sign flips, v3 includes 0 |
| qwen3_0p6b | withinlab | +0.0067 [-0.0018, +0.0153] | +0.0027 [-0.0047, +0.0103] | +0.0567 [+0.0231, +0.0891] | -0.0062 [-0.0843, +0.0565] | same sign, v3 includes 0 |
| scincl | pooled | +0.0177 [+0.0104, +0.0252] | +0.0141 [+0.0087, +0.0190] | -0.0007 [-0.0361, +0.0329] | -0.0378 [-0.0937, +0.0223] | same sign, v3 excludes 0 |
| scincl | withinlab | +0.0108 [+0.0028, +0.0197] | +0.0101 [+0.0042, +0.0164] | +0.0343 [-0.0129, +0.0683] | -0.0148 [-0.1029, +0.0473] | same sign, v3 excludes 0 |
| specter2_base | pooled | -0.0081 [-0.0147, -0.0004] | -0.0075 [-0.0124, -0.0020] | +0.0048 [-0.0188, +0.0313] | -0.0456 [-0.1021, +0.0186] | same sign, v3 excludes 0 |
| specter2_base | withinlab | -0.0084 [-0.0163, -0.0007] | -0.0070 [-0.0132, -0.0017] | +0.0332 [-0.0087, +0.0680] | -0.0179 [-0.0887, +0.0506] | same sign, v3 excludes 0 |
| specter2_proximity | pooled | +0.0008 [-0.0057, +0.0079] | -0.0008 [-0.0062, +0.0053] | +0.0220 [-0.0017, +0.0485] | -0.0350 [-0.0824, +0.0202] | sign flips, v3 includes 0 |
| specter2_proximity | withinlab | -0.0082 [-0.0157, -0.0007] | -0.0078 [-0.0132, -0.0030] | +0.0528 [+0.0132, +0.0899] | -0.0270 [-0.1116, +0.0517] | same sign, v3 excludes 0 |

Lab level (difference-in-differences of lab-year diversity on the lab AI dose; placebo break 2019), abstract embeddings:

| model | outcome | v2 DiD | v3 DiD | v2 placebo 2019 | v3 placebo 2019 |
|---|---|---|---|---|---|
| bge_m3 | disp | +0.035 [+0.005, +0.078] | +0.032 [+0.013, +0.052] | +0.009 [-0.019, +0.042] | +0.012 [-0.011, +0.040] |
| bge_m3 | mpd | +0.070 [+0.012, +0.152] | +0.062 [+0.028, +0.102] | +0.018 [-0.035, +0.083] | +0.023 [-0.023, +0.071] |
| bge_m3 | vendi | +0.152 [-0.080, +0.466] | +0.180 [+0.001, +0.341] | +0.074 [-0.164, +0.335] | +0.112 [-0.075, +0.306] |
| gte_qwen2_1p5b | disp | +0.027 [-0.018, +0.087] | +0.028 [+0.002, +0.059] | -0.017 [-0.056, +0.031] | -0.003 [-0.032, +0.031] |
| gte_qwen2_1p5b | mpd | +0.048 [-0.037, +0.154] | +0.049 [+0.002, +0.104] | -0.027 [-0.097, +0.059] | -0.006 [-0.058, +0.053] |
| gte_qwen2_1p5b | vendi | +0.183 [-0.136, +0.609] | +0.203 [-0.001, +0.422] | -0.167 [-0.484, +0.201] | -0.032 [-0.260, +0.206] |
| nomic_v15 | disp | +0.061 [+0.015, +0.127] | +0.058 [+0.029, +0.091] | +0.013 [-0.028, +0.056] | +0.021 [-0.007, +0.054] |
| nomic_v15 | mpd | +0.110 [+0.025, +0.224] | +0.105 [+0.054, +0.161] | +0.027 [-0.045, +0.103] | +0.037 [-0.016, +0.096] |
| nomic_v15 | vendi | +0.372 [+0.046, +0.813] | +0.394 [+0.157, +0.663] | +0.066 [-0.234, +0.394] | +0.137 [-0.081, +0.376] |
| qwen3_0p6b | disp | +0.017 [-0.023, +0.061] | +0.014 [-0.010, +0.040] | -0.001 [-0.033, +0.038] | +0.004 [-0.021, +0.033] |
| qwen3_0p6b | mpd | +0.030 [-0.044, +0.112] | +0.024 [-0.021, +0.073] | +0.001 [-0.059, +0.073] | +0.005 [-0.040, +0.060] |
| qwen3_0p6b | vendi | +0.092 [-0.199, +0.410] | +0.091 [-0.096, +0.308] | +0.048 [-0.238, +0.336] | +0.085 [-0.145, +0.325] |
| scincl | disp | +0.075 [+0.021, +0.148] | +0.070 [+0.031, +0.106] | +0.007 [-0.047, +0.071] | +0.012 [-0.032, +0.058] |
| scincl | mpd | +0.121 [+0.027, +0.246] | +0.113 [+0.052, +0.175] | +0.019 [-0.073, +0.126] | +0.019 [-0.042, +0.093] |
| scincl | vendi | +0.500 [+0.084, +0.979] | +0.463 [+0.192, +0.742] | -0.003 [-0.443, +0.409] | +0.037 [-0.280, +0.395] |
| specter2_base | disp | +0.075 [+0.015, +0.153] | +0.068 [+0.030, +0.105] | -0.005 [-0.063, +0.051] | +0.002 [-0.038, +0.043] |
| specter2_base | mpd | +0.126 [+0.027, +0.260] | +0.114 [+0.053, +0.177] | -0.003 [-0.101, +0.093] | +0.004 [-0.063, +0.069] |
| specter2_base | vendi | +0.406 [+0.027, +0.935] | +0.390 [+0.138, +0.664] | -0.129 [-0.557, +0.249] | -0.038 [-0.325, +0.263] |
| specter2_proximity | disp | +0.062 [+0.008, +0.131] | +0.062 [+0.028, +0.099] | +0.003 [-0.050, +0.060] | +0.009 [-0.025, +0.046] |
| specter2_proximity | mpd | +0.109 [+0.016, +0.227] | +0.106 [+0.047, +0.170] | +0.009 [-0.082, +0.108] | +0.015 [-0.044, +0.073] |
| specter2_proximity | vendi | +0.365 [+0.020, +0.811] | +0.371 [+0.118, +0.649] | -0.024 [-0.407, +0.335] | +0.043 [-0.220, +0.313] |


## 3. All-AI rewrite

The all-AI rewrite study (`ALL-AI-REWRITE.md`: every abstract rewritten by Qwen2.5-7B, then embedded) does not depend on the passage detector; its numbers are unchanged. The abstract-level detector there is still v1. Where v3 enters is the AI-versus-not groups: the topic-matched test and `ai_vs_not` (AI paper = >= 25% flagged main-body passages) with the wording control on rewritten abstracts; see the site data `matched_test.json` and `ai_vs_not.json.gz` in the new site-data directory.

## 5. Lineage (student-advisor similarity)

v2 report: `exp-lineage-style/ai-writing/diversity/reports/LINEAGE.md`; v3 report: `exp-lineage-style/ai-writing/diversity/reports/LINEAGE-v3.md`.

**v2**

> **Numbers below come from the tables of this report; each bullet is generated, so a re-run on new data rewrites them.**
> - **student-advisor similarity, candidate links (the large sample), abstracts, 7 models.** Post-2023 change inside labs -0.0126 to +0.0058; interval wholly below zero in 5 models, wholly above in 0; placebo breaks (2019-2021) -0.0146 to -0.0023; the post interval lies wholly outside the placebo range in 1 of 7 models.
> - **student-student similarity, candidate links (the large sample), abstracts, 7 models.** Post-2023 change inside labs -0.0144 to +0.0020; interval wholly below zero in 5 models, wholly above in 0; placebo breaks (2019-2021) -0.0215 to -0.0055; the post interval lies wholly outside the placebo range in 0 of 7 models.
> - **student-advisor similarity, verified links (the thin sample), abstracts, 7 models.** Post-2023 change inside labs -0.0121 to +0.0108; interval wholly below zero in 1 models, wholly above in 0; placebo breaks (2019-2021) -0.0116 to +0.0091; the post interval lies wholly outside the placebo range in 0 of 7 models.
> - **student-student similarity, verified links (the thin sample), abstracts, 7 models.** Post-2023 change inside labs -0.0289 to +0.0071; interval wholly below zero in 0 models, wholly above in 0; placebo breaks (2019-2021) -0.0127 to +0.0213; the post interval lies wholly outside the placebo range in 0 of 7 models.
> - **AI dose, student-advisor similarity, abstracts, exposure `ai_share`.** Among 2023-2025 papers the coefficient (0 to 1 exposure, lab and year fixed effects) is -0.0414 to -0.0175 across 7 models, interval excluding zero in 7; the 2017-2021 placebo is -0.0088 to +0.0880 with every interval including zero in 7 of 7 models.
> - **AI dose, student-advisor similarity, abstracts, exposure `flag_abstract`.** Among 2023-2025 papers the coefficient (0 to 1 exposure, lab and year fixed effects) is -0.0116 to -0.0050 across 7 models, interval excluding zero in 6; the 2017-2021 placebo is -0.0011 to +0.0065 with every interval including zero in 7 of 7 models.
> - **Wording.** The post effect on the all-AI rewrites of the same papers is almost the same as on the originals: the gap (the part carried by wording) is -0.0029 to +0.0031 in cosine units (median |gap| / |effect| = 0.10 over model x measure; ratios are unstable where the effect is near zero). Convergence or divergence that is there after rewriting is content, not wording.
> - **Reading of the 2026-11-05 run (hand-written; check it against the bullets above after a re-run).** Students' abstracts after 2023 are slightly less similar to their advisor's recent work and sit slightly further from the lab centroid in most models (not SPECTER2-base), but the pre-2022 trend runs the same way, so the post break is not distinguishable from the existing drift at the pooled level. What does stand out from the placebo is the dose: within 2023-2025, a student paper with more AI-flagged text sits further from the advisor, consistently across models, and about as strongly after rewriting (content, not wording). It is an association between papers of the same lab and year, not a

**v3**

> **Numbers below come from the tables of this report; each bullet is generated, so a re-run on new data rewrites them.**
> - **student-advisor similarity, candidate links (the large sample), abstracts, 7 models.** Post-2023 change inside labs -0.0126 to +0.0058; interval wholly below zero in 5 models, wholly above in 0; placebo breaks (2019-2021) -0.0146 to -0.0023; the post interval lies wholly outside the placebo range in 1 of 7 models.
> - **student-student similarity, candidate links (the large sample), abstracts, 7 models.** Post-2023 change inside labs -0.0144 to +0.0020; interval wholly below zero in 5 models, wholly above in 0; placebo breaks (2019-2021) -0.0215 to -0.0055; the post interval lies wholly outside the placebo range in 0 of 7 models.
> - **student-advisor similarity, verified links (the thin sample), abstracts, 7 models.** Post-2023 change inside labs -0.0121 to +0.0108; interval wholly below zero in 1 models, wholly above in 0; placebo breaks (2019-2021) -0.0116 to +0.0091; the post interval lies wholly outside the placebo range in 0 of 7 models.
> - **student-student similarity, verified links (the thin sample), abstracts, 7 models.** Post-2023 change inside labs -0.0289 to +0.0071; interval wholly below zero in 0 models, wholly above in 0; placebo breaks (2019-2021) -0.0127 to +0.0213; the post interval lies wholly outside the placebo range in 0 of 7 models.
> - **AI dose, student-advisor similarity, abstracts, exposure `ai_share`.** Among 2023-2025 papers the coefficient (0 to 1 exposure, lab and year fixed effects) is -0.0355 to -0.0142 across 7 models, interval excluding zero in 7; the 2017-2021 placebo is +0.0043 to +0.1133 with every interval including zero in 7 of 7 models.
> - **AI dose, student-advisor similarity, abstracts, exposure `flag_abstract`.** Among 2023-2025 papers the coefficient (0 to 1 exposure, lab and year fixed effects) is -0.0116 to -0.0050 across 7 models, interval excluding zero in 6; the 2017-2021 placebo is -0.0065 to +0.0124 with every interval including zero in 7 of 7 models.
> - **Wording.** The post effect on the all-AI rewrites of the same papers is almost the same as on the originals: the gap (the part carried by wording) is -0.0029 to +0.0031 in cosine units (median |gap| / |effect| = 0.10 over model x measure; ratios are unstable where the effect is near zero). Convergence or divergence that is there after rewriting is content, not wording.
> - **Reading of the 2026-11-05 run (hand-written; check it against the bullets above after a re-run).** Students' abstracts after 2023 are slightly less similar to their advisor's recent work and sit slightly further from the lab centroid in most models (not SPECTER2-base), but the pre-2022 trend runs the same way, so the post break is not distinguishable from the existing drift at the pooled level. What does stand out from the placebo is the dose: within 2023-2025, a student paper with more AI-flagged text sits further from the advisor, consistently across models, and about as strongly after rewriting (content, not wording). It is an association between papers of the same lab and year, not a


## 6. Writing style

v2 report: `exp-lineage-style/ai-writing/diversity/reports/STYLE-HOMOGENIZATION.md`; v3 report: `exp-lineage-style/ai-writing/diversity/reports/STYLE-HOMOGENIZATION-v3.md`.

**v2**

> - **abstract, topic removed:** dispersion of style vectors changes by +0.0326 [+0.0213, +0.0425] (+3.0% of its pre level) after 2022 (placebo breaks +0.0050 to +0.0114); distance to the 2016-2021 corpus centroid +0.0496 [+0.0379, +0.0598] (+4.6%; placebo +0.0047 to +0.0112).
> - **abstract, raw style:** dispersion of style vectors changes by +0.0331 [+0.0215, +0.0476] (+3.0% of its pre level) after 2022 (placebo breaks +0.0081 to +0.0147); distance to the 2016-2021 corpus centroid +0.0594 [+0.0475, +0.0736] (+5.3%; placebo +0.0074 to +0.0145).
> - **fulltext, topic removed:** dispersion of style vectors changes by +0.0274 [+0.0110, +0.0406] (+2.6% of its pre level) after 2022 (placebo breaks -0.0059 to +0.0016); distance to the 2016-2021 corpus centroid +0.0476 [+0.0314, +0.0606] (+4.4%; placebo -0.0065 to +0.0017).
> - **fulltext, raw style:** dispersion of style vectors changes by +0.0247 [+0.0079, +0.0447] (+2.0% of its pre level) after 2022 (placebo breaks -0.0051 to +0.0059); distance to the 2016-2021 corpus centroid +0.0528 [+0.0360, +0.0713] (+4.3%; placebo -0.0056 to +0.0067).
> - **AI link (topic removed, abstracts):** detector-flagged papers of 2023-2025 have a dispersion -0.0720 [-0.1363, -0.0140] (-6.5%) against not-flagged papers of the same year; the same contrast for 'flagged' papers of 2019-2021 (false positives, a placebo) is +0.0460 [-0.0070, +0.1094].
> - **AI link (raw, abstracts):** detector-flagged papers of 2023-2025 have a dispersion -0.0862 [-0.1404, -0.0184] (-7.6%) against not-flagged papers of the same year; the same contrast for 'flagged' papers of 2019-2021 (false positives, a placebo) is +0.0481 [-0.0117, +0.1079].
> - **All-AI upper bound (abstracts, same papers):** rewriting every abstract lowers the pre-period dispersion from 1.065 to 1.011 (-5.1%), and its post change is +0.0110 [+0.0019, +0.0221] against +0.0322 [+0.0221, +0.0434] for the originals (gap +0.0211 [+0.0132, +0.0299]).
> **Reading (hand-written, 2026-11-05 run; recheck after a re-run).** Papers do not sound more alike across the corpus: after 2022 the spread of style vectors goes *up* by about 3% (topic removed), while the distance to the 2016-2021 centroid goes up by about 4.5%; both are several times the placebo breaks inside 2016-2021. The movement is a common drift (Kobak words +0.5 sd, longer words, higher MTLD, fewer `the`/`of`/`is`) of unequal size across papers, so the corpus spreads along that direction instead of collapsing. Uniformity shows only inside the AI-flagged group: flagged papers of 2023-2025 are about 6-7% less dispersed than unflagged papers of the same years, while the 2019-2021 'flagg

**v3**

> - **abstract, topic removed:** dispersion of style vectors changes by +0.0326 [+0.0213, +0.0425] (+3.0% of its pre level) after 2022 (placebo breaks +0.0050 to +0.0114); distance to the 2016-2021 corpus centroid +0.0496 [+0.0379, +0.0598] (+4.6%; placebo +0.0047 to +0.0112).
> - **abstract, raw style:** dispersion of style vectors changes by +0.0331 [+0.0215, +0.0476] (+3.0% of its pre level) after 2022 (placebo breaks +0.0081 to +0.0147); distance to the 2016-2021 corpus centroid +0.0594 [+0.0475, +0.0736] (+5.3%; placebo +0.0074 to +0.0145).
> - **fulltext, topic removed:** dispersion of style vectors changes by +0.0274 [+0.0110, +0.0406] (+2.6% of its pre level) after 2022 (placebo breaks -0.0059 to +0.0016); distance to the 2016-2021 corpus centroid +0.0476 [+0.0314, +0.0606] (+4.4%; placebo -0.0065 to +0.0017).
> - **fulltext, raw style:** dispersion of style vectors changes by +0.0247 [+0.0079, +0.0447] (+2.0% of its pre level) after 2022 (placebo breaks -0.0051 to +0.0059); distance to the 2016-2021 corpus centroid +0.0528 [+0.0360, +0.0713] (+4.3%; placebo -0.0056 to +0.0067).
> - **AI link (topic removed, abstracts):** detector-flagged papers of 2023-2025 have a dispersion -0.0681 [-0.1201, -0.0158] (-6.2%) against not-flagged papers of the same year; the same contrast for 'flagged' papers of 2019-2021 (false positives, a placebo) is +0.0508 [-0.0062, +0.1093].
> - **AI link (raw, abstracts):** detector-flagged papers of 2023-2025 have a dispersion -0.0879 [-0.1434, -0.0222] (-7.7%) against not-flagged papers of the same year; the same contrast for 'flagged' papers of 2019-2021 (false positives, a placebo) is +0.0467 [-0.0219, +0.1040].
> - **All-AI upper bound (abstracts, same papers):** rewriting every abstract lowers the pre-period dispersion from 1.066 to 1.011 (-5.1%), and its post change is +0.0105 [+0.0008, +0.0210] against +0.0319 [+0.0205, +0.0438] for the originals (gap +0.0214 [+0.0110, +0.0300]).
> **Reading (hand-written, 2026-11-05 run; recheck after a re-run).** Papers do not sound more alike across the corpus: after 2022 the spread of style vectors goes *up* by about 3% (topic removed), while the distance to the 2016-2021 centroid goes up by about 4.5%; both are several times the placebo breaks inside 2016-2021. The movement is a common drift (Kobak words +0.5 sd, longer words, higher MTLD, fewer `the`/`of`/`is`) of unequal size across papers, so the corpus spreads along that direction instead of collapsing. Uniformity shows only inside the AI-flagged group: flagged papers of 2023-2025 are about 6-7% less dispersed than unflagged papers of the same years, while the 2019-2021 'flagg


## 7. Topic convergence

v2 report: `exp-topics-event-ipw/ai-writing/diversity/reports/TOPIC-CONVERGENCE.md`; v3 report: `exp-topics-event-ipw/ai-writing/diversity/reports/v3/TOPIC-CONVERGENCE.md`.

**v2**

(no summary section)

**v3**

(no summary section)


## 8. Lab event study

v2 report: `exp-topics-event-ipw/ai-writing/diversity/reports/LAB-EVENT-STUDY.md`; v3 report: `exp-topics-event-ipw/ai-writing/diversity/reports/v3/LAB-EVENT-STUDY.md`.

**v2**

> - **Adoption.** Under the primary rule (share of a lab-year's scored papers with `ai_share` >= 0.25 above the 2016-21 floor 0.0008 + 3 SD = threshold 0.037, sustained 2 years) 359 labs adopt (cohorts {"2021.0": 1, "2022.0": 1, "2023.0": 101, "2024.0": 256}), 1432 never exceed it, 103 exceed it without sustaining, 354 exceed it only in 2025 (censored, left out), 0 have too few scored papers. Adoption is concentrated in 2023-2024 by construction of the data (the floor is the pre-ChatGPT noise), so the design has two real cohorts and few usable leads: that limits what a pre-trend test can show.
> - **Overall ATT of adoption on the headline outcomes** (Callaway-Sant'Anna, never-adopter controls, post-adoption years): mpd (specter2_proximity) +0.0090 [-0.0006, +0.0199] (pre-trend p = 0.657); disp (specter2_proximity) +0.0054 [-0.0009, +0.0112] (pre-trend p = 0.699); vendi (specter2_proximity) +0.0381 [-0.0034, +0.0753] (pre-trend p = 0.430); nov3 (specter2_proximity) -0.0065 [-0.0100, -0.0022] (pre-trend p = 0.001); OpenAlex-topic entropy (h_oa) +0.0309 [-0.0264, +0.0849] (pre-trend p = 0.688); dist_centroid (bt_qwen3_0p6b) -0.0062 [-0.0122, +0.0001] (pre-trend p = 0.429).
> - **Pre-trends.** The joint test that the leads (e = -5..-2) are zero rejects at 5% for 16 of 52 outcomes (main source, primary spec); with that many tests about 3 would reject by chance. Details per outcome in the grid below. Timing is not exogenous: adopters are larger labs (pre-2023 papers SMD +0.69) and more LLM-active before 2023 (LLM-text share 2021-22 SMD +0.20) than never-adopters, although among 2023+ adopters the year is unrelated to that share (rho -0.01); every ATT here is an association with adoption, not a causal effect of AI wording.
> - **Wording control.** mpd (specter2_proximity): original +0.0075 [-0.0041, +0.0184], gap (ai - orig) -0.0011 [-0.0026, +0.0005]; disp (specter2_proximity): original +0.0044 [-0.0013, +0.0112], gap (ai - orig) -0.0006 [-0.0015, +0.0004]; dist_centroid (bt_qwen3_0p6b): original -0.0093 [-0.0147, -0.0031], gap (ai - orig) +0.0000 [-0.0027, +0.0026] (section 5).

**v3**

> - **Adoption.** Under the primary rule (share of a lab-year's scored papers with `ai_share` >= 0.25 above the 2016-21 floor 0.0000 + 3 SD = threshold 0.006, sustained 2 years) 500 labs adopt (cohorts {"2022.0": 4, "2023.0": 183, "2024.0": 313}), 1258 never exceed it, 144 exceed it without sustaining, 346 exceed it only in 2025 (censored, left out), 0 have too few scored papers. Adoption is concentrated in 2023-2024 by construction of the data (the floor is the pre-ChatGPT noise), so the design has two real cohorts and few usable leads: that limits what a pre-trend test can show.
> - **Overall ATT of adoption on the headline outcomes** (Callaway-Sant'Anna, never-adopter controls, post-adoption years): mpd (specter2_proximity) +0.0059 [-0.0060, +0.0163] (pre-trend p = 0.930); disp (specter2_proximity) +0.0036 [-0.0029, +0.0100] (pre-trend p = 0.920); vendi (specter2_proximity) +0.0221 [-0.0153, +0.0610] (pre-trend p = 0.937); nov3 (specter2_proximity) -0.0071 [-0.0105, -0.0038] (pre-trend p = 0.002); OpenAlex-topic entropy (h_oa) +0.0204 [-0.0316, +0.0716] (pre-trend p = 0.279); dist_centroid (bt_qwen3_0p6b) -0.0134 [-0.0190, -0.0074] (pre-trend p = 0.043).
> - **Pre-trends.** The joint test that the leads (e = -5..-2) are zero rejects at 5% for 15 of 52 outcomes (main source, primary spec); with that many tests about 3 would reject by chance. Details per outcome in the grid below. Timing is not exogenous: adopters are larger labs (pre-2023 papers SMD +0.72) and more LLM-active before 2023 (LLM-text share 2021-22 SMD +0.24) than never-adopters, although among 2023+ adopters the year is unrelated to that share (rho -0.10); every ATT here is an association with adoption, not a causal effect of AI wording.
> - **Wording control.** mpd (specter2_proximity): original +0.0049 [-0.0059, +0.0168], gap (ai - orig) +0.0004 [-0.0011, +0.0023]; disp (specter2_proximity): original +0.0031 [-0.0043, +0.0094], gap (ai - orig) +0.0003 [-0.0008, +0.0012]; dist_centroid (bt_qwen3_0p6b): original -0.0157 [-0.0218, -0.0088], gap (ai - orig) -0.0007 [-0.0035, +0.0022] (section 5).


## 9. Full-text selection (IPW)

v2 report: `exp-topics-event-ipw/ai-writing/diversity/reports/FULLTEXT-SELECTION-IPW.md`; v3 report: `exp-topics-event-ipw/ai-writing/diversity/reports/v3/FULLTEXT-SELECTION-IPW.md`.

**v2**

> - **Who has a full text.** 65,751 of 101,304 lab papers (2016-2025, Georgia Tech excluded: no full text at all) have a scored full text (64.9%). Selection is strong on open access (closed-access papers 12% of the full-text set against 27% of all papers), on publisher (arXiv DOI prefix 22% against 16%; IEEE 18% against 23%), school and year. The cross-fitted model separates the two sets well (AUC 0.85 logistic, 0.89 boosting).
> - **Balance.** The largest standardised mean difference (SMD) over 155 covariate columns falls from 0.380 to 0.085 (logit model, the table's); 0 columns stay above the 0.1 target. Effective sample size 48,651 of 65,751 (74%); weights trimmed to [0.65, 4.32] (1st-99th percentile of the selected), mean 1.
> - **Headline rates.** Share of papers with `ai_share` >= 0.25: 2024 0.110 unweighted vs 0.105 weighted; 2025 0.242 vs 0.246 (section 3: the two intervals overlap in 10 of 10 years).
> **Where conclusions change.** Paper level: weighting flips the sign of the post-2022 dose-novelty coefficient in 1 of 26 model-design cells and moves an interval across 0 in 2 (section 4 lists them); lab level: sign differs in 0 of 35 model-outcome cells and the zero-status in 4 (section 5). The all-papers abstract-flag estimates are shown next to them.

**v3**

> - **Who has a full text.** 65,751 of 101,304 lab papers (2016-2025, Georgia Tech excluded: no full text at all) have a scored full text (64.9%). Selection is strong on open access (closed-access papers 12% of the full-text set against 27% of all papers), on publisher (arXiv DOI prefix 22% against 16%; IEEE 18% against 23%), school and year. The cross-fitted model separates the two sets well (AUC 0.85 logistic, 0.89 boosting).
> - **Balance.** The largest standardised mean difference (SMD) over 155 covariate columns falls from 0.380 to 0.085 (logit model, the table's); 0 columns stay above the 0.1 target. Effective sample size 48,651 of 65,751 (74%); weights trimmed to [0.65, 4.32] (1st-99th percentile of the selected), mean 1.
> - **Headline rates.** Share of papers with `ai_share` >= 0.25: 2024 0.154 unweighted vs 0.148 weighted; 2025 0.269 vs 0.269 (section 3: the two intervals overlap in 10 of 10 years).
> **Where conclusions change.** Paper level: weighting flips the sign of the post-2022 dose-novelty coefficient in 1 of 26 model-design cells and moves an interval across 0 in 1 (section 4 lists them); lab level: sign differs in 0 of 35 model-outcome cells and the zero-status in 11 (section 5). The all-papers abstract-flag estimates are shown next to them.


## 10. Citation novelty

v2 report: `exp-citation-revision/ai-writing/diversity/reports/CITATION-NOVELTY.md`; v3 report: `exp-citation-revision/ai-writing/diversity/reports/v3/CITATION-NOVELTY.md`.

**v2**

> **Coverage.** 87% of 2016-2021 lab papers have >= 5 references in the snapshot, 63% of 2023-2025 papers (2025: 56%); Uzzi z exists for 81% / 61%; CD1 for 48% / 37% (2023-2024); CD5 only for 2016-2020.
> **Rao-Stirling diversity.** Within labs, 2023-2025 against 2016-2021: 0.009 [0.006, 0.011]; the placebo break at 2019 within 2016-2021 gives 0.009 [0.007, 0.011].
> **cited-venue entropy.** Within labs, 2023-2025 against 2016-2021: 0.154 [0.132, 0.173]; the placebo break at 2019 within 2016-2021 gives 0.126 [0.110, 0.146].
> **Uzzi z p10.** Within labs, 2023-2025 against 2016-2021: -0.282 [-0.453, -0.094]; the placebo break at 2019 within 2016-2021 gives -1.708 [-1.867, -1.596].
> **within-lab reference overlap (cosine).** Within labs, 2023-2025 against 2016-2021: -0.006 [-0.008, -0.004]; the placebo break at 2019 within 2016-2021 gives -0.005 [-0.007, -0.003].
> **AI dose, within lab x year (2023-2025, per unit of ai_share):** Uzzi z, 10th percentile (low = atypical) -0.371 [-1.497, 0.639]; Uzzi z, median (high = conventional) -0.275 [-0.679, 0.064]; CD1 disruption (low = consolidating when high) 0.000 [-0.002, 0.003]; CD to end-2025 (variable window) 0.001 [-0.000, 0.003]; Rao-Stirling (subfields) 0.030 [0.013, 0.043]; cited-venue entropy (bits) 0.139 [0.028, 0.227].

**v3**

> **Coverage.** 87% of 2016-2021 lab papers have >= 5 references in the snapshot, 63% of 2023-2025 papers (2025: 56%); Uzzi z exists for 81% / 61%; CD1 for 48% / 37% (2023-2024); CD5 only for 2016-2020.
> **Rao-Stirling diversity.** Within labs, 2023-2025 against 2016-2021: 0.009 [0.006, 0.011]; the placebo break at 2019 within 2016-2021 gives 0.009 [0.007, 0.011].
> **cited-venue entropy.** Within labs, 2023-2025 against 2016-2021: 0.154 [0.132, 0.173]; the placebo break at 2019 within 2016-2021 gives 0.126 [0.110, 0.146].
> **Uzzi z p10.** Within labs, 2023-2025 against 2016-2021: -0.282 [-0.453, -0.094]; the placebo break at 2019 within 2016-2021 gives -1.708 [-1.867, -1.596].
> **within-lab reference overlap (cosine).** Within labs, 2023-2025 against 2016-2021: -0.006 [-0.008, -0.004]; the placebo break at 2019 within 2016-2021 gives -0.005 [-0.007, -0.003].
> **AI dose, within lab x year (2023-2025, per unit of ai_share):** Uzzi z, 10th percentile (low = atypical) -0.849 [-1.652, 0.002]; Uzzi z, median (high = conventional) -0.379 [-0.636, -0.092]; CD1 disruption (low = consolidating when high) 0.001 [-0.000, 0.004]; CD to end-2025 (variable window) 0.002 [0.000, 0.003]; Rao-Stirling (subfields) 0.025 [0.013, 0.036]; cited-venue entropy (bits) 0.093 [0.011, 0.160].


## 11. AI in revision

v2 report: `exp-citation-revision/ai-writing/diversity/reports/AI-IN-REVISION.md`; v3 report: `exp-citation-revision/ai-writing/diversity/reports/v3/AI-IN-REVISION.md`.

**v2**

> **Kind S, v1 before Dec 2022 and later text after:** 811 pairs; mean change in flagged-passage share 0.0006 [-0.0005, 0.0019] (v1 level 0.011); against the pre_pre baseline -0.0001 [-0.0013, 0.0012], matched -0.0026 [-0.0072, 0.0013] (441 of 811 pairs kept). Shares are fractions of passages (0.01 = one point).
> **Kind A, v1 before Dec 2022 and later text after:** 455 pairs; mean change in flagged-passage share 0.0044 [0.0023, 0.0067] (v1 level 0.010); against the pre_pre baseline 0.0039 [0.0014, 0.0064], matched 0.0026 [-0.0007, 0.0058] (306 of 455 pairs kept). Shares are fractions of passages (0.01 = one point).

**v3**

> **Kind S, v1 before Dec 2022 and later text after:** 784 pairs; mean change in flagged-passage share 0.0011 [0.0001, 0.0022] (v1 level 0.003); against the pre_pre baseline 0.0006 [-0.0005, 0.0020], matched 0.0009 [-0.0015, 0.0036] (430 of 784 pairs kept). Shares are fractions of passages (0.01 = one point).
> **Kind A, v1 before Dec 2022 and later text after:** 444 pairs; mean change in flagged-passage share 0.0029 [0.0010, 0.0057] (v1 level 0.004); against the pre_pre baseline 0.0031 [0.0010, 0.0055], matched 0.0008 [-0.0014, 0.0032] (300 of 444 pairs kept). Shares are fractions of passages (0.01 = one point).


## 12. Lab AI scores (2025, out of 10)

Floor (mean 2016-2021 out-of-sample share): v2 0.90%, v3 0.33%. Labs with a score: v2 771, v3 878 of 2322.

| school | v2 scored / median / max | v3 scored / median / max | v2 paper coverage | v3 paper coverage |
|---|---|---|---|---|
| berkeley | 89 / 1.3 / 4.1 | 95 / 1.3 / 3.8 | 0.741 | 0.79 |
| cmu | 190 / 1.45 / 5.4 | 195 / 1.5 / 5.7 | 0.721 | 0.777 |
| epfl | 89 / 1.7 / 6.2 | 93 / 1.7 / 8.2 | 0.732 | 0.783 |
| gatech | 0 / None / None | 74 / 2.4 / 6.7 | 0.003 | 0.436 |
| michigan | 73 / 1.6 / 4.8 | 77 / 1.9 / 5.0 | 0.612 | 0.638 |
| mit | 125 / 1.0 / 3.8 | 132 / 1.1 / 4.1 | 0.693 | 0.747 |
| princeton | 56 / 0.9 / 3.5 | 57 / 0.7 / 4.0 | 0.768 | 0.792 |
| stanford | 117 / 1.5 / 4.9 | 120 / 1.6 / 4.9 | 0.753 | 0.795 |
| uchicago | 32 / 1.1 / 3.8 | 35 / 0.9 / 4.3 | 0.598 | 0.628 |

2019 placebo (labs scored on 2019 papers; every score should be about 0): v2 546 labs, median 0.0, p90 0.1, max 0.7; v3 648 labs, median 0.0, p90 0.0, max 0.4, 91% exactly 0; out-of-sample only: 344 labs, median 0.0, p90 0.1, max 0.3.

Cross-checks (Pearson of the lab score with): fulltext_ai_share_equiv v2 0.985 / v3 0.934; kobak_ft v2 0.665 / v3 0.673; abstract_flag_share v2 0.7 / v3 0.684

Same labs scored in both (771): Pearson 0.961, Spearman 0.960, median absolute change 0.2 points; top-50 overlap 33 of 50.

**Georgia Tech (full texts now scored).** 437 labs, 2416 papers in 2025, 1060 with a full text, 1053 usable (44%); 74 labs reach the 5-paper minimum and get a score (median 2.4, 90th percentile 4.2, max 6.7). v2 scored none (coverage 0.3%).


## What changed, plainly

**Same direction, tighter intervals (most findings).**
- *How much AI.* The rise is the same shape: papers with at least a quarter of their main-body passages flagged go from about 0% (2016-2022; v3 0.00-0.13%) to 4.0% (2023), 16.5% (2024) and 28.2% (2025); v2 said 2.9%, 11.0%, 24.2%. the v3 share of papers at or above a quarter is higher in every year after 2022 (mean dose is higher in 2024-2025, 3.3% against 3.5% in 2023), and its pre-2023 floor is lower (mean dose 0.2-0.3% in 2016-2021, the 0.3% design rate, against v2's 1.0-1.2%). Georgia Tech, which v2 could not show, has the highest 2025 share (38.6% [35.4, 41.6]). The abstained passage share is 2.5-3.4% of main-body passages (5.6% in the detector's test set). Main + appendix gives nearly the same mean dose (appendix false-alarm check: 0.32% [0.25, 0.41], limit 1.5%, passes).
- *Dose versus novelty and diversity.* Post-2022 coefficients keep their sign in 12 of 14 model x design cells and their intervals narrow somewhat; the cells that flip (SPECTER2-proximity pooled, Qwen3 pooled) are both about zero with intervals including zero. Where v2 had intervals excluding zero (Nomic pooled, +0.0080), v3 includes zero (+0.0040 [-0.0007, +0.0088]). Lab-level difference-in-differences of diversity on lab AI dose stay positive in all seven models for dispersion and mean pairwise distance, now with intervals excluding zero in six of seven (v2: five of seven for dispersion), and the 2019 placebo is about zero in all.
- *All-AI rewrite.* Unchanged by construction (it never used the passage detector); only the AI-versus-not groups in the matched test and `ai_vs_not` move with v3.
- *Lineage, style.* Student-advisor dose coefficients: -0.0355 to -0.0142 (v2 -0.0414 to -0.0175), interval excluding zero in 7 of 7 models both times; every 2017-2021 placebo interval includes zero both times. Style: detector-flagged papers are 6.2-7.7% less dispersed than unflagged papers of the same year (v2 6.5-7.6%); the corpus-wide style spreading and the all-AI bound are detector-free and identical.
- *Topic convergence.* Detector-free: the v3 report is identical to v2.
- *Lab scores.* Floor 0.33% (v2 0.90%); same labs correlate 0.96 across detectors (median change 0.2 points); 878 labs now score (771), the 2019 placebo has median 0.0, p90 0.0 and max 0.4 (v2 max 0.7), and Georgia Tech is scored for the first time: 74 of 437 labs, median 2.4, top lab 6.7 (coverage 44% of its 2025 papers).

**Changed, with the direction stated.**
1. *The dose placebo is no longer biased upward.* In v2 the 2017-2021 "dose" coefficients on novelty were mostly positive and large (up to +0.057 within lab); in v3, with training papers excluded and a 0.3% threshold, they are centred on or below zero with wide intervals (about +-0.07). So v2's statement that "no post-2022 coefficient stands out from the placebo spread" is now stronger: the post coefficients are small and the placebo is wide.
2. *Lab event study.* Adoption is easier to trigger: floor 0.000 (v2 0.0008), threshold 0.006 (v2 0.037), 500 adopting labs (v2 359). Overall effects on diversity stay small with intervals including zero (mpd +0.0059 [-0.0060, +0.0163]); novelty stays negative (-0.0071 [-0.0105, -0.0038], pre-trend p = 0.002, so still an association not an effect); distance to the lab centroid on BERTopic Qwen3 now excludes zero (-0.0134 [-0.0190, -0.0074]; v2 -0.0062 [-0.0122, +0.0001]).
3. *Citation novelty.* Within lab and year, a paper's AI dose goes with more conventional citing: median Uzzi z -0.379 [-0.636, -0.092] (v2 -0.275 [-0.679, +0.064], interval included zero); the tenth percentile -0.849 [-1.652, +0.002] (v2 -0.371 [-1.497, +0.639]). Rao-Stirling and venue-entropy dose coefficients stay positive. The pre/post lab trends are detector-free and unchanged.
4. *AI in revision.* v1 passages are now flagged at 0.3% (v1 level 0.003, v2 0.011). Kind S (v1 before December 2022, stored copy after): 784 pairs, mean change +0.0011 [+0.0001, +0.0022] (v2 811 pairs, +0.0006 [-0.0005, +0.0019]), but against the pre-pre baseline +0.0006 [-0.0005, +0.0020] and matched +0.0009 [-0.0015, +0.0036]: no more than a tenth of a point, not distinguishable from the baseline, as in v2. Kind A: +0.0029 [+0.0010, +0.0057] (v2 +0.0044), matched +0.0008 [-0.0014, +0.0032] (v2 +0.0026 [-0.0007, +0.0058]). Conclusion unchanged: no sign that AI text is added in revision at a scale the detector can see.
5. *Full-text IPW.* Weights were not refitted (the selection model does not depend on the detector); the v3 weighted and unweighted rates still overlap in every year, and the lab-level estimates whose zero-status changes with weighting rise from 4 to 11 (still no sign flips).

**Not a change of direction anywhere**: no finding flipped from "AI goes with less diverse or more homogeneous research" to its opposite or back.
