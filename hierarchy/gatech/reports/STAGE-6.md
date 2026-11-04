# Georgia Institute of Technology, stage 6: students

Date: 2026-11-04. **Gate: fail** (`atlas stage-gate gatech 6`): the lab-page students were not accepted after the four rounds of the normal limit, and 377 of 450 labs have neither students nor a recorded reason. Per-lab table: `LAB-COVERAGE.md` / `.json` (`tools/lab_coverage.py gatech`).

## Sources, in the protocol's order
1. **Thesis repository: probed, not usable at scale.** SMARTech is now `repository.gatech.edu` (DSpace 7). robots.txt has only a `*` group (no AI-agent rules), Crawl-delay 10; it disallows `/server/oai/*` (OAI), `/search`, `/browse`, `/items/*/full`, `/entities/*/full`. An item page (`/entities/publication/<uuid>`) is allowed and carries "Advisor(s)", but the only enumeration left is the sitemap: 95,212 item URLs, undifferentiated, so the advisor field would cost one 690 KB page per 10 s (about 11 days) with no way to select College of Computing dissertations. Skipped (same call as UChicago's Knowledge@UChicago).
2. **Adviser-bearing directories: none.** The College of Computing school sites list PhD students without advisers (`/people/phd-students`, 12 cards a page, not archived at those URLs); ISyE, Psychology and the CoC-wide `/people/phd` list names and programs only; ECE, ME, MSE, ChBE, AE directories name no adviser. CoC defence announcements exist in Wayback only for 2012-13 (`/events/phd-defense-dissertation-<name>`), none for 2016+.
3. **Names-only rosters + co-authorship (R-STU-02, strict rule):** the CoC PhD list (`www.cc.gatech.edu/people/phd`, 2020-2026, paged), `www.scs.gatech.edu/people/students` (2016-2019), ISyE `/people/phd-students` (2019-), Psychology all-graduate-students: **27 student-PI relations in 4 labs** (new `paged` option: a roster capture's other `?page=N` / letter pages of the same year are read, test).
4. **Lab pages and PI homepages (stage-3 audit, 454 labs):** 54 lab sites, 175 homepage-only; 813 proposed additions in 70 labs after the rule fixes (747 before). **Not wired: see rounds.**

## Hand rounds (labpage_audit.py sample / record; bar: membership <= 1, role/year <= 2, doubtful 0.5; 20 rows each, every row read against its own capture)
| round | seed | result | membership errors / doubtful / role-year | what the sample showed -> fix |
|---|---|---|---|---|
| 1 | 20261104 | fail | 2 / 2 / 0.5 | Prakash's Virginia Tech PhDs (undated, "Current: Faculty at ...") on a 2020 arrival's page -> `moved_in_alumnus` |
| 2 | 20261105 | fail | 3 / 2 / 0.5 | "Known PhD siblings" list (the PI's advisor's students); a dated news sentence read as a postdoc -> `autom.HARD_EXCL_HEAD`, `news_item` |
| 3 | 20261106 | fail | 2 / 3 / 1.5 | a publication byline "Zecheng Zhang,"; the kinship fix was not running because the audit read the lab-page toolkit from the MAIN checkout (friction 29: now the running checkout's) -> `byline_item`, `current_position_list`, toolkit path |
| 4 | 20261107 | **fail** | 3 / 4 / 0.5 | Celine Lin's Rice-era students and postdocs on her team page ("ECE@Rice University, 2017-2019"); a CV talk line read as a student; Kalidindi's "Current Position" name columns -> `other_institution_entry`, `talk_item`, current-position names dropped (rules added AFTER the draw; no new sample drawn) |
Four failed rounds are the normal limit (docs/LAB-PAGES.md): the lab-page students are not wired, `labpage-acceptance.json` does not exist, and the error patterns are above. The audit rules have since changed again; a fifth round needs an owner exception like Stanford's, CMU's and Michigan's (30-row sample, membership <= 1.5, role/year <= 3).

## Coverage under the every-lab rule (docs/DECISIONS.md 2026-11-03)
Labs 450 (454 PIs; 4 not built); **with students 4** (27 roster relations); with papers 419 (median 30 per lab). Reasons for 0 students: appointment_ended_early 38, new_hire_2025_or_later 31, **open 377**. For 0 papers: open 14, appointment_ended_early 9, new_hire 6, no_identity 2.
`student_audit.py gatech` (school-local): 27 lab-student pairs, 0 within-lab pairs, 0 across-lab people; `one_person` passes.

## Needs the owner
- **Extra rounds for the lab-page students (recommended):** the 813 additions in 70 labs are the only wide source; with the rules added since round 4 I expect the next round to pass membership, but that is untested. Without it Georgia Tech has 4 labs with students.
- **The other 380 labs have no student source** (no adviser-bearing list, no archived adviser page, SMARTech infeasible). Options: a researched pass over the 377 `open` labs with PI CVs and group pages (hundreds of lookups), or accept `sources_exhausted` reasons per lab (weak), or ask the Library whether a bulk ETD export exists (the OAI path is barred).
- **Data issue:** Alberto Apostolico "(1948-2015)" (a memorial listing) is a PI of the CSE census; his name carries the lifespan. Exclude or review.
