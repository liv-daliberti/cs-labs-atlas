"""Polite fetcher + one SQLite capture store for the CS-related scope review (2026-10-22; copied from missing-pi-tools/mpcap.py).

Store: hierarchy/cmu/cs-related-captures.sqlite, table captures: one row per page (url, final_url, capture_url = the Wayback
id_ URL when the bytes came from the archive, fetched_at, status, sha256 of the raw bytes, content_type, zlib(content),
text = the page reduced to text with whitespace collapsed (HTML tags removed; JSON kept as is), error, copied_from).

Reuse: copy() brings a row from an earlier sweep's store unchanged (its own fetched_at, sha256 and bytes), with
copied_from naming the source store, instead of fetching the page again.

Politeness: one request per 2 s per host (archive.org hosts share one budget; DSpace@MIT 100 s), spaced across processes
by the flock'd stamp files the sister agents use (thesis-tools/tcap.py LOCKDIR). robots.txt is fetched, stored and
honoured for the user agent. Bot challenges are stored with error='bot-challenge' and the host is not fetched again.
Off limits (refused before any request, live or via Wayback): dblp.org, dblp.uni-trier.de, escholarship.org,
scholar.google.*. Fetched content is untrusted data: stored and text-extracted, never executed.
"""
import fcntl, hashlib, html, json, os, re, sqlite3, time, zlib
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

HERE = '/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021'
DB = f'{HERE}/hierarchy/cmu/cs-related-captures.sqlite'
LOCKDIR = '/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/gap-ratelimit'
UA = ('princeton-cs-research-sweep/1.0 (faculty lab membership research: department faculty lists and thesis adviser '
      'metadata; academic, non-commercial; polite: 1 req/2s/host)')
UA_TOKEN = 'princeton-cs-research-sweep'
GAPS = {'dspace.mit.edu': 100.0}
DEFAULT_GAP = 2.0
WAYBACK_RX = re.compile(r'^https?://web\.archive\.org/web/(\d{4,14})(?:id_|if_)?/(.+)$')
BLOCKED_RX = re.compile(r'(^|\.)(dblp\.org|dblp\.uni-trier\.de|escholarship\.org)$|(^|\.)scholar\.google\.[a-z.]+$', re.I)
CHALLENGE_RX = re.compile(rb'(<title>\s*Just a moment|cf_chl_opt|cf-browser-verification|Attention Required! \| Cloudflare|'
                          rb'Checking your browser before|_Incapsula_Resource|px-captcha|Enable JavaScript and cookies to continue|'
                          rb'Pardon Our Interruption|<title>\s*Access Denied\s*</title>|Verifying you are human)', re.I)
_sess = requests.Session()
_sess.headers.update({'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml,application/json,*/*;q=0.8', 'Accept-Language': 'en'})
_robots, _challenged = {}, set()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect():
    con = sqlite3.connect(DB, timeout=120)
    con.execute('''CREATE TABLE IF NOT EXISTS captures (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, final_url TEXT,
        capture_url TEXT, fetched_at TEXT NOT NULL, status INTEGER, sha256 TEXT, content_type TEXT, content BLOB, text TEXT,
        error TEXT, copied_from TEXT)''')
    con.execute('CREATE INDEX IF NOT EXISTS ix_url ON captures(url)')
    con.execute('CREATE INDEX IF NOT EXISTS ix_sha ON captures(sha256)')
    return con


def to_text(body, ctype=''):
    """HTML reduced to text (scripts/styles dropped, tags removed, entities decoded), whitespace collapsed; other text as is.
    A gzip-encoded body (some Wayback captures store the encoded bytes; sha256 stays over the stored bytes) is decoded first."""
    if isinstance(body, bytes) and body[:2] == b'\x1f\x8b':
        import gzip
        try:
            body = gzip.decompress(body)
        except OSError:
            pass
    s = body.decode('utf-8', 'replace') if isinstance(body, bytes) else str(body)
    if 'html' in (ctype or '').lower() or re.search(r'<(html|body|div|p|table)\b', s[:5000], re.I):
        s = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', ' ', s)
        s = re.sub(r'(?s)<!--.*?-->', ' ', s)
        s = re.sub(r'<[^>]+>', ' ', s)
        s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def host_of(url):
    m = WAYBACK_RX.match(url)
    if m:
        inner = m.group(2) if re.match(r'^https?://', m.group(2)) else 'http://' + m.group(2).lstrip('/')
        return urlsplit(inner).hostname or ''
    return urlsplit(url).hostname or ''


