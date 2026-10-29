# Michigan, stage 6: students

Date: 2026-10-29 (started). Gate: **not passed. 219 of 251 labs have no students yet**; two fetches are still
running.

## Sources used, and the ones that are not
- **Not used.** Deep Blue, news.umich.edu and record.umich.edu are not used in any form: not live, not through OAI-PMH or
  REST, and not through Wayback. Their robots.txt names Claude's agents; this holds until the owner decides. No new live
  request goes to a host that served a challenge.
- **Lab member pages and PI homepages** (`tools/labpage_students_school.py links|extract michigan`). The pages are the
  PIs' homepages from stage 4, plus up to three people, students, group or lab links on each.
  - They are fetched live where the host is not challenged and robots allows it. Otherwise they come from Wayback
    captures: the one nearest 2026 and the one nearest the PI's first listed year.
  - Names come from `lpdom.member_candidates` (the EPFL/Berkeley lab-page pass) under role headings.
  - Kept: PhD students and postdocs with a plausible person name that is not the PI's and not another listed faculty
    member's (co-advisers are dropped).
  - Alumni are kept only from alumni sections, and only with a stated year. Nothing whose years end before 2016 is
    kept.
  - Each student's quote runs from the section heading to the name, verbatim, at most 600 characters.
  - "PhD Students and Postdocs" headings give the role `member`.
- **CSE and ECE dissertation-defense announcements** (`labpage_students_school.py defenses michigan`). These are
  Wayback captures of `/event/` pages whose URL says defense or dissertation.
  - The candidate is read from the announcement block ("<name>PhD Candidate", "PhD Defense: <name>").
  - The adviser is the "Faculty Host" (`host_quote`). Of the first 57 captures, 9 name a host.
  - CSE's own "Dissertation Defenses" index pages list names and titles but no chair, so they cannot attach a student
    to a lab.
- **Program-level listings.** The CSE PhD student directory names no adviser. Under R-STU-02 it could only add students
  who co-wrote a lab paper, and there are no lab papers before the sweep (stage 7). Not used yet.

## Counts so far (21:40 UTC; the `links` and `defenses` fetches are still running)
- **Lab pages:** 229 students in 32 labs (`hierarchy/michigan/labpage-evidence.json`). Dropped by the filters:
  - 4,148 strings that are not student names (paper titles, topics, headings);
  - 144 alumni without a year;
  - 106 entries that end before 2016;
  - 89 entries without a heading-to-name quote.
- **Builder** (`tools/pi_hierarchy.py michigan`): 220 students, 222 lab–student pairs, 32 labs with students.
- **Chain checks, in-process:** `students` 32/251 pass, 219 open; `one_person` 1 open item.

## Known precision risks (automatic, unreviewed: `auto: true`)
- **A homepage may list students from the PI's previous school.** Stella Yu's page lists Berkeley students. Their years
  come from the capture date (2022). The appointment rule keeps them from Michigan papers before 2022, but they can
  still be linked to 2022+ papers. A reviewed exclusion, or a rule that drops a section headed by another institution's
  name, is needed. This is stage-9 material.
- **The heading decides the role.** Mixed sections give `member`.

## To finish
```
/usr/local/anaconda3/2024.02/bin/python -I tools/labpage_students_school.py links michigan      # resumable
/usr/local/anaconda3/2024.02/bin/python -I tools/labpage_students_school.py defenses michigan   # resumable (captures cached)
/usr/local/anaconda3/2024.02/bin/python -I tools/labpage_students_school.py extract michigan
LD_LIBRARY_PATH=/n/fs/resemble/cs-atlas-env/py310/lib /n/fs/resemble/cs-atlas-env/py310/bin/python tools/pi_hierarchy.py michigan
```
Then the few-students research pass for labs still without students: lab sites found through the PIs' publications
and group names, in the pattern of `hierarchy/few-students-tools/`. Then program listings with the co-authorship check,
once stage 7 has lab papers.
