
# What if every paper were AI-written? Diversity and novelty on rewritten abstracts

Generated 2026-11-05 by `ai-writing/allai/` (code: `rewrite.py`, `build_texts.py`, `preserve.py`, `allai_analyze.py`, `site_data.py`; tables: `ai-writing/data/embeddings/allai/results/`, git-ignored). Site data: `ai-writing/diversity/site-data/all-ai/` (README there).

## Answer

- **Diversity still falls after 2022 when every abstract is AI-worded, by nearly the same amount.** For all papers (specter2_proximity, 1,000-paper draws), topic entropy over BERTopic topics changes by -0.091 [-0.164, -0.018] bits (original) against -0.092 [-0.165, -0.019] (all-AI), post-2023 minus 2016-2022; the gap (original minus AI, the part due to wording) is 0.001 [-0.023, 0.025]. The Vendi score (effectively distinct papers) falls -7.222 [-8.712, -5.732] in the original and -6.077 [-7.506, -4.648] in the all-AI corpus: about one sixth of the Vendi decline (gap -1.145 [-1.388, -0.902]) is wording, the rest is content.
- **The wording share is small and depends on the embedding model.** Topic entropy and dispersion: gap about 0 for 6 of 7 models (k-means entropy) and for specter2_proximity; Qwen3-0.6B shows a gap of +0.055 bits (the AI corpus falls more). Vendi: gap negative for the SPECTER2 pair, SciNCL and Qwen3-0.6B, positive for Nomic, about 0 for GTE-Qwen2 and BGE-M3. Novelty (k = 3): SPECTER2's fall after 2022 (-0.009) is still there in the AI corpus (-0.0065), the gap is -0.003 (about 30% of it); BGE-M3, SciNCL, GTE-Qwen2 gaps are within 0.001.
- **Levels differ a little, trends hardly.** Rewriting makes the corpus slightly more uniform: Vendi 1-3% lower in the all-AI corpus (specter2_proximity 96.8 -> 94.0 in 2016), topic entropy unchanged.
- **Lab level** (605 labs with >= 20 papers in both periods, 20-paper draws): entropy over topics rises in both corpora by about +0.13 bits (BERTopic, specter2_proximity) and +0.12 (k-means); the gap is 0.009 [-0.002, 0.020] and -0.004 [-0.015, 0.009].

## Method

