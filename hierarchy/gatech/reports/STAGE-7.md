# Georgia Institute of Technology, stage 7: papers and links

Date: 2026-11-04. Gate (`atlas stage-gate gatech 7`): **pass** (0 open: the lab-page papers acceptance is accepted, the chain audit's `papers` and `links` checks pass). Stages 0-6 pass.

## What stage 7 did
`atlas stage-gate gatech 7 --run --submit --force --from-worktree` (jobs 32102064-69, then 32103003-04 and 32103046-47):
- **pi-works** from the OpenAlex snapshot extension (no API credit), **dblp-recover** (7 papers from DBLP/arXiv page 1), the lab-page paper pass **`labpage_audit recover` + `audit`** (no OpenAlex key in the job; the stage table now uses these two steps instead of `labpage_recover.py run`, which needs a file no step produces for a charter school: UChicago's finding), **build** (`pi_hierarchy.py`), **link diagnosis**.
- **Counts:** 449 labs (Apostolico excluded), **22,810 lab papers** (median 31 per lab; 431 labs with papers), 5,240 lab-page papers listed in 2016-2026, 2,764 already lab papers, **291 proposed additions**. Identity basis of the lab papers: PI ORCID 14,354, reviewed OpenAlex id 3,615, DBLP person page 2,542+542, anchored author id 1,368, lab-page listing 266.
- **Hand round 6 (papers; seed 20261110, 20 of 291; bar: at most 1 error, doubtful 0.5):** 0 errors, 1 doubtful (Qi Tang: the page entry parsed as the venue "SIAM Journal on Scientific Computing 2026", so the match is by DOI and the OpenAlex authorship) = **0.5: accepted**. Each row was read for: PI on the byline, Georgia Tech on the paper or its page 1, the listed title the same work, a listing or period covering the year. 291 papers wired.
- **Students:** the 734 accepted lab-page students (round 5) are wired; 742 students, 760 student-lab pairs, 2,049 student-paper links in 68 labs. Student audit (school-local): 0 within-lab pairs, 0 across-lab people.
- **Labs:** 449; with students 73, with papers 431. Zero-paper reasons: emeritus_throughout 2, appointment_ended_early 10, no_identity 2, new_hire_2025_or_later 4.

## Owner points
- **Unresolved titles:** 1,252 listed lab-page papers are `unresolved_metadata` (no OpenAlex, arXiv or proceedings match without the API key) and 3 `not_yet_resolved`. `labpage_audit recover --title-credits N` would spend OpenAlex credits (UChicago spent about 100 for 9 resolutions); not spent here (shared 10k/day key). Say if you want a bounded spend.
- **D2/D3 at stage 7 (GTRI, Georgia Tech-CNRS, Georgia Tech-Europe stay in the lineage sweep):** no change applied. GTRI's raw affiliation ("Georgia Tech Research Institute") matches the Georgia Tech regex, so GTRI-only works are not removed by a `related` gate (unlike UChicago's Argonne); GTRI staff are not PIs unless GT-listed (stage 3). Confirm or ask for an exclusion.
- **Students under the strict `links` check:** 313 of 742 students have no linked lab paper (`student_audit`): mostly lab-page students of 2024-26 and undergraduates; the chain audit's `links` check passes through the lab-coverage reasons.

## Fixes made here (tests): see PROTOCOL-FRICTION rows 35-37
