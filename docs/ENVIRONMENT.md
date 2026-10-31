# The Python environment, the entry point, and the switch-over

## One environment
| | |
|---|---|
| Path | `/n/fs/resemble/homogenizing-science/env/atlas` (= `$CS_ATLAS_ENV/atlas`, `atlas_paths.PY`) |
| Python | 3.12 (conda-forge only) |
| Spec | `env/environment.yml`: the pipeline (requests, beautifulsoup4, lxml, protego, rapidfuzz, pymupdf, numpy, huggingface_hub, poppler for `pdftotext`/`pdfinfo`) and the tools (pytest, ruff) |
| Lock | `env/conda-linux-64.lock`: conda's explicit spec (`conda list --explicit --md5`), every package by URL and md5. A rebuild installs the same files without solving. Verified 2026-10-30: a rebuild from the lock gives the identical package set |
| Build | `env/build_env.sh` (from the lock); `env/build_env.sh --solve` re-solves `environment.yml` and rewrites the lock (commit both). An env is never edited in place: build a new prefix and swap |
| Package | `pyproject.toml` (metadata, ruff, pytest, the `[studies]` and `[dev]` extras); the build installs the repo editable (`pip install --no-deps -e <code>`), which puts `atlas` on the env's `bin/` |

Use it without activating anything (the conda env needs no `LD_LIBRARY_PATH`):
```
. /n/fs/resemble/homogenizing-science/code/paths.sh      # (after the move: <root>/code/paths.sh)
$CS_ATLAS_PY tools/pi_hierarchy.py michigan   # any tool
bin/atlas test                               # the dispatcher, from this checkout (a worktree runs its own code)
```
or put it on PATH: `export PATH=$CS_ATLAS_ENV/atlas/bin:$PATH` (then `atlas ...`, `python`, `pytest`, `ruff`).
`conda activate /n/fs/resemble/homogenizing-science/env/atlas` also works after `module load anaconda3/2026.07`.

One interpreter is defined in one place: `PY` in `tools/atlas_paths.py`, exported as `$CS_ATLAS_PY` by `paths.sh`.
`hierarchy/rebuild.sh`, the `*.slurm` scripts and the tools use it. Two others remain, also defined there:
- `COLLECTOR_PY`: what the download loops run. It stays the old Anaconda Python
  (`/usr/local/anaconda3/2024.02/bin/python -I`) until the loops are switched over (below), then it becomes `PY`.
- `ENV_PY`/`ENV_LIB`: the old py310 env (`/n/fs/resemble/cs-atlas-env/py310`, needs `LD_LIBRARY_PATH=$CS_ATLAS_ENV_LIB`).
  It is kept only for the ML studies in `ai-writing/` (torch, transformers, vllm; SPECTER2 / Pythia). They are the
  `[studies]` extra in `pyproject.toml`. To retire py310, build a second env, `env/atlas-studies`, from a conda-forge
  pytorch-cuda spec plus `pip install -e .[studies]`, lock it the same way, and point `ENV_PY` at it.

## Third-party imports (inventory, 2026-10-30, including vendor/)
| Need | Packages | Where |
|---|---|---|
| pipeline | requests | 45 files (collectors, census, channels, recovery tools), vendor/ |
| | beautifulsoup4 (+ lxml parser) | 34 files (hierarchy tools, census), vendor/ |
| | protego | the collector, lab_channels |
| | rapidfuzz | fulltext-push/review_identity.py |
| | pymupdf (`fitz`) | fulltext-push/local-reuse/identify.py |
| | numpy | tools/dblp_dump_index.py, vendor homog.py |
| | huggingface_hub | tools/hf_upload_release.py |
| | tomllib (stdlib on 3.11+; `tomli` on the 3.10 env) | tools/school_config.py |
| | poppler (`pdftotext`, `pdfinfo` executables) | the collector, fulltext_store |
| tests / lint | pytest, ruff | tests/, CI, the hook |
| studies only | torch, transformers, vllm, scikit-learn, scipy, pandas, pyarrow, matplotlib, pillow, joblib, pymupdf | ai-writing/ only |

## `atlas <command>`
A thin dispatcher (`atlas_cli/`) over the existing tools. Each command runs a script that also works on its own.
`atlas help` lists them: `build <school>`, `rebuild`, `ids`, `copies <school>`, `ledger <school>`, `audit`, `evidence`,
`regression`, `release`, `tree`, `export`, `stage-gate <school>`, `charters`, `collect <school>`, `test [--ci]`, `lint`,
`scan`, `vendor`, `paths`, `relocate`, `run <script>`.

