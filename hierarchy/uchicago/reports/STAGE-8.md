# University of Chicago, stage 8: full texts (collection running)

Date: 2026-11-04. Gate (`atlas stage-gate uchicago 8`): not yet reached: copies are 12.1% of lab papers (521 of 4,316 after the first 25 minutes of collection; target 85%), and the unavailability ledger needs the collection to finish.

## What was done
- Catalog seeded with `fulltext-push/add_works.py uchicago` (4,316 lab papers added as queued works).
- New general script `fulltext-push/school-collector.slurm` (SCHOOL=<key>): the open-copy channels (oa_arxiv, openalex, proceedings, arxiv_title, dblp_ee, s2, core, europepmc, pmc, figshare, labpages, pihomes, wayback_acm) with their per-channel locks, plus the lab-first loop (`--recent-first 2023`), on the project env, 3-day limit; submitted as job 32097901 (`atlas submit --from-worktree`), no `OpenAlex` credit beyond the channel's own free lookups. It is not self-restarting (downloads.slurm has a hand-kept array slot per school): resubmit it when it ends at the limit, then run `tools/lab_paper_copies.py uchicago` and `fulltext-push/unavailable_ledger.py uchicago`, then the gate.
- First measurement: `copies.json` local 521, queued 3,641, needs-access-review 149, identity-unconfirmed 5.

## Next (not done)
Let the collection run (expected days at the channels' pace and the 10 s Linguistics / robots delays); then copies, ledger, gate. Quarantine of copies from hosts whose robots.txt disallows ClaudeBot or anthropic-ai is applied by the collector as for other schools.
