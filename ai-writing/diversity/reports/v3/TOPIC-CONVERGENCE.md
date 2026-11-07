# Topic convergence between labs

Generated 2026-11-06T03:42:07Z by `ai-writing/labstudy/topic_report.py` (analysis `topic_convergence.py`); every number comes from the tables in `ai-writing/data/labstudy/topics` (git-ignored). **Years 2016-2025 only (no 2026); post = 2023-2025, 2022 is the transition year; intervals are 95% percentile intervals of a bootstrap over labs (300 replicates).** Strict lab membership (a lab owns a paper only when its PI is on the byline).

## Question and answer

**Do different labs' topic mixes become more alike over time, and faster after 2023?** Per lab-year we draw `m` = 10 papers (size-matched, 8 draws, labs with fewer papers carrying a topic drop out), form the topic distribution, smooth it toward the pooled mix (pseudo-count 1) and compare labs by Jensen-Shannon divergence (base 2, 0 = identical, 1 = disjoint).

- **BERTopic (Qwen3-0.6B embeddings)**: mean pairwise JSD 0.8719 (2016-21) to 0.8622 (2023-25); the post-2022 deviation from the 2016-21 trend is -0.0081 [-0.0117, -0.0046]; placebo breaks: 2019 -0.0029 [-0.0070, +0.0013], 2020 -0.0002 [-0.0029, +0.0027], 2021 -0.0013 [-0.0034, +0.0014]. Beyond the placebos: **yes**.
- **BERTopic (SPECTER2 proximity)**: mean pairwise JSD 0.8661 (2016-21) to 0.8561 (2023-25); the post-2022 deviation from the 2016-21 trend is -0.0031 [-0.0078, +0.0011]; placebo breaks: 2019 -0.0047 [-0.0094, +0.0002], 2020 -0.0009 [-0.0045, +0.0028], 2021 +0.0002 [-0.0029, +0.0036]. Beyond the placebos: **no**.
- **OpenAlex topic**: mean pairwise JSD 0.8735 (2016-21) to 0.8561 (2023-25); the post-2022 deviation from the 2016-21 trend is +0.0002 [-0.0039, +0.0054]; placebo breaks: 2019 -0.0041 [-0.0084, +0.0003], 2020 -0.0003 [-0.0038, +0.0031], 2021 +0.0007 [-0.0029, +0.0041]. Beyond the placebos: **no**.
- **OpenAlex subfield**: mean pairwise JSD 0.6911 (2016-21) to 0.6541 (2023-25); the post-2022 deviation from the 2016-21 trend is +0.0115 [-0.0049, +0.0314]; placebo breaks: 2019 +0.0075 [-0.0139, +0.0292], 2020 +0.0030 [-0.0126, +0.0173], 2021 +0.0075 [-0.0060, +0.0229]. Beyond the placebos: **no**.

**Bottom line.** Pairwise topic divergence between labs falls beyond the placebo breaks in 3 of 12 level x scope cells (BERTopic (Qwen3-0.6B embeddings) / all lab pairs, BERTopic (Qwen3-0.6B embeddings) / within school, BERTopic (Qwen3-0.6B embeddings) / within department); the finding depends on the topic system, so it is reported as system-specific, not as a general convergence. The rise of LLM topics is large and unambiguous in both BERTopic systems (section 3). Section 4 removes LLM-topic papers; section 7 re-assigns topics on all-AI wording.

- Distance of a lab to the all-lab centroid, post-2022 deviation from trend: BERTopic (Qwen3-0.6B embeddings) -0.0079 [-0.0114, -0.0041]; BERTopic (SPECTER2 proximity) -0.0003 [-0.0052, +0.0045]; OpenAlex topic +0.0059 [+0.0019, +0.0104]; OpenAlex subfield +0.0071 [-0.0032, +0.0189].
- **LLM topics are themselves a finding** (reported separately, definition below): the share of labs whose top BERTopic (Qwen3) topic is LLM-related goes from 0.003 (2019) and 0.016 (2022) to 0.110 [0.090, 0.130] in 2025; the mean share of a lab's papers on LLM topics follows (table 3).

## 1. Mean pairwise JSD between labs (trend 2016-2025, break 2023, placebo breaks)

