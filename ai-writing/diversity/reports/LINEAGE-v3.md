# Advisor-student lineage: do students' papers converge on their advisor's and on each other's?

Generated 2026-11-06 by `ai-writing/lineage/` (`lineage_build.py`, `lineage_run.py`, `lineage_report.py`; tables in `/n/fs/resemble/homogenizing-science/scratch/lineage-style/out/20261105-v3`). Link snapshot: `/n/fs/resemble/homogenizing-science/scratch/lineage-style/hier`, taken 2026-11-05T22:44:09Z; a release was rebuilding the packages at that time. Detector table: `papers.parquet` (v1 abstract + detector-v3 main-body passages, 0.3% threshold, abstained excluded: ai-scores-v3 container). **Years 2017-2025 only (no 2026); post = 2023-2025, 2022 dropped from the pre/post contrast as the transition year.**

## Answer (plain language)

**Numbers below come from the tables of this report; each bullet is generated, so a re-run on new data rewrites them.**

- **student-advisor similarity, candidate links (the large sample), abstracts, 7 models.** Post-2023 change inside labs -0.0126 to +0.0058; interval wholly below zero in 5 models, wholly above in 0; placebo breaks (2019-2021) -0.0146 to -0.0023; the post interval lies wholly outside the placebo range in 1 of 7 models.
- **student-student similarity, candidate links (the large sample), abstracts, 7 models.** Post-2023 change inside labs -0.0144 to +0.0020; interval wholly below zero in 5 models, wholly above in 0; placebo breaks (2019-2021) -0.0215 to -0.0055; the post interval lies wholly outside the placebo range in 0 of 7 models.
- **student-advisor similarity, verified links (the thin sample), abstracts, 7 models.** Post-2023 change inside labs -0.0121 to +0.0108; interval wholly below zero in 1 models, wholly above in 0; placebo breaks (2019-2021) -0.0116 to +0.0091; the post interval lies wholly outside the placebo range in 0 of 7 models.
- **student-student similarity, verified links (the thin sample), abstracts, 7 models.** Post-2023 change inside labs -0.0289 to +0.0071; interval wholly below zero in 0 models, wholly above in 0; placebo breaks (2019-2021) -0.0127 to +0.0213; the post interval lies wholly outside the placebo range in 0 of 7 models.
- **AI dose, student-advisor similarity, abstracts, exposure `ai_share`.** Among 2023-2025 papers the coefficient (0 to 1 exposure, lab and year fixed effects) is -0.0355 to -0.0142 across 7 models, interval excluding zero in 7; the 2017-2021 placebo is +0.0043 to +0.1133 with every interval including zero in 7 of 7 models.
- **AI dose, student-advisor similarity, abstracts, exposure `flag_abstract`.** Among 2023-2025 papers the coefficient (0 to 1 exposure, lab and year fixed effects) is -0.0116 to -0.0050 across 7 models, interval excluding zero in 6; the 2017-2021 placebo is -0.0065 to +0.0124 with every interval including zero in 7 of 7 models.
- **Wording.** The post effect on the all-AI rewrites of the same papers is almost the same as on the originals: the gap (the part carried by wording) is -0.0029 to +0.0031 in cosine units (median |gap| / |effect| = 0.10 over model x measure; ratios are unstable where the effect is near zero). Convergence or divergence that is there after rewriting is content, not wording.
- **Reading of the 2026-11-05 run (hand-written; check it against the bullets above after a re-run).** Students' abstracts after 2023 are slightly less similar to their advisor's recent work and sit slightly further from the lab centroid in most models (not SPECTER2-base), but the pre-2022 trend runs the same way, so the post break is not distinguishable from the existing drift at the pooled level. What does stand out from the placebo is the dose: within 2023-2025, a student paper with more AI-flagged text sits further from the advisor, consistently across models, and about as strongly after rewriting (content, not wording). It is an association between papers of the same lab and year, not a causal effect: students who use AI may differ in topic or career stage.


## Method

