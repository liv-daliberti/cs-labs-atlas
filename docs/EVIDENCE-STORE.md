# Evidence store (phase 1 of the backend refactor, 2026-11-17)

One SQLite file per school holds every per-person decision with its source, replacing over time the scattered reviewed-JSON
layers (`docs/REVIEWED-INPUTS.md`). Phase 1 is a **lossless import and an exporter**: no builder reads the store, no output
changes. Owner rule: container formats, not many small files (hence SQLite, not a JSON file per decision).

## Files
| File | What |
|---|---|
| `schemas/evidence/evidence-store.sql` | the tables (`meta`, `layer`, `evidence`); the tool creates stores from this file |
| `schemas/evidence/evidence-row.schema.json` | the claim columns and the `claim_kind` vocabulary |
| `tools/evidence_store.py` | `import`, `export`, `verify`, `overlay`, `coverage` |
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
  (see `OVERNIGHT-LOG.md` for the comparison table).
- Weak projections (the record is intact, only the index is thin): 41k rows are plain `evidence` (lab pages, directories, websites),
  2.5k `other`, 2.5k `review_note` (legacy `pending_*`); 817 `evidence` and 677 `other` rows have no person key (whole-document rows).

## Next phases (not done)
1. Readers fall back to the store behind a flag (`census_overrides.section`, `pi_hierarchy` reviewed inputs), output compared per school.
2. Writers (stage tools, `excluded_audit.py`) append rows with `decided_by`/`review_ref` and `supersedes` instead of editing files;
   the reviewed JSON files become exports.
3. Split rank/unit/period/identity facets into their own rows once the readers use claims rather than records.
