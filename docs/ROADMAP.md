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
| 9 | A schema + data dictionary for every table | phase A done 2026-10-31 (refactor agent): 34 schemas in schemas/, tools/schema_check.py + tools/validate.py, rebuild stage `validate`, docs/DATA-DICTIONARY.md generated; findings on current data: 13 files, 2,437 violations (hierarchy/logs/validation-findings-20261031.json); fixed at the source and in the builder 2026-10-31 (fix/valfix, landed 1697e3c: new packages 35/35 clean in the equivalence job; the live packages clear at the next rebuild) | schemas in the repo; the build validates every output against them |
| 10 | Separate raw / reviewed / derived | phase A done 2026-10-31 (refactor agent): atlas_paths.DATA_FILES + data() (flat today, split after the move), builder and provenance routed, docs/DATA-LAYOUT.md; Slurm 32041363: 7/7 identical (hierarchy/logs/equivalence-datalayout-32041363.*); phase B (the move): dry-run tool tools/relocate_data.py on branch infra/datalayout (286 moves, 0 conflicts, 227 direct path joins in 55 files still to route), no apply mode; awaits the owner's review of the plan. Collector data dirs routed through slots FT_* (infra/ftroute 5301ea3) | raw immutable, reviewed decisions in git, derived rebuilt from both; documented |
| 11 | Stores moved into the project, one writer per catalog, backup policy | done 2026-10-31 619d8e3, 7364291 (stores under stores/; catalog_lock.py on every write path except the Princeton importer and two vendored resolvers, documented; docs/STORES.md retention/backup policy) | stores are real dirs under `stores/`; one writer per catalog; written retention policy |

## 4. Operations

| # | Item | Status | Done when |
|---|---|---|---|
| 12 | Supervised collectors + status page | done 2026-10-31 7364291 (SIGTERM-clean Slurm loops, idle backoff 10 min-4 h, generated hierarchy/COLLECTORS-STATUS.md); six loops on Slurm: 32041175_0, 32041308_1-5; Princeton proof round passed | loops run as Slurm jobs that back off when idle; generated `STATUS.md` per school |
| 13 | Scratch housekeeping | done 2026-10-31 (refactor agent): SCRATCH slot, tools/scratch.py clean (dry run by default; `--apply` as the last rebuild stage), rebuild snapshots in scratch/ | scratch outside the tree, cleaned automatically |
| 14 | Release notes generated from the build regression | done 2026-10-31 (refactor agent): tools/release_notes.py; make_release writes CHANGES.md into each release (a manifest file) | each release carries a generated `CHANGES.md` |

## 5. Documentation

| # | Item | Status | Done when |
|---|---|---|---|
| 15 | Architecture overview + runbook | done 2026-10-31 (refactor agent): docs/ARCHITECTURE.md, docs/RUNBOOK.md | `docs/ARCHITECTURE.md` and `docs/RUNBOOK.md` cover rebuild, collectors, release and recovery |

## 6. Next round (owner-approved 2026-11-01)

Order: **P0** = starts right after the data-layout move (item 10 phase B), in this order. **P1** = next, all before the release (owner 2026-11-01). **P2** = the ten after P1, also before the release (owner 2026-11-02). The rest are open.

### Robustness and cleanliness

