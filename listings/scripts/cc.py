"""Common Crawl as a second historical source beside the Wayback Machine (S3 route, 2026-11-10).

Read docs/COMMONCRAWL.md first.  Gates this module enforces:

- ONLY the public S3 HTTPS endpoint https://commoncrawl.s3.amazonaws.com is requested for Common Crawl data (polite_get refuses every other host for
  Common Crawl paths, in particular index.commoncrawl.org and data.commoncrawl.org, whose robots.txt disallow automated clients).  Using the bucket
  instead is an OWNER decision (docs/COMMONCRAWL.md); gate() refuses unless the owner-approval marker file exists, checked before any request.
- Lookup: per crawl the cluster.idx is read once (cached under cache/commoncrawl/), the SURT-key block located by binary search on the local file,
  and only that block range-read from cc-index/collections/<crawl>/indexes/cdx-XXXXX.gz; then one range read of the WARC record.
- A target host whose robots.txt names ClaudeBot / anthropic-ai / Claude-Web (school_web.robots_decision) is never used from Common Crawl either.
- Generic User-Agent, no email.  One request per MIN_GAP seconds, 503/429 back off exponentially (Retry-After honoured), give up after MAX_TRIES.
- Records are stored in the school's captures.sqlite `captures` table like Wayback captures: sha256 of the raw page bytes, zlib body, provenance
  (source, crawl, WARC filename, offset, length) in `note` as JSON; capture_url is `commoncrawl:<filename>:<offset>:<length>`.

Network functions take an injectable `http` callable so tests never touch the network: http(url, headers) -> (status, headers, body).
"""
import datetime
import os
import gzip
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

UA = 'Mozilla/5.0 (compatible; faculty-listing-archival-research/1.0)'
S3 = 'https://commoncrawl.s3.amazonaws.com'
S3_HOST = 'commoncrawl.s3.amazonaws.com'
FORBIDDEN_HOSTS = ('index.commoncrawl.org', 'data.commoncrawl.org')
MIN_GAP = 2.0
BYTES = {'n': 0, 'requests': 0}
MAX_TRIES = 4
SOURCE = 'commoncrawl'
_last = [0.0]


class CCRefused(RuntimeError):
    """Common Crawl (or the target host) must not be used; the caller falls back to pending, never to 'no capture'."""


def _http(url, headers):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity', **headers})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b''


def polite_get(url, headers=None, http=None, external=False):
    """One request with a minimum gap and back-off on 429/503/5xx; returns (status, headers, body) or raises CCRefused after MAX_TRIES.
    Common Crawl data comes only from the S3 bucket host; `external=True` is for a target school host's robots.txt only."""
    host = urllib.parse.urlsplit(url).netloc
    if host in FORBIDDEN_HOSTS or (not external and host != S3_HOST):
        raise CCRefused(f'{host} is not an allowed Common Crawl host (only {S3_HOST})')
    http, sleep, now = http or _http, time.sleep, time.time
    delay = 30.0
    for _ in range(MAX_TRIES):
        wait = _last[0] + MIN_GAP - now()
        if wait > 0:
            sleep(wait)
        _last[0] = now()
        st, hd, body = http(url, headers or {})
        BYTES['requests'] += 1
        BYTES['n'] += len(body or b'')
        if st in (429, 503) or st >= 500:
            ra = {k.lower(): v for k, v in hd.items()}.get('retry-after', '')
            sleep(float(ra) if ra.isdigit() else delay)
            delay *= 2
            continue
        return st, hd, body
    raise CCRefused(f'{host} kept answering 429/5xx; backing off')


def project_root():
    here = os.path.abspath(__file__)
    if '/worktrees/' in here:
        return here.split('/worktrees/')[0]
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(here))))


def approval_marker():
    """The owner creates this file to authorize the S3 route (docs/COMMONCRAWL.md); without it nothing is requested."""
    return os.path.join(project_root(), 'cache', 'commoncrawl', 'OWNER-APPROVED')


def cache_dir():
    return os.path.join(project_root(), 'cache', 'commoncrawl')


def robots_allows(robots_txt, path, agent=UA):
    import urllib.robotparser
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots_txt.splitlines())
    return rp.can_fetch(agent, path)


