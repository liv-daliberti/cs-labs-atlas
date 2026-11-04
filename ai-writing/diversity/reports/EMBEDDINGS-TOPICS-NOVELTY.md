# Embeddings, topics and novelty for every paper

Generated 2026-11-04 19:09 UTC by `ai-writing/embeddings/emb_report.py`. Code, layout and models: `ai-writing/embeddings/README.md`. Tables: `ai-writing/data/embeddings/results/*.parquet` (slot `EMBEDDINGS`).

## Method

- **Papers.** Every lab paper of the seven released schools plus Georgia Tech and UChicago (their packages exist, both unreleased), one row per work (atlas id), years 2016-2026 in the analyses. A paper of several labs counts in each of its labs, departments and schools; its vectors are stored once under its home school.
- **Abstracts.** The OpenAlex abstract (rebuilt from `abstract_inverted_index` in the 2026-10-14 bulk snapshot, one more S3 pass: the local filtered snapshot kept no abstracts or topics), else the cached API abstract; at least 10 words. **Full text.** Every local copy: the existing body-text extraction, usable texts only (>= 1000 words, a PDF must show the title).
- **Models.** One vector set each, model id and revision recorded in every container (`index.sqlite` meta): `allenai/specter2_base`, `allenai/specter2_base` + proximity adapter, `malteos/scincl`, `Qwen/Qwen3-Embedding-0.6B`, `Alibaba-NLP/gte-Qwen2-1.5B-instruct`, `BAAI/bge-m3`, `nomic-ai/nomic-embed-text-v1.5`. Qwen3-Embedding-4B needs about 8 GB in fp16, the whole of an RTX 2080: not run. fp16, no flash-attention, windows of 512 (SPECTER2) or 8,192 tokens, chunk vectors kept with their mean.

## Coverage

Papers per school (home school; a paper of two schools is counted once), with an abstract, and with a usable full text:

| school | papers | abstract | usable full text |
|---|---|---|---|
| princeton | 8613 | 7361 | 6067 |
| cmu | 25057 | 21076 | 17478 |
| epfl | 12974 | 10987 | 8757 |
| mit | 19170 | 16233 | 12892 |
| berkeley | 13045 | 11110 | 8599 |
| stanford | 17508 | 14508 | 12035 |
| michigan | 11889 | 10260 | 6383 |
| uchicago (unreleased) | 4289 | 3721 | 2960 |
| gatech (unreleased) | 20115 | 17004 | 0 |
| all | 132660 | 112260 | 75171 |

Embedded papers per model and text kind:

| model | text | papers | by school | revision |
|---|---|---|---|---|
| specter2_base | abstract | 112260 | princeton 7361, cmu 21076, epfl 10987, mit 16233, berkeley 11110, stanford 14508, michigan 10260, uchicago 3721, gatech 17004 | 3447645e1def911799720345 |
| specter2_base | fulltext | 75171 | princeton 6067, cmu 17478, epfl 8757, mit 12892, berkeley 8599, stanford 12035, michigan 6383, uchicago 2960 | 3447645e1def911799720345 |
| specter2_proximity | abstract | 112260 | princeton 7361, cmu 21076, epfl 10987, mit 16233, berkeley 11110, stanford 14508, michigan 10260, uchicago 3721, gatech 17004 | 3447645e1def911799720345 |
| specter2_proximity | fulltext | 74434 | princeton 6043, cmu 17398, epfl 8719, mit 12835, berkeley 8560, stanford 11970, michigan 6356, uchicago 2553 | 3447645e1def911799720345 |
| scincl | abstract | 112260 | princeton 7361, cmu 21076, epfl 10987, mit 16233, berkeley 11110, stanford 14508, michigan 10260, uchicago 3721, gatech 17004 | ebc5348d184ba2fc9beee69b |
| qwen3_0p6b | abstract | 112260 | princeton 7361, cmu 21076, epfl 10987, mit 16233, berkeley 11110, stanford 14508, michigan 10260, uchicago 3721, gatech 17004 | 97b0c614be4d77ee51c0cef4 |
| qwen3_0p6b | fulltext | 0 | not embedded yet |  |
| gte_qwen2_1p5b | abstract | 112260 | princeton 7361, cmu 21076, epfl 10987, mit 16233, berkeley 11110, stanford 14508, michigan 10260, uchicago 3721, gatech 17004 | a9af15a6372d7d6b25e9fb07 |
| gte_qwen2_1p5b | fulltext | 0 | not embedded yet |  |
| bge_m3 | abstract | 112260 | princeton 7361, cmu 21076, epfl 10987, mit 16233, berkeley 11110, stanford 14508, michigan 10260, uchicago 3721, gatech 17004 | 5617a9f61b028005a4858fda |
| bge_m3 | fulltext | 0 | not embedded yet |  |
| nomic_v15 | abstract | 112260 | princeton 7361, cmu 21076, epfl 10987, mit 16233, berkeley 11110, stanford 14508, michigan 10260, uchicago 3721, gatech 17004 | e9b6763023c676ca84316442 |
| nomic_v15 | fulltext | 0 | not embedded yet |  |

## Topics

