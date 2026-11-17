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
  JSON-sourced in R3a (their Michigan slices were a snapshot); R3b below moves Michigan's slices into the store.
- **Guard.** A direct edit of a store-sourced school's reviewed JSON is refused three ways: the pre-commit hook (`evidence_store.py check --staged`,
  compares the git-index bytes of staged `hierarchy/<school>/reviewed/*.json` with the store's rendering, also refusing deletions and files the
  store does not hold), `evidence_store.py check [school]` (worktree vs store, any time), and `atlas doctor` (`evidence_view` per school; a problem
  becomes a next action). `import` refuses to overwrite an existing store of a flagged school (it would erase recorded decisions).
- **Gate.** `stage_gate.py` and `atlas doctor` keep reading the JSON view; the doctor adds `evidence_view` (view == store).

**Result (2026-11-17).** Fresh import of Michigan into the real location: 7,079 school rows + 1,475 `_shared` rows; `check` = view matches
(28 files, byte-identical to main). Build pair from overlay roots (Slurm 32393134 control, 32393135 store-sourced, 14 min each): `pis.json`,
`students.json`, `lab_papers.jsonl.gz`, `student_papers.jsonl.gz` byte-identical; `report.json` differs only in `builtAt` and echoed paths.

### Backups and restore (R3b, 2026-11-17)
The store files are **not in git** and hold decision history (`write_log`, superseded records), so every store-sourced school is backed up:
`bin/atlas evidence-store backup [school...]` writes `archive/evidence-store-backups/<UTC stamp>/<school>-evidence.sqlite` with the sqlite online
backup API (safe while a `record` runs), runs `PRAGMA integrity_check` and a row-count check on the copy (a failing copy is discarded), and writes
`SHA256SUMS` in the stamp directory (`sha256sum -c SHA256SUMS` there). The newest 14 per school are kept (`--keep N`).
`fulltext-push/evidence-backup.slurm` is the automatic one: a light self-restarting Slurm job in the shape of `disk-guard` (1 CPU, 1 G, 59 min, restarts at USR1),
`atlas submit fulltext-push/evidence-backup.slurm`; every 15 min it backs up each flagged school whose newest backup is over 24 h old, and skips while the share
has under 50 GB free. Its log: `fulltext-push/logs/evidence-backup-<jobid>.out`. After a large `record` batch run `backup` by hand too.
**Restore:** `bin/atlas evidence-store restore <school> --from-file archive/evidence-store-backups/<stamp>/<school>-evidence.sqlite` verifies the SHA256SUMS line and
`integrity_check`, refuses when the live store has more logged writes than the backup (`--force` overrides), keeps the live file as `evidence.sqlite.pre-restore-<stamp>`,
and copies the backup in. Then `check <school>`; if the JSON view differs, `sync <school>` and commit it. Never restore by copying over the store while a `record` runs.

### Shared files: a school's slice (R3b, 2026-11-17)
`[evidence] shared = "store"` (needs `source = "store"`; default `"json"`) sources the school's rows in the shared reviewed files (`hierarchy/reviewed/*.json`:
`census-overrides.json`, `student-corrections.json`, `home-departments.json`, `zero-paper-review.json`, ...) from its store. Other schools' rows in the same files stay
JSON-sourced and editable by hand; the shared files remain tracked in git.
- The store holds the slice as `scope = 'shared'` layers (one per shared file that is a list of items with a `school` field or a school-keyed map, also when the school has
  0 rows today, so a first row can be recorded). `adopt-shared <school>` (once, before the flag is set; refused afterwards) snapshots the school's current rows from the shared files.
- **Slice patch exporter** (`sync` writes it, `check`/hook/doctor compare it): the current shared file is parsed, only the school's rows are replaced, the file is written in
  its own detected dump style, and content that did not change returns the original bytes (byte-identical). List files: the school's items are replaced in place by seq, new rows
  go right after its last item; school-keyed maps: the school's section is rebuilt (new school key appended). Deleting a row is not supported (supersede it).
- Record with `bin/atlas evidence-store record <school> --shared --layer student-corrections.json --record '{...}' --source ... --decided-by ...` (`find` the same way), then `sync <school>`
  (rewrites the school's own files and its slices of the shared files) and commit. The hook now also looks at staged `hierarchy/reviewed/*.json`: only the flagged school's slice is
  compared, so an edit to another school's rows is not refused. Shared files whose rows do not name a school per item (`issued-id-review-20261108.json`, `cs-venues.json`,
  `status-packages.json`, ...) are not sliceable and stay JSON-sourced for everyone.
- Overlay builds of a school with `shared = "store"` patch its slices into the root's own shared files.
- **Result (2026-11-17, Michigan).** `adopt-shared`: 388 rows (census-overrides 90, home-departments 288, zero-paper-review 10; student-corrections, student-identity-review,
  student-name-candidates, chain-reasons have 0 Michigan rows today). All 7 shared files patch back byte-identical (`check` clean, `sync` changes nothing). Build pair (Slurm 32393456 control,
  32393457 then 32393576 store-sourced incl. slices, 13-15 min): `pis.json`, `students.json`, `lab_papers.jsonl.gz`, `student_papers.jsonl.gz` byte-identical; `report.json` differs only in `builtAt`,
  echoed paths and the provenance hash of `home-departments.json` (another session edited that file in the main tree between the two builds; the store-sourced build read the newer bytes).

### Princeton, the second store-sourced school (R3b, 2026-11-17)
`schools/princeton.toml`: `source = "store"`, `shared = "store"`, `unmanaged = ["student-recall-check*.json"]`. `unmanaged` (`school_config.evidence_unmanaged`) lists file-name patterns a
store-sourced school keeps out of its store and its guard: tool-regenerated audit samples (`student_recall.py` rewrites the recall check and its dated copies in the main tree; a
guard on them would refuse every regeneration). Overlays copy them from the root. Princeton's store: 2,081 rows over 25 files (5 of them are git-ignored inputs in the main tree, `labpage-input.json`,
`labpage-evidence.json`, `gap-input.json`, `few-students-input.json`, `cs-related-home-departments.json`: the store now keeps them, `sync` materialises them in a checkout, they are never committed)
plus 79 rows in the shared slices (census-overrides 28, home-departments 43, student-name-candidates 3, student-identity-review 2, zero-paper-review 2, chain-reasons 1).
Build pair (Slurm 32393765 control, 32393766 store-sourced, 3 min each): `pis.json`, `students.json`, `lab_papers.jsonl.gz`, `student_papers.jsonl.gz` byte-identical; `report.json` differs only in `builtAt` and `provenance.at`.
Import reads the main tree's files; the first import also saw the dirty student-recall-check, which is why those files became `unmanaged`.

### Record a decision (a worker, Michigan or Princeton)
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
1. A reader may read the store directly (`census_overrides.section`, `pi_hierarchy` reviewed inputs) instead of the exported JSON view.
2. Writers (stage tools, `excluded_audit.py`) call `record()` instead of editing files, school by school.
3. Split rank/unit/period/identity facets into their own rows once the readers use claims rather than records.
