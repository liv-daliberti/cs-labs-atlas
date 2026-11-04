# Georgia Institute of Technology, stage 3: PIs and labs

Date: 2026-11-03. `atlas stage-gate gatech 3 --run --submit --from-worktree` (census-refresh, school-local homes, build, lab-page discover and audit; jobs 32092794-96, then 32096250-52 after the census refresh). Gate: **pass** (456 PIs, 456 homes). The shared `homes-shared` step was skipped (it writes a tracked file of the main checkout; the school-local home file is what the gate reads); nothing tracked was written in the main checkout.

## Counts
- **PIs: 456** (351 from the four College of Computing schools' listings, 105 accepted from other units by the stage-2 review); 455 labs built (`pis.json`).
- **Homes** (from the same listing rows): Interactive Computing 80, ECE 76, ISyE 61, Computer Science 58, CSE 32, ML Center 21, Mechanical Eng. 18, Cybersecurity and Privacy 17, Math 12, Biomedical Eng. 10, LMC 9, CEE 7, Industrial Design 6, Biological Sciences 5, Scheller 5, Aerospace 5, Public Policy 2, Music 2, others 14.
- **Lab-page audit (discover + audit, school-local summary `labpage-audit-summary-school.json`):** 455 labs: 54 lab sites, 175 PI homepage only, 181 no web presence found, 26 profile only, 12 new arrivals, 6 emeritus/admin, 1 site at another institution. Students listed on the audited pages: 3,711 (2,283 current, 1,428 alumni); 747 `genuinely_missing`
  (these feed `labpage-additions.json`, rule LP-STU-01, wired only after the hand-check rounds of stage 6).

## Notes and open items
- **Eight truncated-title PIs need stage-4 bridging** (profile-page titles): C. David Sherrill, Carrie Bruce, Melody Jackson, David Joyner, Peter Swire, Zvi Galil, Dana Randall, Santosh Vempala (stage 2 report).
- **Home departments taken from title text are not clean for 6 people:** "Starting Fall'26" (2), "KUKA Chair of Robotics, and Director of IRIM", "Joint with Wallace H.…", "Joint w/School of Chemistry and Biochemistry", "Joint with School of Literature, Media, and Culture", "College of Architecture"/"Joint with College of Architecture" (3): the charter's `home_units` patterns do not cover them. Fix the patterns (or `hold`) before stage 7; they pass the gate because a home is non-empty. Owner may also want the ML Center (21) as a home: it is a center, not a department.
- PIs of ECE (76) and ISyE (61) enter by the computing-share test; the ML Center "home" (21) is the unit those people were found in.
- Stage 3's gate does not need the owner; the next stages (4 periods, 5 identity) use Wayback and the DBLP dump and are the next work.
