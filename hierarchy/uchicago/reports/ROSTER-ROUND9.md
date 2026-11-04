# Statistics and CAM roster round 9: row analysis and a proposed rule

Round 9 (owner-granted, 2026-11-04) drew 20 of the new roster relations (Statistics `/people/`, CAM `/people/`; names with a 'PhD Student' line, kept only with co-authorship of a lab paper). It failed at 1.5 doubtful (bar 1).
Counts below are recomputed from `lab_papers.jsonl.gz`: papers co-authored by the student and the PI inside the roster years (+-1), and how many of them have the PI as last author.

| student | PI | roster years | papers in years | PI last | old rule (last>=1 or papers>=2) | proposed rule | note / what would settle it |
|---|---|---|---|---|---|---|---|
| Kiho Park | Victor Veitch | [2025, 2025] | 2 | 0 | pass | fail | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed ; fails the proposed rule: settle with an ETD adviser record, a CV or a lab page |
| Raphael Rossellini | Rebecca Willett | [2023, 2025] | 2 | 1 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Ziyang Wei | Wei-Biao Wu | [2023, 2025] | 7 | 0 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Phillip Lo | Yuehaw Khoo | [2025, 2025] | 1 | 1 | pass | fail | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed ; fails the proposed rule: settle with an ETD adviser record, a CV or a lab page |
| Omar Al-Ghattas | Daniel Sanz-Alonso | [2024, 2025] | 8 | 5 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Matthew Frazier | Guillaume Bal | [2026, 2026] | 3 | 2 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Hwanwoo Kim | Daniel Sanz-Alonso | [2023, 2026] | 3 | 1 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Jiaheng Chen | Daniel Sanz-Alonso | [2024, 2026] | 9 | 4 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Zihao Wang | Matthew Stephens | [2020, 2025] | 2 | 2 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| June Wu | Madhur Tulsiani | [2024, 2026] | 2 | 0 | pass | fail | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed ; fails the proposed rule: settle with an ETD adviser record, a CV or a lab page |
| Soham Bonnerjee | Wei-Biao Wu | [2024, 2025] | 5 | 0 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Dongyue Xie | Matthew Stephens | [2019, 2023] | 3 | 3 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Yating Liu | Claire Donnat | [2023, 2025] | 4 | 0 | pass | pass | flagged doubtful: no joint-paper position evidence in the sample (one paper shown) |
| Nathan Waniorek | Daniel Sanz-Alonso | [2023, 2026] | 8 | 0 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Jiaheng Chen | Haotian Jiang | [2025, 2026] | 2 | 0 | pass | fail | flagged doubtful: Chen is a CAM student of Sanz-Alonso (4 papers with him as last author); the two joint papers with Jiang do not say Jiang advises ; fails the proposed rule: settle with an ETD adviser record, a CV or a lab page |
| Ruiyi Yang | Daniel Sanz-Alonso | [2021, 2026] | 6 | 0 | pass | pass | flagged doubtful on one displayed paper; the data show 6 joint papers in the roster years with Yang as last author (an advisor-first byline) |
| Zhen Dai | Nathan Srebro | [2020, 2022] | 3 | 1 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Solomon Quinn | Guillaume Bal | [2023, 2025] | 5 | 2 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Rohan Hore | Rina Foygel Barber | [2022, 2025] | 6 | 2 | pass | pass | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed |
| Su Hyeong Lee | Tian Li | [2024, 2026] | 1 | 1 | pass | fail | consistent with the lab as I know it (roster PhD student, PI on joint papers in the roster years); not independently confirmed ; fails the proposed rule: settle with an ETD adviser record, a CV or a lab page |

## Why the old rule let a doubtful row through, and a proposed rule
- 'PI last author' is not a universal advising signal: statistics, mathematics and theory bylines are alphabetical or advisor-first (Ruiyi Yang: 6 joint papers, the PI never last). Two joint papers with a person who is not the adviser (Jiaheng Chen with Haotian Jiang) pass 'two papers together'.
- **Proposed rule R*: at least 3 joint papers in the roster years, or at least 2 with the PI last author on one.** On all 75 roster relations: old rule passes 75, R* passes 52; of the 20 sampled rows R* keeps 15; it rejects the one row the sample showed to be a collaboration (Chen with Jiang) and also four that look right on what is known of the labs (Park/Veitch, Lo/Khoo, Wu/Tulsiani, Lee/Li: one or two joint papers, PI not last): R* is conservative, and those four are exactly what the ETD adviser record should settle.
- **Settling evidence per kind of doubt:** (a) a Knowledge@UChicago dissertation record naming the PI as advisor (the repository crawl, when it lands; the cross-check below); (b) a CV or a lab page listing the student; (c) a joint paper with the PI last author (already counted); (d) for a current student with no thesis yet, the department's first-year advisor/rotation listing, which these departments do not publish.
- **Plan with the ETD crawl:** every Statistics/CAM roster relation (all 75, including those R* rejects) is cross-checked against the dissertation advisor field: advisor match = confirmed (kept even if R* rejects it), advisor names another PI = rejected, no record (current students) = R*. A relation kept by R* but contradicted by ETD is dropped. The expected gain is the alumni of 2019-2025; current students (Aut 22 onward) have no thesis yet and rest on R*.
- **Not wired yet:** the rosters stay off in the charter until R* is applied in `roster_coauthor_students` and a hand round on the R*-passing rows passes, or the ETD cross-check confirms them.


