"""Polite fetcher + per-school SQLite capture store for the Princeton/EPFL PI gap investigation.

Every fetched page (live page, Wayback id_ capture, robots.txt, OpenAlex/DBLP/Infoscience API response) is one row in
hierarchy/<school>/gap-captures.sqlite: url (the original URL; API URLs without any key), final_url, capture_url (the
Wayback id_ URL when the bytes came from the archive), fetched_at, status, sha256 of the raw bytes, zlib(content).

Rate limits are shared across all of this investigation's processes through flock'd stamp files in the scratchpad:
one request per 2 s per host (OpenAlex 1/s, DBLP 1 per 5 s). robots.txt is fetched with requests (timeout) and honoured.
Fetched content is untrusted data: it is stored and text-extracted, never executed.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
import zlib
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlencode

import requests

ROOT = str(P.HIERARCHY)
DBS = {s: f"{ROOT}/{s}/gap-captures.sqlite" for s in ("princeton", "epfl")}
LOCKDIR = "/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/gap-ratelimit"
UA = ("princeton-cs-research-sweep/1.0 (Princeton/EPFL faculty PI gap investigation: lab members, advisees, "
      "author identifiers; contact via Princeton CS; polite: 1 req/2s/host)")
UA_TOKEN = "princeton-cs-research-sweep"
TIMEOUT = (10, 45)
GAPS = {"api.openalex.org": 1.05, "dblp.org": 5.0, "dblp.uni-trier.de": 5.0}
DEFAULT_GAP = 2.0
WAYBACK_RX = re.compile(r"^https?://web\.archive\.org/web/(\d{4,14})(?:id_|if_)?/(.+)$")

_robots = {}
_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
                      "Accept-Language": "en", "Accept-Encoding": "gzip, deflate"})


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(school):
    con = sqlite3.connect(DBS[school], timeout=120)
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
        txt = ""
        con = connect(school)
        row = con.execute("SELECT status, content FROM captures WHERE url=? AND error IS NULL ORDER BY id DESC LIMIT 1",
                          (base + "/robots.txt",)).fetchone()
        if row:
            st, body = row
            body = zlib.decompress(body) if body else b""
        else:
            _wait(sp.netloc)
            try:
                r = _sess.get(base + "/robots.txt", timeout=TIMEOUT, allow_redirects=True)
                st, body = r.status_code, r.content
                con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error) "
                            "VALUES (?,?,?,?,?,?,?,?,?)", (base + "/robots.txt", r.url, None, now(), st,
                                                           hashlib.sha256(body).hexdigest(), r.headers.get("content-type"),
                                                           zlib.compress(body, 9), None))
                con.commit()
            except Exception:
                st, body = None, b""
        con.close()
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


def _row(con_row):
    rid, url, final_url, capture_url, status, sha, ctype, content, error = con_row
    return {"id": rid, "url": url, "final_url": final_url, "capture_url": capture_url, "status": status, "sha256": sha,
            "content_type": ctype, "content": zlib.decompress(content) if content else b"", "error": error, "cached": True}


def cached(school, url):
    """Latest stored 200 capture: a Wayback id_ URL matches capture_url; any other URL matches only live rows
    (url=?, capture_url IS NULL), never an archived copy of the same page."""
    con = connect(school)
    if WAYBACK_RX.match(url):
        row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content_type,content,error FROM captures "
                          "WHERE capture_url=? AND status=200 ORDER BY id DESC LIMIT 1", (url,)).fetchone()
    else:
        row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content_type,content,error FROM captures "
                          "WHERE url=? AND capture_url IS NULL AND status=200 ORDER BY id DESC LIMIT 1", (url,)).fetchone()
    con.close()
    return _row(row) if row else None


def fetch(school, url, force=False, check_robots=True, params=None, store_url=None, headers=None):
    """Fetch url (cached unless force). Wayback id_ URLs are stored with url=<original> and capture_url=<wayback url>.
    params are added to the request but not to the stored url (use for API keys); store_url overrides the stored url."""
    m = WAYBACK_RX.match(url)
    orig, cap = (m.group(2), url) if m else (store_url or url, None)
    if not force:
        hit = cached(school, cap or orig)
        if hit:
            return hit
    con = connect(school)
    if check_robots and not robots_allowed(url, school):
        con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (orig, None, cap, now(), None, None, None, None, "robots-disallowed"))
        con.commit(); con.close()
        return {"url": orig, "capture_url": cap, "status": None, "error": "robots-disallowed", "content": b""}
    host = urlsplit(url).netloc
    try:
        for attempt in range(4):  # archive.org intermittently refuses connections: back off 15/45/90 s, then give up
            _wait(host)
            try:
                r = _sess.get(url, params=params, timeout=TIMEOUT, allow_redirects=True, headers=headers)
                if host.endswith("archive.org") and r.status_code in (429, 502, 503, 504) and attempt < 3:
                    time.sleep((15, 45, 90)[attempt]); continue
                break
            except requests.exceptions.ConnectionError:
                if not host.endswith("archive.org") or attempt == 3:
                    raise
                time.sleep((15, 45, 90)[attempt])
        body = r.content
        sha = hashlib.sha256(body).hexdigest()
        final = r.url
        if params:  # never store keys
            final = re.sub(r"([?&])api_key=[^&]*&?", r"\1", final).rstrip("?&")
        cur = con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error) "
                          "VALUES (?,?,?,?,?,?,?,?,?)",
                          (orig, final, cap, now(), r.status_code, sha, r.headers.get("content-type"), zlib.compress(body, 9), None))
        con.commit()
        out = {"id": cur.lastrowid, "url": orig, "final_url": final, "capture_url": cap, "status": r.status_code,
               "sha256": sha, "content_type": r.headers.get("content-type"), "content": body, "error": None, "cached": False}
    except Exception as e:
        msg = re.sub(r"api_key=[^&\s'\"]*", "api_key=<redacted>", repr(e))[:500]
        con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (orig, None, cap, now(), None, None, None, None, msg))
        con.commit()
        out = {"url": orig, "capture_url": cap, "status": None, "error": msg, "content": b""}
    con.close()
    return out


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


def dblp(school, url, force=False):
    """DBLP author search API or pid XML (max one request per 5 s; never sparql)."""
    assert "sparql" not in url
    return fetch(school, url, force=force, check_robots=True)


def wayback_cdx(school, url, frm=None, to=None, limit=None, match_prefix=False):
    q = {"url": url + ("*" if match_prefix else ""), "output": "json", "filter": "statuscode:200", "fl": "timestamp,original,digest",
         "collapse": "digest"}
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


# ---------------------------------------------------------------- text
def kind_of(content, ctype=None):
    ctype = (ctype or "").lower()
    head = content[:600].lstrip()
    if head.startswith(b"%PDF") or "pdf" in ctype:
        return "pdf"
    if "json" in ctype or head[:1] in (b"{", b"["):
        return "json"
    if head.startswith(b"<?xml") and b"<html" not in content[:2000].lower() or "xml" in ctype and "html" not in ctype:
        return "xml"
    if b"<html" in content[:5000].lower() or b"<!doctype html" in content[:500].lower() or "html" in ctype or b"<body" in content[:20000].lower():
        return "html"
    return "text"


def _decode(content):
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", "replace")


def collapse(s):
    return re.sub(r"\s+", " ", s).strip()


def html_text(content):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(_decode(content) if isinstance(content, bytes) else content, "lxml")
    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    return collapse(soup.get_text(" "))


def pdf_text(content):
    p = subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", "-", "-"], input=content, capture_output=True, timeout=120)
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
    out["raw"] = collapse(_decode(content))
    return out


def page_text(content, ctype=None):
    t = texts(content, ctype)
    return t.get("pdf") or t.get("html") or t.get("raw") or ""


def by_sha(school, sha):
    con = connect(school)
    row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content_type,content,error FROM captures "
                      "WHERE sha256=? AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (sha,)).fetchone()
    con.close()
    return _row(row) if row else None


def verify_quote(school, sha, quote):
    """True when quote is an exact substring of one whitespace-collapsed text view of the stored bytes."""
    r = by_sha(school, sha)
    if not r:
        return False, "no-capture"
    q = collapse(quote)
    for name, t in texts(r["content"], r["content_type"]).items():
        if q in t:
            return True, name
    return False, "not-found"


def oa_author_works(school, aid, frm=2016, force=False):
    """An author's works from frm on (<=200, newest first) with authorships; one stored response per (author, frm)."""
    return openalex(school, "works", {"filter": f"author.id:{aid},from_publication_date:{frm}-01-01", "per-page": 200,
                                      "sort": "publication_year:desc",
                                      "select": "id,title,publication_year,publication_date,doi,authorships"}, force=force)
