# AI-written text and lab research diversity: the v2 diversity battery

Generated 2026-10-28 by `diversity/report.py` from the files in `diversity/`; rerun everything with `diversity/run_all.sh`. AI-usage variable in this run: **paragraph** detector.

## Summary

Rule-based from the tables below, so it stays true on a rerun.
- "Clears placebo": the main CI excludes zero, |β| exceeds 95% of all placebo slopes, and the CI also excludes the mean of the measure's own two placebo slopes.
- β is SD of change per SD of lab AI usage, with lab-size and school controls.

- **Semantic, title + abstract:** 4 of 9 measures have a CI including zero; clears placebo: N1 distance to field -0.27 (own placebo -0.19; with topic control -0.15); CI excludes zero but the slope does not meet the placebo rule (inside the ±0.15 band or not clear of its own placebo): S3 pairwise distance +0.07 (own placebo +0.03), S5 topic entropy +0.10 (own placebo +0.01), S6 effective topics +0.10 (own placebo +0.01), N2 new topics +0.11 (own placebo -0.01).
- **Semantic, full text:** 4 of 8 measures have a CI including zero; CI excludes zero but the slope does not meet the placebo rule (inside the ±0.15 band or not clear of its own placebo): S1 knowledge extent +0.13 (own placebo +0.03), S2 dispersion +0.10 (own placebo +0.05), S3 pairwise distance +0.11 (own placebo +0.05), S4 Vendi score +0.07 (own placebo +0.03).
- **Lexical and stylistic, full text:** 3 of 10 measures have a CI including zero; clears placebo: L1 MATTR +0.41 (own placebo +0.01; with topic control +0.34), L2 unigram entropy +0.40 (own placebo +0.02; with topic control +0.33), L5 sentence length, SD -0.16 (own placebo -0.02; with topic control -0.17), L7 LLM-marker words +0.71 (own placebo +0.11; with topic control +0.68), Flesch reading ease (mean) -0.46 (own placebo -0.09; with topic control -0.41); CI excludes zero but the slope does not meet the placebo rule (inside the ±0.15 band or not clear of its own placebo): L4 trigram novelty +0.06 (own placebo +0.00), L6 readability spread +0.14 (own placebo -0.02).
- **Citations:** 2 of 4 measures have a CI including zero; clears placebo: C4 self-lab references -0.15 (own placebo -0.05; with topic control -0.08); CI excludes zero but the slope does not meet the placebo rule (inside the ±0.15 band or not clear of its own placebo): C3 reference-age spread -0.17 (own placebo -0.13).
- **Within lab, flagged vs unflagged papers of the same lab and year (2023-2026), CI excluding zero:** N1 distance to field -0.15; L1 MATTR +0.36 (2016-2022 false positives show it too: +0.65); L4 trigram novelty +0.15 (2016-2022 false positives show it too: +0.81); S8 within-paper spread -0.15; L7 LLM-marker words +1.09.

## What was measured

- **Papers:** 95,099 CS lab papers of 2016-2026 (`papers.jsonl.gz`, six schools).
  - 77,184 have a SPECTER2 title+abstract vector.
  - 54,692 have a usable full text (≥ 1,000 body words; a PDF must show its title on page 1).
  - 54,686 have a full-text vector.
  - 28,507 have an S2 reference list with ≥ 5 references.
  - 54,686 have an AI score.
- **Labs:** a lab is a school PI. 1016 labs have ≥ 5 papers in both 2016-2022 and 2023-2026. 861 of them also have ≥ 5 AI-scored post-period papers and enter the lab-level analyses (CMU 266, Stanford 154, MIT 130, Berkeley 118, EPFL 113, Princeton 80).
- **AI usage per lab:** the mean paragraph ai_share of the lab's 2023-2026 papers (v2 paragraph detector). Across labs: median 7%, interquartile range 4-12%, 10th-90th percentile 2-17%.
- **Flagged share by year:** 2016 0.1%, 2017 0.1%, 2018 0.2%, 2019 0.0%, 2020 0.2%, 2021 0.2%, 2022 0.3%, 2023 3.1%, 2024 11.1%, 2025 24.3%, 2026 17.6%.
- **Behind the lab-level fits:** semantic, title + abstract: up to 846 labs, 63,200 distinct papers; semantic, full text: up to 821 labs, 48,534 distinct papers; lexical and stylistic, full text: up to 821 labs, 48,539 distinct papers; citations: up to 494 labs, 25,373 distinct papers.

### Full-text coverage

| School | papers | full text | full-text vector | S2 references |
|---|---:|---:|---:|---:|
| Princeton | 8,314 | 5,600 (67%) | 5,598 | 2,813 (34%) |
| CMU | 24,717 | 16,180 (65%) | 16,179 | 11,900 (48%) |
| EPFL | 12,554 | 7,918 (63%) | 7,915 | 4,970 (40%) |
| MIT | 19,099 | 8,711 (46%) | 8,711 | 6,688 (35%) |
| Berkeley | 13,106 | 7,171 (55%) | 7,171 | 1,129 (9%) |
| Stanford | 17,309 | 9,112 (53%) | 9,112 | 1,007 (6%) |
| 2016-2022 | 57,515 | 30,417 (53%) | 30,412 | |
| 2023-2026 | 37,584 | 24,275 (65%) | 24,274 | |