| # | Item | Status | Done when |
|---|---|---|---|
| 16 | Agents commit through branches only; Slurm jobs only from a code snapshot | **P0-2** (in progress, refactor agent: CI test `tests/test_slurm_snapshot.py`, collector one-offs retired to archive/fulltext-push, `atlas submit` documented; the enforce switch awaits the coordinator's word) | every agent works in a worktree and lands with `agent_worktree.sh land`; the main-commit hook refuses (enforce mode); CI fails on any `.slurm` that does not source `job_code_snapshot.sh`; `atlas submit` is the documented submit path |
| 17 | One lease per agent or session | **P1-3** (done, refactor agent: tools/agent_lease.py + `atlas lease`, tests, RUNBOOK restart checklist) | a lease file per agent, renewed while it works; a second copy refuses to start while the lease is live; restart checklist uses it |
| 18 | Download loops that restart themselves | **P1-2** done 2026-11-02 f3230e8 (downloads.slurm --signal=B:USR1@900 resubmits at the limit; tests/test_loop_job.py; running loops 32065276_0-6 restarted onto it by the coordinator) | a loop resubmits itself at its time limit on the current pinned commit; no manual restart at 3 days |
| 19 | `atlas new-school <key>` | **P2-5** done 2026-11-02 (refactor agent): tools/new_school.py; charter from TEMPLATE.toml, hierarchy folders, an empty store with the standard catalog schema (incl. work_alias) and a receipts row, the stage-0 check's to-do list; refuses an existing school | one command makes the charter, store, folders, catalog schema and receipts, and runs the stage-0 check (no cloning another school's store) |
| 20 | No half-covered catalog locks | **P1-5** done 2026-11-02 d96b17b (Princeton importers and the Infoscience/DSpace resolvers take catalog_lock + backup_catalog; test) | the Princeton importer and the two vendored resolvers take the catalog lock and the pre-write backup |
| 21 | Code as an installed package | **P2-7** done 2026-11-02, option B (refactor agent): 47 `tools/` modules lose their self-directory `sys.path` edit; the tests lose theirs (pytest `pythonpath`); `pyproject.toml` installs the flat tools modules, `pihier` and `atlas` (`pip install -e .`); tests/test_imports_and_sys_path.py forbids new edits outside tests/sys_path_allowlist.json (164 files with their reasons: `python -I` entry points and their helpers, vendored code, cross-directory imports). `-I` stays on every entry point that handles untrusted files (docs/CONTRIBUTING.md) | tools/ installed as a package; no `sys.path` edits in tools, vendor or tests where `-I` allows |
| 22 | Deterministic generators everywhere | **P1-4** done 2026-11-02 (refactor agent): two-seed tests for the reader export, release notes and the coverage resolution; `atlas_paths.gzip_text` (zero gzip header time) in the package writer, id writer, ledger and reader export; tools/content_hash.py names the deliberate stamps (package builtAt, ledger built_at/checked_at, copies counted_at, MANIFEST created, ...), make_release records `content_sha256` without them beside the byte hash, and package_diff ignores them by default | the two-seed determinism test covers the ledger, reader export, coverage counter and release; a content-neutral re-run changes no file content that matters |
| 23 | Chores | **P2-10** (before the release; owner 2026-11-02) | **Done 2026-11-02 except scratch and py310:** CI actions bumped to the current majors (`actions/checkout@v7`, `conda-incubator/setup-miniconda@v4`, same steps, YAML parses); merged local branches `infra/datarouting`, `infra/ftcheck`, `infra/reader` deleted (`infra/publishing-process` is merged but has a live worktree and was left; `infra/p32` and `release/site-20261102` have unmerged commits and were left; remote branches untouched). Scratch clean: `tools/scratch.py clean --days 2` was refused by the permission classifier; candidates older than 2 days by mtime are `ft-data-routing` and `snapshot-proof` (both 2026-10-31), needing an owner or coordinator go. py310: **done 2026-11-03 except the ML studies** (non-ML users and `COLLECTOR_PY` moved to env/atlas; torch/sklearn/pandas studies stay, docs/ENVIRONMENT.md "Retiring py310"). |

### Data quality

