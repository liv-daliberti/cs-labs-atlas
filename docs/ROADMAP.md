# Roadmap: making the codebase standard

Owner-approved on 2026-10-30. Each item has an owner and a definition of done, and it stays open until a reviewer has
checked that definition against the repo. Update the status line when an item moves; never delete an item.

Status: `open` · `in progress (<who>)` · `done <date> <commit>` · `queued (after <x>)`.

## In flight

| # | Item | Status | Done when |
|---|---|---|---|
| 0 | Stable-ID re-run fix (`tools/atlas_ids.py`) | done 2026-10-30 (Slurm 32032541: two runs identical, 0 person/work diffs vs release; 37 ambiguous anchors held out) | two consecutive real-data runs give identical ids; test added; committed |
| L | Per-paper unavailability ledger, as a standard | in progress (downloads agent) | every non-local lab paper has a reason code built from recorded checks; `ledger` step in rebuild.sh; build gate; `docs/UNAVAILABLE.md`; 20 hand-checked entries |
| M | Michigan through stages 0–9; stage 10 prepared | blocked at stage 6 (owner decision), 2026-10-30 dc307d6: stages 0–5 pass; stage 6 fails with 117/288 labs having students once allowed sources are exhausted; stage 7 measured (14,149 lab papers, 278 labs); stage 8 prepared, not submitted | stage gates pass or report their blockers; protocol updated; release steps listed |
| R | Copy recovery toward 85% | in progress (downloads agent) | measured before/after per school; ceiling under the no-paywall rule stated |
| LP | Lab-page audit, all 7 schools (owner 2026-10-30) | in progress (lab-page agent): Princeton done dfdad2c (140/140 labs recorded; 151 students + 59 papers proposed); MIT, CMU, Berkeley, EPFL, Stanford, Michigan next | every PI lab has a lab_page record (found, or none_found with a reason); students incl. alumni and pubs-page papers audited against the build with a reason per gap; additions proposed with evidence; `docs/LAB-PAGES.md`; a gate in the protocol |

## 1. Foundations

| # | Item | Status | Done when |
|---|---|---|---|
| 1 | One Python env, pinned; `pyproject.toml`; `atlas <command>` entry point | done 2026-10-30 f73ec14 (217 tests pass under env/atlas; collectors still on COLLECTOR_PY until the switch-over) | env at `homogenizing-science/env/atlas` built from a lock; one `PY` everywhere; full tests + a Michigan build pass under it |
| 2 | Code from the old working folders brought into the repo | done 2026-10-30 0351fa8, 076bde9 (46 files in vendor/, PROVENANCE.tsv; originals retire after the loops restart) | `git grep` finds no `research-sweeps` / `P.sweep(` read in code that the build or collectors run; provenance per file |
| 3 | Public remote + CI | done 2026-10-30 16d9e6a (dev = main pushed; CI red only on two unused imports in files still open) | `dev` branch on `liv-daliberti/cs-labs-atlas`; CI (ruff, fixture tests, secret scan, charter check) green; history scan clean |
| 4 | Agents work on branches | done 2026-10-30 16d9e6a (hook warns; enforce with `git config atlas.mainCommits enforce` once current agents finish) | `docs/CONTRIBUTING.md`; `tools/agent_worktree.sh`; main-commit hook warns now, enforces after the current agents finish |
| P | Everything under `/n/fs/resemble/homogenizing-science` | done 2026-10-30 619d8e3, ebd080f (42 renames, 274 refs; Codex confirmed; compat links and 13 stale links removed 23:39; vendor check resolves originals through the move record; loops restart as Slurm jobs under item 12) | `relocate_project.py` dry run reviewed by the owner; move logged; no references to old paths left; no compat links left; loops restarted as Slurm jobs |

## 2. Make schools mechanical

