# WashU supported partial package — 2026-11-07

Result: built and manually reviewed; release status and publication remain with the coordinator.

Landed inputs: saved historical/live faculty listings; 22 explicit faculty appointments; reviewed OpenAlex identities; three temporary identity holds; 33 manually sourced student-lab pairs. Unknown history is not interpolated.

Numbers: 249 listing rows, 156 census faculty, 37 included PIs, 22 periods, 32 distinct students, 33 lab-student pairs, 1,351 lab-paper rows, 1,189 unique works, 77 student-paper links; five labs have the complete supported chain.

Current roster: 30 included PIs have current CSE ladder rows; two have other current rows; five are historical-only. Andrew Witt, William Richard and Jerome Cox Jr. remain identity holds, with their faculty evidence preserved. No identity failure is waived.

Owner decision: “lets add what we have / release what we have for washington university, harvard, and JHU (and then keep working on improving them)?”

Exact completeness exceptions retain all open items: stage 1 has 28 missing department-years; stage 2 has 155 undecided CS-related candidates; stage 3 lacks the exhaustive lab-page audit; stage 4 has nine PIs with sourced listing years but no continuous period; stage 6 lacks exhaustive acceptance and has 31 unexplained student-coverage cases; stage 7 lacks exhaustive acceptance and has two snapshot-limited zero-paper cases. None admits an unsupported record or appointment year.

Gates 5 (identity), 8 (copies/ledger/capture store) and 9 (accuracy) pass without exceptions. Stages 1/2/3/4/6/7 use exact finding allowlists, with zero unmatched findings. Stage 10 remains the coordinator's release step.

Precision: deterministic final draw, seed 20261029; uniform lab claims 25/25 correct (Wilson 95% 0.867–1), all lab strata 35/35; uniform student links 25/25 (0.867–1), all strata 40/40; true sampled DBLP lab papers present 15/15 (0.796–1). Student coverage has no measured thesis cohort and is null. These are sample measurements, not exhaustive precision or historical-coverage guarantees.

One sampled duplicate was corrected by a general edition rule: identical year and complete ordered normalized byline, with the work-in-progress label moved between title and subtitle. IEEE DOI 10.1109/emsoft.2018.8537230 leads; ACM mirror 10.5555/3283535.3283542 remains in editions for both Chamberlain and Gill. No real paper was labeled a non-paper.

Evidence check: zero violations for all 22 periods, 93 faculty listings, 33 student relations, 1,351 paper school/appointment claims, and 77 link byline/relation claims. Zero missing or stale ledger entries. Only availability completeness remains: 732 incomplete checks.

Availability: 1,189 ledger entries; 732 incomplete_check and 457 found_not_in_catalog. No local copies, no final exhausted-search findings. Missing checks: DBLP 1,189; lab pages 1,189; OpenAlex/repository 1,185 each; S2 1,155; CORE 987; Wayback ACM 187; PMC 3. The coordinator owns the finite owner-authorized availability exception; all missing/stale/attribution categories remain hard failures.

Zero-paper reasons: Jonathan Turner has no admitted row in supported listing years under the stored sweep/DBLP evidence; the unrelated environmental scientist Jay R. Turner is rejected. Ian Bogost has no admitted row in the supported appointment from 2021-07-01 through the captured 2026-11-06 observation under the stored sources. Both findings are snapshot-limited and additional recovery remains open.

Validation: final offline Slurm job 32138159, committed snapshot 171c98a, completed 0:0 in 1:07, peak RSS 3,132,604 KiB; 20 schema files checked, zero violations. Edition regression suite: 68 passed, including published-placeholder versus arXiv priority. All 12 charters pass configuration checks. Coordinator integrated suite previously passed 1,362 tests.

Caveats:
- Historical listings and cross-department scope remain incomplete; nine included PIs use only individually supported listing years.
- Student discovery covers five labs; Danni/Danielle Beaulieu remains an unaccepted possible alias, and no alumni from another institution were inferred.
- Final release must rebuild against canonical recovery inputs and clean main provenance, then redraw/rebind accuracy hashes after verifying sampled keys and evidence; overlay snapshot provenance is not a clean-main release claim.

Files: `hierarchy/washu/reviewed/` holds decisions; `accuracy/{sample,verdicts,summary}-washu.*` binds the measured package. Canonical raw data and built outputs are in `/n/fs/resemble/homogenizing-science/code/hierarchy/washu/{raw,derived}/`; receipts and evidence sheets are in `/n/fs/resemble/homogenizing-science/code/hierarchy/washu/tmp/partial-20261107/`.
