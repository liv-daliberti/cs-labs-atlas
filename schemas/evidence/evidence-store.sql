-- Per-school evidence store (docs/EVIDENCE-STORE.md). One SQLite file per school: <store dir>/<school>/evidence.sqlite
-- (the schools' shared reviewed files that name no school live in the store "_shared"). Phase 1: a lossless import of the
-- reviewed JSON files; nothing reads the store yet. `record` is the truth; the claim columns are an index projected from it
-- (tools/evidence_store.py verify recomputes them).
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

-- One row per reviewed file ("layer"): what is needed to write the file's JSON again from its rows.
CREATE TABLE IF NOT EXISTS layer (
  layer_id    INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,      -- file name, e.g. census-additions.json
  scope       TEXT NOT NULL CHECK (scope IN ('school', 'shared')),
  skeleton    TEXT,                      -- JSON of the file with every container replaced by null; NULL when the root is a container
  containers  TEXT NOT NULL,             -- JSON [{"path": [key...], "kind": "list"|"map"|"map2"|"doc"}]; path [] = the root
  key_order   TEXT,                      -- JSON list of the root keys in file order (dict roots)
  style       TEXT,                      -- JSON {"indent", "ascii", "compact", "sort", "newline"} that reproduces the file bytes, or NULL
  sha256      TEXT NOT NULL,             -- of the original file bytes
  nbytes      INTEGER NOT NULL,
  source_path TEXT NOT NULL,             -- repo-relative path the file was read from
  verbatim    TEXT,                      -- original text, only when the file could not be decomposed (parse error, duplicate keys)
  layout_text TEXT                       -- original text when no standard dump style reproduces the bytes (hand-formatted file); written back only while the rows still equal it
);

-- One row per decision (a list item, or a map entry). `seq` is the position in the container (a shared file is spread over
-- several schools' stores; seq orders it again).
CREATE TABLE IF NOT EXISTS evidence (
  id           INTEGER PRIMARY KEY,
  school       TEXT NOT NULL,
  layer_id     INTEGER NOT NULL REFERENCES layer(layer_id),
  container    INTEGER NOT NULL,         -- index into layer.containers
  seq          INTEGER NOT NULL,
  entry_key    TEXT,                     -- map containers: the key (map2: the outer key, usually the school)
  sub_key      TEXT,                     -- map2: the inner key (usually the person); NULL for a whole-section row
  person_key   TEXT,                     -- the person the decision is about, as the file names them
  claim_kind   TEXT NOT NULL,            -- vocabulary in evidence-row.schema.json
  facets       TEXT,                     -- JSON list of the other claim kinds the record carries (a census override holds several)
  value        TEXT,                     -- JSON: the decision-bearing fields (decision, rank, unit, period, exclusion reason ...)
  source_url   TEXT,
  source_date  TEXT,                     -- capture or fetch date as the record states it
  source_kind  TEXT,
  decided_by   TEXT,
  decided_at   TEXT,
  reviewed_by  TEXT,
  review_ref   TEXT,
  supersedes   TEXT,
  record       TEXT NOT NULL,            -- the original entry as JSON (compact, key order kept): lossless
  UNIQUE (layer_id, container, seq, sub_key)
);
CREATE INDEX IF NOT EXISTS evidence_person ON evidence (school, person_key);
CREATE INDEX IF NOT EXISTS evidence_kind ON evidence (claim_kind);
