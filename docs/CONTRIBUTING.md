# Contributing: branches, worktrees, merges

Several agents and people work on this repository at the same time. Each of them works on a branch in a separate
worktree, and `main` only moves by fast-forward after a rebase and the full tests.

## Branches and the remote
| Where | Branch | What it holds |
|---|---|---|
| local (`/n/fs/resemble/homogenizing-science/code`, after the move `<root>/code`) | `main` | the integrated code; the data next to it is built from it |
| local worktrees | `agent/<name>`, `infra/<topic>`, `fix/<topic>`, `person/<name>` | one line of work each; never pushed |
| remote `origin` = `git@github.com:liv-daliberti/cs-labs-atlas` (public) | `dev` | the development history: local `main`, pushed as `git push origin main:dev` |
| | `main` | the release exports (`code/`, `data/`, `MANIFEST.json`, `CITATION.cff`), written by `tools/export_release.py`. Never force-pushed, never rewritten |
| | tags `release-<id>` | one per release (`releases/<id>`), on the export commit |

The repository is **public**. Everything committed to `main` becomes public at the next push, including the reviewed
inputs that name people and quote web pages. Keys, API caches, the owner's address and its hash never enter a commit:
the secret scan runs in the pre-commit hook, before each push, and in CI.

## Your own worktree
```
tools/agent_worktree.sh new <name> [kind]    # ../worktrees/<name> on branch <kind>/<name> (kind: agent, infra, fix, person)
cd ../worktrees/<name>                       # work and commit here, as often as you like
tools/agent_worktree.sh land <name>          # rebase on main, full tests, fast-forward main
tools/agent_worktree.sh rm <name>            # when done (refuses while there are uncommitted changes)
```
A worktree has the code only. The data (packages, stores, captures, logs) stays in the main checkout, and every data
path comes from `tools/atlas_paths.py`, which points at it. Code paths come from your worktree: run
`bin/atlas <command>` or `$CS_ATLAS_PY tools/...` from it. When a test or a trial build must not touch the shared data,
send its outputs elsewhere: `PI_HIERARCHY_OUT=<scratch>`, `CS_ATLAS_HIERARCHY=<scratch>/hierarchy`, ... For code you
changed under `vendor/`, set `CS_ATLAS_VENDOR=$PWD/vendor`.

## Landing work on main
1. Commit on your branch. Each commit is one logical change. Mechanical changes (formatting, ruff `--fix`) get their own
   commit. Commit messages say what changed and why.
2. `git rebase main`, then run the full suite: `bin/atlas test` (it includes the `nfs` tests that need the data;
   CI runs the rest), `bin/atlas lint`, `bin/atlas charters`, and `bin/atlas vendor check` if you touched `vendor/`.
3. Fast-forward: `git -C <main checkout> merge --ff-only <branch>` (`tools/agent_worktree.sh land` does steps 2-3). If
   `main` moved meanwhile, or the main checkout has someone's uncommitted changes in the same files, the merge refuses:
   rebase again and retry. Never leave `main` with failing tests.
4. Push (after the tests and the scan): `git -C <main checkout> push origin main:dev`. The gates before a push are
   `bin/atlas scan --history origin/dev..main` (what the push adds) and the test suite. No force pushes.

## No direct commits to main
Commits on `main` other than merges go through the hook. The owner turns enforcement on for the whole repository (every worktree shares the setting):
```
git config atlas.mainCommits enforce      # refuse direct commits to main (the default is warn)
git config atlas.mainCommits warn         # back to warnings
```
Install the hooks once per clone with `tools/install_hooks.sh`. The installed stub runs `tools/hooks/pre-commit` from whichever worktree is committing.
The hook does three things:
- It warns about, or (enforce) refuses, a direct commit to main. `ATLAS_ALLOW_MAIN=1` is for the one sanctioned case, `relocate_data.py --apply`'s commit.
- It runs the secret scan on the staged files. A finding blocks the commit.
- It runs ruff on the staged Python files. Syntax errors and undefined names block the commit; the other rules only warn.

Slurm jobs go the same way: submit with `atlas submit [sbatch options] script.slurm`, and every `.slurm` script sources the code-snapshot helper
(`tests/test_slurm_snapshot.py` fails CI on a script that does not; the ML studies in `ai-writing/` and `archive/` are exempt).

## Handing off uncommitted work
Never commit another agent's uncommitted files. To pass work to someone else:
- **Preferred:** commit it on your own branch, even unfinished (`WIP:` in the subject), and name the branch in the
  handoff. The next owner continues on that branch, or rebases onto it.
- **When you can't commit** (you are on main, mid-run): `git diff > <scratch>/handoff-<name>-<date>.patch`, plus a list
  of the untracked files (`git status --porcelain | grep '^??'`), and say in the handoff note where both are. The
  receiver applies them in their own worktree (`git apply`) and commits there. Don't use `git stash` on a shared
  checkout: other agents' changes are in the same working tree.
