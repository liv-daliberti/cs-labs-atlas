# University of Chicago, stage 6: students (mechanical steps done, gate open)

Date: 2026-11-03. Gate (`atlas stage-gate uchicago 6`): **fail, 3 open**: lab-page students acceptance missing (the hand rounds), chain audit students 138 and one_person 1 unexplained (they close after the rounds and the stage-7 build that reads the students).

## What was done (jobs 32087843-32087845, collector interpreter, robots and Crawl-delay rules honoured, no challenges)
- `labpage_students_school.py links`: 65 lab pages fetched for the 139 PIs (123 labs have no page of their own that the discovery found).
- `extract`: 95 students in 16 labs. Dropped: 2,212 not a student name, 95 without a heading quote, 72 alumni without a year, 34 before the window.
- `directory`: 0 (the charter has no student-directory source: `[thesis] kind = "none"`; CS/TTIC PhD announcements are in the sources list only).

## Open (needs the hand rounds, docs/LAB-PAGES.md)
- A fresh sample of 20 from the 95 students, hand check with `atlas review-page`, the acceptance bar (at most 1 membership, 2 role/year error per 20), a rule fix and a NEW sample on failure; record in `labpage-handcheck.json`. Not started: it is a judgement step that needs a reviewer.
- 16 of 139 labs with students is low next to the other schools; most UChicago CS labs list people on pages the links step reached only partly (65 pages for 139 PIs). A directory source (PhD defence lists) could add advisor links; owner call whether to pursue.
