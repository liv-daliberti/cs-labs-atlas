# Virginia Tech Stage 6 student preflight

2026-11-10 isolated trial on `agent/vt-stage-work-1110`. Stages 2–5 pass; Stage 6 does not.

`CS_ATLAS_CODE=$PWD PYTHONPATH=tools python tools/pi_hierarchy.py vt` built a preliminary 93-PI package from the reviewed census and local sweep. It has 532 PI-paper rows, 22 PIs with papers, and **zero student relations**. These papers are an unadmitted trial, not school-release counts. `student_audit.py vt` wrote the school-local audit and found zero duplicate-person or link issues, but there are no students to check. The live Stage 6 gate reports **75 of 93 labs without explained student coverage** and a missing lab-page student acceptance. Earlier “one_person” open status was the absent school-local audit file, not a duplicate-person finding.

A limited `labpage_audit.py discover` pass checked Doug Bowman, Kirk Cameron, and Alexey Onufriev. Its subsequent `audit vt` found 16 listed people on the three checked pages: eight current and eight alumni. The automated comparison proposed six Kirk Cameron additions (Jon Bernard, Bo Li, Samuel Furman, Chandler Jearls, Nicolas Hardy, Zoe Smith); those are **unreviewed candidates** in the local `labpage-additions.json`, not admitted students. The audit classified five listings outside the period, two at a previous school, and three outside the people section. Robert Buehrer was not in the 93-PI provisional census, so his lab page was not part of this pilot.

Next: discover and audit the remaining PI pages; inspect all proposed additions against dated lab/source captures and the PI's VT period; research each lab with no students using independent sources; run a fresh random 20-person hand check under `docs/LAB-PAGES.md`; record acceptance only if its error limits pass; rebuild and rerun the school-local student and Stage 6 gates. No acceptance was stamped in this preflight.

## 2026-11-11 verified adviser intake

The saved Sanghani student directory and all 16 individual official student profiles were fetched again. Their SHA-256 hashes match the 2026-11-10 source inventory, and each quoted role/adviser sentence appears in the visible page text. `tools/vt_stage6_sanghani_students.py` records 12 students in 14 explicit 2026 adviser relations across 11 reviewed PIs in `reviewed/few-students-evidence.json`. Two students have two source-stated advisers. Four profiles are held in `reviewed/sanghani-student-holds.json` because their advisers are not among the reviewed 93 PIs; the hold preserves their quotes and does not silently reject the people.

The rebuilt isolated package contains 14 student–lab pairs, 22 candidate student–paper links, and 905 PI-paper rows. These papers and links are **unadmitted trial output**. The school-local student audit reports no duplicate-person findings. Stage 6 still fails with 64 of 93 labs lacking explained student coverage and no lab-page student acceptance. Lab-page additions remain unwired pending the required hand check.

## 2026-11-11 lab-page review and acceptance

The source-preserving discovery pass recorded all 93 PIs. The offline audit examined 705 apparent names across 37 pages with student sections. Manual review excluded 20 nonstudent or ambiguous entries, including postdocs, page titles, a program committee colleague, a citation-only name, and four undated student-researcher mentions without individual VT affiliation. The corrected audit proposes 139 lab-page students. Two parser repairs preserve an unspecified degree for a combined MS/PhD section and capture double-hyphen alumni year spans. The three recorded fresh 20-row hand checks had membership/role-year errors of 1/1, 0/1, and 0/0. The third round accepted the 139 rows against the exact additions-file SHA-256; `labpage-acceptance.json` records that hash. The first two reviews also passed the numerical bar, but each surfaced a source or parser error that was fixed before a new sample.

The first accepted rebuild added those 139 rows: 149 distinct students, 153 lab-student pairs, and 26 of 93 PIs with students. The student audit found no duplicate-person or missed-link findings. Cliff Shaffer's own page explicitly calls its dated thesis authors “my students”; five 2019–2025 PhD/MS relations were then checked against the original captured bytes and added to `few-students-evidence.json`. The resulting second build has 154 distinct students, 158 lab-student pairs, and 27 of 93 PIs with students. Its 117 student-paper links and 962 PI-paper rows remain trial output and are not an admitted school package.

Stage 6 remains open: 51 labs still lack students or an evidence-backed reason after the second build. The lab-page auditor selected unrelated VT visitor/alumni pages for some PIs, so those discovery records cannot support a no-student reason. The saved Sanghani directory is a scoped subset, not a full school adviser roster. We will not replace missing student evidence with boilerplate `sources_exhausted` claims.

## Continued source review, 2026-11-10

The following additions were verified against original saved page bytes (URL, SHA-256, and exact visible quotation) in `hierarchy/vt/raw/labpage-audit-captures.sqlite` and recorded in `reviewed/few-students-evidence.json`:

- Kurt Luther: 11 dated current/alumni PhD lab members from his PI-directed VT page.
- Debswapna Bhattacharya: two dated VT PhDs whose own pages explicitly name him as supervisor.
- Alexey Onufriev: Charles Plate, identified as working in his lab by VT News; this supports membership, not an adviser claim.
- Gang Wang: Chun Wang, a dated 2018 VT MS alumnus on Wang's historical student page.
- Bert Huang: four explicit student-adviser records from official Sanghani profiles and graduation stories.
- Na Meng: seven dated current graduate students on her PI-owned VT page; these support lab membership, not an adviser claim.
- Godmar Back and Xun Jian: three and four dated thesis students, respectively, from their PI-owned VT pages.
- Madhav Marathe, Ali Butt, and Jin-Hee Cho: one named doctoral student each from official VT CS highlights with an explicit chair or adviser statement.
- Sang Won Lee: nine current graduate Echolab members on the PI-directed VT lab page; these support lab membership, not an adviser claim.
- Wenjing Lou: one current VT PhD with an explicit adviser statement on the Amazon–Virginia Tech initiative page.
- Naren Ramakrishnan: two current graduate students whose Sanghani profiles explicitly name him as adviser.
- Yang Cao: three named members of his VT computational biology group; the page does not support specific membership years.
- Denis Gracanin: four named current PhD students from his PI-owned advising page; committee listings were excluded.
- Aisling Kelliher: five dated VT graduate advisees from her mentoring page; committee and CMU students were excluded.
- Changhee Jung: Qingrui Liu, a dated 2018 VT PhD alumnus from Jung's PI-owned page.

The latest isolated build has **93 PIs, 213 distinct students, 219 lab-student pairs, and 45 PIs with students**. The student audit reports zero duplicate-person findings; it also flags seven potential paper links for Qi Zhang against Qisheng Zhang bylines. The PI-owned tClab page lists Qi and Qisheng as separate people, so those links remain unadmitted pending an explicit reviewed exclusion in the paper-link audit. The 1,366 lab-paper rows and 209 student-paper links are trial output, not release counts. The latest lab-coverage ledger reports **33 unexplained labs** (plus 15 specific appointment/new-hire reasons). Stage 6 remains **fail** on those 33 gaps; no generic absence reason was added.
