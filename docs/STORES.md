# Full-text stores: layout, writers, retention and backup (2026-10-31; ROADMAP item 11)

One store per school, `stores/<school>/` (paths from `paths.sh` / `tools/atlas_paths.py`, `$CS_ATLAS_STORES`).

## What a store holds

| path | what | kept |
|---|---|---|
| `catalog.sqlite` | works, candidates, attempts, assets, access_review: the record of every copy and every try | the one authoritative record |
| `objects/<sha256>.pdf` / `.xml` | the files, content-addressed: one file per distinct content, shared by every work that has it (dedup by sha256) | while a work references it |
| `by_lab/<lab>/<year>--<work>.pdf` | symlinks into `objects/` | rebuilt by the collector |
| `quarantine/robots-ai/` | copies taken from paths robots.txt disallows for an Anthropic crawler, moved out of `objects/` (`fulltext-push/quarantine_robots_ai.py`), with `manifest.jsonl` (work, both paths, sha256, URLs, rule) | kept; `restore` reverses a move |
| `quarantine/identity-rejected/` | files the download-time identity rule rejected (`collector_wrapper.py`), with `manifest.jsonl` | the newest 500 files; older files are deleted (they are not papers), their manifest lines stay |
| `staged/requeued-attempts.jsonl`, `staged/reverted-downloads.jsonl`, `staged/restored-downloads.jsonl` | every attempt row a tool deleted, every download a tool reverted or restored | kept (append-only logs; they make each step reversible) |
| `backups/catalog.<reason>-<date>.sqlite` | catalog snapshots taken before a bulk change | the latest two per store |
| `loop-state.json`, `loop.log` | the download loop's state and log | `loop.log` may be rotated by size |

## One writer per catalog

- **The loop lock.** One download loop per store holds `<store>/.loop.lock` for its whole life (`fulltext-push/lab_first_loop.py`);
  a second loop exits at once.
- **The catalog write lock.** Every write transaction holds `<store>/.catalog-write.lock` from its first write to its commit
  (`fulltext-push/catalog_lock.py`). The holders:
  - the collector, through `collector_wrapper.py`: each saved result, the start-of-pass reclassification and requeue;
  - the channels' candidate writes (`ftp_common.write_batches`, which `write_candidates` and `add_works` use);
  - the recovery and review tools: `requeue_causes`, `revert_downloads` (revert and restore), `review_access apply`,
    `quarantine_robots_ai apply`, `identity_review apply`.

  Each hold is one short transaction (a batch of at most 200 rows, or one work). A writer that cannot get the lock within
  30 minutes refuses with `CatalogBusy` instead of writing beside another.
- **Writers that do not take the lock yet** (code outside `fulltext-push/`): the Princeton package importer
  (`import_all_when_free.py`) and the vendored Infoscience and DSpace resolvers. They write only candidates and are run
  from `run_steps.sh` and the import step. Until they take the lock, run them only while that store's loop is stopped, or
  through `run_steps.sh`.

## Backup and retention policy

- **The catalogs are the record.** A bulk change (a review apply, a quarantine, a revert) takes a snapshot
  `backups/catalog.<reason>-<date>.sqlite` first, unless every row it changes is logged in `staged/*.jsonl` or a
  quarantine manifest (then the log is the backup). Keep the latest two snapshots per store. Each is a few hundred MB to
  2 GB, so no more copies than that on shared storage.
- **Files are not duplicated.** `objects/` is content-addressed; nothing copies it. A file leaves `objects/` only by an
  `os.rename` into a quarantine directory, with a manifest line, never by deletion. The one exception is a rejected file
  in `quarantine/identity-rejected/` beyond the newest 500: it is not a paper, so it is deleted.
- **Releases** (`releases/<id>/`) copy the derived packages, never the stores.
- **No store data enters git.** The repository holds code, docs and reviewed inputs only.
- **Quotas.** Read `df` on the share (`df -h /n/fs/resemble`), never `du` over the stores. Scope any listing to one store
  directory with a bounded depth.
