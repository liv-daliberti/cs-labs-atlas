# Runbook: rebuild, collectors, release, recovery

Read /etc/motd and the host rules first (shared login node: heavy work goes to Slurm, `mltheory`, `--exclude=node302`, explicit
`--mem`, `--time`, `--cpus-per-task`; `sbatch --test-only` before submitting; do not poll the controller: chain jobs with `--dependency=afterok:` and read their output files, or use `atlas pipeline ... --wait` / `atlas release --wait`, which make one `sacct` call per 120 s or more; a manual `squeue`/`sacct` check is never more often than every 120 s).
Set up a shell: `. /n/fs/resemble/homogenizing-science/code/paths.sh` (gives `$CS_ATLAS_PY` and every path).

## Rebuild

1. Everything committed on `main` (a release refuses uncommitted tracked build files). Land branches first
   (`tools/agent_worktree.sh land <name>`; docs/CONTRIBUTING.md).
2. Is a trial worth it? Trial builds never write live data: `PI_HIERARCHY_OUT=<scratch>` (`tools/scratch.py path <name>`).
   Old-vs-new on the same inputs: `OLD=<commit> REPORT=<dir> [SCHOOLS="..."] [VALIDATE=1] sbatch hierarchy/build-equivalence.slurm`
   from the new checkout; the report lists every changed field and the accepted lab-page papers wired or set aside.
3. Full rebuild on Slurm from the code root: `atlas submit --test-only hierarchy/rebuild-all.slurm`, then `atlas submit hierarchy/rebuild-all.slurm`
   (it pins main's HEAD as the job's code, so a landing during the run cannot change it: docs/CONTRIBUTING.md; about 1-2 h; log `hierarchy/logs/rebuild-all-<jobid>.out`). Subset: `STAGES="build audits" SCHOOLS=mit bin/atlas rebuild`.
4. Exit 0 all good; 1 a stage failed (read the log from the first `FAILED`); 2 regression swings blocked the release.
   `hierarchy/BUILD-REGRESSION.md` says which counts moved. If the swing is intended (a rule change, accepted additions), re-run
   the release with `ALLOW_SWINGS=1`; the release records that. If not, find the cause before anything else.
5. `atlas validate` (also a stage): a violation holds the release. Fix the writer, not the schema, unless the schema is wrong
   (`schemas/`, docs/DATA-DICTIONARY.md is generated from them).

## Collectors