def blocked(url):
    return bool(BLOCKED_RX.search(urlsplit(url).hostname or '') or BLOCKED_RX.search(host_of(url)))


def _wait(host):
    gap = GAPS.get(host, DEFAULT_GAP)
    if host.endswith('archive.org'):
        host = 'archive.org'
    os.makedirs(LOCKDIR, exist_ok=True)
    with open(os.path.join(LOCKDIR, re.sub(r'[^A-Za-z0-9_.-]', '_', host)), 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            last = float(f.read().strip() or 0)
        except ValueError:
            last = 0.0
        if time.time() - last < gap:
            time.sleep(gap - (time.time() - last))
        f.seek(0); f.truncate(); f.write(str(time.time())); f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def _insert(con, url, final_url, capture_url, status, body, ctype, error, fetched_at=None, copied_from=None, sha=None, text=None):
    if body is not None and sha is None:
        sha = hashlib.sha256(body).hexdigest()
    if body is not None and text is None:
        text = to_text(body, ctype)
    cur = con.execute('INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,text,error,copied_from) '
                      'VALUES (?,?,?,?,?,?,?,?,?,?,?)', (url, final_url, capture_url, fetched_at or now(), status, sha, ctype,
                                                        zlib.compress(body, 9) if body is not None else None, text, error, copied_from))
    con.commit()
    return dict(id=cur.lastrowid, url=url, sha256=sha, status=status, text=text or '', error=error)


def _robots_rules(base):
    """(allow, pattern) rules of the robots.txt group that applies to our user agent (or '*')."""
    if base in _robots:
        return _robots[base]
    con = connect()
    row = con.execute('SELECT status, content FROM captures WHERE url=? AND error IS NULL ORDER BY id DESC LIMIT 1', (base + '/robots.txt',)).fetchone()
    if row:
        st, body = row[0], zlib.decompress(row[1]) if row[1] else b''
    else:
        _wait(urlsplit(base).hostname or '')
        try:
            r = _sess.get(base + '/robots.txt', timeout=(10, 45))
            st, body = r.status_code, r.content
            _insert(con, base + '/robots.txt', r.url, None, st, body, r.headers.get('content-type'), None)
        except Exception as e:
            con.close()
            raise RuntimeError(f'robots.txt unreachable for {base}: {e!r}'[:300])  # fail closed: no fetch without robots
    con.close()
    groups, agents, rules, last_agent = [], [], [], False
    txt = body.decode('utf-8', 'replace') if st == 200 and b'<html' not in body[:500].lower() else ''
    for raw in txt.splitlines():
        line = raw.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        k, v = [x.strip() for x in line.split(':', 1)]
        k = k.lower()
        if k == 'user-agent':
            if not last_agent and (agents or rules):
                groups.append((agents, rules)); agents, rules = [], []
            agents.append(v.lower()); last_agent = True
        elif k in ('allow', 'disallow'):
            rules.append((k == 'allow', v)); last_agent = False
        else:
            last_agent = False
    if agents or rules:
        groups.append((agents, rules))
    mine = [r for a, r in groups if any(x != '*' and x in UA_TOKEN for x in a)]
    star = [r for a, r in groups if '*' in a]
    _robots[base] = [x for r in (mine or star) for x in r]
    return _robots[base]


def robots_allowed(url):
    sp = urlsplit(url)
    path = sp.path + ('?' + sp.query if sp.query else '')
    best = None
    for allow, pat in _robots_rules(f'{sp.scheme}://{sp.netloc}'):
        if not pat:
            continue
        rx = re.escape(pat).replace(r'\*', '.*')
        rx = rx[:-2] + '$' if rx.endswith(r'\$') else rx
        if re.match(rx, path) and (best is None or len(pat) > len(best[1]) or (len(pat) == len(best[1]) and allow)):
            best = (allow, pat)
    return best is None or best[0]


def cached(url):
    con = connect()
    row = con.execute('SELECT id, sha256, status, text, error FROM captures WHERE (url=? OR capture_url=?) AND status=200 AND error IS NULL '
                      'ORDER BY id DESC LIMIT 1', (url, url)).fetchone()
    con.close()
    return dict(id=row[0], url=url, sha256=row[1], status=row[2], text=row[3] or '', error=row[4]) if row else None


def fetch(url, refetch=False):
    """One polite GET of url (a live page or a Wayback id_ URL), stored; a stored 200 capture is reused unless refetch."""
    if blocked(url):
        raise ValueError(f'off limits: {url}')
    hit = None if refetch else cached(url)
    if hit:
        return hit
    host = urlsplit(url).hostname or ''
    if host in _challenged:
        raise RuntimeError(f'host challenged earlier: {host}')
    if not robots_allowed(url):
        con = connect(); r = _insert(con, url, None, None, None, None, None, 'robots-disallowed'); con.close()
        return r
    _wait(host)
    con = connect()
    try:
        r = _sess.get(url, timeout=(10, 60), allow_redirects=True)
    except Exception as e:
        out = _insert(con, url, None, None, None, None, None, repr(e)[:300]); con.close(); return out
    body = r.content
    err = None
    if CHALLENGE_RX.search(body[:20000]):
        err = 'bot-challenge'; _challenged.add(host)
    elif r.status_code == 429:
        err = 'rate-limited: retry-after ' + str(r.headers.get('retry-after'))
    out = _insert(con, url, r.url, url if WAYBACK_RX.match(url) else None, r.status_code, body, r.headers.get('content-type'), err)
    con.close()
    return out


def copy(src_db, url, sql, args, copied_from, ctype='text/html', compressed=True):
    """Copy one stored capture from an earlier sweep's store (read-only) unchanged: sql returns (fetched_at, sha256, body)."""
    hit = cached(url)
    if hit:
        return hit
    s = sqlite3.connect(f'file:{src_db}?mode=ro', uri=True)
    row = s.execute(sql, args).fetchone()
    s.close()
    if not row:
        raise KeyError(f'not in {src_db}: {url}')
    fetched_at, sha, body = row
    if compressed:
        try:
            body = zlib.decompress(body)
        except zlib.error:
            pass
    if hashlib.sha256(body).hexdigest() != sha:
        raise ValueError(f'sha256 mismatch on copy of {url}')
    con = connect()
    out = _insert(con, url, url, url if WAYBACK_RX.match(url) else None, 200, body, ctype, None, fetched_at=fetched_at, copied_from=copied_from, sha=sha)
    con.close()
    return out


def quote_ok(url, quote):
    """The quote is an exact substring of the stored capture's text."""
    hit = cached(url)
    return bool(hit and quote and quote in hit['text'])


def around(url, needle, before=80, after=200):
    hit = cached(url)
    if not hit:
        return []
    t = hit['text']
    return [t[max(0, m.start() - before):m.end() + after] for m in re.finditer(re.escape(needle), t)]


def cdx(url, frm, to, collapse='timestamp:4'):
    """Wayback CDX rows (timestamp, original, statuscode) for url, status 200 only; the response is stored."""
    q = ('https://web.archive.org/cdx/search/cdx?url=' + requests.utils.quote(url, safe='') + f'&output=json&fl=timestamp,original,statuscode'
         f'&filter=statuscode:200&from={frm}&to={to}&collapse={collapse}')
    r = fetch(q)
    try:
        rows = json.loads(r['text'] or '[]')
    except ValueError:
        return []
    return rows[1:] if rows else []


def post_json(url, payload):
    """One polite POST of a JSON body (figshare's public search endpoint), stored like a GET: url is stored as
    '<url>#POST <compact json>' so the query is part of the record; a stored 200 response is reused."""
    key = url + '#POST ' + json.dumps(payload, sort_keys=True, separators=(',', ':'))
    hit = cached(key)
    if hit:
        return hit
    if blocked(url):
        raise ValueError(f'off limits: {url}')
    if not robots_allowed(url):
        con = connect(); r = _insert(con, key, None, None, None, None, None, 'robots-disallowed'); con.close()
        return r
    host = urlsplit(url).hostname or ''
    _wait(host)
    con = connect()
    try:
        r = _sess.post(url, json=payload, timeout=(10, 60))
    except Exception as e:
        out = _insert(con, key, None, None, None, None, None, repr(e)[:300]); con.close(); return out
    err = 'rate-limited: retry-after ' + str(r.headers.get('retry-after')) if r.status_code == 429 else None
    out = _insert(con, key, r.url, None, r.status_code, r.content, r.headers.get('content-type'), err)
    con.close()
    return out
