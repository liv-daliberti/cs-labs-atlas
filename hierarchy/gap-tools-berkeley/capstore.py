"""Polite fetcher + SQLite capture store for the UC Berkeley EECS PI gap investigation.

Every fetched page (live, Wayback id_ capture, OpenAlex/DBLP API response) is stored as one row in
hierarchy/berkeley/gap-captures.sqlite: url (the original URL), final_url, capture_url (the Wayback id_ URL
when the bytes came from the archive), fetched_at, status, sha256 (of the raw bytes), zlib(content).
Fetched content is untrusted data: it is stored and text-extracted, never executed.
The OpenAlex API key is added to the request only; stored URLs never contain it.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import zlib
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlencode, parse_qsl, urlunsplit

import requests

DB_MAIN = ("/n/fs/resemble/cs-atlas/work/hierarchy/berkeley/"
           "gap-captures.sqlite")
# Parallel workers write to their own local SQLite file (GAPCAP_DB, on local /tmp) to avoid concurrent SQLite
# writers on NFS; merge_workers.py later copies their rows into DB_MAIN with a single writer. Reads see both.
DB = os.environ.get("GAPCAP_DB") or DB_MAIN
READ_DBS = [DB] + ([DB_MAIN] if DB != DB_MAIN else [])
UA = ("princeton-cs-research-sweep/1.0 (UC Berkeley EECS faculty PI gap investigation: lab members, advisees, "
      "author identifiers; contact via Princeton CS; polite: 1 req/2s/host)")
UA_TOKEN = "princeton-cs-research-sweep"
TIMEOUT = (10, 40)
GAPS = {"api.openalex.org": 1.05, "dblp.org": 5.0, "dblp.uni-trier.de": 5.0}
DEFAULT_GAP = 2.0
WAYBACK_RX = re.compile(r"^https?://web\.archive\.org/web/(\d{4,14})(?:id_|if_)?/(.+)$")

_last = {}
_robots = {}
_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
                      "Accept-Language": "en", "Accept-Encoding": "gzip, deflate"})


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path=None):
    con = sqlite3.connect(path or DB, timeout=120)
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
        error TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_url ON captures(url)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_capurl ON captures(capture_url)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_sha ON captures(sha256)")
    return con


LOCKDIR = "/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/gap-ratelimit"


def _wait(host):
    """Cross-process per-host spacing shared with the sibling gap investigations: flock a stamp file,
    sleep until the gap has passed, write the new stamp."""
    import fcntl
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


def robots_allowed(url):
    sp = urlsplit(url)
    base = f"{sp.scheme}://{sp.netloc}"
    if base not in _robots:
        _wait(sp.netloc)
        try:
            r = _sess.get(base + "/robots.txt", timeout=TIMEOUT, allow_redirects=True)
            txt = r.text if r.status_code == 200 else ""
            if r.status_code in (401, 403):
                txt = "User-agent: *\nDisallow: /\n"
        except Exception:
            txt = ""
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


def split_wayback(url):
    m = WAYBACK_RX.match(url)
    if not m:
        return url, None
    orig = m.group(2)
    if not re.match(r"^https?://", orig):
        orig = "http://" + orig.lstrip("/")
    return orig, url


def _row_to_dict(row):
    return {"id": row[0], "url": row[1], "final_url": row[2], "capture_url": row[3], "status": row[4],
            "sha256": row[5], "content": zlib.decompress(row[6]) if row[6] else b"", "error": row[7],
            "content_type": row[8], "cached": True}


def cached(url):
    orig, cap = split_wayback(url)
    for path in READ_DBS:
        con = connect(path)
        if cap:
            row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content,error,content_type FROM captures "
                              "WHERE capture_url=? AND status=200 ORDER BY id DESC LIMIT 1", (cap,)).fetchone()
        else:
            row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content,error,content_type FROM captures "
                              "WHERE url=? AND capture_url IS NULL AND status=200 ORDER BY id DESC LIMIT 1",
                              (orig,)).fetchone()
        con.close()
        if row:
            return _row_to_dict(row)
    return None


def find_capture(url):
    """Latest 200 capture of url (live url, final_url, or Wayback capture_url) across READ_DBS: (content, sha256, row_url, capture_url)."""
    for path in READ_DBS:
        con = connect(path)
        row = con.execute("SELECT content, sha256, url, capture_url FROM captures WHERE (url=? OR capture_url=? OR final_url=?) "
                          "AND status=200 AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (url, url, url)).fetchone()
        con.close()
        if row:
            return zlib.decompress(row[0]), row[1], row[2], row[3]
    return None


def _store(url, final_url, capture_url, status, body, ctype, error):
    sha = hashlib.sha256(body).hexdigest() if body is not None else None
    con = connect()
    cur = con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error) "
                      "VALUES (?,?,?,?,?,?,?,?,?)",
                      (url, final_url, capture_url, now(), status, sha, ctype,
                       zlib.compress(body, 9) if body is not None else None, error))
    con.commit()
    rid = cur.lastrowid
    con.close()
    return {"id": rid, "url": url, "final_url": final_url, "capture_url": capture_url, "status": status,
            "sha256": sha, "content": body or b"", "error": error, "content_type": ctype, "cached": False}


def fetch(url, force=False, check_robots=True, headers=None):
    """Fetch url (cached unless force). Wayback id_ URLs are stored with url=original, capture_url=wayback."""
    if not force:
        c = cached(url)
        if c:
            return c
    orig, cap = split_wayback(url)
    if check_robots and cap is None and "archive.org" not in urlsplit(url).netloc and not robots_allowed(url):
        return _store(orig, None, cap, None, None, None, "robots-disallowed")
    host = urlsplit(url).netloc
    _wait(host)
    try:
        r = _sess.get(url, timeout=TIMEOUT, allow_redirects=True, headers=headers or {})
        final = r.url
        return _store(orig, final, cap, r.status_code, r.content, r.headers.get("content-type"), None)
    except Exception as e:
        return _store(orig, None, cap, None, None, None, repr(e)[:500])


def _strip_key(url):
    sp = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(sp.query, keep_blank_values=True) if k != "api_key"]
    return urlunsplit((sp.scheme, sp.netloc, sp.path, urlencode(q), sp.fragment))


def openalex(path, params=None, force=False):
    """GET https://api.openalex.org/<path>?params. Stored URL excludes the api key. Returns (row, json)."""
    params = dict(params or {})
    base = "https://api.openalex.org/" + path.lstrip("/")
    public = base + ("?" + urlencode(sorted(params.items())) if params else "")
    if not force:
        c = cached(public)
        if c:
            try:
                return c, json.loads(c["content"])
            except Exception:
                pass
    key = os.environ.get("OPENALEX_API_KEY")
    rp = dict(params)
    if key:
        rp["api_key"] = key
    _wait("api.openalex.org")
    try:
        r = _sess.get(base, params=rp, timeout=TIMEOUT)
        row = _store(public, _strip_key(r.url), None, r.status_code, r.content, r.headers.get("content-type"), None)
        try:
            return row, r.json()
        except Exception:
            return row, None
    except Exception as e:
        msg = repr(e)
        if key:
            msg = msg.replace(key, "<key>")
        return _store(public, None, None, None, None, None, msg[:500]), None


