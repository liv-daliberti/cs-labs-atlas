# UChicago Statistics and CAM rosters: deep dive on the 75 old-rule pairs (2026-11-04)

Nothing is wired. Verdicts, quotes, URLs and capture dates: `hierarchy/uchicago/reviewed/roster-pair-verdicts.json` (built by `tools/roster_pair_verdicts.py`; fetcher `tools/roster_dive_fetch.py`: robots.txt including ClaudeBot/anthropic-ai groups, Wayback only through `fulltext-push/host_throttle.py`'s shared clock). Raw captures: `hierarchy/uchicago/raw/roster-dive-captures.sqlite` (data, not in git).

## Verdicts
| verdict | pairs | meaning |
|---|---|---|
| true | 41 | the PI's own page, the student's own page or CV, or a co-adviser's page names the student as this PI's (co-)advisee |
| not | 15 | a different adviser is named and this PI does not list the student (7), the paired person is a namesake (4 Yuhan Liu pairs), or absent from the PI's personnel page that covers those years (4: Lin Chen/Stephens, Zihao Wang/Stephens, Yian Chen/Lim, Yifan Peng/Livescu) |
| unsettled | 19 | no page found either way |

(basis counts: listing 41; other-adviser 7; namesake 4; absence 4; none 18; one unsettled pair, Hur/Khoo, carries an other-adviser note.)

Findings beyond the five earlier hand checks:
- **Co-advising is common, so "another adviser named" is not "not an advisee"**: Haoyang Liu (Barber and Gao), Yu Gui (Barber and Ma), Wanrong Zhu (Barber and Wu), Yuguan Wang (Khoo and Hoskins), Rossellini (Barber and Willett), Sen Na (Anitescu and Kolar). Only the PI's own list, or a statement that excludes the PI, settles a pair.
- **Namesake pairs**: the four Yuhan Liu pairs (Hoffmann, Jiang, Maire, Lu) pair the Statistics roster's Yuhan Liu (PhD alumnus 2024 on stat.uchicago.edu/alumni/phd-alumni/) with the CS PhD student of the same name (listed on Shan Lu's page and as "Yuhan Liu (with Shan Lu)" on Junchen Jiang's). Any name-based roster rule keeps them.
- **Settled by own pages**: Park/Veitch is true (kihopark.github.io: "advised by Victor Veitch"), reversing the "unsettled" in ROUND9; June Wu/Tulsiani is true (Tulsiani's page: "June Wu ... co-advised with Shmuel Weinberger. PhD 2025"). Lo/Khoo remains unsettled.
- Not usable: the Mathematics Genealogy Project answers again, but its robots.txt names ClaudeBot and anthropic-ai with `Disallow: /`, so it was not fetched (a web-search snippet mentioned a Hur/Khoo entry there; not used). Statistics `/events/` is robots-disallowed and was skipped. The UChicago ETD has no Statistics or CAM dissertations (ROUND9).
- Local full text (texts.sqlite, 2,979 usable UChicago papers): every student-name-near-"advis/thesis/dissertation" hit was a citation context, none an acknowledgement naming an adviser; no pair settled this way.
- Wikidata: `tools/wikidata_students.py` was not run for these students (no pair depended on it).

## Rule measurements (56 settled pairs: 41 true, 15 not; Wilson 95% intervals)
Precision is against the 56 settled pairs. Recall is against the 41 true pairs; it is a recall within the roster pairs only (advisees with no roster pair are not counted).

| rule | kept | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|
| old (PI last, or 2+ papers) | 56 | 41 | 15 | 0 | .73 (.60-.83) | 1.00 (.91-1) |
| R* (3+ papers, or 2+ with PI last) | 36 | 30 | 6 | 11 | .83 (.68-.92) | .73 (.58-.84) |
| R* minus pairs with another adviser/namesake evidence | 34 | 30 | 4 | 11 | .88 (.73-.95) | .73 (.58-.84) |
| 3+ papers | 25 | 21 | 4 | 20 | .84 (.65-.94) | .51 (.37-.66) |
| 2+ papers and PI last on 1+ | 27 | 23 | 4 | 18 | .85 (.68-.94) | .56 (.41-.70) |

Without the four `absence` verdicts (52 pairs): old .79 (.66-.88) / 1.00; R* .94 (.80-.98) / .73; R* minus other-adviser/namesake 1.00 (.89-1) / .73; 3+ papers .91 / .51.

Reading:
- The old rule has perfect recall and a precision of about .73-.79: about one pair in four to five is wrong. R* removes most wrong pairs (precision .83-.94) at the price of losing 11 of 41 real advisees (recall .73), which are the Statistics and CAM pairs with 2 papers and the PI not last.
- The third rule (drop a pair when the student is on another PI's page or names another adviser) is an oracle here: the "other adviser" facts come from the same pages that settle the pairs, and with co-advised students it would also drop real pairs (Gui/Ma, Gui/Barber) if applied bluntly. Its apparent gain (precision 1.00 on 52 pairs) is an upper bound. It also needs the evidence for every student, which is exactly what is missing for the 19 unsettled pairs.
- No paper-count rule does clearly better than R*: the best intervals overlap broadly (n = 56). Byline order is no advising signal in these departments.
- Bias: the 56 settled pairs are those whose PI publishes a student list (Barber, Sanz-Alonso, Stephens, Lim, Willett, Donnat, Srebro, Ma, Tulsiani) or whose student has a homepage. PIs without a list (Khoo, Bal, Schein, Wu, Gao, Amit, Veitch) are over-represented among the 19 unsettled pairs, so these precision numbers describe the listed-PI world, not the whole roster.

## Recommendation: (b), wire only the evidence-confirmed pairs
- Not (c): no rule has an interval that clears a quality bar. R* is the best simple rule but is wrong for about one in six kept pairs and drops a quarter of the real advisees; the old rule is wrong for a quarter.
- Not (a): 41 pairs are confirmed by a source that is stronger than a lab-page row (the PI's own page or the student's own statement). Keeping them off loses real advisee relations.
- (b): the 41 `true` pairs as evidence-backed relations, each carrying its URL, quote and capture date (the JSON is shaped for that). The 19 `unsettled` pairs stay off; the 15 `not` pairs must never be produced by any rule.
- If the owner still wants a rule for the remainder, R* with the namesake guard (drop a roster student whose name is also a different person's name in a CS/other PI's lab list) is the least bad.