BERTopic on the abstract embeddings (UMAP 5 dims, cosine; HDBSCAN min_cluster_size 60; c-TF-IDF labels from title + abstract, unigrams and bigrams, no LLM). HDBSCAN noise is reassigned to the nearest topic so every paper has one; the share is below. Entropy in bits. Plug-in entropy rises with the number of papers, so the headline is entropy **rarefied** to the same number of papers (all papers 2,000 per year, a school 500, a department 100, a lab 20 per period). OpenAlex rows use the primary topic of each paper from the snapshot (4,516 topics; the subfield and field levels are the same papers coarsened).

### specter2_proximity

309 topics over 112,260 papers; 39.3% were HDBSCAN noise before reassignment. Largest topics: rl, demonstrations, imitation, imitation learning (3,203); voltage, electricity, charging, converter (2,451); robust control, lyapunov, nonlinear systems, dynamical (1,589); scene, scenes, rendering, camera (1,546); protein, molecular, molecules, chemical (1,487); brain, fmri, schizophrenia, neuroimaging (1,317); social media, news, political, twitter (1,244); pdes, differential equations, pde, partial differential (1,185).

**All papers, entropy by year (topic_label, rarefied to 2,000 papers)**

| year | papers | topics present | plug-in | rarefied [95%] |
|---|---|---|---|---|
| 2016 | 7758 | 306 | 7.75 | 7.67 [7.59, 7.74] |
| 2017 | 8433 | 306 | 7.82 | 7.73 [7.66, 7.81] |
| 2018 | 9498 | 307 | 7.85 | 7.76 [7.69, 7.82] |
| 2019 | 9702 | 306 | 7.84 | 7.74 [7.68, 7.81] |
| 2020 | 10408 | 307 | 7.84 | 7.74 [7.68, 7.81] |
| 2021 | 11047 | 309 | 7.82 | 7.72 [7.63, 7.80] |
| 2022 | 10056 | 309 | 7.82 | 7.73 [7.65, 7.81] |
| 2023 | 11061 | 309 | 7.82 | 7.73 [7.64, 7.81] |
| 2024 | 11699 | 309 | 7.78 | 7.67 [7.60, 7.75] |
| 2025 | 12300 | 309 | 7.71 | 7.61 [7.52, 7.71] |
| 2026 | 10298 | 308 | 7.51 | 7.40 [7.33, 7.48] |

**By school, mean yearly rarefied entropy, pre (2016-2022) and post (2023-2026), topic_label**

| school | pre | post | post - pre |
|---|---|---|---|
| berkeley | 6.81 | 6.84 | 0.02 |
| cmu | 7.10 | 6.93 | -0.18 |
| epfl | 6.77 | 6.91 | 0.14 |
| gatech | 7.00 | 6.93 | -0.06 |
| michigan | 7.01 | 7.05 | 0.05 |
| mit | 7.19 | 7.11 | -0.08 |
| princeton | 6.48 | 6.64 | 0.16 |
| stanford | 7.12 | 6.92 | -0.20 |

**Labs with >= 20 papers in both periods: entropy rarefied to 20 papers, mean over labs, post minus pre [95%, bootstrap over labs]**

| level | labs | pre | post | change |
|---|---|---|---|---|
| topic_label | 697 | 2.59 | 2.70 | 0.11 [0.07, 0.15] |

### qwen3_0p6b

379 topics over 112,260 papers; 36.6% were HDBSCAN noise before reassignment. Largest topics: electricity, power flow, renewable, buildings (1,609); diffusion models, texttoimage, vlms, generative models (1,502); social media, news, misinformation, political (1,212); quantum, qubits, qubit, superconducting (1,211); rl, markov decision, learning rl, mdps (1,174); fmri, schizophrenia, functional connectivity, restingstate (1,142); project page, website, page, project website (1,087); student, teachers, educational, tutoring (1,046).

**All papers, entropy by year (topic_label, rarefied to 2,000 papers)**

| year | papers | topics present | plug-in | rarefied [95%] |
|---|---|---|---|---|
| 2016 | 7758 | 369 | 8.04 | 7.93 [7.85, 8.02] |
| 2017 | 8433 | 374 | 8.12 | 8.01 [7.94, 8.09] |
| 2018 | 9498 | 377 | 8.18 | 8.07 [8.01, 8.13] |
| 2019 | 9702 | 377 | 8.21 | 8.10 [8.05, 8.16] |
| 2020 | 10408 | 379 | 8.22 | 8.09 [8.05, 8.14] |
| 2021 | 11047 | 379 | 8.19 | 8.07 [8.00, 8.13] |
| 2022 | 10056 | 379 | 8.17 | 8.06 [7.99, 8.12] |
| 2023 | 11061 | 379 | 8.17 | 8.06 [7.98, 8.14] |
| 2024 | 11699 | 379 | 8.10 | 7.97 [7.90, 8.05] |
| 2025 | 12300 | 378 | 8.02 | 7.90 [7.81, 7.99] |
| 2026 | 10298 | 379 | 7.87 | 7.76 [7.69, 7.83] |

**By school, mean yearly rarefied entropy, pre (2016-2022) and post (2023-2026), topic_label**

