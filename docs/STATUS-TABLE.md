# Status table (`atlas status`, 2026-11-10)

`tools/status_table.py` regenerates, on demand, one table of where every cohort school stands. It replaces the one-off generator scripts of the
2026-11-10 status audit (`scratch/top25-goal-1107/status-audit-20261110/`).

```
bin/atlas status                          # live gates, writes hierarchy/derived/STATUS-TABLE.csv, .json, .md (generated, not in git)
bin/atlas status --gates recorded         # no gate evaluation: reads the last hierarchy/<key>/reports/stage-<n>-gate.json (fast, labelled "recorded <date>")
bin/atlas status --gates off --schools oxford hkust --print
bin/atlas status --out-dir <dir>          # a trial run into another directory
bin/atlas status --write-legacy           # also writes scratch/top25-goal-1107/parallel-progress-current.csv (the top-N rows); default off, the old file is otherwise untouched
```

## What it reads (and never writes)
One niced process, known files only, no network, no Slurm, no directory walks. Every path comes from `tools/atlas_paths.py`. The only writes are the three
generated files (and the legacy CSV when `--write-legacy` is given).

| column group | source |
|---|---|
| `rank`, `university`, `country` | `docs/cohort/gras-2025-cse-roster.tsv`: `cohort_rank` is the GRAS CS&E 2025 rank or band (never ARWU). Rows: every charter `schools/*.toml` plus every roster row of rank <= `--top` (default the registry's `top_n`, 25) |
| `frozen_*`, `copies_*` fallback | the newest release (`releases/latest`, else the newest dated `MANIFEST.json`) and its `hierarchy/<key>/copies.json` summary and `students.json`; distinct papers = the copies summary's `lab_papers`, rows stay in `frozen_lab_paper_rows` |
| `package_*`, `papers`, `PIs`, pairs | the latest isolated package registered in `hierarchy/reviewed/status-packages.json` (below): distinct works (OpenAlex id, else DOI, else normalised title), PI-paper relations, PIs with papers, students, lab-student pairs |
| `source_backed_distinct`, `all_kept_distinct` | the registry entry's reviewed `split`; typed from a report, never recomputed, and the row says so in `flags` |
| `gate0` .. `gate10`, `gates_left`, `gate_exceptions` | `stage_gate.evaluate(key, n)` called IN-PROCESS (the gates' own check functions, the data root atlas_paths resolves; `CS_ATLAS_CODE` / `CS_ATLAS_HIERARCHY` move it). A reviewed waiver (`reviewed/gate-exceptions.json`) shows `waived`. `gates_left` lists every stage that is not pass: `N` fail, `Nw` waived, `N?` no result. A stage whose in-process call raises falls back to the recorded stage file, shown as `recorded <date>: ...`; `gates_basis` says `live`, `recorded`, `live+recorded` or `no charter`. It never runs `--run` or `--record` and never writes `chain-audit.json` (`meta.chain_audit_untouched` checks) |
| `copies_local/total/share/source` | the registry entry's `copies_counter` (e.g. the downloads worker's scratch `copies.json`), else `hierarchy/<key>/copies.json`, else the frozen release's; `copies_total` can differ from `papers` (flagged) |
| `loop_*` | `hierarchy/derived/COLLECTORS-STATUS.json` (written by `fulltext-push/collectors_status.py`; `loop_as_of` is its time) |
| `last_main_commit`, `latest_work_branch`, `branch_on_main`, `unlanded_branches` | `git log main -- hierarchy/<key> schools/<key>.toml`; branches not merged into `main` whose name has the school key as a token (`agent/oxford-apply-1109`), plus the registry entry's `branches` |
| `task_ids`, `tasks_live`, `tasks_stale` | `leases/queue.jsonl` through `tools/work_queue.py` (`load`, `state`): live claims with their holder, stale claims, open and blocked tasks of the school |
| `meta.ids` | sha256 of `hierarchy/derived/ids/registry.sqlite` and the live coadvising holds (`IDS-REPORT.json` `coadvising_holds_skipped`; unknown, with the reason, when the report predates the field). The ids stage is never run |
| `websites` | `hierarchy/<key>/lab-websites.json` register: labs with `website` coverage; blank when the school has no register |
| `data_as_of_utc`, `source_files`, `flags` | every row: the time of its counts source, the files read, and every figure that could not be verified (blank counts, mismatched bases, registry-typed numbers, recorded gates, newer candidate package not built yet) |

Unknown values are blank, never zero. `state` is `built` when the frozen release counts the school, else `staged`. A school is never marked admitted by this tool:
`admission_status` says `in frozen release <id>` or `not admitted`.

## The package registry: `hierarchy/reviewed/status-packages.json`
A reviewed input (tracked; `.gitignore` admits it). Paths are relative to the project root and must stay under it. To register a package or move a school to its newer one, edit the file and commit it:

```json
"packages": {
  "oxford": {
    "basis": "latest isolated native package, not admitted",         // label shown in counts_basis
    "path": "scratch/oxford-apply-1109/native4/oxford",             // holds lab_papers.jsonl.gz, pis.json, students.json, report.json
    "candidates": ["scratch/oxford-apply-1110/native5/oxford"],     // optional, newest first: the first one that is built wins, a missing one is flagged
    "split": {"source_backed_distinct": 2832, "all_kept_distinct": 4597, "as_of": "2026-11-10", "source": "hierarchy/sjtu/reports/...md"},  // optional reviewed split
    "copies_counter": "scratch/downloads-1110/hierarchy/harvard/derived/copies.json",   // optional copies.json from a counter run
    "branches": ["fix/oxford-students"],                            // optional extra branches to list as unlanded
    "next_step": "one line"                                         // optional, shown as-is (reviewed text, not generated)
  }
},
"inventory": {"ustc": {"site_id": "university-of-science-and-technology-of-china"}}   // cohort schools without a charter: key -> roster site_id
```
Also `paper_target` (2500) and `top_n` (25). A package that is not built yet is flagged, never counted as zero. The registry is not data about papers: only the package directory is.

## Tests and conventions
`tests/test_status_table.py` (synthetic fixtures: a fake release manifest, package, gate result, roster, git repo; no live data) pins the distinct-works count,
the read-only guarantee (a hash of the whole fixture tree is unchanged, only the three files appear), `--write-legacy` being opt-in, and the blank-not-zero rule.
The tool adds no build rule, so there is nothing to register in `docs/RULES.md` or the rule-coverage test.
