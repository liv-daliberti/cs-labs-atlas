# UMD stage 3: PIs and labs (2026-11-24/25, worker claude-umd-1124)

Per-PI process v4: stage 3 ran as soon as stage 1 passed; stage 2 (computing-related candidates review) is still open, so the PIs it admits get stage 3 afterwards (census-refresh, homes, build, discovery for the new PIs only).

## What was done
- Census at this point: 240 persons, 99 PIs (97 ladder, 2 courtesy). Name defects fixed first by reviewed `source_names` (census-name-aliases.json, 55 evidence rows): Zaoxing Liu / Alan Zaoxing Liu, Zhicheng Liu / Leo Zhicheng Liu (one person each, same profile page), "Hal Daumé III." (period) and "Rance Cleaveland (1961-2024)" (year range).
- Homes (`home_departments_school.py umd`, school-local; shared write done by the coordinator with owner approval, 99 umd rows, diff touched only umd): 99 accepted, 0 held: 97 Computer Science, 1 Linguistics, 1 Electrical and Computer Engineering (John Baras, reviewed override with two dated ECE directory quotes, census-overrides-school.json).
- Build (pi_hierarchy, job 32543977, rerun 32548073), lab-page discovery x8 (32543978, rerun 32548074 for the two renamed PIs only), merge (32543979, 32548075) and audit (32543980, 32548076): all COMPLETED rc 0. Orphan discovery records of the four removed names were dropped (101 -> 97 records, backup in hierarchy/umd/tmp/) before the rerun.
- Websites (register reviewed/lab-websites.json, `lab_websites.py build umd`): 99 labs, 47 with a website, 52 with a recorded reason, 0 neither, official provenance complete. Reviewed in person-website-review.json: Alan Zaoxing Liu (homepage https://zaoxing.github.io/ replaces a department news article), Zia Khan (listed 2016-2017; old UMD homepage address now redirects to Princeton's "This person has moved" page: `pi_left_school_site_moved`).
- Audits (independent reviewers, not the worker): homes (seed bd9d1ec78ed3, 50 of 99, hash 80bc78fdaa77402a): reviewer claude-umd-audit-homes-1125 recorded 49 pass, 1 fail (Baras, since fixed by the override: the row changed, as the audit rule allows). Websites drawn: seed 10bd4a7457ec, 50 of 99, hash 084390eea2ff879f; review pending.

## Gate
`stage-gate umd 3` (dry run, 2026-11-25): one open item, "websites audit missing" (the draw exists; the independent verdicts are not recorded). Not recorded as passed.

## Friction items
- **Courtesy-home rule took a role string as a unit.** `home_departments_school.py` read a courtesy row's text after the first comma as the home unit. For Baras that text is a role ("Lockheed Martin Chair in Systems Engineering, Director HyNET, Founding Director, ISR"), and the professor-title fallback then read the courtesy row's second title and gave "Computer Science". Fixed for onboarding schools: a courtesy home counts only when it names a charter department, affiliated unit or [census].home_units name (`courtesy_home_ok`, tested), and courtesy-slot rows no longer give a home in the fallback. Baras was the only UMD PI affected.
- **The gate's in-memory register build does not apply reviewed website decisions** (`verify_websites` runs only in `lab_websites.py build`): a reviewed website_found or absence row has no effect on gate 3 until the register file is rebuilt with `lab_websites.py build <key>`.
- **census_build source-name evidence** failed for sites with relative profile links (UMD links '/people/hal3'): fixed by resolving them against the Wayback original URL (`wayback_original`).
- Slurm array requeues: node016 /tmp was full for the stage-0 snapshot filter; three filter tasks hit the 59-minute cap under contention and were rerun.

## Exceptions
None. The labpage-additions.json proposal file written by the audit is unreviewed and not committed.