`dev_2023` = mean(2023-25) minus the 2016-21 linear trend projected to the same years; `placeboB` = the same for a fake break at B (trend on 2016..B-1, window B..min(B+2, 2021)). A post-2022 effect is counted only when `dev_2023` has an interval excluding 0 and exceeds every placebo point in size.

| level | pairs | mean 2016-21 | mean 2023-25 | pre-slope / yr | dev_2023 | placebo 2019 | placebo 2020 | placebo 2021 | beyond placebos |
|---|---|---|---|---|---|---|---|---|---|
| BERTopic (Qwen3-0.6B embeddings) | all lab pairs | 0.8719 | 0.8622 | -0.00029 [-0.00091, +0.00024] | -0.0081 [-0.0117, -0.0046] | -0.0029 [-0.0070, +0.0013] | -0.0002 [-0.0029, +0.0027] | -0.0013 [-0.0034, +0.0014] | yes |
| BERTopic (Qwen3-0.6B embeddings) | between schools | 0.8726 | 0.8629 | -0.00028 [-0.00094, +0.00029] | -0.0081 [-0.0116, -0.0044] | -0.0033 [-0.0074, +0.0009] | -0.0003 [-0.0033, +0.0026] | -0.0011 [-0.0033, +0.0015] | yes |
| BERTopic (Qwen3-0.6B embeddings) | within school | 0.8671 | 0.8570 | -0.00032 [-0.00111, +0.00047] | -0.0083 [-0.0133, -0.0038] | -0.0016 [-0.0075, +0.0051] | -0.0015 [-0.0059, +0.0031] | -0.0027 [-0.0064, +0.0009] | yes |
| BERTopic (Qwen3-0.6B embeddings) | within department | 0.8546 | 0.8316 | -0.00052 [-0.00225, +0.00145] | -0.0202 [-0.0312, -0.0097] | -0.0022 [-0.0168, +0.0126] | -0.0028 [-0.0131, +0.0072] | -0.0044 [-0.0127, +0.0038] | yes |
| BERTopic (SPECTER2 proximity) | all lab pairs | 0.8661 | 0.8561 | -0.00124 [-0.00201, -0.00043] | -0.0031 [-0.0078, +0.0011] | -0.0047 [-0.0094, +0.0002] | -0.0009 [-0.0045, +0.0028] | +0.0002 [-0.0029, +0.0036] | no |
| BERTopic (SPECTER2 proximity) | between schools | 0.8669 | 0.8570 | -0.00124 [-0.00206, -0.00043] | -0.0031 [-0.0075, +0.0015] | -0.0046 [-0.0092, +0.0000] | -0.0008 [-0.0044, +0.0027] | +0.0005 [-0.0026, +0.0040] | no |
| BERTopic (SPECTER2 proximity) | within school | 0.8606 | 0.8508 | -0.00120 [-0.00214, -0.00024] | -0.0032 [-0.0096, +0.0028] | -0.0056 [-0.0132, +0.0024] | -0.0030 [-0.0081, +0.0025] | -0.0021 [-0.0070, +0.0025] | no |
| BERTopic (SPECTER2 proximity) | within department | 0.8413 | 0.8222 | -0.00139 [-0.00350, +0.00110] | -0.0114 [-0.0255, +0.0007] | -0.0103 [-0.0282, +0.0073] | -0.0046 [-0.0170, +0.0073] | -0.0037 [-0.0133, +0.0059] | no |
| OpenAlex topic | all lab pairs | 0.8735 | 0.8561 | -0.00320 [-0.00414, -0.00254] | +0.0002 [-0.0039, +0.0054] | -0.0041 [-0.0084, +0.0003] | -0.0003 [-0.0038, +0.0031] | +0.0007 [-0.0029, +0.0041] | no |
| OpenAlex topic | between schools | 0.8743 | 0.8571 | -0.00323 [-0.00419, -0.00257] | +0.0006 [-0.0035, +0.0056] | -0.0045 [-0.0085, +0.0002] | -0.0003 [-0.0037, +0.0031] | +0.0012 [-0.0024, +0.0046] | no |
| OpenAlex topic | within school | 0.8689 | 0.8505 | -0.00323 [-0.00434, -0.00230] | -0.0006 [-0.0064, +0.0051] | -0.0034 [-0.0092, +0.0021] | -0.0016 [-0.0065, +0.0032] | -0.0020 [-0.0060, +0.0020] | no |
| OpenAlex topic | within department | 0.8493 | 0.8204 | -0.00454 [-0.00640, -0.00268] | -0.0039 [-0.0145, +0.0075] | -0.0055 [-0.0166, +0.0052] | -0.0005 [-0.0110, +0.0087] | -0.0002 [-0.0090, +0.0076] | no |
| OpenAlex subfield | all lab pairs | 0.6911 | 0.6541 | -0.00883 [-0.01219, -0.00586] | +0.0115 [-0.0049, +0.0314] | +0.0075 [-0.0139, +0.0292] | +0.0030 [-0.0126, +0.0173] | +0.0075 [-0.0060, +0.0229] | no |
| OpenAlex subfield | between schools | 0.6932 | 0.6560 | -0.00877 [-0.01224, -0.00582] | +0.0110 [-0.0059, +0.0309] | +0.0046 [-0.0166, +0.0263] | +0.0020 [-0.0134, +0.0164] | +0.0079 [-0.0061, +0.0230] | no |
| OpenAlex subfield | within school | 0.6785 | 0.6434 | -0.00859 [-0.01265, -0.00506] | +0.0121 [-0.0075, +0.0353] | +0.0297 [+0.0035, +0.0574] | +0.0075 [-0.0102, +0.0256] | +0.0059 [-0.0099, +0.0228] | no |
| OpenAlex subfield | within department | 0.6091 | 0.5774 | -0.01174 [-0.01716, -0.00588] | +0.0329 [+0.0029, +0.0642] | +0.0365 [+0.0004, +0.0773] | +0.0248 [-0.0022, +0.0574] | +0.0323 [+0.0048, +0.0575] | no |