- **Full-text segments:** 54,686 papers by passages.
  - `fulltext.sqlite` stores whitespace-flattened bodies, so its `paragraphs` table holds almost nothing. A paper uses the table when it has ≥ 3 paragraphs there.
  - Otherwise the body is cut into sentence-bounded passages of about 150 words (40-400 words), with the 70% printable-word filter, at most 100 per paper.
  - Embedding: SPECTER2 base, CLS, ≤ 512 tokens. A paper's vector is the mean of its segment vectors.

### Measures

Every set-level measure is a mean over 1,000 equal-size random draws of the lab's papers. n is the smaller of the two groups compared, at least 5, so size alone cannot make a lab look more diverse. Lab-years use n = 5.

Paper-level measures are means over the group's papers. Embedding vectors have the corpus mean subtracted and are then L2-normalized, because SPECTER2 puts random CS papers at cosine ~0.8.

| Measure | Definition | Level | Input |
|---|---|---|---|
| S1 | knowledge extent: largest distance of a paper from the set centroid (Hao et al. M8) | set | abstract, full text |
| S2 | dispersion: mean distance from the centroid | set | abstract, full text |
| S3 | mean pairwise cosine distance | set | abstract, full text |
| S4 | Vendi score: exp(entropy of the eigenvalues of K/n), K the cosine-similarity matrix | set | abstract, full text |
| S5 / S6 | entropy over 50 global k-means topic clusters / its exponential | set | abstract, full text |
| S7 | Rao-Stirling: Σ_{a≠b} d_ab p_a p_b, d = cosine distance between cluster centroids | set | abstract, full text |
| S8 | within-paper spread: mean pairwise cosine distance between a paper's segment vectors (≥ 5 segments) | paper | full text |
| L1 | MATTR, 1,000-token moving window | paper | full text |
| L2 | unigram entropy, mean over consecutive 1,000-token windows | paper | full text |
| L3 | homogeneity: mean pairwise TF-IDF cosine (higher = more alike) | set | full text, first 5,000 tokens |
| L4 | trigram novelty: share of a paper's distinct trigrams absent from 3 of the lab's papers of the 3 previous years (10 draws) | paper | full text, 2019+ |
| L5 | sentence length (words), mean and SD within the paper | paper | full text |
| L6 | readability spread: SD of the papers' Flesch reading ease | set | full text |
| L7 | Kobak et al. rare excess style words per 1,000 tokens (detector check, not diversity) | paper | full text |
| L8 | compression: zlib(concatenated 4,000-character excerpts) / Σ zlib(each); 1 = nothing shared | set | full text |
| N1 | cosine distance to the nearest arXiv CS paper of the previous year (10,000-paper background sample per year) | paper | abstract |
| N2 | new topic: the paper's cluster is absent from 3 of the lab's papers of the 3 previous years (10 draws) | paper | abstract, 2019+ |
| C1 | venue entropy of 40 references drawn from the set's pooled references | set | S2 references |
| C2 | mean pairwise Jaccard overlap of reference lists (higher = more alike) | set | S2 references |
| C3 | SD of reference ages, pooled over the set | set | S2 references |
| C4 | share of a paper's references that are the lab's own papers | paper | S2 references |

## Results

### 1. Lab level: change against AI usage

- **Model:** y = post − pre change in the measure; x = post-period AI usage.
  - Both are z-scored over the labs in the fit, so β is SD of change per SD of AI usage.
  - Huber regression with controls for log n of the family's papers in each period and school dummies.
- **Uncertainty:** 95% percentile-bootstrap CI over labs; p_perm permutes AI usage within school.
- **Placebo null:** 95% of placebo |β| fall below ±0.15. This band is the null spread (analysis 3).

