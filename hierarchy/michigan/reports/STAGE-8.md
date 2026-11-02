# Michigan, stage 8: full texts

Date: 2026-11-01. Gate: **not passed** (copies 53.5% against the 85% target; the ledger is complete: `incomplete_check` 0 of 5,793).

## What was done
1. Catalog seeded with `fulltext-push/add_works.py michigan` on the login host (Slurm 32041316 for the add-works pass).
2. Channels and the download loop ran as one Slurm job, `fulltext-push/michigan-collector.slurm`: 32041321, then 32041862 (the one still running). Channels run in order: oa_arxiv, openalex, proceedings, arxiv_title, dblp_ee, s2, core, europepmc, pmc, figshare, labpages, pihomes, wayback_acm. All finished 2026-10-31 23:48 UTC. `labpages` and `pihomes` **failed** (below); `wayback_acm` found 799 candidates on 1,404 ACM DOIs.
3. The loop is at round 15 and `queue_exhausted`: every remaining queued URL sits on a paused source (dspace.mit.edu HTTP 429, t2r2.star.titech.ac.jp robots delay, figshare bot challenge).
4. `tools/lab_paper_copies.py michigan` (counted 2026-11-01 14:37 UTC), then the ledger `fulltext-push/unavailable_ledger.py michigan` as Slurm **32046860** from a code snapshot (`atlas submit`, pinned 6a6a041 plus 3e88cbe on main; COMPLETED in 5 min, its OpenAlex/S2/CORE/PMC/DBLP/arXiv checks reused from the earlier runs' checks store).
   - Ledger runs that failed first: 32043773 (live code, broken by the ftroute landing), 32046841 (S2 pace file inside the snapshot, fixed in a469f4c), 32046849 (`KeyError: 'michigan'` in the repository check, fixed in 3e88cbe: Deep Blue is never asked; only what OpenAlex and CORE list is recorded and no Deep Blue link counts as a usable copy).
5. Follow-ups, 2026-11-01:
   - Export crash fixed (6f5399e): the catalog had no `graph` receipt; `source_graph()` tolerates its absence and Michigan's receipt was seeded.
   - `review_access.py classify|apply michigan`: 1,469 works, closed 1,431 and requeue_transient 38 (backup `backups/catalog.before-review-access-20261101.sqlite`). Closed causes: robots_disallow 705, landing_no_pdf 385, paywall_or_forbidden 196, policy_skip 30, challenge 23, not_found 17, other small.
   - `identity_review.py` on the 87 pending copies: 55 confirmed by the arXiv rule, 2 more by alternative titles, 0 reverted; 30 stay pending (not counted).
   - Lab-page captures arrived (`hierarchy/michigan/labpage-captures.sqlite`, 1,810 rows). The labpages channel now reads page roots from `labpage-evidence.json` and `labpage-audit.jsonl.gz` (e013a77). Job 32046887 (snapshot of e013a77, 10 min): labpages 401 candidates for 347 works (205 PIs with missing papers); pihomes 159 candidates for 97 works (174 PIs without a site).
   - Ledger re-run 32046889 (45 s, checks reused): `incomplete_check` 5,449 -> 0.

## Counts (copies counted 2026-11-01 14:57 UTC; ledger built 2026-11-01)
- Lab papers 12,455. **Local copies 6,662 (53.5%)**, up from 1,222 (9.8%) on 2026-10-31 18:56 and 6,605 before the identity review. The loop keeps downloading (the channels' own count was 6,692 minutes later).
- Non-local 5,793: queued 4,333, needs_access_review 1,430 (all with a recorded cause), identity_unconfirmed 30.
- Ledger reasons (`hierarchy/michigan/unavailable-summary.json`, 5,793 papers, `incomplete_check` 0):

| reason | papers |
|---|---|
| publisher_only_closed | 3,248 |
| landing_page_without_pdf | 970 |
| found_awaiting_download | 707 |
| open_copy_robots_disallowed | 589 |
| paywall_only | 94 |
| no_doi_no_match | 60 |
| open_copy_unusable | 41 |
| pending_retry | 34 |
| found_not_in_catalog | 29 |
| open_copy_bot_challenge | 19 |
| identity_unconfirmed | 1 |
| open_copy_behind_login | 1 |

- Host rules kept: Deep Blue, news.umich.edu and record.umich.edu never used (the ledger's repository check records what OpenAlex and CORE list for Deep Blue and never counts it as a usable copy); Cloudflare-challenged umich.edu hosts read only from Wayback captures.

## Open items
1. 707 `found_awaiting_download` and 29 `found_not_in_catalog`: picked up by the running loop and `add_works.py` on the next rounds; re-run `tools/lab_paper_copies.py michigan` and the ledger afterwards.
2. 30 copies pending identity review (22 have no alternative title, 8 undecided): manual look or leave uncounted.
3. 38 `requeue_transient` works are back in the queue; the paused hosts (dspace.mit.edu 429, t2r2.star.titech.ac.jp robots delay, figshare bot challenge) hold most of the remaining queue.
4. Coverage target 85% is not met; the gap is mostly publisher paywalls (publisher_only_closed 3,248) and landing pages without a PDF (970).

## Running jobs and restarts (owner decision 2026-11-01)
The six school loops (32041175_0, 32041308_1-5) and Michigan's collector 32041862 run on the **old code**. Leave them running to their 3-day limit (about Nov 3), or until one stops for another reason. Restart each then with `bin/atlas submit` (pins the commit; code snapshot with the FT_* data slots), `--test-only` first, never on "Preempts:". Michigan: `atlas submit fulltext-push/michigan-collector.slurm`; schools: `atlas submit --array=<n> fulltext-push/downloads.slurm` (0 princeton, 1 cmu, 2 epfl, 3 mit, 4 berkeley, 5 stanford). A plain `scancel -s TERM` does not reach the loop (it needs `--batch`), and stopping them early is not allowed.

## Gate
- Copies measured; **53.5%, below the 85% target.**
- Every non-local lab paper has a ledger entry and `incomplete_check` is 0.

**Not passed** (coverage only).
