# Ten wins: measured results

Completed all ten items. Added **264 native member records**, with **13 additional PIs containing student-role data** across the five student batches. Held 25 unsupported legacy ETH member records; the net member gain is 239.

The comparison uses this wave’s frozen 40-school baseline. Other contributors continued work during the run; changes outside these eight targeted schools are not attributed to this batch. Target-school score changes also reflect current shared copy counters and gates; the native changes described below are separately bound to this wave’s validated output hashes.

[Refreshed full 40-school table](TABLE.md) · [CSV](table.csv) · [Before table](BEFORE.md) · [Next ten wins](NEXT-10.md)

| School | PIs with student data, before → after | Homes/websites resolved, before → after | Score, before → after | Change |
| --- | --- | --- | --- | --- |
| Purdue | 321 → 321 | 226/361 → 272/361 | 73.2 → 75.8 | +2.5 |
| UIUC | 126 → 126 | 337/370 → 349/370 | 54.4 → 55.0 | +0.6 |
| Harvard | 201 → 201 | 149/244 → 134/244 | 77.2 → 75.9 | -1.2 |
| NUS | 10 → 11 | 0/140 → 114/140 | 38.3 → 54.8 | +16.5 |
| UMD | 10 → 14 | 99/99 → 99/99 | 55.9 → 57.2 | +1.2 |
| NYU | 3 → 6 | 150/227 → 150/227 | 41.7 → 42.1 | +0.4 |
| ETH Zurich | 4 → 7 | 210/210 → 210/210 | 52.9 → 53.3 | +0.4 |
| USTC | 0 → 2 | 109/198 → 109/198 | 41.7 → 42.0 | +0.3 |

Score changes use unrounded values.

## The ten completed items

| # | Item | Result |
| --- | --- | --- |
| 1 | Compressed cached HTML | Decode retained zlib/HTTP-gzip views for literal links, cards and profile chains while preserving original response bytes and SHA-256 evidence identities. Corrupt gzip fails closed. |
| 2 | Purdue website leads/provenance | Three recovered sites, source-backed provenance reviews and repairs to wrong page selections. Five provenance gaps remain. |
| 3 | UIUC provenance | Two remaining gaps; Sarita Adve’s wrong-person site and Sreenivas’s false rejection independently repaired. Original failed judgments retained. |
| 4 | Harvard inventory | Current 214-PI inventory; twelve owned sites recovered during full negative-class rework, plus earlier source repairs. 116 sites, 37 bounded reasons, 61 pending cases. |
| 5 | NUS inventory | Current 140-PI inventory; recovered Xiao and Soh homepages, repaired article/shell selections and false negative reasons. 58 sites, 58 bounded reasons, 24 pending cases. |
| 6 | UMD student batch | 58 new member records; student coverage 10 → 14 PIs. Current Tianyi roster remains held for School-period proof. |
| 7 | NUS student batch | 33 new records; student coverage 10 → 11 PIs. Includes Angela Yao and Lu Yao omissions; old accepted Lu facts preserved. |
| 8 | NYU student batch | 29 new records; student coverage 3 → 6 PIs. Shared Bonneau-group assignments held without individual ties. |
| 9 | ETH student batch | 81 new member records and additive Paul Paschmanns PhD evidence; student coverage 4 → 7 PIs. Full legacy-class review held 26 unsupported source relations. |
| 10 | USTC student batch | 63 new member records; student coverage 0 → 2 PIs. Mixed degree headings stay generic; UVa and undated former-student claims held. |

## What the checks establish

All five native packages passed schema validation. Existing PI inventories stayed unchanged. All other member facts and paper rows were preserved except the exact independently reviewed corrections below.

The builds added 618 candidate student-paper link rows and removed 169 old source-bound rows affected by the ETH corrections, a net increase of 449. Source audits establish the sampled roster facts; these link counts do not certify every candidate paper association.

ETH: all 54 older members and 55 relations were reviewed after the initial 41/9 failed sample. Twenty-six source relations were held as visible unresolved observations. Twenty-nine supported relations remain, including Christina Giannoula’s 2019 ETH visit. Her separate NTUA degree claim is held. Paul’s original generic membership remains alongside the literal PhD statement. A fresh 50/110 audit passed without transferring old verdicts.

NYU: one old proceedings preface was removed under the existing paratext rule after independent review of the [publisher page](https://proceedings.mlr.press/v83/mohri18a.html) and both PDF pages. All 6,216 other NYU PI-paper rows remain.

Final website audits: Purdue 50 accepted; UIUC 48 pass/2 independently fixed; Harvard fresh 50 pass after complete review of its 88 reason rows; NUS 49 pass/1 independently fixed. Final student audits: UMD 50 pass, NUS 50 pass, NYU all 42 pass, ETH fresh 50 pass, USTC 50 pass. Original failed Harvard/ETH draws and all fixed-row judgments are retained.

The homes/websites measure requires a valid home and an accepted website or bounded supported reason. Unread destinations and unsupported claims remain open. The same scoring formula and independent student-role recount were used before and after. The stage-3 denominator can differ from the native PI count; the table retains the gate’s actual population.

[Results JSON](results.json), [deltas](deltas.json), [source/audit receipt manifest](receipts-manifest.json), [native validation](native-validation/) and [original evidence histories](evidence/) contain the supporting checks. Canonical copy counters remain under their existing owner; NYU’s changed paper set uses a private native copy recount for this table.

Replay: run `replay/refresh.py` with the atlas environment and the matching tools on `PYTHONPATH`. Original response bodies remain in the registered capture stores; promoted source-carrier rows preserve their original hashes and dates.
