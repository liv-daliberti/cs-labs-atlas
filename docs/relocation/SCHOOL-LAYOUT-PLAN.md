# School layout plan (owner decision 2026-11-26): each school's data under `<ROOT>/schools/<school>/`

**Status: prepared, nothing moved.** The code (`tools/atlas_paths.py` third placement, `tools/relocate_schools.py`) is on branch
`infra/school-layout-1126`; the live code is routed through atlas_paths on `infra/school-paths-1126` (section "Code routing" below). The dry run is `docs/relocation/school-layout-dryrun-1126.txt` (regenerate: `python tools/relocate_schools.py --references`).

## Selecting the placement
`CS_ATLAS_DATA_LAYOUT=school` (beside `flat` and `split`) selects it per process; `DATA_LAYOUT_DEFAULT` stays `'split'`, so today's behaviour is identical.
`data()/data_w()/store()` keep their signatures. New helpers: `school_dir(school, part)`, `checks_db(school)`, `ai_dir(school, model)`; new slot `SLURM_LOGS` (`<ROOT>/logs/slurm`).
`flat_of()` reads school paths back to the flat names, so releases keep their layout. The `layout` test fixture runs in flat, split and school.

## Mapping (per school key `<s>`; `H` = `<ROOT>/code/hierarchy/<s>`, `T` = `<ROOT>/schools/<s>`)
| today | after | note |
|---|---|---|
| `H/derived`, `H/raw`, `H/work`, `H/reports`, `H/tmp` | `T/derived`, `T/raw`, `T/work`, `T/reports`, `T/tmp` | a directory holding git-tracked files moves child by child; the tracked children stay in git |
| `H/inputs-manifest.sha256.json` | `T/derived/` | `tools/input_manifest.py` hand-joins its path |
| `H/reviewed` (tracked) | stays; `T/reviewed` is a link to it | **the one permanent link, needs owner sign-off** |
| `H/STAGE-*.md`, `PROVENANCE.md`, `STAGE-0.md`, tracked `reports/*`, `derived/report.md` | stay in git | listed in section 4 of the dry run |
| `listings/<s>/` | `T/listings/{raw,derived}` | |
| `stores/<s>/` (catalog.sqlite, objects/) | `T/store/` | `.loop.lock` of 35 stores is held by the download loops |
| `fulltext-push/checks/<s>.sqlite` (+`-wal/-shm`) | `T/checks/<s>.sqlite` | `atlas_paths.checks_db(s)` |
| `captures/<s>.sqlite` | `T/raw/school-captures.sqlite` | today every one of the 5 is a 0-byte pre-split leftover beside the live copy in `H/raw/`: removal, owner approval |
| `hierarchy/derived/reader/<s>.jsonl.gz`, `derived/link-sweep/<s>.json`, `hierarchy/listings-input-<s>.json` (tracked: `git mv`), `sweep-<s>.log` | `T/derived/reader.jsonl.gz`, `T/derived/link-sweep.json`, `H/reviewed/listings-input.json`, `T/work/sweep.log` | |
| `census/<s>-*`, `periods/<s>-*` | `T/derived` / `T/reviewed` | no such files exist today (the split layout already put them in `H/`) |
| `ai-writing/data/embeddings/<model>/<s>` | `T/ai/embeddings/<model>` | `--no-ai` leaves them out; `ai-scores` is one sqlite/parquet, not per school: stays |
| `T/labs`, `T/school.json` | unchanged | organize_tree's view (6 schools today, the plan makes the other 34 directories) |
Stays outside for every school: `releases/<id>/` (immutable dated snapshots), `export/`, the charter `code/schools/<s>.toml`, site and world-atlas builds.

