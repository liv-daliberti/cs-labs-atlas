# University of Chicago, stage 7: papers and links

Date: 2026-11-03. Gate (`atlas stage-gate uchicago 7`): **1 open of 2**: the lab-page papers acceptance is accepted (round 5); the chain audit's `links` check has **47 of 447 students unexplained** (below). Stages 2-6 pass.

## D3 final ("related", owner 2026-11-03), applied
Argonne National Laboratory and its four facilities, Evanston Hospital and CZ Biohub Chicago count for UChicago only with a raw affiliation naming the university or a cited joint appointment. Charter: the seven ids moved into `openalex_related`. One mechanism per layer, each with a test:
- **snapshot filter** (`oa_snapshot.related_gates`, `keep_work(rel=)`, per affiliation: a joint UChicago + Argonne byline keeps its UChicago hit, an Argonne-only authorship needs the regex);
- **extension re-filtered** (16 tasks + merge; 412,159 -> 299,398 works) and **the sweep re-run from it** (124,924 works; sweep check pass);
- **candidate rule** (`cs_related_candidates.school_test`): 103 Argonne-staff candidates drop out; the review re-run gives the **same 51 accepted** and the same 23 additions;
- **builder** (`pihier.common.gate_related`, applied once in `sweep_works`): the school id is taken out of an Argonne-only institution's lineage on a copy of the authorship unless the raw string names the university or the PI has a cited `joint_appointments` entry: **Chien, Foster, Stevens** (department listing quotes, 2016 capture).

## What stage 7 did
- `pi-works` from the snapshot (no OpenAlex credit; 207 author ids, 11,428 works), `dblp-recover` (14 papers recovered from arXiv page 1), the lab-page paper pass `labpage_audit recover` + audit (no OpenAlex key in the job): 262 listed lab-page papers were already lab papers, **28 proposed additions**, hand round 5 (seed 20261109, 20 of 28): 0 errors, 2 doubtful (1.0): accepted. `labpage-recover` (the stage's own tool) needs `labpage-pubs.jsonl.gz`, which no step produces for a charter school (friction 52); the audit's recover covered it.
- Lab-page students regenerated: the first regeneration proposed 158 rows from department rosters (the Statistics alumni page and TTIC's alumni list filed under PIs not on them); the page-lacks-PI rule now applies to charter schools and an entry that names another adviser is dropped: 32 proposals, round 6 (seed 20261112): 0 errors, accepted. 32 students and 28 papers are wired and the acceptance re-stamped.
- Builder rebuilt, link diagnosis (new `atlas pipeline link-diagnosis`), student audit (school-local).

## Per-lab coverage (`LAB-COVERAGE.md`, `tools/lab_coverage.py uchicago`)
134 labs: **64 with students** (447 student relations), **124 with papers** (4,849 lab papers; per lab min 0, quartiles 8 / 21 / 52, max 409). Reasons recorded: 0 students: `sources_exhausted` 59, `new_hire_2025_or_later` 7, `appointment_ended_early` 4; 0 papers: `no_school_affiliated_works` 4, `new_hire_2025_or_later` 4, `no_identity` 1 (Dupont, Rogers, reasons in the overrides), `appointment_ended_early` 1.

## Open: 47 links unexplained (students with no linked lab paper)
12 undergraduates and 19 advisees starting 2025+ and 16 labs with no papers are already explained; the 47 left are 38 students of 2016-2022 whose lab has papers in their years (no link, no school work under the name) plus 9 recently listed (Doiron and Casillas labs, Tulsiani). Among them name noise from the TTIC and lab-page lists: "Research Fellowship Lingyu Gao", "PhD Fellowship Falcon Dai", "Microsoft Taehwan Kim", "Caltech Zhiyong Wang", "Structured Prediction Shubhendu Trivedi", "Nick Collins Delta Dictionaries", and a non-student (Samir Khuller, a co-adviser at another university). Next step: a name cleaner for these label prefixes and a drop for faculty names, then link diagnosis again; or an owner call that 2016-2018 students without a link are reasoned `no_link_found`.

## Owner decisions open
1. The 47 links (above), and whether `sources_exhausted` (59 labs, weak) is accepted at stage 6/7.
2. OpenAlex credits for the lab-page title search (`labpage_audit recover` ran without the key; titles it could not resolve stay `unresolved_metadata`, 44).
3. 2017 CS gap: re-check after Georgia Tech's R3 lands.
