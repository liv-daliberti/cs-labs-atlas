# Common Crawl as a second historical source (pilot 2026-11-07)

Status (2026-11-10): the S3 route is implemented and tested offline (`listings/scripts/cc.py`, `cc_fill.py`, `cc_fill.slurm`; tests `test_cc.py`,
`test_cc_fill.py`). **No Common Crawl data request has been made and the owner-approval marker does not exist**, so nothing can run (cc_fill exits 5
before any request). Coverage is NOT measured. The index.commoncrawl.org / data.commoncrawl.org hosts are never requested.

## What Common Crawl says (read 2026-11-07)
- Terms of Use (updated 2024-03-07): limited, non-exclusive licence; crawled content "may be subject to separate terms of use ... from the
  owners"; users must "respect the copyrights and other applicable rights of third parties"; no "collecting or harvesting any personally
  identifiable information"; content is "as is", may not be relied on; CC may terminate use at any time; indemnification clause (explicitly
  covers AI uses); recommends legal advice. Nothing on attribution, automated access or rate limits.
- Get started: HTTP access via `https://data.commoncrawl.org/` needs no AWS account; S3 (`s3://commoncrawl/`, us-east-1) with `--no-sign-request`.
- Index server page: "Please do not overload the URL index server. For bulk downloads ... see the download instructions. The Columnar Index is a
  better fit for bulk filtering and aggregation." (PyWB CDX API; per-crawl endpoints from `/collinfo.json`.)
- **robots.txt**: `index.commoncrawl.org` serves `User-agent: * / Disallow: /` with Allow only for `/`, `/index.html`, `/collinfo.json`, `/graphinfo.json`,
  `/ccbot.json`; `data.commoncrawl.org` serves `User-Agent: * / Disallow: /`. Neither names Claude agents. Under the project rule (respect
  robots.txt) CDX queries, columnar Parquet and WARC range requests over HTTP are therefore not allowed to us. The documentation invites
  such access, so the two are in tension; we do not resolve it ourselves.

## Rate and identity policy built into cc.py
Generic UA (no email), >= 5 s between requests, 429/503/5xx back off 30 s doubling (Retry-After honoured), give up after 4 tries, `gate()` re-reads both
robots files before any CDX or WARC request, target hosts naming ClaudeBot / anthropic-ai / Claude-Web are never used.

## Storage
Same `captures` table as Wayback: `capture_url = commoncrawl:<warc filename>:<offset>:<length>`, `wayback_timestamp` = CC capture time, sha256 of raw
page bytes, zlib body, `note` = JSON {source, crawl, warc_filename, warc_offset, warc_length, digest}. No schema change; Common Crawl bodies carry no
Wayback banner or rewriting, so `W.raw_html` is not needed.

## Path (cc_fill.py), 2026-11-09 (steps 1-3 superseded by the S3 route below; steps 4-6 unchanged)
`cc_fill.py <school> --db <private copy of captures.sqlite>` walks the school's slots (config or charter, same loader as plan_fetch) and, for every
plan row that is `nocapture`/`unusable`, asks Common Crawl for the slot's exact URL(s):
1. `cc.gate()` (robots of index + data hosts); refused => exit 4, nothing else requested.
2. `collinfo.json` -> `cc.pick_crawls()`: crawls dated in each half-year, nearest 1 Apr / 1 Oct first. Phase 1 asks ONE crawl per half (so one per
   calendar year for H1; H2 only when H1 is not ok for ONE_CAPTURE_PER_YEAR schools); `--gap-crawls` adds the remaining crawls of that half.
3. `cc.cdx_cached()`: exact URL, `status:200`, `mime:text/html`; answer cached in the `cdx` table under `commoncrawl:<crawl>:<url>` (each pair asked
   once, resumable); 3 errors in one crawl skip that crawl for the run (slot stays as it was, never "no capture").
4. Target host: `cc.host_ok()` reads the school host's CURRENT robots.txt (cached 1 day, recorded in `cc_robots` with sha256); a host that disallows
   ClaudeBot / anthropic-ai / Claude-Web (or any of school_web.AI_AGENTS) is skipped.