| school | pre | post | post - pre |
|---|---|---|---|
| berkeley | 7.17 | 7.11 | -0.06 |
| cmu | 7.39 | 7.21 | -0.18 |
| epfl | 7.07 | 7.23 | 0.17 |
| gatech | 7.23 | 7.16 | -0.07 |
| michigan | 7.28 | 7.30 | 0.02 |
| mit | 7.46 | 7.33 | -0.13 |
| princeton | 6.87 | 7.04 | 0.17 |
| stanford | 7.36 | 7.14 | -0.22 |

**Labs with >= 20 papers in both periods: entropy rarefied to 20 papers, mean over labs, post minus pre [95%, bootstrap over labs]**

| level | labs | pre | post | change |
|---|---|---|---|---|
| topic_label | 697 | 2.92 | 2.96 | 0.04 [0.01, 0.07] |

### OpenAlex primary topics

**All papers, entropy by year (oa_field, rarefied to 2,000 papers)**

| year | papers | topics present | plug-in | rarefied [95%] |
|---|---|---|---|---|
| 2016 | 9620 | 25 | 2.74 | 2.74 [2.60, 2.84] |
| 2017 | 10336 | 25 | 2.76 | 2.78 [2.67, 2.82] |
| 2018 | 11633 | 25 | 2.70 | 2.71 [2.55, 2.78] |
| 2019 | 11638 | 25 | 2.71 | 2.71 [2.58, 2.82] |
| 2020 | 12276 | 25 | 2.72 | 2.72 [2.60, 2.84] |
| 2021 | 12678 | 26 | 2.78 | 2.77 [2.62, 2.87] |
| 2022 | 11460 | 25 | 2.76 | 2.75 [2.64, 2.86] |
| 2023 | 12279 | 26 | 2.74 | 2.74 [2.60, 2.82] |
| 2024 | 13101 | 26 | 2.74 | 2.74 [2.62, 2.84] |
| 2025 | 14102 | 26 | 2.75 | 2.75 [2.62, 2.84] |
| 2026 | 11980 | 26 | 2.74 | 2.74 [2.61, 2.83] |

**By school, mean yearly rarefied entropy, pre (2016-2022) and post (2023-2026), oa_field**

| school | pre | post | post - pre |
|---|---|---|---|
| berkeley | 2.41 | 2.36 | -0.05 |
| cmu | 2.38 | 2.33 | -0.06 |
| epfl | 2.54 | 2.60 | 0.06 |
| gatech | 2.68 | 2.88 | 0.20 |
| michigan | 2.62 | 2.74 | 0.11 |
| mit | 2.82 | 2.84 | 0.01 |
| princeton | 2.66 | 2.65 | -0.01 |
| stanford | 2.97 | 2.81 | -0.16 |

**All papers, entropy by year (oa_subfield, rarefied to 2,000 papers)**

| year | papers | topics present | plug-in | rarefied [95%] |
|---|---|---|---|---|
| 2016 | 9620 | 168 | 5.35 | 5.29 [5.15, 5.37] |
| 2017 | 10336 | 176 | 5.34 | 5.29 [5.10, 5.37] |
| 2018 | 11633 | 183 | 5.28 | 5.23 [5.10, 5.31] |
| 2019 | 11638 | 186 | 5.26 | 5.19 [5.06, 5.32] |
| 2020 | 12276 | 177 | 5.25 | 5.18 [5.05, 5.34] |
| 2021 | 12678 | 183 | 5.25 | 5.19 [5.04, 5.30] |
| 2022 | 11460 | 178 | 5.25 | 5.20 [5.02, 5.33] |
| 2023 | 12279 | 188 | 5.21 | 5.15 [5.01, 5.21] |
| 2024 | 13101 | 198 | 5.17 | 5.12 [4.97, 5.23] |
| 2025 | 14102 | 191 | 5.16 | 5.11 [4.93, 5.18] |
| 2026 | 11980 | 184 | 5.14 | 5.09 [4.96, 5.16] |

**By school, mean yearly rarefied entropy, pre (2016-2022) and post (2023-2026), oa_subfield**

| school | pre | post | post - pre |
|---|---|---|---|
| berkeley | 4.57 | 4.46 | -0.11 |
| cmu | 4.74 | 4.53 | -0.22 |
| epfl | 4.92 | 4.81 | -0.12 |
| gatech | 5.11 | 5.16 | 0.05 |
| michigan | 5.06 | 5.05 | -0.00 |
| mit | 5.06 | 4.94 | -0.12 |
| princeton | 4.48 | 4.55 | 0.08 |
| stanford | 5.16 | 4.96 | -0.20 |

**All papers, entropy by year (oa_topic, rarefied to 2,000 papers)**

| year | papers | topics present | plug-in | rarefied [95%] |
|---|---|---|---|---|
| 2016 | 9620 | 1112 | 8.87 | 8.55 [8.35, 8.50] |
| 2017 | 10336 | 1152 | 8.90 | 8.56 [8.39, 8.54] |
| 2018 | 11633 | 1189 | 8.84 | 8.51 [8.28, 8.50] |
| 2019 | 11638 | 1175 | 8.76 | 8.43 [8.24, 8.40] |
| 2020 | 12276 | 1218 | 8.74 | 8.40 [8.19, 8.38] |
| 2021 | 12678 | 1235 | 8.71 | 8.35 [8.13, 8.37] |
| 2022 | 11460 | 1194 | 8.63 | 8.30 [8.09, 8.30] |
| 2023 | 12279 | 1223 | 8.60 | 8.26 [8.06, 8.27] |
| 2024 | 13101 | 1217 | 8.52 | 8.18 [7.97, 8.19] |
| 2025 | 14102 | 1262 | 8.46 | 8.09 [7.87, 8.15] |
| 2026 | 11980 | 1191 | 8.35 | 8.02 [7.85, 8.06] |

