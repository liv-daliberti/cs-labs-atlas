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

## Review result (2026-11-03; `atlas stage-gate gatech 2`: **pass**, 0 open)
`cs_related_school.py review gatech` decided all 957 candidates: **216 accepted** (80 become census additions, `census-additions.json`), 77 faculty_not_computing, 61 too_few_school_works (new or recent faculty: revisit at the next sweep),
581 not_faculty_listed (479 are DBLP-affiliation records of students, postdocs and staff), 8 census_alias, 2 research_or_other_rank. The share test decided the pending and OpenAlex-rule candidates (OpenAlex rule: 45 accepted, 106 not_faculty_listed).
Evidence needed units: the charter now searches 15 affiliated units (ML, Math, BME, ME, AE, CEE, ChBE, MSE, Biological Sciences, Psychology, Physics, LMC, Public Policy, EAS, Scheller) after the first review searched 3 and wrongly
settled 141 OpenAlex-rule candidates as not faculty; `units` now follows the pages of paged unit directories (47 pages) and runs as a stage-2 step (job 32092569, 145 Wayback captures).

## Checks asked for
1. **Cybersecurity and Privacy.** 32 names are listed in 2025-26: 26 are census PIs, 6 are research / teaching / other-rank (Chhotaray, Crooks, Perullo, Chung, Swire, Mertoguno), none is missing. People hired in 2023-24 and
   not on a 2025-26 page would come from the DBLP / OpenAlex candidates: none of the accepted additions is a CSP-unit person, so no hire is known to be missing.
2. **Truncated titles.** 38 people have an ellipsis title in 2023-26; 30 have ladder rows in the same or an adjacent year. **8 need stage-4 bridging** (profile-page titles): C. David Sherrill (2024-26), Carrie Bruce (2023-26, no ladder row at all),
   Melody Jackson (2024-26), David Joyner (2023-26, none), Peter Swire (2025-26, none), Zvi Galil (2024, 2026), Dana Randall (2024), Santosh Vempala (2024, 2026).
3. **Unit URLs.** 13 units added (BME `bme.gatech.edu/bme/faculty`, ME, AE (two URL eras), CEE, ChBE, MSE, Biological Sciences, Psychology, Physics, LMC, Public Policy, EAS, Scheller); hosts gate: 26 hosts, 0 inconsistent.

## Open for the owner (not blocking the gate)
- **Evidence-limited faculty.** 106 OpenAlex-rule candidates stay `not_faculty_listed`; most are students, postdocs and GTRI/Emory/GSU staff, but about 25 look like Georgia Tech faculty whose unit pages are script shells in Wayback after 2020-23 (Math, Scheller,
  ME, CEE, ML) or whose unit is not searched yet: Wenjing Liao, Rose McCarty, Konstantin Tikhomirov, Chi Hoi Yip (Math); L. Beril Toktay, Eric Overby, Karthik Ramachandran, Basak Kalkanci (Scheller); Robert C. Wilson, Anna A. Ivanova (Psychology);
  Thomas Lodato, Alexander Zook (LMC); Jason Borenstein, Jan Youtie (Public Policy); Joseph M. Le Doux (BME); Hakki Mert Torun (ECE); Athanassios Economou (Architecture); Claire Arthur (Music); Jon Sanford, Leila Aflatoony (Industrial Design/Architecture).
  Recommendation: decide them from their profile pages in the stage-4 period tool (`[periods].profile_patterns`) rather than the shell captures, and add Architecture, Music and Industrial Design to the searched units; the owner may instead accept them as out of the census.
