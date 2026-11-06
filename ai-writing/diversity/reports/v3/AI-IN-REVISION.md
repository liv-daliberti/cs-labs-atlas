# AI added in revision: arXiv v1 against the later version (Experiment B, detector v3)

Generated 2026-11-06T04:47:32Z by `ai-writing/revision/rv_report.py`. Detector v3 (main body only, `fulltext_sections.split_text` for the arXiv texts and the v3 container for the stored copies; abstained passages excluded): flagged passage = v3 score z >= -6.12 (0.3% false-alarm rate on calibration passages; human passages wrongly flagged 0.30%, 0.27-0.32%), strict = z >= 0.0 (P(AI) >= 0.5); passages between the two cuts are the abstain band (flagged, not confident). All intervals: cluster bootstrap over first labs. Years end at 2025. v3 shares are not comparable in level with the v2 report.

## Summary

**Kind S, v1 before Dec 2022 and later text after:** 784 pairs; mean change in flagged-passage share 0.0011 [0.0001, 0.0022] (v1 level 0.003); against the pre_pre baseline 0.0006 [-0.0005, 0.0020], matched 0.0009 [-0.0015, 0.0036] (430 of 784 pairs kept). Shares are fractions of passages (0.01 = one point).
**Kind A, v1 before Dec 2022 and later text after:** 444 pairs; mean change in flagged-passage share 0.0029 [0.0010, 0.0057] (v1 level 0.004); against the pre_pre baseline 0.0031 [0.0010, 0.0055], matched 0.0008 [-0.0014, 0.0032] (300 of 444 pairs kept). Shares are fractions of passages (0.01 = one point).
Every difference is a fraction of passages; the detector flags about 0.3% of human passages by design, so effects of a few tenths of a point are near its floor. Details, strict cut, abstract and Kobak rows below.

## 1. Pairs

Pair kinds: **S** = arXiv v1 (public cloud-mirror copy) against the lab paper's stored full text (the version our stores captured), dated by its publication date; **A** = arXiv v1 against the latest arXiv version in the mirror (dated by the margin stamp). The mirror does not hold late revisions of old arXiv papers (a 2022 paper's latest mirrored version is uploaded within the month of v1), so only kind S can show "v1 before Dec 2022, final after".

| kind | pairs_scored | v1_title_found | same_work | dated | valid | valid_to_2025 | cells |
|---|---|---|---|---|---|---|---|
| S | 11234 | 10296 | 10631 | 11234 | 7518 | 5987 | post_post: 3034, pre_post: 784, pre_pre: 2169 |
| A | 7877 | 6405 | 7145 | 7799 | 5917 | 5637 | post_post: 2138, pre_post: 444, pre_pre: 3055 |

Filters (exact pairing): the arXiv record's DOI equals the paper's DOI with compatible titles, or the paper's own arXiv DOI, or an identical normalised title with a single arXiv record within -1 to +3 years; the v1 PDF shows the arXiv title on page 1; >= 10 passages and >= 1,000 body words in both texts; >= 20% of v1's 8-word shingles occur in the later text (same work); the later text is dated. Cell names: v1 period _ final period, `pre` = before 1 Dec 2022 (final of kind S: before 1 Jan 2023; papers published in Dec 2022 are left out as the transition month).

## 2S. Change in AI wording, kind S

Mean change (later text minus v1) per cell, with `v1` the mean level in v1; `pre_pre` is the revision-noise and false-positive baseline (both texts predate ChatGPT: any change is revision, extraction and detector noise, since the flagged share of human text is about 1% by design).

| outcome | all | post_post | pre_post | pre_pre |
|---|---|---|---|---|
| Kobak style words per 1,000 tokens (abstract) | 0.812 [0.451, 1.151] | 1.147 [0.694, 1.723] | 0.568 [-0.431, 1.417] | 0.427 [0.029, 0.900] |
| abstain band (flagged, not strict) | 0.001 [0.000, 0.002] | 0.002 [0.001, 0.003] | 0.001 [-0.000, 0.001] | 0.000 [-0.000, 0.001] |
| abstract flag (v1 abstract detector) | 0.014 [0.009, 0.019] | 0.017 [0.010, 0.027] | 0.020 [0.008, 0.034] | 0.007 [0.002, 0.011] |
| flagged-passage share (ai_share) | 0.001 [0.000, 0.002] | 0.001 [-0.000, 0.003] | 0.001 [0.000, 0.002] | 0.001 [-0.000, 0.001] |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | n/a | n/a | n/a | n/a |
| strict share (p >= 0.5) | -0.000 [-0.001, 0.001] | -0.000 [-0.002, 0.001] | 0.001 [-0.000, 0.001] | 0.000 [-0.000, 0.001] |