- **Corpus.** The embeddings universe: 112,260 abstracts (`oa_fields`/`texts.sqlite`), keyed by atlas paper id. The title stays as written (it is human text; abstracts only, as asked).
- **Rewrite.** Qwen/Qwen2.5-7B-Instruct, revision `a09a35458c702b33eeacc393d103063234e8bc28` (it was not in the HF cache; fetched by job 32105407), vLLM 0.8.3, bf16, greedy decoding (temperature 0, seed 20261104), max new tokens min(1500, 1.5 x source tokens + 100), sources over 1,800 tokens skipped. One fixed prompt, system prompt "You are a helpful assistant.": *Here is the abstract of a research paper titled "{title}". Rewrite it as a polished academic abstract: improve its clarity, flow and academic style. Keep every claim, number, method name and technical term exactly as given; do not add or drop any information. Keep roughly the same length (about {n} words). Return only the rewritten abstract, as plain text in a single paragraph.* (the detector's "polish" task, written for abstracts). Output cleaning is detector_v2's `clean`. Container: `allai/rewrites_polish.sqlite` (paper id, text, ok, why, hashes, meta with model, revision, prompt, parameters). Resumable per-shard sqlite files, 3 shards, 59-minute task chains on node105 A5000s.
- **Second style.** Paraphrase ("in your own words", numbers and named methods kept) on 4,996 papers stratified by home school and year, same model and parameters.
- **Embeddings.** The same seven models as the originals (SPECTER2 base and proximity, SciNCL, Qwen3-0.6B, GTE-Qwen2-1.5B, BGE-M3, Nomic v1.5), `embed.py --texts-db ... --store-name <model>__allai` (`__para`), so originals and rewrites never share a container. Qwen3-Embedding-4B is not run: its original-abstract container does not exist yet (another job is still producing it), so there is nothing to compare against.
- **Measures** (`allai_analyze.py`; as the embeddings report plus the geometry measures of the diversity battery). Each corpus is centred on its own mean and normalised. Dispersion (mean distance from the centroid), mean pairwise cosine distance, Vendi score, topic entropy over **fixed clusters defined on the originals** (BERTopic topics of `topics.py`, specter2_proximity and qwen3_0p6b: a paper goes to the nearest topic centroid in both corpora, the rewrite's topic is whatever it is nearest to; and 100 k-means clusters, every model), novelty k = 1, 3, 5 (`novelty.py`, nearest-5 and max cosine, pool capped at 2,000). Size-matched paired draws: all papers 1,000, a school-year 500, a lab-period 20 papers (novelty as in the embeddings report). Intervals: bootstrap over labs (a paper's first lab) with replacement; for the diversity series 40 replicates, estimate +- 1.96 sd (resampling labs repeats papers, which lowers every resampled diversity, so percentiles would not bracket the estimate); the original-minus-AI gap is paired (same papers drawn from both), so its interval is narrow. Lab changes: 1,000 bootstrap resamples of labs; novelty: `mean_by_year` / `diff_ci` as in the embeddings report.
- **Same papers in both corpora.** Both corpora are restricted to the papers whose rewrite passed the filter below (97,940 of 112,260).

## Content preservation

Polish style, all 112,260 abstracts: 112,187 rewrites passed the basic checks (not cut at the token limit, not a refusal, at least 40% of the source's words); the failures are 44 much shorter than the source, 22 sources over 1,800 tokens (not rewritten), 6 truncated, 1 refusal. The rewrite is 8% shorter than its source (median length ratio 0.916).

**Automatic number and named-method check** (`preserve.py`: numeric tokens; named methods = acronyms, CamelCase and names with digits such as BERT, ResNet-50, LoRA; matching ignores case, hyphens and spaces):

| check | share of rewrites |
|---|---|
| lose at least one number of the source (of the 55,149 abstracts with numbers) | 10.0% (all abstracts); 11.5% of all numbers |
| add a number that is not in the source | 4.7% |
| lose at least one named method (of the 84,222 abstracts with terms) | 7.6%; 4.5% of all terms |

**Filter** (build_texts.py): drop a rewrite that fails the basic checks, loses 25% or more of the source's numbers, adds more new numbers than a quarter of the source's (at least 1), or loses 25% or more of its named methods. This removes 14,320 rewrites (12.8%): numbers lost 9,200, named methods lost 4,156, numbers added 891, and the basic failures above. **Kept: 97,940 papers**; the analyses use only these, with the same papers' originals. (I did not redo failures: they are 13% and the filter is applied to both corpora, so the comparison is unchanged; the all-AI corpus is therefore the 87% of papers whose rewrite kept its content.)

**Embedding cosine, original vs its rewrite** (per model; unrelated pairs sit at 0 after centring; `own rewrite is nearest` = for 2,000 random papers, the share whose own rewrite is the nearest of the 2,000 rewrites):

| model | centred cosine, mean | 5th percentile | raw cosine, mean | unrelated pair (centred) | own rewrite is nearest of 2,000 |
|---|---|---|---|---|---|
| specter2_base | 0.982 | 0.956 | 0.9965 | -0.000 | 0.9995 |
| specter2_proximity | 0.977 | 0.946 | 0.9953 | -0.000 | 0.9995 |
| scincl | 0.982 | 0.954 | 0.9937 | 0.001 | 0.9995 |
| qwen3_0p6b | 0.936 | 0.848 | 0.9709 | 0.000 | 0.9985 |
| gte_qwen2_1p5b | 0.982 | 0.954 | 0.9898 | 0.000 | 1.0000 |
| bge_m3 | 0.961 | 0.909 | 0.9791 | -0.000 | 1.0000 |
| nomic_v15 | 0.977 | 0.952 | 0.9879 | 0.000 | 1.0000 |

Qwen3-0.6B is the least invariant to rewriting (centred cosine 0.936, 5th percentile 0.85); the SPECTER2 models, SciNCL and GTE-Qwen2 sit at 0.98. This matches where the all-AI trend differs most from the original's (Qwen3-0.6B entropy gap, Nomic and Qwen3 Vendi gaps): those models see some of the wording.

**Hand read, 20 random kept polish rewrites** (seed 20261104). No change of claim, number or method in any. Four small drifts: "Kalman filter" became "Kalman-Bucy filter"; "Milano" became "Milan"; two rewrites added a mild evaluative phrase ("more accurate and reliable", "to enhance user experience"). Two additions that looked invented were in the part of the original abstract I had not yet read. No rewrite dropped a result or reversed a finding.

**AI detector** (detector_v2's final ModernBERT model, threshold at 1% false positives on held-out body passages, each abstract scored as one passage): **99.3% of the 112,187 rewrites are flagged.** Original abstracts (a sample of 1,000 per year): 24.9% overall, 15.1% for 2016-2022 and 42.2% for 2023-2026. The detector was trained on body passages, not abstracts, so the pre-2023 abstract rate (15%, far above the 1% design rate) is the baseline of this register, and the rise to 42% after 2022 is the signal of AI-assisted wording already in the real abstracts. Paraphrase rewrites: 99.7% flagged.

## Results

All tables: post (2023-2026) minus pre (2016-2022; novelty 2017-2022), 95% intervals. Negative gap = the original fell more (or rose less) than the all-AI corpus.

### Levels, original / all-AI, all papers (size-matched 1,000-paper draws)

| measure | model | 2016 | 2019 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| vendi | specter2_proximity | 96.77 / 94.03 | 94.50 / 92.19 | 93.74 / 91.86 | 89.56 / 88.13 | 86.54 / 85.52 |
| vendi | qwen3_0p6b | 216.73 / 213.00 | 217.07 / 212.58 | 218.40 / 214.29 | 212.78 / 209.84 | 205.18 / 206.71 |
| vendi | bge_m3 | 240.13 / 239.33 | 242.87 / 241.90 | 244.88 / 244.11 | 242.37 / 241.39 | 240.67 / 240.05 |
| H_bt | specter2_proximity | 7.66 / 7.65 | 7.76 / 7.77 | 7.75 / 7.75 | 7.71 / 7.71 | 7.64 / 7.64 |
| H_bt | qwen3_0p6b | 7.85 / 7.89 | 8.00 / 7.99 | 7.98 / 7.99 | 7.93 / 7.88 | 7.86 / 7.81 |
| H_km | specter2_proximity | 6.40 / 6.40 | 6.51 / 6.51 | 6.52 / 6.52 | 6.48 / 6.48 | 6.45 / 6.45 |
| H_km | qwen3_0p6b | 6.31 / 6.33 | 6.46 / 6.46 | 6.49 / 6.48 | 6.44 / 6.38 | 6.35 / 6.29 |
| H_km | bge_m3 | 6.33 / 6.33 | 6.45 / 6.45 | 6.50 / 6.50 | 6.46 / 6.46 | 6.40 / 6.40 |

### Post minus pre, all papers

| measure | model | original post - pre | all-AI post - pre | gap (orig - AI) |
|---|---|---|---|---|
| vendi | specter2_proximity | -7.222 [-8.712, -5.732] | -6.077 [-7.506, -4.648] | -1.145 [-1.388, -0.902] |
| vendi | specter2_base | -10.959 [-12.350, -9.568] | -9.111 [-10.410, -7.811] | -1.849 [-2.091, -1.606] |
| vendi | scincl | -3.267 [-4.422, -2.112] | -3.034 [-4.186, -1.883] | -0.233 [-0.393, -0.073] |
| vendi | qwen3_0p6b | -7.530 [-10.632, -4.428] | -4.390 [-7.190, -1.589] | -3.140 [-4.033, -2.247] |
| vendi | gte_qwen2_1p5b | -12.597 [-16.927, -8.266] | -12.379 [-16.668, -8.091] | -0.217 [-0.651, 0.216] |
| vendi | bge_m3 | -0.310 [-2.447, 1.827] | -0.210 [-2.325, 1.904] | -0.100 [-0.492, 0.293] |
| vendi | nomic_v15 | -0.289 [-2.320, 1.743] | -1.384 [-3.407, 0.640] | 1.095 [0.690, 1.500] |
| H_bt | specter2_proximity | -0.091 [-0.164, -0.018] | -0.092 [-0.165, -0.019] | 0.001 [-0.023, 0.025] |
| H_bt | qwen3_0p6b | -0.090 [-0.151, -0.030] | -0.146 [-0.212, -0.081] | 0.056 [0.030, 0.082] |
| H_km | specter2_proximity | -0.051 [-0.103, 0.002] | -0.052 [-0.102, -0.002] | 0.001 [-0.010, 0.012] |
| H_km | specter2_base | -0.052 [-0.102, -0.001] | -0.051 [-0.095, -0.008] | -0.000 [-0.013, 0.012] |
| H_km | scincl | -0.004 [-0.045, 0.037] | -0.008 [-0.050, 0.034] | 0.004 [-0.006, 0.014] |
| H_km | qwen3_0p6b | -0.055 [-0.103, -0.006] | -0.109 [-0.165, -0.053] | 0.055 [0.031, 0.078] |
| H_km | gte_qwen2_1p5b | -0.073 [-0.125, -0.021] | -0.078 [-0.129, -0.027] | 0.005 [-0.007, 0.018] |
| H_km | bge_m3 | -0.020 [-0.059, 0.019] | -0.019 [-0.057, 0.018] | -0.001 [-0.013, 0.012] |
| H_km | nomic_v15 | 0.001 [-0.041, 0.043] | 0.003 [-0.040, 0.046] | -0.003 [-0.015, 0.010] |
| dispersion | specter2_proximity | -0.003 [-0.005, -0.001] | -0.003 [-0.005, -0.000] | -0.000 [-0.001, -0.000] |
| dispersion | specter2_base | -0.003 [-0.005, -0.001] | -0.003 [-0.005, -0.000] | -0.000 [-0.000, -0.000] |
| dispersion | scincl | -0.002 [-0.004, -0.000] | -0.002 [-0.004, -0.000] | -0.000 [-0.000, -0.000] |
| dispersion | qwen3_0p6b | -0.002 [-0.004, -0.001] | -0.001 [-0.002, -0.000] | -0.001 [-0.002, -0.001] |
| dispersion | gte_qwen2_1p5b | -0.001 [-0.003, 0.000] | -0.001 [-0.003, 0.000] | -0.000 [-0.000, 0.000] |
| dispersion | bge_m3 | -0.001 [-0.001, -0.000] | -0.001 [-0.001, -0.000] | -0.000 [-0.000, 0.000] |
| dispersion | nomic_v15 | -0.001 [-0.003, -0.000] | -0.001 [-0.003, -0.000] | -0.000 [-0.000, 0.000] |

### Post minus pre, per lab (labs with >= 20 papers in both periods; 20-paper draws; mean over labs)

| measure | model | labs | original post - pre | all-AI post - pre | gap |
|---|---|---|---|---|---|
| vendi | specter2_proximity | 605 | 0.073 [-0.013, 0.165] | 0.115 [0.027, 0.203] | -0.042 [-0.055, -0.030] |
| vendi | specter2_base | 605 | -0.145 [-0.236, -0.048] | -0.067 [-0.158, 0.030] | -0.078 [-0.089, -0.065] |
| vendi | scincl | 605 | 0.285 [0.192, 0.383] | 0.286 [0.191, 0.383] | -0.001 [-0.012, 0.010] |
| vendi | qwen3_0p6b | 605 | 0.202 [0.110, 0.295] | 0.215 [0.121, 0.309] | -0.013 [-0.034, 0.010] |
| vendi | gte_qwen2_1p5b | 605 | 0.187 [0.099, 0.282] | 0.179 [0.090, 0.277] | 0.008 [-0.000, 0.017] |
| vendi | bge_m3 | 605 | 0.335 [0.260, 0.414] | 0.320 [0.244, 0.400] | 0.015 [0.004, 0.025] |
| vendi | nomic_v15 | 605 | 0.375 [0.280, 0.468] | 0.326 [0.233, 0.419] | 0.048 [0.036, 0.060] |
| H_bt | specter2_proximity | 605 | 0.137 [0.104, 0.172] | 0.128 [0.092, 0.163] | 0.009 [-0.002, 0.020] |
| H_bt | qwen3_0p6b | 605 | 0.071 [0.039, 0.105] | 0.055 [0.022, 0.089] | 0.016 [0.000, 0.032] |
| H_km | specter2_proximity | 605 | 0.116 [0.082, 0.150] | 0.119 [0.086, 0.154] | -0.004 [-0.015, 0.009] |
| H_km | specter2_base | 605 | 0.107 [0.073, 0.143] | 0.106 [0.070, 0.142] | 0.001 [-0.011, 0.013] |
| H_km | scincl | 605 | 0.117 [0.081, 0.154] | 0.109 [0.073, 0.145] | 0.008 [-0.005, 0.020] |
| H_km | qwen3_0p6b | 605 | 0.093 [0.059, 0.132] | 0.066 [0.032, 0.106] | 0.027 [0.010, 0.044] |
| H_km | gte_qwen2_1p5b | 605 | 0.114 [0.079, 0.152] | 0.109 [0.074, 0.146] | 0.005 [-0.005, 0.016] |
| H_km | bge_m3 | 605 | 0.105 [0.070, 0.140] | 0.096 [0.063, 0.130] | 0.009 [-0.004, 0.022] |
| H_km | nomic_v15 | 605 | 0.102 [0.068, 0.139] | 0.109 [0.075, 0.145] | -0.008 [-0.021, 0.005] |
| dispersion | specter2_proximity | 605 | 0.005 [0.002, 0.008] | 0.005 [0.002, 0.008] | -0.001 [-0.001, -0.000] |
| dispersion | specter2_base | 605 | -0.000 [-0.003, 0.003] | 0.001 [-0.002, 0.005] | -0.002 [-0.002, -0.001] |
| dispersion | scincl | 605 | 0.008 [0.005, 0.012] | 0.008 [0.005, 0.012] | 0.000 [-0.000, 0.000] |
| dispersion | qwen3_0p6b | 605 | 0.004 [0.002, 0.006] | 0.004 [0.002, 0.006] | -0.000 [-0.001, 0.000] |
| dispersion | gte_qwen2_1p5b | 605 | 0.005 [0.003, 0.007] | 0.005 [0.003, 0.007] | 0.000 [-0.000, 0.000] |
| dispersion | bge_m3 | 605 | 0.006 [0.005, 0.007] | 0.006 [0.004, 0.007] | 0.000 [0.000, 0.000] |
| dispersion | nomic_v15 | 605 | 0.008 [0.006, 0.010] | 0.007 [0.005, 0.010] | 0.001 [0.001, 0.001] |

### Novelty (1 - mean cosine to the 5 nearest papers of the previous k years, size-matched pool), all papers, paired per paper

| k | model | original post - pre | all-AI post - pre | gap |
|---|---|---|---|---|
| 1 | specter2_proximity | -0.0109 [-0.0135, -0.0077] | -0.0077 [-0.0103, -0.0047] | -0.0032 [-0.0035, -0.0028] |
| 1 | specter2_base | -0.0236 [-0.0262, -0.0206] | -0.0186 [-0.0211, -0.0158] | -0.0050 [-0.0054, -0.0047] |
| 1 | scincl | 0.0026 [-0.0000, 0.0053] | 0.0033 [0.0006, 0.0060] | -0.0007 [-0.0009, -0.0004] |
| 1 | qwen3_0p6b | -0.0025 [-0.0052, 0.0000] | -0.0013 [-0.0039, 0.0012] | -0.0012 [-0.0017, -0.0007] |
| 1 | gte_qwen2_1p5b | -0.0063 [-0.0091, -0.0034] | -0.0057 [-0.0086, -0.0028] | -0.0005 [-0.0007, -0.0003] |
| 1 | bge_m3 | 0.0038 [0.0020, 0.0056] | 0.0038 [0.0020, 0.0057] | -0.0001 [-0.0003, 0.0002] |
| 1 | nomic_v15 | 0.0042 [0.0017, 0.0065] | 0.0018 [-0.0007, 0.0042] | 0.0024 [0.0020, 0.0027] |
| 3 | specter2_proximity | -0.0093 [-0.0119, -0.0064] | -0.0065 [-0.0091, -0.0036] | -0.0028 [-0.0031, -0.0025] |
| 3 | specter2_base | -0.0217 [-0.0243, -0.0187] | -0.0169 [-0.0195, -0.0141] | -0.0048 [-0.0050, -0.0044] |
| 3 | scincl | 0.0036 [0.0008, 0.0065] | 0.0042 [0.0014, 0.0071] | -0.0006 [-0.0009, -0.0004] |
| 3 | qwen3_0p6b | 0.0010 [-0.0015, 0.0036] | 0.0007 [-0.0016, 0.0031] | 0.0002 [-0.0003, 0.0008] |
| 3 | gte_qwen2_1p5b | -0.0042 [-0.0071, -0.0014] | -0.0040 [-0.0070, -0.0011] | -0.0002 [-0.0004, 0.0000] |
| 3 | bge_m3 | 0.0051 [0.0032, 0.0068] | 0.0052 [0.0033, 0.0069] | -0.0001 [-0.0003, 0.0002] |
| 3 | nomic_v15 | 0.0060 [0.0033, 0.0084] | 0.0038 [0.0010, 0.0063] | 0.0022 [0.0019, 0.0025] |
| 5 | specter2_proximity | -0.0073 [-0.0097, -0.0046] | -0.0046 [-0.0071, -0.0019] | -0.0027 [-0.0030, -0.0024] |
| 5 | specter2_base | -0.0191 [-0.0216, -0.0164] | -0.0146 [-0.0170, -0.0120] | -0.0045 [-0.0048, -0.0042] |
| 5 | scincl | 0.0051 [0.0024, 0.0078] | 0.0058 [0.0030, 0.0084] | -0.0007 [-0.0009, -0.0004] |
| 5 | qwen3_0p6b | 0.0041 [0.0015, 0.0064] | 0.0031 [0.0007, 0.0054] | 0.0010 [0.0005, 0.0016] |
| 5 | gte_qwen2_1p5b | -0.0012 [-0.0039, 0.0012] | -0.0015 [-0.0042, 0.0010] | 0.0003 [0.0001, 0.0005] |
| 5 | bge_m3 | 0.0068 [0.0049, 0.0084] | 0.0070 [0.0051, 0.0086] | -0.0002 [-0.0004, 0.0000] |
| 5 | nomic_v15 | 0.0074 [0.0046, 0.0097] | 0.0053 [0.0026, 0.0077] | 0.0020 [0.0017, 0.0023] |

### Per school, specter2_proximity, 500-paper draws

| school | measure | original post - pre | all-AI post - pre | gap |
|---|---|---|---|---|
| princeton | vendi | -0.36 [-6.22, 5.51] | -0.17 [-5.89, 5.55] | -0.18 [-0.49, 0.12] |
| princeton | H_bt | 0.18 [-0.17, 0.53] | 0.13 [-0.23, 0.48] | 0.05 [0.01, 0.10] |
| cmu | vendi | -9.60 [-11.97, -7.24] | -8.71 [-11.02, -6.40] | -0.90 [-1.15, -0.64] |
| cmu | H_bt | -0.17 [-0.27, -0.08] | -0.17 [-0.28, -0.06] | -0.00 [-0.04, 0.04] |
| epfl | vendi | -0.29 [-2.78, 2.19] | 0.12 [-2.25, 2.49] | -0.42 [-0.73, -0.11] |
| epfl | H_bt | 0.15 [0.01, 0.29] | 0.15 [0.01, 0.30] | -0.00 [-0.03, 0.03] |
| mit | vendi | -5.65 [-7.43, -3.88] | -4.65 [-6.44, -2.85] | -1.01 [-1.28, -0.73] |
| mit | H_bt | -0.09 [-0.19, 0.02] | -0.10 [-0.21, 0.01] | 0.01 [-0.02, 0.04] |
| berkeley | vendi | -5.41 [-8.51, -2.31] | -4.54 [-7.69, -1.39] | -0.87 [-1.10, -0.64] |
| berkeley | H_bt | 0.05 [-0.10, 0.20] | 0.06 [-0.07, 0.20] | -0.01 [-0.05, 0.02] |
| stanford | vendi | -9.23 [-12.19, -6.27] | -8.22 [-11.20, -5.24] | -1.01 [-1.26, -0.76] |
| stanford | H_bt | -0.20 [-0.32, -0.07] | -0.18 [-0.31, -0.05] | -0.01 [-0.04, 0.01] |
| michigan | vendi | -3.46 [-6.80, -0.11] | -2.54 [-5.76, 0.67] | -0.91 [-1.25, -0.58] |
| michigan | H_bt | 0.07 [-0.08, 0.21] | 0.04 [-0.10, 0.19] | 0.02 [-0.01, 0.06] |

The school-level changes of the original corpus (CMU and Stanford down, EPFL and Princeton up in topic entropy; the same pattern as the embeddings report) are reproduced almost exactly by the all-AI corpus. The Vendi gaps are -0.9 to -1.0 for every large school, about 10% of those schools' decline.

### Robustness: the paraphrase style, and polish on the same papers

The paraphrase style was run on 3,986 kept papers of a 4,996-paper stratified subsample; polish is repeated on the same papers. Draw sizes are smaller (250 papers for all; 60 per school-year; 8 per lab-period), so intervals are wider.

| rewrite | measure | model | original post - pre | rewrite post - pre | gap |
|---|---|---|---|---|---|
| paraphrase | vendi | specter2_proximity | -4.01 [-5.59, -2.44] | -2.91 [-4.41, -1.40] | -1.11 [-1.42, -0.80] |
| paraphrase | vendi | qwen3_0p6b | -2.84 [-6.58, 0.90] | -1.57 [-5.33, 2.20] | -1.27 [-1.69, -0.86] |
| paraphrase | vendi | nomic_v15 | -0.26 [-3.03, 2.51] | -0.73 [-3.62, 2.15] | 0.47 [0.14, 0.81] |
| paraphrase | H_bt | specter2_proximity | -0.13 [-0.21, -0.04] | -0.13 [-0.22, -0.05] | 0.01 [-0.02, 0.03] |
| paraphrase | H_bt | qwen3_0p6b | -0.11 [-0.22, -0.01] | -0.11 [-0.21, -0.01] | -0.00 [-0.04, 0.04] |
| paraphrase | H_km | specter2_proximity | -0.02 [-0.11, 0.06] | -0.04 [-0.11, 0.04] | 0.01 [-0.02, 0.05] |
| paraphrase | H_km | qwen3_0p6b | -0.07 [-0.17, 0.04] | -0.13 [-0.23, -0.03] | 0.06 [0.02, 0.10] |
| paraphrase | H_km | nomic_v15 | -0.03 [-0.11, 0.05] | -0.04 [-0.12, 0.04] | 0.01 [-0.03, 0.04] |
| polish-sub | vendi | specter2_proximity | -3.79 [-5.66, -1.93] | -3.05 [-4.82, -1.28] | -0.74 [-1.00, -0.48] |
| polish-sub | vendi | qwen3_0p6b | -2.83 [-6.74, 1.09] | -1.46 [-5.23, 2.31] | -1.36 [-2.04, -0.69] |
| polish-sub | vendi | nomic_v15 | -0.11 [-2.78, 2.56] | -0.51 [-3.16, 2.14] | 0.40 [0.08, 0.72] |
| polish-sub | H_bt | specter2_proximity | -0.12 [-0.21, -0.02] | -0.10 [-0.20, -0.01] | -0.01 [-0.04, 0.01] |
| polish-sub | H_bt | qwen3_0p6b | -0.11 [-0.21, -0.01] | -0.11 [-0.21, -0.02] | 0.01 [-0.03, 0.04] |
| polish-sub | H_km | specter2_proximity | -0.05 [-0.13, 0.03] | -0.04 [-0.13, 0.05] | -0.01 [-0.04, 0.02] |
| polish-sub | H_km | qwen3_0p6b | -0.10 [-0.19, -0.01] | -0.15 [-0.23, -0.07] | 0.05 [0.01, 0.10] |
| polish-sub | H_km | nomic_v15 | -0.04 [-0.12, 0.04] | -0.04 [-0.12, 0.04] | 0.00 [-0.02, 0.03] |

Paraphrase and polish give the same picture on the same papers: topic-entropy gaps about 0 except Qwen3-0.6B k-means (+0.05 to +0.06, as in the full run), Vendi gaps with the same signs and sizes (specter2_proximity -1.1 against -0.7, Qwen3 -1.3 against -1.4, Nomic +0.5 against +0.4). The wording effect is a property of the embedding model more than of the rewrite style.

## Reading it

1. Holding the wording constant does not remove the post-2022 change in topic spread: where the original corpus shows a fall (all papers, CMU, Stanford, SPECTER2 novelty), the all-AI corpus shows it too, at 70-100% of the size. The change is mostly in what papers are about.
2. The wording-attributable part is measurable but small and not one-signed across models: it is the gap column, mostly within +-0.06 bits of entropy, 1-3 Vendi points of 7-12 (SPECTER2), and 0.002-0.005 of novelty.
3. Rewriting itself homogenises a little (Vendi 1-3% lower, same entropy), which is the expected cost of making every abstract come from one model.

## Caveats

- One rewriting model, one prompt (plus a paraphrase check on 4,996 papers). A different model could shorten or lengthen abstracts differently; length shrinks by 8% here.
- Titles stay human-written and are embedded with the rewrite; the 87% of papers that pass the preservation filter are not a random 87% (abstracts with many numbers or acronyms fail more often, which is why the filter step is applied to both corpora).
- Pairwise cosine distance on centred vectors is 0.98-1.00 in every set and carries almost no signal; Vendi, dispersion and topic entropy are the informative measures. Intervals use 40 bootstrap replicates for the yearly series; interval widths are approximate. Entropy at m = 1,000 papers differs from the embeddings report's m = 2,000.
- 2026 is a partial year. Qwen3-Embedding-4B is not included (no original container to compare). The year-level "post minus pre" of all papers is negative for entropy while the lab-level change is positive: these are different populations (all papers in one pool against labs with at least 20 papers in each period).

## Compute

Rewrite 8.3 GPU-hours on A5000 (3 shards; includes the 300-paper test and the paraphrase run), embeddings 1.3 GPU-hours, detector 0.3 GPU-hours: about 9.9 GPU-hours, all on node105 or another A5000 node; plus CPU jobs for the merge and analyses and one CPU model download. Jobs: rewrite chains 32105618-32105652 (polish), 32107841 (paraphrase); embeddings 32107850-32107886, 32108167-32108171; detector 32107888, 32108172; analyses 32108284-32108296, 32108382-32108390.
