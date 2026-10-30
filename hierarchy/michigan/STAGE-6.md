# Michigan, stage 6: students

Date: 2026-10-29, updated 2026-10-30. Gate: **not passed. 116 of 288 labs have students; 172 do not**, and the
allowed sources are exhausted (see the update at the end).

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

## Update, 2026-10-30: all allowed sources run. Gate not passed (source-limited)

### What was added
- **Gzip-encoded lab pages.** 12 lab pages and many homepages had been read as empty, Stella Yu's 2026 page among them.
  They are decoded now (`wb.body`).
- **Alumni markers in page text** (`alumni_in_text`). An 'Alumni' line that is not a heading element left the role
  headings under it looking current. The rule found 1,183 such rows; alumni without a stated year are dropped as
  before, which accounts for 1,632 drops.
- **Students of the PI's previous school** (`previous_school_students`). A student whom the same PI's lab at a released
  school already holds is dropped. The PI is matched by a shared DBLP id or ORCID.
  - 31 students were dropped under 8 cross-school PIs: Jia Deng (Princeton), Matthew Johnson-Roberson and Pei Zhang
    (CMU), Michael Cafarella and Leia Stirling (MIT), Prabal Dutta and Stella Yu (Berkeley), Mert Pilanci (Stanford).
  - Stella Yu's Berkeley PhD students and postdocs are gone. Her 2022 Michigan graduate students (Ganesan,
    Doraiswamy, Wang, Zhang) and her 2026 group stay.
- **Students' own websites from the CSE and ECE PhD directories** (`labpage_students_school.py directory`;
  charter `[students].directories`). 15 yearly directory captures 2019–2026 list 561 students, 260 of them with a
  website.
  - A page counts when it names Michigan, says PhD, and puts an adviser phrase directly before a PI's full name.
  - Result: 99 relations, 97 students, 56 labs; 28 of them were already on a lab page.
  - The quotes are the students' own sentences, for example "Ph.D. student in Computer Science and Engineering at the
    University of Michigan, advised by Prof. Jean-Baptiste Jeannin". One directory name parsed badly (". Sidharth").
- **PIs' homepages from their DBLP person records** (`periods_school.targets`). 248 new URLs were tried; authority
  records (DNB, LoC, VIAF) are skipped. Then `links` and `extract` were re-run.
- **Defense announcements:** 142 captures, 3 announcements with a Faculty Host, and none of those hosts is a single
  PI. They give no students.

### Counts (build of 2026-10-30 14:14)
- Lab pages: 626 students in 91 labs. Directory websites: 99 relations.
- Builder: 658 students, 680 lab–student pairs, 116 labs with students.
- `tools/student_audit.py`: 680 pairs; 0 within-lab duplicate pairs; 2 people across labs, listed and not merged.
- Chain checks in-process: `students` 116/288; `one_person` 680/680; `links` 520 pass, 71 explained, 89 open.
- **Caution:** run `student_audit.py` with every school. It rewrites the shared `hierarchy/student-audit.json`. A
  Michigan-only run dropped the six released schools' entries; it was re-run at once for all seven.

### Gate
**Not passed: 172 labs without students.** The cause is the sources, and it is outside this run's control:
- **Deep Blue**, the dissertation repository with advisers, is excluded by owner decision 2 (2026-10-30). Its
  robots.txt names Claude's agents.
- **The Mathematics Genealogy Project** (no robots.txt) has advisers for many CS dissertations. It has been offline
  since 21 October 2026 (a PHP vulnerability).
- **The CSE and ECE pages are Cloudflare-challenged** and read only from Wayback (decision 3). The defense
  announcements name a Faculty Host in 3 of 142 captures.
- **Program directories name no adviser.** R-STU-02 does not let co-authorship alone make one.

What would close the gap, in order of yield:
1. the Mathematics Genealogy Project once it is back online;
2. a researched few-students pass over the 172 labs (lab sites found through publications and group names), as the
   released schools did for their last labs;
3. an owner decision on Deep Blue metadata.