The JSD level is high (about 0.86-0.87 for BERTopic) because an m-paper draw touches few of the ~300-380 topics, so the unit of interest is the change, not the level; size-matching makes the level comparable across labs and years.

### Yearly series, BERTopic (Qwen3-0.6B embeddings)

| year | labs | JSD all | JSD within school | JSD within dept | dist. to centroid | top topic LLM (share of labs) | LLM paper share |
|---|---|---|---|---|---|---|---|
| 2016 | 306 | 0.8724 [0.8700, 0.8746] | 0.8671 [0.8631, 0.8707] | 0.8538 [0.8438, 0.8614] | 0.7071 [0.7041, 0.7104] | 0.0000 [0.0000, 0.0000] | 0.0067 [0.0045, 0.0093] |
| 2017 | 339 | 0.8717 [0.8697, 0.8738] | 0.8678 [0.8648, 0.8711] | 0.8574 [0.8501, 0.8632] | 0.7057 [0.7030, 0.7083] | 0.0018 [0.0004, 0.0045] | 0.0081 [0.0058, 0.0107] |
| 2018 | 399 | 0.8734 [0.8712, 0.8753] | 0.8676 [0.8648, 0.8704] | 0.8545 [0.8476, 0.8601] | 0.7068 [0.7043, 0.7091] | 0.0063 [0.0020, 0.0124] | 0.0099 [0.0072, 0.0126] |
| 2019 | 408 | 0.8711 [0.8688, 0.8736] | 0.8675 [0.8635, 0.8706] | 0.8556 [0.8489, 0.8612] | 0.7028 [0.7002, 0.7055] | 0.0031 [0.0003, 0.0068] | 0.0096 [0.0073, 0.0125] |
| 2020 | 431 | 0.8721 [0.8697, 0.8742] | 0.8676 [0.8643, 0.8706] | 0.8553 [0.8489, 0.8612] | 0.7036 [0.7011, 0.7057] | 0.0119 [0.0043, 0.0212] | 0.0165 [0.0124, 0.0216] |
| 2021 | 462 | 0.8706 [0.8683, 0.8729] | 0.8650 [0.8616, 0.8683] | 0.8512 [0.8442, 0.8575] | 0.7006 [0.6981, 0.7030] | 0.0051 [0.0014, 0.0107] | 0.0159 [0.0125, 0.0195] |
| 2022 | 394 | 0.8703 [0.8675, 0.8729] | 0.8658 [0.8617, 0.8692] | 0.8529 [0.8458, 0.8593] | 0.7001 [0.6971, 0.7029] | 0.0159 [0.0064, 0.0266] | 0.0213 [0.0162, 0.0264] |
| 2023 | 431 | 0.8646 [0.8610, 0.8678] | 0.8599 [0.8549, 0.8640] | 0.8374 [0.8277, 0.8460] | 0.6936 [0.6899, 0.6973] | 0.0386 [0.0254, 0.0518] | 0.0457 [0.0374, 0.0540] |
| 2024 | 484 | 0.8633 [0.8599, 0.8662] | 0.8582 [0.8538, 0.8624] | 0.8312 [0.8229, 0.8404] | 0.6901 [0.6868, 0.6936] | 0.0757 [0.0561, 0.0964] | 0.0778 [0.0674, 0.0888] |
| 2025 | 526 | 0.8587 [0.8548, 0.8625] | 0.8529 [0.8482, 0.8574] | 0.8261 [0.8173, 0.8344] | 0.6858 [0.6816, 0.6897] | 0.1103 [0.0901, 0.1305] | 0.1015 [0.0885, 0.1125] |

