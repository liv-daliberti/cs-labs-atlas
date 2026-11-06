# AI added in revision: arXiv v1 against the later version (Experiment B, detector v2)

Generated 2026-11-06T01:27:43Z by `ai-writing/revision/rv_report.py`. Detector v2: flagged passage = P(AI) >= 0.000853 (1% passage false-positive rate by design on pre-ChatGPT text), strict = P(AI) >= 0.5; passages between the two cuts are the abstain band. All intervals: cluster bootstrap over first labs. Years end at 2025.

## Summary

**Kind S, v1 before Dec 2022 and later text after:** 811 pairs; mean change in flagged-passage share 0.0006 [-0.0005, 0.0019] (v1 level 0.011); against the pre_pre baseline -0.0001 [-0.0013, 0.0012], matched -0.0026 [-0.0072, 0.0013] (441 of 811 pairs kept). Shares are fractions of passages (0.01 = one point).
**Kind A, v1 before Dec 2022 and later text after:** 455 pairs; mean change in flagged-passage share 0.0044 [0.0023, 0.0067] (v1 level 0.010); against the pre_pre baseline 0.0039 [0.0014, 0.0064], matched 0.0026 [-0.0007, 0.0058] (306 of 455 pairs kept). Shares are fractions of passages (0.01 = one point).
Every difference is a fraction of passages; the detector flags about 1% of human passages by design, so effects of a few tenths of a point are near its floor. Details, strict cut, abstract and Kobak rows below.

## 1. Pairs

Pair kinds: **S** = arXiv v1 (public cloud-mirror copy) against the lab paper's stored full text (the version our stores captured), dated by its publication date; **A** = arXiv v1 against the latest arXiv version in the mirror (dated by the margin stamp). The mirror does not hold late revisions of old arXiv papers (a 2022 paper's latest mirrored version is uploaded within the month of v1), so only kind S can show "v1 before Dec 2022, final after".

| kind | pairs_scored | v1_title_found | same_work | dated | valid | valid_to_2025 | cells |
|---|---|---|---|---|---|---|---|
| S | 11471 | 10515 | 10851 | 11471 | 7729 | 6725 | post_post: 3133, pre_post: 811, pre_pre: 2781 |
| A | 8059 | 6558 | 7315 | 7979 | 6084 | 5795 | post_post: 2224, pre_post: 455, pre_pre: 3116 |

Filters (exact pairing): the arXiv record's DOI equals the paper's DOI with compatible titles, or the paper's own arXiv DOI, or an identical normalised title with a single arXiv record within -1 to +3 years; the v1 PDF shows the arXiv title on page 1; >= 10 passages and >= 1,000 body words in both texts; >= 20% of v1's 8-word shingles occur in the later text (same work); the later text is dated. Cell names: v1 period _ final period, `pre` = before 1 Dec 2022 (final of kind S: before 1 Jan 2023; papers published in Dec 2022 are left out as the transition month).

## 2S. Change in AI wording, kind S

Mean change (later text minus v1) per cell, with `v1` the mean level in v1; `pre_pre` is the revision-noise and false-positive baseline (both texts predate ChatGPT: any change is revision, extraction and detector noise, since the flagged share of human text is about 1% by design).

| outcome | all | post_post | pre_post | pre_pre |
|---|---|---|---|---|
| Kobak style words per 1,000 tokens (abstract) | 0.723 [0.392, 1.037] | 1.049 [0.532, 1.569] | 0.683 [-0.233, 1.672] | 0.370 [-0.005, 0.750] |
| abstain band (flagged, not strict) | 0.000 [-0.000, 0.001] | 0.000 [-0.001, 0.001] | 0.000 [-0.001, 0.001] | 0.000 [-0.000, 0.001] |
| abstract flag (v1 abstract detector) | 0.014 [0.010, 0.019] | 0.019 [0.010, 0.028] | 0.019 [0.008, 0.032] | 0.007 [0.003, 0.012] |
| flagged-passage share (ai_share) | 0.000 [-0.000, 0.001] | 0.000 [-0.001, 0.001] | 0.001 [-0.001, 0.002] | 0.001 [0.000, 0.001] |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | 0.120 [0.111, 0.129] | 0.180 [0.165, 0.195] | 0.039 [0.024, 0.055] | 0.075 [0.064, 0.086] |
| strict share (p >= 0.5) | 0.000 [-0.000, 0.001] | -0.000 [-0.001, 0.001] | 0.000 [-0.000, 0.001] | 0.000 [0.000, 0.001] |