| Family | Measure | β main [95% CI] | p_perm | labs | β + topic FE | β + baseline | placebo 2019 | placebo 2020 | β − own placebo | clears placebo |
|---|---|---|---:|---:|---|---|---|---|---:|:-:|
| Semantic | S1 knowledge extent | +0.02 [-0.04, +0.10] | 0.453 | 846 | +0.03 [-0.04, +0.11] | +0.06 [+0.01, +0.12] | +0.06 [-0.03, +0.15] | -0.01 [-0.09, +0.07] | -0.00 |  |
| Semantic | S2 dispersion | +0.07 [-0.00, +0.15] | 0.029 | 846 | +0.10 [+0.01, +0.18] | +0.08 [+0.02, +0.15] | +0.05 [-0.03, +0.13] | +0.03 [-0.05, +0.11] | +0.03 |  |
| Semantic | S3 pairwise distance | +0.07 [+0.00, +0.15] | 0.020 | 846 | +0.10 [+0.01, +0.19] | +0.09 [+0.02, +0.16] | +0.05 [-0.03, +0.12] | +0.02 [-0.06, +0.10] | +0.04 |  |
| Semantic | S4 Vendi score | +0.02 [-0.03, +0.08] | 0.492 | 846 | +0.04 [-0.02, +0.12] | +0.01 [-0.04, +0.06] | +0.02 [-0.04, +0.09] | -0.00 [-0.06, +0.06] | +0.01 |  |
| Semantic | S5 topic entropy | +0.10 [+0.02, +0.18] | 0.005 | 846 | +0.12 [+0.03, +0.21] | +0.13 [+0.06, +0.20] | +0.03 [-0.06, +0.11] | -0.02 [-0.10, +0.06] | +0.09 |  |
| Semantic | S6 effective topics | +0.10 [+0.02, +0.17] | 0.001 | 846 | +0.13 [+0.03, +0.21] | +0.12 [+0.05, +0.19] | +0.02 [-0.06, +0.09] | -0.01 [-0.08, +0.05] | +0.09 |  |
| Semantic | S7 Rao-Stirling | +0.03 [-0.04, +0.11] | 0.318 | 846 | +0.07 [-0.01, +0.15] | +0.08 [+0.01, +0.15] | +0.01 [-0.08, +0.10] | -0.04 [-0.13, +0.03] | +0.05 |  |
| Semantic | N1 distance to field | -0.27 [-0.36, -0.20] | 0.001 | 846 | -0.15 [-0.24, -0.08] | -0.28 [-0.36, -0.20] | -0.20 [-0.27, -0.11] | -0.18 [-0.28, -0.09] | -0.08 | ✓ |
| Semantic | N2 new topics | +0.11 [+0.02, +0.19] | 0.002 | 820 | +0.10 [+0.00, +0.18] | +0.14 [+0.07, +0.20] | n/a | -0.01 [-0.09, +0.07] | +0.12 |  |
| Semantic (ft) | S1 knowledge extent | +0.13 [+0.06, +0.20] | 0.001 | 821 | +0.14 [+0.06, +0.22] | +0.16 [+0.10, +0.22] | +0.04 [-0.04, +0.12] | +0.02 [-0.06, +0.09] | +0.10 |  |
| Semantic (ft) | S2 dispersion | +0.10 [+0.03, +0.17] | 0.001 | 821 | +0.12 [+0.04, +0.20] | +0.15 [+0.08, +0.22] | +0.07 [-0.01, +0.16] | +0.03 [-0.06, +0.12] | +0.05 |  |
| Semantic (ft) | S3 pairwise distance | +0.11 [+0.04, +0.17] | 0.003 | 821 | +0.12 [+0.05, +0.20] | +0.16 [+0.09, +0.23] | +0.08 [-0.01, +0.16] | +0.03 [-0.06, +0.11] | +0.06 |  |
| Semantic (ft) | S4 Vendi score | +0.07 [+0.01, +0.13] | 0.032 | 821 | +0.08 [+0.01, +0.15] | +0.09 [+0.03, +0.14] | +0.06 [-0.01, +0.13] | +0.01 [-0.06, +0.07] | +0.04 |  |
| Semantic (ft) | S5 topic entropy | +0.04 [-0.05, +0.12] | 0.242 | 821 | +0.03 [-0.06, +0.13] | +0.07 [-0.01, +0.15] | +0.08 [-0.00, +0.17] | +0.02 [-0.09, +0.11] | -0.01 |  |
| Semantic (ft) | S6 effective topics | +0.02 [-0.05, +0.09] | 0.464 | 821 | +0.01 [-0.07, +0.10] | +0.04 [-0.03, +0.11] | +0.06 [-0.00, +0.13] | +0.02 [-0.06, +0.09] | -0.02 |  |
| Semantic (ft) | S7 Rao-Stirling | +0.04 [-0.04, +0.12] | 0.212 | 821 | +0.05 [-0.05, +0.14] | +0.08 [+0.01, +0.17] | +0.06 [-0.03, +0.15] | +0.00 [-0.10, +0.10] | +0.01 |  |
| Semantic (ft) | S8 within-paper spread | -0.00 [-0.08, +0.07] | 0.920 | 821 | -0.06 [-0.13, +0.02] | -0.05 [-0.13, +0.02] | -0.16 [-0.24, -0.07] | -0.09 [-0.18, +0.00] | +0.12 |  |
| Lexical and stylistic | L1 MATTR | +0.41 [+0.34, +0.47] | 0.001 | 821 | +0.34 [+0.27, +0.41] | +0.47 [+0.41, +0.54] | +0.03 [-0.06, +0.12] | -0.02 [-0.11, +0.06] | +0.40 | ✓ |
| Lexical and stylistic | L2 unigram entropy | +0.40 [+0.33, +0.46] | 0.001 | 821 | +0.33 [+0.27, +0.40] | +0.44 [+0.39, +0.51] | +0.04 [-0.04, +0.13] | -0.00 [-0.09, +0.08] | +0.38 | ✓ |
| Lexical and stylistic | L3 TF-IDF homogeneity | -0.03 [-0.09, +0.05] | 0.335 | 821 | -0.03 [-0.10, +0.05] | -0.10 [-0.17, -0.03] | -0.11 [-0.18, -0.03] | -0.07 [-0.14, -0.00] | +0.06 |  |
| Lexical and stylistic | L4 trigram novelty | +0.06 [+0.03, +0.10] | 0.001 | 778 | +0.07 [+0.03, +0.11] | +0.15 [+0.11, +0.20] | n/a | +0.00 [-0.04, +0.05] | +0.06 |  |
| Lexical and stylistic | L5 sentence length, mean | -0.02 [-0.10, +0.06] | 0.582 | 821 | +0.02 [-0.06, +0.11] | -0.12 [-0.19, -0.05] | -0.03 [-0.12, +0.07] | +0.04 [-0.04, +0.13] | -0.02 |  |
| Lexical and stylistic | L5 sentence length, SD | -0.16 [-0.25, -0.08] | 0.001 | 821 | -0.17 [-0.26, -0.08] | -0.29 [-0.35, -0.22] | -0.05 [-0.15, +0.04] | +0.01 [-0.07, +0.10] | -0.14 | ✓ |
| Lexical and stylistic | L6 readability spread | +0.14 [+0.07, +0.22] | 0.001 | 821 | +0.18 [+0.09, +0.26] | +0.12 [+0.05, +0.18] | -0.02 [-0.09, +0.05] | -0.01 [-0.08, +0.06] | +0.16 |  |
| Lexical and stylistic | L7 LLM-marker words | +0.71 [+0.66, +0.76] | 0.001 | 821 | +0.68 [+0.62, +0.73] | +0.72 [+0.67, +0.78] | +0.10 [+0.04, +0.18] | +0.11 [+0.04, +0.19] | +0.60 | ✓ |
| Lexical and stylistic | L8 compression ratio | -0.03 [-0.08, +0.04] | 0.354 | 821 | -0.04 [-0.11, +0.02] | +0.02 [-0.04, +0.08] | +0.09 [+0.01, +0.17] | +0.11 [+0.03, +0.19] | -0.12 |  |
| Lexical and stylistic | Flesch reading ease (mean) | -0.46 [-0.51, -0.40] | 0.001 | 821 | -0.41 [-0.47, -0.34] | -0.53 [-0.60, -0.48] | -0.08 [-0.19, +0.01] | -0.11 [-0.20, -0.01] | -0.36 | ✓ |
| Citations | C1 venue entropy | +0.01 [-0.08, +0.08] | 0.877 | 494 | +0.03 [-0.06, +0.11] | +0.05 [-0.03, +0.13] | -0.05 [-0.18, +0.08] | +0.04 [-0.09, +0.16] | +0.02 |  |
| Citations | C2 reference overlap | +0.00 [-0.05, +0.06] | 0.888 | 494 | -0.02 [-0.08, +0.04] | -0.04 [-0.08, -0.00] | +0.08 [-0.03, +0.18] | +0.01 [-0.07, +0.08] | -0.04 |  |
| Citations | C3 reference-age spread | -0.17 [-0.27, -0.08] | 0.001 | 494 | -0.11 [-0.22, -0.00] | -0.24 [-0.33, -0.13] | -0.12 [-0.24, +0.01] | -0.15 [-0.28, -0.02] | -0.04 |  |
| Citations | C4 self-lab references | -0.15 [-0.24, -0.07] | 0.001 | 494 | -0.08 [-0.16, +0.01] | -0.16 [-0.24, -0.07] | -0.06 [-0.18, +0.06] | -0.04 [-0.15, +0.06] | -0.10 | ✓ |