## 2. Distance to the all-lab centroid and the LLM share of topics

| level | measure | dev_2023 (bootstrap over labs) | lab-FE post-2022 shift [lab-clustered] | placebo FE shifts 2019 / 2020 / 2021 (points) |
|---|---|---|---|---|
| BERTopic (Qwen3-0.6B embeddings) | dist_centroid | -0.0079 [-0.0114, -0.0041] | -0.0117 [-0.0146, -0.0088] | -0.0049; -0.0040; -0.0048 |
| BERTopic (Qwen3-0.6B embeddings) | dist_pre_centroid | +0.0054 [+0.0029, +0.0083] | +0.0035 [+0.0021, +0.0049] | -0.0009; -0.0003; -0.0007 |
| BERTopic (SPECTER2 proximity) | dist_centroid | -0.0003 [-0.0052, +0.0045] | -0.0106 [-0.0134, -0.0078] | -0.0085; -0.0073; -0.0064 |
| BERTopic (SPECTER2 proximity) | dist_pre_centroid | +0.0085 [+0.0050, +0.0122] | +0.0019 [+0.0001, +0.0037] | -0.0032; -0.0022; -0.0008 |
| OpenAlex topic | dist_centroid | +0.0059 [+0.0019, +0.0104] | -0.0180 [-0.0207, -0.0153] | -0.0162; -0.0144; -0.0134 |
| OpenAlex topic | dist_pre_centroid | +0.0086 [+0.0056, +0.0124] | -0.0044 [-0.0060, -0.0028] | -0.0071; -0.0059; -0.0057 |
| OpenAlex subfield | dist_centroid | +0.0071 [-0.0032, +0.0189] | -0.0214 [-0.0269, -0.0159] | -0.0187; -0.0186; -0.0152 |
| OpenAlex subfield | dist_pre_centroid | +0.0121 [+0.0018, +0.0234] | -0.0114 [-0.0160, -0.0069] | -0.0139; -0.0126; -0.0107 |

`dist_centroid`: JSD to the year's own all-lab centroid (centroid = mean of the labs' draws; equal weight per lab). `dist_pre_centroid`: JSD to the fixed 2016-2021 centroid, so a rise means labs move away from the old average mix (here toward LLM topics) while a fall means they move toward it.

## 3. LLM topics (defined from topic labels, reported separately)

| level | measure | 2016 | 2019 | 2022 | 2023 | 2024 | 2025 | dev_2023 |
|---|---|---|---|---|---|---|---|---|
| BERTopic (Qwen3-0.6B embeddings) | top_llm | 0.000 | 0.003 | 0.016 | 0.039 | 0.076 | 0.110 | +0.062 [+0.047, +0.078] |
| BERTopic (Qwen3-0.6B embeddings) | mass_llm | 0.007 | 0.010 | 0.021 | 0.046 | 0.078 | 0.101 | +0.053 [+0.043, +0.061] |
| BERTopic (SPECTER2 proximity) | top_llm | 0.008 | 0.022 | 0.023 | 0.080 | 0.112 | 0.159 | +0.087 [+0.065, +0.110] |
| BERTopic (SPECTER2 proximity) | mass_llm | 0.019 | 0.025 | 0.036 | 0.077 | 0.109 | 0.145 | +0.072 [+0.060, +0.086] |
| OpenAlex topic | top_llm | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| OpenAlex topic | mass_llm | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |

`top_llm` = share of labs whose most frequent topic in the draw is an LLM topic; `mass_llm` = mean share of a lab's papers on LLM topics. LLM topic = BERTopic topic whose label (four c-TF-IDF terms) matches `lcommon.LLM_RE` (llm/language model/GPT/prompt/in-context/RLHF/chatbot/generative AI/agentic/RAG/hallucination/chain-of-thought/instruction tuning/text generation); OpenAlex topics are matched by name, OpenAlex subfields have no LLM category (not defined).

| level | topics | papers with a topic | LLM topics | papers in LLM topics | LLM topic labels |
|---|---|---|---|---|---|
| bt_qwen3_0p6b | 379 | 101962 | 12 | 2840 | agentic, llm agents, ai agents, multiagent; generative ai, ai systems, genai, intelligence ai; cot, chainofthought, thinking, reasoning models; harmful, attack, prompt, defenses; rlhf, rl, human feedback, preference optimization; lms, language model, prompts, prompt; qa, rag, answering, question answering; kv, llm inference, cache, gpu; scientific discovery, scientists, ai agents, hypothesis generation; pretraining, incontext, incontext learning, forgetting; text generation, lms, language generation, sentence; persona, personas, personality, chatbots |
| bt_specter2_proximity | 309 | 101962 | 13 | 4610 | vlms, visionlanguage, visionlanguage models, captioning; transformers, kv, llm, tokens; clinical, notes, llms, biomedical; math, reasoning models, cot, llms; harmful, llms, attacks, attack; answering, qa, question answering, rag; agentic, llm, llm agents, ai agents; llms, llm, models llms, personality; agentic, llm, llm agents, multiturn; incontext, incontext learning, llms, pretraining; preference, rlhf, preference optimization, human feedback; generative ai, creative, creativity, genai; llms, commonsense, tom, cognitive science |
| oa_subfield | 222 | 119123 | 0 | 0 |  |
| oa_topic | 2328 | 119123 | 0 | 0 |  |

## 4. With and without the LLM topics

"Without": papers in LLM topics are removed before the draws (labs need `m` papers outside LLM topics). Convergence that is only the rise of one topic would disappear.

| level | measure | dev_2023 with all topics | dev_2023 without LLM topics | largest placebo (without) | beyond placebos without LLM |
|---|---|---|---|---|---|
| BERTopic (Qwen3-0.6B embeddings) | jsd | -0.0081 [-0.0117, -0.0046] | -0.0076 [-0.0113, -0.0042] | 0.0037 | yes |
| BERTopic (Qwen3-0.6B embeddings) | dist_centroid | -0.0079 [-0.0114, -0.0041] | -0.0074 [-0.0115, -0.0033] | 0.0040 | yes |
| BERTopic (SPECTER2 proximity) | jsd | -0.0031 [-0.0078, +0.0011] | +0.0005 [-0.0036, +0.0050] | 0.0050 | no |
| BERTopic (SPECTER2 proximity) | dist_centroid | -0.0003 [-0.0052, +0.0045] | +0.0047 [+0.0002, +0.0094] | 0.0048 | no |

## 5. Fixed lab panel and the size / smoothing rules

