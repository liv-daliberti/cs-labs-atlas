# Toronto: student coverage for 30 previously empty PIs

Reviewed 2026-11-14. Baseline: 217 PIs, 59 with recorded students, 158 without. Target: at least 89 with recorded students and at most 128 without.

Thirty manually reviewed graduate relationships under R-STU-01, with exact source quotations and SHA-256-bound saved pages. Current PhD observations are dated only to the capture year; dated degree/alumni entries use explicit completion years. The old failed automated lab-page proposals remain unaccepted. This review does not certify the full Stage 6 gate.

Raw captures: `hierarchy/toronto/raw/student-coverage-20261114/` (local data, excluded from git by policy). Baseline and review receipts: `scratch/toronto-students30-1114/`.

| PI | Student | Role | Recorded years | Source |
|---|---|---|---|---|
| Marsha Chechik | Alicia Grubb | phd | 2017 | [page](https://www.cs.toronto.edu/~chechik/people.shtml) |
| Sheila McIlraith | Maayan Shvo | phd | 2023 | [page](https://www.cs.toronto.edu/~sheila/students/) |
| Chris Beck | Roy Luo | masters | 2016 | [page](https://www.cs.toronto.edu/~sheila/students/) |
| Robert Soden | Sophia Jit | masters | 2022–2024 | [page](http://robertsoden.io/students/) |
| Sam Toueg | Myles Thiessen | phd | 2026 | [page](https://delara.github.io/people/) |
| Niv Dayan | Guy Khazma | phd | 2026 | [page](https://delara.github.io/people/) |
| Fan Long | Yanning Chen | phd | 2024–2026 | [page](https://xnning.github.io/team.html) |
| Alán Aspuru-Guzik | Manuel Drehwald | masters | 2025 | [page](https://xnning.github.io/team.html) |
| Anna Goldenberg | Jingyi Zhao | phd | 2026 | [page](http://goldenberglab.ca/people.html) |
| Bo Wang | Kaden McKeen | phd | 2026 | [page](http://goldenberglab.ca/people.html) |
| Nicolas Papernot | Anvith Thudi | phd | 2026 | [page](https://cleverhans.io/members.html) |
| Shurui Zhou | Jiayi Sun | phd | 2021–2026 | [page](https://www.eecg.utoronto.ca/~shuruiz/forcolab/team.html) |
| Kelly Lyons | Enmeng Liu | masters | 2021–2023 | [page](https://www.eecg.utoronto.ca/~shuruiz/forcolab/team.html) |
| Cristiana Amza | Timur Malgazdarov | masters | 2018 | [page](https://www.eecg.utoronto.ca/~amza/) |
| Ding Yuan | Yongle Zhang | phd | 2020 | [page](https://www.eecg.utoronto.ca/~yuan/Home.html) |
| Ashvin Goel | Francis Deslauriers | masters | 2016 | [page](https://www.eecg.utoronto.ca/~ashvin/students.html) |
| Graeme Hirst | Kathleen Fraser | phd | 2016 | [page](https://www.cs.toronto.edu/~gh/diaspora.html) |
| Andreas Veneris | Keerthi Nelaturu | phd | 2024 | [page](https://www.eecg.utoronto.ca/~veneris/students.html) |
| Ashton Anderson | Lillio Mok | phd | 2024 | [page](http://csslab.cs.toronto.edu/people/) |
| Farid N. Najm | Yara Halawi | masters | 2024 | [page](https://www.eecg.utoronto.ca/~najm/) |
| Natalie Enright Jerger | Karthik Ganesan | phd | 2024 | [page](https://www.eecg.utoronto.ca/~enright/) |
| Vardan Papyan | Jonah Mackey | masters | 2025 | [page](https://sites.google.com/view/vardan-papyan) |
| Kirill Serkh | Siphelele Danisa | masters | 2023 | [page](https://sites.google.com/view/vardan-papyan) |
| Michael Stumm | Sari Sultan | phd | 2024 | [page](https://www.eecg.utoronto.ca/~stumm/MichaelStummAlumni) |
| Jonathan Rose | Alex Rodionov | phd | 2019 | [page](https://www.eecg.utoronto.ca/~jayar/graduate-theses.html) |
| Vaughn Betz | Andrew Boutros | masters | 2018 | [page](https://www.eecg.utoronto.ca/~vaughn/students.html) |
| Ben Liang | Wen Xu | phd | 2026 | [page](https://www.comm.utoronto.ca/~liang/group/members.html) |
| Kieran Campbell | Shanza Ayub | phd | 2026 | [page](https://www.camlab.ca/people/) |
| Daniel Roy | Ziyi Liu | phd | 2026 | [page](https://danroy.org/) |
| David Lie | Kexin Li | masters | 2024 | [page](https://security.csl.toronto.edu/blog/2024/09/22/congrats-to-kexin-and-jiaqi-for-completing-their-masc-degrees-and-welcome-to-guozhen-and-xiao/) |

Validation: all 30 names refer to baseline-zero PIs; all saved raw SHA-256 values and each quoted segment verified against captured page text. Private native rebuild (job 32256055) passed the before/after check: 217 PIs unchanged; recorded-student coverage 59 → 89; PIs without students 158 → 128; lab–student pairs 757 → 787. All 757 existing records are retained exactly. Removed 16 obsolete no-student reason fields for newly covered PIs, preserving all other coverage notes. Raw hashes and quoted source segments rechecked against the saved pages.

The Stage 6 gate remains failed with five pre-existing categories: missing lab-page acceptance; 30 unexplained lab-page student gaps (was 44); 113 zero-student PIs without researched reasons (was 141); missing recall sample; and 83 boilerplate reasons (was 97). Trap checks also report the pre-existing stale Stage 2 gate and remaining boilerplate reasons. No gate exceptions or acceptance decisions were changed.

Normal rebuild effects: lab-paper rows 9328 → 9334; student–paper links 1457 → 1547; labs with student papers 55 → 78. New relationships participate in the existing advising/identity/link rules; no builder logic changed.