## Proof (2026-10-30, under the new env)
- The full test suite passes under `env/atlas`, and still passes under py310.
- A Michigan-only build in a scratch copy (see the infra report in the commit log): `tools/pi_hierarchy.py michigan`,
  with the overrides `CS_ATLAS_HIERARCHY=<scratch>/hierarchy` (a copy of the reviewed inputs and the Michigan package
  inputs) and `CS_ATLAS_VENDOR=<worktree>/vendor`.

## Switching the collectors over (the download loops on rinse)
Today six loops (`fulltext-push/lab_first_loop.py <school>`) run on host `rinse` under the old Anaconda Python. Each
round they start the collector from its old path (`.research-sweeps/claude-cmu-20261017/tools/collector_wrapper.py`,
which runs `homogenizing-science/scripts/collect_princeton_fulltext_expanded.py`). Code merged to main changes nothing
for a running loop: Python loaded `lab_first_loop.py` when the loop started. A loop picks up the vendored collector
(`vendor/cmu_tools/collector_wrapper.py`, cwd `vendor/homogenizing_scripts/`) the next time it is started. The
interpreter stays `COLLECTOR_PY` until step 4 below.

1. **Drift check.** On main: `bin/atlas vendor check` must report 0 mismatches and 0 drifted sources. On drift: review
   the original's change, `bin/atlas vendor sync`, test, commit.
2. **Stop a loop between passes** (on rinse). `<store>/loop-state.json` gives the phase and `child_pid`. Stop the loop
   process first (SIGTERM), then the child collector (SIGTERM to `child_pid`). A stopped pass loses nothing: tried URLs
   are recorded per work. Check that `<store>/.loop.lock` is free (`flock -n <store>/.loop.lock true`).
3. **Restart on the vendored code, same interpreter**, from the code root: `sbatch fulltext-push/downloads.slurm`
   (one array task per school; Slurm scripts are submitted from the code root), or on rinse
   `cd <code> && nohup bin/atlas collect <school> --recent-first 2023 >> fulltext-push/logs/lab_first_loop-<school>.out 2>&1 &`.
   Check: `ps -o args` shows `.../vendor/cmu_tools/collector_wrapper.py`, and `loop.log` shows a `lab_*` phase starting.
4. **New interpreter.** Try one school first: `export CS_ATLAS_COLLECTOR_PY=$CS_ATLAS_PY` before step 3, and watch
   one full round (`loop.log`, `attempts` growing, no import errors). Then make it the default for everyone: in
   `tools/atlas_paths.py`, change `('COLLECTOR_PY', '/usr/local/anaconda3/2024.02/bin/python', None)` to
   `('COLLECTOR_PY', 'atlas/bin/python', 'ENV')`, regenerate `paths.sh` (`$CS_ATLAS_PY tools/atlas_paths.py --sh > paths.sh`),
   test, commit, and restart the remaining loops.
5. **Retire** once all six run on `vendor/` with the new env for a full round. The originals listed in
   `vendor/PROVENANCE.tsv` are no longer read by any code and can go to `archive/` with the project move. Stop using
   the old Anaconda Python. py310 stays until a studies env exists.

## What still lives outside the repository
Data only; no code path the build or the collectors run points outside the repository except these data reads, all
through `atlas_paths`:
- `archive_sweep(<stage>)`: the DBLP publication lists (`raw/dblp_pubs.json.gz`, pi_hierarchy, dblp_recover,
  missing_papers_audit), the EPFL/CMU/MIT/Berkeley people and roster captures (faculty_periods, epfl_census,
  epfl_profiles, berkeley_census, berkeley_pubs, princeton_census), the arXiv OAI index (labpage_recover), the Princeton
  listings capture, and the Princeton OAR / NSF-PAR / proceedings indexes (repo_index, nsf_par_lab, lab_channels).
  The vendored modules' own stage data (S2/arXiv caches, discovery packages) is reached the same way.
- `SITE_DATA`: the site collections `collection-<school>.json.gz` (pi_hierarchy, faculty_periods, provenance,
  make_release, census builders). After the move this is `archive/site-history/princeton-live-20261015`. It should
  become a project input (for example `external/site-collections/`) so that nothing in `code/` reads `archive/`.
- `tools/export_release.py` copies the site build's scripts (`SITE_SCRIPTS`) into the export as a record. That is a
  data copy, not an import.
