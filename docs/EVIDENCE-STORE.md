# Evidence store (phase 1 of the backend refactor, 2026-11-17)

One SQLite file per school holds every per-person decision with its source, replacing over time the scattered reviewed-JSON
layers (`docs/REVIEWED-INPUTS.md`). Phase 1 was a **lossless import and an exporter**: no builder reads the store, no output
changes. Phase 2 (below) makes it the source of truth for one school. Owner rule: container formats, not many small files (hence SQLite, not a JSON file per decision).

## Files
| File | What |
|---|---|
| `schemas/evidence/evidence-store.sql` | the tables (`meta`, `layer`, `evidence`); the tool creates stores from this file |
| `schemas/evidence/evidence-row.schema.json` | the claim columns and the `claim_kind` vocabulary |
| `tools/evidence_store.py` | `import`, `export`, `verify`, `overlay`, `coverage`; phase 2: `flagged`, `find`, `record`, `sync`, `check` (`bin/atlas evidence-store ...`) |
| `tests/test_evidence_store.py` | fixture round trips, claim columns, shared-file split, overlay |

Default location: `<stores>/<school>/evidence.sqlite` (`CS_ATLAS_EVIDENCE_DIR` or `--store-dir` override it). `_shared` is the store
for shared reviewed files that name no school. Importing writes a fresh file each time (built in local temp, copied in), so an
import is a snapshot, never a merge.

## Model
- `evidence`: one row per decision = a list item or a map entry of a reviewed file. Columns: `school`, `person_key`, `claim_kind`,
  `facets`, `value`, source (`source_url`, `source_date` = capture or fetch date as stated, `source_kind`), `decided_by`,
  `decided_at`, `reviewed_by`, `review_ref`, `supersedes`, and `record`.
- **`record` is the truth.** It is the original entry as JSON, key order kept. The other columns are an index projected from it
  by `claim()` (best effort: a column is NULL when the record does not state it). Nothing may be written to a column that the
  record does not carry; the exporter reads only `record`.
- `claim_kind`: `admission`, `cs_related`, `exclusion`, `excluded_unresolved` (owner ruling 2026-11-17: no source places the person in
  the window; `value` carries `reason`, `reason_code`, `sources_tried`; never a proven absence), `rank`, `unit`, `period`,
  `identity_link`, `student_membership`, `hold`, `home_department`, `paper_claim`, `lab_reason`, `evidence`, `review_note`
  (pending/unresolved legacy rows), `other`. A census override carries several claims: `claim_kind` is the strongest and `facets`
  lists the rest. Rank/unit claims of a census row live inside the `admission` row's `value` until a later phase splits them.
- `layer`: one row per reviewed file: skeleton (the file with the decision containers cut out), containers, key order, the dump
  style that reproduces the bytes, sha256, and the source path. `seq` in `evidence` is the position inside the container.
- Containers: `list` (root list, or a top-level key holding a list of dicts), `map` (root map of person -> entry, or a
  `decisions`-style key), `map2` (school -> person -> entry, only the shared school-keyed files), `doc` (a file with no
  list/map of decisions is one row holding the whole document).
- Shared files (`hierarchy/reviewed/`): rows go to the owning school's store (list items by their `school` field, school-keyed
  maps by key); what names no school (`cs-venues.json`, `status-packages.json`, ...) goes to `_shared`, which also holds the full
  descriptor. Rebuilding a shared file needs every school store plus `_shared`.

## Lossless guarantee
`export` writes a file as `json.dumps` with the style found at import (indent, `ensure_ascii`, separators, key sorting, final
newline). A file whose bytes no standard style reproduces (hand-formatted) keeps its original text in `layer.layout_text`; the
exporter writes it back only while the rows still equal it, otherwise it writes the default style (`indent=1`, UTF-8). A file
that is not valid JSON or has duplicate keys is kept verbatim with no rows and named in the report. Not covered: non-JSON files
(`nicknames/*.csv`), subdirectories of a `reviewed/` directory (`reader/`, Vermont `source-captures/`).

## Use
```
python tools/evidence_store.py import --all --store-dir DIR      # or import michigan
python tools/evidence_store.py verify --all                      # import to scratch, export, compare every file with the original
python tools/evidence_store.py export michigan --out DIR         # DIR/hierarchy/<school>/reviewed/*.json + DIR/hierarchy/reviewed/*.json
python tools/evidence_store.py overlay michigan --out <school tmp>/ov --store-dir DIR [--control]
```
`overlay` builds an `overlay_root.py` code root whose reviewed files (school and shared) are the exported ones; `--control` copies
the root's own files the same way, so a build pair differs only in where the bytes came from. Run a build against it with
`CS_ATLAS_CODE=<overlay> PI_HIERARCHY_OUT=<scratch> python tools/pi_hierarchy.py <school>` and compare the outputs.

## Phase 1 results (2026-11-17)
- Import of all 31 schools plus `_shared`: 523 reviewed JSON files (508 school, 15 shared), 91.3k rows, 60 MB in total, 0 files the
  converters cannot represent. Export of every file is byte-identical (`verify --all`, 34 s).
