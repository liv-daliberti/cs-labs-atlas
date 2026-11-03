# University of Chicago, stage 6: students

Date: 2026-11-03. Gate (`atlas stage-gate uchicago 6`): **fail, 2 open**: chain-audit `students` 114 of 138 labs unexplained (24 have students), `one_person` 1 (student-audit has no entry for the school). The lab-page students acceptance is **accepted** (round 2).

## Sources, in the protocol's order
1. **Thesis repository: Knowledge@UChicago probed, skipped.** robots.txt (2026-11-03) has only a `*` group (no AI-agent rules), Crawl-delay 10, and disallows `/search`, `/api`, `/administration`, `/uploads`. It is allowed, but not usable: the only listing is the sitemap (16,089 record pages), search and API are off limits, so reading the advisor field is one record page per 10 s (about 45 hours) with no way to select computer-science dissertations.
2. **Adviser-bearing student list wired in: TTIC `/students/`** (2017-2026 Wayback captures; each PhD student with an `Advisor:` line; two page markups). New `[students].adviser_directories` source (`labpage_students_school.adviser_directory`, tests): 131 student-PI relations (112 students), quotes verbatim from the capture. The TTIC alumni page is not used (its listed years are not membership years). CS department PhD lists exist (`/people/students/`, 2018-2022) but name no adviser. CS/TTIC defence announcements: the generic `defenses` step is Michigan's EECS event format; no UChicago parser was written.
3. **Lab pages:** 65 pages fetched (18 min, robots and Crawl-delay honoured, no challenge); 95 students from 16 labs.

**Labs with students: 16 before, 25 after** (226 student rows after, from 95). Of 139 PIs, 24 labs have students in the build; the rest are the 114 below.

## Hand rounds (`labpage_audit.py sample` / `record`; standard bar: membership <= 1, role/year <= 2, doubtful 0.5; 44 proposed additions)
- **Round 1** (seed 20261103): fail. 0 membership errors; 5 doubtful rows carried a stated end year ("PhD 2024", "postdoc 2022-2025") with `alumni = False` (role/year 2.5). Fixes: `entry_years_end_the_stay` (a degree or end year makes the entry an alumnus) and additions taking the newest capture's alumni reading (an older capture that listed the person as current had kept the flag).
- **Round 2** (seed 20261105, a new sample): **pass**. 0 membership errors, 1 role error (Bogdan Stoica "Ph.D. 2025, Post Doc @ Univ. of Illinois" read as postdoc; the employer after the degree). Recorded in `labpage-handcheck.json`, accepted in `labpage-acceptance.json`.
  The additions stay unwired until the builder integration (docs/LAB-PAGES.md), which is why Barber, Casillas, Doiron's labs still read "no students" in the chain audit.

## Open
- **114 labs without students.** Options: wire the accepted additions (Barber, Casillas, Doiron, Shan Lu, Tulsiani, Willett, ...), then a researched few-students pass over the remaining labs (Michigan was source-limited the same way, 116 of 288). Owner call: how much of that pass, and whether Statistics/Booth labs without a lab page may carry the reason "no group page; advisees only in the program directories".
- **one_person:** `student_audit.py` must run with every school and rewrites the shared TRACKED `hierarchy/student-audit.json`; not run while a release rebuilds the main checkout. Request R12: a school-local audit output for an onboarding school (as the lab-page summary).
- One known rule defect: "Ph.D. YYYY, Post Doc @ ..." reads as postdoc (request R13: read the first degree token, not the employer).