**Reading:**
- **CI excludes zero:** 18 of 31 measures: S3 pairwise distance (+0.07), S5 topic entropy (+0.10), S6 effective topics (+0.10), N1 distance to field (-0.27), N2 new topics (+0.11), S1 knowledge extent (+0.13), S2 dispersion (+0.10), S3 pairwise distance (+0.11), S4 Vendi score (+0.07), L1 MATTR (+0.41), L2 unigram entropy (+0.40), L4 trigram novelty (+0.06), L5 sentence length, SD (-0.16), L6 readability spread (+0.14), L7 LLM-marker words (+0.71), Flesch reading ease (mean) (-0.46), C3 reference-age spread (-0.17), C4 self-lab references (-0.15).
- **Clear the placebo** (|β| above the band and the CI excludes the measure's own placebo mean): N1 distance to field, L1 MATTR, L2 unigram entropy, L5 sentence length, SD, L7 LLM-marker words, Flesch reading ease (mean), C4 self-lab references.
- **Do not clear it:** S3 pairwise distance, S5 topic entropy, S6 effective topics, N2 new topics, S1 knowledge extent, S2 dispersion, S3 pairwise distance, S4 Vendi score, L4 trigram novelty, L6 readability spread, C3 reference-age spread. A pre-ChatGPT break produces slopes like these with the same AI variable, so they are not evidence of an AI effect.
- **Semantic, title + abstract:** 4 of 9 measures have a CI that includes zero.
- **Semantic, full text:** 4 of 8 measures have a CI that includes zero.
- **Lexical and stylistic, full text:** 3 of 10 measures have a CI that includes zero.
- **Citations:** 2 of 4 measures have a CI that includes zero.

### 3. Placebo breaks

- **Spread:** 60 placebo slopes (fake breaks at 2019 and 2020, same x and controls) have SD 0.07, and 95% of their |β| are below 0.15.
- **Placebo CIs excluding zero:** N1 distance to field 2019 (-0.20), S8 within-paper spread 2019 (-0.16), L3 TF-IDF homogeneity 2019 (-0.11), L7 LLM-marker words 2019 (+0.10), L8 compression ratio 2019 (+0.09), N1 distance to field 2020 (-0.18), L3 TF-IDF homogeneity 2020 (-0.07), L7 LLM-marker words 2020 (+0.11), L8 compression ratio 2020 (+0.11), Flesch reading ease (mean) 2020 (-0.11), C3 reference-age spread 2020 (-0.15).
  - These labs were already moving in that direction before ChatGPT, in step with their later AI usage.
  - That is a pre-trend, or a property of the labs that later adopt AI, not an effect of AI.
- **Missing values:** L4 and N2 start in 2019, so the 2019 placebo has no early group for them.

### 2. Within lab: papers with more vs less AI in the same lab and year

- **Model:** outcome z-scored; regressed on the paper's flag with lab × year fixed effects.
  - A paper of k labs counts 1/k in each; SE clustered by lab.
- **Pre-period placebo:** compares flagged with unflagged papers of 2016-2022, where every flag is a detector false positive. It shows what the detector's errors alone produce.

| Outcome | 2023-2026 | + topic FE | 2016-2022 placebo | papers (post) | flagged (post) | labs |
|---|---|---|---|---:|---:|---:|
| distance to lab centroid (abstract) | -0.02 [-0.06, +0.02] | -0.03 [-0.06, +0.01] | +0.33 [-0.11, +0.76] | 12230 | 2893 | 678 |
| distance to lab centroid (full text) | +0.03 [-0.01, +0.06] | +0.03 [-0.01, +0.06] | +0.49 [+0.15, +0.83] | 14345 | 3289 | 704 |
| N1 distance to field | -0.15 [-0.20, -0.11] | -0.13 [-0.16, -0.09] | -0.10 [-0.37, +0.18] | 12232 | 2894 | 679 |
| L1 MATTR | +0.36 [+0.32, +0.41] | +0.35 [+0.30, +0.39] | +0.65 [+0.27, +1.03] | 14341 | 3289 | 707 |
| L4 trigram novelty | +0.15 [+0.11, +0.19] | +0.15 [+0.11, +0.19] | +0.81 [+0.33, +1.29] | 14006 | 3193 | 674 |
| S8 within-paper spread | -0.15 [-0.20, -0.10] | -0.18 [-0.22, -0.13] | -0.10 [-0.46, +0.27] | 14321 | 3287 | 705 |
| N2 new topics | +0.03 [-0.01, +0.08] | +0.01 [-0.03, +0.04] | +0.24 [-0.26, +0.73] | 11980 | 2825 | 660 |
| L7 LLM-marker words | +1.09 [+1.04, +1.14] | +1.09 [+1.03, +1.14] | -0.17 [-0.60, +0.25] | 14349 | 3291 | 707 |

With the continuous paragraph dose (ai_share) instead of the flag, 2023-2026:

- distance to lab centroid (abstract): -0.01 [-0.13, +0.10]
- distance to lab centroid (full text): +0.11 [+0.00, +0.21]
- N1 distance to field: -0.50 [-0.61, -0.38]
- L1 MATTR: +1.07 [+0.96, +1.19]
- L4 trigram novelty: +0.41 [+0.34, +0.49]
- S8 within-paper spread: -0.34 [-0.46, -0.22]
- N2 new topics: +0.16 [+0.05, +0.28]
- L7 LLM-marker words: +3.70 [+3.56, +3.84]

### 4. Topic control

- **Model:** the topic column of the lab-level table adds two terms.
  - Fixed effects for the lab's modal topic (10 k-means clusters of abstracts).
  - The lab's change in LLM-topic share (the homogenization study's title/abstract pattern).
