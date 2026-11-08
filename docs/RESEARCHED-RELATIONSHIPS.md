# Explicit relationships on researched member rows

`students.researched` accepts an optional reviewed `relationship` field on source rows in `gap-evidence.json` and the researched evidence files, including `few-students-evidence.json` and `roster-evidence.json`.

- `"relationship": "membership"` emits `researched_membership` while retaining the literal degree/student role. A group page may identify a PhD, master's or undergraduate member without naming an individual PI adviser.
- `"relationship": "advising"` emits `researched_advising` only when the existing student-role guards permit advising. It cannot override a visiting, nonstudent or withheld-role classification.
- Omission preserves the existing role-based behavior and output objects. A present null, misspelled or unsupported value raises `ValueError`; it never silently falls back to advising.

The selector changes only the relation type. It does not create an identity, attendance span, university affiliation, current status or paper link. Keep role/program labels, source sections, original URLs/hashes, dates/status precision and adviser statements in their own source fields. A dated degree or alumni membership can remain a membership. Every new explicit relationship is a reviewed source decision, not permission to infer supervision from a shared group or a coauthor list. Automatic corroborated-paper additions retain their separate existing behavior.
