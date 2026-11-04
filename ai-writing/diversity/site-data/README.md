# Site data: "How much AI" and "Given AI, how much" (written by `ai-writing/dose/dose_site.py`)

Status: schema fixed 2026-11-04; the JSON files appear when the detector scoring and `dose_validate.py --recalibrate` have run (not committed until then).
All files: compact JSON, `generated` = UTC time. Years 2016-2026; **2026 is a partial year** (`partial: true`). Schools: princeton, cmu, epfl, mit, berkeley, stanford, michigan, uchicago, gatech (uchicago and gatech are unreleased onboarding schools: the page may hide them). A paper counts in every school it belongs to; `all` counts each paper once.

## Definition of "AI" (primary)
`ai_share_cal >= 0.25` when the paper has a usable full text (`ai_share_cal` = share of body passages flagged by the passage detector at its 1%-FPR threshold, recut on the school's or field's own 2016-2021 text if that group failed the ~1% check, else `ai_share`); otherwise the abstract detector's flag (1% design FPR). The `fulltext` and `abstract` series give each rule alone. Validation tables: `ai-writing/diversity/reports/AI-DOSE-NOVELTY-DIVERSITY.md`.

## how_much_ai.json
`{definition, series: {primary|fulltext|abstract: {all|<school>: [ {year, partial, n, flagged, not_flagged, share, baseline, baseline_n, adjusted, adj_lo, adj_hi} ]}}}`.
`baseline` = the same rule's 2016-2021 rate in that school (papers the detector never trained on); `adjusted = share - baseline` with a 95% interval (binomial errors of both terms).

## given_ai.json
`{threshold, by_school_year: {all|<school>: [ {year, partial, n, mean, median, deciles[9] (10th..90th pct), hist_edges[16], hist[15]} ]}, position_profile: {note, deciles[10]}}` among AI-flagged full-text papers; `ai_share` is the dose. Sections (abstract, intro, related work, ...) are **not recoverable** from the stored text, so `position_profile` gives the flagged-passage share by relative position in the body (decile 0 = start) for 2023-2026 papers.

## labs_ai_amount.json
`{min_papers: 5, shrinkage_k, note, rows: [ {school, lab_id, lab, pi, year, n, mean, median, shrunk} ]}`: labs with at least 5 scored papers in the year; `shrunk = (n*mean + k*school_year_mean)/(n+k)`, the number to rank on.