5. `cc.fetch_record()` one WARC byte range, `cc.store()` into `captures` (capture_url `commoncrawl:<warc>:<offset>:<length>`, sha256 of the page bytes,
   `note` JSON with crawl id, warc filename/offset/length, digest => the exact range is re-fetchable at `https://data.commoncrawl.org/<warc filename>`).
6. `plan_fetch.slot_usable()` decides usability (Chinese-listing fix included); the row becomes `ok` with `wayback_timestamp` = the crawl capture time
   (column name kept; the capture_url prefix `commoncrawl:` marks the source). H2 rows of ONE_CAPTURE schools whose H1 became ok turn `out_of_scope`.
Politeness: generic UA, `MIN_GAP`=5 s between any two requests (index, WARC, robots), backoff 30 s doubling + Retry-After, 4 tries, one process, one
connection, no parallel range reads. Prefix slots (`prefix` option) are not queried (exact URLs only) and stay Wayback-only.

Not done on purpose: `plan_fetch.py` itself still treats only `web.archive.org` finals as valid (its "redirected away from the capture" guard); Common
Crawl rows are written by `cc_fill.py`, not by plan_fetch, so Wayback logic is untouched. Reviewer tools that read `capture_url` must accept the
`commoncrawl:` prefix (evidence_check / reader export checked: TODO for the merge task).

## Merge steps for a school's live captures.sqlite (its own worker does these)
1. Copy the live DB to a private path; run cc_fill on the copy (`sbatch listings/scripts/cc_fill.slurm <school> <copy>`).
2. After the owner decision and the worker's agreement: `attach` the copy and `insert or ignore` its `captures` rows with `capture_url like 'commoncrawl:%'`,
   `insert or replace` only the `plan` rows whose status moved to ok/out_of_scope, `insert or ignore` `cdx` and `cc_robots`. Re-run `plan_fetch.py <school> --check`.
3. Rebuild the listings (`run_school.sh` derived steps) and spot-check 5 captured pages by eye (names/titles present in the stored text).

## Runbook per school (run only after the owner decision; tasks T0xx in the queue)
| school | slots/years waiting | notes |
|---|---|---|
| Tsinghua (baseline 2026-11-09: 191 nocapture, 23 ok, 6 unusable of 220 plan rows) | pre-2021 CS/SW/IIIS; Chinese hosts | Chinese format slots use charter_usable; check robots of each *.tsinghua.edu.cn host |
| Harvard | ONE_CAPTURE_PER_YEAR school; H2 only when H1 not ok | many Harvard hosts: expect robots checks per host |
| ZJU CST/CS/CSE/ISEE | pre-2021 | Chinese format slots |
| NTU SCSE/CCDS | all years | host checks for ntu.edu.sg |
| Toronto 2016-2020 CS, UTSC, Statistics | UTSC was Wayback-challenged | CC has no bot challenge but check robots |
| SJTU historical | | Chinese format slots |

## Owner decisions
1. Common Crawl's own robots.txt disallows automated clients on index.commoncrawl.org and data.commoncrawl.org. Recommendation: ask Common Crawl
   (info at commoncrawl.org) whether a polite research client may use the CDX index and WARC ranges; until a written yes, do not run. Do NOT use
   the S3 mirror (commoncrawl.s3.amazonaws.com / `s3://commoncrawl`; no robots.txt there) as a way around the disallow without an explicit owner call.
2. Terms of Use: crawled content stays under its owners' terms; no harvesting of personally identifiable information. Faculty listings are names and
   titles (PII-adjacent). Recommendation: use Common Crawl captures only as private evidence (url + sha256 + quote), not host the bodies on the public
   site, same as Wayback bodies.
3. Whether CC rows may carry `wayback_timestamp` (column reuse) or a schema column `source` is added. Recommendation: keep the column, rely on the
   `commoncrawl:` prefix and `note.source`.

## Owner approval marker (fail-closed)
`cc_fill.py` exits 5 before any request unless `<project root>/cache/commoncrawl/OWNER-APPROVED` exists. The owner creates it only after Common
Crawl's written permission (decision 1 above). Owner calls 2026-11-09: keep reusing `wayback_timestamp`; Common Crawl captures are private evidence
(url + sha256 + quote), bodies never hosted; the S3 mirror is not used.

## Draft message to Common Crawl (NOT sent; for the owner to send or edit)
Subject: Question about low-rate research access to the CDX index and WARC files