- Within lab, "+ topic FE" adds the paper's 50-cluster topic and its LLM-topic indicator.
- **Main slopes whose CI excludes zero, before and after the topic control:**
  - S3 pairwise distance: +0.07 → +0.10
  - S5 topic entropy: +0.10 → +0.12
  - S6 effective topics: +0.10 → +0.13
  - N1 distance to field: -0.27 → -0.15
  - N2 new topics: +0.11 → +0.10
  - S1 knowledge extent: +0.13 → +0.14
  - S2 dispersion: +0.10 → +0.12
  - S3 pairwise distance: +0.11 → +0.12
  - S4 Vendi score: +0.07 → +0.08
  - L1 MATTR: +0.41 → +0.34
  - L2 unigram entropy: +0.40 → +0.33
  - L4 trigram novelty: +0.06 → +0.07
  - L5 sentence length, SD: -0.16 → -0.17
  - L6 readability spread: +0.14 → +0.18
  - L7 LLM-marker words: +0.71 → +0.68
  - Flesch reading ease (mean): -0.46 → -0.41
  - C3 reference-age spread: -0.17 → -0.11
  - C4 self-lab references: -0.15 → -0.08

### 5. Per school

Main specification within each school with ≥ 20 labs: β [95% CI].

| Measure | Princeton | CMU | EPFL | MIT | Berkeley | Stanford |
|---|---|---|---|---|---|---|
| S1 knowledge extent | -0.02 [-0.19, +0.25] | +0.05 [-0.06, +0.18] | +0.04 [-0.17, +0.22] | -0.21 [-0.42, +0.00] | +0.09 [-0.11, +0.25] | +0.03 [-0.15, +0.20] |
| S2 dispersion | +0.23 [-0.22, +0.64] | +0.03 [-0.08, +0.13] | +0.07 [-0.10, +0.29] | +0.19 [+0.01, +0.36] * | -0.22 [-0.40, +0.06] | +0.23 [+0.04, +0.39] * |
| S3 pairwise distance | +0.26 [-0.21, +0.63] | +0.04 [-0.07, +0.15] | +0.06 [-0.11, +0.28] | +0.16 [-0.01, +0.33] | -0.19 [-0.38, +0.06] | +0.25 [+0.06, +0.41] * |
| S4 Vendi score | +0.07 [-0.14, +0.32] | -0.02 [-0.12, +0.10] | -0.00 [-0.14, +0.17] | +0.10 [-0.01, +0.25] | -0.12 [-0.24, +0.02] | +0.14 [-0.02, +0.28] |
| S5 topic entropy | +0.16 [-0.12, +0.61] | +0.04 [-0.09, +0.21] | +0.01 [-0.20, +0.21] | +0.11 [-0.06, +0.29] | -0.11 [-0.36, +0.10] | +0.32 [+0.17, +0.47] * |
| S6 effective topics | +0.22 [-0.13, +0.58] | +0.02 [-0.09, +0.15] | +0.06 [-0.14, +0.24] | +0.13 [-0.03, +0.35] | -0.03 [-0.22, +0.10] | +0.30 [+0.16, +0.43] * |
| S7 Rao-Stirling | +0.10 [-0.07, +0.47] | -0.03 [-0.16, +0.12] | -0.05 [-0.22, +0.15] | +0.02 [-0.16, +0.23] | -0.15 [-0.39, +0.02] | +0.27 [+0.12, +0.43] * |
| N1 distance to field | -0.33 [-0.65, +0.02] | -0.47 [-0.59, -0.33] * | -0.20 [-0.43, +0.01] | -0.27 [-0.42, -0.14] * | -0.07 [-0.30, +0.12] | -0.18 [-0.38, +0.04] |
| N2 new topics | +0.31 [-0.29, +0.60] | +0.04 [-0.10, +0.17] | +0.12 [-0.04, +0.28] | +0.19 [-0.09, +0.37] | -0.10 [-0.34, +0.20] | +0.26 [+0.12, +0.42] * |
| S1 knowledge extent (ft) | +0.25 [+0.09, +0.45] * | +0.20 [+0.07, +0.32] * | +0.07 [-0.09, +0.26] | -0.13 [-0.37, +0.12] | +0.20 [-0.00, +0.39] | +0.05 [-0.12, +0.21] |
| S2 dispersion (ft) | +0.38 [+0.16, +0.65] * | +0.08 [-0.05, +0.21] | +0.04 [-0.10, +0.19] | +0.11 [-0.10, +0.30] | +0.07 [-0.10, +0.30] | +0.14 [-0.08, +0.40] |
| S3 pairwise distance (ft) | +0.40 [+0.22, +0.66] * | +0.09 [-0.03, +0.21] | +0.04 [-0.10, +0.19] | +0.09 [-0.15, +0.28] | +0.10 [-0.08, +0.31] | +0.13 [-0.07, +0.38] |
| S4 Vendi score (ft) | +0.22 [+0.09, +0.43] * | +0.05 [-0.08, +0.16] | +0.00 [-0.12, +0.13] | +0.12 [-0.07, +0.33] | +0.05 [-0.12, +0.20] | +0.10 [-0.08, +0.26] |
| S5 topic entropy (ft) | +0.25 [-0.08, +0.52] | +0.04 [-0.11, +0.18] | -0.04 [-0.20, +0.14] | +0.05 [-0.11, +0.21] | -0.04 [-0.33, +0.20] | +0.06 [-0.12, +0.25] |
| S6 effective topics (ft) | +0.22 [-0.04, +0.40] | -0.00 [-0.15, +0.14] | -0.01 [-0.14, +0.14] | +0.06 [-0.09, +0.24] | -0.01 [-0.23, +0.19] | +0.01 [-0.15, +0.17] |
| S7 Rao-Stirling (ft) | +0.30 [+0.10, +0.55] * | +0.03 [-0.11, +0.19] | -0.09 [-0.23, +0.12] | -0.04 [-0.22, +0.17] | +0.01 [-0.22, +0.17] | +0.11 [-0.11, +0.32] |
| S8 within-paper spread (ft) | +0.34 [+0.14, +0.50] * | -0.01 [-0.17, +0.12] | -0.12 [-0.25, +0.01] | -0.07 [-0.24, +0.13] | -0.18 [-0.39, +0.10] | +0.09 [-0.09, +0.28] |
| L1 MATTR | +0.50 [+0.26, +0.65] * | +0.43 [+0.31, +0.54] * | +0.37 [+0.21, +0.53] * | +0.50 [+0.26, +0.69] * | +0.31 [+0.12, +0.48] * | +0.36 [+0.19, +0.52] * |
| L2 unigram entropy | +0.45 [+0.19, +0.61] * | +0.42 [+0.32, +0.52] * | +0.39 [+0.25, +0.54] * | +0.45 [+0.22, +0.65] * | +0.33 [+0.16, +0.51] * | +0.36 [+0.22, +0.51] * |
| L3 TF-IDF homogeneity | -0.30 [-0.57, -0.07] * | +0.03 [-0.07, +0.13] | +0.05 [-0.13, +0.20] | -0.08 [-0.22, +0.12] | -0.05 [-0.28, +0.33] | -0.05 [-0.21, +0.13] |
| L4 trigram novelty | +0.26 [+0.08, +0.51] * | +0.03 [-0.02, +0.09] | +0.12 [+0.03, +0.27] * | +0.02 [-0.08, +0.16] | +0.07 [-0.01, +0.24] | +0.04 [-0.02, +0.13] |
| L5 sentence length, mean | -0.20 [-0.41, -0.02] * | +0.04 [-0.08, +0.15] | -0.06 [-0.22, +0.16] | -0.07 [-0.23, +0.10] | +0.11 [-0.09, +0.25] | -0.13 [-0.33, +0.10] |
| L5 sentence length, SD | -0.34 [-0.56, -0.07] * | -0.10 [-0.25, +0.04] | +0.02 [-0.18, +0.19] | -0.13 [-0.30, +0.07] | -0.25 [-0.40, -0.08] * | -0.36 [-0.53, -0.14] * |
| L6 readability spread | +0.26 [+0.03, +0.51] * | +0.13 [-0.04, +0.26] | +0.16 [-0.02, +0.35] | +0.10 [-0.08, +0.27] | +0.12 [-0.16, +0.43] | +0.13 [-0.02, +0.30] |
| L7 LLM-marker words | +0.58 [+0.41, +0.72] * | +0.79 [+0.72, +0.85] * | +0.65 [+0.55, +0.86] * | +0.73 [+0.58, +0.83] * | +0.69 [+0.54, +0.79] * | +0.63 [+0.52, +0.75] * |
| L8 compression ratio | +0.19 [-0.04, +0.37] | -0.02 [-0.11, +0.08] | -0.20 [-0.35, -0.06] * | +0.00 [-0.16, +0.21] | -0.00 [-0.26, +0.21] | -0.00 [-0.14, +0.15] |
| Flesch reading ease (mean) | -0.25 [-0.63, -0.02] * | -0.56 [-0.64, -0.47] * | -0.48 [-0.63, -0.33] * | -0.45 [-0.60, -0.28] * | -0.40 [-0.59, -0.21] * | -0.39 [-0.52, -0.25] * |
| C1 venue entropy | +0.15 [-0.15, +0.43] | -0.01 [-0.16, +0.12] | +0.05 [-0.17, +0.28] | +0.18 [+0.01, +0.37] * |  | -0.14 [-0.53, +0.31] |
| C2 reference overlap | -0.27 [-0.55, +0.05] | -0.00 [-0.09, +0.08] | +0.02 [-0.11, +0.18] | +0.05 [-0.15, +0.26] |  | -0.02 [-0.65, +0.32] |
| C3 reference-age spread | -0.20 [-0.54, +0.17] | -0.12 [-0.28, +0.04] | -0.28 [-0.46, -0.11] * | -0.11 [-0.38, +0.11] |  | -0.34 [-0.76, +0.28] |
| C4 self-lab references | -0.35 [-0.76, -0.07] * | -0.20 [-0.30, -0.08] * | +0.09 [-0.15, +0.35] | -0.18 [-0.37, -0.02] * |  | -0.13 [-0.91, +0.33] |