Pairs and mean v1 level by cell (flagged share):

| cell | n | v1 |
|---|---|---|
| post_post | 3133 | 0.104 |
| pre_post | 811 | 0.011 |
| pre_pre | 2781 | 0.009 |
| all | 6725 | 0.053 |

### Contrasts, kind S

Difference between cells in the mean change. `matched`: control pairs reweighted to the treated pairs' school x v1-year bin x revision-lag bin distribution (coarsened exact; strata without control are dropped, `kept` = treated pairs retained).

| outcome | contrast | matched | diff (95% CI) | n_treat | n_ctrl | kept |
|---|---|---|---|---|---|---|
| flagged-passage share (ai_share) | pre_post - pre_pre | False | -0.000 [-0.001, 0.001] | 811 | 2781 | 811/811 |
| flagged-passage share (ai_share) | post_post - pre_pre | False | -0.001 [-0.002, 0.001] | 3133 | 2781 | 3133/3133 |
| flagged-passage share (ai_share) | pre_post - post_post | False | 0.001 [-0.001, 0.002] | 811 | 3133 | 811/811 |
| flagged-passage share (ai_share) | pre_post - pre_pre | True | -0.003 [-0.007, 0.001] | 441 | 655 | 441/811 |
| flagged-passage share (ai_share) | post_post - pre_pre | True | 0.004 [-0.003, 0.011] | 49 | 521 | 49/3133 |
| flagged-passage share (ai_share) | pre_post - post_post | True | -0.005 [-0.013, 0.001] | 449 | 63 | 449/811 |
| strict share (p >= 0.5) | pre_post - pre_pre | False | 0.000 [-0.000, 0.001] | 811 | 2781 | 811/811 |
| strict share (p >= 0.5) | post_post - pre_pre | False | -0.000 [-0.001, 0.001] | 3133 | 2781 | 3133/3133 |
| strict share (p >= 0.5) | pre_post - post_post | False | 0.001 [-0.001, 0.002] | 811 | 3133 | 811/811 |
| strict share (p >= 0.5) | pre_post - pre_pre | True | 0.000 [-0.002, 0.002] | 441 | 655 | 441/811 |
| strict share (p >= 0.5) | post_post - pre_pre | True | 0.002 [-0.001, 0.004] | 49 | 521 | 49/3133 |
| strict share (p >= 0.5) | pre_post - post_post | True | -0.000 [-0.001, 0.001] | 449 | 63 | 449/811 |
| abstain band (flagged, not strict) | pre_post - pre_pre | False | -0.000 [-0.001, 0.001] | 811 | 2781 | 811/811 |
| abstain band (flagged, not strict) | post_post - pre_pre | False | -0.000 [-0.001, 0.001] | 3133 | 2781 | 3133/3133 |
| abstain band (flagged, not strict) | pre_post - post_post | False | -0.000 [-0.001, 0.002] | 811 | 3133 | 811/811 |
| abstain band (flagged, not strict) | pre_post - pre_pre | True | -0.003 [-0.007, 0.001] | 441 | 655 | 441/811 |
| abstain band (flagged, not strict) | post_post - pre_pre | True | 0.002 [-0.005, 0.010] | 49 | 521 | 49/3133 |
| abstain band (flagged, not strict) | pre_post - post_post | True | -0.005 [-0.012, 0.002] | 449 | 63 | 449/811 |
| abstract flag (v1 abstract detector) | pre_post - pre_pre | False | 0.012 [-0.001, 0.027] | 627 | 2399 | 811/811 |
| abstract flag (v1 abstract detector) | post_post - pre_pre | False | 0.012 [0.002, 0.022] | 2661 | 2399 | 3133/3133 |
| abstract flag (v1 abstract detector) | pre_post - post_post | False | 0.000 [-0.014, 0.016] | 627 | 2661 | 811/811 |
| abstract flag (v1 abstract detector) | pre_post - pre_pre | True | 0.012 [-0.007, 0.032] | 351 | 568 | 441/811 |
| abstract flag (v1 abstract detector) | post_post - pre_pre | True | -0.002 [-0.076, 0.072] | 38 | 476 | 49/3133 |
| abstract flag (v1 abstract detector) | pre_post - post_post | True | -0.009 [-0.047, 0.019] | 358 | 51 | 449/811 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - pre_pre | False | -0.035 [-0.055, -0.016] | 627 | 2399 | 811/811 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | post_post - pre_pre | False | 0.105 [0.088, 0.124] | 2661 | 2399 | 3133/3133 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - post_post | False | -0.140 [-0.161, -0.120] | 627 | 2661 | 811/811 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - pre_pre | True | -0.006 [-0.034, 0.021] | 351 | 568 | 441/811 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | post_post - pre_pre | True | -0.081 [-0.104, -0.057] | 38 | 476 | 49/3133 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - post_post | True | 0.027 [-0.007, 0.052] | 358 | 51 | 449/811 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - pre_pre | False | 0.313 [-0.643, 1.239] | 636 | 2433 | 811/811 |
| Kobak style words per 1,000 tokens (abstract) | post_post - pre_pre | False | 0.678 [0.007, 1.315] | 2708 | 2433 | 3133/3133 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - post_post | False | -0.366 [-1.357, 0.630] | 636 | 2708 | 811/811 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - pre_pre | True | 1.186 [-1.069, 3.541] | 357 | 573 | 441/811 |
| Kobak style words per 1,000 tokens (abstract) | post_post - pre_pre | True | -2.732 [-7.732, 1.700] | 42 | 480 | 49/3133 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - post_post | True | 0.229 [-2.997, 3.445] | 365 | 55 | 449/811 |

