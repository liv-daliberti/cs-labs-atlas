"""Polite fetcher + per-school SQLite capture store for the few-students lab investigation (2026-10-21/22).

Every fetched page (live page, Wayback id_ capture, robots.txt, API response) is one row in
hierarchy/<school>/few-students-captures.sqlite: url (the original URL; never an API key), final_url, capture_url (the
Wayback id_ URL when the bytes came from the archive), fetched_at, status, sha256 of the raw bytes, content_type,
zlib(content), error, copied_from.

Reuse: when a URL is not yet in the school's store but the sister gap investigation already stored a 200 capture of
exactly that URL (hierarchy/<school>/gap-captures.sqlite, read-only), the row is copied unchanged (its own fetched_at,
sha256 and bytes) with copied_from set, instead of fetching it again.

Politeness: one request every 2 s per host, shared across all processes (flock'd stamp files; the same stamp directory
the sister agents use, so concurrent agents share each host's budget); DSpace@MIT 100 s (it tolerates ~10 requests per
15 min). robots.txt is fetched with requests (timeout) and honoured. 429 responses are stored with Retry-After and never
retried by this module. A page that is a bot challenge is stored with error='bot-challenge' and the host is not fetched
again by this process (and not for 6 h by any process): we never try to get past a challenge.
Off limits (refused before any request, live or via Wayback): dblp.org, dblp.uni-trier.de, escholarship.org,
scholar.google.*.
Fetched content is untrusted data: it is stored and text-extracted, never executed.
"""
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
import zlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlencode, quote as urlquote

import requests

ROOT = "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy"
SCHOOLS = ("princeton", "epfl", "mit", "berkeley")
DBS = {s: f"{ROOT}/{s}/few-students-captures.sqlite" for s in SCHOOLS}
SISTER = {s: [f"{ROOT}/{s}/gap-captures.sqlite"] for s in SCHOOLS}
LOCKDIR = "/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/gap-ratelimit"
UA = ("princeton-cs-research-sweep/1.0 (faculty lab membership research: public lab pages, people profiles, thesis "
      "metadata; academic, non-commercial; polite: 1 req/2s/host)")
UA_TOKEN = "princeton-cs-research-sweep"
TIMEOUT = (10, 45)
GAPS = {"api.openalex.org": 1.05, "dspace.mit.edu": 100.0}
DEFAULT_GAP = 2.0
WAYBACK_RX = re.compile(r"^https?://web\.archive\.org/web/(\d{4,14})(?:id_|if_)?/(.+)$")
BLOCKED_RX = re.compile(r"(^|\.)(dblp\.org|dblp\.uni-trier\.de|escholarship\.org)$|(^|\.)scholar\.google\.[a-z.]+$", re.I)
CHALLENGE_RX = re.compile(rb"(<title>\s*Just a moment|cf_chl_opt|cf-browser-verification|Attention Required! \| Cloudflare|"
                          rb"Checking your browser before|_Incapsula_Resource|px-captcha|Enable JavaScript and cookies to continue|"
                          rb"Pardon Our Interruption|<title>\s*Access Denied\s*</title>|Verifying you are human)", re.I)

_robots = {}
_challenged = set()
_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
                      "Accept-Language": "en", "Accept-Encoding": "gzip, deflate"})


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_db(school):
    """Where this process writes: FSCAP_LOCAL (a worker-local SQLite file, merged later by merge.py with a single
    writer) when set, else the school's store on NFS."""
    return os.environ.get("FSCAP_LOCAL") or DBS[school]


