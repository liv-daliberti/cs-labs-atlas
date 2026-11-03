# University of Chicago, stage 3: PIs, home departments, lab-page audit

Date: 2026-11-03. Gate (`atlas stage-gate uchicago 3`): **pass** (124 PIs, 124 accepted home departments, lab-page audit written).

## What was done
- `census_build.py` re-run after the stage-2 review (the 23 additions get person records only then, PROTOCOL-FRICTION 28): 270 people, 101 census PIs + 23 additions = **124 PIs**.
- Home departments (`home_departments_school.py`, school-local file; the shared `hierarchy/home-departments.json` was NOT written): Computer Science 66, TTIC 22, Booth 18,
  Statistics 13, Mathematics 3, Data Science 2. All accepted, none on hold. Every PI is a ladder professor (basis `ladder_faculty`), so no research/teaching basis review was needed.
- Builder (`pi_hierarchy.py uchicago`, job 32085440, wired charter): 124 PIs, 0 without a person, 124 new labs. It runs before periods and identity, so its paper counts are provisional.
- Lab-page audit: discover 32085476 (9 min, robots.txt and Crawl-delay honoured, no challenges), audit step offline.

## Owner decisions
None open for stage 3. Stage 2 notes about Mathematics logic/topology additions and unsearched units stand.
