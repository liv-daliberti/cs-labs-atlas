# CS Labs Atlas: the code repository

The code repository (`/n/fs/resemble/cs-atlas/work`; after the project move `homogenizing-science/code`) is a git repository (branch `main`) since 2026-10-29. It holds the code, the docs and the
reviewed inputs; everything else in `work/` (packages, sweeps, captures, logs, PDFs, sqlite) is data and stays out of git
(`.gitignore` is a whitelist). Data leaves the working root only through a dated release.

## Layout
| Path | What |
|---|---|
| `tools/` | the builder (`pi_hierarchy.py`), the audits (`student_audit.py`, `chain_audit.py`, `link_diagnosis.py`), `build_regression.py`, `make_release.py`, `organize_tree.py`, `export_release.py`, `lab_paper_copies.py`, census and recovery tools, `atlas_paths.py`, `secret_scan.py` |
| `tools/atlas_paths.py`, `paths.sh` | every path in one place (Python, and generated for shell: `python tools/atlas_paths.py --sh > paths.sh`) |
| `hierarchy/rebuild.sh`, `hierarchy/rebuild-all.slurm` | the full rebuild (local / Slurm) |
| `fulltext-push/` | the full-text collectors (run on `COLLECTOR_PY -I`; docs/ENVIRONMENT.md) |
| `vendor/` | code copied in from the old working folders, with provenance (vendor/README.md) |
| `atlas_cli/`, `bin/atlas`, `pyproject.toml`, `env/` | the entry point, the package metadata and the pinned environment |
| `tests/` | pytest; real-case fixtures for the build rules |
| `docs/RULES.md` | every build rule with its date and id |
| `docs/REVIEWED-INPUTS.md` | the hand-curated decision files the build reads |

## Run
The project interpreter is `env/atlas` (Python 3.12, built from `env/conda-linux-64.lock`; docs/ENVIRONMENT.md).
Everything is reachable through one entry point, `bin/atlas <command>` (or `atlas` with the env's `bin/` on PATH):
```
bin/atlas help                               # the commands
bin/atlas test                               # the tests (seconds); --ci skips the ones that need the NFS data
bin/atlas build michigan                     # one school's packages (tools/pi_hierarchy.py)
STAGES="build audits" SCHOOLS=mit bin/atlas rebuild     # hierarchy/rebuild.sh: snapshot, build, audits, tests,
                                             # regression, copies, release, tree (~1 h; one heavy builder at a time)
bin/atlas export /n/fs/resemble/cs-labs-atlas --skip-atlas   # the GitHub export from releases/latest
```
Shell and Slurm scripts take every path and the interpreter from `paths.sh` (`$CS_ATLAS_PY`, `$CS_ATLAS_HIERARCHY`, ...);
submit Slurm scripts from the code root (`sbatch hierarchy/rebuild-all.slurm`): their logs are written relative to it.
A release (`releases/<date>[.N]/`, `releases/latest`) is made only when the build, the audits and the tests pass, the
code is committed, and `hierarchy/BUILD-REGRESSION.md` flags nothing (or `ALLOW_SWINGS=1`). Everything downstream reads
a release: the organized tree (`schools/`, `school.json` names the release), the GitHub export (`MANIFEST.json`
`export.release`, `export.code.commit`), the site and the Hugging Face dataset.

## Paths and the project root
Every location comes from `tools/atlas_paths.py`, derived from one root, `/n/fs/resemble/homogenizing-science`.
`LAYOUT_DEFAULT` says whether the directories are still at their old places (`legacy`) or have moved
(`project`: `code/ releases/ schools/ stores/ studies/ figures/ site/ export/ env/ cache/ external/ archive/
world-atlas/`). The move is `tools/relocate_project.py` (dry run by default), then that one line. No code file may
contain an absolute project path: `tools/route_paths.py check` (in CI) finds them, and `route_paths.py fix` rewrites them
through atlas_paths. Code the pipeline used to import from old working folders is in `vendor/` (vendor/README.md).

## Branches, commits, the remote
Work on a branch in your own worktree (`tools/agent_worktree.sh new <name>`), rebase, run the full tests, and
fast-forward `main`: docs/CONTRIBUTING.md. The remote is the public repository
`git@github.com:liv-daliberti/cs-labs-atlas`: `dev` is the development history (local `main`, pushed with
`git push origin main:dev` after the tests and the scan), `main` holds the release exports, and releases are tagged
`release-<id>`. Install the hooks once (`tools/install_hooks.sh`): secret scan and ruff on staged files, and a warning
on direct commits to main. Commit before a release: `make_release.py` refuses uncommitted changes to tracked files.