**By school, mean yearly rarefied entropy, pre (2016-2022) and post (2023-2026), oa_topic**

| school | pre | post | post - pre |
|---|---|---|---|
| berkeley | 7.08 | 6.93 | -0.15 |
| cmu | 7.33 | 7.05 | -0.28 |
| epfl | 7.46 | 7.36 | -0.09 |
| gatech | 7.63 | 7.46 | -0.17 |
| michigan | 7.54 | 7.40 | -0.15 |
| mit | 7.54 | 7.39 | -0.16 |
| princeton | 7.02 | 7.06 | 0.03 |
| stanford | 7.50 | 7.14 | -0.36 |

**Labs with >= 20 papers in both periods: entropy rarefied to 20 papers, mean over labs, post minus pre [95%, bootstrap over labs]**

| level | labs | pre | post | change |
|---|---|---|---|---|
| oa_field | 771 | 1.22 | 1.24 | 0.01 [-0.02, 0.04] |
| oa_subfield | 771 | 2.12 | 2.14 | 0.01 [-0.02, 0.05] |
| oa_topic | 771 | 2.87 | 2.91 | 0.04 [0.00, 0.07] |

## Novelty

Distance of each paper to the papers of the previous k years in the same scope (all papers, school, department, lab): `nov_max` = 1 - cosine to the closest earlier paper; `nov_nn` = 1 - mean cosine of the 5 nearest. `_cap` columns use a size-matched reference pool (at most 2,000 random earlier papers), because an uncapped pool grows with output and lowers 1 - max cosine by itself. Vectors are centred on the corpus mean and normalized. k = 3 is the headline; k = 1 and 5 are in `results/novelty_*.parquet`. Intervals: 95% bootstrap over labs.

### Year by year, all papers (k = 3, size-matched nearest-neighbour novelty `nov_nn_cap`)

| model | text | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | abstract | 0.684 [0.681, 0.686] | 0.689 [0.687, 0.691] | 0.691 [0.689, 0.692] | 0.693 [0.692, 0.695] | 0.691 [0.689, 0.693] | 0.692 [0.690, 0.694] | 0.694 [0.692, 0.696] | 0.694 [0.692, 0.696] | 0.693 [0.690, 0.695] | 0.695 [0.694, 0.697] |
| gte_qwen2_1p5b | abstract | 0.567 [0.562, 0.570] | 0.574 [0.570, 0.577] | 0.573 [0.569, 0.575] | 0.575 [0.572, 0.578] | 0.573 [0.570, 0.576] | 0.575 [0.571, 0.578] | 0.574 [0.571, 0.577] | 0.572 [0.569, 0.575] | 0.565 [0.561, 0.568] | 0.563 [0.561, 0.566] |
| nomic_v15 | abstract | 0.532 [0.529, 0.536] | 0.540 [0.536, 0.543] | 0.541 [0.538, 0.544] | 0.543 [0.540, 0.546] | 0.543 [0.540, 0.546] | 0.543 [0.539, 0.546] | 0.546 [0.542, 0.548] | 0.548 [0.545, 0.550] | 0.546 [0.542, 0.549] | 0.548 [0.545, 0.550] |
| qwen3_0p6b | abstract | 0.594 [0.590, 0.597] | 0.601 [0.597, 0.604] | 0.598 [0.596, 0.601] | 0.607 [0.604, 0.610] | 0.600 [0.597, 0.603] | 0.604 [0.601, 0.607] | 0.605 [0.603, 0.608] | 0.604 [0.602, 0.607] | 0.600 [0.596, 0.602] | 0.596 [0.593, 0.598] |
| scincl | abstract | 0.382 [0.377, 0.386] | 0.389 [0.385, 0.393] | 0.388 [0.384, 0.391] | 0.390 [0.386, 0.393] | 0.390 [0.387, 0.393] | 0.390 [0.387, 0.393] | 0.391 [0.388, 0.394] | 0.394 [0.391, 0.397] | 0.393 [0.389, 0.397] | 0.391 [0.388, 0.394] |
| specter2_base | abstract | 0.435 [0.431, 0.438] | 0.440 [0.436, 0.443] | 0.433 [0.430, 0.436] | 0.429 [0.426, 0.432] | 0.424 [0.420, 0.427] | 0.419 [0.415, 0.423] | 0.415 [0.412, 0.419] | 0.412 [0.409, 0.416] | 0.405 [0.401, 0.409] | 0.400 [0.397, 0.404] |
| specter2_base | fulltext | 0.304 [0.300, 0.308] | 0.311 [0.306, 0.315] | 0.307 [0.303, 0.311] | 0.303 [0.299, 0.306] | 0.301 [0.297, 0.304] | 0.296 [0.292, 0.300] | 0.297 [0.293, 0.301] | 0.295 [0.292, 0.298] | 0.292 [0.288, 0.295] | 0.290 [0.286, 0.294] |
| specter2_proximity | abstract | 0.456 [0.452, 0.459] | 0.462 [0.458, 0.465] | 0.460 [0.457, 0.463] | 0.461 [0.457, 0.464] | 0.459 [0.455, 0.462] | 0.457 [0.454, 0.460] | 0.454 [0.452, 0.458] | 0.453 [0.450, 0.457] | 0.448 [0.445, 0.451] | 0.444 [0.441, 0.448] |
| specter2_proximity | fulltext | 0.314 [0.309, 0.318] | 0.319 [0.314, 0.323] | 0.322 [0.318, 0.327] | 0.327 [0.324, 0.331] | 0.326 [0.322, 0.331] | 0.327 [0.323, 0.331] | 0.326 [0.322, 0.330] | 0.326 [0.323, 0.330] | 0.323 [0.319, 0.327] | 0.318 [0.314, 0.321] |