| level | variant | labs ever eligible | dev_2023 (JSD, all pairs) | largest placebo | beyond placebos |
|---|---|---|---|---|---|
| BERTopic (Qwen3-0.6B embeddings) | main | 1113 | -0.0081 [-0.0117, -0.0046] | 0.0029 | yes |
| BERTopic (Qwen3-0.6B embeddings) | panel | 244 | -0.0050 [-0.0091, -0.0007] | 0.0034 | yes |
| BERTopic (Qwen3-0.6B embeddings) | m5 | 1808 | -0.0027 [-0.0043, -0.0009] | 0.0020 | yes |
| BERTopic (Qwen3-0.6B embeddings) | m20 | 299 | -0.0233 [-0.0371, -0.0123] | 0.0091 | yes |
| BERTopic (Qwen3-0.6B embeddings) | a0.25 | 1113 | -0.0089 [-0.0126, -0.0054] | 0.0032 | yes |
| BERTopic (Qwen3-0.6B embeddings) | a4 | 1113 | -0.0060 [-0.0094, -0.0024] | 0.0020 | yes |
| OpenAlex topic | main | 1259 | +0.0002 [-0.0039, +0.0054] | 0.0041 | no |
| OpenAlex topic | panel | 308 | +0.0082 [+0.0038, +0.0134] | 0.0031 | yes |
| OpenAlex topic | m5 | 1938 | +0.0003 [-0.0020, +0.0027] | 0.0021 | no |
| OpenAlex topic | m20 | 403 | -0.0005 [-0.0133, +0.0110] | 0.0093 | no |
| OpenAlex topic | a0.25 | 1259 | -0.0008 [-0.0050, +0.0042] | 0.0045 | no |
| OpenAlex topic | a4 | 1259 | +0.0022 [-0.0016, +0.0070] | 0.0031 | no |
| OpenAlex subfield | main | 1259 | +0.0115 [-0.0049, +0.0314] | 0.0075 | no |
| OpenAlex subfield | panel | 308 | +0.0269 [+0.0088, +0.0455] | 0.0144 | yes |
| BERTopic (SPECTER2 proximity) | main | 1113 | -0.0031 [-0.0078, +0.0011] | 0.0047 | no |
| BERTopic (SPECTER2 proximity) | panel | 244 | +0.0006 [-0.0038, +0.0058] | 0.0048 | no |

`panel` = labs eligible in >= 6 of 10 years with >= 2 pre and >= 2 post years (composition held roughly fixed); `m5`/`m20` change the minimum-papers rule from 10; `a0.25`/`a4` the smoothing pseudo-count from 1.

## 6. By department type

Department type is a rule-based grouping of the PI's first listed department (`lcommon.dept_type`; cs, ee, eecs, engineering, math_stats, social_business, life_medical). Pairs are labs of the same type (any school); the centroid is still the all-lab centroid.

| level | department type | labs | JSD within type: dev_2023 | largest placebo | dist. to centroid: dev_2023 | LLM paper share: dev_2023 |
|---|---|---|---|---|---|---|
| BERTopic (Qwen3-0.6B embeddings) | cs | 617 | -0.0111 [-0.0161, -0.0071] | 0.0020 | -0.0097 [-0.0145, -0.0046] | +0.064 [+0.047, +0.079] |
| BERTopic (Qwen3-0.6B embeddings) | eecs | 103 | -0.0007 [-0.0177, +0.0211] | 0.0056 | -0.0043 [-0.0159, +0.0092] | +0.078 [+0.048, +0.105] |
| BERTopic (Qwen3-0.6B embeddings) | ee | 149 | -0.0146 [-0.0260, -0.0043] | 0.0083 | -0.0090 [-0.0204, +0.0002] | +0.034 [+0.019, +0.050] |
| BERTopic (Qwen3-0.6B embeddings) | engineering | 138 | +0.0029 [-0.0105, +0.0155] | 0.0047 | +0.0072 [-0.0020, +0.0161] | +0.008 [+0.002, +0.015] |
| BERTopic (Qwen3-0.6B embeddings) | math_stats | 26 | not reported (fewer than 40 labs ever eligible) |  |  |  |
| BERTopic (Qwen3-0.6B embeddings) | social_business | 37 | not reported (fewer than 40 labs ever eligible) |  |  |  |
| BERTopic (Qwen3-0.6B embeddings) | life_medical | 25 | not reported (fewer than 40 labs ever eligible) |  |  |  |
| OpenAlex topic | cs | 687 | -0.0039 [-0.0117, +0.0035] | 0.0038 | +0.0020 [-0.0042, +0.0086] | +0.000 [+0.000, +0.000] |
| OpenAlex topic | eecs | 117 | +0.0318 [+0.0054, +0.0569] | 0.0140 | +0.0278 [+0.0114, +0.0417] | +0.000 [+0.000, +0.000] |
| OpenAlex topic | ee | 158 | -0.0043 [-0.0155, +0.0077] | 0.0057 | +0.0083 [-0.0057, +0.0198] | +0.000 [+0.000, +0.000] |
| OpenAlex topic | engineering | 166 | +0.0016 [-0.0090, +0.0122] | 0.0047 | +0.0124 [+0.0018, +0.0231] | +0.000 [+0.000, +0.000] |
| OpenAlex topic | math_stats | 36 | not reported (fewer than 40 labs ever eligible) |  |  |  |
| OpenAlex topic | social_business | 48 | -0.0267 [-0.0679, +0.0025] | 0.0322 | -0.0018 [-0.0167, +0.0129] | +0.000 [+0.000, +0.000] |
| OpenAlex topic | life_medical | 27 | not reported (fewer than 40 labs ever eligible) |  |  |  |

