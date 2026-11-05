# Georgia Institute of Technology, stage 10: release (prepared, not applied)

Date: 2026-11-05. Prepared on agent/gatech by the stage-10 commit (the last one on the branch, so the earlier commits can land first): `schools/gatech.toml` `status = "released"`, `stage = 10`; `paths.sh` regenerated (`CS_ATLAS_SCHOOLS` ends in `gatech`). Landing and the rebuild wait for the running 7-school release.

Checks: `bin/atlas test` with the released charter: 1034 passed, 9 skipped, rc 0. A scratch census rebuild of Michigan (the one protocol school the census builder serves) with this branch's code is byte-identical to the released one (454 persons); the six pre-protocol schools do not run any code changed here except R-PAP-31 (about 100 rows across the eight packages change at their next rebuild).

## Gates at release time
2, 3, 4, 5, 6, 7, 9 pass; **8 does not** (copies 42.1% of 21,013, ceiling 53.3%; ledger complete: 46 incomplete_check). Student coverage is unmeasured (no thesis source yet). The lab-page students: 73 of 447 labs have students (reasons recorded for the other 374: sources_exhausted 311, appointment_ended_early 37, new_hire_2025_or_later 26).

## Site handoff needs (Codex)
- `schools/gatech.toml [site]` already maps the four College of Computing schools (CS, IC, CSE, CSP); `site_uni = ""` is empty and must be set to the site's university key.
- Site builder tables (Codex's checkout): `SCHOOLS`, `FULL_CODES` (CS, IC, CSE, CSP), `CORE`, the department mapping for the 19 home departments (College of Sciences, Engineering, Design, Business, Liberal Arts units appear as home departments of the 452 PIs) and the page copy.
- Reader: host only CC*/PD copies, link the rest (docs/DECISIONS.md); at 42% copies most papers are links with the ledger reason.
- Not in the release yet: GTRI, Georgia Tech-CNRS and Georgia Tech-Europe are inside the lineage (coordinator call 11-04); theses (live crawl 32103184 and Wayback crawl 32104467 still running; adviser relations to be wired as a student source when evidence passes the bar); `ai-writing/*` school tuples (owner decides whether Georgia Tech joins the study).
- Hugging Face upload and GitHub export follow the release (`hierarchy/rebuild.sh`, then the export).