### Regression, kind S

Change = cell dummies (pre_pre is the base) + controls: school FE, field FE, revision lag (months), log length ratio, v1 level; clustered by first lab.

| outcome | term | cells | school_fe | school_field_fe | start_level |
|---|---|---|---|---|---|
| Kobak style words per 1,000 tokens (abstract) | post_post | 0.678 [0.055, 1.302] | 0.800 [0.153, 1.446] | 0.843 [0.189, 1.497] | 0.930 [0.231, 1.629] |
| Kobak style words per 1,000 tokens (abstract) | pre_post | 0.313 [-0.666, 1.291] | -0.150 [-1.308, 1.009] | -0.168 [-1.326, 0.990] | -0.159 [-1.317, 0.999] |
| flagged-passage share (ai_share) | post_post | -0.001 [-0.002, 0.001] | -0.000 [-0.002, 0.001] | -0.000 [-0.002, 0.001] | 0.005 [0.004, 0.007] |
| flagged-passage share (ai_share) | pre_post | -0.000 [-0.001, 0.001] | -0.001 [-0.003, 0.001] | -0.001 [-0.003, 0.001] | -0.000 [-0.002, 0.001] |
| strict share (p >= 0.5) | post_post | -0.000 [-0.002, 0.001] | -0.000 [-0.001, 0.001] | -0.000 [-0.001, 0.001] | 0.003 [0.002, 0.004] |
| strict share (p >= 0.5) | pre_post | 0.000 [-0.000, 0.001] | -0.000 [-0.001, 0.001] | -0.000 [-0.001, 0.001] | 0.000 [-0.001, 0.001] |

### Pairs where AI looks added, kind S

| rule | post_post | pre_post | pre_pre |
|---|---|---|---|
| final>=25% flagged, v1<5% | 0.1 [0.0, 0.3] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.1] |
| final>=25% strict, v1<5% strict | 0.0 [0.0, 0.1] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |

(per cent of pairs; the `pre_pre` share is the false-positive floor of the rule.)

### Mean change in flagged share by year of v1 (rows) and year of the later text (columns), kind S, cells with >= 20 pairs

