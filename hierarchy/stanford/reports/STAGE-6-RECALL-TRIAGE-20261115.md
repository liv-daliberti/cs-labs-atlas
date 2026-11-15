# Stanford Stage 6 recall triage — 2026-11-15

The current 30-PI draw (`student-recall-check.json`, SHA-256
`1e0db59c8c8606895edf80f50b0b446b01a0600c505d03897d23d4c6a08fae5f`)
reports R1 = 139/259 = 0.541 and lacks independent signoff. This note does not
sign the draw or accept additional student rows.

The proposed 101-row packet (`scratch/oxford-vt-release-1114/regression-review/
stanford-recall-candidates-101.json`, SHA-256
`b36bb503412dc2a81930e83fda3b292096890341408e708febc3ea12bfa37822`)
has 52 Amin Arbabian, 41 Daniel Bruce Ennis, and 8 Hariharan Subramonyam
candidates. It must be reviewed row by row before integration. Its `status`
is explicitly `proposed; not wired or accepted`.

The bound [candidate triage](STAGE-6-RECALL-CANDIDATES-20261115.json) holds
12 rows: five Arbabian visitors who are faculty/scientists, five Ennis
research scientists or a visiting scholar, one Ennis graduate dated before
his sourced Stanford appointment, and a duplicate Joshuah Chen alumni row
that conflicts with his current-page entry. The other 89 remain proposals
pending the lab-page hand-check; this is not an acceptance verdict.

The primary pages confirm why a bulk import is unsafe:

R-STU-17 counts visiting *students* as members of the lab. The `visitor`
labels below are a review queue, not automatic exclusions. Visiting faculty,
scientists, and scholars require separate `not_a_student` decisions.

- [Arbabian current people](https://arbabianlab.stanford.edu/people) separates
  students/researchers from adjunct and visiting faculty, staff, and the PI.
  [Previous students/researchers](https://arbabianlab.stanford.edu/previous-students-researchers)
  includes dated alumni and other contributors. The current draw lists 93
  names from this lab, including 42 tagged `visitor`, with zero exclusions.
- [Ennis CMR people](https://med.stanford.edu/cmrgroup/people.html) separates
  current lab members from alumni and gives explicit roles for many entries,
  including visiting students and staff. The draw lists 66 names, including
  14 tagged `visitor`, with zero exclusions.
- [Subramonyam advising](https://haridecoded.com/) lists current postdocs,
  PhD students, and other student researchers. It includes people at other
  institutions. The draw lists 36 names and zero exclusions; the proposed
  packet contains eight rows from this page, so the remaining names still
  need an eligibility decision.

Next: classify each listed person against the member and visiting rules,
verify role and appointment years against the stored capture, then generate a
new lab-page additions set and run the required fresh hand-check before wiring
it. Redraw the recall sample after rebuilding. The three Stanford student-count
regression flags remain held until this evidence and Stage 6 pass.