def gate(http=None):
    """Raise CCRefused unless the owner-approval marker exists (fail-closed, before any request)."""
    if not os.path.exists(approval_marker()):
        raise CCRefused(f'no owner approval marker {approval_marker()}')


def host_allowed(robots_status, robots_body, url):
    """The target host's own robots verdict (AI-named opt-out means Common Crawl copies of it are not used either)."""
    import school_web as W
    ours, ai, _ = W.robots_decision(robots_status, robots_body, url)
    return ours and ai


# CC-MAIN crawl ids 2016-2025 (static: collinfo.json lives on index.commoncrawl.org, which is never requested).  An id whose cluster.idx is absent
# (HTTP 403/404) is skipped at run time, so a wrong guess costs one request.
CRAWLS = ('CC-MAIN-2016-07 CC-MAIN-2016-18 CC-MAIN-2016-22 CC-MAIN-2016-26 CC-MAIN-2016-30 CC-MAIN-2016-36 CC-MAIN-2016-40 CC-MAIN-2016-44 CC-MAIN-2016-50 '
          'CC-MAIN-2017-04 CC-MAIN-2017-09 CC-MAIN-2017-13 CC-MAIN-2017-17 CC-MAIN-2017-22 CC-MAIN-2017-26 CC-MAIN-2017-30 CC-MAIN-2017-34 CC-MAIN-2017-39 '
          'CC-MAIN-2017-43 CC-MAIN-2017-47 CC-MAIN-2017-51 CC-MAIN-2018-05 CC-MAIN-2018-09 CC-MAIN-2018-13 CC-MAIN-2018-17 CC-MAIN-2018-22 CC-MAIN-2018-26 '
          'CC-MAIN-2018-30 CC-MAIN-2018-34 CC-MAIN-2018-39 CC-MAIN-2018-43 CC-MAIN-2018-47 CC-MAIN-2018-51 CC-MAIN-2019-04 CC-MAIN-2019-09 CC-MAIN-2019-13 '
          'CC-MAIN-2019-18 CC-MAIN-2019-22 CC-MAIN-2019-26 CC-MAIN-2019-30 CC-MAIN-2019-35 CC-MAIN-2019-39 CC-MAIN-2019-43 CC-MAIN-2019-47 CC-MAIN-2019-51 '
          'CC-MAIN-2020-05 CC-MAIN-2020-10 CC-MAIN-2020-16 CC-MAIN-2020-24 CC-MAIN-2020-29 CC-MAIN-2020-34 CC-MAIN-2020-40 CC-MAIN-2020-45 CC-MAIN-2020-50 '
          'CC-MAIN-2021-04 CC-MAIN-2021-10 CC-MAIN-2021-17 CC-MAIN-2021-21 CC-MAIN-2021-25 CC-MAIN-2021-31 CC-MAIN-2021-39 CC-MAIN-2021-43 CC-MAIN-2021-49 '
          'CC-MAIN-2022-05 CC-MAIN-2022-21 CC-MAIN-2022-27 CC-MAIN-2022-33 CC-MAIN-2022-40 CC-MAIN-2022-49 CC-MAIN-2023-06 CC-MAIN-2023-14 CC-MAIN-2023-23 '
          'CC-MAIN-2023-40 CC-MAIN-2023-50 CC-MAIN-2024-10 CC-MAIN-2024-18 CC-MAIN-2024-22 CC-MAIN-2024-26 CC-MAIN-2024-30 CC-MAIN-2024-33 CC-MAIN-2024-38 '
          'CC-MAIN-2024-42 CC-MAIN-2024-46 CC-MAIN-2024-51 CC-MAIN-2025-05 CC-MAIN-2025-08 CC-MAIN-2025-13 CC-MAIN-2025-18 CC-MAIN-2025-21 CC-MAIN-2025-26').split()


def crawls_for_years(collinfo, frm=2016, to=2026):
    """Crawl ids (CC-MAIN-YYYY-WW) whose year is in [frm, to], oldest first."""
    ids = [c['id'] for c in collinfo if re.fullmatch(r'CC-MAIN-\d{4}-\d+', c.get('id', ''))]
    return sorted(i for i in ids if frm <= int(i.split('-')[2]) <= to)


