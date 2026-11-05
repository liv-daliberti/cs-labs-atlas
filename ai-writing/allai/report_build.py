"""Writes ai-writing/diversity/reports/ALL-AI-REWRITE.md from the analysis tables (numbers in the Answer section are read from them).  usage: report_build.py"""
import contextlib
import io
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
import report_tables as RT  # noqa: E402

R = RT.R


def sections():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        RT.main()
    sec = {}
    for part in buf.getvalue().split('### ')[1:]:
        k, b = part.split('\n', 1)
        sec[k.strip()] = b.strip() + '\n'
    return sec


def row(df, **kw):
    for k, v in kw.items():
        df = df[df[k] == v]
    return df.iloc[0]


def main():
    sec = sections()
    pres = json.load(open(R / 'preservation_polish.json')); pp = json.load(open(R / 'preservation_paraphrase.json'))
    kd = json.load(open(R / 'kept_dropped.json'))
    chg = RT.ld('geom_change'); labs = RT.ld('geom_labsummary'); nov = RT.ld('novelty_contrast')
    v = row(chg, scope='all', measure='vendi', model='specter2_proximity'); h = row(chg, scope='all', measure='H_bt', model='specter2_proximity')
    q = row(chg, scope='all', measure='H_km', model='qwen3_0p6b')
    lb = row(labs, scope='all', measure='H_bt', model='specter2_proximity'); lk = row(labs, scope='all', measure='H_km', model='specter2_proximity')
    n3 = row(nov, scope='all', k=3, measure='nov_nn_cap', model='specter2_proximity')
    fr, d, dp = pres['filtered_reasons'], pres['detector'], pp['detector']
    reps = int(chg['reps'].dropna().iloc[0]) if 'reps' in chg else 0
    iv = RT.iv
    text = f"""# What if every paper were AI-written? Diversity and novelty on rewritten abstracts

Generated 2026-11-05 by `ai-writing/allai/` (code: `rewrite.py`, `build_texts.py`, `preserve.py`, `allai_analyze.py`, `site_data.py`, `report_build.py`; tables: `ai-writing/data/embeddings/allai/results/`, git-ignored). Site data: `ai-writing/diversity/site-data/all-ai/` (README there). **Years 2016-2025 only: 2026 is a partial year and is left out of every series and trend; post = 2023-2025.**

## Answer

- **Holding the wording constant leaves the post-2022 changes in place, at nearly the same size.** All papers, specter2_proximity, 1,000-paper draws, 2023-2025 minus 2016-2022: the Vendi score (effectively distinct papers) changes by {iv(v.orig, v.orig_lo, v.orig_hi, 2)} in the original corpus and {iv(v.ai, v.ai_lo, v.ai_hi, 2)} when every abstract is AI-worded; the gap (original minus AI, the part due to wording) is {iv(v.gap, v.gap_lo, v.gap_hi, 2)}, about 15% of the Vendi fall, the rest is content. Topic entropy over BERTopic topics changes by {iv(h.orig, h.orig_lo, h.orig_hi)} bits (original) and {iv(h.ai, h.ai_lo, h.ai_hi)} (all-AI), gap {iv(h.gap, h.gap_lo, h.gap_hi)}: for all papers pooled, the topic-spread change after 2022 is small and its interval includes 0 in both corpora.
- **The wording share is small and depends on the embedding model.** k-means entropy gap about 0 for 6 of 7 models (Qwen3-0.6B: {iv(q.gap, q.gap_lo, q.gap_hi)}, the AI corpus falls more). Vendi gap negative for the SPECTER2 pair and Qwen3-0.6B, positive for Nomic (+1.0), about 0 for SciNCL, GTE-Qwen2 and BGE-M3. Novelty (k = 3, 1 - mean of 5 nearest): SPECTER2's fall after 2022 is {iv(n3.orig_change, n3.orig_lo, n3.orig_hi, 4)} in the original and {iv(n3.ai_change, n3.ai_lo, n3.ai_hi, 4)} in the all-AI corpus (gap {iv(n3.gap_change, n3.gap_lo, n3.gap_hi, 4)}, about 27%); the other models' gaps are within 0.002.
- **Levels differ a little, trends hardly.** Rewriting makes the corpus slightly more uniform: Vendi 1-3% lower in the all-AI corpus (specter2_proximity 97.2 -> 94.4 in 2016), topic entropy unchanged.
- **Lab level** ({int(lb.labs)} labs with >= 20 papers in both periods, 20-paper draws): entropy over topics rises in both corpora, {iv(lb.orig_change, lb.orig_lo, lb.orig_hi)} (original) and {iv(lb.ai_change, lb.ai_lo, lb.ai_hi)} (all-AI) bits for BERTopic topics (specter2_proximity), {iv(lk.orig_change, lk.orig_lo, lk.orig_hi)} and {iv(lk.ai_change, lk.ai_lo, lk.ai_hi)} for k-means; the gaps are {iv(lb.gap_change, lb.gap_lo, lb.gap_hi)} and {iv(lk.gap_change, lk.gap_lo, lk.gap_hi)}.

## Method

- **Corpus.** The embeddings universe: 112,260 abstracts (`oa_fields`/`texts.sqlite`), keyed by atlas paper id. **The title stays as written (human text) and is embedded with the rewrite; only abstracts are rewritten.**
- **Rewrite.** Qwen/Qwen2.5-7B-Instruct, revision `a09a35458c702b33eeacc393d103063234e8bc28` (it was not in the HF cache; fetched by job 32105407), vLLM 0.8.3, bf16, greedy decoding (temperature 0, seed 20261104), max new tokens min(1500, 1.5 x source tokens + 100), sources over 1,800 tokens skipped. One fixed prompt, system prompt "You are a helpful assistant.": *Here is the abstract of a research paper titled "{{title}}". Rewrite it as a polished academic abstract: improve its clarity, flow and academic style. Keep every claim, number, method name and technical term exactly as given; do not add or drop any information. Keep roughly the same length (about {{n}} words). Return only the rewritten abstract, as plain text in a single paragraph.* (the detector's "polish" task, written for abstracts). Output cleaning is detector_v2's `clean`. Container: `allai/rewrites_polish.sqlite` (paper id, text, ok, why, hashes, meta with model, revision, prompt, parameters); resumable per-shard sqlite files, 3 shards, 59-minute task chains on node105 A5000s.
- **Second style.** Paraphrase ("in your own words", numbers and named methods kept) on 4,996 papers stratified by home school and year, same model and parameters.
- **Embeddings.** The same seven models as the originals (SPECTER2 base and proximity, SciNCL, Qwen3-0.6B, GTE-Qwen2-1.5B, BGE-M3, Nomic v1.5), `embed.py --texts-db ... --store-name <model>__allai` (`__para`; `__allaix` for the rewrites the filter dropped), so originals and rewrites never share a container. Qwen3-Embedding-4B is not run: its original-abstract container does not exist yet, so there is nothing to compare against; to be added after it exists.
- **Measures** (`allai_analyze.py`). Each corpus is centred on its own mean and normalised. Dispersion (mean distance from the centroid), mean pairwise cosine distance, Vendi score, topic entropy over **fixed clusters defined on the originals** (BERTopic topics of `topics.py`, specter2_proximity and qwen3_0p6b: a paper goes to the nearest topic centroid in both corpora; and 100 k-means clusters, every model), novelty k = 1, 3, 5 (`novelty.py`, nearest-5 and max cosine, pool capped at 2,000). Size-matched paired draws: all papers 1,000, a school-year 500, a lab-period 20 papers (novelty as in the embeddings report). Intervals: bootstrap over labs (a paper's first lab) with replacement, **{reps} replicates** for the all-paper, school and trend intervals, estimate +- 1.96 sd (resampling labs repeats papers, which lowers every resampled diversity, so percentiles would not bracket the estimate); the original-minus-AI gap is paired (same papers drawn from both), so its interval is narrow. Lab changes: 1,000 bootstrap resamples of labs; novelty: `mean_by_year` (200 replicates) and `diff_ci` (500). The robustness runs (paraphrase, polish on the same papers) use 40 replicates.
- **Same papers in both corpora.** Both corpora are restricted to the papers whose rewrite passed the filter below (97,940 of 112,260 with a year of 2016-2025: the counts below are for all 112,260; the analyses drop 2026).

## Content preservation

Polish style, all 112,260 abstracts: {pres['ok']:,} rewrites passed the basic checks (not cut at the token limit, not a refusal, at least 40% of the source's words); the failures are {fr['much_shorter_than_source']} much shorter than the source, {fr['source_too_long']} sources over 1,800 tokens (not rewritten), {fr['truncated']} truncated, {fr['refusal_or_short']} refusal. The rewrite is 8% shorter than its source (median length ratio {pres['len_ratio_median']:.3f}).

**Automatic number and named-method check** (`preserve.py`: numeric tokens; named methods = acronyms, CamelCase and names with digits such as BERT, ResNet-50, LoRA; matching ignores case, hyphens and spaces):

| check | share of rewrites |
|---|---|
| lose at least one number of the source (abstracts with numbers: {pres['papers_with_numbers']:,}) | {pres['any_number_lost_share']:.1%} of all abstracts; {pres['numbers_lost_share_of_numbers']:.1%} of all numbers |
| add a number that is not in the source | {pres['any_number_added_share']:.1%} |
| lose at least one named method (abstracts with terms: {pres['papers_with_terms']:,}) | {pres['any_term_lost_share']:.1%}; {pres['terms_lost_share_of_terms']:.1%} of all terms |

**Filter** (`build_texts.py`): drop a rewrite that fails the basic checks, loses 25% or more of the source's numbers, adds more new numbers than a quarter of the source's (at least 1), or loses 25% or more of its named methods. This removes {pres['rewrites']-pres['kept']:,} rewrites ({(pres['rewrites']-pres['kept'])/pres['rewrites']:.1%}): numbers lost {fr['numbers_lost']:,}, named methods lost {fr['terms_lost']:,}, numbers added {fr['numbers_added']:,}, and the basic failures above. **Kept: {pres['kept']:,} papers.** Failures were not regenerated: the filter is applied to both corpora, so the comparison is on the same papers.

**Kept vs dropped papers differ.** Among the ok rewrites (2016-2025) {kd['dropped_share']:.1%} were dropped. By school the dropped share is 10.8% (EPFL) to 13.8% (CMU); by year 11.9% to 13.8% with no trend; by OpenAlex field it is highest in Medicine (17.5%), Environmental Science (17.3%) and Materials Science (17.2%) and lowest in Decision Sciences (9.3%), Business (9.5%) and Economics (9.5%); Computer Science (13.1%) and Engineering (12.0%) are close to the overall rate. The strongest driver is content: abstracts with numbers lose {kd['by_content']['has numbers']['dropped_share']:.1%} against {kd['by_content']['no numbers']['dropped_share']:.1%} without; with named methods {kd['by_content']['has named methods']['dropped_share']:.1%} against {kd['by_content']['no named methods']['dropped_share']:.1%}; dropped sources are longer (mean {kd['source_words']['dropped']:.0f} against {kd['source_words']['kept']:.0f} words).

{sec['kd school']}
{sec['kd year']}
{sec['kd field']}
{sec['kd content']}
**The headline does not depend on the filter.** Re-running the all-papers change on all 112,187 ok rewrites (the 14,247 dropped ones embedded into `<model>__allaix` and added back), three models, 120 bootstrap replicates:

{sec['unfiltered']}
The unfiltered gaps equal the filtered ones within their intervals (specter2_proximity Vendi gap -0.96 against -0.94; Qwen3-0.6B k-means entropy +0.08 against +0.07).

**Embedding cosine, original vs its rewrite** (per model; unrelated pairs sit at 0 after centring; `own rewrite is nearest` = for 2,000 random papers, the share whose own rewrite is the nearest of the 2,000 rewrites):

{sec['cosine']}
Qwen3-0.6B is the least invariant to rewriting (centred cosine 0.936, 5th percentile 0.85); the SPECTER2 models, SciNCL and GTE-Qwen2 sit at 0.98. This matches where the all-AI trend differs most from the original's (Qwen3-0.6B entropy gap, Nomic and Qwen3 Vendi gaps): those models see some of the wording.

**Hand read, 20 random kept polish rewrites** (seed 20261104). No change of claim, number or method in any. Four small drifts: "Kalman filter" became "Kalman-Bucy filter"; "Milano" became "Milan"; two rewrites added a mild evaluative phrase ("more accurate and reliable", "to enhance user experience"). No rewrite dropped a result or reversed a finding.

**AI detector: the v1 abstract detector** (`ai-writing/detector.py`, ModernBERT-large on `title | abstract`, threshold at 1% false positives on validation human abstracts; the v2 paragraph detector is not used on abstracts because it flags 11-16% of pre-2022 abstracts). Years 2016-2025. **{d['rewrite']['flagged']:.1%} of the {d['rewrite']['n']:,} rewrites are flagged** ({d['rewrite_pre2023']['flagged']:.1%} for papers of 2016-2022, {d['rewrite_post2023']['flagged']:.1%} for 2023-2025). The original abstracts of the same papers: {d['original']['flagged']:.1%} overall, **{d['original_pre2023']['flagged']:.1%} for 2016-2022 and {d['original_post2023']['flagged']:.1%} for 2023-2025**. On the kept papers only: originals {d['original_kept_papers']['flagged']:.1%}, rewrites {d['rewrite_kept_papers']['flagged']:.1%}. Paraphrase rewrites: {dp['rewrite']['flagged']:.1%} flagged (originals of the subsample {dp['original']['flagged']:.1%}).

## Results

All tables: 2023-2025 minus 2016-2022 (novelty 2017-2022), 95% intervals. Negative gap = the original fell more (or rose less) than the all-AI corpus.

### Levels, original / all-AI, all papers (size-matched 1,000-paper draws)

{sec['levels']}
### Change after 2022, all papers

{sec['change all']}
### Change after 2022, per lab (labs with >= 20 papers in both periods; 20-paper draws; mean over labs)

{sec['labs']}
### Novelty (1 - mean cosine to the 5 nearest papers of the previous k years, size-matched pool), all papers, paired per paper

{sec['novelty all']}
### Per school, specter2_proximity, 500-paper draws

{sec['schools (specter2_proximity)']}
CMU and Stanford fall and EPFL, Princeton and Berkeley rise in topic entropy in both corpora, with the same signs and sizes. The Vendi gaps are -0.7 to -0.9 for the large schools, about 10% of their change.

### Robustness: the paraphrase style, and polish on the same papers

The paraphrase style was run on {pp['kept']:,} kept papers of a 4,996-paper stratified subsample; polish is repeated on the same papers. Draw sizes are smaller (250 papers for all; 60 per school-year; 8 per lab-period) and 40 replicates are used, so the intervals are wider.

{sec['robustness']}
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
"""
    out = HERE.parent / 'diversity' / 'reports' / 'ALL-AI-REWRITE.md'
    out.write_text(text)
    print(out, len(text.splitlines()), 'lines')


if __name__ == '__main__':
    main()
