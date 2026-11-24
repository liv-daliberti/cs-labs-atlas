"""Polite fetcher + SQLite capture store for the home-department sweep.

All fetched content is untrusted data: it is stored and text-extracted, never executed.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib
import json
import re
import sqlite3
import sys
import time
import zlib
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

DB = str(P.HIERARCHY / 'home-departments-captures.sqlite')
UA = ("princeton-cs-research-sweep/1.0 (home-department census of faculty PIs; "
      "contact via Princeton CS; polite: 1 req/2s/host)")
TIMEOUT = (10, 30)
MIN_GAP = 2.0

_last = {}
_robots = {}
_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                      "Accept-Language": "en", "Accept-Encoding": "gzip, deflate"})


def connect():
    con = sqlite3.connect(DB, timeout=60)
    con.execute("""CREATE TABLE IF NOT EXISTS captures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        final_url TEXT,
        fetched_at TEXT NOT NULL,
        status INTEGER,
        sha256 TEXT,
        content_type TEXT,
        content BLOB,
        error TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_url ON captures(url)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_sha ON captures(sha256)")
    return con


def _wait(host):
    t = _last.get(host)
    if t is not None:
        d = time.monotonic() - t
        if d < MIN_GAP:
            time.sleep(MIN_GAP - d)
    _last[host] = time.monotonic()


def _parse_robots(txt):
    """Return list of (agent_set, [(allow:bool, path)]) groups."""
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
        except Exception:  # unreachable robots -> treat as allow, record
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


def fetch(url, force=False, check_robots=True):
    """Fetch url (cached in SQLite unless force). Returns dict with id,url,final_url,status,sha256,content."""
    con = connect()
    if not force:
        row = con.execute("SELECT id,url,final_url,status,sha256,content,error FROM captures "
                          "WHERE url=? AND status=200 ORDER BY id DESC LIMIT 1", (url,)).fetchone()
        if row:
            con.close()
            return {"id": row[0], "url": row[1], "final_url": row[2], "status": row[3],
                    "sha256": row[4], "content": zlib.decompress(row[5]) if row[5] else b"",
                    "error": row[6], "cached": True}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if check_robots and "web.archive.org" not in url and not robots_allowed(url):
        con.execute("INSERT INTO captures(url,final_url,fetched_at,status,sha256,content_type,content,error) "
                    "VALUES (?,?,?,?,?,?,?,?)", (url, None, now, None, None, None, None, "robots-disallowed"))
        con.commit(); con.close()
        return {"url": url, "status": None, "error": "robots-disallowed", "content": b""}
    host = urlsplit(url).netloc
    _wait(host)
    try:
        r = _sess.get(url, timeout=TIMEOUT, allow_redirects=True)
        body = r.content
        sha = hashlib.sha256(body).hexdigest()
        cur = con.execute("INSERT INTO captures(url,final_url,fetched_at,status,sha256,content_type,content,error) "
                          "VALUES (?,?,?,?,?,?,?,?)",
                          (url, r.url, now, r.status_code, sha, r.headers.get("content-type"),
                           zlib.compress(body, 9), None))
        con.commit()
        out = {"id": cur.lastrowid, "url": url, "final_url": r.url, "status": r.status_code,
               "sha256": sha, "content": body, "error": None, "cached": False}
    except Exception as e:
        con.execute("INSERT INTO captures(url,final_url,fetched_at,status,sha256,content_type,content,error) "
                    "VALUES (?,?,?,?,?,?,?,?)", (url, None, now, None, None, None, None, repr(e)[:500]))
        con.commit()
        out = {"url": url, "status": None, "error": repr(e)[:500], "content": b""}
    con.close()
    return out


def wayback_latest(url):
    """Ask the Wayback availability API for the closest capture; return id_ capture URL or None."""
    api = "https://archive.org/wayback/available?url=" + requests.utils.quote(url, safe="")
    _wait("archive.org")
    try:
        r = _sess.get(api, timeout=TIMEOUT)
        j = r.json()
        snap = j.get("archived_snapshots", {}).get("closest")
        if snap and snap.get("available") and str(snap.get("status")) == "200":
            ts = snap["timestamp"]
            return f"https://web.archive.org/web/{ts}id_/{url}"
    except Exception:
        return None
    return None


def page_text(content):
    """Whitespace-collapsed visible text of an HTML (or plain) page."""
    from bs4 import BeautifulSoup
    if isinstance(content, bytes):
        try:
            html = content.decode("utf-8")
        except UnicodeDecodeError:
            html = content.decode("latin-1")
    else:
        html = content
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    txt = soup.get_text(" ")
    return re.sub(r"\s+", " ", txt).strip()


def get_by_sha(sha):
    con = connect()
    row = con.execute("SELECT content FROM captures WHERE sha256=? LIMIT 1", (sha,)).fetchone()
    con.close()
    return zlib.decompress(row[0]) if row else None


if __name__ == "__main__":
    # CLI: capstore.py URL [URL...]  -> fetch and print status + text snippet
    for u in sys.argv[1:]:
        res = fetch(u)
        print(json.dumps({k: v for k, v in res.items() if k != "content"}))
        if res.get("content"):
            print(page_text(res["content"])[:3000])
        print("=" * 80)
