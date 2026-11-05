# What if every paper were AI-written? Diversity and novelty on rewritten abstracts

Generated 2026-11-05 by `ai-writing/allai/` (code: `rewrite.py`, `build_texts.py`, `preserve.py`, `allai_analyze.py`, `site_data.py`, `report_build.py`; tables: `ai-writing/data/embeddings/allai/results/`, git-ignored). Site data: `ai-writing/diversity/site-data/all-ai/` (README there). **Years 2016-2025 only: 2026 is a partial year and is left out of every series and trend; post = 2023-2025.**

## Answer

- **Holding the wording constant leaves the post-2022 changes in place, at nearly the same size.** All papers, specter2_proximity, 1,000-paper draws, 2023-2025 minus 2016-2022: the Vendi score (effectively distinct papers) changes by -6.10 [-7.61, -4.58] in the original corpus and -5.15 [-6.63, -3.67] when every abstract is AI-worded; the gap (original minus AI, the part due to wording) is -0.94 [-1.18, -0.71], about 15% of the Vendi fall, the rest is content. Topic entropy over BERTopic topics changes by -0.038 [-0.101, 0.025] bits (original) and -0.040 [-0.102, 0.021] (all-AI), gap 0.002 [-0.022, 0.026]: for all papers pooled, the topic-spread change after 2022 is small and its interval includes 0 in both corpora.
- **The wording share is small and depends on the embedding model.** k-means entropy gap about 0 for 6 of 7 models (Qwen3-0.6B: 0.071 [0.047, 0.094], the AI corpus falls more). Vendi gap negative for the SPECTER2 pair and Qwen3-0.6B, positive for Nomic (+1.0), about 0 for SciNCL, GTE-Qwen2 and BGE-M3. Novelty (k = 3, 1 - mean of 5 nearest): SPECTER2's fall after 2022 is -0.0089 [-0.0118, -0.0063] in the original and -0.0065 [-0.0094, -0.0039] in the all-AI corpus (gap -0.0024 [-0.0027, -0.0021], about 27%); the other models' gaps are within 0.002.
- **Levels differ a little, trends hardly.** Rewriting makes the corpus slightly more uniform: Vendi 1-3% lower in the all-AI corpus (specter2_proximity 97.2 -> 94.4 in 2016), topic entropy unchanged.
- **Lab level** (495 labs with >= 20 papers in both periods, 20-paper draws): entropy over topics rises in both corpora, 0.095 [0.054, 0.137] (original) and 0.093 [0.050, 0.134] (all-AI) bits for BERTopic topics (specter2_proximity), 0.045 [0.006, 0.086] and 0.043 [0.005, 0.085] for k-means; the gaps are 0.003 [-0.010, 0.015] and 0.001 [-0.013, 0.015].

## Method

