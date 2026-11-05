# Site data for the two AI pages (written by `ai-writing/dose/dose_site.py`)

Status: schema fixed 2026-11-04 (slider version); the files appear once scoring and `dose_validate.py --recalibrate` have run. Another agent writes `all-ai/` in this folder; these files stay outside it.

The page has a **cutoff slider t, 1%..100% of a paper's paragraphs flagged** (default 25, ticks at 10 and 50). Everything is recomputed in the browser from histograms. A paper is "AI at t" when its dose `x` is at least t/100.

## Dose and bin rule
`x = ai_share_cal` (share of the paper's body passages flagged at the passage detector's 1%-FPR threshold, recut on the school's or field's own 2016-2021 text where validation needed it; listed in `meta.recalibrated_groups` as `school:<name>` / `field:<name>` with the cut), else `ai_share`. **bin = floor(100*x + 1e-9), bin 100 holds exactly x = 1.0**, so bin b is [b%, (b+1)%) and **"AI at t" is exactly "bin >= t"** (t integer 1..100). Papers with zero flagged passages are bin 0. Full-text papers only; arrays have 101 entries.

## ai_hist.json
`{meta, series: {all|<school>: {"<year>": cell}}}`, years 2016-2025 (`all` counts each paper once; a school counts every paper of its labs; 2026 is a partial year and is dropped everywhere, owner 2026-11-04). A cell:
- `hist[101]` counts and `sum[101]` sum of x per bin, for full-text papers; `n_ft` their number; `papers` all papers of the cell.
- From these, for any t: share = sum(hist[t:])/n_ft; mean among AI = sum(sum[t:])/sum(hist[t:]); median among AI: the bin where the cumulative count from t reaches half, valued at that bin's mean (sum/hist), so within 1 percentage point.
- `abstract_only: {n, flagged}`: papers with an abstract score but **no usable full text**, and how many the v1 abstract rule (1% FPR) flags. On the page: toggle "include abstract-only papers (abstract flag)", default on; the flag does not depend on t, so these counts are constant across the slider (add flagged to the AI count and n to the denominator).
- `hist_out_of_sample`, `sum_out_of_sample` (years <= 2021 only): the same for papers the detector never trained on. **The false-positive floor at t** = share at t computed from the 2016-2021 cells (out-of-sample arrays preferred; the plain arrays include papers whose text was a training negative).
- `band`: `{"1","5","10","25","50","75","100": [lo, hi]}`, 95% **bootstrap over labs** (clusters = the paper's first lab, 300 draws) of the share >= t among full-text papers; show a band only at those cutoffs or interpolate linearly. When abstract-only papers are included, compute a **Wilson interval client-side** from the combined counts (a band is not stored for that case). Cells with fewer than 20 full-text papers have no band.

## ai_position.json
`{meta, position_bins: 10, series: {all|<school>: {pre|post: {flagged[101][10], total[101][10]}}}}`: passages by their paper's dose bin (rows) and relative position decile in the body (columns, 0 = opening, 9 = end), `pre` = 2016-2021 papers, `post` = 2023-2026. A passage is flagged at its paper's own cut. For the share of flagged passages at position p among papers AI at t: sum(flagged[t:][p]) / sum(total[t:][p]); group the deciles into opening/middle/end (0-2, 3-6, 7-9) client-side. Sections (intro, related work...) are not recoverable from the stored text (the body is flattened; a heading regex finds 3+ headings in only ~23% of papers).

## labs_ai_hist_<school>.json (or `.json.gz` when over 1.5 MB)
`{meta, labs: [{lab_id, lab, pi, year, n, bins[], counts[], sums[]}]}`: one row per lab-year with **at least 5 full-text papers**; sparse histogram (only non-empty bins, bin indices in `bins`). The lab's share AI at t = sum(counts where bin >= t)/n, its mean AI amount = sum(sums where bin >= t)/sum(counts where bin >= t); the list re-ranks as t moves. Small labs (n < 5) are omitted; for ranking, shrink toward the school-year mean with weight n/(n+5).
