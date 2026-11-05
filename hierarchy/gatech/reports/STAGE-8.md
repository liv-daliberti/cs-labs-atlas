# Georgia Institute of Technology, stage 8: full texts

Date: 2026-11-05. Gate (`atlas stage-gate gatech 8`): **fail** on the 85% target only (ledger exists, 46 `incomplete_check`); the target is out of reach under the access rules (ceiling below).

## Measured (`tools/lab_paper_copies.py gatech`, counted 2026-11-05 after the final build)
| | papers | share |
|---|---|---|
| lab papers | 21,013 | |
| local copy (PDF or full-text XML) | 8,855 | **42.1%** |
| needs_access_review (closed) | 3,752 | |
| queued, never reached | 8,288 | |

## Why the rest has no copy (ledger `fulltext-push/unavailable_ledger.py gatech`, 12,158 papers, docs/UNAVAILABLE.md)
publisher_only_closed 6,460 · found_awaiting_download 2,085 · landing_page_without_pdf 1,884 · open_copy_robots_disallowed 987 · paywall_only 222 · pending_retry 138 · found_not_in_catalog 114 · open_copy_unusable 95 · no_doi_no_match 74 · open_copy_bot_challenge 50 · incomplete_check 46 · open_copy_behind_login 3 (identity_unconfirmed 115 papers sit inside the local count until the identity review).
Final (closed for good under the rules): 9,775. Recoverable: found_awaiting_download + found_not_in_catalog + pending_retry = 2,337.

## Expected rate when the collector finishes
Ceiling = (8,855 + 2,337) / 21,013 = **53.3%**; the 85% target cannot be met without paywalled, login or robots-disallowed copies. The loop has not moved since 02:56 UTC on 11-05 (+208 downloads in 14 h; queued 8,232 flat) because web.archive.org (shared 429 cooldown) and dspace.mit.edu are paused: the 2,085 awaiting-download papers are mostly ACM PDFs found through the Wayback channel. Expect 48-53% once Wayback answers again.

## Collector
Job 32104361 (school-collector.slurm SCHOOL=gatech, node916, started 11-04 13:43, 3-day limit, ends about 11-07 13:43) was submitted from a script with no `--signal` and no loop_job: **it will not resubmit itself**. `fulltext-push/school-collector.slurm` on this branch now uses loop_job.sh (USR1 900 s before the limit, `atlas submit` of itself); after landing, chain the replacement with `SCHOOL=gatech atlas submit --dependency=afterany:32104361 fulltext-push/school-collector.slurm`.

## Fixes made here (tests)
- The `labpages` channel crashed on Georgia Tech (`labpage-captures.sqlite` missing: a charter school has only the audit's `labpage-audit-captures.sqlite`), and the ledger then marked every paper `incomplete_check` (10,187 of 12,189). `labpage_channel.captures_db` falls back to the audit store; after re-running the channel (349 candidates, 337 papers found) the ledger has 46 `incomplete_check`. tests/test_labpage_channel_audit_captures.py.
- 77 new lab papers (the identities and periods of this round) were added to the catalog with `add_works.py gatech`.
