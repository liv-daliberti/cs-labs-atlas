# Michigan, stage 8: full texts

Date: 2026-11-01. Gate: **not passed** (copies 53.0% against the 85% target; the ledger is `incomplete_check` for 5,449 of 5,850 papers).

## What was done
1. Catalog seeded with `fulltext-push/add_works.py michigan` on the login host (Slurm 32041316 for the add-works pass).
2. Channels and the download loop ran as one Slurm job, `fulltext-push/michigan-collector.slurm`: 32041321, then 32041862 (the one still running). Channels run in order: oa_arxiv, openalex, proceedings, arxiv_title, dblp_ee, s2, core, europepmc, pmc, figshare, labpages, pihomes, wayback_acm. All finished 2026-10-31 23:48 UTC. `labpages` and `pihomes` **failed** (below); `wayback_acm` found 799 candidates on 1,404 ACM DOIs.
3. The loop is at round 15 and `queue_exhausted`: every remaining queued URL sits on a paused source (dspace.mit.edu HTTP 429, t2r2.star.titech.ac.jp robots delay, figshare bot challenge).
4. `tools/lab_paper_copies.py michigan` (counted 2026-11-01 14:37 UTC), then the ledger `fulltext-push/unavailable_ledger.py michigan` as Slurm **32046860** from a code snapshot (`atlas submit`, pinned 6a6a041 plus 3e88cbe on main; COMPLETED in 5 min, its OpenAlex/S2/CORE/PMC/DBLP/arXiv checks reused from the earlier runs' checks store).
   - Ledger runs that failed first: 32043773 (live code, broken by the ftroute landing), 32046841 (S2 pace file inside the snapshot, fixed in a469f4c), 32046849 (`KeyError: 'michigan'` in the repository check, fixed in 3e88cbe: Deep Blue is never asked; only what OpenAlex and CORE list is recorded and no Deep Blue link counts as a usable copy).

## Counts
- Lab papers 12,455. **Local copies 6,605 (53.0%)**, up from 1,222 (9.8%) on 2026-10-31 18:56. Catalog: downloaded 6,423, fulltext_xml 267, needs_access_review 1,469, queued 4,296; 87 copies pending identity review (not counted).
- Non-local 5,850: queued 4,295, needs_access_review 1,468 (no access cause recorded yet), identity_unconfirmed 87.
- Ledger reasons (`hierarchy/michigan/unavailable-summary.json`):

| reason | papers |
|---|---|
| incomplete_check (labpages check missing) | 5,449 |
| found_awaiting_download | 259 |
| found_not_in_catalog | 86 |
| pending_retry | 55 |
| identity_unconfirmed | 1 |

- Publishers of the non-local: IEEE 2,816, ACM 628, Elsevier 497, Springer Nature 389, SAGE 124, Wiley 109.
- Host rules kept: Deep Blue, news.umich.edu and record.umich.edu never used; Cloudflare-challenged umich.edu hosts read only from Wayback captures.

## Open items
1. **Lab-page captures.** Michigan has no `hierarchy/michigan/labpage-captures.sqlite` (only `labpage-audit-captures.sqlite`). The `labpages` and `pihomes` channels died with "unable to open database file", and the ledger's `labpages` check is missing for all 5,850 papers: this alone makes 5,449 of them `incomplete_check`. Needs the lab-page capture store (lab-page audit) or a recorded `not_applicable` decision, then `unavailable_ledger.py michigan --max-age-days 30` and the `labpages`/`pihomes` channels again.
2. The collector's final export crashes every round (`receipts` has no `graph` row; `collect_princeton_fulltext.export`), exit 1 after the pass. Downloads are not affected; seed the `graph` receipt or skip the export for Michigan.
3. 1,468 `needs_access_review` works have no access cause: run `review_access.py classify michigan` / `apply`.
4. 259 `found_awaiting_download` and 86 `found_not_in_catalog` are recoverable by the next loop round and `add_works.py`.
5. 87 pending identity reviews: `identity_review.py` for Michigan.
6. Coverage target 85% is not met; the remaining gap is mostly queued URLs on paused hosts and publisher paywalls.

## Running jobs and restarts (owner decision 2026-11-01)
The six school loops (32041175_0, 32041308_1-5) and Michigan's collector 32041862 run on the **old code**. Leave them running to their 3-day limit (about Nov 3), or until one stops for another reason. Restart each then with `bin/atlas submit` (pins the commit; code snapshot with the FT_* data slots), `--test-only` first, never on "Preempts:". Michigan: `atlas submit fulltext-push/michigan-collector.slurm`; schools: `atlas submit --array=<n> fulltext-push/downloads.slurm` (0 princeton, 1 cmu, 2 epfl, 3 mit, 4 berkeley, 5 stanford). A plain `scancel -s TERM` does not reach the loop (it needs `--batch`), and stopping them early is not allowed.

## Gate
- Copies measured; **53.0%, below the 85% target.**
- Every non-local lab paper has a ledger entry; `incomplete_check` 5,449 exceeds any whitelist threshold until open item 1 is closed.

**Not passed.**