def wayback_cdx(url, extra="", limit=None):
    """CDX listing of 200 captures (distinct digests). Returns list of (timestamp, original)."""
    q = ("https://web.archive.org/cdx/search/cdx?url=" + requests.utils.quote(url, safe="")
         + "&output=json&filter=statuscode:200&fl=timestamp,original,digest&collapse=digest" + extra)
    if limit:
        q += f"&limit={limit}"
    r = fetch(q, check_robots=False)
    try:
        rows = json.loads(r["content"] or b"[]")[1:]
    except Exception:
        rows = []
    return [(x[0], x[1]) for x in rows]


def _decode(content):
    if isinstance(content, str):
        return content
    for enc in ("utf-8",):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            pass
    return content.decode("latin-1")


def is_pdf(content):
    return isinstance(content, bytes) and content[:5] == b"%PDF-"


def pdf_text(content):
    p = subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", "-", "-"], input=content,
                       capture_output=True, timeout=120)
    return p.stdout.decode("utf-8", "replace")


def page_text(content):
    """Whitespace-collapsed text: visible text for HTML, pdftotext for PDF, raw for JSON/XML/plain."""
    if is_pdf(content):
        return re.sub(r"\s+", " ", pdf_text(content)).strip()
    txt = _decode(content)
    head = txt[:2000].lower()
    if "<html" in head or "<!doctype html" in head or "<body" in head or "<div" in head:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(txt, "lxml")
        for t in soup(["script", "style", "noscript", "template"]):
            t.decompose()
        txt = soup.get_text(" ")
    return re.sub(r"\s+", " ", txt).strip()


def raw_text(content):
    if is_pdf(content):
        return page_text(content)
    return re.sub(r"\s+", " ", _decode(content)).strip()


def get_by_sha(sha):
    for path in READ_DBS:
        con = connect(path)
        row = con.execute("SELECT content FROM captures WHERE sha256=? AND content IS NOT NULL LIMIT 1", (sha,)).fetchone()
        con.close()
        if row:
            return zlib.decompress(row[0])
    return None


def quote_ok(sha, quote):
    c = get_by_sha(sha)
    if c is None:
        return False
    return quote in page_text(c) or quote in raw_text(c)


if __name__ == "__main__":
    for u in sys.argv[1:]:
        res = fetch(u)
        print(json.dumps({k: v for k, v in res.items() if k != "content"}))
        if res.get("content"):
            print(page_text(res["content"])[:3000])
        print("=" * 80)


def post_json(url, payload, force=False):
    """POST a JSON body (e.g. the figshare search API). Stored url = '<url>#post=<canonical json body>'."""
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    key = url + "#post=" + body
    if not force:
        c = cached(key)
        if c:
            return c
    host = urlsplit(url).netloc
    _wait(host)
    try:
        r = _sess.post(url, data=body, timeout=TIMEOUT, headers={"Content-Type": "application/json"})
        return _store(key, r.url, None, r.status_code, r.content, r.headers.get("content-type"), None)
    except Exception as e:
        return _store(key, None, None, None, None, None, repr(e)[:500])
