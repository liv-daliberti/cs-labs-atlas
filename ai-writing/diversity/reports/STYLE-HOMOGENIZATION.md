# Do papers sound more alike? Writing-style homogenization, apart from topic

Generated 2026-11-05 by `ai-writing/style/` (`style_features.py`, `style_extract.py`, `style_analyze.py`, `style_report.py`; tables in `/n/fs/resemble/homogenizing-science/scratch/lineage-style/style/20261105/tables`). **Years 2016-2025 only (no 2026); post = 2023-2025, pre = 2016-2022.** Detector table: `papers.parquet`. Full-text body: `texts.sqlite` = **today's stored body (Introduction to References, pdftotext, 60 pages); the section-split main body (`agent/fulltext-sections`) has not landed, so full-text numbers are on that body and will move when it does.**

## Answer (plain language)

Bullets are generated from the tables; the closing reading is hand-written for the 2026-11-05 run.

- **abstract, topic removed:** dispersion of style vectors changes by +0.0326 [+0.0213, +0.0425] (+3.0% of its pre level) after 2022 (placebo breaks +0.0050 to +0.0114); distance to the 2016-2021 corpus centroid +0.0496 [+0.0379, +0.0598] (+4.6%; placebo +0.0047 to +0.0112).
- **abstract, raw style:** dispersion of style vectors changes by +0.0331 [+0.0215, +0.0476] (+3.0% of its pre level) after 2022 (placebo breaks +0.0081 to +0.0147); distance to the 2016-2021 corpus centroid +0.0594 [+0.0475, +0.0736] (+5.3%; placebo +0.0074 to +0.0145).
- **fulltext, topic removed:** dispersion of style vectors changes by +0.0274 [+0.0110, +0.0406] (+2.6% of its pre level) after 2022 (placebo breaks -0.0059 to +0.0016); distance to the 2016-2021 corpus centroid +0.0476 [+0.0314, +0.0606] (+4.4%; placebo -0.0065 to +0.0017).
- **fulltext, raw style:** dispersion of style vectors changes by +0.0247 [+0.0079, +0.0447] (+2.0% of its pre level) after 2022 (placebo breaks -0.0051 to +0.0059); distance to the 2016-2021 corpus centroid +0.0528 [+0.0360, +0.0713] (+4.3%; placebo -0.0056 to +0.0067).
- **AI link (topic removed, abstracts):** detector-flagged papers of 2023-2025 have a dispersion -0.0720 [-0.1363, -0.0140] (-6.5%) against not-flagged papers of the same year; the same contrast for 'flagged' papers of 2019-2021 (false positives, a placebo) is +0.0460 [-0.0070, +0.1094].
- **AI link (raw, abstracts):** detector-flagged papers of 2023-2025 have a dispersion -0.0862 [-0.1404, -0.0184] (-7.6%) against not-flagged papers of the same year; the same contrast for 'flagged' papers of 2019-2021 (false positives, a placebo) is +0.0481 [-0.0117, +0.1079].
- **All-AI upper bound (abstracts, same papers):** rewriting every abstract lowers the pre-period dispersion from 1.065 to 1.011 (-5.1%), and its post change is +0.0110 [+0.0019, +0.0221] against +0.0322 [+0.0221, +0.0434] for the originals (gap +0.0211 [+0.0132, +0.0299]).

**Reading (hand-written, 2026-11-05 run; recheck after a re-run).** Papers do not sound more alike across the corpus: after 2022 the spread of style vectors goes *up* by about 3% (topic removed), while the distance to the 2016-2021 centroid goes up by about 4.5%; both are several times the placebo breaks inside 2016-2021. The movement is a common drift (Kobak words +0.5 sd, longer words, higher MTLD, fewer `the`/`of`/`is`) of unequal size across papers, so the corpus spreads along that direction instead of collapsing. Uniformity shows only inside the AI-flagged group: flagged papers of 2023-2025 are about 6-7% less dispersed than unflagged papers of the same years, while the 2019-2021 'flagged' false positives are, if anything, more dispersed. The all-AI rewrite is the bound: AI wording alone is about 5% less dispersed than human wording and its dispersion grows only a third as much, so AI wording does not explain the corpus-wide rise in spread (content of the drift: the same words everywhere, adopted to different degrees). Lab level: labs with more flagged abstracts spread more after 2023 (slope +0.05 per unit, interval above zero), the placebo slope is about zero.

