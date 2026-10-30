# Contributing: branches, worktrees, merges

Several agents and people work on this repository at the same time. Each of them works on a branch in a separate
worktree, and `main` only moves by fast-forward after a rebase and the full tests.

## Branches and the remote
| Where | Branch | What it holds |
|---|---|---|
| local (`/n/fs/resemble/cs-atlas/work`, after the move `<root>/code`) | `main` | the integrated code; the data next to it is built from it |
| local worktrees | `agent/<name>`, `infra/<topic>`, `fix/<topic>`, `person/<name>` | one line of work each; never pushed |
| remote `origin` = `git@github.com:liv-daliberti/cs-labs-atlas` (public) | `dev` | the development history: local `main`, pushed as `git push origin main:dev` |
| | `main` | the release exports (`code/`, `data/`, `MANIFEST.json`, `CITATION.cff`), written by `tools/export_release.py`. Never force-pushed, never rewritten |
| | tags `release-<id>` | one per release (`releases/<id>`), on the export commit |

The repository is **public**. Everything committed to `main` becomes public at the next push, including the reviewed
inputs that name people and quote web pages. Keys, API caches, the owner's address and its hash never enter a commit:
the secret scan runs in the pre-commit hook, before each push, and in CI.

## Your own worktree
```
tools/agent_worktree.sh new <name> [kind]    # ../work-<name> on branch <kind>/<name> (kind: agent, infra, fix, person)
cd ../work-<name>                            # work and commit here, as often as you like
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
Commits on `main` other than merges go through the hook. For now it **warns**, because agents started before this rule
are still committing on `main`. When they have moved to worktrees, the owner turns enforcement on for every worktree:
```
git config atlas.mainCommits enforce      # refuse direct commits to main (warn is the default)
git config atlas.mainCommits warn         # back to warnings
```
Install the hooks once per clone with `tools/install_hooks.sh`. The installed stub runs `tools/hooks/pre-commit` from
whichever worktree is committing. The hook does three things:
- It warns about, or refuses, a direct commit to main.
- It runs the secret scan on the staged files. A finding blocks the commit.
- It runs ruff on the staged Python files. Syntax errors and undefined names block the commit; the other rules only warn.

## Handing off uncommitted work
Never commit another agent's uncommitted files. To pass work to someone else:
- **Preferred:** commit it on your own branch, even unfinished (`WIP:` in the subject), and name the branch in the
  handoff. The next owner continues on that branch, or rebases onto it.
- **When you can't commit** (you are on main, mid-run): `git diff > <scratch>/handoff-<name>-<date>.patch`, plus a list
  of the untracked files (`git status --porcelain | grep '^??'`), and say in the handoff note where both are. The
  receiver applies them in their own worktree (`git apply`) and commits there. Don't use `git stash` on a shared
  checkout: other agents' changes are in the same working tree.
- Note what is running (job ids, hosts, locks held) and what must not be touched until it finishes.

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