\* CI excludes zero. Labs per school: Princeton 78, CMU 265, EPFL 111, MIT 128, Berkeley 115, Stanford 151.

### Figure 3 on full texts

Not drawn in this run: too few full texts have vectors yet (see `diversity/logs/emb-*.out`).

### Detector check (L7)

- **Papers of 2023-2026:** Kobak style words run 9.33 per 1,000 tokens in flagged papers and 4.11 in unflagged ones.
- **Lab level:** the change in L7 rises with AI usage, β = +0.71 [+0.66, +0.76]. The abstract detector and the full-text marker words agree.

## Caveats

- **Detector errors.** The v1 abstract detector reads only the title and abstract and is set to a 1% false-positive rate on held-out pre-ChatGPT abstracts.
  - Its flagged share before ChatGPT is 0.1%, 0.1%, 0.2%, 0.0%, 0.2%, 0.2%, 0.3% (2016-2022).
  - A flag marks AI-like style in the abstract, not AI use in the paper. Lab AI usage is a noisy share of a few papers, which biases slopes toward zero.
  - The 2016-2022 within-lab comparison shows what the detector's false positives alone look like. Where those papers already differ (e.g. MATTR), part of the post-2023 contrast is the detector selecting a writing style, not an effect of AI on diversity.
  - The paragraph detector (v2) will replace the flag with a dose once `paragraph_scores.jsonl.gz` exists. `run_all.sh` picks it up automatically.