def surt(url):
    """The SURT key Common Crawl indexes a URL under: scheme and www dropped, host reversed and comma-joined, ')' then the path, query args
    sorted, all lower-case (e.g. https://www.cs.harvard.edu/people/ -> edu,harvard,cs)/people/)."""
    u = urllib.parse.urlsplit(url if '//' in url else 'http://' + url)
    host = re.sub(r'^www\d*\.', '', (u.hostname or '').lower())
    key = ','.join(reversed(host.split('.'))) + ')' + (u.path or '/')
    if u.query:
        key += '?' + '&'.join(sorted(u.query.split('&')))
    return key.lower()


def cluster_path(crawl):
    return os.path.join(cache_dir(), f'{crawl}.cluster.idx')


def ensure_cluster(crawl, http=None, chunk=32 << 20):
    """Read the crawl's cluster.idx once (32 MiB range reads, resumable via a .part file) into cache/commoncrawl/; returns its path, or None when the
    crawl has no cluster.idx.  Bytes read are counted in BYTES."""
    gate(http)
    path = cluster_path(crawl)
    if os.path.exists(path):
        return path
    os.makedirs(cache_dir(), exist_ok=True)
    url = f'{S3}/cc-index/collections/{crawl}/indexes/cluster.idx'
    part = path + '.part'
    have = os.path.getsize(part) if os.path.exists(part) else 0
    while True:
        st, hd, body = polite_get(url, {'Range': f'bytes={have}-{have + chunk - 1}'}, http=http)
        if st in (403, 404):
            return None
        if st == 416:
            break
        if st not in (200, 206):
            raise CCRefused(f'cluster.idx {crawl} HTTP {st}')
        with open(part, 'ab') as f:
            f.write(body)
        have += len(body)
        total = {k.lower(): v for k, v in hd.items()}.get('content-range', '').rpartition('/')[2]
        if st == 200 or len(body) < chunk or (total.isdigit() and have >= int(total)):
            break
    os.replace(part, path)
    return path


def cluster_blocks(path, key):
    """Cluster lines (surt, timestamp, cdx file, offset, length) whose block may hold exact-key rows: the line before the first line with
    surt >= key, then every line with surt == key.  Binary search on byte offsets of the local file (no full read)."""
    kb = key.encode()
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        lo, hi, ans = 0, size, size
        while lo < hi:  # ans = start of the first line whose surt >= key
            mid = (lo + hi) // 2
            f.seek(mid)
            if mid:
                f.readline()
            ls = f.tell()
            if ls >= hi:
                hi = mid
                continue
            ln = f.readline()
            if ln.split(b' ', 1)[0] < kb:
                lo = f.tell()
            else:
                ans, hi = ls, mid
        start = max(0, ans - 4096)
        f.seek(start)
        if start:
            f.readline()
        prev = None
        while f.tell() < ans:
            prev = f.readline()
        lines = [prev] if prev else []
        f.seek(ans)
        for ln in f:
            if ln.split(b' ', 1)[0] != kb:
                break
            lines.append(ln)
    out = []
    for ln in lines:
        head, _, rest = ln.decode().rstrip('\n').partition('\t')
        parts = head.split(' ')
        f2 = rest.split('\t')
        if len(parts) >= 2 and len(f2) >= 3:
            out.append((parts[0], parts[1], f2[0], int(f2[1]), int(f2[2])))
    return out


