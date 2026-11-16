# Toronto student coverage under 50

## Result

The private native rebuild (Slurm job `32258026`) covers **168 of 217 PIs**, leaving **49 PIs with no student records**. It contains 1,188 unique student records and 1,229 PI–student pairs. The preceding under-75 checkpoint had 71 PIs with no student records.

This pass added reviewed evidence for 16 newly covered PIs across 92 student records. Sources include U of T and lab rosters, explicit supervision statements, a PI CV, and student-authored records. Quotes and SHA-256 hashes were checked against the locally captured source pages.

The already-covered Karan Singh lab grew from five to 15 students. The ten added records are distinct and appear in the native rebuild.

## Validation

- `bin/atlas lint`: passed.
- `bin/atlas charters toronto`: passed.
- Native rebuild: completed successfully; 49 PIs without student records.
- Stage 6 student-coverage gate: **not passed**. It still reports missing lab-page acceptance and recall-review records, 12 unexplained PIs, 42 zero-record PIs without researched reasons, and 62 boilerplate `sources_exhausted` reasons.
- Stage 6 trap check: **two findings** remain: the recorded Stage 2 gate is stale relative to the CS-related review, and 62 PIs retain the boilerplate `sources_exhausted` reason.

The requested student-count target and the ten-student addition are met. Toronto still has the Stage 6 review items above before release readiness can be claimed.
