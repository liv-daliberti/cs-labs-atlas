# Site data for the "all papers AI-written" page

Built by `ai-writing/allai/site_data.py build` from the analysis tables (`ai-writing/data/embeddings/allai/results/`, git-ignored). The report is
`ai-writing/diversity/reports/ALL-AI-REWRITE.md`. All files are plain JSON; `null` = not available; numbers are rounded to 5 decimals.

Vocabulary. **orig** = the paper's original abstract; **ai** = the same abstract rewritten by the language model (every paper, same prompt); **gap** = orig - ai
(the part of a value, or of a change, that is due to the wording). A 95% interval is `*_lo` / `*_hi`. **pre** = 2016-2022, **post** = 2023-2025.
`model` is the embedding model: `specter2_proximity` (headline), `specter2_base`, `scincl`, `qwen3_0p6b`, `gte_qwen2_1p5b`, `bge_m3`, `nomic_v15`.

| file | content |
|---|---|
| `methods.json` | `title`, `blurb` (short methods text for the page), `model`, `prompt`, `second_style`, `corpus` {abstracts, rewritten_ok, kept_after_preservation_filter}, `filter`, `limits` (list), `periods` |
| `overall.json` | `measures.<measure>.{label, models.<model>: [ {year, orig, orig_lo, orig_hi, ai, ai_lo, ai_hi, gap, gap_lo, gap_hi} ]}` for all papers, one point per year 2016-2025 (2026 is a partial year and is left out). Measures: `vendi`, `dispersion`, `pairwise`, `H_bt` (topic entropy over BERTopic topics, bits; only `specter2_proximity`, `qwen3_0p6b`), `H_km` (entropy over 100 k-means clusters, every model). Size-matched draws of 1,000 papers; interval = estimate +- 1.96 sd of a bootstrap over labs |
| `schools.json` | `schools.<school>.<measure>.<model>: [ {year, orig, ..., gap_hi} ]`, 500-paper draws, same measures |
| `trend.json` | `rows: [ {model, scope ('all' or a school), scope_id, measure, orig, orig_lo, orig_hi, ai, ai_lo, ai_hi, gap, gap_lo, gap_hi} ]`: mean of post minus mean of pre, per corpus and the gap (headline: the post-2023 change with wording held constant is the `ai` columns; the original's is `orig`) |
| `labs.json` | `rows: [ {model, measure, scope ('all' or a school), labs, orig_change, ..., gap_change, gap_lo, gap_hi, orig_pre, orig_post, ai_pre, ai_post} ]`: labs with >= 20 papers in both periods, 20-paper draws, change = post - pre averaged over labs, interval by bootstrap over labs |
| `novelty.json` | `trend: [ {model, scope, scope_id, k=3, year, orig.., ai.., gap..} ]` (novelty = 1 - mean cosine of the 5 nearest papers of the previous k years, pool capped at 2,000) and `contrast: [ {model, scope, scope_id, k (1, 3, 5), measure (nov_nn_cap, nov_max_cap), orig_change, ..., gap_hi} ]` post (2023-2025) minus pre (2017-2022); intervals by cluster bootstrap over labs |
| `preservation.json` | `polish` and `paraphrase`: counts, filter reasons, share of rewrites that lose numbers or named terms, per-model embedding cosine original vs rewrite (`cosine.<model>.{raw, centred, random_centred, retrieval_at_1}`), v1 abstract-detector flagged shares (`detector.rewrite`, `detector.original_pre2023`, `detector.original_post2023`, ...; years 2016-2025) |

Reading `trend.json`: if `ai` and `orig` agree (and `gap` is small with an interval around 0), the post-2023 change is in what papers are about; a `gap`
away from 0 is the share due to wording. Vendi is the number of effectively distinct papers (higher = more diverse); `H_*` are bits.
