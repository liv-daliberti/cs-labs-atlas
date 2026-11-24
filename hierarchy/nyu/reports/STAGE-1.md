# NYU onboarding, stage 1 - 2026-11-24

Gate: `atlas stage-gate nyu 1` PASS (4 departments, each with a roster source; `roster_years_open` = 38, reported not blocking under the 2026-11-17 ruling).

## Sources and formats (tools/listing_formats.py, tests/test_listing_formats_nyu.py)
- CS (Courant): cs.nyu.edu/dynamic/people/faculty/, format `nyu_cs_dynamic`, 2016-2026 (Wayback has no 2018H1 capture). Live supplement saved (126 entries).
- CDS: cds.nyu.edu/people/ 2016-17 (`nyu_cds_wp_2017`, CDS Faculty group only), then cds.nyu.edu/jointfaculty/ and /clinicalfaculty/ 2018- (`nyu_cds_profile_cards`; Wayback has jointfaculty from 2020-06 only; the 2018-19 and 2025-26 roster years stay open). The host is challenged live (wayback-only). The associated/adjunct/affiliated CDS pages were dropped as non-PI sources.
- CSE and ECE (Tandon): .../computer-science-and-engineering|electrical-and-computer-engineering/people, format `nyu_tandon_cards` (Core, Associated, Research, Affiliated, Emeritus groups; Staff and the Global Network Faculty of other campuses are dropped), Wayback 2018H1- ; CSE moved to .../faculty-and-staff by 2025 (separate slot). Live supplements saved for CSE (73) and ECE (46).
- Tandon 2016-17: engineering.nyu.edu/faculty (24 captures) is a faculty-information page, not a roster; no CSE/ECE roster capture found before 2018-05 among the URLs tried (computer-science-and-engineering/{faculty,people}, electrical-and-computer-engineering/{faculty,people}). Those years stay open.

## Captures
Wayback throughput is about 1 capture per 6 minutes (shared clock with other schools). Job 32542509 was cancelled and the charter reordered (CDS, CSE, ECE first; CS last, it has a live supplement and early captures); job 32542900 (59-min resubmits) continues the backfill. `listing_rows`: CDS 17, CS 154, ECE 46, CSE 72 people so far.
