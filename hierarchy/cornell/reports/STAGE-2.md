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

## Blocker (owner question Q-0364)
`cs_related_school.py review` refuses without `units-done.json`. The units step fetches one Wayback capture per unit listing URL and year (14 units, 2-ish URLs each, 11 years, about 300 fetches). On the shared Wayback lock it captured about 15 snapshots in 2 h 50 min (INFO and STSCI through 2019), so it will hit its 6 h limit with roughly 10 percent done. Recommendation filed: trim `[[affiliated_units]]` to INFO, STSCI, ECE, ORIE, Cornell Tech and CB (one URL each) and add the rest when Wayback is quiet; candidates from dropped units become `excluded_unresolved` and go to the 50-row audit.

## Not done
Review of the 448 candidates, `excluded_unresolved` conversion and the 50-row audit draw (`excluded_audit.py draw cornell --worker claude-cornell-1124`) wait for the units decision. Gate 2 fails only on the missing review/candidate decisions.