### Post (2023-2026) minus pre (2017-2022), difference in mean novelty, 95% interval

**1 - max cosine, size-matched, k = 3**

| model | text | all | princeton | cmu | epfl | mit | berkeley | stanford | michigan | uchicago | gatech | departments (pooled) | labs (pooled) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | abstract | 0.008 [0.006, 0.011] | 0.020 [-0.001, 0.033] | 0.005 [-0.001, 0.012] | 0.036 [0.027, 0.044] | 0.015 [0.008, 0.023] | 0.026 [0.018, 0.035] | 0.013 [0.006, 0.020] | 0.015 [0.005, 0.026] | -0.022 [-0.034, -0.009] | 0.017 [0.003, 0.031] | 0.006 [0.001, 0.010] | 0.014 [0.009, 0.019] |
| gte_qwen2_1p5b | abstract | 0.000 [-0.002, 0.003] | 0.012 [-0.009, 0.026] | -0.008 [-0.015, -0.001] | 0.025 [0.016, 0.036] | 0.006 [-0.001, 0.014] | 0.014 [0.004, 0.022] | 0.003 [-0.004, 0.011] | 0.007 [-0.004, 0.017] | -0.028 [-0.042, -0.013] | 0.009 [-0.004, 0.022] | -0.004 [-0.008, 0.000] | 0.004 [-0.001, 0.008] |
| nomic_v15 | abstract | 0.010 [0.007, 0.012] | 0.018 [-0.002, 0.031] | 0.005 [-0.002, 0.012] | 0.033 [0.023, 0.043] | 0.015 [0.009, 0.023] | 0.024 [0.015, 0.032] | 0.011 [0.004, 0.020] | 0.012 [0.001, 0.023] | -0.022 [-0.037, -0.007] | 0.015 [0.001, 0.031] | 0.005 [-0.000, 0.009] | 0.013 [0.008, 0.017] |
| qwen3_0p6b | abstract | 0.005 [0.003, 0.008] | 0.011 [-0.010, 0.026] | -0.006 [-0.013, 0.002] | 0.025 [0.016, 0.035] | 0.011 [0.005, 0.018] | 0.018 [0.009, 0.028] | 0.002 [-0.005, 0.009] | 0.011 [-0.000, 0.022] | -0.029 [-0.043, -0.015] | 0.015 [0.002, 0.028] | -0.002 [-0.007, 0.002] | 0.007 [0.002, 0.011] |
| scincl | abstract | 0.008 [0.006, 0.011] | 0.014 [-0.002, 0.025] | 0.001 [-0.006, 0.008] | 0.024 [0.015, 0.034] | 0.010 [0.005, 0.016] | 0.019 [0.011, 0.027] | 0.007 [0.001, 0.014] | 0.011 [0.002, 0.019] | -0.020 [-0.034, -0.006] | 0.014 [0.002, 0.025] | 0.002 [-0.002, 0.006] | 0.009 [0.004, 0.013] |
| specter2_base | abstract | -0.017 [-0.019, -0.014] | -0.007 [-0.021, 0.003] | -0.023 [-0.030, -0.016] | 0.007 [-0.001, 0.014] | -0.012 [-0.017, -0.007] | -0.006 [-0.013, 0.000] | -0.015 [-0.021, -0.008] | -0.013 [-0.022, -0.006] | -0.037 [-0.050, -0.025] | -0.007 [-0.018, 0.005] | -0.019 [-0.023, -0.016] | -0.011 [-0.015, -0.007] |
| specter2_base | fulltext | -0.005 [-0.008, -0.002] | -0.002 [-0.012, 0.007] | -0.011 [-0.018, -0.004] | 0.006 [-0.002, 0.014] | -0.003 [-0.008, 0.003] | -0.003 [-0.011, 0.003] | -0.009 [-0.014, -0.003] | -0.019 [-0.027, -0.012] | -0.016 [-0.029, -0.001] |  | -0.011 [-0.014, -0.007] | -0.003 [-0.008, 0.001] |
| specter2_proximity | abstract | -0.006 [-0.008, -0.003] | 0.000 [-0.017, 0.012] | -0.013 [-0.019, -0.006] | 0.018 [0.009, 0.026] | -0.002 [-0.008, 0.004] | 0.003 [-0.005, 0.010] | -0.006 [-0.012, 0.001] | -0.000 [-0.009, 0.008] | -0.029 [-0.041, -0.016] | 0.006 [-0.005, 0.016] | -0.009 [-0.012, -0.006] | -0.001 [-0.006, 0.003] |
| specter2_proximity | fulltext | 0.004 [0.001, 0.007] | 0.007 [-0.006, 0.017] | -0.004 [-0.012, 0.003] | 0.015 [0.006, 0.024] | 0.006 [0.000, 0.012] | 0.003 [-0.005, 0.010] | -0.003 [-0.009, 0.003] | -0.010 [-0.018, -0.001] | -0.010 [-0.024, 0.005] |  | -0.002 [-0.006, 0.001] | 0.004 [-0.000, 0.009] |