def connect(school, path=None):
    con = sqlite3.connect(path or write_db(school), timeout=120)
    con.execute("""CREATE TABLE IF NOT EXISTS captures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        final_url TEXT,
        capture_url TEXT,
        fetched_at TEXT NOT NULL,
        status INTEGER,
        sha256 TEXT,
        content_type TEXT,
        content BLOB,
        error TEXT,
        copied_from TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_url ON captures(url)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_capurl ON captures(capture_url)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_final ON captures(final_url)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_sha ON captures(sha256)")
    return con


def host_of(url):
    m = WAYBACK_RX.match(url)
    if m:
        inner = m.group(2)
        if not re.match(r"^https?://", inner):
            inner = "http://" + inner.lstrip("/")
        return urlsplit(inner).hostname or ""
    return urlsplit(url).hostname or ""


def blocked(url):
    """Off-limits hosts, checked on the URL itself and on the original URL inside a Wayback capture URL."""
    return bool(BLOCKED_RX.search(urlsplit(url).hostname or "") or BLOCKED_RX.search(host_of(url)))


def _wait(host):
    """Cross-process per-host spacing: flock a stamp file, sleep until the gap has passed, write the new stamp."""
    gap = GAPS.get(host, DEFAULT_GAP)
    if host.endswith("archive.org"):
        host = "archive.org"  # web.archive.org and archive.org share one budget
    os.makedirs(LOCKDIR, exist_ok=True)
    path = os.path.join(LOCKDIR, re.sub(r"[^A-Za-z0-9_.-]", "_", host))
    with open(path, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            last = float(f.read().strip() or 0)
        except ValueError:
            last = 0.0
        d = time.time() - last
        if d < gap:
            time.sleep(gap - d)
        f.seek(0)
        f.truncate()
        f.write(str(time.time()))
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def _insert(con, url, final_url, capture_url, status, body, ctype, error, fetched_at=None, copied_from=None, sha=None):
    if body is not None and sha is None:
        sha = hashlib.sha256(body).hexdigest()
    cur = con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error,copied_from) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (url, final_url, capture_url, fetched_at or now(), status, sha, ctype,
                       zlib.compress(body, 9) if body is not None else None, error, copied_from))
    con.commit()
    return cur.lastrowid, sha


# ---------------------------------------------------------------- robots
def _parse_robots(txt):
    groups, cur_agents, cur_rules, last_was_agent = [], [], [], False
    for raw in txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            if not last_was_agent and (cur_agents or cur_rules):
                groups.append((cur_agents, cur_rules))
                cur_agents, cur_rules = [], []
            cur_agents.append(v.lower())
            last_was_agent = True
        elif k in ("allow", "disallow"):
            cur_rules.append((k == "allow", v))
            last_was_agent = False
        else:
            last_was_agent = False
    if cur_agents or cur_rules:
        groups.append((cur_agents, cur_rules))
    return groups


def _rule_match(pattern, path):
    if pattern == "":
        return False
    rx = re.escape(pattern).replace(r"\*", ".*")
    if rx.endswith(r"\$"):
        rx = rx[:-2] + "$"
    return re.match(rx, path) is not None


def robots_allowed(url, school):
    sp = urlsplit(url)
    base = f"{sp.scheme}://{sp.netloc}"
    if base not in _robots:
        con = connect(school)
        row = con.execute("SELECT status, content FROM captures WHERE url=? AND capture_url IS NULL AND error IS NULL "
                          "ORDER BY id DESC LIMIT 1", (base + "/robots.txt",)).fetchone()
        if row:
            st, body = row[0], (zlib.decompress(row[1]) if row[1] else b"")
        else:
            _wait(sp.hostname or sp.netloc)
            try:
                r = _sess.get(base + "/robots.txt", timeout=TIMEOUT, allow_redirects=True)
                st, body = r.status_code, r.content
                _insert(con, base + "/robots.txt", r.url, None, st, body, r.headers.get("content-type"), None)
            except Exception as e:
                st, body = None, b""
                _insert(con, base + "/robots.txt", None, None, None, None, None, repr(e)[:300])
        con.close()
        txt = ""
        if st == 200:
            txt = body.decode("utf-8", "replace")
            if "<html" in txt[:500].lower():
                txt = ""
        elif st in (401, 403):
            txt = "User-agent: *\nDisallow: /\n"
        _robots[base] = _parse_robots(txt)
    groups = _robots[base]
    chosen = [g for g in groups if any(a != "*" and a in UA_TOKEN for a in g[0])]
    if not chosen:
        chosen = [g for g in groups if "*" in g[0]]
    rules = [r for g in chosen for r in g[1]]
    path = sp.path or "/"
    if sp.query:
        path += "?" + sp.query
    best = None
    for allow, pat in rules:
        if _rule_match(pat, path):
            if best is None or len(pat) > len(best[1]) or (len(pat) == len(best[1]) and allow):
                best = (allow, pat)
    return True if best is None else best[0]


# ---------------------------------------------------------------- cache
COLS = "id,url,final_url,capture_url,status,sha256,content_type,content,error,fetched_at"


def _row(r):
    rid, url, final_url, capture_url, status, sha, ctype, content, error, fetched_at = r
    return {"id": rid, "url": url, "final_url": final_url, "capture_url": capture_url, "status": status, "sha256": sha,
            "content_type": ctype, "content": zlib.decompress(content) if content else b"", "error": error,
            "fetched_at": fetched_at, "cached": True}


def _lookup(con, url):
    if WAYBACK_RX.match(url):
        return con.execute(f"SELECT {COLS} FROM captures WHERE capture_url=? AND status=200 AND content IS NOT NULL "
                           "AND error IS NULL ORDER BY id DESC LIMIT 1", (url,)).fetchone()
    return con.execute(f"SELECT {COLS} FROM captures WHERE url=? AND capture_url IS NULL AND status=200 AND content IS NOT NULL "
                       "AND error IS NULL ORDER BY id DESC LIMIT 1", (url,)).fetchone()


def cached(school, url, sister=True):
    """Latest stored 200 capture. A Wayback id_ URL matches capture_url; any other URL matches only live rows
    (url=?, capture_url IS NULL). Falls back to the sister store (copying the row in unchanged)."""
    con = connect(school)
    r = _lookup(con, url)
    if r:
        con.close()
        return _row(r)
    if write_db(school) != DBS[school] and os.path.exists(DBS[school]):  # worker-local writer: also read the main store
        m = sqlite3.connect(f"file:{DBS[school]}?mode=ro", uri=True, timeout=60)
        try:
            r = _lookup(m, url)
        finally:
            m.close()
        if r:
            con.close()
            return _row(r)
    if sister:
        for path in SISTER.get(school, []):
            if not os.path.exists(path):
                continue
            g = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
            try:
                gr = _lookup(g, url)
            except sqlite3.DatabaseError:
                gr = None
            g.close()
            if gr:
                d = _row(gr)
                if hashlib.sha256(d["content"]).hexdigest() != d["sha256"]:
                    continue
                rid, _ = _insert(con, d["url"], d["final_url"], d["capture_url"], d["status"], d["content"], d["content_type"],
                                 None, fetched_at=d["fetched_at"], copied_from=os.path.basename(path), sha=d["sha256"])
                con.close()
                d["id"] = rid
                d["copied_from"] = path
                return d
    con.close()
    return None


def _challenged_recently(school, host):
    if host in _challenged:
        return True
    con = connect(school)
    since = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(timespec="seconds")
    rows = con.execute("SELECT url, capture_url FROM captures WHERE error='bot-challenge' AND fetched_at>=?", (since,)).fetchall()
    con.close()
    for u, c in rows:
        if urlsplit(c or u).hostname == host:
            _challenged.add(host)
            return True
    return False


def fetch(school, url, force=False, check_robots=True, params=None, store_url=None, headers=None):
    """Fetch url (cached unless force). Wayback id_ URLs are stored with url=<original> and capture_url=<wayback url>.
    params are sent with the request but not stored (use for keys); store_url overrides the stored url."""
    m = WAYBACK_RX.match(url)
    orig, cap = (m.group(2), url) if m else (store_url or url, None)
    if m and not re.match(r"^https?://", orig):
        orig = "http://" + orig.lstrip("/")
    if blocked(url):
        return {"url": orig, "capture_url": cap, "status": None, "error": "off-limits-host", "content": b""}
    if not force:
        hit = cached(school, cap or orig)
        if hit:
            return hit
    host = urlsplit(url).hostname or ""
    con = connect(school)
    if _challenged_recently(school, host):
        con.close()
        return {"url": orig, "capture_url": cap, "status": None, "error": "host-challenged-skip", "content": b""}
    if check_robots and not cap and not host.endswith("archive.org") and not robots_allowed(url, school):
        _insert(con, orig, None, cap, None, None, None, "robots-disallowed")
        con.close()
        return {"url": orig, "capture_url": cap, "status": None, "error": "robots-disallowed", "content": b""}
    try:
        for attempt in range(4):  # archive.org intermittently refuses connections: back off 15/45/90 s, then give up
            _wait(host)
            try:
                r = _sess.get(url, params=params, timeout=TIMEOUT, allow_redirects=True, headers=headers)
                if host.endswith("archive.org") and r.status_code in (502, 503, 504) and attempt < 3:
                    time.sleep((15, 45, 90)[attempt]); continue
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
                if not host.endswith("archive.org") or attempt == 3:
                    raise
                time.sleep((15, 45, 90)[attempt])
        body = r.content
        final = r.url
        if params:
            final = re.sub(r"([?&])(api_key|key|token)=[^&]*&?", r"\1", final).rstrip("?&")
        err = None
        if r.status_code == 429:
            err = f"HTTP 429 retry-after={r.headers.get('Retry-After')}"
        elif CHALLENGE_RX.search(body[:200000]) and (r.status_code != 200 or len(body) < 150000):
            err = "bot-challenge"
            _challenged.add(host)
        rid, sha = _insert(con, orig, final, cap, r.status_code, body, r.headers.get("content-type"), err)
        out = {"id": rid, "url": orig, "final_url": final, "capture_url": cap, "status": r.status_code if err != "bot-challenge" else None,
               "http_status": r.status_code, "sha256": sha, "content_type": r.headers.get("content-type"),
               "content": body if err != "bot-challenge" else b"", "error": err, "cached": False,
               "retry_after": r.headers.get("Retry-After")}
    except Exception as e:
        msg = re.sub(r"(api_key|key|token)=[^&\s'\"]*", r"\1=<redacted>", repr(e))[:500]
        _insert(con, orig, None, cap, None, None, None, msg)
        out = {"url": orig, "capture_url": cap, "status": None, "error": msg, "content": b""}
    con.close()
    return out


# ---------------------------------------------------------------- Wayback
def wayback_cdx(school, url, frm=None, to=None, limit=None, match_prefix=False):
    """Distinct-digest 200 captures of url: list of [timestamp, original, digest]."""
    if blocked(url):
        return []
    q = {"url": url + ("*" if match_prefix else ""), "output": "json", "filter": "statuscode:200",
         "fl": "timestamp,original,digest", "collapse": "digest"}
    if frm:
        q["from"] = str(frm)
    if to:
        q["to"] = str(to)
    if limit:
        q["limit"] = str(limit)
    cdx = "https://web.archive.org/cdx/search/cdx?" + urlencode(q)
    r = fetch(school, cdx, check_robots=False)
    try:
        rows = json.loads(r["content"] or b"[]")
        return rows[1:] if rows else []
    except Exception:
        return []


def wayback_id(ts, url):
    return f"https://web.archive.org/web/{ts}id_/{url}"


def wayback_latest(school, url, frm=None, to=None):
    rows = wayback_cdx(school, url, frm=frm, to=to)
    if not rows:
        return None
    ts, orig = rows[-1][0], rows[-1][1]
    return wayback_id(ts, orig)


def get(school, url, wb=True, frm=None, to=None):
    """Live fetch; when it is not a 200 (or robots-disallowed / challenged), the newest Wayback id_ capture."""
    r = fetch(school, url)
    if r.get("status") == 200 and r.get("content"):
        return r
    if wb and not WAYBACK_RX.match(url) and not blocked(url):
        w = wayback_latest(school, url, frm=frm, to=to)
        if w:
            r2 = fetch(school, w, check_robots=False)
            if r2.get("status") == 200:
                return r2
    return r


# ---------------------------------------------------------------- APIs
def openalex(school, path, params=None, force=False):
    """GET https://api.openalex.org/<path>; the key comes from the environment and is never stored."""
    params = dict(params or {})
    base = "https://api.openalex.org/" + path.lstrip("/")
    store = base + ("?" + urlencode(sorted(params.items())) if params else "")
    key = os.environ.get("OPENALEX_API_KEY")
    req = dict(params)
    if key:
        req["api_key"] = key
    res = fetch(school, base, force=force, check_robots=False, params=req, store_url=store)
    try:
        j = json.loads(res["content"]) if res.get("content") else None
    except Exception:
        j = None
    return res, j


# ---------------------------------------------------------------- text
def kind_of(content, ctype=None):
    ctype = (ctype or "").lower()
    head = content[:600].lstrip()
    if head.startswith(b"%PDF") or "pdf" in ctype:
        return "pdf"
    if "json" in ctype or head[:1] in (b"{", b"["):
        return "json"
    if (head.startswith(b"<?xml") and b"<html" not in content[:2000].lower()) or ("xml" in ctype and "html" not in ctype):
        return "xml"
    low = content[:20000].lower()
    if b"<html" in low or b"<!doctype html" in low[:500] or "html" in ctype or b"<body" in low:
        return "html"
    return "text"


def decode(content):
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", "replace")


def collapse(s):
    return re.sub(r"\s+", " ", s).strip()


def html_text(content):
    import warnings
    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(decode(content) if isinstance(content, bytes) else content, "lxml")
    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    return collapse(soup.get_text(" "))


def pdf_text(content):
    p = subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", "-", "-"], input=content, capture_output=True, timeout=180)
    return collapse(p.stdout.decode("utf-8", "replace"))


def texts(content, ctype=None):
    """All whitespace-collapsed text views a quote may be checked against: visible text (HTML), pdftotext (PDF), and the
    raw decoded bytes (JSON/XML/plain, and HTML as a fallback for attribute values)."""
    k = kind_of(content, ctype)
    out = {}
    if k == "pdf":
        out["pdf"] = pdf_text(content)
        return out
    if k == "html":
        out["html"] = html_text(content)
    out["raw"] = collapse(decode(content))
    return out


def page_text(content, ctype=None):
    t = texts(content, ctype)
    return t.get("pdf") or t.get("html") or t.get("raw") or ""


def by_sha(school, sha):
    con = connect(school)
    row = con.execute(f"SELECT {COLS} FROM captures WHERE sha256=? AND content IS NOT NULL AND status=200 AND error IS NULL ORDER BY id DESC LIMIT 1",
                      (sha,)).fetchone()
    con.close()
    return _row(row) if row else None


def links(content, base):
    """(href, anchor text) pairs of an HTML page."""
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(decode(content), "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        out.append((urljoin(base, a["href"]), collapse(a.get_text(" "))))
    return out