| # | Item | Status | Done when |
|---|---|---|---|
| 5 | Replace the one-school scripts (271 files) with config-driven tools | done 2026-10-31, the commits "Retire the one-off and one-school scripts to archive/" .. "export: copy tools/pihier/" (docs/SCRIPT-MAP.md: 389 scripts, 265 retired to archive/, 4 folded into tools/mpcap.py and tools/sweep_school.py, 4 configs kept, 116 deferred to the lab-page and downloads agents; tests/test_script_map.py; Slurm 32040672: 7/7 schools identical before and after on top of fix/stu08, report hierarchy/logs/equivalence-item5-32040672.{txt,out}) | each one-school script is folded into a `tools/*_school.py` stage tool or retired to `archive/`, with a list of what went where; adding a school = a charter + `atlas stage-gate` runs |
| 6 | Discovery channels as plugins (`discover(school, papers) -> hits + recorded misses`) | done 2026-10-30 d164d03 (25 plugins in fulltext-push/channels/, channel_runner.py; old = new candidates on CMU; tests/test_channels.py; docs/CHANNELS.md) | each source is one module; a shared runner writes candidates + checks; old and new outputs are identical on one school; a test per plugin; `docs/CHANNELS.md` |
| 7 | Sanity checks on bulk pulls (per-year counts, duplicates, outliers) | done 2026-10-30 7320995, 6e75a20 (tools/sweep_check.py; all 7 schools pass, Michigan 2022 and Berkeley 2026 by reviewed exceptions; tests/test_sweep_check.py) | `sweep-check.json` per school; fails on a synthetic 20× year; passes or explains the released schools; wired into the stage gate and the protocol |
| 8 | Split `pi_hierarchy.py` (2,098 lines) into census / periods / identity / papers / students / links; one test per rule ID | done 2026-10-31 83ab9e7..624be3f, pushed 4e0cccc (tools/pihier/, 9 modules + the pi_hierarchy.py entry point; Slurm 32037267: 7/7 schools identical old vs new at one hash seed, only builtAt and provenance.at ignored, report hierarchy/logs/equivalence-item8-32037267.{txt,out} and -seed-control.txt; 64/64 rule ids tested, tests/test_rule_coverage.py; a pre-existing hash-seed dependence found and fixed on fix/stu08) | a rebuild before and after the split gives identical packages for all schools; every rule in `RULES.md` has a test named after its id; CI checks that coverage |

## 3. Data standards

| # | Item | Status | Done when |
|---|---|---|---|
| 9 | A schema + data dictionary for every table | phase A done 2026-10-31 (refactor agent): 34 schemas in schemas/, tools/schema_check.py + tools/validate.py, rebuild stage `validate`, docs/DATA-DICTIONARY.md generated; findings on current data: 13 files, 2,437 violations (hierarchy/logs/validation-findings-20261031.json), not fixed | schemas in the repo; the build validates every output against them |
| 10 | Separate raw / reviewed / derived | phase A done 2026-10-31 (refactor agent): atlas_paths.DATA_FILES + data() (flat today, split after the move), builder and provenance routed, docs/DATA-LAYOUT.md; Slurm 32041363: 7/7 identical (hierarchy/logs/equivalence-datalayout-32041363.*); phase B (the move) awaits the owner's OK on a dry run | raw immutable, reviewed decisions in git, derived rebuilt from both; documented |
| 11 | Stores moved into the project, one writer per catalog, backup policy | done 2026-10-31 619d8e3, 7364291 (stores under stores/; catalog_lock.py on every write path except the Princeton importer and two vendored resolvers, documented; docs/STORES.md retention/backup policy) | stores are real dirs under `stores/`; one writer per catalog; written retention policy |

## 4. Operations

| # | Item | Status | Done when |
|---|---|---|---|
| 12 | Supervised collectors + status page | done 2026-10-31 7364291 (SIGTERM-clean Slurm loops, idle backoff 10 min-4 h, generated hierarchy/COLLECTORS-STATUS.md); six loops on Slurm: 32041175_0, 32041308_1-5; Princeton proof round passed | loops run as Slurm jobs that back off when idle; generated `STATUS.md` per school |
| 13 | Scratch housekeeping | done 2026-11-01 314feeb (SCRATCH slot outside the tree, tools/scratch.py clean, rebuild housekeeping stage) | scratch outside the tree, cleaned automatically |
| 14 | Release notes generated from the build regression | done 2026-11-01 8322ca4 (tools/release_notes.py: each release carries a generated CHANGES.md from the build regression) | each release carries a generated `CHANGES.md` |

## 5. Documentation

| # | Item | Status | Done when |
|---|---|---|---|
| 15 | Architecture overview + runbook | done 2026-11-01 (docs/ARCHITECTURE.md, docs/RUNBOOK.md; also 7fb0cdb: Slurm jobs run from a code snapshot) | `docs/ARCHITECTURE.md` and `docs/RUNBOOK.md` cover rebuild, collectors, release and recovery |
