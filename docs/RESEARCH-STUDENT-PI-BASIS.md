# Research students as a faculty PI basis

The school procedure admits research or teaching faculty with a verified group
or advisees. Undergraduate and master's research supervision is represented by
`kind: advises_students` in `pi-basis-evidence.json`. This preserves the actual
degree level instead of calling those students PhD advisees.

The existing appointment, computing-scope and exact candidate-identity checks
remain required. A `stage2_review: true` basis retains the academic unit, original
research/teaching rank, role, observation date, source URL, SHA-256 and quote.
Its `research_student_supervision` list names at least one student, a supported
role (`student`, `undergraduate`, `masters`, or `phd`), the relationship
`research_supervision`, an observation date, source URL/hash, literal name quote,
and `research_context_quote`. Both quotes are replayed against saved source bytes.
The context must explicitly concern research, a thesis, dissertation or capstone.
Course-only and summer-reading supervision do not establish this basis.

This PI review does not add students to the native package. Student identity,
role, membership and dates still require their separate reviewed evidence and
stage 6 checks. The existing `advises_phd` student-extraction route is unchanged.
