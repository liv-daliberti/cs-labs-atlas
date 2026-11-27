Shared schema repair, November 26, 2026

Observed atlas validate gatech --reviewed --shared: 53 violations across 5 files; candidate: zero violations across all 28 present files. Nine optional absent files are reported as missing, not waived violations.

17 home-department holds legitimately have no source evidence and no assigned department. The schema now admits null only on an explained, unassigned hold; accepted/assigned records and affirmative no-academic-department decisions still require valid source evidence.
28 student-audit errors came from the writer’s source-distinct same-name pairs and their counter. The schema now models those fields, requiring the separate source keys and a nonnegative count; distinct people remain distinct.
6 zero-paper ledger records preserve nonempty legacy provenance text. The schema now follows the existing writer’s array/null/nonempty-string evidence contract, without changing any generated record, review or citation. Empty notes and arbitrary evidence object/number values remain invalid.
1 chain reason used status instead of verdict. The exact reviewed NTU staff-membership explanation is restored under the reader’s verdict key; sources and the independent review are preserved.
1 Georgia Tech identity review lacked school metadata. The school key is restored, and the proposal writer preserves/adds that key and refuses a mismatched school without replacing manual decisions.

Before/after JSON and focused regression tests retain the evidence of repair. No unproven department, student degree, identity, or review approval is invented.