- Note what is running (job ids, hosts, locks held) and what must not be touched until it finishes.

## Slurm jobs run from a code snapshot
A landing is a fast-forward that rewrites many files in the main checkout. A job that imports code from that checkout while
it happens can see half a commit (2026-10-31: `atlas_paths has no LOCKS`, then `no RATE_STAMPS`, in lab-page jobs). So a job
runs the code of **one commit**, extracted from git into job-local scratch, and reads and writes the data in the main checkout:
```
. "$CS_ATLAS_CODE/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1      # git archive <commit> -> $TMPDIR/atlas-code-<user>-<jobid>
cd "$CS_ATLAS_CODE"                                          # the data
$CS_ATLAS_PY -u "$CS_ATLAS_TOOLS/some_tool.py" ...           # the code: "$CS_ATLAS_TOOLS/x.py", never "tools/x.py"
```
- `git archive` reads the object store, so the snapshot is exact whatever happens to the working tree. The helper points
  `CS_ATLAS_TOOLS`, `TESTS`, `VENDOR`, `SCHOOL_CONFIGS`, `FULLTEXT_PUSH` and `AI_WRITING` at it; `CS_ATLAS_CODE` and every data
  slot keep pointing at the main checkout through atlas_paths. The snapshot is removed on exit (an `EXIT` trap, installed only
  when the script has none; otherwise call `snapshot_remove` from yours, or set `SNAPSHOT_DIR` and remove it yourself).
- **Which commit:** `CS_ATLAS_SNAPSHOT_COMMIT`, else main's HEAD when the job starts. Submit with `atlas submit [sbatch options] script.slurm`
  to pin main's HEAD **at submit time** (it is `sbatch --export=ALL,CS_ATLAS_SNAPSHOT_COMMIT=<sha>`). The commit is printed
  in the job log (`code snapshot: commit ...`) and `tools/provenance.py` records it as `report.json` provenance `code.commit`
  (`snapshot: true`, plus `live_head` when main had moved on).
- Run the *script* from the snapshot too when it is long: `hierarchy/rebuild.sh` extracts a snapshot and re-runs its own
  copy from it. Slurm already copies the batch script itself at submit.
- Data is not snapshotted. Reviewed inputs and packages are read live, so a landing that changes them mid-run still shows;
  land inputs between jobs. `SNAPSHOT_REPO=<worktree>` takes the code from a branch under test (`hierarchy/build-equivalence.slurm`
  does, for the new side; commit first: uncommitted changes are not in the snapshot).
- `fulltext-push/` modules keep their caches, logs, locks and the OpenAlex budget log next to the code (`raw/`, `checks/`, `logs/`,
  `review-*/`). Its jobs (`ledger`, `recover-1030`, `channels-1030`, `michigan-collector`, `downloads`) therefore source
  `fulltext-push/job_snapshot.sh`, which takes the snapshot and links every untracked entry of the main `fulltext-push/` into it.
  The loops adopt it at their next restart.
- The collectors' own data (`fulltext-push/raw`, `checks`, `logs`, `local-reuse` data, `review-<stamp>`) is reached through the
  slots `FT_RAW`, `FT_CHECKS`, `FT_LOGS`, `FT_LOCAL_REUSE` and `ft_review()` (shell `$CS_ATLAS_FT_*`), which point at the main
  checkout; `tools/route_ft_data.py` and a test fail on a hand-joined path. Download loops already running keep the code they
  loaded (hand-joined paths included) until they restart; they write the same directories, so nothing moves.
- Adopted by `hierarchy/rebuild.sh`, `rebuild-all.slurm`, `organize-tree.slurm` and `build-equivalence.slurm`. Other
  scripts: source the helper after `paths.sh` and replace `tools/` in the command lines.

## Checks run by CI (`.github/workflows/ci.yml`, on pushes and pull requests to `dev` and `main`)
- The env is built from `env/conda-linux-64.lock`.
- `ruff check .`
- `pytest -m "not nfs"`: fixture-only tests. Tests that need the NFS data carry `@pytest.mark.nfs`.
- `school_config.py --check` over every charter.
- `vendor_sync.py check --no-sources`
- `route_paths.py check`: no hardcoded project paths in code.
- The secret scan over the pushed commits.

On the export branch (`main` on the remote) the job finds no env lock and does nothing.

## Proposal (not done): `dev` as the default branch
Today the remote's `main` holds the release exports, and its history went public first. Once `dev` has a clean
history and CI is green, the proposal is:
- make `dev` the default branch, renamed to `main` at a convenient point;
- move the exports out of the branch history, either under a `releases/<id>/` path written by
  `tools/export_release.py` on that branch, or (lighter) as an orphan branch `exports` plus a tag `release-<id>` per
  release, with release assets attached on GitHub.

People who clone the repository would then get the code first. Each release stays immutable and addressable by its tag.
The owner decides. Nothing has been changed.