| # | Item | Status | Done when |
|---|---|---|---|
| 24 | OpenAlex bulk snapshot instead of the API | **P0-1** | a filtered local snapshot (our institutions' works and authors), refreshed on a schedule; lookups read it first; the 10k/day API key is a fallback only; no shared-storage I/O hazard (streamed and filtered)  **Refresh done 2026-11-03:** `atlas pipeline snapshot-refresh` (new dated store, per-school compare, `--promote` only) and the self-resubmitting monthly `tools/oa_snapshot_refresh.slurm` (docs/OPENALEX-SNAPSHOT.md section 14; dry-run only so far) |
| 25 | Better title checks | **P2-1** done 2026-11-03 (f1dcc14 and the revert 9a95460; docs/UNAVAILABLE.md "Better title checks"): 172 confirmed, then 50 doubtful ones sent back, 122 stay; false-pass 7.5% (3 of 40) in-sample before the apply rules; fresh holdout of 20: 1 wrong (5%), removed by the title-overlap rule; full audit of the 67 non-arXiv-DOI passes found 11 wrong or doubtful, 50 reverted, 0 wrong in the rest; false-reject among the 222 undecided: 13 of 15 sampled were the right paper (kept pending on purpose) | identity matches every known title (OpenAlex, S2, arXiv versions) and the PDF's title metadata; re-measured false-pass and false-reject rates recorded |
| 26 | Departed-faculty detection | **P2-2** (before the release; owner 2026-11-02); open (needs 24) | a review list of PIs whose OpenAlex/DBLP affiliation moved elsewhere while our build has an open period; Gupta and Platzer resolved or recorded unresolved |
| 27 | Lab-page template readers | **P2-8** (before the release; owner 2026-11-02) | structural readers for al-folio/Jekyll, Google Sites and WordPress team pages; membership error rate re-measured |
| 28 | One entry per paper in the stores | **P2-3** (before the release; owner 2026-11-02) | DOI/title sibling works collapsed onto the atlas work id in every store; counts and identity checks run on canonical works |
| 29 | Boundary years settled | **P2-4** (before the release; owner 2026-11-02) | the dated-capture (transition_side) rule applies to every arrival/departure-year paper; undecided count reported per school |
| 30 | The site serves only from releases | **P1-1** (done in the release tooling, refactor agent: reader/unpublish.tsv + upload.tsv + SUMMARY site_sync, the handoff note text, `atlas release` checks them; the site-side removal is Codex's) | the release's reader export is the only source of hosted files; the 5,326 untraceable hosted files are gone |
| 31 | Open owner decisions | open | publisher TDM access via the Library; Michigan's 171-lab student gap |

### Speed and efficiency

| # | Item | Status | Done when |
|---|---|---|---|
| 32 | Per-school parallel equivalence and rebuild | **P0-3** done 2026-11-02 (refactor agent): `atlas parallel equivalence|rebuild` (hierarchy/submit-parallel.sh, `ARRAY_THROTTLE=N`); measured: six schools old==new in 15m37s parallel (array 32065414, throttle 3) vs 35m23s serial (32071116); a same-input rerun waits for a clean `--test-only`, and the release's parallel rebuild is the final proof | one Slurm array task per school plus a merge step; equivalence 15m37s vs 35m23s serial, rebuild target ≈ 45 min |
| 33 | Rebuild only what changed | **P2-6** v1 done 2026-11-02 (refactor agent): tools/stale_stages.py (`atlas stale`; `STAGES=auto hierarchy/rebuild.sh`): each stage declares DATA_FILES inputs, store catalog and code files; stale = output missing, input newer than the oldest output, or code committed after it; fresh stages are skipped and the checks (audits..housekeeping) always run. Limits: mtimes not hashes; per-school stages run for the union of stale schools; a live catalog keeps copies/ledger stale while the loops download | a dependency-driven rebuild from DATA_FILES inputs/outputs that redoes only stale outputs |
| 34 | Script the mechanical work out of agents | **P0-5** (built, refactor agent: `atlas pipeline copies|labpage|reader`, tools/atlas_pipeline.py + hierarchy/pipeline-stage.slurm; the fulltext-push stages (ledger, recount, status) run the downloads agent's tools unchanged - it should read the registry) | submit/poll/recount/restamp/ledger/copies run as a Slurm pipeline with dependencies; agents only for hand checks, design and diagnosis |
| 35 | Poll less | **done** 2026-11-02 (refactor agent): tools/slurm_wait.py (one `sacct -j` per >= 120 s, ends on the first failed job, backs off on errors; `scontrol wait_job` dropped because it polls every few seconds); `atlas pipeline --wait` and `atlas release --wait` (the release chain as hierarchy/release.slurm, pinned HEAD, `--test-only` guard, then the same wait); poll guidance removed from RUNBOOK and ADDING-A-SCHOOL. Left alone: fetcher pacing and retry sleeps, and the retired one-off fulltext-push/chain_*.sh process waits (local `kill -0`, not the controller) | jobs chain by Slurm dependencies and output files instead of repeated status checks |
| 36 | A review page for hand checks | **done** 2026-11-02 (refactor agent): `atlas review-page labpage|accuracy|build|serve|export` (tools/review_page.py): a self-contained HTML page per sample (facts, quote, capture link, verdict boxes, localStorage progress, Export), the lab-page draw identical to `labpage_audit.py sample`, export -> the `labpage_audit.py record` round spec (bar scaled by sample size) or `accuracy/record.py` input; local file or 127.0.0.1 only; not browser-tested here (no node/browser on the login host), the page script is plain DOM code | a page per sample with each row's quote, capture and a verdict box; rounds recorded from it |

### Standardizing the process

| # | Item | Status | Done when |
|---|---|---|---|
| 37 | One release command: `atlas release` | **P0-4** (built, refactor agent: tools/atlas_release.py, hierarchy/release.slurm, tests). **v2 done 2026-11-03** (owner: "a lot more efficient"; the first release took ~10 runs over a day): fast preflight before any build (tests in a git-archive snapshot with the release env, validate, evidence, regression vs the last release, swings signed off up front by `--allow-swings` or `--swings-file`), stage-granular resume (run.json `rebuild_stages`; resume across a tests/docs-only commit with a note), the build as the per-school Slurm array newest first (`--serial-build`), regression before validate, `zero_paper` as a rebuild stage, one release at a time (lease `atlas-release`), `rebuild.sh STAGES=...` as an argument (unknown arguments refused), Slurm by default (`--local` opt-in), `--preflight-only` | rebuild → validate → regression → reader export → release notes → release → GitHub export → HF upload → Codex handoff note, in order, stopping at any failure |
| 38 | One decision log | **P2-9** (before the release; owner 2026-11-02) | docs/DECISIONS.md, dated, each decision linked to the rule or file it changed |
| 39 | Adding a school runs itself to the review steps | **done** 2026-11-02 (refactor agent): `atlas stage-gate <school> <n> --run [--submit]` runs a stage's steps up to its first hand step (light steps here, heavy ones as an afterok Slurm chain with a Preempts guard), refuses released schools, writes `reports/stage-<n>-gate.json`; gates now cover stages 0-10 (adds charter+hosts, students/papers/copies/accuracy/release, ISO period dates, `gate-exceptions.json` waivers; Michigan reproduces its recorded gate results). docs/ADDING-A-SCHOOL.md "Running a stage"; UChicago PROTOCOL-FRICTION.md requests are handled as they appear | `atlas new-school` + `atlas stage-gate` per stage; the protocol's checks as code |
| 40 | Restart checklist in the runbook | **done** 2026-11-02 (refactor agent): docs/RUNBOOK.md "Restart checklist": other sessions, handover, re-creating the session-only auto-resume check (`/loop 30m`), no job on live code, loops on the current commit, locks and journals | other sessions, agent handover, auto-resume check, no job on live code |
| 41 | One report shape for agents | **done 2026-11-03** | the template in docs/CONTRIBUTING.md ("Agent reports"), used by the atlas-worker agent file |