- **Unit.** A (PI, student) pair. The student's papers are the links in `student_papers` (status `verified`; `candidate` links are reported separately, and `all` is both). The PI's papers are the strict lab papers (`lab_papers`: the PI is on the byline; the study-labs-are-strict rule). Only papers with an embedding are used.
- **Student-advisor similarity (`sa`).** For a student paper of year t: the PI's lab papers of t-3..t-1, those the student co-authored removed (by linked work and by byline name), the pool drawn down to 6 papers (size-matched, mean over 20 draws; pairs with fewer are dropped), then the mean cosine of the 3 nearest. **Distance from the lab centroid (`cd`)** is 1 - cos(paper, centroid of the same pool). **Student-student similarity (`ss`)** is a lab-year measure: the mean pairwise cosine of 4 papers of 4 different students (distinct papers; 30 draws; labs with at least 4 students publishing that year).
- **Estimator.** Lab fixed effect, Post = 2023-2025 against 2017-2021 (2022 dropped); each student has total weight 1 (weight 1 / number of the student's papers in the window), so prolific students do not dominate; interval = 2.5/97.5 percentiles of a cluster bootstrap over labs (1,000 draws). The lab-year `ss` table has equal lab-year weights. **Placebo:** the same contrast inside 2017-2021 with breaks at 2019, 2020 and 2021. **Dose:** within 2023-2025 (and, as placebo, within 2017-2021 where the dose is detector noise), the measure on the student paper's own `ai_share` (full-text passage share; scored papers only) or `flag_abstract` (abstract detector; all papers), with lab and year fixed effects (residuals computed once, the bootstrap reweights labs: a close approximation).
- **Wording control.** The same measures on the all-AI rewritten abstracts (`<model>__allai`), both corpora restricted to the same papers and centred on that common set; the gap column is original minus all-AI, estimated as one regression of the difference, so its interval is exact for the paired design. A convergence that appears in the original and not in the rewrite is wording; one that survives in both is content.

## Coverage

Student-paper links with a paper year of 2017-2025 and an embedded paper; `papers` are distinct papers.

| status | school | pairs | students | phd_students | labs | papers | links |
|---|---|---|---|---|---|---|---|
| verified | cmu | 468 | 389 | 226 | 95 | 902 | 1329 |
| verified | epfl | 803 | 720 | 706 | 92 | 2796 | 3949 |
| verified | mit | 209 | 192 | 101 | 79 | 393 | 478 |
| verified | princeton | 22 | 17 | 10 | 15 | 48 | 60 |
| verified | ALL | 1502 | 1318 | 1043 | 281 | 4139 | 5816 |
| candidate | berkeley | 2875 | 2479 | 1381 | 193 | 7456 | 14808 |
| candidate | cmu | 4816 | 4146 | 2412 | 433 | 12784 | 22509 |
| candidate | epfl | 1718 | 1652 | 1164 | 152 | 5855 | 8368 |
| candidate | gatech | 376 | 366 | 218 | 62 | 1225 | 1710 |
| candidate | michigan | 482 | 464 | 406 | 109 | 1913 | 2619 |
| candidate | mit | 3606 | 3363 | 1248 | 256 | 9745 | 17234 |
| candidate | princeton | 1392 | 1277 | 604 | 125 | 3640 | 6232 |
| candidate | stanford | 2370 | 2125 | 1852 | 221 | 9059 | 14884 |
| candidate | uchicago | 408 | 307 | 292 | 75 | 1291 | 1925 |
| candidate | ALL | 18043 | 16179 | 9577 | 1626 | 52399 | 90289 |

Verified links exist only for Princeton, CMU, EPFL and MIT; at the other five schools every link is a `candidate`. Pairs actually entering a measure are fewer (a student paper needs 6 PI papers in the previous 3 years): see the `n` and `n_students` columns of `effects_*.parquet`.

Papers (student-paper rows), students and labs in the Post contrast of `sa` (specter2_proximity abstracts):

| set | n | n_students | n_labs |
|---|---|---|---|
| verified | 3741 | 1085.0 | 102.0 |
| candidate | 54472 | 13180.0 | 803.0 |
| all | 58213 | 13790.0 | 815.0 |

## 1. Pre/post 2023 inside labs, with placebo breaks

`sa` and `ss`: positive = more alike; `cd`: positive = further from the lab centroid. Post effect = 2023-2025 minus 2017-2021 within lab (cosine units). "placebo range" = the smallest and largest of the three placebo estimates (breaks 2019-2021 inside 2017-2021); "outside?" = the post interval lies wholly beyond that range.

### Abstracts, Verified links

| model | sa post | sa placebo range | sa outside? | cd post | cd placebo range | cd outside? | ss post | ss placebo range | ss outside? |
|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | -0.0121 [-0.0236, -0.0008] | -0.0041 to +0.0031 | no | +0.0154 [+0.0002, +0.0317] | -0.0057 to +0.0048 | no | -0.0289 [-0.0543, +0.0015] | -0.0069 to +0.0111 | no |
| gte_qwen2_1p5b | -0.0045 [-0.0212, +0.0105] | -0.0051 to +0.0078 | no | +0.0031 [-0.0160, +0.0232] | -0.0128 to +0.0068 | no | -0.0062 [-0.0460, +0.0378] | -0.0073 to +0.0051 | no |
| nomic_v15 | -0.0118 [-0.0267, +0.0027] | -0.0037 to +0.0056 | no | +0.0128 [-0.0063, +0.0326] | -0.0089 to +0.0036 | no | -0.0177 [-0.0593, +0.0307] | -0.0127 to +0.0072 | no |
| qwen3_0p6b | -0.0111 [-0.0257, +0.0028] | -0.0053 to +0.0041 | no | +0.0137 [-0.0043, +0.0328] | -0.0057 to +0.0081 | no | -0.0200 [-0.0581, +0.0260] | -0.0040 to +0.0213 | no |
| scincl | -0.0022 [-0.0235, +0.0176] | -0.0101 to +0.0009 | no | -0.0041 [-0.0278, +0.0214] | -0.0014 to +0.0149 | no | +0.0022 [-0.0562, +0.0711] | -0.0105 to +0.0063 | no |
| specter2_base | +0.0108 [-0.0083, +0.0282] | -0.0038 to +0.0091 | no | -0.0101 [-0.0313, +0.0137] | -0.0069 to +0.0101 | no | +0.0071 [-0.0453, +0.0680] | -0.0098 to +0.0052 | no |
| specter2_proximity | +0.0020 [-0.0155, +0.0184] | -0.0116 to +0.0024 | no | -0.0047 [-0.0242, +0.0182] | -0.0000 to +0.0191 | no | +0.0008 [-0.0483, +0.0565] | -0.0122 to -0.0012 | no |

### Abstracts, Candidate links (reported separately)

| model | sa post | sa placebo range | sa outside? | cd post | cd placebo range | cd outside? | ss post | ss placebo range | ss outside? |
|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | -0.0126 [-0.0163, -0.0089] | -0.0120 to -0.0086 | no | +0.0154 [+0.0102, +0.0206] | +0.0098 to +0.0136 | no | -0.0144 [-0.0196, -0.0094] | -0.0129 to -0.0074 | no |
| gte_qwen2_1p5b | -0.0080 [-0.0132, -0.0027] | -0.0113 to -0.0087 | no | +0.0067 [-0.0005, +0.0134] | +0.0088 to +0.0114 | no | -0.0095 [-0.0167, -0.0019] | -0.0152 to -0.0081 | no |
| nomic_v15 | -0.0122 [-0.0174, -0.0068] | -0.0139 to -0.0110 | no | +0.0110 [+0.0037, +0.0182] | +0.0112 to +0.0143 | no | -0.0142 [-0.0207, -0.0073] | -0.0186 to -0.0081 | no |
| qwen3_0p6b | -0.0098 [-0.0146, -0.0044] | -0.0146 to -0.0105 | no | +0.0092 [+0.0019, +0.0156] | +0.0109 to +0.0160 | no | -0.0081 [-0.0143, -0.0016] | -0.0133 to -0.0099 | no |
| scincl | -0.0082 [-0.0149, -0.0015] | -0.0138 to -0.0075 | no | +0.0046 [-0.0036, +0.0127] | +0.0063 to +0.0119 | no | -0.0101 [-0.0192, -0.0009] | -0.0215 to -0.0066 | no |
| specter2_base | +0.0058 [-0.0004, +0.0121] | -0.0058 to -0.0023 | yes | -0.0052 [-0.0131, +0.0024] | +0.0029 to +0.0066 | yes | +0.0020 [-0.0068, +0.0112] | -0.0158 to -0.0055 | no |
| specter2_proximity | -0.0026 [-0.0083, +0.0033] | -0.0113 to -0.0077 | no | +0.0023 [-0.0051, +0.0095] | +0.0079 to +0.0121 | no | -0.0038 [-0.0123, +0.0048] | -0.0208 to -0.0103 | no |

### Full text, verified and candidate

*verified*

| model | sa post | sa placebo range | sa outside? | cd post | cd placebo range | cd outside? | ss post | ss placebo range | ss outside? |
|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | -0.0027 [-0.0162, +0.0102] | -0.0116 to -0.0039 | no | +0.0056 [-0.0128, +0.0254] | +0.0055 to +0.0164 | no | -0.0071 [-0.0370, +0.0219] | +0.0057 to +0.0210 | no |
| gte_qwen2_1p5b | -0.0041 [-0.0189, +0.0115] | -0.0103 to -0.0044 | no | +0.0031 [-0.0153, +0.0219] | +0.0022 to +0.0098 | no | +0.0026 [-0.0351, +0.0422] | -0.0038 to +0.0176 | no |
| nomic_v15 | -0.0081 [-0.0258, +0.0104] | -0.0087 to -0.0042 | no | +0.0081 [-0.0143, +0.0299] | +0.0017 to +0.0064 | no | -0.0113 [-0.0581, +0.0409] | +0.0135 to +0.0225 | no |
| qwen3_0p6b | -0.0031 [-0.0182, +0.0124] | -0.0133 to -0.0038 | no | +0.0026 [-0.0176, +0.0228] | +0.0039 to +0.0193 | no | +0.0036 [-0.0323, +0.0371] | +0.0021 to +0.0162 | no |
| specter2_base | +0.0108 [-0.0099, +0.0304] | -0.0047 to +0.0014 | no | -0.0096 [-0.0323, +0.0153] | -0.0042 to +0.0023 | no | +0.0120 [-0.0512, +0.0831] | +0.0049 to +0.0287 | no |
| specter2_proximity | +0.0013 [-0.0175, +0.0205] | -0.0181 to -0.0086 | no | -0.0027 [-0.0246, +0.0199] | +0.0058 to +0.0168 | no | +0.0070 [-0.0522, +0.0738] | -0.0040 to +0.0144 | no |

*candidate*

| model | sa post | sa placebo range | sa outside? | cd post | cd placebo range | cd outside? | ss post | ss placebo range | ss outside? |
|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | -0.0052 [-0.0105, +0.0003] | -0.0098 to -0.0038 | no | +0.0072 [-0.0003, +0.0142] | +0.0044 to +0.0111 | no | -0.0030 [-0.0096, +0.0034] | -0.0188 to -0.0088 | no |
| gte_qwen2_1p5b | -0.0095 [-0.0162, -0.0028] | -0.0137 to -0.0059 | no | +0.0079 [-0.0010, +0.0163] | +0.0055 to +0.0136 | no | -0.0039 [-0.0124, +0.0042] | -0.0236 to -0.0138 | yes |
| nomic_v15 | -0.0126 [-0.0201, -0.0049] | -0.0127 to -0.0064 | no | +0.0115 [+0.0016, +0.0206] | +0.0049 to +0.0112 | no | -0.0095 [-0.0186, -0.0008] | -0.0237 to -0.0161 | no |
| qwen3_0p6b | -0.0075 [-0.0126, -0.0024] | -0.0091 to -0.0070 | no | +0.0078 [+0.0001, +0.0148] | +0.0094 to +0.0113 | no | -0.0023 [-0.0087, +0.0042] | -0.0192 to -0.0083 | no |
| specter2_base | -0.0010 [-0.0093, +0.0077] | -0.0098 to +0.0008 | no | +0.0010 [-0.0097, +0.0109] | -0.0026 to +0.0083 | no | -0.0012 [-0.0131, +0.0110] | -0.0252 to -0.0149 | yes |
| specter2_proximity | -0.0085 [-0.0169, -0.0000] | -0.0213 to -0.0085 | no | +0.0049 [-0.0060, +0.0150] | +0.0058 to +0.0210 | no | -0.0050 [-0.0166, +0.0067] | -0.0369 to -0.0203 | yes |

## 2. Interaction with AI dose

Coefficient of the measure on the student paper's AI exposure, 0 to 1, with lab and year fixed effects. Post: papers of 2023-2025. Placebo: papers of 2017-2021 (exposure = detector noise). Verified and candidate links pooled (`all`) because the verified sample is thin; per-set tables are in `effects_*.parquet`.

| kind | model | measure | exposure | post (2023-25) | n | placebo (2017-21) |
|---|---|---|---|---|---|---|
| abstract | bge_m3 | sa | ai_share | -0.0142 [-0.0239, -0.0047] | 23498 | +0.0064 [-0.1588, +0.1705] |
| abstract | bge_m3 | sa | flag_abstract | -0.0064 [-0.0105, -0.0025] | 27394 | +0.0000 [-0.0156, +0.0137] |
| abstract | bge_m3 | cd | ai_share | +0.0221 [+0.0076, +0.0370] | 23498 | -0.0134 [-0.2586, +0.2280] |
| abstract | bge_m3 | cd | flag_abstract | +0.0095 [+0.0036, +0.0158] | 27394 | +0.0004 [-0.0192, +0.0205] |
| abstract | gte_qwen2_1p5b | sa | ai_share | -0.0294 [-0.0422, -0.0158] | 23498 | +0.0043 [-0.2369, +0.2609] |
| abstract | gte_qwen2_1p5b | sa | flag_abstract | -0.0092 [-0.0149, -0.0037] | 27394 | +0.0036 [-0.0164, +0.0211] |
| abstract | gte_qwen2_1p5b | cd | ai_share | +0.0409 [+0.0220, +0.0589] | 23498 | -0.0105 [-0.3407, +0.3119] |
| abstract | gte_qwen2_1p5b | cd | flag_abstract | +0.0131 [+0.0055, +0.0206] | 27394 | -0.0040 [-0.0279, +0.0224] |
| abstract | nomic_v15 | sa | ai_share | -0.0247 [-0.0385, -0.0107] | 23498 | +0.0343 [-0.2177, +0.2976] |
| abstract | nomic_v15 | sa | flag_abstract | -0.0085 [-0.0143, -0.0029] | 27394 | +0.0004 [-0.0195, +0.0188] |
| abstract | nomic_v15 | cd | ai_share | +0.0341 [+0.0150, +0.0534] | 23498 | -0.0533 [-0.4243, +0.3021] |
| abstract | nomic_v15 | cd | flag_abstract | +0.0119 [+0.0045, +0.0199] | 27394 | +0.0015 [-0.0233, +0.0277] |
| abstract | qwen3_0p6b | sa | ai_share | -0.0186 [-0.0304, -0.0063] | 23498 | +0.0750 [-0.1602, +0.3165] |
| abstract | qwen3_0p6b | sa | flag_abstract | -0.0050 [-0.0105, +0.0005] | 27394 | -0.0065 [-0.0254, +0.0119] |
| abstract | qwen3_0p6b | cd | ai_share | +0.0290 [+0.0121, +0.0459] | 23498 | -0.0807 [-0.3917, +0.2134] |
| abstract | qwen3_0p6b | cd | flag_abstract | +0.0078 [+0.0002, +0.0156] | 27394 | +0.0108 [-0.0132, +0.0367] |
| abstract | scincl | sa | ai_share | -0.0355 [-0.0542, -0.0180] | 23498 | +0.1133 [-0.2150, +0.4447] |
| abstract | scincl | sa | flag_abstract | -0.0110 [-0.0183, -0.0040] | 27394 | +0.0124 [-0.0148, +0.0375] |
| abstract | scincl | cd | ai_share | +0.0432 [+0.0186, +0.0684] | 23498 | -0.0536 [-0.4515, +0.3729] |
| abstract | scincl | cd | flag_abstract | +0.0140 [+0.0047, +0.0235] | 27394 | -0.0126 [-0.0445, +0.0247] |
| abstract | specter2_base | sa | ai_share | -0.0316 [-0.0490, -0.0141] | 23498 | +0.0919 [-0.2365, +0.4203] |
| abstract | specter2_base | sa | flag_abstract | -0.0092 [-0.0160, -0.0023] | 27394 | +0.0092 [-0.0175, +0.0343] |
| abstract | specter2_base | cd | ai_share | +0.0442 [+0.0205, +0.0672] | 23498 | -0.0822 [-0.5080, +0.3596] |
| abstract | specter2_base | cd | flag_abstract | +0.0132 [+0.0040, +0.0222] | 27394 | -0.0113 [-0.0426, +0.0248] |
| abstract | specter2_proximity | sa | ai_share | -0.0337 [-0.0497, -0.0176] | 23498 | +0.0719 [-0.2478, +0.3850] |
| abstract | specter2_proximity | sa | flag_abstract | -0.0116 [-0.0180, -0.0053] | 27394 | +0.0112 [-0.0113, +0.0328] |
| abstract | specter2_proximity | cd | ai_share | +0.0463 [+0.0243, +0.0683] | 23498 | -0.0669 [-0.4699, +0.3521] |
| abstract | specter2_proximity | cd | flag_abstract | +0.0161 [+0.0075, +0.0249] | 27394 | -0.0140 [-0.0433, +0.0171] |
| fulltext | bge_m3 | sa | ai_share | -0.0280 [-0.0398, -0.0169] | 27602 | -0.0566 [-0.2252, +0.1152] |
| fulltext | bge_m3 | sa | flag_abstract | -0.0090 [-0.0140, -0.0040] | 24843 | -0.0038 [-0.0235, +0.0160] |
| fulltext | bge_m3 | cd | ai_share | +0.0390 [+0.0231, +0.0555] | 27602 | +0.0851 [-0.1638, +0.3249] |
| fulltext | bge_m3 | cd | flag_abstract | +0.0144 [+0.0073, +0.0220] | 24843 | +0.0030 [-0.0269, +0.0311] |
| fulltext | gte_qwen2_1p5b | sa | ai_share | -0.0456 [-0.0608, -0.0321] | 27602 | -0.0550 [-0.2588, +0.1312] |
| fulltext | gte_qwen2_1p5b | sa | flag_abstract | -0.0142 [-0.0204, -0.0080] | 24843 | -0.0016 [-0.0266, +0.0233] |
| fulltext | gte_qwen2_1p5b | cd | ai_share | +0.0605 [+0.0417, +0.0804] | 27602 | +0.0534 [-0.1869, +0.3240] |
| fulltext | gte_qwen2_1p5b | cd | flag_abstract | +0.0194 [+0.0113, +0.0279] | 24843 | +0.0002 [-0.0330, +0.0344] |
| fulltext | nomic_v15 | sa | ai_share | -0.0426 [-0.0586, -0.0267] | 27602 | -0.0030 [-0.2130, +0.2079] |
| fulltext | nomic_v15 | sa | flag_abstract | -0.0118 [-0.0184, -0.0054] | 24843 | -0.0127 [-0.0464, +0.0184] |
| fulltext | nomic_v15 | cd | ai_share | +0.0532 [+0.0328, +0.0742] | 27602 | +0.0049 [-0.2603, +0.2790] |
| fulltext | nomic_v15 | cd | flag_abstract | +0.0172 [+0.0088, +0.0255] | 24843 | +0.0104 [-0.0309, +0.0544] |
| fulltext | qwen3_0p6b | sa | ai_share | -0.0185 [-0.0298, -0.0072] | 27602 | -0.0161 [-0.1816, +0.1561] |
| fulltext | qwen3_0p6b | sa | flag_abstract | -0.0079 [-0.0125, -0.0033] | 24843 | -0.0190 [-0.0412, +0.0029] |
| fulltext | qwen3_0p6b | cd | ai_share | +0.0325 [+0.0150, +0.0507] | 27602 | -0.0097 [-0.2766, +0.2517] |
| fulltext | qwen3_0p6b | cd | flag_abstract | +0.0135 [+0.0064, +0.0206] | 24843 | +0.0162 [-0.0217, +0.0553] |
| fulltext | specter2_base | sa | ai_share | -0.0568 [-0.0776, -0.0362] | 27602 | -0.0575 [-0.3450, +0.2038] |
| fulltext | specter2_base | sa | flag_abstract | -0.0202 [-0.0287, -0.0120] | 24843 | -0.0075 [-0.0387, +0.0215] |
| fulltext | specter2_base | cd | ai_share | +0.0713 [+0.0451, +0.0976] | 27602 | +0.0762 [-0.2379, +0.4132] |
| fulltext | specter2_base | cd | flag_abstract | +0.0254 [+0.0154, +0.0365] | 24843 | +0.0094 [-0.0326, +0.0516] |
| fulltext | specter2_proximity | sa | ai_share | -0.0585 [-0.0785, -0.0396] | 27602 | -0.0669 [-0.3405, +0.1833] |
| fulltext | specter2_proximity | sa | flag_abstract | -0.0198 [-0.0280, -0.0119] | 24843 | -0.0096 [-0.0404, +0.0205] |
| fulltext | specter2_proximity | cd | ai_share | +0.0740 [+0.0490, +0.0991] | 27602 | +0.0920 [-0.2230, +0.4192] |
| fulltext | specter2_proximity | cd | flag_abstract | +0.0257 [+0.0159, +0.0361] | 24843 | +0.0108 [-0.0312, +0.0527] |

## 3. Wording control: original against all-AI rewritten abstracts

Post effect (all links) on the original abstracts, on the all-AI rewrites of the same papers, and the gap (original minus rewrite = the part carried by wording).

| model | measure | original | all-AI | gap (wording) |
|---|---|---|---|---|
| bge_m3 | sa | -0.0122 [-0.0161, -0.0083] | -0.0114 [-0.0153, -0.0075] | -0.0008 [-0.0013, -0.0003] |
| bge_m3 | cd | +0.0150 [+0.0094, +0.0203] | +0.0137 [+0.0083, +0.0190] | +0.0013 [+0.0005, +0.0019] |
| bge_m3 | ss | -0.0142 [-0.0191, -0.0092] | -0.0129 [-0.0179, -0.0079] | -0.0013 [-0.0022, -0.0006] |
| gte_qwen2_1p5b | sa | -0.0077 [-0.0129, -0.0024] | -0.0073 [-0.0124, -0.0020] | -0.0003 [-0.0008, +0.0001] |
| gte_qwen2_1p5b | cd | +0.0065 [-0.0004, +0.0130] | +0.0061 [-0.0007, +0.0129] | +0.0003 [-0.0002, +0.0008] |
| gte_qwen2_1p5b | ss | -0.0089 [-0.0156, -0.0017] | -0.0080 [-0.0149, -0.0009] | -0.0009 [-0.0015, -0.0003] |
| nomic_v15 | sa | -0.0117 [-0.0168, -0.0062] | -0.0098 [-0.0150, -0.0040] | -0.0019 [-0.0026, -0.0013] |
| nomic_v15 | cd | +0.0107 [+0.0033, +0.0175] | +0.0085 [+0.0008, +0.0154] | +0.0022 [+0.0013, +0.0030] |
| nomic_v15 | ss | -0.0128 [-0.0198, -0.0059] | -0.0099 [-0.0170, -0.0028] | -0.0029 [-0.0039, -0.0020] |
| qwen3_0p6b | sa | -0.0092 [-0.0141, -0.0039] | -0.0081 [-0.0130, -0.0028] | -0.0011 [-0.0022, -0.0001] |
| qwen3_0p6b | cd | +0.0085 [+0.0015, +0.0147] | +0.0076 [+0.0007, +0.0139] | +0.0009 [-0.0005, +0.0023] |
| qwen3_0p6b | ss | -0.0067 [-0.0131, -0.0003] | -0.0089 [-0.0154, -0.0025] | +0.0022 [+0.0005, +0.0038] |
| scincl | sa | -0.0080 [-0.0147, -0.0012] | -0.0082 [-0.0150, -0.0014] | +0.0002 [-0.0005, +0.0009] |
| scincl | cd | +0.0043 [-0.0040, +0.0121] | +0.0046 [-0.0038, +0.0125] | -0.0003 [-0.0012, +0.0007] |
| scincl | ss | -0.0080 [-0.0165, +0.0009] | -0.0074 [-0.0158, +0.0014] | -0.0007 [-0.0018, +0.0003] |
| specter2_base | sa | +0.0063 [+0.0004, +0.0122] | +0.0032 [-0.0030, +0.0094] | +0.0031 [+0.0024, +0.0038] |
| specter2_base | cd | -0.0056 [-0.0132, +0.0016] | -0.0029 [-0.0106, +0.0046] | -0.0027 [-0.0035, -0.0019] |
| specter2_base | ss | +0.0033 [-0.0052, +0.0125] | +0.0020 [-0.0068, +0.0110] | +0.0013 [+0.0003, +0.0023] |
| specter2_proximity | sa | -0.0022 [-0.0079, +0.0036] | -0.0034 [-0.0089, +0.0026] | +0.0011 [+0.0004, +0.0018] |
| specter2_proximity | cd | +0.0018 [-0.0052, +0.0090] | +0.0027 [-0.0045, +0.0098] | -0.0008 [-0.0017, +0.0001] |
| specter2_proximity | ss | -0.0021 [-0.0105, +0.0063] | -0.0021 [-0.0101, +0.0060] | +0.0000 [-0.0010, +0.0011] |

Dose in 2023-2025 (coefficient on the abstract-flag exposure, `all` links), original, rewrite and gap:

| model | measure | exposure | original | all-AI | gap (wording) |
|---|---|---|---|---|---|
| bge_m3 | sa | flag_abstract | -0.0064 [-0.0105, -0.0025] | -0.0060 [-0.0101, -0.0020] | -0.0004 [-0.0010, +0.0002] |
| bge_m3 | sa | ai_share | -0.0142 [-0.0239, -0.0047] | -0.0128 [-0.0223, -0.0036] | -0.0014 [-0.0030, +0.0005] |
| bge_m3 | cd | flag_abstract | +0.0095 [+0.0036, +0.0158] | +0.0091 [+0.0032, +0.0151] | +0.0004 [-0.0005, +0.0013] |
| bge_m3 | cd | ai_share | +0.0221 [+0.0076, +0.0370] | +0.0200 [+0.0063, +0.0340] | +0.0020 [-0.0006, +0.0046] |
| gte_qwen2_1p5b | sa | flag_abstract | -0.0092 [-0.0149, -0.0037] | -0.0088 [-0.0146, -0.0034] | -0.0004 [-0.0009, +0.0001] |
| gte_qwen2_1p5b | sa | ai_share | -0.0294 [-0.0422, -0.0158] | -0.0286 [-0.0414, -0.0153] | -0.0008 [-0.0021, +0.0006] |
| gte_qwen2_1p5b | cd | flag_abstract | +0.0131 [+0.0055, +0.0206] | +0.0122 [+0.0045, +0.0201] | +0.0008 [+0.0001, +0.0015] |
| gte_qwen2_1p5b | cd | ai_share | +0.0409 [+0.0220, +0.0589] | +0.0394 [+0.0212, +0.0574] | +0.0015 [-0.0004, +0.0033] |
| nomic_v15 | sa | flag_abstract | -0.0085 [-0.0143, -0.0029] | -0.0086 [-0.0146, -0.0031] | +0.0002 [-0.0007, +0.0011] |
| nomic_v15 | sa | ai_share | -0.0247 [-0.0385, -0.0107] | -0.0242 [-0.0389, -0.0100] | -0.0005 [-0.0029, +0.0018] |
| nomic_v15 | cd | flag_abstract | +0.0119 [+0.0045, +0.0199] | +0.0121 [+0.0045, +0.0202] | -0.0002 [-0.0013, +0.0009] |
| nomic_v15 | cd | ai_share | +0.0341 [+0.0150, +0.0534] | +0.0329 [+0.0128, +0.0539] | +0.0012 [-0.0020, +0.0043] |
| qwen3_0p6b | sa | flag_abstract | -0.0050 [-0.0105, +0.0005] | -0.0056 [-0.0114, +0.0001] | +0.0006 [-0.0009, +0.0021] |
| qwen3_0p6b | sa | ai_share | -0.0186 [-0.0304, -0.0063] | -0.0197 [-0.0329, -0.0072] | +0.0011 [-0.0027, +0.0054] |
| qwen3_0p6b | cd | flag_abstract | +0.0078 [+0.0002, +0.0156] | +0.0083 [+0.0007, +0.0163] | -0.0004 [-0.0025, +0.0015] |
| qwen3_0p6b | cd | ai_share | +0.0290 [+0.0121, +0.0459] | +0.0287 [+0.0114, +0.0472] | +0.0003 [-0.0047, +0.0057] |
| scincl | sa | flag_abstract | -0.0110 [-0.0183, -0.0040] | -0.0102 [-0.0172, -0.0031] | -0.0008 [-0.0017, +0.0001] |
| scincl | sa | ai_share | -0.0355 [-0.0542, -0.0180] | -0.0350 [-0.0540, -0.0167] | -0.0004 [-0.0027, +0.0017] |
| scincl | cd | flag_abstract | +0.0140 [+0.0047, +0.0235] | +0.0128 [+0.0033, +0.0223] | +0.0012 [+0.0000, +0.0023] |
| scincl | cd | ai_share | +0.0432 [+0.0186, +0.0684] | +0.0424 [+0.0173, +0.0675] | +0.0008 [-0.0020, +0.0039] |
| specter2_base | sa | flag_abstract | -0.0092 [-0.0160, -0.0023] | -0.0095 [-0.0164, -0.0025] | +0.0003 [-0.0006, +0.0011] |
| specter2_base | sa | ai_share | -0.0316 [-0.0490, -0.0141] | -0.0333 [-0.0509, -0.0155] | +0.0017 [-0.0007, +0.0039] |
| specter2_base | cd | flag_abstract | +0.0132 [+0.0040, +0.0222] | +0.0131 [+0.0036, +0.0223] | +0.0000 [-0.0010, +0.0011] |
| specter2_base | cd | ai_share | +0.0442 [+0.0205, +0.0672] | +0.0453 [+0.0210, +0.0687] | -0.0011 [-0.0039, +0.0019] |
| specter2_proximity | sa | flag_abstract | -0.0116 [-0.0180, -0.0053] | -0.0112 [-0.0177, -0.0046] | -0.0004 [-0.0013, +0.0005] |
| specter2_proximity | sa | ai_share | -0.0337 [-0.0497, -0.0176] | -0.0335 [-0.0503, -0.0173] | -0.0002 [-0.0023, +0.0019] |
| specter2_proximity | cd | flag_abstract | +0.0161 [+0.0075, +0.0249] | +0.0153 [+0.0065, +0.0241] | +0.0008 [-0.0004, +0.0020] |
| specter2_proximity | cd | ai_share | +0.0463 [+0.0243, +0.0683] | +0.0452 [+0.0220, +0.0677] | +0.0011 [-0.0018, +0.0038] |

## 4. By school and by student role

Post effect on `sa` (all links, original abstracts), per school and per role, for two models; groups with too few labs are n/a. PhD = students whose records list a PhD role; other = undergraduates, masters, postdocs, visitors and others with a stated role (unspecified roles left out).

| model | measure | group | post | n | students | labs |
|---|---|---|---|---|---|---|
| specter2_proximity | sa | school=berkeley | +0.0102 [-0.0065, +0.0270] | 9542 | 2086.0 | 99.0 |
| specter2_proximity | sa | school=cmu | +0.0096 [-0.0014, +0.0213] | 14062 | 3429.0 | 202.0 |
| specter2_proximity | sa | school=epfl | -0.0101 [-0.0227, +0.0032] | 7915 | 1787.0 | 85.0 |
| specter2_proximity | sa | school=gatech | +0.0133 [-0.0251, +0.0527] | 854 | 276.0 | 26.0 |
| specter2_proximity | sa | school=michigan | -0.0139 [-0.0351, +0.0025] | 1492 | 366.0 | 29.0 |
| specter2_proximity | sa | school=mit | -0.0095 [-0.0214, +0.0023] | 10708 | 2717.0 | 146.0 |
| specter2_proximity | sa | school=princeton | -0.0283 [-0.0548, -0.0027] | 3513 | 999.0 | 58.0 |
| specter2_proximity | sa | school=stanford | -0.0065 [-0.0198, +0.0050] | 8982 | 1882.0 | 135.0 |
| specter2_proximity | sa | school=uchicago | +0.0119 [-0.0174, +0.0409] | 1145 | 248.0 | 35.0 |
| specter2_proximity | sa | role=other | -0.0049 [-0.0161, +0.0065] | 10618 | 3491.0 | 319.0 |
| specter2_proximity | sa | role=phd | -0.0016 [-0.0074, +0.0039] | 40888 | 8469.0 | 747.0 |
| specter2_proximity | cd | school=berkeley | -0.0141 [-0.0352, +0.0082] | 9542 | 2086.0 | 99.0 |
| specter2_proximity | cd | school=cmu | -0.0104 [-0.0251, +0.0036] | 14062 | 3429.0 | 202.0 |
| specter2_proximity | cd | school=epfl | +0.0091 [-0.0079, +0.0252] | 7915 | 1787.0 | 85.0 |
| specter2_proximity | cd | school=gatech | -0.0177 [-0.0636, +0.0286] | 854 | 276.0 | 26.0 |
| specter2_proximity | cd | school=michigan | +0.0160 [-0.0069, +0.0434] | 1492 | 366.0 | 29.0 |
| specter2_proximity | cd | school=mit | +0.0128 [-0.0028, +0.0286] | 10708 | 2717.0 | 146.0 |
| specter2_proximity | cd | school=princeton | +0.0353 [+0.0019, +0.0680] | 3513 | 999.0 | 58.0 |
| specter2_proximity | cd | school=stanford | +0.0042 [-0.0103, +0.0210] | 8982 | 1882.0 | 135.0 |
| specter2_proximity | cd | school=uchicago | -0.0270 [-0.0639, +0.0078] | 1145 | 248.0 | 35.0 |
| specter2_proximity | cd | role=other | +0.0053 [-0.0097, +0.0199] | 10618 | 3491.0 | 319.0 |
| specter2_proximity | cd | role=phd | +0.0014 [-0.0050, +0.0087] | 40888 | 8469.0 | 747.0 |
| bge_m3 | sa | school=berkeley | -0.0085 [-0.0186, +0.0023] | 9542 | 2086.0 | 99.0 |
| bge_m3 | sa | school=cmu | -0.0091 [-0.0171, -0.0008] | 14062 | 3429.0 | 202.0 |
| bge_m3 | sa | school=epfl | -0.0135 [-0.0221, -0.0053] | 7915 | 1787.0 | 85.0 |
| bge_m3 | sa | school=gatech | -0.0095 [-0.0346, +0.0157] | 854 | 276.0 | 26.0 |
| bge_m3 | sa | school=michigan | -0.0206 [-0.0315, -0.0102] | 1492 | 366.0 | 29.0 |
| bge_m3 | sa | school=mit | -0.0120 [-0.0196, -0.0041] | 10708 | 2717.0 | 146.0 |
| bge_m3 | sa | school=princeton | -0.0244 [-0.0409, -0.0073] | 3513 | 999.0 | 58.0 |
| bge_m3 | sa | school=stanford | -0.0148 [-0.0224, -0.0081] | 8982 | 1882.0 | 135.0 |
| bge_m3 | sa | school=uchicago | -0.0072 [-0.0236, +0.0093] | 1145 | 248.0 | 35.0 |
| bge_m3 | sa | role=other | -0.0128 [-0.0201, -0.0052] | 10618 | 3491.0 | 319.0 |
| bge_m3 | sa | role=phd | -0.0119 [-0.0156, -0.0083] | 40888 | 8469.0 | 747.0 |
| bge_m3 | cd | school=berkeley | +0.0073 [-0.0086, +0.0225] | 9542 | 2086.0 | 99.0 |
| bge_m3 | cd | school=cmu | +0.0094 [-0.0024, +0.0212] | 14062 | 3429.0 | 202.0 |
| bge_m3 | cd | school=epfl | +0.0172 [+0.0065, +0.0283] | 7915 | 1787.0 | 85.0 |
| bge_m3 | cd | school=gatech | +0.0068 [-0.0288, +0.0426] | 854 | 276.0 | 26.0 |
| bge_m3 | cd | school=michigan | +0.0253 [+0.0108, +0.0400] | 1492 | 366.0 | 29.0 |
| bge_m3 | cd | school=mit | +0.0181 [+0.0072, +0.0290] | 10708 | 2717.0 | 146.0 |
| bge_m3 | cd | school=princeton | +0.0328 [+0.0093, +0.0544] | 3513 | 999.0 | 58.0 |
| bge_m3 | cd | school=stanford | +0.0189 [+0.0097, +0.0291] | 8982 | 1882.0 | 135.0 |
| bge_m3 | cd | school=uchicago | -0.0012 [-0.0267, +0.0226] | 1145 | 248.0 | 35.0 |
| bge_m3 | cd | role=other | +0.0159 [+0.0053, +0.0268] | 10618 | 3491.0 | 319.0 |
| bge_m3 | cd | role=phd | +0.0147 [+0.0097, +0.0199] | 40888 | 8469.0 | 747.0 |

## 5. Yearly means (specter2_proximity abstracts, student-weighted; all links)

| year | cd | sa | ss |
|---|---|---|---|
| 2017 | 0.5273 | 0.4228 | 0.3468 |
| 2018 | 0.5322 | 0.4186 | 0.3352 |
| 2019 | 0.5363 | 0.4156 | 0.3312 |
| 2020 | 0.5367 | 0.4144 | 0.3229 |
| 2021 | 0.5378 | 0.4139 | 0.3364 |
| 2022 | 0.5243 | 0.4233 | 0.3358 |
| 2023 | 0.5249 | 0.4232 | 0.3433 |
| 2024 | 0.5293 | 0.4195 | 0.3358 |
| 2025 | 0.5246 | 0.423 | 0.3474 |

Early years are composed differently (the PI history window is shorter in 2017-2018 and students are earlier in their career); the regressions use lab fixed effects, the raw means are descriptive.

## What changes with the final inputs

- **Final paper set (release 20261105i) and links.** Re-snapshot the hierarchy (`LINEAGE_HIER`), rebuild the universe and embeddings for new papers, then `run_all.sh`. The `verified` share is what matters: today only Princeton, CMU, EPFL and MIT have verified links, so the headline sample is small (1,085 students in the specter2_proximity Post contrast); every additional verified link tightens the intervals in section 1. Students without a role record stay `unspecified`.
- **Detector v3.** Only section 2 (dose) and the `dose_*` rows depend on it: point `LINEAGE_AI` at the v3 table (`paper_id`, `ai_share`, `flag_abstract`). Sections 1, 3 (post effect) and 4 do not.
- **Main/appendix split.** The full-text vectors are whole-body embeddings (the dose study's); when the section-split main body is embedded, rerun with the new containers (`MODELS_FT` in `lineage_common.py`); abstracts are unaffected.

## Re-running

```
# paths: LINEAGE_HIER (a hierarchy snapshot or the live packages), LINEAGE_OUT, LINEAGE_TAG, LINEAGE_AI (detector table: v3 later)
cd <code>/ai-writing/lineage
export LINEAGE_HIER=<snapshot dir or $CS_ATLAS_HIERARCHY> LINEAGE_TAG=<release id>
python lineage_build.py                       # links (12 s)
sbatch --array=0-12%6 lineage.slurm            # 13 (model, kind) tasks, ~3-10 min each
python lineage_report.py                      # LINEAGE.md
```
One command: `ai-writing/lineage/run_all.sh` (build, submit, wait with `tools/slurm_wait.py`, report).
