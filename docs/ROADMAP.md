# Roadmap: making the codebase standard

Owner-approved on 2026-10-30. Each item has an owner and a definition of done, and it stays open until a reviewer has
checked that definition against the repo. Update the status line when an item moves; never delete an item.

Status: `open` · `in progress (<who>)` · `done <date> <commit>` · `queued (after <x>)`.

## In flight

| # | Item | Status | Done when |
|---|---|---|---|
| 0 | Stable-ID re-run fix (`tools/atlas_ids.py`) | in progress (coordinator) | two consecutive real-data runs give identical ids; test added; committed |
| L | Per-paper unavailability ledger, as a standard | in progress (downloads agent) | every non-local lab paper has a reason code built from recorded checks; `ledger` step in rebuild.sh; build gate; `docs/UNAVAILABLE.md`; 20 hand-checked entries |
| M | Michigan through stages 0–9; stage 10 prepared | in progress (Michigan agent) | stage gates pass or report their blockers; protocol updated; release steps listed |
| R | Copy recovery toward 85% | in progress (downloads agent) | measured before/after per school; ceiling under the no-paywall rule stated |
| LP | Lab-page audit, all 7 schools (owner 2026-10-30) | in progress (lab-page agent) | every PI lab has a lab_page record (found, or none_found with a reason); students incl. alumni and pubs-page papers audited against the build with a reason per gap; additions proposed with evidence; `docs/LAB-PAGES.md`; a gate in the protocol |

## 1. Foundations

| # | Item | Status | Done when |
|---|---|---|---|
| 1 | One Python env, pinned; `pyproject.toml`; `atlas <command>` entry point | done 2026-10-30 f73ec14 (217 tests pass under env/atlas; collectors still on COLLECTOR_PY until the switch-over) | env at `homogenizing-science/env/atlas` built from a lock; one `PY` everywhere; full tests + a Michigan build pass under it |
| 2 | Code from the old working folders brought into the repo | done 2026-10-30 0351fa8, 076bde9 (46 files in vendor/, PROVENANCE.tsv; originals retire after the loops restart) | `git grep` finds no `research-sweeps` / `P.sweep(` read in code that the build or collectors run; provenance per file |
| 3 | Public remote + CI | done 2026-10-30 16d9e6a (dev = main pushed; CI red only on two unused imports in files still open) | `dev` branch on `liv-daliberti/cs-labs-atlas`; CI (ruff, fixture tests, secret scan, charter check) green; history scan clean |
| 4 | Agents work on branches | done 2026-10-30 16d9e6a (hook warns; enforce with `git config atlas.mainCommits enforce` once current agents finish) | `docs/CONTRIBUTING.md`; `tools/agent_worktree.sh`; main-commit hook warns now, enforces after the current agents finish |
| P | Everything under `/n/fs/resemble/homogenizing-science` | queued (after 1–4, M, L/R report; rinse loops stopped; Codex told) | `relocate_project.py` dry run reviewed by the owner; move logged; no references to old paths left; no compat links left; loops restarted as Slurm jobs |

## 2. Make schools mechanical

| # | Item | Status | Done when |
|---|---|---|---|
| 5 | Replace the one-school scripts (271 files) with config-driven tools | queued (after M and P) | each one-school script is folded into a `tools/*_school.py` stage tool or retired to `archive/`, with a list of what went where; adding a school = a charter + `atlas stage-gate` runs |
| 6 | Discovery channels as plugins (`discover(school, papers) -> hits + recorded misses`) | in progress (downloads agent) | each source is one module; a shared runner writes candidates + checks; old and new outputs are identical on one school; a test per plugin; `docs/CHANNELS.md` |
| 7 | Sanity checks on bulk pulls (per-year counts, duplicates, outliers) | in progress (Michigan agent) | `sweep-check.json` per school; fails on a synthetic 20× year; passes or explains the released schools; wired into the stage gate and the protocol |
| 8 | Split `pi_hierarchy.py` (2,098 lines) into census / periods / identity / papers / students / links; one test per rule ID | queued (after M and P) | a rebuild before and after the split gives identical packages for all schools; every rule in `RULES.md` has a test named after its id; CI checks that coverage |

## 3. Data standards

| # | Item | Status | Done when |
|---|---|---|---|
| 9 | A schema + data dictionary for every table | open | schemas in the repo; the build validates every output against them |
| 10 | Separate raw / reviewed / derived | open | raw immutable, reviewed decisions in git, derived rebuilt from both; documented |
| 11 | Stores moved into the project, one writer per catalog, backup policy | partly via P | stores are real dirs under `stores/`; one writer per catalog; written retention policy |

## 4. Operations

| # | Item | Status | Done when |
|---|---|---|---|
| 12 | Supervised collectors + status page | queued (with P) | loops run as Slurm jobs that back off when idle; generated `STATUS.md` per school |
| 13 | Scratch housekeeping | open | scratch outside the tree, cleaned automatically |
| 14 | Release notes generated from the build regression | open | each release carries a generated `CHANGES.md` |

## 5. Documentation

| # | Item | Status | Done when |
|---|---|---|---|
| 15 | Architecture overview + runbook | open | `docs/ARCHITECTURE.md` and `docs/RUNBOOK.md` cover rebuild, collectors, release and recovery |
