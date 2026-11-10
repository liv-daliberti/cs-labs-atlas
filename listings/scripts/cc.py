"""Common Crawl as a second historical source beside the Wayback Machine (proposal, 2026-11-07).

Read docs/COMMONCRAWL.md first.  Summary of the gates this module enforces:

- FAIL CLOSED on robots.txt.  index.commoncrawl.org and data.commoncrawl.org both serve `User-agent: *  Disallow: /` (checked 2026-11-07;
  only the front page and collinfo.json are allowed).  `gate()` re-reads those robots files (cached for a day) and refuses every CDX query and
  WARC range request while they disallow our paths.  Nothing here bypasses that: when Common Crawl opens the paths, the module starts working.
- A target host whose robots.txt names ClaudeBot / anthropic-ai / Claude-Web (school_web.robots_decision) is never used from Common Crawl either.
- Generic User-Agent, no email.  One request per MIN_GAP seconds, 503/429 back off exponentially (Retry-After honoured) and give up after MAX_TRIES.
- Records are stored in the school's captures.sqlite `captures` table like Wayback captures: sha256 of the raw page bytes, zlib body, and
  provenance (source, WARC filename, offset, length) in `note` as JSON; capture_url is `commoncrawl:<filename>:<offset>:<length>`.

Network functions take an injectable `http` callable so tests never touch the network: http(url, headers) -> (status, headers, body).
"""
import datetime
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
INDEX = 'https://index.commoncrawl.org'
DATA = 'https://data.commoncrawl.org'
MIN_GAP = 5.0
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


def polite_get(url, headers=None, http=None):
    """One request with a minimum gap and back-off on 429/503/5xx; returns (status, headers, body) or raises CCRefused after MAX_TRIES."""
    http, sleep, now = http or _http, time.sleep, time.time
    delay = 30.0
    for _ in range(MAX_TRIES):
        wait = _last[0] + MIN_GAP - now()
        if wait > 0:
            sleep(wait)
        _last[0] = now()
        st, hd, body = http(url, headers or {})
        if st in (429, 503) or st >= 500:
            ra = {k.lower(): v for k, v in hd.items()}.get('retry-after', '')
            sleep(float(ra) if ra.isdigit() else delay)
            delay *= 2
            continue
        return st, hd, body
    raise CCRefused(f'{urllib.parse.urlsplit(url).netloc} kept answering 429/5xx; backing off')


def robots_allows(robots_txt, path, agent=UA):
    import urllib.robotparser
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots_txt.splitlines())
    return rp.can_fetch(agent, path)


def gate(http=None, paths=('/CC-MAIN-2024-10-index', '/crawl-data/CC-MAIN-2024-10/x.warc.gz')):
    """Raise CCRefused unless index and data hosts' robots.txt allow our UA to request CDX queries and WARC files."""
    for host, path in ((INDEX, paths[0]), (DATA, paths[1])):
        st, _, body = polite_get(host + '/robots.txt', http=http)
        if st == 200 and not robots_allows(body.decode('utf-8', 'replace'), path):
            raise CCRefused(f'{host} robots.txt disallows {path} for automated clients')
        if st not in (200, 404, 410):
            raise CCRefused(f'{host} robots.txt unavailable (HTTP {st})')


def host_allowed(robots_status, robots_body, url):
    """The target host's own robots verdict (AI-named opt-out means Common Crawl copies of it are not used either)."""
    import school_web as W
    ours, ai, _ = W.robots_decision(robots_status, robots_body, url)
    return ours and ai


def crawls_for_years(collinfo, frm=2016, to=2026):
    """Crawl ids (CC-MAIN-YYYY-WW) from collinfo.json whose year is in [frm, to], oldest first."""
    ids = [c['id'] for c in collinfo if re.fullmatch(r'CC-MAIN-\d{4}-\d+', c.get('id', ''))]
    return sorted(i for i in ids if frm <= int(i.split('-')[2]) <= to)


def cdx_rows(crawl, url, http=None):
    """Exact-URL CDX lines for one crawl, status 200 html only.  Dicts with the Wayback-compatible keys timestamp/original plus warc fields."""
    gate(http)
    q = urllib.parse.urlencode({'url': url, 'output': 'json', 'filter': ['=status:200', '=mime:text/html'], 'limit': '50'}, doseq=True)
    st, _, body = polite_get(f'{INDEX}/{crawl}-index?{q}', http=http)
    if st == 404:
        return []
    if st != 200:
        raise CCRefused(f'CDX {crawl} HTTP {st}')
    out = []
    for ln in body.decode('utf-8', 'replace').splitlines():
        if ln.strip():
            r = json.loads(ln)
            out.append(dict(timestamp=r['timestamp'], original=r['url'], filename=r['filename'], offset=int(r['offset']),
                            length=int(r['length']), digest=r.get('digest'), crawl=crawl))
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
    st, _, rec = polite_get(f"{DATA}/{row['filename']}", {'Range': rng}, http=http)
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
    st, _, body = polite_get(f'https://{host}/robots.txt', http=http)
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
