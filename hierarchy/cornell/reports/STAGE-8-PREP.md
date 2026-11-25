# Cornell stage 8 preparation (not started), 2026-11-25

Owner: downloads wait for gate 2 to genuinely pass (no exception). Nothing below has been run except the two read-only checks.

## Readiness now
- `atlas stage-gate cornell catalogue` and `tools/downloads_ready.py cornell`: `ready: false`, settled PIs 157, catalogue rows 6,351 (all ready, 0 held per PI). The only school blocker printed is "build is older than pi-works.sqlite (rebuild: pi_hierarchy.py cornell)": the stage-7 post chain's build (32548965) fixes it. Pollack and Brachman show as held (no identity anchor): they are excluded non-PIs (D-0009), so they do not count as PIs. The readiness record does not list gate 2 as a blocker today; it must be re-read after the stage-2 review and the audit.
- Disk: /n/fs/resemble 571 GB free (96% used), above the 50 GB floor; disk-guard job 32549963 is running.
- `fulltext-push/add_works.py` (`--early`) and `fulltext-push/loop_starter.py` (`--early`) are present in the worktree.

## Start commands (step 1 of the resume list, after the stage-2 audit is drawn and gate 2 passes)
1. `bin/atlas stage-gate cornell catalogue` must print `"ready": true`.
2. `bin/atlas run fulltext-push/add_works.py cornell --early` (collector interpreter; adds the school's works to the catalogue).
3. `LOOP_STARTER_CHANNELS="oa_arxiv openalex s2 core core_bulk europepmc pmc labpages" nohup bin/atlas run fulltext-push/loop_starter.py --early cornell` (starts `school-collector.slurm` once the copy-quality cache is warm; it refuses on `Preempts:`).

## Catalogue not pruned (2026-11-25)
After the stage-9 early rules the rebuild removed 75 lab_papers rows, but the download catalogue still holds those works (added by `add_works --early` before the rules). They are left in place: release reads lab_papers, so the extra works only cost download time. `fulltext-push/add_works.py` has no sync or prune mode (grep for prune/sync finds none): it only adds what the catalog lacks, so nothing removes them on its own.
