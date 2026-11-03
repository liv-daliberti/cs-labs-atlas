# Michigan, stage 9: accuracy

Date: 2026-11-02. Gate: **not passed** (lab-paper precision 0.920 < 0.95 and lab-paper coverage 0.867 < 0.90; student-link precision passed). The owner accepted shipping with a failed gate; no one-off fixes were made.

## What was measured
The standard hand-checked sample, 105 judgments (`accuracy/sample.py --school michigan`; seed 20261029, `random.Random(seed)` reset for the school, the same draw order and strata as the six released schools). The sample is from the **pre-release onboarding build** (the Michigan files as they were on 2026-11-02 before the release rebuild). Every judgment was made from a copy of those files; sha256 of the measured build:

| file | sha256 |
|---|---|
| `pis.json` | `72f6ad03b275573573a06f5477fa6d791dc68f9a58f39418b200a93bd2faaae6` |
| `students.json` | `8d8eb0eef7d6543041d7357416fabe4cea26368779e162d09ff7b30f53c18131` |
| `lab_papers.jsonl.gz` | `b560dc664e59099df8c851ea7d81677217e70ccc5c933ed8f7c8e440653e2665` |
| `student_papers.jsonl.gz` | `d838a8cb4d07b5eb77fede6657c7ee5918acab5e91e55813ab598dd9f8df05b9` |
| `copies.json` | `b819371eee03be90077d15f7f587c0754fe076bcb6304026adf7263a942fb09c` |

Files: `accuracy/sample-michigan.json` (the draw), `accuracy/verdicts-michigan.jsonl` (105 verdicts), `accuracy/screened-michigan.jsonl`, `accuracy/summary-michigan.json`. The six released schools' `sample.json`, `verdicts.jsonl` and `summary.json` are untouched (a rerun of the old and new `sample.py` on the same data gives identical draws for all six). Populations: 14,149 lab papers, 3,175 student-paper links, 9,903 DBLP coverage records, 83 student-coverage candidates.

## The four measures (Wilson 95%)
| Measure | Result | Threshold | |
|---|---|---|---|
| Lab-paper precision (25 uniform) | **0.920 [0.750, 0.978]**, 23/25 | >= 0.95 | **failed** |
| Student-link precision (25 uniform) | **1.000 [0.867, 1.000]**, 25/25 | >= 0.97 | **passed** (point estimate; the interval's lower bound is below 0.97, as for every school at n=25) |
| Lab-paper coverage (15 DBLP records, all true lab papers) | **0.867 [0.621, 0.963]**, 13/15 | >= 0.90 | **failed** |
| Student coverage (10 PhD students) | **1.000 [0.723, 1.000]**, 10/10 | no gate | |

Strata (5 each): lab precision, advisee on an unaffiliated byline 4/5, listing 4/5, identity not a reviewed OpenAlex id 5/5, all 40 = 36/40 = 0.900 [0.770, 0.960]. Student precision strata 5/5 each; all 40 = 40/40.

## Every incorrect item (6 of 105)
| Sample · stratum | Item | Failure | Reason |
|---|---|---|---|
| lab · uniform | Wenisch, W2911565108 | not_a_paper | CACM "Technical perspective", one page (pp. 97-97), a commentary |
| lab · uniform | Guzdial, W2917722693 | not_a_paper | SIGCSE 2019 pp. 502-503, a two-page invited keynote abstract |
| lab · listing | Guzdial, W2981998115 | not_a_paper | CACM Viewpoint (pp. 28-30), an opinion column. Borderline; judged like the 2026-10-29 columns |
| lab · advisee on unaffiliated byline | Ziyou Song, W4406147831 | not_at_school | SSRN preprint; the same title in OpenAlex (W4405433441) credits Song and Bai to the National University of Singapore. The build's Michigan appointment is a stale ECE faculty directory in Wayback (Assistant Research Scientist 2020; Assistant Professor 2024-2026 captures) |
| lab coverage | Wenisch, HPCA 2016 (Selective GPU caches) | missing_from_build | Wenisch is a Michigan author (NVIDIA's publication page lists "Wenisch (University of Michigan)"); OpenAlex credits him to NVIDIA |
| lab coverage | Klasnja, IMWUT 2020 (Personalized HeartSteps) | missing_from_build | UMSI author inside his 2020 period; the build holds only his 2026 papers (2020-2025 papers are absent) |

If the owner counts meeting-abstract-type items as papers nothing changes here (none of the errors is a meeting abstract). The two one-to-three page items (keynote abstract, technical perspective) are the same kind as the CMU, EPFL and MIT `not_a_paper` errors in the 2026-10-29 record; the proposed R1/R2 rules there would catch the title and page patterns.

## Notes on method and exceptions
- **Draw.** `sample.py --school michigan` writes `accuracy/sample-michigan.json`; `record.py`, `evidence.py`, `oalookup.py` and `summarize.py --school` route Michigan to its own files. `summarize.py` also had an undefined `H` import; it now reads `atlas_paths.SchoolDir`.
- **Student-coverage candidates.** The released rule needs a thesis or dissertation source. Michigan's build has none (Deep Blue is never used), so for schools outside the six, `alumni_relation` takes students whose recorded role is PhD alumnus and whose relation (lab alumni page, student homepage, defense listing) has a year >= 2018. Judged in draw order; the first ten confirmed PhD students form the sample. Five candidates were screened out (`screened-michigan.jsonl`): three listed only as "Graduate Student" or with no degree stated, and two under the PI row named "Y Z", whose row mixes people. The ten confirmed students had at least one co-authored paper with the PI, and all ten are linked.
- **Evidence and hosts.** The row itself, DBLP person pages, periods and listings, student sources, OpenAlex API (works by DOI or title, biblio pages), and the NVIDIA research publication page (robots.txt allows all agents, no ClaudeBot or anthropic-ai rule). Deep Blue, news.umich.edu and record.umich.edu were not used, Wayback included; no umich.edu host was fetched live. Rows whose venue shows "Deep Blue" in OpenAlex (Robert, W3206930445) were judged on the row's own authorship and the arXiv DOI, not on Deep Blue.
- **Side observations (not scored).** "Y Z" is a PI row whose name is a placeholder; Michigan student names with a trailing "Site" (Xinyu Hua Site, Joseph Peper Site) carry a page-navigation word; Stella Yu's CVPR 2023 paper credits both Berkeley and Michigan.
