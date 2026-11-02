# OpenAlex bulk snapshot instead of the API (ROADMAP #24, P0-1): plan

Status 2026-11-01: **plan only**. No job has run and no code changed. Figures marked (verify) come from OpenAlex's public
documentation as known today and are confirmed by the probe in step 0 before anything is built.

## 1. Why
The shared key allows 10,000 credits a day, split between this work and the lab-page audit. It throttles the sweeps
(`tools/oa_sweep.py`, one cursor page of 200 works per call), `fulltext-push/oa_refresh.py` and the ledger's OpenAlex check
(50 ids per call, 7-day freshness), the reader's licence lookups and the lab-page resolution. The snapshot is free, has no
daily quota and is the same data the API serves.

## 2. What we need from it
Works (the large part) and authors, filtered to what the pipeline reads.
- **Works** matching either key:
  - an authorship institution `lineage` containing a charter id: the `[ids]` `openalex` and `openalex_related` of the 7 charters
    (Princeton I20089843, Michigan I27837315 plus related I4210114445, ... exactly as `schools/*.toml`), minus each
    charter's `openalex_excluded` (Michigan-Dearborn, Michigan-Flint); or
  - an authorship author id in our PI and student author sets (`hierarchy/<school>/pis.json`, the `pi-works.sqlite` author ids):
    papers of our people written while at another institution, which `pi-works` holds today. Keep this set as a file the
    filter reads, so adding a PI never needs a re-download of everything (it needs a pass over the stored snapshot only).