| y1 | 2016.0 | 2017.0 | 2018.0 | 2019.0 | 2020.0 | 2021.0 | 2022.0 | 2023.0 | 2024.0 | 2025.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016.0 | -0.001 | 0.001 |  |  |  |  |  |  |  |  |
| 2017.0 |  | -0.0 | -0.003 |  |  |  |  |  |  |  |
| 2018.0 |  |  | -0.0 | -0.002 | -0.001 |  |  |  |  |  |
| 2019.0 |  |  |  | -0.0 | -0.0 | 0.004 |  |  |  |  |
| 2020.0 |  |  |  |  | 0.0 | 0.002 | 0.005 | -0.003 |  |  |
| 2021.0 |  |  |  |  |  | 0.001 | 0.003 | 0.0 | -0.002 |  |
| 2022.0 |  |  |  |  |  |  | 0.002 | 0.001 | 0.005 | 0.003 |
| 2023.0 |  |  |  |  |  |  |  | 0.001 | 0.002 | 0.004 |
| 2024.0 |  |  |  |  |  |  |  |  | 0.001 | 0.004 |
| 2025.0 |  |  |  |  |  |  |  |  |  | -0.004 |

## 2A. Change in AI wording, kind A

Mean change (later text minus v1) per cell, with `v1` the mean level in v1; `pre_pre` is the revision-noise and false-positive baseline (both texts predate ChatGPT: any change is revision, extraction and detector noise, since the flagged share of human text is about 1% by design).

| outcome | all | post_post | pre_post | pre_pre |
|---|---|---|---|---|
| Kobak style words per 1,000 tokens (abstract) | 0.080 [-0.151, 0.305] | 0.226 [-0.200, 0.662] | 0.390 [-0.514, 1.378] | -0.066 [-0.307, 0.207] |
| abstain band (flagged, not strict) | 0.001 [-0.000, 0.001] | 0.001 [-0.001, 0.002] | 0.001 [-0.000, 0.003] | 0.001 [-0.000, 0.001] |
| abstract flag (v1 abstract detector) | 0.004 [0.000, 0.008] | 0.010 [0.001, 0.021] | 0.002 [-0.005, 0.012] | -0.000 [-0.004, 0.003] |
| flagged-passage share (ai_share) | 0.001 [-0.000, 0.002] | 0.000 [-0.002, 0.003] | 0.004 [0.002, 0.007] | 0.001 [-0.000, 0.001] |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | 0.007 [0.003, 0.011] | 0.013 [0.004, 0.022] | 0.008 [-0.002, 0.021] | 0.002 [-0.001, 0.005] |
| strict share (p >= 0.5) | 0.000 [-0.001, 0.001] | -0.000 [-0.002, 0.002] | 0.003 [0.002, 0.004] | 0.000 [-0.000, 0.000] |

Pairs and mean v1 level by cell (flagged share):

| cell | n | v1 |
|---|---|---|
| post_post | 2224 | 0.107 |
| pre_post | 455 | 0.01 |
| pre_pre | 3116 | 0.009 |
| all | 5795 | 0.046 |

### Contrasts, kind A

Difference between cells in the mean change. `matched`: control pairs reweighted to the treated pairs' school x v1-year bin x revision-lag bin distribution (coarsened exact; strata without control are dropped, `kept` = treated pairs retained).