- **Corpus.** The embeddings universe: 112,260 abstracts (`oa_fields`/`texts.sqlite`), keyed by atlas paper id. **The title stays as written (human text) and is embedded with the rewrite; only abstracts are rewritten.**
- **Rewrite.** Qwen/Qwen2.5-7B-Instruct, revision `a09a35458c702b33eeacc393d103063234e8bc28` (it was not in the HF cache; fetched by job 32105407), vLLM 0.8.3, bf16, greedy decoding (temperature 0, seed 20261104), max new tokens min(1500, 1.5 x source tokens + 100), sources over 1,800 tokens skipped. One fixed prompt, system prompt "You are a helpful assistant.": *Here is the abstract of a research paper titled "{title}". Rewrite it as a polished academic abstract: improve its clarity, flow and academic style. Keep every claim, number, method name and technical term exactly as given; do not add or drop any information. Keep roughly the same length (about {n} words). Return only the rewritten abstract, as plain text in a single paragraph.* (the detector's "polish" task, written for abstracts). Output cleaning is detector_v2's `clean`. Container: `allai/rewrites_polish.sqlite` (paper id, text, ok, why, hashes, meta with model, revision, prompt, parameters); resumable per-shard sqlite files, 3 shards, 59-minute task chains on node105 A5000s.
- **Second style.** Paraphrase ("in your own words", numbers and named methods kept) on 4,996 papers stratified by home school and year, same model and parameters.
- **Embeddings.** The same seven models as the originals (SPECTER2 base and proximity, SciNCL, Qwen3-0.6B, GTE-Qwen2-1.5B, BGE-M3, Nomic v1.5), `embed.py --texts-db ... --store-name <model>__allai` (`__para`; `__allaix` for the rewrites the filter dropped), so originals and rewrites never share a container. Qwen3-Embedding-4B is not run: its original-abstract container does not exist yet, so there is nothing to compare against; to be added after it exists.
- **Measures** (`allai_analyze.py`). Each corpus is centred on its own mean and normalised. Dispersion (mean distance from the centroid), mean pairwise cosine distance, Vendi score, topic entropy over **fixed clusters defined on the originals** (BERTopic topics of `topics.py`, specter2_proximity and qwen3_0p6b: a paper goes to the nearest topic centroid in both corpora; and 100 k-means clusters, every model), novelty k = 1, 3, 5 (`novelty.py`, nearest-5 and max cosine, pool capped at 2,000). Size-matched paired draws: all papers 1,000, a school-year 500, a lab-period 20 papers (novelty as in the embeddings report). Intervals: bootstrap over labs (a paper's first lab) with replacement, **240 replicates** for the all-paper, school and trend intervals, estimate +- 1.96 sd (resampling labs repeats papers, which lowers every resampled diversity, so percentiles would not bracket the estimate); the original-minus-AI gap is paired (same papers drawn from both), so its interval is narrow. Lab changes: 1,000 bootstrap resamples of labs; novelty: `mean_by_year` (200 replicates) and `diff_ci` (500). The robustness runs (paraphrase, polish on the same papers) use 40 replicates.
- **Same papers in both corpora.** Both corpora are restricted to the papers whose rewrite passed the filter below (97,940 of 112,260 with a year of 2016-2025: the counts below are for all 112,260; the analyses drop 2026).

## Content preservation

Polish style, all 112,260 abstracts: 112,187 rewrites passed the basic checks (not cut at the token limit, not a refusal, at least 40% of the source's words); the failures are 44 much shorter than the source, 22 sources over 1,800 tokens (not rewritten), 6 truncated, 1 refusal. The rewrite is 8% shorter than its source (median length ratio 0.916).

**Automatic number and named-method check** (`preserve.py`: numeric tokens; named methods = acronyms, CamelCase and names with digits such as BERT, ResNet-50, LoRA; matching ignores case, hyphens and spaces):

| check | share of rewrites |
|---|---|
| lose at least one number of the source (abstracts with numbers: 55,149) | 10.0% of all abstracts; 11.5% of all numbers |
| add a number that is not in the source | 4.7% |
| lose at least one named method (abstracts with terms: 84,222) | 7.6%; 4.5% of all terms |

**Filter** (`build_texts.py`): drop a rewrite that fails the basic checks, loses 25% or more of the source's numbers, adds more new numbers than a quarter of the source's (at least 1), or loses 25% or more of its named methods. This removes 14,320 rewrites (12.8%): numbers lost 9,200, named methods lost 4,156, numbers added 891, and the basic failures above. **Kept: 97,940 papers.** Failures were not regenerated: the filter is applied to both corpora, so the comparison is on the same papers.

**Kept vs dropped papers differ.** Among the ok rewrites (2016-2025) 12.9% were dropped. By school the dropped share is 10.8% (EPFL) to 13.8% (CMU); by year 11.9% to 13.8% with no trend; by OpenAlex field it is highest in Medicine (17.5%), Environmental Science (17.3%) and Materials Science (17.2%) and lowest in Decision Sciences (9.3%), Business (9.5%) and Economics (9.5%); Computer Science (13.1%) and Engineering (12.0%) are close to the overall rate. The strongest driver is content: abstracts with numbers lose 22.6% against 3.9% without; with named methods 14.8% against 7.5%; dropped sources are longer (mean 181 against 170 words).

| school | papers | dropped | vs overall |
|---|---|---|---|
| berkeley | 10176 | 11.6% | -1.2% |
| cmu | 18936 | 13.8% | +0.9% |
| epfl | 9948 | 10.8% | -2.1% |
| gatech | 15903 | 13.4% | +0.6% |
| michigan | 9394 | 13.5% | +0.6% |
| mit | 14710 | 12.9% | +0.0% |
| princeton | 6645 | 11.7% | -1.2% |
| stanford | 12876 | 13.4% | +0.5% |
| uchicago | 3302 | 13.5% | +0.6% |

| year | papers | dropped |
|---|---|---|
| 2016 | 7750 | 12.8% |
| 2017 | 8429 | 11.9% |
| 2018 | 9488 | 12.1% |
| 2019 | 9685 | 12.8% |
| 2020 | 10403 | 12.4% |
| 2021 | 11042 | 13.8% |
| 2022 | 10051 | 13.5% |
| 2023 | 11051 | 13.4% |
| 2024 | 11696 | 13.4% |
| 2025 | 12295 | 12.5% |

| field | papers | dropped | vs overall |
|---|---|---|---|
| Medicine | 3883 | 17.5% | +4.6% |
| Environmental Science | 854 | 17.3% | +4.5% |
| Materials Science | 906 | 17.2% | +4.3% |
| Health Professions | 642 | 14.5% | +1.6% |
| Psychology | 2203 | 14.1% | +1.2% |
| Neuroscience | 3029 | 14.0% | +1.1% |
| Social Sciences | 3805 | 13.8% | +0.9% |
| Computer Science | 46330 | 13.1% | +0.3% |
| Physics and Astronomy | 2862 | 12.3% | -0.6% |
| Engineering | 24015 | 12.0% | -0.9% |
| Biochemistry, Genetics and Molecular Biology | 3252 | 11.4% | -1.4% |
| Mathematics | 3923 | 10.8% | -2.1% |
| Economics, Econometrics and Finance | 769 | 9.5% | -3.4% |
| Business, Management and Accounting | 866 | 9.5% | -3.4% |
| Decision Sciences | 2896 | 9.3% | -3.6% |

| abstracts | papers | dropped |
|---|---|---|
| has numbers | 49149 | 22.6% |
| no numbers | 52741 | 3.9% |
| has named methods | 75582 | 14.8% |
| no named methods | 26308 | 7.5% |

**The headline does not depend on the filter.** Re-running the all-papers change on all 112,187 ok rewrites (the 14,247 dropped ones embedded into `<model>__allaix` and added back), three models, 120 bootstrap replicates:

| measure | model | filtered: original | filtered: all-AI | filtered: gap | unfiltered: original | unfiltered: all-AI | unfiltered: gap |
|---|---|---|---|---|---|---|---|
| vendi | specter2_proximity | -6.10 [-7.61, -4.58] | -5.15 [-6.63, -3.67] | -0.94 [-1.18, -0.71] | -6.55 [-8.03, -5.07] | -5.59 [-7.05, -4.13] | -0.96 [-1.21, -0.71] |
| H_bt | specter2_proximity | -0.04 [-0.10, 0.02] | -0.04 [-0.10, 0.02] | 0.00 [-0.02, 0.03] | -0.05 [-0.11, 0.00] | -0.06 [-0.12, 0.00] | 0.00 [-0.02, 0.02] |
| H_km | specter2_proximity | -0.03 [-0.08, 0.02] | -0.03 [-0.08, 0.02] | 0.00 [-0.01, 0.01] | -0.01 [-0.05, 0.03] | -0.02 [-0.06, 0.03] | 0.00 [-0.01, 0.02] |
| vendi | qwen3_0p6b | -6.23 [-9.31, -3.16] | -3.63 [-6.57, -0.69] | -2.60 [-3.52, -1.68] | -7.13 [-9.96, -4.30] | -4.38 [-7.15, -1.60] | -2.75 [-3.84, -1.66] |
| H_bt | qwen3_0p6b | -0.04 [-0.11, 0.02] | -0.09 [-0.16, -0.03] | 0.05 [0.02, 0.08] | -0.05 [-0.11, 0.01] | -0.11 [-0.16, -0.05] | 0.05 [0.02, 0.08] |
| H_km | qwen3_0p6b | -0.01 [-0.05, 0.04] | -0.08 [-0.13, -0.03] | 0.07 [0.05, 0.09] | -0.05 [-0.09, -0.00] | -0.12 [-0.18, -0.07] | 0.08 [0.05, 0.10] |
| vendi | nomic_v15 | 0.09 [-1.75, 1.93] | -0.92 [-2.77, 0.93] | 1.01 [0.60, 1.43] | -0.30 [-2.10, 1.51] | -1.38 [-3.25, 0.50] | 1.08 [0.61, 1.55] |
| H_km | nomic_v15 | -0.01 [-0.05, 0.04] | -0.01 [-0.06, 0.04] | 0.01 [-0.01, 0.02] | -0.02 [-0.06, 0.02] | -0.02 [-0.06, 0.02] | 0.00 [-0.01, 0.02] |

The unfiltered gaps equal the filtered ones within their intervals (specter2_proximity Vendi gap -0.96 against -0.94; Qwen3-0.6B k-means entropy +0.08 against +0.07).

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

**Hand read, 20 random kept polish rewrites** (seed 20261104). No change of claim, number or method in any. Four small drifts: "Kalman filter" became "Kalman-Bucy filter"; "Milano" became "Milan"; two rewrites added a mild evaluative phrase ("more accurate and reliable", "to enhance user experience"). No rewrite dropped a result or reversed a finding.

**AI detector: the v1 abstract detector** (`ai-writing/detector.py`, ModernBERT-large on `title | abstract`, threshold at 1% false positives on validation human abstracts; the v2 paragraph detector is not used on abstracts because it flags 11-16% of pre-2022 abstracts). Years 2016-2025. **96.5% of the 101,890 rewrites are flagged** (96.3% for papers of 2016-2022, 97.0% for 2023-2025). The original abstracts of the same papers: 10.5% overall, **3.6% for 2016-2022 and 23.8% for 2023-2025**. On the kept papers only: originals 10.1%, rewrites 96.5%. Paraphrase rewrites: 96.9% flagged (originals of the subsample 10.5%).

## Results

All tables: 2023-2025 minus 2016-2022 (novelty 2017-2022), 95% intervals. Negative gap = the original fell more (or rose less) than the all-AI corpus.

### Levels, original / all-AI, all papers (size-matched 1,000-paper draws)

| measure | model | 2016 | 2019 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| vendi | specter2_proximity | 97.16 / 94.37 | 94.62 / 92.30 | 93.75 / 91.87 | 89.35 / 87.94 | 86.20 / 85.22 |
| vendi | qwen3_0p6b | 217.25 / 213.33 | 217.22 / 212.68 | 218.38 / 214.26 | 212.20 / 209.55 | 204.11 / 206.22 |
| vendi | bge_m3 | 240.33 / 239.53 | 242.94 / 241.97 | 244.85 / 244.07 | 242.17 / 241.20 | 240.31 / 239.70 |
| H_bt | specter2_proximity | 7.66 / 7.66 | 7.76 / 7.76 | 7.75 / 7.75 | 7.71 / 7.70 | 7.64 / 7.63 |
| H_bt | qwen3_0p6b | 7.86 / 7.89 | 8.00 / 7.99 | 7.98 / 7.99 | 7.92 / 7.87 | 7.85 / 7.80 |
| H_km | specter2_proximity | 6.38 / 6.39 | 6.49 / 6.49 | 6.51 / 6.51 | 6.44 / 6.44 | 6.38 / 6.38 |
| H_km | qwen3_0p6b | 6.34 / 6.36 | 6.46 / 6.46 | 6.51 / 6.50 | 6.44 / 6.38 | 6.38 / 6.30 |
| H_km | bge_m3 | 6.39 / 6.39 | 6.47 / 6.47 | 6.50 / 6.49 | 6.38 / 6.37 | 6.27 / 6.26 |

### Change after 2022, all papers

| measure | model | original post - pre | all-AI post - pre | gap (orig - AI) |
|---|---|---|---|---|
| vendi | specter2_proximity | -6.095 [-7.609, -4.581] | -5.150 [-6.628, -3.672] | -0.945 [-1.178, -0.711] |
| vendi | specter2_base | -9.628 [-11.038, -8.219] | -7.940 [-9.279, -6.600] | -1.689 [-1.925, -1.452] |
| vendi | scincl | -2.261 [-3.580, -0.941] | -2.121 [-3.438, -0.803] | -0.140 [-0.309, 0.029] |
| vendi | qwen3_0p6b | -6.235 [-9.310, -3.159] | -3.632 [-6.573, -0.691] | -2.602 [-3.524, -1.681] |
| vendi | gte_qwen2_1p5b | -10.472 [-14.580, -6.364] | -10.386 [-14.509, -6.263] | -0.086 [-0.575, 0.404] |
| vendi | bge_m3 | -0.443 [-2.507, 1.620] | -0.406 [-2.504, 1.691] | -0.037 [-0.454, 0.380] |
| vendi | nomic_v15 | 0.090 [-1.751, 1.932] | -0.922 [-2.772, 0.929] | 1.012 [0.597, 1.427] |
| H_bt | specter2_proximity | -0.038 [-0.101, 0.025] | -0.040 [-0.102, 0.021] | 0.002 [-0.022, 0.026] |
| H_bt | qwen3_0p6b | -0.042 [-0.108, 0.024] | -0.093 [-0.160, -0.026] | 0.051 [0.019, 0.084] |
| H_km | specter2_proximity | -0.033 [-0.082, 0.017] | -0.033 [-0.082, 0.016] | 0.000 [-0.013, 0.014] |
| H_km | specter2_base | 0.000 [-0.046, 0.047] | 0.002 [-0.044, 0.048] | -0.001 [-0.014, 0.011] |
| H_km | scincl | -0.008 [-0.055, 0.038] | -0.006 [-0.051, 0.040] | -0.003 [-0.015, 0.010] |
| H_km | qwen3_0p6b | -0.008 [-0.055, 0.038] | -0.079 [-0.131, -0.027] | 0.071 [0.047, 0.094] |
| H_km | gte_qwen2_1p5b | -0.049 [-0.098, -0.000] | -0.055 [-0.105, -0.005] | 0.006 [-0.006, 0.018] |
| H_km | bge_m3 | -0.085 [-0.135, -0.035] | -0.093 [-0.143, -0.042] | 0.008 [-0.008, 0.024] |
| H_km | nomic_v15 | -0.006 [-0.051, 0.039] | -0.012 [-0.060, 0.036] | 0.006 [-0.010, 0.022] |
| dispersion | specter2_proximity | -0.002 [-0.004, -0.000] | -0.002 [-0.004, 0.000] | -0.000 [-0.000, -0.000] |
| dispersion | specter2_base | -0.002 [-0.004, -0.000] | -0.002 [-0.004, 0.000] | -0.000 [-0.000, -0.000] |
| dispersion | scincl | -0.002 [-0.003, 0.000] | -0.001 [-0.003, 0.000] | -0.000 [-0.000, -0.000] |
| dispersion | qwen3_0p6b | -0.002 [-0.003, -0.001] | -0.001 [-0.002, -0.000] | -0.001 [-0.002, -0.001] |
| dispersion | gte_qwen2_1p5b | -0.001 [-0.003, 0.000] | -0.001 [-0.002, 0.000] | -0.000 [-0.000, -0.000] |
| dispersion | bge_m3 | -0.001 [-0.001, -0.000] | -0.001 [-0.001, -0.000] | -0.000 [-0.000, 0.000] |
| dispersion | nomic_v15 | -0.001 [-0.002, 0.000] | -0.001 [-0.002, 0.000] | -0.000 [-0.000, 0.000] |

### Change after 2022, per lab (labs with >= 20 papers in both periods; 20-paper draws; mean over labs)

| measure | model | labs | original post - pre | all-AI post - pre | gap |
|---|---|---|---|---|---|
| vendi | specter2_proximity | 495 | -0.064 [-0.171, 0.041] | -0.030 [-0.134, 0.075] | -0.034 [-0.047, -0.020] |
| vendi | specter2_base | 495 | -0.247 [-0.355, -0.134] | -0.178 [-0.283, -0.066] | -0.070 [-0.082, -0.057] |
| vendi | scincl | 495 | 0.154 [0.047, 0.268] | 0.154 [0.048, 0.267] | -0.001 [-0.012, 0.011] |
| vendi | qwen3_0p6b | 495 | 0.080 [-0.030, 0.187] | 0.075 [-0.035, 0.185] | 0.004 [-0.022, 0.030] |
| vendi | gte_qwen2_1p5b | 495 | 0.037 [-0.075, 0.145] | 0.031 [-0.082, 0.142] | 0.006 [-0.003, 0.016] |
| vendi | bge_m3 | 495 | 0.156 [0.069, 0.252] | 0.148 [0.060, 0.243] | 0.008 [-0.003, 0.021] |
| vendi | nomic_v15 | 495 | 0.222 [0.116, 0.328] | 0.177 [0.068, 0.290] | 0.045 [0.030, 0.059] |
| H_bt | specter2_proximity | 495 | 0.095 [0.054, 0.137] | 0.093 [0.050, 0.134] | 0.003 [-0.010, 0.015] |
| H_bt | qwen3_0p6b | 495 | 0.042 [0.005, 0.082] | 0.025 [-0.014, 0.063] | 0.017 [-0.001, 0.035] |
| H_km | specter2_proximity | 495 | 0.045 [0.006, 0.086] | 0.043 [0.005, 0.085] | 0.001 [-0.013, 0.015] |
| H_km | specter2_base | 495 | 0.044 [0.004, 0.082] | 0.040 [0.000, 0.081] | 0.004 [-0.007, 0.015] |
| H_km | scincl | 495 | 0.077 [0.040, 0.115] | 0.079 [0.041, 0.118] | -0.001 [-0.015, 0.011] |
| H_km | qwen3_0p6b | 495 | 0.060 [0.018, 0.102] | 0.026 [-0.016, 0.066] | 0.034 [0.014, 0.057] |
| H_km | gte_qwen2_1p5b | 495 | 0.068 [0.029, 0.110] | 0.065 [0.023, 0.106] | 0.003 [-0.006, 0.014] |
| H_km | bge_m3 | 495 | 0.020 [-0.014, 0.058] | 0.003 [-0.034, 0.042] | 0.017 [0.003, 0.032] |
| H_km | nomic_v15 | 495 | 0.038 [0.001, 0.074] | 0.031 [-0.005, 0.068] | 0.007 [-0.009, 0.021] |
| dispersion | specter2_proximity | 495 | 0.001 [-0.002, 0.004] | 0.001 [-0.002, 0.005] | -0.000 [-0.001, -0.000] |
| dispersion | specter2_base | 495 | -0.003 [-0.007, 0.000] | -0.002 [-0.005, 0.002] | -0.001 [-0.002, -0.001] |
| dispersion | scincl | 495 | 0.005 [0.001, 0.008] | 0.005 [0.001, 0.008] | 0.000 [-0.000, 0.000] |
| dispersion | qwen3_0p6b | 495 | 0.001 [-0.001, 0.004] | 0.002 [-0.001, 0.004] | -0.000 [-0.001, 0.000] |
| dispersion | gte_qwen2_1p5b | 495 | 0.002 [-0.000, 0.005] | 0.002 [-0.001, 0.005] | 0.000 [-0.000, 0.000] |
| dispersion | bge_m3 | 495 | 0.003 [0.002, 0.005] | 0.003 [0.002, 0.005] | 0.000 [0.000, 0.000] |
| dispersion | nomic_v15 | 495 | 0.005 [0.002, 0.008] | 0.004 [0.001, 0.007] | 0.001 [0.000, 0.001] |

### Novelty (1 - mean cosine to the 5 nearest papers of the previous k years, size-matched pool), all papers, paired per paper

| k | model | original post - pre | all-AI post - pre | gap |
|---|---|---|---|---|
| 1 | specter2_proximity | -0.0104 [-0.0130, -0.0078] | -0.0077 [-0.0103, -0.0051] | -0.0027 [-0.0030, -0.0024] |
| 1 | specter2_base | -0.0225 [-0.0257, -0.0195] | -0.0179 [-0.0209, -0.0150] | -0.0046 [-0.0050, -0.0043] |
| 1 | scincl | 0.0022 [-0.0008, 0.0049] | 0.0026 [-0.0002, 0.0054] | -0.0005 [-0.0007, -0.0002] |
| 1 | qwen3_0p6b | -0.0021 [-0.0051, 0.0004] | -0.0019 [-0.0049, 0.0006] | -0.0002 [-0.0007, 0.0003] |
| 1 | gte_qwen2_1p5b | -0.0062 [-0.0091, -0.0033] | -0.0058 [-0.0088, -0.0029] | -0.0004 [-0.0006, -0.0001] |
| 1 | bge_m3 | 0.0025 [0.0004, 0.0042] | 0.0026 [0.0006, 0.0044] | -0.0001 [-0.0003, 0.0002] |
| 1 | nomic_v15 | 0.0031 [0.0002, 0.0055] | 0.0010 [-0.0019, 0.0034] | 0.0021 [0.0017, 0.0024] |
| 3 | specter2_proximity | -0.0089 [-0.0118, -0.0063] | -0.0065 [-0.0094, -0.0039] | -0.0024 [-0.0027, -0.0021] |
| 3 | specter2_base | -0.0208 [-0.0242, -0.0179] | -0.0163 [-0.0194, -0.0134] | -0.0045 [-0.0048, -0.0042] |
| 3 | scincl | 0.0030 [-0.0002, 0.0059] | 0.0035 [0.0003, 0.0064] | -0.0005 [-0.0007, -0.0002] |
| 3 | qwen3_0p6b | 0.0011 [-0.0018, 0.0036] | -0.0000 [-0.0028, 0.0024] | 0.0011 [0.0006, 0.0017] |
| 3 | gte_qwen2_1p5b | -0.0043 [-0.0074, -0.0015] | -0.0042 [-0.0074, -0.0013] | -0.0001 [-0.0003, 0.0002] |
| 3 | bge_m3 | 0.0036 [0.0014, 0.0052] | 0.0038 [0.0015, 0.0054] | -0.0002 [-0.0004, 0.0001] |
| 3 | nomic_v15 | 0.0047 [0.0013, 0.0072] | 0.0027 [-0.0006, 0.0052] | 0.0020 [0.0016, 0.0023] |
| 5 | specter2_proximity | -0.0076 [-0.0103, -0.0051] | -0.0052 [-0.0080, -0.0027] | -0.0024 [-0.0027, -0.0021] |
| 5 | specter2_base | -0.0184 [-0.0217, -0.0156] | -0.0142 [-0.0173, -0.0115] | -0.0042 [-0.0046, -0.0039] |
| 5 | scincl | 0.0040 [0.0012, 0.0063] | 0.0045 [0.0018, 0.0069] | -0.0006 [-0.0008, -0.0003] |
| 5 | qwen3_0p6b | 0.0038 [0.0011, 0.0060] | 0.0020 [-0.0008, 0.0043] | 0.0017 [0.0012, 0.0023] |
| 5 | gte_qwen2_1p5b | -0.0012 [-0.0042, 0.0014] | -0.0016 [-0.0047, 0.0011] | 0.0004 [0.0002, 0.0006] |
| 5 | bge_m3 | 0.0053 [0.0031, 0.0069] | 0.0054 [0.0033, 0.0071] | -0.0002 [-0.0004, 0.0001] |
| 5 | nomic_v15 | 0.0057 [0.0027, 0.0082] | 0.0040 [0.0009, 0.0065] | 0.0017 [0.0014, 0.0020] |

### Per school, specter2_proximity, 500-paper draws

| school | measure | original post - pre | all-AI post - pre | gap |
|---|---|---|---|---|
| princeton | vendi | 0.32 [-4.72, 5.35] | 0.32 [-4.56, 5.20] | 0.00 [-0.35, 0.35] |
| princeton | H_bt | 0.20 [-0.13, 0.52] | 0.15 [-0.18, 0.48] | 0.04 [-0.01, 0.10] |
| cmu | vendi | -8.35 [-11.28, -5.41] | -7.67 [-10.59, -4.74] | -0.68 [-0.99, -0.38] |
| cmu | H_bt | -0.13 [-0.27, 0.02] | -0.12 [-0.26, 0.02] | -0.00 [-0.04, 0.03] |
| epfl | vendi | 0.12 [-2.78, 3.01] | 0.39 [-2.44, 3.23] | -0.28 [-0.60, 0.05] |
| epfl | H_bt | 0.18 [0.02, 0.33] | 0.17 [0.02, 0.33] | 0.00 [-0.04, 0.04] |
| mit | vendi | -4.67 [-6.67, -2.67] | -3.84 [-5.82, -1.86] | -0.83 [-1.12, -0.54] |
| mit | H_bt | -0.04 [-0.14, 0.06] | -0.04 [-0.14, 0.06] | 0.00 [-0.04, 0.04] |
| berkeley | vendi | -4.52 [-7.26, -1.77] | -3.77 [-6.54, -1.01] | -0.75 [-1.06, -0.43] |
| berkeley | H_bt | 0.12 [-0.02, 0.26] | 0.12 [-0.02, 0.26] | 0.00 [-0.04, 0.04] |
| stanford | vendi | -8.15 [-11.17, -5.12] | -7.29 [-10.27, -4.30] | -0.86 [-1.13, -0.59] |
| stanford | H_bt | -0.15 [-0.27, -0.03] | -0.12 [-0.24, 0.00] | -0.03 [-0.06, 0.01] |
| michigan | vendi | -3.01 [-5.76, -0.26] | -2.14 [-4.74, 0.46] | -0.87 [-1.23, -0.51] |
| michigan | H_bt | 0.08 [-0.06, 0.23] | 0.06 [-0.08, 0.20] | 0.02 [-0.02, 0.06] |

CMU and Stanford fall and EPFL, Princeton and Berkeley rise in topic entropy in both corpora, with the same signs and sizes. The Vendi gaps are -0.7 to -0.9 for the large schools, about 10% of their change.

### Robustness: the paraphrase style, and polish on the same papers

The paraphrase style was run on 3,986 kept papers of a 4,996-paper stratified subsample; polish is repeated on the same papers. Draw sizes are smaller (250 papers for all; 60 per school-year; 8 per lab-period) and 40 replicates are used, so the intervals are wider.

| rewrite | measure | model | original post - pre | rewrite post - pre | gap |
|---|---|---|---|---|---|
| paraphrase | vendi | specter2_proximity | -3.08 [-4.81, -1.35] | -2.33 [-4.01, -0.65] | -0.75 [-1.12, -0.38] |
| paraphrase | vendi | qwen3_0p6b | -1.99 [-5.86, 1.87] | -1.01 [-4.90, 2.88] | -0.99 [-1.54, -0.44] |
| paraphrase | vendi | nomic_v15 | -0.10 [-3.08, 2.88] | -0.74 [-3.61, 2.12] | 0.65 [0.27, 1.03] |
| paraphrase | H_bt | specter2_proximity | -0.07 [-0.16, 0.01] | -0.08 [-0.17, 0.01] | 0.01 [-0.03, 0.04] |
| paraphrase | H_bt | qwen3_0p6b | -0.06 [-0.17, 0.05] | -0.07 [-0.17, 0.03] | 0.01 [-0.02, 0.04] |
| paraphrase | H_km | specter2_proximity | 0.02 [-0.07, 0.10] | 0.00 [-0.09, 0.10] | 0.01 [-0.02, 0.05] |
| paraphrase | H_km | qwen3_0p6b | -0.08 [-0.17, 0.01] | -0.12 [-0.21, -0.02] | 0.04 [-0.01, 0.09] |
| paraphrase | H_km | nomic_v15 | -0.04 [-0.14, 0.06] | -0.02 [-0.12, 0.07] | -0.01 [-0.05, 0.02] |
| polish-sub | vendi | specter2_proximity | -2.88 [-5.13, -0.62] | -2.30 [-4.48, -0.12] | -0.58 [-0.92, -0.23] |
| polish-sub | vendi | qwen3_0p6b | -2.13 [-6.66, 2.40] | -0.87 [-5.24, 3.50] | -1.26 [-1.79, -0.72] |
| polish-sub | vendi | nomic_v15 | 0.10 [-3.25, 3.44] | -0.36 [-3.61, 2.89] | 0.45 [0.13, 0.78] |
| polish-sub | H_bt | specter2_proximity | -0.06 [-0.17, 0.05] | -0.03 [-0.14, 0.07] | -0.03 [-0.06, 0.00] |
| polish-sub | H_bt | qwen3_0p6b | -0.07 [-0.17, 0.03] | -0.09 [-0.19, 0.02] | 0.02 [-0.02, 0.05] |
| polish-sub | H_km | specter2_proximity | -0.04 [-0.12, 0.04] | -0.03 [-0.11, 0.05] | -0.01 [-0.04, 0.03] |
| polish-sub | H_km | qwen3_0p6b | -0.07 [-0.17, 0.02] | -0.11 [-0.21, -0.00] | 0.03 [-0.02, 0.09] |
| polish-sub | H_km | nomic_v15 | -0.02 [-0.12, 0.07] | -0.03 [-0.13, 0.08] | 0.00 [-0.04, 0.04] |

Paraphrase and polish give the same picture on the same papers: topic-entropy gaps about 0 except Qwen3-0.6B k-means, Vendi gaps with the same signs and similar sizes (specter2_proximity -0.75 against -0.58, Qwen3 -1.0 against -1.3, Nomic +0.65 against +0.45). The wording effect is a property of the embedding model more than of the rewrite style.

## Reading it

1. Holding the wording constant does not remove the post-2022 changes: the all-AI corpus shows the original's Vendi fall at about 85% of its size, SPECTER2's novelty fall at about 70%, and the same school pattern in topic entropy. The changes are mostly in what papers are about.
2. The wording-attributable part is measurable but small and not one-signed across models: it is the gap column, mostly within +-0.07 bits of entropy, 1-3 Vendi points (SPECTER2, Qwen3), and 0.002-0.005 of novelty.
3. Rewriting itself homogenises a little (Vendi 1-3% lower, same entropy), the expected cost of making every abstract come from one model.

## Caveats

- One rewriting model, one prompt (plus a paraphrase check on 4,996 papers). Length shrinks by 8%.
- Titles stay human-written and are embedded with the rewrite. The kept 87% are not a random 87% (see above); the unfiltered re-run gives the same gaps.
- Pairwise cosine distance on centred vectors is 0.98-1.00 in every set and carries almost no signal; Vendi, dispersion and topic entropy are the informative measures. Entropy at m = 1,000 papers differs from the embeddings report's m = 2,000.
- Qwen3-Embedding-4B is not included. The pooled all-paper change is negative for some measures while the lab-level change is positive: different populations (all papers in one pool against labs with at least 20 papers in each period).

## Compute

Rewrite 8.3 GPU-hours on A5000 (3 shards; includes the 300-paper test and the paraphrase run), embeddings about 1.5 GPU-hours (incl. the 14,247 dropped rewrites), detectors under 1 GPU-hour; about 10 GPU-hours, all on node105 or another A5000 node; plus CPU jobs for the merge and analyses and one CPU model download.
