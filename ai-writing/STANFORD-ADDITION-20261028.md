# Stanford added to the AI-writing study (2026-10-28)

Stanford is in as the sixth school, and every analysis was rerun with it. The only GPU work was scoring new texts with
the existing final detector ('all'); nothing was retrained, and `merge.py --publish` passed its held-out gate. Before
versions of every result are in `logs/backup-before-stanford-20261028/`.

## What Stanford added
- **Papers:** 17,309 lab papers from 2016–2026 (13,617 with a 50+ word abstract). The corpus is now 95,099 papers.
- **Full texts:** 9,544 matched to the catalog at 23:10Z (the collector is still downloading); 9,112 usable and scored.
- **Labs:** 154 Stanford labs enter the lab-level analyses (861 in total).
- **Flagged share (ai_share >= 0.25) by year:** 2016–22 0–0.3%; 2023 3.9%; 2024 10.7%; 2025 24.9%; 2026 16.5%.
  - That is mid-pack: in 2025 the range runs from MIT 18.4% to CMU/EPFL 27.6%.
  - Pooled 2023/24/25/26 went from 3.0/11.2/23.8/17.6% to 3.1/11.0/24.3/17.6%.
- **Caution:** Stanford's pre-ChatGPT passage false-positive rate is 1.0–1.65%, slightly above the pooled 0.9–1.4%.

## Why before vs after is not pure Stanford
- The hierarchy changed for other schools since 10-27 (MIT −609 papers, Berkeley +361).
- Running collectors added newly scored texts for other schools too: Berkeley +1,304, CMU +983, EPFL +331.
- The corpus reflects the hierarchy as of about 19:00 EDT on 10-28, before rebuild 32015113.

## Headline changes
- **Citations:** essentially unchanged.
  - Within lab, S2 recent-reference share +0.038 → +0.039; reference age −0.72 → −0.80 years.
  - Stanford alone: recent share +0.061 [0.022, 0.098] (S2).
  - Berkeley's OpenAlex reference-age gap now excludes zero.
  - Raw gaps, flagged − none (S2): 2025 reference age −3.45 → −3.61 years; recent share +0.145 → +0.149.
  - The cited-years IQR trend is unchanged at −0.24 per year.
  - Share of citations going to AI-flagged works (q2v2): within lab +5.5 points, unchanged. For flagged papers in 2023–26 it went from 22.0% to 21.1%.
  - 2025 median reference age: 4.79 years for AI-detected papers against 6.77 for the rest. Share of references from the last two years: 0.356 against 0.268.
- **Diversity battery** (job 32014925; `diversity/REPORT.md`):
  - N1 (distance to the field) still clears placebo, but weaker: −0.36 → −0.27.
  - L5 sentence-length SD (−0.16) and C4 self-lab references (−0.15) now clear placebo; C4 only just, against a ±0.146 band.
  - On abstracts, S3, S5, S6 and N2 now have intervals that exclude zero, without clearing placebo. S7 flips sign (−0.02 → +0.03); both intervals include zero.
  - Pooled slopes, before → after: L1 +0.42 → +0.41; L7 +0.71 → +0.71; Flesch −0.49 → −0.46; S1 full text +0.15 → +0.13; N2 +0.05 → +0.11 [0.02, 0.19]; S5 abstract +0.02 → +0.10 [0.02, 0.18]; S5 full text +0.07 → +0.04; L5 SD −0.10 → −0.16.
  - Stanford alone (about 150 labs), intervals excluding zero:
    - abstract semantic: S2 +0.23, S3 +0.25, S5 +0.32, S6 +0.30, S7 +0.27, N2 +0.26;
    - lexical: L1 +0.36, L2 +0.36, L5 SD −0.36, L7 +0.63, Flesch −0.39;
    - no full-text semantic measure excludes zero.
  - Stanford's C1–C4 rest on only 24 labs, because `s2.sqlite` has references for 6% of Stanford papers.
  - Within lab: N1 −0.14 → −0.15; S8 −0.165 → −0.153. The abstract lab-centroid distance under dose flips +0.023 → −0.013 (n.s.). The S8 2016–22 placebo flips +0.21 → −0.10.
- **Figure 3** (cosine):
  - Extent, flagged vs not: 0.107 vs 0.113 → 0.103 vs 0.119; Stanford 0.100 vs 0.122.
  - Lab entropy: Stanford 4.26 vs 4.63; pooled 5.69 vs 6.10.
  - In the period figure, not-flagged papers after 2022 now have higher extent than papers before it (it was lower), under both geometries.
- **Fields:** 23,716 papers; AI-detected rate 13.95% → 14.09%. The lowest-rate subfields are unchanged: Theory/Mathematics, Management Science/OR and Statistics, at about 6%.

## Not finished
- **20,839 missing OpenAlex cited ids were not retried** (16,985 pre-date this run), so the five-school baseline stayed as it was.
- **The open-full-text v2 sample (`ftsample.py`/`v2score.py`) was not extended.** The 2023+ reference v2 coverage dropped (2025 flagged: 38.5% → 35.4%).
- **The v1 abstract detector was not run on Stanford.** The abstract-detector line in `flag_share_by_year.png` lacks Stanford.
- **`citations/REPORT.md` is hand-written and now stale.**

## Jobs and files
- **Jobs:**
  - Full-text extraction 32014390: 12,425 texts, 59,916 in total.
  - Delta scoring 32014651, 4 A5000 shards. The first try, 32014579, failed because `~/.triton/cache` is missing on the nodes; it was fixed with `TRITON_CACHE_DIR`.
  - Embeddings 32014392 (abstracts, 77,185 in total) and 32014766 (full texts, 56,329 stored).
  - Citations: fetch 32014899 (11,557 citing papers, 147,866 cited works) and rerun 32015143.
- **Edited scripts** (originals in the backup's `scripts/`):
  - School lists: `build_corpus.py`, `fig3.py`, `detector_v2/merge.py`, `detector_v2/tables.py`, `diversity/common.py`, `citations/analyze.py`.
  - `detector_v2/detector.py`: new `--name` option.
  - `diversity/figures.py`: a sixth colour.
  - `diversity/report.py`.
  - `diversity/run_battery.slurm`: the merge now runs before the store copy.
- **New:** `fulltext.slurm`, `embed.slurm`, `detector_v2/score_delta{.slurm,_prep.py}`, `citations/fetch_new.slurm`, `citations/rerun_20261028.slurm`.
- **Kept for provenance:** `detector_v2/data/delta-d20261028.sqlite`.

## Incident
The battery was submitted once even though `--test-only` printed "Preempts:", and was cancelled within seconds. Another
user's lowprio job (32014629, node105) was preempted at 20:24:31 and requeued; afterwards Slurm showed it PENDING
(JobHeldUser). Later submissions waited for a clean `--test-only`.
