# Passage-level AI-written-text detector (v2)

ModernBERT-large classifies single ~150-word body passages of the full texts as human-written (2016–2021) or LLM-written. It is applied to every passage of every stored lab-paper full text. This is the "Paragraph (v2)" level of DESIGN-v2.md section 1.

## Headline

- **In-distribution detection:** per-generator AUC 0.9989–0.9998 for the final model. At a 1% passage false-positive rate (FPR), the true-positive rate (TPR) is 97.8–99.8%.
- **Leave-one-generator-out:**
  - Trained without Llama-3.3-70B, it catches Llama-70B with AUC 0.9997 and TPR 99.4%.
  - Trained without Qwen2.5-72B, it catches Qwen-72B with AUC 0.9953 and TPR 95.7%. Paraphrase is the weakest case at 90.4%.
- **Real-text check:** on all 114,050 passages of the 2,928 held-out 2016–2021 papers, the final model flags 0.98% (95% CI 0.90–1.08%, paper bootstrap). Each year 2016–2021 is between 0.86% and 1.24%.
- **Flagged passage share in lab papers:**
  - 2016–2020: 0.83–0.91%;
  - 2021: 1.08%; 2022: 1.27%;
  - 2023: 3.3%; 2024: 7.9%; 2025: 14.0%; 2026: 11.3%.
  - At a strict cut of p ≥ 0.5 the trend is the same: pre-period floor 0.19%, 2025 8.7%.
- **Paper level:**
  - Papers with `ai_share ≥ 0.25`: ≤ 0.21% each year through 2022, then 2.5% (2023), 10.8% (2024), 23.5% (2025) and 15.9% (2026).
  - `ai_any` is mostly chance: 21–31% of pre-2023 papers have at least one flagged passage. See caveat 4.

## Data

**Pool:** lab papers from 2016–2021 with a usable full text (`common.usable_text`: at least 1,000 words, and for a PDF the title found on page 1). That is 14,531 papers:

| school | papers |
|---|---|
| CMU | 5,945 |
| MIT | 3,886 |
| EPFL | 1,780 |
| Princeton | 1,597 |
| Berkeley | 1,323 |

**Passages:** `diversity/common.passages`, imported. Splitter source sha is `77cb33092b84`. The `paragraphs` table is not used.

**Paper split:** `sha1(20261022|key)` gives train / cal / test at 70 / 10 / 20%. That is 10,081 / 1,522 / 2,928 papers.

**Sources for generation:** 18,000 passages from 14,528 papers.
- One passage per paper per round, with school quotas proportional to the pool.
- A source is never a paper's first passage, has 60–400 words, and its paper has a title.
- 6,000 per generator; 2,000 per generator × task.

**Human passages:**
- 25,000 further passages, stratified by school and disjoint from the sources, plus the 18,000 source originals.
- 29,863 of these are in train-split papers and are used for training.

**Held-out text:**
- Calibration: every passage of the cal-split papers (59,838).
- Real-text test: every passage of the test-split papers (114,050).

**Generation** (vLLM 0.8.4, temperature 0.7, top-p 0.9, at most 900 tokens):

| generator | job | resources | kept |
|---|---|---|---|
| Qwen2.5-72B-Instruct | 31950260 | 4× A6000, tensor parallel 4, cs/allcs, 200G, 64 min | 5,997 |
| Llama-3.3-70B-Instruct | 31950285 | same, 56 min; MaxRSS 115 GB | 5,994 |
| Qwen2.5-7B-Instruct | 31950286 | 1× A5000, 40G, 20 min | 5,993 |

- **70B-class GPU request:** v1's 31948963 and 31948964 ran on node206 with `--partition=cs --account=allcs --gres=gpu:a6000:4 --cpus-per-task=16 --mem=256G`, tensor parallel 4 and `disable_custom_all_reduce`. The same request was reused with 200G.
- **Over-length sources:** sources over 1,200 tokens are skipped; these are extraction junk such as base64 blobs. One such source (12.6k tokens) crashed the first Llama and 7B runs, 31950261 and 31950262.
- **Tasks:**
  - polish: "Revise it to improve its clarity, flow and academic style. Keep the content and roughly the same length."
  - paraphrase.
  - notes: list 3–6 key points, then write an N-word passage from the title plus the points.
  - All three ask the model to keep citation markers and symbols and to return one plain paragraph.
- **Cleaning:** preambles and trailing notes are stripped. Outputs that are truncated, refused, or under 40 words are dropped.