| outcome | contrast | matched | diff (95% CI) | n_treat | n_ctrl | kept |
|---|---|---|---|---|---|---|
| flagged-passage share (ai_share) | pre_post - pre_pre | False | 0.004 [0.001, 0.006] | 455 | 3116 | 455/455 |
| flagged-passage share (ai_share) | post_post - pre_pre | False | -0.000 [-0.003, 0.002] | 2224 | 3116 | 2224/2224 |
| flagged-passage share (ai_share) | pre_post - post_post | False | 0.004 [0.001, 0.007] | 455 | 2224 | 455/455 |
| flagged-passage share (ai_share) | pre_post - pre_pre | True | 0.003 [-0.001, 0.006] | 306 | 505 | 306/455 |
| flagged-passage share (ai_share) | post_post - pre_pre | True | 0.006 [0.000, 0.012] | 55 | 320 | 55/2224 |
| flagged-passage share (ai_share) | pre_post - post_post | True | -0.004 [-0.013, 0.007] | 249 | 66 | 249/455 |
| strict share (p >= 0.5) | pre_post - pre_pre | False | 0.003 [0.002, 0.004] | 455 | 3116 | 455/455 |
| strict share (p >= 0.5) | post_post - pre_pre | False | -0.000 [-0.002, 0.002] | 2224 | 3116 | 2224/2224 |
| strict share (p >= 0.5) | pre_post - post_post | False | 0.003 [0.001, 0.006] | 455 | 2224 | 455/455 |
| strict share (p >= 0.5) | pre_post - pre_pre | True | 0.002 [0.000, 0.003] | 306 | 505 | 306/455 |
| strict share (p >= 0.5) | post_post - pre_pre | True | 0.000 [-0.003, 0.003] | 55 | 320 | 55/2224 |
| strict share (p >= 0.5) | pre_post - post_post | True | 0.002 [-0.004, 0.007] | 249 | 66 | 249/455 |
| abstain band (flagged, not strict) | pre_post - pre_pre | False | 0.001 [-0.001, 0.003] | 455 | 3116 | 455/455 |
| abstain band (flagged, not strict) | post_post - pre_pre | False | 0.000 [-0.001, 0.002] | 2224 | 3116 | 2224/2224 |
| abstain band (flagged, not strict) | pre_post - post_post | False | 0.001 [-0.001, 0.003] | 455 | 2224 | 455/455 |
| abstain band (flagged, not strict) | pre_post - pre_pre | True | 0.001 [-0.002, 0.004] | 306 | 505 | 306/455 |
| abstain band (flagged, not strict) | post_post - pre_pre | True | 0.006 [0.001, 0.011] | 55 | 320 | 55/2224 |
| abstain band (flagged, not strict) | pre_post - post_post | True | -0.006 [-0.013, 0.002] | 249 | 66 | 249/455 |
| abstract flag (v1 abstract detector) | pre_post - pre_pre | False | 0.003 [-0.006, 0.012] | 411 | 2891 | 455/455 |
| abstract flag (v1 abstract detector) | post_post - pre_pre | False | 0.011 [0.001, 0.021] | 2029 | 2891 | 2224/2224 |
| abstract flag (v1 abstract detector) | pre_post - post_post | False | -0.008 [-0.020, 0.005] | 411 | 2029 | 455/455 |
| abstract flag (v1 abstract detector) | pre_post - pre_pre | True | -0.002 [-0.005, 0.000] | 279 | 463 | 306/455 |
| abstract flag (v1 abstract detector) | post_post - pre_pre | True | 0.015 [-0.010, 0.061] | 49 | 302 | 55/2224 |
| abstract flag (v1 abstract detector) | pre_post - post_post | True | -0.024 [-0.094, 0.009] | 233 | 59 | 249/455 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - pre_pre | False | 0.006 [-0.004, 0.017] | 411 | 2891 | 455/455 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | post_post - pre_pre | False | 0.011 [0.000, 0.021] | 2029 | 2891 | 2224/2224 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - post_post | False | -0.005 [-0.019, 0.010] | 411 | 2029 | 455/455 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - pre_pre | True | 0.006 [-0.003, 0.019] | 279 | 463 | 306/455 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | post_post - pre_pre | True | -0.001 [-0.013, 0.012] | 49 | 302 | 55/2224 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - post_post | True | 0.007 [-0.008, 0.023] | 233 | 59 | 249/455 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - pre_pre | False | 0.456 [-0.506, 1.406] | 411 | 2891 | 455/455 |
| Kobak style words per 1,000 tokens (abstract) | post_post - pre_pre | False | 0.292 [-0.242, 0.825] | 2029 | 2891 | 2224/2224 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - post_post | False | 0.164 [-0.806, 1.229] | 411 | 2029 | 455/455 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - pre_pre | True | 0.430 [-1.080, 2.046] | 279 | 463 | 306/455 |
| Kobak style words per 1,000 tokens (abstract) | post_post - pre_pre | True | 1.806 [-0.478, 3.962] | 49 | 302 | 55/2224 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - post_post | True | -0.437 [-3.870, 3.423] | 233 | 59 | 249/455 |

### Regression, kind A

Change = cell dummies (pre_pre is the base) + controls: school FE, field FE, revision lag (months), log length ratio, v1 level; clustered by first lab.