Pairs and mean v1 level by cell (flagged share):

| cell | n | v1 |
|---|---|---|
| post_post | 3034 | 0.116 |
| pre_post | 784 | 0.003 |
| pre_pre | 2169 | 0.003 |
| all | 5987 | 0.06 |

### Contrasts, kind S

Difference between cells in the mean change. `matched`: control pairs reweighted to the treated pairs' school x v1-year bin x revision-lag bin distribution (coarsened exact; strata without control are dropped, `kept` = treated pairs retained).

| outcome | contrast | matched | diff (95% CI) | n_treat | n_ctrl | kept |
|---|---|---|---|---|---|---|
| flagged-passage share (ai_share) | pre_post - pre_pre | False | 0.001 [-0.000, 0.002] | 784 | 2169 | 784/784 |
| flagged-passage share (ai_share) | post_post - pre_pre | False | 0.001 [-0.001, 0.003] | 3034 | 2169 | 3034/3034 |
| flagged-passage share (ai_share) | pre_post - post_post | False | -0.000 [-0.002, 0.002] | 784 | 3034 | 784/784 |
| flagged-passage share (ai_share) | pre_post - pre_pre | True | 0.001 [-0.002, 0.004] | 430 | 613 | 430/784 |
| flagged-passage share (ai_share) | post_post - pre_pre | True | 0.001 [-0.003, 0.006] | 48 | 500 | 48/3034 |
| flagged-passage share (ai_share) | pre_post - post_post | True | 0.002 [-0.000, 0.004] | 417 | 61 | 417/784 |
| strict share (p >= 0.5) | pre_post - pre_pre | False | 0.000 [-0.000, 0.001] | 784 | 2169 | 784/784 |
| strict share (p >= 0.5) | post_post - pre_pre | False | -0.001 [-0.002, 0.001] | 3034 | 2169 | 3034/3034 |
| strict share (p >= 0.5) | pre_post - post_post | False | 0.001 [-0.001, 0.003] | 784 | 3034 | 784/784 |
| strict share (p >= 0.5) | pre_post - pre_pre | True | 0.001 [-0.000, 0.001] | 430 | 613 | 430/784 |
| strict share (p >= 0.5) | post_post - pre_pre | True | -0.000 [-0.001, 0.000] | 48 | 500 | 48/3034 |
| strict share (p >= 0.5) | pre_post - post_post | True | 0.001 [0.000, 0.002] | 417 | 61 | 417/784 |
| abstain band (flagged, not strict) | pre_post - pre_pre | False | 0.000 [-0.001, 0.001] | 784 | 2169 | 784/784 |
| abstain band (flagged, not strict) | post_post - pre_pre | False | 0.001 [0.000, 0.003] | 3034 | 2169 | 3034/3034 |
| abstain band (flagged, not strict) | pre_post - post_post | False | -0.001 [-0.002, 0.000] | 784 | 3034 | 784/784 |
| abstain band (flagged, not strict) | pre_post - pre_pre | True | 0.000 [-0.002, 0.003] | 430 | 613 | 430/784 |
| abstain band (flagged, not strict) | post_post - pre_pre | True | 0.002 [-0.002, 0.006] | 48 | 500 | 48/3034 |
| abstain band (flagged, not strict) | pre_post - post_post | True | 0.000 [-0.001, 0.002] | 417 | 61 | 417/784 |
| abstract flag (v1 abstract detector) | pre_post - pre_pre | False | 0.013 [-0.000, 0.028] | 607 | 1863 | 784/784 |
| abstract flag (v1 abstract detector) | post_post - pre_pre | False | 0.010 [-0.000, 0.021] | 2581 | 1863 | 3034/3034 |
| abstract flag (v1 abstract detector) | pre_post - post_post | False | 0.002 [-0.014, 0.020] | 607 | 2581 | 784/784 |
| abstract flag (v1 abstract detector) | pre_post - pre_pre | True | 0.016 [0.001, 0.038] | 342 | 531 | 430/784 |
| abstract flag (v1 abstract detector) | post_post - pre_pre | True | -0.001 [-0.081, 0.078] | 37 | 456 | 48/3034 |
| abstract flag (v1 abstract detector) | pre_post - post_post | True | -0.005 [-0.046, 0.024] | 332 | 49 | 417/784 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - pre_pre | False | n/a | 0 | 0 | 784/784 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | post_post - pre_pre | False | n/a | 0 | 0 | 3034/3034 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - post_post | False | n/a | 0 | 0 | 784/784 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - pre_pre | True | n/a | 0 | 0 | 430/784 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | post_post - pre_pre | True | n/a | 0 | 0 | 48/3034 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - post_post | True | n/a | 0 | 0 | 417/784 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - pre_pre | False | 0.141 [-0.774, 1.134] | 616 | 1889 | 784/784 |
| Kobak style words per 1,000 tokens (abstract) | post_post - pre_pre | False | 0.721 [0.045, 1.329] | 2625 | 1889 | 3034/3034 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - post_post | False | -0.579 [-1.456, 0.332] | 616 | 2625 | 784/784 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - pre_pre | True | 1.144 [-1.008, 3.450] | 348 | 536 | 430/784 |
| Kobak style words per 1,000 tokens (abstract) | post_post - pre_pre | True | -2.572 [-7.727, 2.284] | 41 | 460 | 48/3034 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - post_post | True | 0.183 [-3.218, 3.301] | 339 | 53 | 417/784 |

