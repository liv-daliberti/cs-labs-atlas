# CS Labs Atlas: the code repository

`/n/fs/resemble/cs-atlas/work` is a git repository (branch `main`) since 2026-10-29. It holds the code, the docs and the
reviewed inputs; everything else in `work/` (packages, sweeps, captures, logs, PDFs, sqlite) is data and stays out of git
(`.gitignore` is a whitelist). Data leaves the working root only through a dated release.

## Layout
| Path | What |
|---|---|
| `tools/` | the builder (`pi_hierarchy.py`), the audits (`student_audit.py`, `chain_audit.py`, `link_diagnosis.py`), `build_regression.py`, `make_release.py`, `organize_tree.py`, `export_release.py`, `lab_paper_copies.py`, census and recovery tools, `atlas_paths.py`, `secret_scan.py` |
| `tools/atlas_paths.py`, `paths.sh` | every path in one place (Python, and generated for shell: `python tools/atlas_paths.py --sh > paths.sh`) |
| `hierarchy/rebuild.sh`, `hierarchy/rebuild-all.slurm` | the full rebuild (local / Slurm) |
| `fulltext-push/` | the full-text collectors (run on `/usr/local/anaconda3/2024.02/bin/python -I`) |
| `tests/` | pytest; real-case fixtures for the build rules |
| `docs/RULES.md` | every build rule with its date and id |
| `docs/REVIEWED-INPUTS.md` | the hand-curated decision files the build reads |

## Run
```
export LD_LIBRARY_PATH=/n/fs/resemble/cs-atlas-env/py310/lib
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python
$PY -m pytest tests -q                      # the tests (seconds)
nohup hierarchy/rebuild.sh > hierarchy/logs/rebuild-$(date +%Y%m%d-%H%M).out 2>&1 &   # snapshot, build, audits, tests,
                                            # regression, copies, release, tree (~1 h; one heavy builder at a time)
$PY tools/export_release.py /n/fs/resemble/cs-labs-atlas --skip-atlas   # the GitHub export from releases/latest
```
A release (`/n/fs/resemble/cs-atlas/releases/<date>[.N]/`, `releases/latest`) is made only when the build, the audits
and the tests pass, the code is committed, and `hierarchy/BUILD-REGRESSION.md` flags nothing (or `ALLOW_SWINGS=1`).
Everything downstream reads a release: the organized tree (`/n/fs/resemble/cs-atlas/schools/`, `school.json` names the
release), the GitHub export (`MANIFEST.json` `export.release`, `export.code.commit`), the site (point the site
builder's `H` at `<release>/hierarchy`) and the Hugging Face dataset (`releases/<id>/`).

## Commits
Commit before a release: `make_release.py` refuses uncommitted changes to tracked files. Scan before committing:
`$PY tools/secret_scan.py --staged`. The repository has no remote yet; to add one (a private repository is advised:
the reviewed inputs quote web pages and name people):
```
git remote add origin [email removed]:<owner>/<repo>.git
git push -u origin main
```
