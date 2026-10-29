# Michigan, stage 1: sources and captures

Date: 2026-10-29. Gate: **passed**. Every department has a usable listing in every year 2016–2026, and each missing
half-year has a recorded reason.

## What was done
- **Discovery.** URL eras found with Wayback CDX, exact-URL queries with `collapse=timestamp:4`. Prefix queries on
  eecs.umich.edu returned 503/504 for minutes and were abandoned.

  | dept | era | URL (CDX key) |
  |---|---|---|
  | CSE | 2016–2019 | `eecs.umich.edu/eecs/faculty/csefaculty.html` (mirrored at `cse.umich.edu/...`); one table, `Division: CSE` |
  | CSE | 2019-09 – 2026 | `cse.engin.umich.edu/people/faculty/` ("All Faculty": tenure-track, teaching, research, courtesy and emeritus in one list) |
  | CSE | 2019-09 – 2026 | `cse.engin.umich.edu/people/faculty/emeritus-faculty/` (cross-check) |
  | ECE | 2016–2019 | `eecs.umich.edu/eecs/faculty/ecefaculty.html` |
  | ECE | 2019-09 – 2020 | `ece.engin.umich.edu/people/faculty/` |
  | ECE | 2020 – 2026 | `ece.engin.umich.edu/people/directory/faculty/` |

  These are the charter's `[[departments.listings]]`. Entries that share a slot name are URL eras of one slot.
- **Capture.** `listings/scripts/run_school.sh michigan` ran `plan_fetch.py` with the charter's slots. It takes one
  capture per slot and half-year, H1 and H2, into `listings/michigan/captures.sqlite`: 61 captures and 7 CDX answers.
  - The first pass accepted three spring captures of the CSE list (2023, 2024, 2025) that are 31 KB script-rendered
    shells with no people. They passed the old usability test because the navigation has title-like lines.
  - `plan_fetch` now requires a charter school's capture to parse to at least 5 people (`charter_usable`). The shells
    were re-planned; 2025 H1 found a full capture, 2023 H1 and 2024 H1 have none (their H2 captures are used).
- **Parsing.**
  - `tools/listing_rows.py michigan` parsed 54 captures with the two formats in `tools/listing_formats.py`: `eecs_table`
    for 2016–2019 and `eecs_wp` for 2019–2026. From 2018 the old table puts the name in `<b>`; from 2025 the new site
    puts it in `p.eecs_person_name`.
  - Result: 5,634 rows, 287 CSE people and 312 ECE people. Contact lines (email, phone, office) are never kept.
- **Other captures.** Probes, robots files and unit listings for stage 2 are in `captures/michigan.sqlite`.

## Coverage (`listings/michigan/coverage.json`)
| dept | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CSE all faculty | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H2 | H2 | H1 H2 | H1 |
| CSE emeritus | – | – | – | H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 |
| ECE all faculty | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 H2 | H1 |

## Exceptions with reasons
- **CSE 2023 H1, 2024 H1:** `unusable`. Every capture in the half-year is a script-rendered shell (0 entries). The
  year is covered by its H2 capture.
- **CSE emeritus 2016–2018:** `nocapture`. The page did not exist before the 2019 site; the old list carries emeriti
  inline.
- **CSE emeritus 2019 H1:** `nocapture`. The page started in September 2019.
- **2026 H2, all slots:** `nocapture`. The half-year is in progress; the last captures are April–May 2026.

## Gate
Every department has a usable listing for every year 2016–2026. Each missing half-year carries its plan reason.
**Pass.**

## Protocol notes (folded into `docs/ADDING-A-SCHOOL.md`)
- Listing captures live in `listings/<key>/captures.sqlite`, the listings-pipeline schema that the period tools read.
  Everything else goes in `captures/<key>.sqlite`.
- Use exact-URL CDX queries with `collapse=timestamp:4` for discovery. Prefix queries on a large host time out.
- A usable listing capture must parse to people, not just look like one.