### Regression, kind S

Change = cell dummies (pre_pre is the base) + controls: school FE, field FE, revision lag (months), log length ratio, v1 level; clustered by first lab.

| outcome | term | cells | school_fe | school_field_fe | start_level |
|---|---|---|---|---|---|
| Kobak style words per 1,000 tokens (abstract) | post_post | 0.721 [0.058, 1.383] | 0.831 [0.150, 1.512] | 0.852 [0.167, 1.537] | 0.849 [0.164, 1.534] |
| Kobak style words per 1,000 tokens (abstract) | pre_post | 0.141 [-0.862, 1.145] | -0.396 [-1.621, 0.829] | -0.411 [-1.642, 0.820] | -0.411 [-1.642, 0.819] |
| flagged-passage share (ai_share) | post_post | 0.001 [-0.001, 0.003] | 0.001 [-0.001, 0.003] | 0.001 [-0.001, 0.003] | 0.004 [0.003, 0.006] |
| flagged-passage share (ai_share) | pre_post | 0.001 [-0.001, 0.002] | -0.000 [-0.002, 0.002] | 0.000 [-0.002, 0.002] | 0.000 [-0.001, 0.002] |
| strict share (p >= 0.5) | post_post | -0.001 [-0.002, 0.001] | -0.000 [-0.002, 0.001] | -0.000 [-0.002, 0.001] | 0.002 [0.001, 0.003] |
| strict share (p >= 0.5) | pre_post | 0.000 [-0.000, 0.001] | -0.000 [-0.001, 0.001] | -0.000 [-0.001, 0.001] | 0.000 [-0.001, 0.001] |

### Pairs where AI looks added, kind S

| rule | post_post | pre_post | pre_pre |
|---|---|---|---|
| final>=25% flagged, v1<5% | 0.1 [0.0, 0.1] | 0.1 [0.0, 0.4] | 0.0 [0.0, 0.1] |
| final>=25% strict, v1<5% strict | 0.1 [0.0, 0.2] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.1] |

(per cent of pairs; the `pre_pre` share is the false-positive floor of the rule.)

### Mean change in flagged share by year of v1 (rows) and year of the later text (columns), kind S, cells with >= 20 pairs