**1 - mean of 5 nearest, size-matched, k = 3**

| model | text | all | princeton | cmu | epfl | mit | berkeley | stanford | michigan | uchicago | gatech | departments (pooled) | labs (pooled) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | abstract | 0.004 [0.002, 0.005] | 0.004 [-0.014, 0.017] | -0.001 [-0.005, 0.004] | 0.023 [0.016, 0.030] | 0.007 [0.001, 0.013] | 0.015 [0.008, 0.022] | 0.001 [-0.004, 0.007] | 0.005 [-0.004, 0.013] | -0.024 [-0.032, -0.015] | 0.008 [-0.003, 0.020] | -0.004 [-0.007, -0.000] | 0.002 [-0.002, 0.006] |
| gte_qwen2_1p5b | abstract | -0.004 [-0.007, -0.001] | -0.002 [-0.023, 0.014] | -0.015 [-0.020, -0.009] | 0.016 [0.007, 0.026] | -0.002 [-0.008, 0.005] | 0.005 [-0.004, 0.014] | -0.008 [-0.014, -0.001] | -0.000 [-0.011, 0.009] | -0.035 [-0.046, -0.023] | 0.003 [-0.010, 0.017] | -0.013 [-0.017, -0.009] | -0.007 [-0.012, -0.002] |
| nomic_v15 | abstract | 0.006 [0.004, 0.008] | 0.006 [-0.015, 0.020] | -0.001 [-0.007, 0.005] | 0.024 [0.016, 0.034] | 0.007 [0.001, 0.014] | 0.015 [0.008, 0.023] | 0.001 [-0.006, 0.008] | 0.005 [-0.006, 0.014] | -0.029 [-0.040, -0.017] | 0.010 [-0.004, 0.025] | -0.005 [-0.010, -0.001] | 0.001 [-0.004, 0.006] |
| qwen3_0p6b | abstract | 0.000 [-0.002, 0.003] | 0.001 [-0.021, 0.017] | -0.012 [-0.019, -0.005] | 0.016 [0.007, 0.024] | 0.004 [-0.002, 0.011] | 0.009 [0.000, 0.018] | -0.008 [-0.014, -0.002] | 0.003 [-0.006, 0.013] | -0.032 [-0.043, -0.021] | 0.007 [-0.006, 0.020] | -0.012 [-0.016, -0.007] | -0.005 [-0.011, -0.000] |
| scincl | abstract | 0.004 [0.002, 0.007] | 0.004 [-0.017, 0.018] | -0.007 [-0.014, 0.001] | 0.018 [0.008, 0.029] | 0.004 [-0.002, 0.010] | 0.012 [0.004, 0.021] | -0.002 [-0.008, 0.005] | 0.007 [-0.003, 0.016] | -0.031 [-0.045, -0.019] | 0.010 [-0.003, 0.023] | -0.008 [-0.012, -0.003] | -0.003 [-0.008, 0.003] |
| specter2_base | abstract | -0.021 [-0.023, -0.019] | -0.018 [-0.035, -0.007] | -0.031 [-0.039, -0.024] | -0.001 [-0.009, 0.008] | -0.020 [-0.024, -0.014] | -0.015 [-0.022, -0.008] | -0.026 [-0.032, -0.020] | -0.020 [-0.029, -0.012] | -0.047 [-0.060, -0.034] | -0.012 [-0.025, 0.000] | -0.029 [-0.033, -0.025] | -0.022 [-0.028, -0.018] |
| specter2_base | fulltext | -0.010 [-0.013, -0.007] | -0.013 [-0.027, -0.001] | -0.021 [-0.030, -0.012] | -0.000 [-0.009, 0.008] | -0.012 [-0.018, -0.006] | -0.013 [-0.021, -0.005] | -0.018 [-0.024, -0.012] | -0.030 [-0.039, -0.023] | -0.033 [-0.047, -0.018] |  | -0.023 [-0.027, -0.019] | -0.017 [-0.023, -0.011] |
| specter2_proximity | abstract | -0.009 [-0.012, -0.007] | -0.011 [-0.030, 0.002] | -0.019 [-0.026, -0.012] | 0.011 [0.002, 0.019] | -0.008 [-0.014, -0.003] | -0.005 [-0.012, 0.002] | -0.015 [-0.021, -0.010] | -0.006 [-0.015, 0.001] | -0.037 [-0.048, -0.024] | 0.002 [-0.010, 0.013] | -0.017 [-0.021, -0.014] | -0.011 [-0.016, -0.007] |
| specter2_proximity | fulltext | -0.000 [-0.003, 0.003] | -0.001 [-0.017, 0.012] | -0.011 [-0.020, -0.003] | 0.011 [0.001, 0.020] | -0.002 [-0.008, 0.004] | -0.005 [-0.014, 0.002] | -0.011 [-0.017, -0.004] | -0.019 [-0.028, -0.009] | -0.025 [-0.040, -0.010] |  | -0.013 [-0.017, -0.008] | -0.008 [-0.013, -0.002] |