| outcome | term | cells | school_fe | school_field_fe | start_level |
|---|---|---|---|---|---|
| Kobak style words per 1,000 tokens (abstract) | post_post | 0.292 [-0.225, 0.809] | 0.377 [-0.148, 0.902] | 0.362 [-0.169, 0.892] | 0.647 [0.081, 1.212] |
| Kobak style words per 1,000 tokens (abstract) | pre_post | 0.456 [-0.507, 1.420] | 0.500 [-0.521, 1.521] | 0.494 [-0.537, 1.524] | 0.504 [-0.526, 1.534] |
| flagged-passage share (ai_share) | post_post | -0.000 [-0.003, 0.002] | 0.000 [-0.002, 0.003] | 0.000 [-0.002, 0.003] | 0.011 [0.008, 0.013] |
| flagged-passage share (ai_share) | pre_post | 0.004 [0.001, 0.006] | 0.003 [0.001, 0.006] | 0.003 [0.001, 0.006] | 0.004 [0.001, 0.006] |
| strict share (p >= 0.5) | post_post | -0.000 [-0.002, 0.002] | 0.000 [-0.002, 0.002] | 0.000 [-0.002, 0.002] | 0.007 [0.005, 0.008] |
| strict share (p >= 0.5) | pre_post | 0.003 [0.002, 0.004] | 0.003 [0.001, 0.004] | 0.003 [0.002, 0.005] | 0.003 [0.002, 0.005] |

### Pairs where AI looks added, kind A

| rule | post_post | pre_post | pre_pre |
|---|---|---|---|
| final>=25% flagged, v1<5% | 0.2 [0.0, 0.4] | 0.2 [0.0, 0.7] | 0.0 [0.0, 0.1] |
| final>=25% strict, v1<5% strict | 0.0 [0.0, 0.1] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |

(per cent of pairs; the `pre_pre` share is the false-positive floor of the rule.)

### Mean change in flagged share by year of v1 (rows) and year of the later text (columns), kind A, cells with >= 20 pairs

| y1 | 2016.0 | 2017.0 | 2018.0 | 2019.0 | 2020.0 | 2021.0 | 2022.0 | 2023.0 | 2024.0 | 2025.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2015.0 | -0.001 | 0.0 |  |  |  |  |  |  |  |  |
| 2016.0 | 0.001 | 0.0 |  |  |  |  |  |  |  |  |
| 2017.0 |  | -0.001 | -0.002 | -0.002 |  |  |  |  |  |  |
| 2018.0 |  |  | 0.0 | 0.001 | -0.001 |  |  |  |  |  |
| 2019.0 |  |  |  | 0.001 | 0.001 | 0.003 |  |  |  |  |
| 2020.0 |  |  |  |  | 0.001 | 0.002 | 0.001 | 0.003 |  |  |
| 2021.0 |  |  |  |  |  | 0.0 | 0.001 | 0.005 |  |  |
| 2022.0 |  |  |  |  |  |  | 0.0 | 0.002 | 0.013 |  |
| 2023.0 |  |  |  |  |  |  |  | 0.004 | 0.0 | -0.001 |
| 2024.0 |  |  |  |  |  |  |  |  | -0.002 | 0.006 |
| 2025.0 |  |  |  |  |  |  |  |  |  | -0.006 |

## 3. Reading and limits

- A positive `pre_post - pre_pre` difference is the extra rise in flagged wording between v1 and a later text when the later text was written in the ChatGPT era, over the rise that revision alone gives. For kind S the later text is the stored (usually published) version, whose extraction differs from the arXiv PDF's; `pre_pre` carries the same mismatch, so the contrast removes it to first order.
- v1 of a post-2022 paper may already contain AI wording, so `post_post` changes understate use; `pre_post` begins from human v1 texts and is the cleaner contrast, but its pairs sit mostly in 2022-2023 (the earliest months of use), where the flagged-share rise is small.
- The passage detector flags about 1% of human passages by design; with roughly 60 passages per paper a single paper's change is noisy, so conclusions rest on cell means and the share of pairs, not on single papers.
- Kobak style words in abstracts are detector-free; for kind S the later abstract is OpenAlex's (the published abstract), for A the arXiv PDF's, extracted by a heading rule (`Abstract` ... `Introduction`).