| y1 | 2016.0 | 2017.0 | 2018.0 | 2019.0 | 2020.0 | 2021.0 | 2022.0 | 2023.0 | 2024.0 | 2025.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016.0 | -0.001 | 0.001 |  |  |  |  |  |  |  |  |
| 2017.0 |  | 0.002 | -0.001 |  |  |  |  |  |  |  |
| 2018.0 |  |  | 0.001 | 0.0 |  |  |  |  |  |  |
| 2019.0 |  |  |  | 0.0 | 0.001 |  |  |  |  |  |
| 2020.0 |  |  |  |  | 0.0 | -0.001 | -0.003 | -0.002 |  |  |
| 2021.0 |  |  |  |  |  | 0.0 | -0.0 | 0.0 | 0.0 |  |
| 2022.0 |  |  |  |  |  |  | 0.002 | 0.001 | 0.005 | -0.001 |
| 2023.0 |  |  |  |  |  |  |  | 0.002 | 0.003 | 0.005 |
| 2024.0 |  |  |  |  |  |  |  |  | 0.002 | 0.005 |
| 2025.0 |  |  |  |  |  |  |  |  |  | -0.002 |

## 2A. Change in AI wording, kind A

Mean change (later text minus v1) per cell, with `v1` the mean level in v1; `pre_pre` is the revision-noise and false-positive baseline (both texts predate ChatGPT: any change is revision, extraction and detector noise, since the flagged share of human text is about 1% by design).

| outcome | all | post_post | pre_post | pre_pre |
|---|---|---|---|---|
| Kobak style words per 1,000 tokens (abstract) | 0.095 [-0.146, 0.324] | 0.275 [-0.199, 0.711] | 0.382 [-0.539, 1.384] | -0.069 [-0.338, 0.201] |
| abstain band (flagged, not strict) | 0.000 [-0.000, 0.001] | 0.001 [-0.001, 0.003] | 0.001 [-0.001, 0.002] | -0.000 [-0.000, 0.000] |
| abstract flag (v1 abstract detector) | 0.004 [-0.000, 0.008] | 0.011 [0.001, 0.022] | 0.003 [-0.005, 0.012] | -0.000 [-0.004, 0.003] |
| flagged-passage share (ai_share) | 0.000 [-0.001, 0.001] | -0.000 [-0.003, 0.003] | 0.003 [0.001, 0.006] | -0.000 [-0.001, 0.000] |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | n/a | n/a | n/a | n/a |
| strict share (p >= 0.5) | -0.000 [-0.001, 0.001] | -0.001 [-0.003, 0.001] | 0.002 [0.001, 0.004] | -0.000 [-0.000, 0.000] |

Pairs and mean v1 level by cell (flagged share):

| cell | n | v1 |
|---|---|---|
| post_post | 2138 | 0.123 |
| pre_post | 444 | 0.004 |
| pre_pre | 3055 | 0.003 |
| all | 5637 | 0.048 |

### Contrasts, kind A

Difference between cells in the mean change. `matched`: control pairs reweighted to the treated pairs' school x v1-year bin x revision-lag bin distribution (coarsened exact; strata without control are dropped, `kept` = treated pairs retained).

