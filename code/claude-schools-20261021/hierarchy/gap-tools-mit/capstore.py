"""Polite fetcher + SQLite capture store for the MIT gap-lab investigation (hierarchy/mit/gap-captures.sqlite).

Every fetched page is untrusted data: stored (zlib) and text-extracted, never executed.
Rules: descriptive User-Agent, timeouts, one request per 2 s per host (DSpace@MIT: 95 s, DBLP: 5 s, OpenAlex: 1 s),
robots.txt fetched with requests and honoured, Wayback id_ captures when a live page fails.
"""
import hashlib
import json
import re
import sqlite3
import sys
import time
import zlib
from datetime import datetime, timezone
from urllib.parse import urlsplit, quote

import requests

DB = "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/mit/gap-captures.sqlite"
UA = ("princeton-cs-research-sweep/1.0 (MIT faculty lab gap research: public group pages, theses metadata; "
      "academic, non-commercial; polite 1 req/2s/host)")
TIMEOUT = (10, 40)
GAP = {"dspace.mit.edu": 95.0, "dblp.org": 5.0, "api.openalex.org": 1.0}
DEFAULT_GAP = 2.0

_last = {}
_robots = {}
_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
                      "Accept-Language": "en", "Accept-Encoding": "gzip, deflate"})


def connect():
    con = sqlite3.connect(DB, timeout=120)
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


def _host_key(host):
    for k in GAP:
        if host == k or host.endswith("." + k):
            return k
    if host.endswith("archive.org"):
        return "archive.org"
    return host


def _wait(host):
    k = _host_key(host)
    gap = GAP.get(k, DEFAULT_GAP)
    t = _last.get(k)
    if t is not None:
        d = time.monotonic() - t
        if d < gap:
            time.sleep(gap - d)
    _last[k] = time.monotonic()


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
    ua = "princeton-cs-research-sweep"
    chosen = [g for g in groups if any(a != "*" and a in ua for a in g[0])]
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


def _row(row):
    return {"id": row[0], "url": row[1], "final_url": row[2], "capture_url": row[3], "status": row[4],
            "sha256": row[5], "content": zlib.decompress(row[6]) if row[6] else b"", "error": row[7], "cached": True}


def cached(url, capture_url=None):
    con = connect()
    if capture_url:
        row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content,error FROM captures "
                          "WHERE capture_url=? AND status=200 ORDER BY id DESC LIMIT 1", (capture_url,)).fetchone()
    else:
        row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content,error FROM captures "
                          "WHERE url=? AND capture_url IS NULL AND status=200 ORDER BY id DESC LIMIT 1", (url,)).fetchone()
    con.close()
    return _row(row) if row else None


def fetch(url, force=False, check_robots=True, capture_url=None, headers=None, log_url=None):
    """Fetch url live (or capture_url, a Wayback id_ capture of url). Cached unless force.
    log_url: the URL to record (for API calls whose key must never be stored)."""
    rec_url = log_url or url
    if not force:
        c = cached(rec_url, capture_url)
        if c:
            return c
    target = capture_url or url
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con = connect()
    if check_robots and not capture_url and not robots_allowed(url):
        con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (rec_url, None, None, now, None, None, None, None, "robots-disallowed"))
        con.commit(); con.close()
        return {"url": rec_url, "status": None, "error": "robots-disallowed", "content": b""}
    _wait(urlsplit(target).netloc)
    try:
        r = _sess.get(target, timeout=TIMEOUT, allow_redirects=True, headers=headers or {})
        body = r.content
        sha = hashlib.sha256(body).hexdigest()
        final = r.url if not log_url else log_url
        cur = con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error) "
                          "VALUES (?,?,?,?,?,?,?,?,?)",
                          (rec_url, final, capture_url, now, r.status_code, sha, r.headers.get("content-type"),
                           zlib.compress(body, 9), None if r.status_code == 200 else f"HTTP {r.status_code} retry-after={r.headers.get('Retry-After')}"))
        con.commit()
        out = {"id": cur.lastrowid, "url": rec_url, "final_url": final, "capture_url": capture_url, "status": r.status_code,
               "sha256": sha, "content": body, "error": None, "cached": False, "retry_after": r.headers.get("Retry-After")}
    except Exception as e:
        err = type(e).__name__ if log_url else repr(e)[:500]  # never store a URL that carries a key
        con.execute("INSERT INTO captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (rec_url, None, capture_url, now, None, None, None, None, err))
        con.commit()
        out = {"url": rec_url, "status": None, "error": err, "content": b""}
    con.close()
    return out


def wayback_cdx(url, limit=40, from_=None, to=None):
    """Distinct-digest 200 captures of url via CDX: list of (timestamp, original)."""
    q = ("https://web.archive.org/cdx/search/cdx?url=" + quote(url, safe="") +
         "&output=json&filter=statuscode:200&fl=timestamp,original,digest&collapse=digest&limit=" + str(limit))
    if from_:
        q += "&from=" + str(from_)
    if to:
        q += "&to=" + str(to)
    r = fetch(q, check_robots=False)
    try:
        rows = json.loads(r["content"] or b"[]")[1:]
    except Exception:
        return []
    return [(x[0], x[1]) for x in rows]


def wayback_fetch(url, ts):
    cap = f"https://web.archive.org/web/{ts}id_/{url}"
    return fetch(url, capture_url=cap, check_robots=False)


def decode(content):
    if isinstance(content, bytes):
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                return content.decode(enc)
            except UnicodeDecodeError:
                continue
    return content


def page_text(content):
    """Whitespace-collapsed visible text of an HTML page; JSON / plain text is whitespace-collapsed as is."""
    s = decode(content) or ""
    st = s.lstrip()
    if st.startswith("{") or st.startswith("[") or not re.search(r"<(html|body|div|p|head|table|ul|span|a)\b", s[:20000], re.I):
        return re.sub(r"\s+", " ", s).strip()
    import warnings
    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(s, "lxml")
    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def by_sha(sha):
    con = connect()
    row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content,error FROM captures WHERE sha256=? "
                      "AND content IS NOT NULL ORDER BY id LIMIT 1", (sha,)).fetchone()
    con.close()
    return _row(row) if row else None


def latest(url):
    con = connect()
    row = con.execute("SELECT id,url,final_url,capture_url,status,sha256,content,error FROM captures WHERE (url=? OR final_url=? OR capture_url=?) "
                      "AND content IS NOT NULL ORDER BY (status=200) DESC, id DESC LIMIT 1", (url, url, url)).fetchone()
    con.close()
    return _row(row) if row else None


if __name__ == "__main__":
    for u in sys.argv[1:]:
        res = fetch(u)
        print(json.dumps({k: v for k, v in res.items() if k != "content"}))
        if res.get("content"):
            print(page_text(res["content"])[:3000])
        print("=" * 80)
