# Agent instructions (Claude and Codex read this first)

Project rules live in `docs/CONTRIBUTING.md` (branches, landing, reports), `docs/RULES.md` (scope) and `docs/ADDING-A-SCHOOL.md` (onboarding).
Paths come from `paths.sh` / `tools/atlas_paths.py` only. Never push. Stage explicit paths. Never print keys from `~/.config/cs-atlas`.

## Before any work: the shared work queue
Two AI sessions (Claude and Codex) land on `main`. A lease is a per-session lock; the queue is the per-TASK claim that stops two sessions doing the same job.
```
export ATLAS_SESSION=<your stable session id>   # e.g. codex-root-1107; every task command needs it
bin/atlas task list                              # 1. look first: what is open, who holds what, on which branch
bin/atlas task claim T012 --branch agent/x       # 2. claim before the first command of work (REFUSED = a live claim overlaps; it prints the holder and branch)
bin/atlas task heartbeat T012 --job 3152...      # 3. at least every 15 min (ttl 30 min); record Slurm job ids
bin/atlas task done T012 --commit <hash>         # 4. finish with the commit; or: block --note WHY | release (give it back)
```
- New work that is not on the list: `bin/atlas task add --title ... --school ... --kind collect|build|review|land|release|analysis --scope <paths you will write>` and claim it. `add` refuses a duplicate title.
- Scope keys are the paths/files the task writes. Keep them accurate: overlap is how a duplicate is caught. `--allow-overlap 'reason'` is recorded; use it only for provably disjoint work.
- A stale claim (no heartbeat for its ttl) stops blocking; the next claimant takes it over. Keep the lease too (`bin/atlas lease acquire <name>`); the queue does not replace it.
- Long-running work is a restartable Slurm job (explicit --mem/--time/--cpus, `sbatch --test-only` first). The job is the work; agents claim only the REVIEW step ("review T033 results") and heartbeat while the job runs.
- Landing: `bin/atlas task land-lock acquire`, then `tools/agent_worktree.sh land <name>`, then `bin/atlas task land-lock release`. Without the lock the land warns (`git config atlas.landLock enforce` makes it refuse).

## Store-sourced schools: record decisions, never edit their reviewed JSON
A school whose charter says `[evidence] source = "store"` (check: `bin/atlas evidence-store flagged`; currently **michigan** and **princeton**) keeps its decisions in `<stores>/<school>/evidence.sqlite`; its `hierarchy/<school>/reviewed/*.json` files are only an export.
- Write a decision with `bin/atlas evidence-store record <school> --layer <file.json> --record '<entry>' --source <url|file> --decided-by <your session> ...` (`find` first to see existing rows; `--supersede ID` to correct one), then `bin/atlas evidence-store sync <school>` and commit the regenerated JSON on your branch.
- A direct edit of those JSON files is refused by the pre-commit hook (`evidence_store.py check --staged`), by `evidence_store.py check` and by `atlas doctor` (`evidence_view`). Do not bypass it; do not re-import a flagged school (it would erase recorded decisions).
- The store is not in git; it is backed up daily to `archive/evidence-store-backups/` (restore: `bin/atlas evidence-store restore`).
- Details, the shared-file slices and how a school is switched: `docs/EVIDENCE-STORE.md`.