**Normalizer (`v2common.norm`).** This is v1's `norm()` plus five steps, applied to every text:
- NFKC normalization.
- `delatex`. The generators rewrote garbled PDF math as LaTeX in 26% (Qwen-72B), 29% (Qwen-7B) and 3% (Llama) of outputs. The PDF text layer never contains LaTeX, so this would be a shortcut. Math is now rendered as pdftotext shows it, and afterwards the leftover `\`, `$` and `{` rates are no higher in AI text than in human text.
- Line-end hyphenation is undone.
- Numeric citation markers are removed.
- Author-year citation markers are removed.

## Training (v1 recipe)

- **Recipe:** ModernBERT-large, 512 tokens, AdamW at 2e-5, 2 epochs, batch size 16, bf16. Classes are balanced by repeating the AI passages.
- **Scoring precision:** the pooling, head and classifier run in fp32, because bf16 logits are too coarse at a low threshold.
- **Threshold:** the 99th percentile of the 59,838 cal passages.

| model | job | train AI (× repeat) | threshold p | cal AUC | wall time |
|---|---|---|---|---|---|
| holdout-llama70b | 31950355 | 8,333 (×4) | 3.03e-4 | 0.9986 | 56 min |
| holdout-qwen72b | 31950356 | 8,292 (×4) | 5.97e-6 | 0.9997 | 58 min |
| **all** (final) | 31950357 | 12,480 (×2) | **8.53e-4** | 0.9992 | 49 min |

The final model trains on the train split only, so the cal and test papers stay unseen.

## Detection: AUC and TPR at 1% FPR

The AI passages are from test-split sources. The human comparison set is all test-split passages. `*` marks the generator that model never saw.

| generator / task | holdout-llama70b AUC | TPR | holdout-qwen72b AUC | TPR | all AUC | TPR | n |
|---|---|---|---|---|---|---|---|
| qwen72b / polish | 0.9986 | 97.1% | 0.9962* | 96.1%* | 0.9991 | 97.6% | 409 |
| qwen72b / paraphrase | 0.9972 | 95.3% | 0.9890* | 90.4%* | 0.9975 | 95.6% | 385 |
| qwen72b / notes | 1.0000 | 100% | 1.0000* | 100%* | 1.0000 | 100% | 430 |
| qwen72b / all | 0.9987 | 97.5% | 0.9953* | 95.7%* | 0.9989 | 97.8% | 1,224 |
| qwen7b / polish | 0.9997 | 99.0% | 0.9993 | 98.5% | 0.9995 | 98.3% | 408 |
| qwen7b / paraphrase | 0.9994 | 99.0% | 0.9994 | 99.3% | 0.9995 | 99.0% | 421 |
| qwen7b / notes | 1.0000 | 100% | 1.0000 | 100% | 1.0000 | 100% | 377 |
| qwen7b / all | 0.9997 | 99.3% | 0.9996 | 99.3% | 0.9997 | 99.1% | 1,206 |
| llama70b / polish | 0.9999* | 99.7%* | 0.9999 | 99.5% | 0.9999 | 100% | 391 |
| llama70b / paraphrase | 0.9993* | 98.6%* | 0.9997 | 99.5% | 0.9996 | 99.3% | 416 |
| llama70b / notes | 1.0000* | 100%* | 1.0000 | 100% | 1.0000 | 100% | 394 |
| llama70b / all | 0.9997* | 99.4%* | 0.9999 | 99.7% | 0.9998 | 99.8% | 1,201 |
| all / polish | 0.9994 | 98.6% | 0.9984 | 98.0% | 0.9995 | 98.6% | 1,208 |
| all / paraphrase | 0.9987 | 97.7% | 0.9962 | 96.6% | 0.9989 | 98.0% | 1,222 |
| all / notes | 1.0000 | 100% | 1.0000 | 100% | 1.0000 | 100% | 1,201 |

The held-out generator scored on all of its outputs, from every split:

| held out | polish TPR | paraphrase TPR | notes TPR | all |
|---|---|---|---|---|
| Llama-70B | 99.4% | 98.7% | 99.8% | AUC 0.9993, TPR 99.3% (n = 5,994) |
| Qwen-72B | 95.0% | 91.9% | 100% | AUC 0.9958, TPR 95.6% (n = 5,997) |

## Real-text FPR on the 114,050 held-out 2016–2021 passages

| model | flagged | 95% CI | sampled test humans (n = 8,651) |
|---|---|---|---|
| holdout-llama70b | 1.02% | 0.95–1.11% | 0.97% |
| holdout-qwen72b | 0.98% | 0.90–1.06% | 1.03% |
| all | 0.98% | 0.90–1.08% | 1.03% |

Final model, by stratum:

| stratum | flagged |
|---|---|
| year 2016 / 2017 / 2018 / 2019 / 2020 / 2021 | 0.86 / 0.95 / 0.90 / 0.95 / 0.88 / 1.24% |
| Berkeley / CMU / EPFL / MIT / Princeton | 1.56 / 0.78 / 0.87 / 1.16 / 0.89% |
| PDF / XML | 0.98 / 1.00% |
| first passage / later passages | 1.54 / 0.97% |
| 40–100 / 100–150 / 150–200 / 200–400 words | 8.12% (n = 985) / 2.04% / 0.94% / 0.39% |
| mid-sentence-capital quintiles, q1 to q5 | 1.00 / 0.75 / 0.66 / 0.73 / 1.78% |
| non-ASCII and printable-word quintiles | 0.74–1.16% |

Paper-level null on the same test papers (median 34 passages):
- mean `ai_share` 0.99%;
- `ai_any` 24.1% (30.7% expected if passages were independent);
- `ai_share ≥ 0.25` 0.07%.

## Scoring

- 33,043 texts and **1,409,830 passages** scored (job 31950358, 10× A5000, 19–29 min each).
- **30,982 usable papers from 2016–2026**, with 1,336,312 passages.
- 71,446 passages flagged.

**Flagged share by year (usable texts):**

| year | papers | flagged share (95% CI) | held-out test papers only | p ≥ 0.5 | mean `ai_share` | `ai_any` | `ai_share ≥ 0.25` |
|---|---|---|---|---|---|---|---|
| 2016 | 1,903 | 0.85% (0.76–0.95) | 0.86% | 0.18% | 0.76% | 21.4% | 0.05% |
| 2017 | 2,046 | 0.83% (0.73–0.92) | 0.95% | 0.21% | 0.83% | 21.4% | 0.10% |
| 2018 | 2,163 | 0.91% (0.79–1.04) | 0.90% | 0.19% | 0.88% | 21.3% | 0.14% |
| 2019 | 2,614 | 0.89% (0.82–0.97) | 0.95% | 0.19% | 0.81% | 21.8% | 0.00% |
| 2020 | 2,789 | 0.91% (0.83–1.00) | 0.88% | 0.19% | 0.92% | 23.6% | 0.11% |
| 2021 | 3,016 | 1.08% (0.99–1.17) | 1.24% | 0.26% | 1.05% | 27.3% | 0.07% |
| 2022 | 2,818 | 1.27% (1.16–1.36) | | 0.32% | 1.25% | 30.6% | 0.21% |
| 2023 | 3,233 | 3.32% (3.06–3.60) | | 1.61% | 3.39% | 44.6% | 2.51% |
| 2024 | 3,335 | 7.86% (7.39–8.36) | | 4.74% | 8.35% | 62.1% | 10.79% |
| 2025 | 3,497 | 14.01% (13.44–14.64) | | 8.69% | 14.80% | 77.9% | 23.51% |
| 2026 | 3,568 | 11.34% (10.88–11.81) | | 5.95% | 12.06% | 79.2% | 15.89% |

Dropping passages under 100 words changes no year by more than 0.06 points.

**By school** (flagged share, papers in parentheses):

| year | Princeton | CMU | EPFL | MIT | Berkeley |
|---|---|---|---|---|---|
| 2016 | 0.81% (205) | 0.79% (759) | 0.88% (296) | 0.81% (462) | 1.13% (181) |
| 2017 | 0.88% (208) | 0.73% (831) | 0.92% (271) | 0.90% (519) | 0.82% (217) |
| 2018 | 0.69% (247) | 0.88% (991) | 0.70% (267) | 1.11% (658) | (none) |
| 2019 | 0.95% (271) | 0.75% (1,050) | 0.88% (290) | 0.97% (725) | 1.12% (278) |
| 2020 | 0.94% (332) | 0.76% (1,103) | 0.77% (310) | 1.10% (740) | 1.10% (304) |
| 2021 | 1.24% (334) | 0.95% (1,211) | 0.94% (346) | 1.15% (782) | 1.30% (343) |
| 2022 | 1.25% (353) | 1.21% (1,150) | 1.14% (306) | 1.37% (701) | 1.36% (308) |
| 2023 | 3.08% (383) | 3.31% (1,353) | 2.91% (354) | 3.05% (800) | 4.72% (343) |
| 2024 | 6.81% (413) | 8.78% (1,437) | 7.95% (415) | 6.81% (741) | 7.93% (329) |
| 2025 | 12.18% (447) | 15.11% (1,386) | 15.91% (415) | 12.03% (690) | 13.99% (559) |
| 2026 | 8.88% (443) | 13.08% (1,320) | 13.25% (616) | 9.44% (676) | 9.52% (513) |

## Caveats

1. **The positives are synthetic.**
   - They come from three open models (two Qwen sizes, one Llama) rewriting extracted passages.
   - Sensitivity to GPT, Claude or Gemini text, partial edits, or AI text that went through pdftotext is unmeasured.
   - The flagged share is roughly FPR + TPR × (true share), so it is a measure of the LLM register, not an exact usage rate.
2. **The pre-period floor creeps up:** 0.83–0.91% in 2016–2020, 1.08% (held-out 1.24%) in 2021, 1.27% in 2022.
   - Possible causes: 2022 includes papers after 30 November 2022, a stored full text can be a later revision, or style is drifting.
   - The floor also varies by school (CMU 0.78% vs Berkeley 1.56%), so compare each school or lab against its own pre-period baseline.
3. **Short tail passages:** the last passage of a paper (40–100 words, acknowledgments or future work) has 8% FPR. These are only 0.9% of passages and don't move the trend. They can be filtered on `words`.
4. **`ai_any` is chance-dominated** (21–31% before 2023). Use `ai_share`. Its ≥ 0.25 cut has a clean null (≤ 0.21% through 2022).
5. **Extraction quality:** FPR is flat across quality strata except heading- or interleaving-heavy passages (1.78%) and first passages (1.54%).
6. **The threshold is a low p (8.5e-4).** The p ≥ 0.5 column gives the same picture, so the result doesn't rest on marginal scores.
7. **2026 is a partial year** and is below 2025; don't read that as a decline unchecked.
8. **Berkeley 2018 is missing** from `papers.jsonl.gz` upstream.
9. **Train-split leakage is small.** Train-split pre-period papers lent at most 43k of 570k passages to training. Their all-papers share is within 0.16 points of the held-out-only share.
10. **Stored scores are rounded.** `mean_p` is rounded to 5 decimals, so it is 0.0 for most human papers; use `ai_share` as the dose. Likewise v1's `ai-writing/scores.jsonl.gz` rounds `p_ai` to 5 decimals while v1's threshold is 1.25e-6, so its stored `p_ai` cannot be re-thresholded (its `flagged` column is correct).

## Outputs

All paths are under `/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/ai-writing/`.

| file | content |
|---|---|
| `detector_v2/passage_scores.jsonl.gz` | `{key, pidx, words, p_ai, flagged}` for 1,409,830 passages. `pidx` indexes `common.passages(body)`. |
| `detector_v2/paper_ai_fulltext.jsonl.gz` | `{key, school, year, kind, usable, split, n_passages, n_flagged, ai_share, ai_any, mean_p, n_paragraphs}` for 33,043 texts. |
| `detector_v2/results/flagged_by_year_school.csv` (and `.json`) | Year × school (and all), with paper-bootstrap CIs and test-split-only rows for 2016–2021. |
| `detector_v2/results/{all,holdout-llama70b,holdout-qwen72b}/metrics.json` and `test_scores.jsonl.gz` | Every number above. |
| `detector_v2/results/tables.md` | The tables. |
| `detector_v2/models/all/model` | The final model (about 2 GB). Its threshold is in `results/all/metrics.json`. |
| `detector_v2/data/` | Sources, humans, `cal_real` / `test_real`, `generated-{qwen72b,llama70b,qwen7b}.jsonl`, `prep_stats.json`. |
| `paragraph_scores.jsonl.gz` | 30,982 rows of `{key, n_paragraphs, n_flagged, ai_share, ai_any, mean_p}`, published by `detector_v2/merge.py --publish` after the gate (real-text flagged share ≤ 1.5% overall and ≤ 2% in every year; AUC ≥ 0.95 and TPR ≥ 0.5 per generator). |

**Code**, all in `detector_v2/`:
- `v2common.py`: paths, split, `norm` / `delatex`.
- `prep.py`
- `gen.py` and `gen.slurm`
- `detector.py` and `detector.slurm`: train with `[--holdout GEN] [--save]`; score with `score N` as an array.
- `merge.py`: the `--publish` flag and the gate.
- `tables.py`
- Logs are in `logs/`.