def cdx_rows(crawl, url, http=None, cluster=None):
    """Exact-URL index rows (status 200 html) for one crawl via cluster.idx + a ranged read of only the matching cdx block(s)."""
    gate(http)
    path = cluster or ensure_cluster(crawl, http=http)
    if not path:
        return []
    key = surt(url)
    out, seen = [], set()
    for variant in dict.fromkeys([key, key.rstrip('/') if key.endswith('/') and not key.endswith(')/') else key + '/']):
        for _, _, name, off, length in cluster_blocks(path, variant):
            if (name, off) in seen:
                continue
            seen.add((name, off))
            st, _, blk = polite_get(f'{S3}/cc-index/collections/{crawl}/indexes/{name}', {'Range': f'bytes={off}-{off + length - 1}'}, http=http)
            if st not in (200, 206):
                raise CCRefused(f'cdx block {crawl} {name} HTTP {st}')
            for ln in gzip.decompress(blk).decode('utf-8', 'replace').splitlines():
                k, _, js = ln.split(' ', 2)
                if k != variant:
                    continue
                r = json.loads(js)
                if r.get('status') != '200' or 'html' not in (r.get('mime-detected') or r.get('mime') or ''):
                    continue
                out.append(dict(timestamp=r['timestamp'] if 'timestamp' in r else ln.split(' ', 2)[1], original=r['url'], filename=r['filename'],
                                offset=int(r['offset']), length=int(r['length']), digest=r.get('digest'), crawl=crawl))
    return out


def parse_warc(record):
    """(warc headers, http status, http headers, body) from one gzip member WARC response record."""
    raw = gzip.decompress(record)
    head, _, rest = raw.partition(b'\r\n\r\n')
    warc = dict(l.split(': ', 1) for l in head.decode('utf-8', 'replace').split('\r\n')[1:] if ': ' in l)
    hh, _, body = rest.partition(b'\r\n\r\n')
    lines = hh.decode('utf-8', 'replace').split('\r\n')
    status = int(lines[0].split()[1])
    hdrs = {k.lower(): v for k, v in (l.split(': ', 1) for l in lines[1:] if ': ' in l)}
    if hdrs.get('transfer-encoding', '').lower() == 'chunked':
        body = _dechunk(body)
    return warc, status, hdrs, body


def _dechunk(b):
    out = b''
    while b:
        n, _, b = b.partition(b'\r\n')
        k = int(n.split(b';')[0] or b'0', 16)
        if k == 0:
            break
        out, b = out + b[:k], b[k + 2:]
    return out


def fetch_record(row, http=None):
    """Range-request one WARC record; returns (status, body, headers).  The body is the raw page bytes, with no banner or rewriting."""
    gate(http)
    rng = f"bytes={row['offset']}-{row['offset'] + row['length'] - 1}"
    st, _, rec = polite_get(f"{S3}/{row['filename']}", {'Range': rng}, http=http)
    if st not in (200, 206):
        raise CCRefused(f'WARC range HTTP {st}')
    _, status, hdrs, body = parse_warc(rec)
    if hdrs.get('content-encoding', '').lower() == 'gzip':
        body = gzip.decompress(body)
    return status, body, hdrs


def capture_key(row):
    return f"{SOURCE}:{row['filename']}:{row['offset']}:{row['length']}"


def store(con, row, status, body, headers, page_url, department=''):
    """Insert into the Wayback `captures` schema (wb.db); returns the sha256 of the raw bytes."""
    sha = hashlib.sha256(body).hexdigest()
    note = json.dumps(dict(source=SOURCE, crawl=row.get('crawl'), warc_filename=row['filename'], warc_offset=row['offset'],
                           warc_length=row['length'], digest=row.get('digest')))
    con.execute('insert or ignore into captures(capture_url,page_url,department,wayback_timestamp,final_url,http_status,fetched_at,sha256,'
                'nbytes,content_type,raw_zlib,note) values (?,?,?,?,?,?,?,?,?,?,?,?)',
                (capture_key(row), page_url, department, row['timestamp'], row['original'], status, time.strftime('%Y-%m-%dT%H:%M:%S'),
                 sha, len(body), headers.get('content-type', ''), zlib.compress(body), note))
    con.commit()
    return sha


def fallback_halves(rows, frm=2016, to=2026):
    """Half-years covered by Common Crawl rows (same labels as discover_listings.half)."""
    return sorted({f"{r['timestamp'][:4]}{'H1' if int(r['timestamp'][4:6]) <= 6 else 'H2'}" for r in rows
                   if frm <= int(r['timestamp'][:4]) <= to})


# ---- crawl choice, cached index lookups, robots record, per-crawl error budget (added 2026-11-09) ----
MAX_CRAWL_ERRORS = 3


