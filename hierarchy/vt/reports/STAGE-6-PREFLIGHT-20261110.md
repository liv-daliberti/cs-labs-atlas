# Virginia Tech Stage 6 student preflight

2026-11-10 isolated trial on `agent/vt-stage-work-1110`. Stages 2–5 pass; Stage 6 does not.

`CS_ATLAS_CODE=$PWD PYTHONPATH=tools python tools/pi_hierarchy.py vt` built a preliminary 93-PI package from the reviewed census and local sweep. It has 532 PI-paper rows, 22 PIs with papers, and **zero student relations**. These papers are an unadmitted trial, not school-release counts. `student_audit.py vt` wrote the school-local audit and found zero duplicate-person or link issues, but there are no students to check. The live Stage 6 gate reports **75 of 93 labs without explained student coverage** and a missing lab-page student acceptance. Earlier “one_person” open status was the absent school-local audit file, not a duplicate-person finding.

A limited `labpage_audit.py discover` pass checked Doug Bowman, Kirk Cameron, and Alexey Onufriev. Its subsequent `audit vt` found 16 listed people on the three checked pages: eight current and eight alumni. The automated comparison proposed six Kirk Cameron additions (Jon Bernard, Bo Li, Samuel Furman, Chandler Jearls, Nicolas Hardy, Zoe Smith); those are **unreviewed candidates** in the local `labpage-additions.json`, not admitted students. The audit classified five listings outside the period, two at a previous school, and three outside the people section. Robert Buehrer was not in the 93-PI provisional census, so his lab page was not part of this pilot.

Next: discover and audit the remaining PI pages; inspect all proposed additions against dated lab/source captures and the PI's VT period; research each lab with no students using independent sources; run a fresh random 20-person hand check under `docs/LAB-PAGES.md`; record acceptance only if its error limits pass; rebuild and rerun the school-local student and Stage 6 gates. No acceptance was stamped in this preflight.

## 2026-11-11 verified adviser intake

The saved Sanghani student directory and all 16 individual official student profiles were fetched again. Their SHA-256 hashes match the 2026-11-10 source inventory, and each quoted role/adviser sentence appears in the visible page text. `tools/vt_stage6_sanghani_students.py` records 12 students in 14 explicit 2026 adviser relations across 11 reviewed PIs in `reviewed/few-students-evidence.json`. Two students have two source-stated advisers. Four profiles are held in `reviewed/sanghani-student-holds.json` because their advisers are not among the reviewed 93 PIs; the hold preserves their quotes and does not silently reject the people.

The rebuilt isolated package contains 14 student–lab pairs, 22 candidate student–paper links, and 905 PI-paper rows. These papers and links are **unadmitted trial output**. The school-local student audit reports no duplicate-person findings. Stage 6 still fails with 64 of 93 labs lacking explained student coverage and no lab-page student acceptance. Lab-page additions remain unwired pending the required hand check.