- Michigan: 28 school files + 15 shared; round trip byte-identical; build outputs with regenerated inputs identical to the control
  (Slurm 32392867 control vs 32392868 regenerated, 15 min, 8 GB each): `pis.json`, `students.json`, `lab_papers.jsonl.gz`,
  `student_papers.jsonl.gz` byte-identical; `report.json` differs only in `builtAt` and the path of the reviewed file it echoes.
- Weak projections (the record is intact, only the index is thin): 41k rows are plain `evidence` (lab pages, directories, websites),
  2.5k `other`, 2.5k `review_note` (legacy `pending_*`); 817 `evidence` and 677 `other` rows have no person key (whole-document rows).

## Phase 2 (R3a, 2026-11-17): a store-sourced school
Michigan is the first school whose store is the **source of truth**. Charter `schools/michigan.toml`: `[evidence] source = "store"`
(default `"json"`; `school_config.evidence_source(key)`, validated by `school_config.py --check`). Readers and writers switch together,
per school: nothing is ever switched for readers only (the store would go stale).
- **The store** is `<stores>/michigan/evidence.sqlite` (imported 2026-11-17 from main's reviewed files). **The JSON view**:
  `hierarchy/michigan/reviewed/*.json` (28 files) is an export of it, tracked in git exactly as before, so every unchanged tool (pi_hierarchy,
  stage_gate, atlas doctor, the audits, the release export) keeps reading the same bytes. The shared files `hierarchy/reviewed/*.json` stay
  JSON-sourced: Michigan's slices in them are only a snapshot (scope `shared`, not authoritative) until a later phase.
- **Guard.** A direct edit of a store-sourced school's reviewed JSON is refused three ways: the pre-commit hook (`evidence_store.py check --staged`,
  compares the git-index bytes of staged `hierarchy/<school>/reviewed/*.json` with the store's rendering, also refusing deletions and files the
  store does not hold), `evidence_store.py check [school]` (worktree vs store, any time), and `atlas doctor` (`evidence_view` per school; a problem
  becomes a next action). `import` refuses to overwrite an existing store of a flagged school (it would erase recorded decisions).
- **Gate.** `stage_gate.py` and `atlas doctor` keep reading the JSON view; the doctor adds `evidence_view` (view == store).

**Result (2026-11-17).** Fresh import of Michigan into the real location: 7,079 school rows + 1,475 `_shared` rows; `check` = view matches
(28 files, byte-identical to main). Build pair from overlay roots (Slurm 32393134 control, 32393135 store-sourced, 14 min each): `pis.json`,
`students.json`, `lab_papers.jsonl.gz`, `student_papers.jsonl.gz` byte-identical; `report.json` differs only in `builtAt` and echoed paths.

### Record a decision (a worker, Michigan)
```
bin/atlas evidence-store find michigan --layer census-additions.json --key "Jane Doe"       # existing rows: id, container, seq, record
bin/atlas evidence-store record michigan --layer census-additions.json \
    --record '{"name": "Jane Doe", "rank": "Professor", ...}' --source https://... --decided-by <your session> [--reviewed-by <reviewer>] [--note ...]
bin/atlas evidence-store record michigan --layer census-overrides-school.json --entry-key "Jane Doe" --record '{"aliases": [...]}' ...   # map layers: new key
bin/atlas evidence-store record michigan --layer census-additions.json --supersede 1234 --record '{...}' ...                             # replace a row (the old record stays in write_log)
bin/atlas evidence-store sync michigan      # (record already does it) rewrite the JSON view in YOUR worktree; then commit it on your branch and land
```
`--record` is the entry exactly as the reviewed file holds it (a list item, or the value of a map entry); `--source` and `--decided-by` are mandatory and
go to `write_log` (`evidence_id`, action add/supersede, time, decided_by, reviewed_by, source, old record) and to the claim columns the record does
not itself carry. The store is shared data (it is not in git), the JSON view is code (it lands by commit): between `record` and the landing, `check`
on main reports the difference, which is the intended signal that a landing is pending. `sync` and `check` act on the checkout the tool runs from.
Container choice: lists append, maps need a new `--entry-key` (maps keyed school -> person also `--sub-key`); `--container N` for a layer with several.
Not supported yet: deleting a row (supersede it with the corrected record), adding a new kind of reviewed file (a layer; ask the coordinator).

### Switch another school
1. `bin/atlas evidence-store import <school>` into the real location (a fresh snapshot of its reviewed files; `verify <school>` first).
2. Build a control and a store-sourced overlay (`overlay <school> --out DIR [--control]`; a flagged school's overlay takes only its own files from the
   store) as Slurm jobs and require byte-identical `pis.json`, `students.json`, `lab_papers.jsonl.gz`, `student_papers.jsonl.gz`.
3. Add `[evidence]` `source = "store"` to the charter in the same commit; from then on the hook, `check` and the doctor guard it.
4. To go back: set `source = "json"` (the JSON view is already the current state; the store file can be archived).

## Next phases (not done)
1. Michigan's slices of the shared reviewed files (`census-overrides.json`, `student-corrections.json`, ...) move into the store with an export that
   patches only that school's slice; then a reader may read the store directly (`census_overrides.section`, `pi_hierarchy` reviewed inputs).
2. Writers (stage tools, `excluded_audit.py`) call `record()` instead of editing files, school by school.
3. Split rank/unit/period/identity facets into their own rows once the readers use claims rather than records.