| outcome | contrast | matched | diff (95% CI) | n_treat | n_ctrl | kept |
|---|---|---|---|---|---|---|
| flagged-passage share (ai_share) | pre_post - pre_pre | False | 0.003 [0.001, 0.006] | 444 | 3055 | 444/444 |
| flagged-passage share (ai_share) | post_post - pre_pre | False | 0.000 [-0.002, 0.002] | 2138 | 3055 | 2138/2138 |
| flagged-passage share (ai_share) | pre_post - post_post | False | 0.003 [-0.000, 0.007] | 444 | 2138 | 444/444 |
| flagged-passage share (ai_share) | pre_post - pre_pre | True | 0.001 [-0.001, 0.003] | 300 | 484 | 300/444 |
| flagged-passage share (ai_share) | post_post - pre_pre | True | 0.003 [-0.001, 0.007] | 53 | 283 | 53/2138 |
| flagged-passage share (ai_share) | pre_post - post_post | True | -0.000 [-0.007, 0.006] | 244 | 63 | 244/444 |
| strict share (p >= 0.5) | pre_post - pre_pre | False | 0.002 [0.001, 0.004] | 444 | 3055 | 444/444 |
| strict share (p >= 0.5) | post_post - pre_pre | False | -0.001 [-0.003, 0.001] | 2138 | 3055 | 2138/2138 |
| strict share (p >= 0.5) | pre_post - post_post | False | 0.003 [0.001, 0.006] | 444 | 2138 | 444/444 |
| strict share (p >= 0.5) | pre_post - pre_pre | True | 0.001 [-0.000, 0.002] | 300 | 484 | 300/444 |
| strict share (p >= 0.5) | post_post - pre_pre | True | 0.002 [-0.000, 0.005] | 53 | 283 | 53/2138 |
| strict share (p >= 0.5) | pre_post - post_post | True | -0.001 [-0.005, 0.002] | 244 | 63 | 244/444 |
| abstain band (flagged, not strict) | pre_post - pre_pre | False | 0.001 [-0.000, 0.002] | 444 | 3055 | 444/444 |
| abstain band (flagged, not strict) | post_post - pre_pre | False | 0.001 [-0.001, 0.003] | 2138 | 3055 | 2138/2138 |
| abstain band (flagged, not strict) | pre_post - post_post | False | -0.000 [-0.003, 0.002] | 444 | 2138 | 444/444 |
| abstain band (flagged, not strict) | pre_post - pre_pre | True | 0.000 [-0.002, 0.003] | 300 | 484 | 300/444 |
| abstain band (flagged, not strict) | post_post - pre_pre | True | 0.001 [-0.002, 0.003] | 53 | 283 | 53/2138 |
| abstain band (flagged, not strict) | pre_post - post_post | True | 0.000 [-0.004, 0.005] | 244 | 63 | 244/444 |
| abstract flag (v1 abstract detector) | pre_post - pre_pre | False | 0.003 [-0.006, 0.012] | 400 | 2832 | 444/444 |
| abstract flag (v1 abstract detector) | post_post - pre_pre | False | 0.011 [0.000, 0.022] | 1949 | 2832 | 2138/2138 |
| abstract flag (v1 abstract detector) | pre_post - post_post | False | -0.008 [-0.020, 0.003] | 400 | 1949 | 444/444 |
| abstract flag (v1 abstract detector) | pre_post - pre_pre | True | -0.002 [-0.005, 0.000] | 273 | 444 | 300/444 |
| abstract flag (v1 abstract detector) | post_post - pre_pre | True | 0.015 [-0.012, 0.063] | 47 | 267 | 53/2138 |
| abstract flag (v1 abstract detector) | pre_post - post_post | True | -0.024 [-0.086, 0.013] | 228 | 56 | 244/444 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - pre_pre | False | n/a | 0 | 0 | 444/444 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | post_post - pre_pre | False | n/a | 0 | 0 | 2138/2138 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - post_post | False | n/a | 0 | 0 | 444/444 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - pre_pre | True | n/a | 0 | 0 | 300/444 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | post_post - pre_pre | True | n/a | 0 | 0 | 53/2138 |
| mean P(AI) of the abstract (detector, uncalibrated for abstracts) | pre_post - post_post | True | n/a | 0 | 0 | 244/444 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - pre_pre | False | 0.451 [-0.496, 1.458] | 400 | 2832 | 444/444 |
| Kobak style words per 1,000 tokens (abstract) | post_post - pre_pre | False | 0.344 [-0.188, 0.864] | 1949 | 2832 | 2138/2138 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - post_post | False | 0.107 [-0.883, 1.176] | 400 | 1949 | 444/444 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - pre_pre | True | 0.463 [-1.326, 2.261] | 273 | 444 | 300/444 |
| Kobak style words per 1,000 tokens (abstract) | post_post - pre_pre | True | 1.960 [-0.374, 4.198] | 47 | 267 | 53/2138 |
| Kobak style words per 1,000 tokens (abstract) | pre_post - post_post | True | -0.993 [-4.443, 2.422] | 228 | 56 | 244/444 |

### Regression, kind A

Change = cell dummies (pre_pre is the base) + controls: school FE, field FE, revision lag (months), log length ratio, v1 level; clustered by first lab.