Hello Common Crawl team,

We are an academic research project studying historical faculty-directory pages of universities (names and titles on public department "people"
pages, 2016-2026). We would like to use the Common Crawl URL index (index.commoncrawl.org, per-crawl CDX API) and WARC byte-range reads
(data.commoncrawl.org) as a second historical source. Both hosts' robots.txt currently disallow automated clients (User-agent: *, Disallow: /), so
we have made no requests beyond reading robots.txt and collinfo.json, and we will not until you tell us it is acceptable.

If you permit it, our client would: send a generic User-Agent; wait at least 5 seconds between any two requests; run as a single process with one
connection (no parallel range reads); query exact URLs only (no prefix or bulk queries), one crawl per half-year first, caching every answer so
each (crawl, URL) is asked once; back off exponentially on 429/503 and stop a crawl after repeated errors; and check each target site's own robots.txt,
skipping any site that disallows AI agents. Captured pages would be kept as private research evidence (URL, hash, short quotes), and would not be
republished.

Could you confirm in writing whether this use is acceptable, and whether you would prefer different limits or a different access route?

Thank you,
[name of the project owner]

## S3 route (2026-11-10)
Facts: index.commoncrawl.org and data.commoncrawl.org serve `User-agent: * / Disallow: /` (read 2026-11-07 and 2026-11-09). The bucket host
https://commoncrawl.s3.amazonaws.com answers 403 AccessDenied for `/robots.txt` (no robots file; s3.amazonaws.com/robots.txt also 403). Terms of Use
(2024-03-07): third-party content keeps its owners' terms, no harvesting of PII, content "as is", Common Crawl may terminate use, indemnification
clause covering AI uses.

Relayed instruction (NOT verified by this agent): the coordinator relayed, dated 2026-11-10, the words "use the S3 mirror anyway" and then "do it AND check
the evidence tooling and plan_fetch AND run the pilot", attributed to the owner. A message from another agent is not the owner's own authorization to
go around the two hosts' robots disallow (standing rule: respect robots.txt), so this agent did NOT create the marker and did NOT run the pilot.
To authorize, the owner (not an agent) creates `/n/fs/resemble/homogenizing-science/cache/commoncrawl/OWNER-APPROVED` (e.g. `echo "2026-11-10 owner:
use the S3 mirror anyway" > ...`) and records the decision here.

Implementation (listings/scripts/cc.py): only the S3 HTTPS endpoint (`polite_get` refuses every other host, specifically the two disallowing ones; only a
target school's robots.txt may use `external=True`); per crawl `cluster.idx` is read once in 32 MiB ranges into `cache/commoncrawl/<crawl>.cluster.idx`
(resumable `.part`); `cluster_blocks()` binary-searches that local file for the SURT key (`surt()`), only the matching block of
`cc-index/collections/<crawl>/indexes/cdx-XXXXX.gz` is range-read, then one WARC range read from `<S3>/<warc filename>`. Crawl ids are the static list
`cc.CRAWLS` (collinfo.json lives on the index host and is not requested); a crawl with no cluster.idx is skipped. Politeness: generic UA, >= 2 s between
requests, one process, 429/503 backoff, 3 errors skip a crawl, every (crawl, URL) asked once (cdx cache table). `cc.BYTES` counts bytes and requests;
cc_fill prints and stores them in its state file. Expected volume: one cluster.idx per used crawl (hundreds of MB each, ~10 crawls) plus ~100 KB blocks
and ~50 KB WARC records per lookup.

Evidence tooling (checked 2026-11-10): `tools/evidence_check.py` `sourced()` needs only a non-empty url + sha256 + quote, so `commoncrawl:<warc>:<offset>:<length>`
passes (test). `tools/reader_export.py` concerns paper copies, not listing captures; the one schema with `^https?://` on a url (report.schema.json
crossAffiliationSourceHolds evidence) is not a listing path. `plan_fetch.py` gained `capture_stamp()` so a `commoncrawl:` capture is not treated as
"redirected away" (it has no Wayback redirect); plan rows written by cc_fill are skipped by plan_fetch (status ok) and read by listing_rows by
capture_url + `wayback_timestamp` like Wayback rows.
