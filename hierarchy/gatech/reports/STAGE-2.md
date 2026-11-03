# Georgia Institute of Technology, stage 2: faculty census (run to the hand-review step)

Date: 2026-11-03. `atlas stage-gate gatech 2 --run --submit --from-worktree` ran census, DBLP pass, sweep from the snapshot extension, sweep check, OpenAlex candidates (jobs 32090692-95, all COMPLETED), then
candidates and the cross-check locally. It stops at the `review` hand step; the gate is open on 957 candidates with no decision (expected).

## Numbers
- **Census:** 1,375 persons, **215 PIs** (all `ladder_faculty`, from the four College of Computing schools' listings; 6,928 listing rows).
- **Sweep from the extension:** 92,032 works 2016-2026 (no API credit). Sweep check: pass, no trips (every year complete, duplicate id rate 0, DOI 0.08%, institution share 1.0).
- **DBLP pass:** 1,142 dump persons name the school (1,964 notes, 826 not matching the regex; the regex was tested against DBLP notes at stage 0).
- **Candidates (957):** 531 DBLP-affiliation, 274 from the affiliated departments (ECE, ISyE ladder faculty), 152 from the OpenAlex rule.
- **Cross-check (listed, not in census):** 10 names, 3 ladder, 0 likely-missing PIs.
- **Units captured** (`cs_related_school.py units`): 32 Wayback + 3 live captures for ML, Math, BME. The BME listing URL is still the homepage placeholder and its 2022-2025 captures are shells (0 blocks); ML and Math lists must be read before the review.

## What the hand review must do (next)
1. Decide every candidate (`cs_related_school.py review gatech`), with the share test for pending and OpenAlex candidates.
2. **Cybersecurity and Privacy.** The school's listing rows now exist for 2025-26 (28 and 31 names); 2023-24 are reviewed gaps. People hired into it in 2023-24 reach the census only through the DBLP and OpenAlex candidates above: check each CSP name against them.
3. **Truncated titles.** 159 of 976 gt_card rows of the four schools in 2023-26 carry an ellipsis (CSE 37 of 214, IC 50 of 479, CSP 38 of 83, CS 34 of 200) and read as unranked in that year; confirm that every PI they hide has ladder rows in an adjacent year or a profile-page title (stage 4 bridging).
4. Find the BME and other unit faculty URLs, add to `[[affiliated_units]]`, re-run `units`.