## Cross-check against the Knowledge@UChicago ETD (2026-11-04, owner decision of the same day)
The rosters stay UNWIRED. Method: all 75 roster pairs (Statistics `/people/` and CAM `/people/`, rule as in the charter before round 9: the PI last author on a joint paper, or two joint papers, within the roster capture years +-1; `roster_coauthor_students`) against the 717 doctoral-type theses of the repository crawl (job 32101759: 661 with an advisor field, 11 matched to an atlas PI inside the PI's listed years, `reviewed/thesis-evidence.json`).

**Result: the ETD cannot score the rosters.** No thesis in the repository names any of the 23 roster PIs as advisor (surname search over all 443 advisor strings: 3 surname coincidences, none a PI: Li Jiaqi, Li Darryl, Ma Zhiying), and none of the 75 roster students is the author of a thesis. The repository's `doctoralThesis` type is almost all master's theses (MAPSS 357, Committee on International Relations MA 92, MACSS 84+8; set names `community-ma-program-in-the-social-sciences-mapss-theses`, `...-ma-theses`, `...-masters-in-computational-social-science-macss-theses`); only 4 are Computer Science dissertations and 3 Mathematics or CAM. PhD dissertations of the Statistics and CAM programmes are not deposited there. So: ETD-confirmed 0 of 75, ETD-contradicted 0 of 75, for both rules; precision and recall against ETD are undefined.

| rule | pairs kept (of 75) | ETD confirmed | ETD contradicted |
|---|---|---|---|
| old (last author, or 2 papers) | 75 | 0 | 0 |
| R* (3 papers, or 2 with the PI last on one) | 50 | 0 | 0 |

(ROUND9 counted 52 for R* from per-capture paper counts; recounted over the union of roster years it is 50. 25 pairs separate the rules; they are in `ROSTER-ETD-CROSSCHECK.json`, which is git-ignored data next to this report.)

**The five hand-checked pairs** (ETD has no record for any of them; evidence outside the ETD, found in the stored captures):
| pair | joint papers / PI last | old | R* | what the evidence says |
|---|---|---|---|---|
| Chen / Jiang | 2 / 0 | keep | drop | round 9: Jiaheng Chen is Sanz-Alonso's CAM student (9 papers, 4 with him last); the two papers with Jiang are a collaboration. R* is right |
| Park / Veitch | 2 / 0 | keep | drop | no lab page names Park; Kiho Park is on the Mathematics graduate list 2019-2021 and the Statistics people page 2026 (no adviser). Unsettled |
| Lo / Khoo | 1 / 1 | keep | drop | CAM student 2020-2023 (PhD, first to fourth year); no adviser line. Unsettled |
| Wu / Tulsiani | 2 / 0 | keep | drop | June Wu is a CAM first-year in 2019 and "2025 PhD" in the 2026 capture; no adviser line. Unsettled |
| Lee / Li | 1 / 1 | keep | drop | Su Hyeong Lee is listed on Risi Kondor's group page (people.cs.uchicago.edu/~risi/, capture 2026-08-20, "CCAM PhD, 4th year"), not Tian Li's. The old rule keeps a wrong pair; R* is right |

One more pair settled by a lab page: Abby Stevens / Rebecca Willett is listed on Willett's group-members page (voices.uchicago.edu/willett/research/group-members/, 2019 and 2021 captures, "Statistics grad student"); the old rule keeps it, R* DROPS it (2 papers, PI last on none), a false negative.

**Scoring on the three pairs that outside evidence settles:** old rule 1 true positive, 2 false positives (Chen/Jiang, Lee/Li), 0 false negatives; R* 0 true positives, 0 false positives, 1 false negative (Stevens/Willett). Three pairs are too few to estimate precision or recall.

**Recommendation (owner decides; nothing wired):** keep the rosters off. If roster students are wanted, wire R* and only R*, because the old rule keeps both pairs that evidence shows wrong, but expect R* to lose real advisees (25 of 75 pairs dropped, among them Stevens/Willett); the safer route to those advisees is the per-PI lab page or CV, which the homepage dive already reads. A pair should also be dropped whenever the student is listed on another PI's own lab page (Lee: Kondor).