## Project-root tidy-up (dry-run sections 2, 6-8)
1. 97 stray `slurm-*.out` at `<ROOT>` (all 2026-11-11, one burst, jobs 32206731-32209913) plus 55 in `<ROOT>/code` (git-ignored) and `hierarchy/logs/rebuild-all-32226451.out` move to `SLURM_LOGS`.
   Scripts with no `#SBATCH --output` (they write `slurm-%j.out` into the submit directory): `hierarchy/{alias-apply,build-equivalence,build-school,layout-equivalence,merge-equivalence,pipeline-stage}.slurm`, `ai-writing/dose/dose_v3.slurm`.
   Fix (not applied, outside this task's scope): `#SBATCH --output=${CS_ATLAS_SLURM_LOGS}...` cannot expand variables, so set `SBATCH_OUTPUT=$CS_ATLAS_SLURM_LOGS/%x-%j.out` in `atlas submit` (`atlas_cli/__init__.py`); `#SBATCH` lines still win.
2. `site-interim-1120`, `site-publish-1115`, `site-visibility-1118` are registered git worktrees of `site/` (`.git` files point into `site/.git/worktrees/`): move with `git -C site worktree move <old> site-worktrees/<name>`, never a plain rename. The worktree list also holds a prunable record (`/tmp/atlas-site-update-1115`).
3. Remove with owner approval (never done by the tool): empty `x/`, empty `site-host-update-1115/`, `hierarchy/` (after its log moves), `.pytest_cache/`, stale 0-byte `.queue.lock`, the 5 empty `code/captures/*.sqlite`. Also 12 junk directories in `code/hierarchy/` named like CLI flags (`-c`, `--help`, `-rf`, ...).
4. Not a documented slot: `worktrees/` and `site-worktrees/` (keep; add `WORKTREES` and `SITE_WORKTREES` slots), the rest are items above.

## Cutover steps
1. **Quiesce:** the 40-school rebuild (job 32579326) done; agents landed and their worktrees idle; Codex download loops paused (35 `.loop.lock` files must be free); `squeue -u $USER` shows nothing that reads these paths; `fulltext-push` ledger writers stopped (the `checks` sqlite files have WAL companions).
2. **Snapshot** all 40 schools' gates (`atlas stage-gate <s> --traps` outputs and `report.json` counts) to `scratch/` for the comparison.
3. Owner decisions below, then `git rm --cached` of whatever the owner declares generated.
4. **Dry run again** (`tools/relocate_schools.py`): zero conflicts, zero busy, no held lock.
5. **Apply** `tools/relocate_schools.py --apply --compat-links` (records to `archive/migrations/school-layout-<date>.jsonl`; `relocate_project.py --remove-compat` removes the links later). Then the root moves: `git -C site worktree move`, slurm outputs (in the same apply).
6. **Flip:** `DATA_LAYOUT_DEFAULT = 'school'`, `python tools/atlas_paths.py --sh > paths.sh`, commit with the `listings-input` renames.
7. **Re-measure** all 40 schools' gates and compare with the step-2 snapshot; run the full tests (`bin/atlas test`, `lint`, `charters`).
8. Later: `relocate_project.py --remove-compat`; route the hand-joins listed in section 12 of the dry run (they keep working through the compat links until then).

## Rollback
Before step 6: `os.rename` every recorded move back in reverse order (the record has old and new), remove the link, `git mv` back. After step 6: set the default back to `'split'`, regenerate `paths.sh`, then reverse the moves. Compat links make the old paths work in between.

## Code routing (2026-11-26, branch infra/school-paths-1126)
Live code reaches per-school data only through `atlas_paths` (`data()`/`data_w()`, `store()`, `checks_db()`, `school_part()`, `reviewed_path()`, `reviewed_rel()`, `rel_label()`;
paths.sh: `cs_atlas_school_dir`, `cs_atlas_store`, `cs_atlas_checks`). `tools/route_school_paths.py` scans it (comments and docstrings exempt, `route-ok` for a line that must
name a path: recorded wording, a release's flat layout, tracked code); `tests/test_route_school_paths.py` is the guard. Routed: tools/ (about 70 files: listing_rows, input_manifest,
evidence_store, overlay_root, onboarding, stage tools, the vt_stage scripts, ...), accuracy/, atlas_cli, reports/, tests, tools/ft-adv-trial-build.slurm. The overlay code root
has a school-placement mode (`school-data/<school>/`, found through `.overlay.json`). Decisions 2 and 4 are applied: the 13 `derived/report.md` and the EPFL raw capture are
untracked (git rm --cached, `.gitignore`), `derived/` and `raw/` move whole, and untracked leftovers go to `schools/<s>/work/` (the dry run no longer lists leftovers).

**Second pass** (held by live sessions, not touched; in the school placement they work only through `--compat-links` until routed). `fulltext-push/` (line numbers of today's hand-joins):
- `fulltext-push/add_works.py`: lines 35
- `fulltext-push/addworks-1029.slurm`: lines 18
- `fulltext-push/addworks-1104.slurm`: lines 18
- `fulltext-push/addworks-1105.slurm`: lines 34
- `fulltext-push/berkeley_catalog.py`: lines 110
- `fulltext-push/chain_labpages.sh`: lines 21
- `fulltext-push/chain_others.sh`: lines 14
- `fulltext-push/chain_refresh.sh`: lines 13
- `fulltext-push/channels-1030.slurm`: lines 21
- `fulltext-push/checks.py`: lines 16
- `fulltext-push/defense-scan.slurm`: lines 8, 17
- `fulltext-push/downloads.slurm`: lines 36
- `fulltext-push/ftp_common.py`: lines 21
- `fulltext-push/local-reuse/princeton_import.slurm`: lines 17
- `fulltext-push/missing_breakdown.py`: lines 33
- `fulltext-push/newsteps.slurm`: lines 21
- `fulltext-push/oa_editions.slurm`: lines 18
- `fulltext-push/princeton_pass.sh`: lines 13
- `fulltext-push/priority_file.py`: lines 36
- `fulltext-push/proceedings_extra.py`: lines 126
- `fulltext-push/recover-1030.slurm`: lines 20
- `fulltext-push/repath_evidence.py`: lines 37
- `fulltext-push/repull-addworks.slurm`: lines 42
- `fulltext-push/review_access.py`: lines 39, 120, 198
- `fulltext-push/review_identity.py`: lines 40, 291, 371
- `fulltext-push/school-collector.slurm`: lines 52
- `fulltext-push/stanford_catalog.py`: lines 131, 132
- `fulltext-push/wayback_rotate.py`: lines 157

Other second-pass files: `ai-writing/` (embeddings, studies; owner decision 3 keeps `ai/` for later), `hierarchy/labpage-tools-*`:
- `ai-writing/dose/lab_ai_main_tags.py`: 1
- `ai-writing/entropy32/e32.py`: 1
- `ai-writing/entropy32/ftrefs.py`: 1
- `ai-writing/figlab/manifest.py`: 1
- `ai-writing/sections/pilot.py`: 2
- `ai-writing/sections/review.py`: 1
- `ai-writing/sections/run_split.py`: 1
- `ai-writing/study/study_common.py`: 2
- `ai-writing/study/study_delta_build.py`: 1
- `ai-writing/study/study_delta_oa.py`: 1
- `ai-writing/study/study_hetero_attr.py`: 1
- `ai-writing/study/study_hetero_authors.py`: 1
- `ai-writing/study/study_prep.py`: 2
- `ai-writing/study/study_report.py`: 1
- `ai-writing/study/study_snapshot.py`: 5
- `hierarchy/labpage-tools-cmu/w_b05_raw.py`: 1
- `hierarchy/labpage-tools-stanford/seeds.py`: 1
The 15 charters with an unread `[store] path = ".../stores/<s>"` line (cuhk, gatech, harvard, hit, jhu, michigan, nus, pku, seu, uchicago, uestc, ustc, uwashington, washu, whu) are stale after the move; no code reads it.

## Owner decisions
1. Sign off the permanent links `schools/<s>/reviewed -> code/hierarchy/<s>/reviewed` (recommended: yes; decisions stay in git).
2. (done on infra/school-paths-1126) `git rm --cached` the 13 generated `hierarchy/<s>/derived/report.md` (and the epfl raw capture) so `derived/` and `raw/` move as whole directories (recommended: yes; otherwise ~1,100 child moves and `data('census-report.md')` does not resolve in the new place).
3. Include `ai/` embeddings now or later (`--no-ai`; recommended: later, the ai-writing studies hand-join `EMBEDDINGS/<model>/<s>`).
4. (done on infra/school-paths-1126: the dry run maps them) Keep `work/` per school (recommended; the target list did not name it) and untracked leftovers (`cs-related-tools`, stray sqlite) into `work/`.
5. The root removals above.