- **Topic confound.** Labs that use AI more may also have moved into LLM research. The topic fixed effects and the LLM-topic share control for this only coarsely (10 lab topics, a keyword pattern).
- **Pre-trends.** The placebo slopes come from the same labs with no ChatGPT. A main slope inside the placebo band is not distinguishable from how these labs were already changing.
- **Partial 2026.** The post period includes 2026 papers to the extraction date, and lab-year rows for 2026 are partial.
- **Labs too small to measure:**
  - 155 of the 1016 labs with ≥ 5 papers in both periods lack ≥ 5 AI-scored post papers or the family's draw size.
  - 453 of the 1469 labs have < 5 papers in one of the periods and are not in `lab_diversity.csv` at all.
  - Family coverage differs: full texts and S2 references are missing for many papers.
  - Berkeley and Stanford have S2 reference lists for very few papers (the homogenization study's static s2.sqlite), so they rarely enter C1-C4.
- **Equal-size draws.** n is lab-specific (the smaller period), so a big lab's measures are on a different scale from a small lab's. The change within a lab is size-controlled; the regressions add log n.
- **Segments, not paragraphs.** Full-text vectors average ~150-word passages. S8 is the spread of those passages.
- **N1 space.** The arXiv background is re-embedded with specter2_base, because S2's stored specter_v2 vectors are a different space (same-paper cosine ~0.956 against ~0.82 between random papers).
- **Multiple comparisons.** 31 measures × several specifications. Read the pattern across families and against the placebo null, not single p-values.

## Files

- `lab_diversity.csv`: one row per lab × period, with every measure, n per family (`n_*`), draw size (`ndraw_*`) and AI usage (`ai_mean`, `ai_high`, `p_ai_mean`, `llm_share`).
  - `lab_diversity_placebo.csv`: the same for the placebo splits.
  - `lab_diversity_year.csv`: lab × year rows with n = 5 draws (7,841 rows).
- `results/`:
  - `slopes.csv`: every lab-level β, CI, p_boot, p_perm and n.
  - `within.csv`: the within-lab contrasts.
  - `lab_wide.csv`: per-lab changes.
  - `paper_lab_measures.csv.gz`: paper × lab measures.
  - `analysis.json`: counts and the null band.
- `figures/`:
  - `lab_scatter_{abs,ft,txt,ref}.png`: per-measure scatters.
  - `forest.png`, `forest_by_school.png`.
  - `fig3_fulltext.png`.
  - `flag_share_by_year.png`.
- `data/`:
  - `fulltext_emb.sqlite`: segment and mean vectors.
  - `background_specter2base.npz`.
  - `paper_features.parquet`.
  - `topics.npz`.
  - `s2_refs_cache.pkl.gz`.
- Code:
  - `measures.py` (+ `test_measures.py`).
  - `embed_fulltext.py` / `embed_fulltext.slurm` / `submit_embed.sh`.
  - `paper_features.py`, `lab_diversity.py`, `analyze.py`, `figures.py`, `report.py`.
  - `run_all.sh`.
