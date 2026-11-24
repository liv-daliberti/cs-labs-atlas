# Cornell onboarding, stage 1 (sources and captures) - 2026-11-24

## Sources

One full-coverage department: Computer Science (Ann S. Bowers College of Computing and Information Science). Its directory is the Bowers CIS Drupal directory shared with
Information Science and Statistics and Data Science, and it lists "CS Field Members" (faculty of ECE, ORIE, Information Science, Cornell Tech and others) next to the
CS-department faculty; the line after the rank names the home department, kept as a title. Every other unit is an affiliated unit (stage-2 discovery source), as at UMD and UCSD.

URL eras of the `CS faculty` slot (exact-URL CDX, `discover_listings.py`):
| era | URL | captures |
|---|---|---|
| 2016-01 .. 2025-07 | www.cs.cornell.edu/people/faculty | 95 monthly captures, every half-year 2016H1-2025H1 |
| 2025-08 .. | www.cs.cornell.edu/directory/index (one page, 144 cards) | 5 captures 2025-08-22 .. 2026-06-12 (2025H2, 2026H1) |
| not used | www.cs.cornell.edu/directory (20 per page, `?page=N`) and /current-faculty | 12 and 10 captures from 2025-08; the faculty index replaces them |

Three page formats, written before the captures (`tools/listing_formats.py`, fixtures in `tests/test_cornell_listing_formats.py`):
`cornell_cs_legacy` (2016-2017, `div.person`, title lines up to the Ph.D. line), `cornell_cis_directory` (2018-2025, `div.person-listing` with `h6` name and `strong/span.inline-field`
titles; 2024- nests a second `div.person-listing`), `cornell_cis_index_cards` (2025-08-, `div.directory-card`; name, position titles, College/Department and Profile Type lines).
The charter names the index format for the last era and detects the other two.

## Captures and rows

- Captures: `listings/scripts/run_school.sh cornell` ran locally, nice, on the shared Wayback clock (about one capture per 10 minutes while other schools were fetching): no Slurm job, 22 slot-halves, `unplanned slot-halves: 0`, finished 2026-11-24 15:52 EST. (The first run was killed by a session end and resumed; plan rows are resumable.)
- `tools/listing_rows.py cornell`: 2,407 rows, 201 people (all CS slot). Captures parsed: cornell_cs_legacy 2, cornell_cis_directory 18, cornell_cis_index_cards 1. No capture without entries.
- People per half-year: 83 (2016H1), 95 (2017H2), 107 (2019H2), 116 (2021), 123 (2023H1), 140 (2024H2), 143 (2025H1), 142 (2025H2), 132 (2026H1: index lists 144 cards, the Emeritus and Field profile types included).
- Ranks of the 2,407 rows: ladder 2,137, lecturer 118, emeritus 102, research 28, visiting 12, adjunct 6, teaching 3, other 1. 1,445 rows carry a "Computer Science" department title; the rest are field members whose home is another unit (and 2016-2017 rows that list only a rank).
- Open metric: 2026H2 has no capture yet (the index page is archived through 2026-06); no year is partial or uncovered in `coverage.json`.

## Gate

`atlas stage-gate cornell 1`: **pass** (0 open, 1 department, `roster_years_open` 0, no gap waivers).
