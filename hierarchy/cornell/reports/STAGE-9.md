# Cornell stage 9 (accuracy): early go/no-go draw, 2026-11-25

Early go/no-go draw (owner rule 2026-11-05: spot-checks are judged right after the build, before freeze). It binds the stage-7 build 32548965 and copies.json from lab_paper_copies.py (32551828), taken while downloads had just started. Gate 9's staleness check will force a redraw after the final build, once the unit (department-search) candidates are added.
Sample: `accuracy/sample-cornell.json` (35 / 40 / 15 / 0 rows by measure, 105 hand judgments). Review: `atlas review-page accuracy/sample-cornell.json`, then `accuracy/summarize.py`. The worker must not judge; a separate reviewer does.

Where to look (known weaknesses, nothing pre-fixed):
- Copies: the draw was taken with downloads only just started, so downloaded-copy rows are expected to be thin; judge only what is recorded.
- Lab websites: 6 labs have no official link recorded; 2 hosts are blocked by robots (recorded as access_blocked); 91 labs are "PI homepage only" and 29 "no web presence found" (check these reasons).
- Students: lab-page student rounds and the live student pass are still running; the units captures are about 23 of ~300, so older appointment evidence is thin.
- Identity: Pollack and Brachman are held (no anchor, excluded non-PIs); 152 PIs got decisions from the identity fix.