**1 - max cosine, full pool, k = 3**

| model | text | all | princeton | cmu | epfl | mit | berkeley | stanford | michigan | uchicago | gatech | departments (pooled) | labs (pooled) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bge_m3 | abstract | 0.001 [-0.002, 0.004] | 0.013 [-0.007, 0.026] | -0.008 [-0.015, -0.002] | 0.018 [0.008, 0.027] | -0.000 [-0.007, 0.008] | 0.014 [0.007, 0.022] | -0.008 [-0.015, 0.000] | 0.006 [-0.005, 0.016] | -0.022 [-0.034, -0.009] | -0.001 [-0.014, 0.012] | 0.004 [-0.001, 0.007] | 0.014 [0.009, 0.019] |
| gte_qwen2_1p5b | abstract | -0.009 [-0.012, -0.006] | 0.005 [-0.016, 0.020] | -0.023 [-0.029, -0.015] | 0.007 [-0.002, 0.017] | -0.009 [-0.015, -0.001] | 0.002 [-0.007, 0.009] | -0.016 [-0.024, -0.009] | -0.005 [-0.015, 0.005] | -0.028 [-0.042, -0.013] | -0.009 [-0.021, 0.003] | -0.006 [-0.010, -0.002] | 0.004 [-0.001, 0.008] |
| nomic_v15 | abstract | -0.001 [-0.003, 0.002] | 0.011 [-0.009, 0.024] | -0.010 [-0.017, -0.003] | 0.016 [0.006, 0.025] | 0.000 [-0.006, 0.007] | 0.011 [0.002, 0.019] | -0.009 [-0.017, -0.001] | 0.001 [-0.009, 0.012] | -0.022 [-0.037, -0.007] | -0.003 [-0.016, 0.011] | 0.002 [-0.002, 0.006] | 0.013 [0.008, 0.017] |
| qwen3_0p6b | abstract | -0.007 [-0.010, -0.004] | 0.004 [-0.018, 0.019] | -0.021 [-0.028, -0.014] | 0.007 [-0.002, 0.017] | -0.004 [-0.010, 0.003] | 0.005 [-0.003, 0.013] | -0.020 [-0.028, -0.012] | -0.000 [-0.011, 0.009] | -0.029 [-0.043, -0.015] | -0.004 [-0.016, 0.008] | -0.005 [-0.009, -0.000] | 0.007 [0.002, 0.011] |
| scincl | abstract | -0.000 [-0.002, 0.002] | 0.009 [-0.007, 0.021] | -0.010 [-0.017, -0.004] | 0.010 [0.002, 0.019] | -0.003 [-0.008, 0.003] | 0.009 [0.002, 0.016] | -0.010 [-0.016, -0.004] | 0.002 [-0.007, 0.010] | -0.020 [-0.034, -0.006] | -0.002 [-0.012, 0.008] | -0.000 [-0.004, 0.004] | 0.009 [0.004, 0.013] |
| specter2_base | abstract | -0.022 [-0.023, -0.019] | -0.012 [-0.026, -0.001] | -0.034 [-0.040, -0.028] | -0.007 [-0.014, -0.000] | -0.023 [-0.028, -0.019] | -0.015 [-0.022, -0.009] | -0.032 [-0.038, -0.026] | -0.022 [-0.030, -0.014] | -0.037 [-0.050, -0.025] | -0.021 [-0.031, -0.011] | -0.021 [-0.024, -0.018] | -0.011 [-0.015, -0.007] |
| specter2_base | fulltext | -0.013 [-0.014, -0.010] | -0.002 [-0.013, 0.007] | -0.022 [-0.029, -0.016] | -0.003 [-0.011, 0.004] | -0.012 [-0.016, -0.006] | -0.012 [-0.019, -0.006] | -0.022 [-0.028, -0.017] | -0.021 [-0.029, -0.014] | -0.016 [-0.029, -0.001] |  | -0.012 [-0.016, -0.009] | -0.003 [-0.008, 0.001] |
| specter2_proximity | abstract | -0.013 [-0.015, -0.010] | -0.005 [-0.022, 0.007] | -0.024 [-0.030, -0.018] | 0.004 [-0.005, 0.011] | -0.015 [-0.020, -0.009] | -0.006 [-0.013, -0.000] | -0.022 [-0.028, -0.016] | -0.008 [-0.017, -0.001] | -0.029 [-0.041, -0.016] | -0.009 [-0.020, 0.000] | -0.011 [-0.014, -0.007] | -0.001 [-0.006, 0.003] |
| specter2_proximity | fulltext | -0.006 [-0.008, -0.004] | 0.007 [-0.006, 0.017] | -0.013 [-0.020, -0.007] | 0.006 [-0.002, 0.014] | -0.004 [-0.010, 0.002] | -0.005 [-0.013, 0.001] | -0.017 [-0.023, -0.011] | -0.012 [-0.020, -0.003] | -0.010 [-0.024, 0.005] |  | -0.004 [-0.008, -0.000] | 0.004 [-0.000, 0.009] |