| outcome | term | cells | school_fe | school_field_fe | start_level |
|---|---|---|---|---|---|
| Kobak style words per 1,000 tokens (abstract) | post_post | 0.344 [-0.182, 0.869] | 0.428 [-0.105, 0.962] | 0.414 [-0.124, 0.951] | 0.647 [0.077, 1.217] |
| Kobak style words per 1,000 tokens (abstract) | pre_post | 0.451 [-0.532, 1.433] | 0.516 [-0.523, 1.554] | 0.505 [-0.544, 1.553] | 0.513 [-0.536, 1.561] |
| flagged-passage share (ai_share) | post_post | 0.000 [-0.003, 0.003] | 0.001 [-0.002, 0.003] | 0.001 [-0.002, 0.003] | 0.010 [0.008, 0.012] |
| flagged-passage share (ai_share) | pre_post | 0.003 [0.001, 0.005] | 0.003 [0.000, 0.005] | 0.003 [0.000, 0.005] | 0.003 [0.001, 0.005] |
| strict share (p >= 0.5) | post_post | -0.001 [-0.003, 0.001] | -0.001 [-0.003, 0.001] | -0.001 [-0.003, 0.001] | 0.006 [0.004, 0.008] |
| strict share (p >= 0.5) | pre_post | 0.002 [0.001, 0.004] | 0.002 [0.000, 0.004] | 0.002 [0.001, 0.004] | 0.003 [0.001, 0.004] |

### Pairs where AI looks added, kind A

| rule | post_post | pre_post | pre_pre |
|---|---|---|---|
| final>=25% flagged, v1<5% | 0.1 [0.0, 0.2] | 0.2 [0.0, 0.9] | 0.0 [0.0, 0.0] |
| final>=25% strict, v1<5% strict | 0.1 [0.0, 0.3] | 0.2 [0.0, 0.9] | 0.0 [0.0, 0.0] |

(per cent of pairs; the `pre_pre` share is the false-positive floor of the rule.)

### Mean change in flagged share by year of v1 (rows) and year of the later text (columns), kind A, cells with >= 20 pairs

| y1 | 2016.0 | 2017.0 | 2018.0 | 2019.0 | 2020.0 | 2021.0 | 2022.0 | 2023.0 | 2024.0 | 2025.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2015.0 | -0.001 | -0.003 |  |  |  |  |  |  |  |  |
| 2016.0 | 0.0 | 0.002 |  |  |  |  |  |  |  |  |
| 2017.0 |  | 0.001 | -0.001 | 0.0 |  |  |  |  |  |  |
| 2018.0 |  |  | 0.0 | -0.001 | -0.001 |  |  |  |  |  |
| 2019.0 |  |  |  | 0.0 | -0.001 | -0.001 |  |  |  |  |
| 2020.0 |  |  |  |  | 0.0 | -0.0 | 0.001 | -0.002 |  |  |
| 2021.0 |  |  |  |  |  | -0.001 | -0.001 | 0.006 |  |  |
| 2022.0 |  |  |  |  |  |  | -0.0 | 0.002 | 0.01 |  |
| 2023.0 |  |  |  |  |  |  |  | 0.005 | 0.001 | -0.001 |
| 2024.0 |  |  |  |  |  |  |  |  | -0.004 | 0.007 |
| 2025.0 |  |  |  |  |  |  |  |  |  | -0.007 |

## 3. Reading and limits

- A positive `pre_post - pre_pre` difference is the extra rise in flagged wording between v1 and a later text when the later text was written in the ChatGPT era, over the rise that revision alone gives. For kind S the later text is the stored (usually published) version, whose extraction differs from the arXiv PDF's; `pre_pre` carries the same mismatch, so the contrast removes it to first order.
- v1 of a post-2022 paper may already contain AI wording, so `post_post` changes understate use; `pre_post` begins from human v1 texts and is the cleaner contrast, but its pairs sit mostly in 2022-2023 (the earliest months of use), where the flagged-share rise is small.
- The passage detector flags about 0.3% of human passages by design; with roughly 60 passages per paper a single paper's change is noisy, so conclusions rest on cell means and the share of pairs, not on single papers.
- Kobak style words in abstracts are detector-free; for kind S the later abstract is OpenAlex's (the published abstract), for A the arXiv PDF's, extracted by a heading rule (`Abstract` ... `Introduction`).
