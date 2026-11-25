# Cornell onboarding, stage 2 (faculty census) - 2026-11-24/25 (in progress, stopped before the audit draw)

## Census
- `census_build.py cornell`: 177 persons, 159 listed as PIs (basis `ladder_faculty`), 18 non-PI (lecturers, emeriti and others without a ladder row). Rows: 2,407 CS-slot rows, 201 listed names.
- Name variants: "Kirstin Peterson" (one 2017 H1 row) and "Kirstin Petersen" are one ECE person (same profile link `netid=khp37`, same title); the surname differs, which the ordinary matcher and `census-name-aliases.json` `rows` refuse, so the 19 rows are bound through a reviewed `source_names` entry (`hierarchy/cornell/reviewed/census-name-aliases.json`, every row carries its capture URL, sha256, format and quote). "Jose F. Martinez", "Jose Martinez" and "Josè Martinez" were already one person (the display name keeps the source's grave accent). A similarity scan (ratio > 0.82) of the 177 names found no other pair.

## Data steps (Slurm, from commit 167a3b5a / main code)
| step | job | result |
|---|---|---|
| DBLP affiliation pass | 32541742 | 679 dump persons with a Cornell note, 1,265 notes |
| sweep from the snapshot extension | 32541743 | 194,821 works, every year complete |
| sweep check | 32541744 | pass |
| OpenAlex candidates | 32542563 | `cs-related-candidates-openalex.json`, `oa-author-stats.json.gz` |
| units (Wayback, 14 affiliated units) | 32542564 | RUNNING, see below |
- `cs_related_school.py candidates cornell`: **448 candidates** (343 DBLP-affiliation, 105 OpenAlex-rule), `hierarchy/cornell/cs-related-candidates.json`.

## Units: load-limited by the shared Wayback lock (owner answer to Q-0364: keep all 14 units, full recall)
`cs_related_school.py review` refuses without `units-done.json`. The units step fetches one Wayback capture per unit listing URL and year (14 units, about 300 fetches) and, on the shared lock, got about 15 snapshots in 2 h 50 min, so stage 2 is limited by Wayback throughput, not by Cornell work. The step is resumable: `school_web.capture` -> `wb.fetch_capture` reuses a stored capture (not -1/429/5xx) and `wb.cdx` reads the cached query, `W.live` reuses a stored live page, so a rerun refetches nothing. Plan: a serial `afterany` chain of 6 h runs, never two at once: 32542564 (running) -> 32546907 -> 32546911 -> 32546913 -> 32546915 -> 32546917 -> 32546919 (the later ones are quick no-ops once `units-done.json` exists). Review, the `excluded_unresolved` conversion and the 50-row audit draw follow when it completes.

## Update 2026-11-25
- 32542564 timed out at 6 h with 23 captures (INFO 9, STSCI 12, ECE 1, ORIE 1): the rate is load-limited by other schools on the shared Wayback lock (units shares it with Cornell's periods-fetch and the other onboarding schools' steps).
- Owner decision: keep all units and years, change the order only. `cs_related_school.units` now reads every live listing first (13 hosts are live; a current page is a dated capture of its year) and then fetches the current year and 2020 of every unit before the tail (`unit_fetch_order`, test `tests/test_units_fetch_order.py`, commit 94e8790c). The CDX queries and stored captures are reused, so nothing is refetched.
- Never two units jobs at once, and at most two Cornell Wayback fetchers at a time (units plus one other). New serial `afterany` chain of 14 runs: 32550849, 32550851, 32550853, 32550855, 32550857, 32550861, 32550863, 32550865, 32550867, 32550869, 32550871, 32550873, 32550875, 32550877.