Other windows (k = 1, 5) for all papers, `nov_nn_cap`:

| model | text | k | mean pre | mean post | post - pre |
|---|---|---|---|---|---|
| bge_m3 | abstract | 1 | 0.688 | 0.690 | 0.002 [0.001, 0.004] |
| bge_m3 | abstract | 3 | 0.690 | 0.694 | 0.004 [0.002, 0.005] |
| bge_m3 | abstract | 5 | 0.691 | 0.697 | 0.005 [0.004, 0.007] |
| gte_qwen2_1p5b | abstract | 1 | 0.571 | 0.563 | -0.007 [-0.010, -0.004] |
| gte_qwen2_1p5b | abstract | 3 | 0.573 | 0.569 | -0.004 [-0.007, -0.001] |
| gte_qwen2_1p5b | abstract | 5 | 0.574 | 0.572 | -0.002 [-0.004, 0.001] |
| nomic_v15 | abstract | 1 | 0.539 | 0.542 | 0.003 [0.001, 0.005] |
| nomic_v15 | abstract | 3 | 0.541 | 0.547 | 0.006 [0.004, 0.008] |
| nomic_v15 | abstract | 5 | 0.542 | 0.550 | 0.007 [0.005, 0.010] |
| qwen3_0p6b | abstract | 1 | 0.599 | 0.595 | -0.004 [-0.007, -0.002] |
| qwen3_0p6b | abstract | 3 | 0.601 | 0.601 | 0.000 [-0.002, 0.003] |
| qwen3_0p6b | abstract | 5 | 0.602 | 0.604 | 0.002 [-0.000, 0.004] |
| scincl | abstract | 1 | 0.386 | 0.388 | 0.002 [0.000, 0.005] |
| scincl | abstract | 3 | 0.388 | 0.392 | 0.004 [0.002, 0.007] |
| scincl | abstract | 5 | 0.390 | 0.395 | 0.005 [0.003, 0.008] |
| specter2_base | abstract | 1 | 0.426 | 0.403 | -0.023 [-0.026, -0.021] |
| specter2_base | abstract | 3 | 0.430 | 0.409 | -0.021 [-0.023, -0.019] |
| specter2_base | abstract | 5 | 0.432 | 0.412 | -0.019 [-0.022, -0.017] |
| specter2_base | fulltext | 1 | 0.299 | 0.288 | -0.012 [-0.015, -0.009] |
| specter2_base | fulltext | 3 | 0.303 | 0.293 | -0.010 [-0.013, -0.007] |
| specter2_base | fulltext | 5 | 0.305 | 0.298 | -0.007 [-0.010, -0.004] |
| specter2_proximity | abstract | 1 | 0.457 | 0.445 | -0.012 [-0.014, -0.009] |
| specter2_proximity | abstract | 3 | 0.459 | 0.450 | -0.009 [-0.012, -0.007] |
| specter2_proximity | abstract | 5 | 0.461 | 0.453 | -0.008 [-0.010, -0.006] |
| specter2_proximity | fulltext | 1 | 0.320 | 0.317 | -0.003 [-0.006, -0.000] |
| specter2_proximity | fulltext | 3 | 0.323 | 0.323 | -0.000 [-0.003, 0.003] |
| specter2_proximity | fulltext | 5 | 0.325 | 0.328 | 0.004 [0.001, 0.007] |

## Reading the results (as of 2026-11-04)

- Novelty: the direction of the post-2023 change depends on the embedding model, so there is no model-agnostic trend. The SPECTER2 family (trained on citation structure) shows lower novelty after 2022 on abstracts (size-matched 1 - mean-of-5-nearest, k = 3, all papers: SPECTER2 base about -0.02, proximity about -0.01); BGE-M3, Nomic and SciNCL show a small rise (about +0.004 to +0.006); gte-Qwen2 and Qwen3 are near zero. EPFL rises under every model; UChicago falls under every model (its 2016-2018 pool is small). Full-text vectors move less than abstract vectors. The size-matched and full-pool columns differ because a growing pool lowers 1 - max cosine by itself.
- Topics: entropy over BERTopic topics is flat from 2016 to 2023 and lower in 2025-2026 (2026 is a partial year); per school the post-pre change has opposite signs (CMU and Stanford down, EPFL and Princeton up). Labs with >= 20 papers in both periods are slightly more spread over topics after 2022 (interval in the lab table). Topics are model-dependent (309 and 379 topics; 37-39% of papers are HDBSCAN noise before reassignment), so compare the two models and the OpenAlex rows rather than trust one.
- Full-text vectors of the 8k-token models (Qwen3, GTE-Qwen2, BGE-M3, Nomic) are produced by queued resumable jobs; the coverage table shows what has been merged so far.