def crawl_date(entry):
    """Mid-crawl date of a collinfo entry: its `from`/`to` when present, else the id's ISO week (CC-MAIN-YYYY-WW)."""
    if entry.get('from') and entry.get('to'):
        a, b = (datetime.datetime.fromisoformat(entry[k][:19]).date() for k in ('from', 'to'))
        return a + (b - a) / 2
    y, w = (int(x) for x in entry['id'].split('-')[2:4])
    return datetime.date(y, 1, 1) + datetime.timedelta(days=7 * (w - 1) + 3)


def pick_crawls(collinfo, frm=2016, to=2026):
    """{(year, half): [crawl ids]} for CC-MAIN crawls dated in that half-year, nearest the half's middle (1 Apr / 1 Oct) first.
    A caller queries the first id of each half (one crawl per calendar year first, H2 only when H1 gave nothing usable) and the
    rest only to fill gaps."""
    out = {}
    for c in collinfo:
        if not re.fullmatch(r'CC-MAIN-\d{4}-\d+', c.get('id', '')):
            continue
        d = crawl_date(c)
        if frm <= d.year <= to:
            h = 'H1' if d.month <= 6 else 'H2'
            out.setdefault((d.year, h), []).append((abs((d - datetime.date(d.year, 4 if h == 'H1' else 10, 1)).days), c['id']))
    return {k: [i for _, i in sorted(v)] for k, v in sorted(out.items())}


def init_tables(con):
    con.execute('create table if not exists cdx(query text primary key, fetched_at text, status integer, body text)')
    con.execute('create table if not exists cc_robots(host text, checked_at text, status integer, ours_allowed integer, ai_allowed integer, '
                'robots_sha256 text, primary key(host, checked_at))')
    con.commit()


def cdx_cached(con, crawl, url, errors, http=None):
    """Exact-URL index rows for one (crawl, url), asked at most once: the answer (including 'no rows') is cached in the `cdx` table under
    the query string, so a re-run costs no request.  Errors are counted per crawl; after MAX_CRAWL_ERRORS the crawl is skipped for the run
    and the slot stays unplanned (never recorded as 'no capture')."""
    key = f'commoncrawl:{crawl}:{url}'
    row = con.execute('select status, body from cdx where query=?', (key,)).fetchone()
    if row and row[0] == 200:
        return [dict(r, crawl=crawl) for r in json.loads(row[1])]
    if errors.get(crawl, 0) >= MAX_CRAWL_ERRORS:
        raise CCRefused(f'{crawl}: {MAX_CRAWL_ERRORS} errors this run; skipped')
    try:
        rows = cdx_rows(crawl, url, http=http)
    except CCRefused:
        errors[crawl] = errors.get(crawl, 0) + 1
        raise
    con.execute('insert or replace into cdx values(?,?,?,?)', (key, time.strftime('%Y-%m-%dT%H:%M:%S'), 200, json.dumps(rows)))
    con.commit()
    return rows


def record_target_robots(con, url, http=None):
    """Check the target school host's CURRENT robots.txt (cached 1 day per host in cc_robots) and return True only when it allows us and
    names no AI agent (ClaudeBot / anthropic-ai / Claude-Web ...) as disallowed.  Every check is recorded with the robots sha256."""
    host = urllib.parse.urlsplit(url if '//' in url else 'https://' + url).netloc
    row = con.execute("select ours_allowed, ai_allowed from cc_robots where host=? and checked_at>?", (
        host, time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time() - 86400)))).fetchone()
    if row:
        return bool(row[0] and row[1])
    st, _, body = polite_get(f'https://{host}/robots.txt', http=http, external=True)
    text = body.decode('utf-8', 'replace')
    import school_web as W
    ours, ai, _ = W.robots_decision(st, text, urllib.parse.urlsplit(url if '//' in url else 'https://' + url).path or '/')
    con.execute('insert or replace into cc_robots values(?,?,?,?,?,?)', (host, time.strftime('%Y-%m-%dT%H:%M:%S'), st, int(ours), int(ai),
                                                                         hashlib.sha256(body).hexdigest()))
    con.commit()
    return ours and ai


def host_ok(con, url, http=None):
    """True when the target host's current robots.txt (cached per day, recorded in cc_robots) allows us and names no AI agent as disallowed."""
    return record_target_robots(con, url, http=http)