- Seven loops, one per school with a store, as one Slurm array (task 0-6, Michigan is 6): `atlas submit fulltext-push/downloads.slurm`
  (from the code root; `--array=N` for one school; pins main's HEAD). `hierarchy/COLLECTORS-STATUS.md` (regenerated after every round) shows each loop's job, phase, last round,
  attempts and downloads in 24 h. Check it before touching anything.
- Stop a loop: `scancel <jobid>` (SIGTERM; the running pass stops cleanly and loses nothing, tried URLs are recorded).
  A loop that idles backs off from 10 minutes to 4 hours by itself.
- **Loops restart themselves** (ROADMAP #18, `fulltext-push/loop_job.sh`): Slurm sends USR1 to the batch script 900 s before the
  3-day limit (`--signal=B:USR1@900`); the script stops the loop with TERM (lock released, pass stopped cleanly), then runs
  `atlas submit --test-only` and, unless it prints `Preempts:`, `atlas submit fulltext-push/downloads.slurm --array=<n>`, which
  pins main's HEAD at that moment. The line `{"loop_job": ...}` in `<store>/loop.log`/`lab_first_loop-<school>.out` says what
  happened; a refused or failed resubmit leaves the loop down (the status page alarm). `scancel` (TERM) stops for good: no resubmit.
  Michigan's collector job restarts as `downloads.slurm --array=6`, the loop alone. Proof: `tests/test_loop_job.py`.
- A second loop for the same store exits at once (`<store>/.loop.lock`); `flock -n <store>/.loop.lock true` tells whether it is free.
- Never run a writer that does not take the catalog lock (Princeton importer, vendored Infoscience/DSpace resolvers) while that
  store's loop runs (docs/STORES.md). Do not `du` or walk `stores/`; use `df`.
- Failed attempts: diagnose from the catalog's attempts table and `loop.log`; `fulltext-push/requeue_causes.py` requeues by cause
  and logs every row it deletes under `staged/`.

## Pipelines (the mechanical chains)

`atlas pipeline --list` shows them. `atlas pipeline copies` runs lab_paper_copies per school (a Slurm array), then the unavailability ledger, the coverage recount and
the collectors status page; `atlas pipeline labpage` runs the lab-page audit per school, restamps the acceptance files and writes the summary; `atlas pipeline reader`
the reader export. Each stage is submitted `afterok` the one before, from a code snapshot of main's HEAD, so nothing is polled and nothing is typed between stages;
`--test-only` checks the first stage, `--wait` blocks until the chain ends with one `sacct` call per 120 s or more (tools/slurm_wait.py; it stops at the first failed job) and prints the states, `atlas pipeline status` shows a run. A new chain is a new entry
in `PIPELINES` in tools/atlas_pipeline.py. The hand checks, the design and the diagnosis of a failed stage stay with the agent.

## Release

`atlas release` runs the whole chain and stops at the first failure: preflight, rebuild, validate, regression, reader export, release (with the generated
CHANGES.md), notes check, organized tree, GitHub export (written and committed locally), then the two steps that publish outside this host, `export-push`
(tag `release-<id>` and push) and `hf-upload`, and last the Codex handoff note (SITE-HANDOFF.md, added to the release). The two external steps need
`--yes-push` / `--yes-hf` (or a "y" at the terminal); without them the run stops with exit status 3 and `--resume` continues after you confirm. As a job:
`atlas release --wait` (submits that job from main's HEAD and blocks on it with one `sacct` call per 120 s or more) or `atlas submit hierarchy/release.slurm` (`RELEASE_ARGS="--yes-push --yes-hf"` in the environment to confirm in advance). `atlas release --dry-run` prints the steps.
A release is `releases/<date>[.N]/`, read-only, with `MANIFEST.json` (hashes, code commit, rules, counts, regression, ledger, ids, reader) and `CHANGES.md`;
`releases/latest` points at the newest. Releases are never overwritten or edited; notes are added only with `make_release.py add-note` (`atlas make-release`
cuts just the release). Agents do not push; the coordinator confirms the external steps.

## Recovery

| what went wrong | what to do |
|---|---|
| A rebuild wrote bad packages | the previous packages are in the last release (`releases/<id>/hierarchy/<school>/`, read-only) and in the rebuild's snapshot `scratch/pkg-before-<tag>/` (kept for the newest two rebuilds). Copy back the five package files, never into a release. Then find why: `hierarchy/BUILD-REGRESSION.md` |
| A reviewed input was changed badly | it is in git: `git log -p -- hierarchy/<school>/<file>`; revert on a branch and land it |
| A bulk change to a store catalog | `stores/<school>/backups/catalog.<reason>-<date>.sqlite` (latest two kept) and the append-only logs under `staged/` (requeued, reverted, restored rows); quarantined files are renamed, never deleted (`quarantine/*/manifest.jsonl`) |
| A branch landed something wrong on `main` | `git revert` it on a branch and land the revert; `main` only moves by fast-forward, no force |
| A loop died or the host rebooted | `squeue -u $USER`; resubmit only the missing array task(s) of `downloads.slurm` (`--array=<n>`) after checking `COLLECTORS-STATUS.md` and the lock |
| The build is not deterministic between two runs | the builder's output depends on str hash order in places; compare with the same `PYTHONHASHSEED` (the equivalence job fixes it to 0) |
| Ids changed | they must not: `hierarchy/ids/registry.sqlite` travels with every release; restore it from the last release (docs/IDS.md) |
| Moved files, old paths | `archive/migrations/*.jsonl` records every move of the project relocation; `tools/relocate_project.py` and `tools/relocate_data.py` are dry runs by default |

## Starting or restarting an agent (leases and the restart checklist; ROADMAP #17, #40)

Every agent holds one lease while it works (`atlas lease`, tools/agent_lease.py; files in `<root>/leases/`). A second copy of the same agent refuses to start
while the lease is live, so a restarted session cannot run beside a forgotten one. In this order:
1. `atlas lease status`: is the agent's lease live? A live lease of another session means that session is still working: stop and ask the coordinator.
   An expired lease (renewed more than 30 min ago) is free.
2. `atlas lease acquire <name> --note "<what I am doing>"` (exit 3 = refused). Renew on every report: `atlas lease renew <name> --note "<step>"`.
3. Read the hand-off: `docs/ROADMAP.md` for your rows, the memory index, and the last report.
4. Find your own state, not someone else's: `tools/agent_worktree.sh ls` (your worktree and branch, with uncommitted changes), `git -C <worktree> status`, `squeue -u $USER`
   (your jobs and the download loops; never cancel what is not yours) and `hierarchy/COLLECTORS-STATUS.md`.
5. Work in your worktree, land with `tools/agent_worktree.sh land <name>`; submit jobs with `atlas submit` / `atlas pipeline`; never commit on main (enforce is on).
6. At a clean stop, hand the work over (a note, branch names, job ids) and `atlas lease release <name>`. A crashed agent needs nothing: its lease expires.

## Housekeeping

`tools/scratch.py clean` (dry run) / `--apply` removes scratch entries, old rebuild snapshots and old `.equiv/` reports older than 14
days; the rebuild runs it as its last stage. Keep a scratch directory by putting a file `KEEP` in it. Disk: `df -h /n/fs/resemble`
for quota; never traverse `/n/fs` or `du` the stores.