- **Work fields** (the union of today's `SELECT` constants, so consumers get the dict they get from the API):
  `id, doi, title, publication_year, publication_date, type, authorships` (author id, display name, ORCID, position,
  institutions with ids and lineage, raw affiliation strings), `ids` (doi, pmid, pmcid, mag), `primary_location`, `locations`,
  `best_oa_location`, `open_access` (is_oa, oa_status, oa_url), `biblio`, `language`. The oa_refresh and ledger checks read
  locations (host, version, license, pdf_url, source type); the reader licence lookup reads `locations[].license` and
  `best_oa_location`. Not kept: abstract_inverted_index, concepts, topics, referenced_works lists, counts_by_year, related works
  (large, unused). Add a field later by re-running the filter pass; the plan keeps the stream cheap to repeat.
- **Authors** (small): `id, display_name, orcid, last_known_institutions, affiliations (institution, years), works_count`, only
  authors seen in a kept work's authorships or in our author sets. This feeds the identity checks and the departed-faculty review
  (ROADMAP #26).
- **Institutions** (tiny, all of them): needed to resolve lineage ids.
- Types: keep all, but tag `type`; readers already drop datasets (Michigan's 434,618 ENCODE records of 2022 are the big case, so
  **drop `type == dataset` with a DOI prefix 10.17989 at the filter** to save about 1 GB; everything else stays).

## 3. The source
- Public S3 bucket `s3://openalex` (us-east-1), no credentials, also reachable over HTTPS (`https://openalex.s3.amazonaws.com/...`).
  Layout (verify): `data/works/updated_date=YYYY-MM-DD/part_NNN.gz` (gzipped JSON Lines, one work per line),
  `data/authors/...`, `data/institutions/...`, `data/works/manifest` with per-part sizes and record counts.
- Size (verify): works are roughly 250 million records, about 300 GB gzipped and 1.5-2 TB uncompressed; authors about 90-100
  million, tens of GB. The manifest gives exact byte counts; step 0 reads only the manifests (a few KB).
- The host has no `aws` CLI; use HTTPS ranges/streams from Python (`requests`, already in the env), or boto3 with an unsigned config
  if the env has it. Do not install system-wide.

## 4. How to stream and filter without landing the dump
Never write the raw snapshot to shared storage.
1. Each Slurm worker takes a disjoint set of partitions from the manifest and streams one part at a time over HTTPS through
   `gzip` (decompress on the fly, no temp file).
2. **Pre-filter on the raw bytes before parsing**: a line is kept for JSON parsing only if it contains one of the charter
   institution ids (`"I20089843"` and so on) or one of our author ids as a byte substring. This rejects well over 95% of lines at
   memory speed and avoids parsing 1.5+ TB of JSON. A false positive costs one parse; there are no false negatives, because ids
   appear in the line verbatim. After parsing, the exact lineage / author test decides.
3. Kept works are projected to the field list above and appended to a **job-local `/tmp` SQLite part** (zlib JSON body, as
   `pi-works.sqlite` does), one part per array task. The merge job runs on another node and cannot read `/tmp`, so when a task
   has finished its partitions it **copies its one finished part to the SCRATCH slot** (`P.SCRATCH / 'openalex-<snapshot-date>' /
   part-NN.sqlite`, a single sequential write of a few hundred MB; 16 files in total, not a small-file load), then writes
   `part-NN.done` (the part's byte count and sha256). A crashed task leaves no `.done`, and a retry rewrites its part.
4. The merge job (after `afterok` on the array) checks every `.done`, attaches the 16 parts and writes **one SQLite file** per
   snapshot to the project, with sequential block writes (>= 64 KiB pages, large transactions), then indexes and
   `VACUUM`. **After the merge verifies its row counts against the parts, it removes the 16 parts and `.done` files**
   (`tools/scratch.py` rules, logged in `manifest.json`). No per-work files and no per-partition files on `/n/fs`.
5. Authors and institutions go in the same file as separate tables.
Layout: `snapshots/openalex/<snapshot-date>/openalex.sqlite` (resolved through a new `atlas_paths` data slot, never a literal
path) plus `manifest.json` (snapshot date, the manifest checksums, id sets used, counts, code commit).
Tables: `works(id TEXT PRIMARY KEY, doi, year, type, title, body BLOB)`, `work_inst(work_id, inst)` for each lineage id found,
`work_author(work_id, author_id)`, `authors(id, body BLOB)`, `institutions(id, body BLOB)`, plus indexes on `doi`, `year`,
`inst`, `author_id`. Indexes make the sweep's "lineage = X, year = Y" and the ledger's "id / doi" lookups point queries.
(Parquet is the alternative if pyarrow is added to the env; it is not there today and SQLite fits the existing readers.)

## 5. Expected size and room
- Kept works: the seven lineages plus our people's other-institution papers, about 2-4 million works after the dataset drop
  (Michigan including Michigan Medicine and Stanford are the largest). At about 1-2 KB compressed per projected work the
  store is **about 4-8 GB**, authors under 1 GB. The existing per-school `openalex-sweep.sqlite` files already total about 1 GB
  for the same projection and a narrower window, which bounds the estimate.
- Room: `df -h /n/fs/resemble` shows 12 TB, 8.9 TB used, 3.2 TB free (74%) on 2026-11-01, so one store is nothing; keep the
  latest two snapshots (the older one for rollback), the rest are deleted by a documented step, never by hand.
- Job-local scratch: each worker's part is a few hundred MB on `/tmp` until it is copied to SCRATCH; the SCRATCH parts total
  about the final store's size (4-8 GB) until the merge removes them. Request CPU nodes with enough local `/tmp` free or flush
  the part when it reaches 2 GB (then a task writes a few numbered parts, still tens of files, not thousands).

## 6. Shared-storage I/O (host rules)
- Reads from S3 are network, not `/n/fs`. Writes to `/n/fs`: one file, large sequential blocks, in a single merge step, which is the
  pattern the host rules ask for. No small-file storm, no directory walk, no `du`/`find` over the shares.
- Never traverse `/n/fs`; the snapshot directory is a known path from `atlas_paths`.
- Network politeness to AWS: a bounded number of concurrent streams (say 8-16), no requests to the OpenAlex API at all in the
  build.

## 7. Run time and effort on Slurm
- Download: about 300 GB over HTTPS. At 100-200 MB/s per node, with 8 workers, about 1-2 h wall.
- CPU: with the byte pre-filter the cost is gunzip (about 150-250 MB/s per core), so 1.5-2 TB uncompressed over 8 cores is
  about 1.5-3 h; parse only the few percent that pass. Plan: one `atlas submit` array of 16 tasks (2 CPU, 8 GB, 4 h each,
  `mltheory`, `--exclude=node302`), then a single merge job (1 CPU, 16 GB, 1 h). `sbatch --test-only` first, never on
  "Preempts:". Total wall about 4-5 h, CPU about 60-80 core-hours.
- Engineering: about 2-3 days. The filter job and merge, `atlas_paths` slot, the reader library (`oa_snapshot.py`: `works_by_lineage`,
  `work(id|doi)`, `authors`), a manifest/refresh command, tests on a fixture of 3 hand-made part files, the equivalence check.

## 8. Refresh schedule and fallback
- OpenAlex republishes the snapshot on a periodic cadence (monthly or so; verify the current one in step 0). Refresh monthly
  with a job that diffs the manifest: only partitions whose `updated_date` is newer than the stored snapshot's are read
  (the snapshot is organised by `updated_date`), merged by `id` into a new file; the previous file is kept.
- The store records `snapshot_date` per row. A lookup returns the row and its date; a caller that needs fresher than
  `max_age_days` (the ledger's 7-day OpenAlex rule, relaxed to 35 days for snapshot rows) asks the API for just that id.
- **Fallback order:** snapshot, then the API key (budget-guarded as today, `oa_refresh.get`), then "missing". A work absent from
  the snapshot but present on the API is a real case (new since the snapshot): the API result is kept in the existing
  `raw/openalex_works.jsonl` cache as now.
- Anything the snapshot cannot do stays on the API: search by title, `from_updated_date` freshness, and works newer than the
  latest snapshot.

## 9. Code paths, in the order they switch
1. `tools/oa_sweep.py` (the biggest consumer: cursor paging by lineage and year): read `works_by_lineage(inst, year)` from the
   snapshot; the API path stays behind a flag. First proof target: one school, equal output to its existing
   `openalex-sweep.sqlite`.
2. `fulltext-push/oa_refresh.py` and `ftp_common.oa_bodies`/`fetch_oa_bodies` (work records by id): snapshot first.
3. The ledger's OpenAlex check (`unavailable_ledger.py`, 50 ids per call): snapshot rows within the age rule, the API for the rest.
4. Reader licence lookup (`tools/reader_export.py` and the candidate licence fields): `locations[].license` from the snapshot.
5. Lab-page resolution and `labpage_recover.py`, `pi_fulltext_affiliation.py`, `dblp_recover.py`, `oa_identity_school.py`: author and
   work lookups by id and by author, moving from `api.openalex.org` calls to the store.
Each switch adds a `source` field to what it records (`openalex_snapshot:<date>` or `openalex_api`) so provenance stays honest.

## 10. Proof of equivalence (before any switch is trusted)
On one school (EPFL or Princeton: small), run the sweep from the snapshot and compare with the API-built
`openalex-sweep.sqlite`: work-id sets by year (expected differences only for works created or merged since, listed), then field
equality on a sample of 1,000 works for every projected field; record the report under `review-*/` and in the school's STAGE
notes. Differences that are real (OpenAlex data changed) are listed, not hidden.

## 11. Risks
- The snapshot lags the API by up to a cycle: handled by the age rule and API fallback above.
- OpenAlex may change the snapshot format or location: step 0 reads the manifest and the build fails closed on an unknown layout.
- Pre-filter by substring depends on ids appearing as full ids in the JSON (`https://openalex.org/I...`): the fixture test covers it.
- Disk: keep two snapshots only.

## 12. Steps after the data-layout move
0. Probe the manifests (read-only, tiny) and record the real size and cadence here.
1. Add the `atlas_paths` slot and the reader library with tests on fixtures.
2. Submit the filter array and the merge with `atlas submit`.
3. Switch `oa_sweep`, run the one-school equivalence, report.
4. Switch the other paths in the order of section 9.
