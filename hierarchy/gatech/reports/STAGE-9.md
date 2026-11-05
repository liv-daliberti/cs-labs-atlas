# Georgia Institute of Technology, stage 9: accuracy

Date: 2026-11-05. Gate (`atlas stage-gate gatech 9`): **pass** on the second draw (lab precision 0.960, student-link precision 1.000, lab coverage 1.000).

## Draws
- **Draw 1** (`accuracy/sample.py --school gatech` on the first final build, 21,044 lab papers; seed 20261029): lab precision 21/25 = **0.84, failed**. Four `not_a_paper`: a 'Closure to "..."' reply (J. Struct. Eng.), a poster abstract (SoCC 2018 'Mnemo'), a guest-editor 'Special Topic on ...' (JXCDC) and an IEEE Micro 'Special Issue on Top Picks'. Student links 25/25, coverage 10/10. Not recorded in verdicts (judged and discarded after the rule).
- **General rule R-PAP-31** (docs/RULES.md; tools/pihier/papers.py `REPLY_COMMENTARY_TITLE`, `SPECIAL_ISSUE_TITLE`; tests/test_not_paper_replies_and_special_issues.py): a closure, discussion, "authors' reply" or quoted comment/reply is a commentary; a 'Special Issue/Topic/Section on ...' or 'Top Picks from ...' title is an editorial. It drops 31 Georgia Tech lab papers (21,044 to 21,013) and about 100 rows across the eight packages at their next rebuild (every school's counts move; no data of another school was touched here). The poster abstract has no general signal that spares real EC/ACM extended abstracts (Delarue, EC 2024), so it stays a residual.
- **Draw 2** (after the rebuild, 21,013 lab papers; same seed, the lab population moved so the draw differs; hashes in `accuracy/summary-gatech.json`, 95 verdicts in `accuracy/verdicts-gatech.jsonl`, files `sample-gatech.json`): below.

## The measures (Wilson 95%)
| Measure | Result | Bar | |
|---|---|---|---|
| Lab-paper precision (25 uniform) | **0.960 [0.805, 0.993]**, 24/25 | >= 0.95 | passed |
| Student-link precision (25 uniform) | **1.000 [0.867, 1.000]**, 25/25 | >= 0.97 | passed |
| Lab-paper coverage (15 DBLP records; 10 are true lab papers, all in the build; 5 are Kiyavash 2022 (EPFL by then) or Van Hentenryck 2017-18 (Michigan), correctly absent) | **1.000 [0.723, 1.000]**, n=10 | >= 0.90 | passed |
| Student coverage | not measured: 0 candidates (no thesis or alumni-relation source yet) | no gate | |

Strata (5 each): lab, advisee on an unaffiliated byline 5/5, listing 4/5, identity not reviewed 5/5, all 40 = 38/40; student links: advisee-name 5/5, within-lab 1/1, full-name 2/5, fill 4/4, all 40 = 37/40.

## Every incorrect item (5 of 95)
| Sample | Item | Failure | Reason |
|---|---|---|---|
| lab, uniform | Fumin Zhang, W2894741214 | not_a_paper | guest-editors' editorial of the FITEE marine information technology special issue (DOI 10.1631/fitee.1820000, seven editor-authors) |
| lab, listing | Essa, W4385489965 | other | 'Video Textures' as a 2023 ACM Books chapter: a reprint of the 2000 SIGGRAPH paper |
| student, full-name stratum | Peter Anderson (Batra) | wrong_student | research scientist (role 'other'), not a student |
| student, full-name stratum | Beste Basciftci (Van Hentenryck) | wrong_student | recorded advisers are Ahmed and Gebraeel, not the linked PI |
| student, full-name stratum | Andoni Elola (Clifford) | wrong_student | visiting researcher, not a student |

The three student errors share a cause: a person whose recorded role is `other` (or whose advisers name another PI) enters through the full-name byline route. Not fixed (uniform precision passes); a rule "full-name route needs a student role and the PI among the advisers" is the candidate (owner decision in the report).

## Method notes
Judged from `accuracy/evidence.py` sheets and `accuracy/oalookup.py` (OpenAlex works by DOI or title; `AFF['gatech']` added; about 20 credits). Hosts used: OpenAlex API only; no repository.gatech.edu fetch.