## Method

- **Features per text** (`style_features.py`): sentence length mean and standard deviation; MTLD (threshold 0.72, forward and backward; first 5,000 tokens; NaN under 50 tokens, those papers are dropped); mean word length and share of 7+ letter words; Flesch reading ease and Flesch-Kincaid grade; punctuation per 1,000 characters (comma, semicolon, colon, parenthesis, dash, quote, question mark, percent, slash); hedging words per 1,000 words; the Kobak et al. (2024) style-word rate (one feature among ~140); frequencies of 117 function words. **No POS n-gram profile: spaCy and its model are not in the study environment (the nltk tagger data are absent too), so it was skipped.**
- **Space.** Each feature is z-scored on 2016-2022 papers and winsorized at 4 sd; the scalar block and the function-word block get equal total weight; Euclidean distance. **Topic removed (`resid`):** each feature is regressed (OLS, 2016-2022 papers) on OpenAlex subfield dummies and 32 principal components of the abstract embedding (specter2_proximity); the residual is used. Fitting on the pre-period keeps the post-period shift out of the topic model. `raw` is the same without that step.
- **Measures.** Per stratum and year, size-matched draws (1,000 papers for the corpus, 500 for full text, 150 for school/field strata with at least 300 papers a year, 20 per lab-period) from a bootstrap of the stratum's papers, 100 draws: dispersion = mean distance to the draw's centroid, mpd = mean pairwise distance (in the tables' `mpd` rows), convergence = mean distance to the 2016-2021 corpus centroid. Effect = mean of 2023-2025 minus mean of 2016-2022; placebo = the same inside 2016-2021 with breaks at 2019, 2020, 2021. Intervals are 2.5/97.5 percentiles over the draws. Lab level: labs with at least 20 papers in both periods, mean change across labs with a bootstrap over labs, and the slope of the change on the lab's post-period flagged share.
- **AI link.** Flagged = `flag_abstract` (abstract detector) for abstracts, `ai_share >= 0.25` for full text; 60-paper draws per year; effect = flagged minus not-flagged, mean over 2023-2025; the placebo uses 2019-2021 (flagged there are false positives). Flagged and not-flagged are not matched on school or field; the topic-removed space handles content only.
- **All-AI rewrite.** `allai/` (Qwen2.5-7B polish, 97,940 filter-kept abstracts); features of the rewrite use the original corpus's means and sds and the original paper's topic fit, so the comparison is on the same papers.

## 1. Which features moved (all papers, post 2023-2025 minus pre, in sd units of the 2016-2022 spread)

Abstracts, the 14 largest shifts (of ~140 features); the last column is what an all-AI rewrite does to the same feature (original corpus, sd units).

| feature | raw shift | topic removed | sd post / pre | rewrite shift |
|---|---|---|---|---|
| kobak | +0.616 [+0.600, +0.632] | +0.515 | 1.33 | +1.615 |
| word_len | +0.412 [+0.398, +0.426] | +0.297 | 1.11 | +0.832 |
| long_share | +0.365 [+0.351, +0.379] | +0.277 | 1.10 | +0.808 |
| mtld | +0.299 [+0.289, +0.309] | +0.190 | 1.23 | +0.348 |
| fw_the | -0.292 [-0.304, -0.279] | -0.099 | 0.92 | -0.172 |
| fw_of | -0.265 [-0.278, -0.252] | -0.204 | 0.94 | -0.243 |
| fw_across | +0.256 [+0.242, +0.269] | +0.179 | 1.32 | +0.133 |
| fw_is | -0.247 [-0.259, -0.235] | -0.110 | 0.86 | -0.256 |
| p_comma | +0.223 [+0.210, +0.235] | +0.164 | 0.98 | +0.287 |
| flesch | -0.204 [-0.215, -0.193] | -0.087 | 1.12 | -0.245 |
| fw_be | -0.160 [-0.172, -0.148] | -0.126 | 0.87 | -0.248 |
| fw_are | -0.157 [-0.169, -0.145] | -0.106 | 0.87 | -0.163 |
| fw_while | +0.153 [+0.139, +0.166] | +0.124 | 1.11 | +0.072 |
| fw_a | -0.143 [-0.155, -0.130] | -0.116 | 0.93 | -0.039 |

## 2. Dispersion and convergence, whole corpus: abstract

98,771 papers with all features (64,755 pre, 34,016 post). Effect in style-space units (percent of the pre level in brackets).

*topic removed*

| contrast | disp | mpd | conv |
|---|---|---|---|
| post | +0.0326 [+0.0213, +0.0425] (+3.0%) | +0.0460 [+0.0291, +0.0603] (+3.0%) | +0.0496 [+0.0379, +0.0598] (+4.6%) |
| placebo2019 | +0.0050 [-0.0063, +0.0174] (+0.5%) | +0.0068 [-0.0093, +0.0247] (+0.4%) | +0.0047 [-0.0067, +0.0169] (+0.4%) |
| placebo2020 | +0.0098 [-0.0019, +0.0225] (+0.9%) | +0.0141 [-0.0022, +0.0328] (+0.9%) | +0.0095 [-0.0022, +0.0222] (+0.9%) |
| placebo2021 | +0.0114 [-0.0030, +0.0288] (+1.1%) | +0.0165 [-0.0047, +0.0425] (+1.1%) | +0.0112 [-0.0030, +0.0286] (+1.0%) |

*raw*

| contrast | disp | mpd | conv |
|---|---|---|---|
| post | +0.0331 [+0.0215, +0.0476] (+3.0%) | +0.0467 [+0.0307, +0.0678] (+2.9%) | +0.0594 [+0.0475, +0.0736] (+5.3%) |
| placebo2019 | +0.0081 [-0.0020, +0.0205] (+0.7%) | +0.0115 [-0.0033, +0.0295] (+0.7%) | +0.0074 [-0.0023, +0.0198] (+0.7%) |
| placebo2020 | +0.0139 [-0.0005, +0.0263] (+1.2%) | +0.0204 [-0.0014, +0.0383] (+1.3%) | +0.0134 [-0.0004, +0.0255] (+1.2%) |
| placebo2021 | +0.0147 [-0.0051, +0.0323] (+1.3%) | +0.0213 [-0.0075, +0.0464] (+1.3%) | +0.0145 [-0.0051, +0.0321] (+1.3%) |

Yearly means (topic removed):

| year | disp | mpd | conv |
|---|---|---|---|
| 2016 | 1.0771 | 1.5401 | 1.0779 |
| 2017 | 1.0661 | 1.5233 | 1.067 |
| 2018 | 1.0719 | 1.5319 | 1.0727 |
| 2019 | 1.0686 | 1.5264 | 1.0692 |
| 2020 | 1.0777 | 1.5403 | 1.0782 |
| 2021 | 1.0837 | 1.5489 | 1.0842 |
| 2022 | 1.0872 | 1.5542 | 1.0882 |
| 2023 | 1.1026 | 1.5762 | 1.1052 |
| 2024 | 1.1031 | 1.5757 | 1.1164 |
| 2025 | 1.1201 | 1.5997 | 1.1573 |

By school (abstract, topic removed; strata with fewer than 300 papers in some year are left out):

| stratum | disp post | disp placebo range | conv post | conv placebo range |
|---|---|---|---|---|
| berkeley | +0.0444 [+0.0195, +0.0684] (+4.2%) | +0.0110 to +0.0294 | +0.0592 [+0.0348, +0.0815] (+5.5%) | +0.0104 to +0.0290 |
| cmu | +0.0126 [-0.0216, +0.0431] (+1.1%) | -0.0143 to -0.0055 | +0.0326 [-0.0008, +0.0629] (+2.9%) | -0.0142 to -0.0056 |
| epfl | +0.0368 [+0.0134, +0.0669] (+3.6%) | +0.0101 to +0.0229 | +0.0610 [+0.0328, +0.0924] (+5.9%) | +0.0098 to +0.0222 |
| gatech | +0.0371 [+0.0065, +0.0660] (+3.5%) | +0.0090 to +0.0104 | +0.0619 [+0.0357, +0.0934] (+5.9%) | +0.0088 to +0.0101 |
| michigan | +0.0590 [+0.0248, +0.0917] (+5.6%) | +0.0267 to +0.0358 | +0.0725 [+0.0417, +0.1065] (+6.9%) | +0.0257 to +0.0350 |
| mit | +0.0267 [+0.0009, +0.0570] (+2.5%) | +0.0147 to +0.0229 | +0.0414 [+0.0133, +0.0751] (+3.8%) | +0.0146 to +0.0229 |
| princeton | +0.0363 [+0.0061, +0.0645] (+3.4%) | -0.0098 to -0.0081 | +0.0482 [+0.0187, +0.0771] (+4.5%) | -0.0095 to -0.0080 |
| stanford | +0.0352 [+0.0053, +0.0649] (+3.2%) | -0.0023 to +0.0054 | +0.0489 [+0.0193, +0.0771] (+4.5%) | -0.0025 to +0.0050 |

By OpenAlex field (abstract, topic removed; strata with fewer than 300 papers in some year are left out):

| stratum | disp post | disp placebo range | conv post | conv placebo range |
|---|---|---|---|---|
| Computer Science | +0.0288 [+0.0013, +0.0568] (+2.6%) | +0.0051 to +0.0130 | +0.0471 [+0.0213, +0.0762] (+4.3%) | +0.0046 to +0.0123 |
| Engineering | +0.0295 [+0.0033, +0.0598] (+2.9%) | +0.0021 to +0.0033 | +0.0512 [+0.0258, +0.0820] (+5.0%) | +0.0017 to +0.0029 |

## 2. Dispersion and convergence, whole corpus: fulltext

59,522 papers with all features (37,210 pre, 22,312 post). Effect in style-space units (percent of the pre level in brackets).

*topic removed*

| contrast | disp | mpd | conv |
|---|---|---|---|
| post | +0.0274 [+0.0110, +0.0406] (+2.6%) | +0.0381 [+0.0148, +0.0568] (+2.5%) | +0.0476 [+0.0314, +0.0606] (+4.4%) |
| placebo2019 | -0.0059 [-0.0265, +0.0088] (-0.6%) | -0.0093 [-0.0395, +0.0122] (-0.6%) | -0.0065 [-0.0268, +0.0080] (-0.6%) |
| placebo2020 | -0.0020 [-0.0214, +0.0172] (-0.2%) | -0.0041 [-0.0334, +0.0247] (-0.3%) | -0.0022 [-0.0215, +0.0168] (-0.2%) |
| placebo2021 | +0.0016 [-0.0191, +0.0233] (+0.1%) | +0.0015 [-0.0299, +0.0337] (+0.1%) | +0.0017 [-0.0191, +0.0232] (+0.2%) |

*raw*

| contrast | disp | mpd | conv |
|---|---|---|---|
| post | +0.0247 [+0.0079, +0.0447] (+2.0%) | +0.0338 [+0.0099, +0.0616] (+1.9%) | +0.0528 [+0.0360, +0.0713] (+4.3%) |
| placebo2019 | -0.0051 [-0.0257, +0.0137] (-0.4%) | -0.0082 [-0.0391, +0.0201] (-0.5%) | -0.0056 [-0.0260, +0.0134] (-0.5%) |
| placebo2020 | +0.0019 [-0.0201, +0.0225] (+0.2%) | +0.0013 [-0.0291, +0.0319] (+0.1%) | +0.0018 [-0.0194, +0.0221] (+0.2%) |
| placebo2021 | +0.0059 [-0.0199, +0.0379] (+0.5%) | +0.0076 [-0.0293, +0.0520] (+0.4%) | +0.0067 [-0.0192, +0.0379] (+0.5%) |

Yearly means (topic removed):

| year | disp | mpd | conv |
|---|---|---|---|
| 2016 | 1.0782 | 1.5396 | 1.0806 |
| 2017 | 1.0686 | 1.5241 | 1.0704 |
| 2018 | 1.0838 | 1.5474 | 1.0856 |
| 2019 | 1.0677 | 1.5238 | 1.0687 |
| 2020 | 1.07 | 1.5257 | 1.0712 |
| 2021 | 1.0752 | 1.5336 | 1.077 |
| 2022 | 1.0748 | 1.5333 | 1.0774 |
| 2023 | 1.0888 | 1.5539 | 1.0941 |
| 2024 | 1.1039 | 1.5739 | 1.1204 |
| 2025 | 1.1116 | 1.5841 | 1.1557 |

By school (fulltext, topic removed; strata with fewer than 300 papers in some year are left out):

| stratum | disp post | disp placebo range | conv post | conv placebo range |
|---|---|---|---|---|
| berkeley | +0.0430 [+0.0178, +0.0672] (+4.1%) | +0.0023 to +0.0266 | +0.0605 [+0.0334, +0.0848] (+5.8%) | +0.0012 to +0.0272 |
| cmu | +0.0211 [-0.0036, +0.0433] (+2.0%) | -0.0192 to -0.0143 | +0.0453 [+0.0207, +0.0683] (+4.2%) | -0.0209 to -0.0149 |
| epfl | +0.0064 [-0.0203, +0.0347] (+0.6%) | -0.0056 to -0.0025 | +0.0282 [+0.0000, +0.0594] (+2.6%) | -0.0055 to -0.0024 |
| michigan | +0.0264 [+0.0007, +0.0530] (+2.4%) | +0.0230 to +0.0286 | +0.0468 [+0.0210, +0.0756] (+4.3%) | +0.0232 to +0.0287 |
| mit | +0.0241 [+0.0015, +0.0496] (+2.3%) | -0.0029 to +0.0076 | +0.0400 [+0.0175, +0.0662] (+3.7%) | -0.0032 to +0.0080 |
| stanford | +0.0403 [+0.0136, +0.0693] (+3.8%) | -0.0037 to +0.0060 | +0.0619 [+0.0336, +0.0916] (+5.8%) | -0.0048 to +0.0059 |

By OpenAlex field (fulltext, topic removed; strata with fewer than 300 papers in some year are left out):

| stratum | disp post | disp placebo range | conv post | conv placebo range |
|---|---|---|---|---|
| Computer Science | +0.0273 [-0.0006, +0.0508] (+2.6%) | -0.0102 to +0.0003 | +0.0506 [+0.0204, +0.0749] (+4.7%) | -0.0105 to +0.0008 |
| Engineering | +0.0093 [-0.0193, +0.0367] (+0.9%) | -0.0094 to -0.0066 | +0.0367 [+0.0093, +0.0651] (+3.6%) | -0.0104 to -0.0068 |

## 3. Detector-flagged against not-flagged papers (abstracts)

| space | contrast | years | metric | flagged minus not | relative |
|---|---|---|---|---|---|
| raw | post | 3 | disp | -0.0862 [-0.1404, -0.0184] | -7.6% |
| raw | post | 3 | mpd | -0.1270 [-0.2089, -0.0282] | -7.8% |
| raw | post | 3 | conv | +0.0847 [+0.0341, +0.1466] | +7.4% |
| raw | placebo2019-21 | 3 | disp | +0.0481 [-0.0117, +0.1079] | +4.4% |
| raw | placebo2019-21 | 3 | mpd | +0.0657 [-0.0225, +0.1548] | +4.1% |
| raw | placebo2019-21 | 3 | conv | +0.0886 [+0.0260, +0.1452] | +8.0% |
| resid | post | 3 | disp | -0.0720 [-0.1363, -0.0140] | -6.5% |
| resid | post | 3 | mpd | -0.1061 [-0.2045, -0.0203] | -6.7% |
| resid | post | 3 | conv | +0.0540 [-0.0095, +0.1081] | +4.8% |
| resid | placebo2019-21 | 3 | disp | +0.0460 [-0.0070, +0.1094] | +4.3% |
| resid | placebo2019-21 | 3 | mpd | +0.0632 [-0.0160, +0.1528] | +4.1% |
| resid | placebo2019-21 | 3 | conv | +0.0771 [+0.0214, +0.1389] | +7.2% |

Full text (flagged = at least a quarter of passages flagged):

| space | contrast | years | metric | flagged minus not | relative |
|---|---|---|---|---|---|
| raw | post | 3 | disp | -0.1199 [-0.1692, -0.0675] | -9.8% |
| raw | post | 3 | mpd | -0.1720 [-0.2397, -0.0967] | -9.8% |
| raw | post | 3 | conv | +0.1413 [+0.0947, +0.1989] | +11.3% |
| resid | post | 3 | disp | -0.0472 [-0.1089, +0.0065] | -4.4% |
| resid | post | 3 | mpd | -0.0690 [-0.1592, +0.0090] | -4.4% |
| resid | post | 3 | conv | +0.1282 [+0.0671, +0.1860] | +11.6% |

## 4. All-AI rewrite: an upper bound on how uniform AI style makes papers

Same 97,940 papers, original against all-AI wording; `gap` = original minus rewrite. Pre level of the gap = how much more dispersed the human wording is.

| space | variant | metric | pre level | post - pre |
|---|---|---|---|---|
| raw | orig | disp | 1.100 | +0.0339 [+0.0219, +0.0437] |
| raw | orig | mpd | 1.573 | +0.0479 [+0.0309, +0.0631] |
| raw | orig | conv | 1.102 | +0.0617 [+0.0503, +0.0715] |
| raw | allai | disp | 1.040 | +0.0101 [+0.0001, +0.0208] |
| raw | allai | mpd | 1.484 | +0.0139 [-0.0006, +0.0289] |
| raw | allai | conv | 1.183 | +0.0471 [+0.0377, +0.0562] |
| raw | gap | disp | 0.060 | +0.0238 [+0.0149, +0.0343] |
| raw | gap | mpd | 0.089 | +0.0340 [+0.0213, +0.0492] |
| raw | gap | conv | -0.081 | +0.0146 [+0.0037, +0.0252] |
| resid | orig | disp | 1.065 | +0.0322 [+0.0221, +0.0434] |
| resid | orig | mpd | 1.522 | +0.0453 [+0.0311, +0.0618] |
| resid | orig | conv | 1.066 | +0.0504 [+0.0404, +0.0609] |
| resid | allai | disp | 1.011 | +0.0110 [+0.0019, +0.0221] |
| resid | allai | mpd | 1.442 | +0.0151 [+0.0023, +0.0311] |
| resid | allai | conv | 1.153 | +0.0251 [+0.0157, +0.0345] |
| resid | gap | disp | 0.054 | +0.0211 [+0.0132, +0.0299] |
| resid | gap | mpd | 0.080 | +0.0302 [+0.0187, +0.0433] |
| resid | gap | conv | -0.087 | +0.0253 [+0.0167, +0.0350] |

Dispersion by year, topic removed:

| year | allai | gap | orig |
|---|---|---|---|
| 2016 | 1.0122 | 0.051 | 1.0631 |
| 2017 | 1.0069 | 0.0499 | 1.0568 |
| 2018 | 1.0096 | 0.0529 | 1.0625 |
| 2019 | 1.0092 | 0.0496 | 1.0588 |
| 2020 | 1.0058 | 0.0624 | 1.0682 |
| 2021 | 1.0159 | 0.0574 | 1.0733 |
| 2022 | 1.0178 | 0.056 | 1.0738 |
| 2023 | 1.0187 | 0.0707 | 1.0894 |
| 2024 | 1.0182 | 0.0732 | 1.0914 |
| 2025 | 1.0293 | 0.082 | 1.1113 |

## 5. Inside labs (abstracts)

Labs with at least 20 papers in both periods, 20-paper draws. `change` = mean over labs of (later period minus earlier); post = 2023-2025 minus 2016-2022; placebo2019 = 2019-2021 minus 2016-2018. `slope` = change per unit of the lab's later-period flagged-abstract share.

| space | contrast | metric | labs | change | slope on dose |
|---|---|---|---|---|---|
| raw | post | disp | 568 | +0.0239 [+0.0194, +0.0293] | +0.064 [+0.023, +0.104] |
| raw | post | mpd | 568 | +0.0341 [+0.0264, +0.0417] | +0.091 [+0.030, +0.153] |
| raw | placebo2019 | disp | 400 | +0.0077 [+0.0014, +0.0141] | -0.017 [-0.293, +0.245] |
| raw | placebo2019 | mpd | 400 | +0.0109 [+0.0006, +0.0205] | -0.006 [-0.379, +0.382] |
| resid | post | disp | 568 | +0.0229 [+0.0173, +0.0282] | +0.048 [+0.006, +0.094] |
| resid | post | mpd | 568 | +0.0328 [+0.0248, +0.0405] | +0.068 [+0.009, +0.127] |
| resid | placebo2019 | disp | 400 | +0.0060 [-0.0010, +0.0121] | +0.009 [-0.239, +0.255] |
| resid | placebo2019 | mpd | 400 | +0.0083 [-0.0008, +0.0175] | +0.031 [-0.325, +0.372] |

## What changes with the final inputs

- **Final paper set (release 20261105i).** More or fewer papers per school-year; the features are recomputed for new abstracts and full texts only if you rerun `extract` after the texts DB is rebuilt (chunks are keyed by row offsets, so delete `RUN/parts` when the paper list changes). Strata thresholds (300 papers a year) decide which schools and fields appear.
- **Detector v3.** Only the AI-link section (flagged vs not, lab slope) and the 0.25 full-text threshold depend on the detector: set `STYLE_AI` to the v3 table (columns `paper_id`, `ai_share`, `flag_abstract`). Dispersion, convergence and the all-AI bound do not use it.
- **Main/appendix split (`agent/fulltext-sections`).** Point `STYLE_FULLTEXT_DB` at the texts DB holding the section-split main body (same `fulltext(paper_id, body, usable)` table); full-text features and every full-text number then follow. Today's body includes appendices and, with the extraction's 60-page cap, may include acknowledgements.
- **POS profile.** Add it when spaCy `en_core_web_sm` is installed in the study environment (a new block in `style_features.py`).

## Re-running

```
cd <code>/ai-writing/style
export STYLE_TAG=<release id>  [STYLE_AI=<detector parquet: v3>]  [STYLE_FULLTEXT_DB=<texts db with the section-split main body>]
sbatch style.slurm extract abstract; sbatch style.slurm extract allai; sbatch style.slurm extract fulltext     # features, resumable, a few minutes
sbatch style.slurm analyze abstract; sbatch style.slurm analyze fulltext
python style_report.py
```
One command: `ai-writing/style/run_all.sh`.
