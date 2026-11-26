# UMD stage 1: sources and captures (2026-11-24, worker claude-umd-1124)

## What was done
- Format: `umd_cs_faculty` in tools/listing_formats.py (fixture test tests/test_umd_cs_faculty.py). www.cs.umd.edu/people/faculty is one page with every category under h3 headings; 2016-17 is a table grid, 2018- a bootstrap card grid. Three slots keep each category its own kind so affiliates never rank as ladder: `umd_cs_main` (CS, Emeritus, Visiting faculty; kind main), `umd_cs_affiliates` (courtesy), `umd_cs_adjuncts` (adjunct). Post-doc/research-assistant sections are in no slot.
- Captures: Slurm job 32541527 (cs-stage1-umd-captures, from commit dd6c1a67), COMPLETED rc=0 in 1h21m, "umd unplanned slot-halves: 0". Wayback only; 95 CS captures exist 2016-2026.
- Rows: `listing_rows.py umd`: 2,831 rows, 245 listed names (CS); 1,833 main + 650 courtesy + 348 adjunct. Ranks: ladder 1162, courtesy 606, adjunct 348, lecturer 310, emeritus 294, visiting 46, research 37, teaching 14, other 14. No truncated ("...") titles.
- Main-slot people per year: 2016 73, 2017 84, 2018 88, 2019 89, 2020 89, 2021 93, 2022 92, 2023 99, 2024 106, 2025 114, 2026 115.

## Coverage
All 66 slot-years are ok except six slot-halves with a recorded reason `nocapture: no archived 200 capture of the listing URL(s) in this half-year`: 2019H1 and 2020H1 for each of the three slots. The year is still covered by its H2 capture. Per the 2026-11-17 owner ruling these stay listed as open metric, not a blocker; no waiver was written.

## Affiliated units (found while sizing stage 2; Wayback exact-URL checks 2026-11-24)
Captured at stage 2 (`cs_related_school.py units`), not at stage 1, because affiliated units are plain-string listings outside plan_fetch. The stage-2 run is submitted from HEAD >= 0ffbe56e, so the UMIACS 2016-2025 URL (www.umiacs.umd.edu/people/faculty, 81 captures) is included; the capture job at stage 1 (dd6c1a67) did not need it.
- ECE ece.umd.edu/faculty 2016-18, clark/facultydir 2019-26; iSchool ischool.umd.edu/people 2016-19 (+ /faculty 2016-17), info.umd.edu/directory 2026; MATH www-math.umd.edu/people/faculty.html 2016-26; ISR clark/facultydir 2019-26; PHYS 2016-26 with gaps; ME 2024-26 only; AERO 2018-26; CEE 2018-26; BIOE 2019-26; LING 2020-26; PSYC 2025-26; RHSMITH 2016-26; ESSIC 2024-26; CISESS 2019-26; UMIACS 2016-25 (old URL) + 2025-26.
- Hosts with use = none (quics, jqi) or wayback-only (arlis, mqmc, robotics) have no live unit listing.

## Gate
`bin/atlas stage-gate umd 1 --record`: pass, 0 open, `roster_years_open` 0.

## Census (stage-2 first step, `census_build.py umd`)
242 persons, 101 PIs (ladder_faculty 99, courtesy_faculty 2), 141 not PIs at this point (lecturers, emeriti, adjuncts, visiting without ladder evidence). Counts are before the computing-related candidates review.

## Exceptions
None.
