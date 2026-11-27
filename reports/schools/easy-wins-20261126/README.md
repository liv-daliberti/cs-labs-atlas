# First ten wins: implementation and refreshed progress

All ten requested tasks are complete. Reviewed inputs landed on local main at `075b0cd2`; 51 validated native/generated output files were then promoted. Raw databases and generated packages follow the repository’s data layout and are represented here by hashes and receipts. The GitHub development branch receives the reviewed inputs and this report.

[Full 40-school progress table](table.md) · [CSV](table.csv) · [Next ten wins](NEXT-WINS.md) · [Machine-readable snapshot](snapshot-ranked.json)

| Order | Original win | Completed result |
| --- | --- | --- |
| 1 | Harvard schema repair | Normalized seven reviewed home-decision records without changing academic-home facts; all previously throwing gates now evaluate. |
| 2 | Seven offline availability ledgers | Created missing ledgers for UMD, ETH Zurich, Cornell, KAIST, NYU, UCSD and Northeastern; all seven passed gate 8 at initial validation. Existing local-copy counters were preserved. |
| 3 | Toronto homes and websites audit | Corrected 39 academic-home decisions. Fresh independent homes draw passed 50/50; website draw passed 50/50 with six original positive-body retention limits disclosed. Gate 3 passes. |
| 4 | NYU excluded-faculty rework | Reviewed the full 358-row original excluded class and recovered 19 faculty. Fresh 50-row draw retained 49 passes and one source-backed fixed finding. Native census 208 to 227; PI-paper records 6065 to 6217. Gate 2 passes. |
| 5 | NTU, VT and WashU appointment gaps | VT official rendered profile supplies actual assistant/associate appointment dates. WashU 2024 and 2025 official programs recover 12 PI-paper records. NTU 2023–2025 remain explicitly unproven. All three gate 4 checks pass. |
| 6 | Oxford and UW paper gaps | Recovered 17 Oxford Rui Ponte Costa PI-paper records and one UW Andres Erbsen paper using retained primary evidence. UW now has papers for all 229 native PIs. Both gate 5 checks pass. |
| 7 | UIUC cached websites | Materialized the full 370-row register: 205 sites, 148 bounded reasons and 17 pending rows. Independent 50-row draw has 49 passes and one corrected foreign-profile finding. Sixteen official-link gaps remain. |
| 8 | Purdue cached websites | Expanded the register from 84 to 361 rows. Final: 161 sites, 153 bounded reasons, 47 pending; 59 prior cached rows corrected through class rework and independent redraw. Fresh draw retained 48 passes and two verified fixes. Fifty-two official-link gaps remain. |
| 9 | UMD researched student batch | Added 46 source-reviewed memberships across ten previously empty PI labs, with all 46 independently checked. Native builder added 191 student-paper links and preserved all 4873 PI-paper records. |
| 10 | NUS researched student batch | Added 43 source-reviewed memberships across ten previously empty PI labs, with all 43 independently checked. Native builder added 89 student-paper links and preserved all 6746 PI-paper records. |

## Validation and interpretation

The source landing passed 6,192 tests, with 23 skipped; lint and all 40 charter checks passed. Seven rebuilt native packages passed schema validation. Preservation receipts cover existing faculty, memberships and PI-paper records; UW has exactly three independently source-checked visiting-scholar candidate links retired by the current student-role guard. The memberships and all corresponding papers remain.

This batch added 19 faculty, 182 PI-paper records, 89 student memberships across 20 previously empty labs, and 280 derived student-paper links. PI-paper records count PI/work relationships and can overlap across labs. The independently reviewed new facts concern source-backed memberships; the 280 generated links have native preservation checks and were not each hand-certified.

NTU’s 2023–2025 appointment years remain unproven. UIUC and Purdue retain pending websites and provenance/audit work. Toronto’s initial website audit records six cases whose original positive bodies were not retained; this limit is preserved in the reviewed audit. A passed workflow gate can include an explicitly supported bounded outcome or unknown rather than a newly discovered website or appointment.

The table is freshly measured from canonical packages, live gate evaluations and independent student-role recounts. Other contributors’ concurrent work is included, so changes relative to the user’s earlier table cannot all be attributed to these ten tasks. Each row records its source signatures and measurement time, and validation confirms stable reads with no gate exceptions or student-count disagreements.

Scores retain the existing formula: 30% student coverage, 20% PI-paper coverage, 20% resolved homes/websites, 20% gates, 10% local-copy coverage. Stage-3 process inventories can differ from the native PI census. Local-copy measurements use exact-package private recounts for changed packages when their canonical counters were older or had different work keys; the snapshot records which path and count time was used. Canonical copy-counter files were left to their existing owner.

`refresh.py`, `render.py` and `copy-sources.json` preserve the table recipe and source selection. `opportunities-snapshot.json` preserves the cached lead counts used to prioritize the next ten; parser proposals are research leads and may overlap already admitted members. Primary source hashes, original audit failures, whole-class repairs and redraw results remain in the tracked per-school reviewed artifacts and the evidence receipts.
