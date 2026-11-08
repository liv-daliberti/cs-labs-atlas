# Common Crawl as a second historical source (pilot 2026-11-07)

Status: module `listings/scripts/cc.py` + `tests/test_cc.py` written; **no Common Crawl request beyond robots.txt, the front page and
collinfo.json was made**, because both data hosts disallow automated clients (below). Owner decision pending.

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