## 7. Wording control: topics re-assigned on all-AI rewritten abstracts

Same papers (88,768 with an abstract and a passing rewrite, 2016-2025), same draws, same labs: each paper is assigned to the nearest BERTopic centroid (centroids of the original abstracts) from its original abstract (`orig`) and from its Qwen2.5-7B-polished abstract (`ai`). The nearest-centroid assignment agrees with the BERTopic label for 0.872 of papers (Qwen3) and 0.844 (SPECTER2). `gap` = ai - orig, interval from the same lab bootstrap. OpenAlex topics are metadata of the work, not of its wording, so they have no all-AI version.

| level | measure | dev_2023, original wording | dev_2023, all-AI wording | gap in dev_2023 (ai - orig) | gap in post-pre |
|---|---|---|---|---|---|
| BERTopic (Qwen3-0.6B embeddings) | jsd | -0.0060 [-0.0099, -0.0023] | -0.0065 [-0.0100, -0.0027] | -0.0005 [-0.0016, +0.0006] | -0.0017 [-0.0025, -0.0009] |
| BERTopic (Qwen3-0.6B embeddings) | dist_centroid | -0.0042 [-0.0082, -0.0001] | -0.0051 [-0.0090, -0.0009] | -0.0009 [-0.0020, +0.0004] | -0.0028 [-0.0036, -0.0020] |
| BERTopic (Qwen3-0.6B embeddings) | top_llm | +0.0770 [+0.0573, +0.0938] | +0.0839 [+0.0637, +0.1049] | +0.0070 [-0.0017, +0.0158] | +0.0110 [+0.0033, +0.0186] |
| BERTopic (SPECTER2 proximity) | jsd | -0.0026 [-0.0070, +0.0018] | -0.0024 [-0.0069, +0.0023] | +0.0002 [-0.0006, +0.0011] | +0.0001 [-0.0004, +0.0006] |
| BERTopic (SPECTER2 proximity) | dist_centroid | +0.0004 [-0.0045, +0.0056] | +0.0010 [-0.0040, +0.0059] | +0.0006 [-0.0006, +0.0016] | +0.0002 [-0.0004, +0.0007] |
| BERTopic (SPECTER2 proximity) | top_llm | +0.0997 [+0.0768, +0.1243] | +0.1028 [+0.0802, +0.1270] | +0.0031 [-0.0049, +0.0106] | +0.0046 [-0.0003, +0.0096] |

A gap interval around 0 means the change is carried by content, not by wording; a gap that is not 0 is the part wording can move.

## Not done and caveats

- Topic assignments are model-dependent (309 / 379 BERTopic topics, 37-39% of abstracts were HDBSCAN noise reassigned to the nearest topic); the two BERTopic models and OpenAlex are shown side by side, none is privileged.
- Lab composition changes with the minimum-papers rule and over the years (labs need m papers in a year); section 5 gives the number of labs ever eligible per variant and the fixed-panel result.
- Pair JSDs are computed on a uniform sample of up to 40000 lab pairs per scope-year (all pairs when fewer); the lab bootstrap resamples labs, not pairs.
- Wording control for OpenAlex levels is undefined (metadata). Full-text-based topics were not built (abstract embeddings only).

## Re-run

```
ai-writing/labstudy/run_all.sh frame topics reports     # frame -> topic runs (all levels and variants) + wording control -> this report
```
Configured by `ai-writing/labstudy/config.json` and `LABSTUDY_*` paths (final paper set, detector scores); about 6 minutes of 16 CPUs for the topic run, 3 for the control.
