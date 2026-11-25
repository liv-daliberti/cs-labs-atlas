# Cornell stage 9 (accuracy): early go/no-go draw, 2026-11-25

Early go/no-go draw (owner rule 2026-11-05: spot-checks are judged right after the build, before freeze). It binds the stage-7 build 32548965 and copies.json from lab_paper_copies.py (32551828), taken while downloads had just started. Gate 9's staleness check will force a redraw after the final build, once the unit (department-search) candidates are added.
Sample: `accuracy/sample-cornell.json` (35 / 40 / 15 / 0 rows by measure, 105 hand judgments). Review: `atlas review-page accuracy/sample-cornell.json`, then `accuracy/summarize.py`. The worker must not judge; a separate reviewer does.

Where to look (known weaknesses, nothing pre-fixed):
- Copies: the draw was taken with downloads only just started, so downloaded-copy rows are expected to be thin; judge only what is recorded.
- Lab websites: 6 labs have no official link recorded; 2 hosts are blocked by robots (recorded as access_blocked); 91 labs are "PI homepage only" and 29 "no web presence found" (check these reasons).
- Students: lab-page student rounds and the live student pass are still running; the units captures are about 23 of ~300, so older appointment evidence is thin.
- Identity: Pollack and Brachman are held (no anchor, excluded non-PIs); 152 PIs got decisions from the identity fix.

## Early draw result and rules (2026-11-25)
Early reviewers (5, shallow: 3-4 tool calls each): lab-paper precision 30.5/35 = 0.87 (fail, bar 0.95), student-link 39.5/40 = 0.99, lab coverage 15/15, student coverage not measurable (0 candidates; fixed in 29afb1df, 417 candidates now). General rules added (9f3eb7bd and the follow-up): chairs' welcome front matter (EDITORIAL_TITLE), IOVS/ARVO no-DOI abstract supplement (R-PAP-64), work-done-at-elsewhere affiliation (R-PAP-62), anchored-id-only author on a work of 100+ authors (R-PAP-63). Rebuild 32552359 removed 75 lab_papers rows (6,746 -> 6,671): Wen Sun 71 (CMS collaboration papers), Naaman 1, Azenkot 1, Fei Wang 1 (IOVS, no DOI), Ellis 1.
Open: #5611 Cheng Zhang "Intelligent Soft Wearables" (UbiComp Companion '25, no venue, DOI 10.1145/3714394.3750561) may be a tutorial/workshop description; no general rule decides it from the stored row, so it stays for the official round.
Thin but judged correct: #3755 Abdelfattah AAAI 2023 and #712 Chattopadhyay STOC 2018 (first-year work possibly done at the previous institution); Snavely ECCV 2016 (on leave at Google).
For the official round the reviewer brief must require row-level checks (open the landing page or the stored record for each row), not a 3-4 call skim.
