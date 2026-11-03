# University of Chicago, stage 4: periods

Date: 2026-11-03. Gate (`atlas stage-gate uchicago 4`): **pass** (124 PIs: 102 contiguous listings, 10 reviewed periods, 12 gaps reviewed as unproven).

## What was done
- `periods_school.py fetch|extract|gaps|extend` (jobs 32085593-32085596, Wayback pace and robots rules): 7 PIs got reviewed periods from dated captures closing their gap years.
- 12 PIs keep a gap year no dated evidence closes, recorded as `unproven_years` + `why_unproven` in the school's override file (R-PAP-01: papers of those years stay outside the appointment):
  11 CS PIs for **2017** (the only 2017 capture of the CS directory is page 1 of a paged list, 5 of about 45 people; later pages are archived only from 2019), James A. Evans (2021-22), Shmuel Weinberger (Mathematics 2022).
- Overrides live in `hierarchy/uchicago/reviewed/census-overrides-school.json` (friction 31), not in the shared tracked file.

## For the owner
- The 2017 gap is the main judgement: these eleven were listed in 2016 and 2018 and plausibly were faculty in 2017, but the project never infers appointments from roster years. Alternatives: accept as recorded, or find 2017 evidence (FPO lists, news).
