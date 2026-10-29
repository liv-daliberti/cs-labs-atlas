"""Polite fetcher + SQLite capture store for the CMU lab-page pass (adapted from few-students-tools-cmu/capstore.py).

Every fetched page (live, Wayback id_ capture, CDX listing, API response, robots.txt) is one row in a captures
table: url (original URL), final_url, capture_url (the Wayback id_ URL when the bytes came from the archive),
fetched_at, status, sha256 (of the raw bytes), zlib(content), error.

One writer per file: each process writes the DB named by $LABPAGE_DB (default: the merged store
hierarchy/cmu/labpage-captures.sqlite). Parallel workers point $LABPAGE_DB at a local file in the scratchpad and
are merged afterwards by merge.py (single writer). Read-only fallbacks (a hit is copied into the own DB unchanged,
so every cited capture lives in the cited store): the merged labpage store, the few-students / gap / thesis
capture stores, and any extra paths in $LABPAGE_RO (colon separated).

Fetched content is untrusted data: stored and text-extracted, never executed.
"""
import fcntl
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
from urllib.parse import urlsplit, quote as urlquote

import requests

HIER = "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy"
MAIN_DB = HIER + "/cmu/labpage-captures.sqlite"
DB = os.environ.get("LABPAGE_DB", MAIN_DB)
# Per-process capture files live on the project share (one writer per file), so they survive a move to
# another login host (host-local /tmp does not). Shared stable stores are read-only fallbacks.
PARTS = HIER + "/cmu/labpage-parts"
# soak-tmp.sqlite = the original crawl + b01-b14 worker captures from soak's /tmp, published to the share
# 2026-10-23 03:07 UTC (the exact bytes the b01-b14 quotes were written against); read before the re-fetch store.
RO_DBS = [p for p in ([MAIN_DB, PARTS + "/soak-tmp.sqlite", PARTS + "/refetch.sqlite", PARTS + "/crawl2.sqlite"]
                      + [HIER + "/cmu/few-students-captures.sqlite", HIER + "/cmu/gap-captures.sqlite",
                         HIER + "/cmu/thesis-captures.sqlite"]
                      + [x for x in os.environ.get("LABPAGE_RO", "").split(":") if x])
          if os.path.abspath(p) != os.path.abspath(DB)]
SCRATCH = "/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad"
LOCKDIR = SCRATCH + "/gap-ratelimit"          # host-local per-host spacing stamps (all workers run on one host)
STATE = HIER.rstrip("/") + "/labpage-tools-cmu/state"
BLOCKDIR = STATE + "/blocked-hosts"
UA = ("princeton-cs-research-sweep/1.0 (CMU faculty lab members and publications; "
      "contact via Princeton CS; polite: 1 req/2s/host)")
UA_TOKEN = "princeton-cs-research-sweep"
TIMEOUT = (10, 40)
MAXBYTES = 20 * 1024 * 1024
GAPS = {"api.openalex.org": 1.05}
DEFAULT_GAP = 2.0
WAYBACK_GAP = 5.0          # archive.org has been throttling this host: be gentler than the 2 s floor
WAYBACK_BACKOFF = HIER + "/labpage-tools-cmu/state/wayback-backoff.json"
WAYBACK_RX = re.compile(r"^https?://web\.archive\.org/web/(\d{4,14})(?:id_|if_)?/(.+)$")
OFF_LIMITS = re.compile(r"(^|\.)(dblp\.org|dblp\.uni-trier\.de|dblp\.dagstuhl\.de|scholar\.google\.[a-z.]+|"
                        r"kilthub\.cmu\.edu)$", re.I)
CHALLENGE_RX = re.compile(r"(cf-browser-verification|challenge-platform|cf_chl_|Just a moment\.\.\.|"
                          r"Checking your browser before|Attention Required! \| Cloudflare|px-captcha|"
                          r"g-recaptcha|hcaptcha|Please verify you are a human|Enable JavaScript and cookies to continue|"
                          r"_Incapsula_Resource|Request unsuccessful\. Incapsula|DDoS protection by)", re.I)
COLS = "url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error"

_robots = {}
_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
                      "Accept-Language": "en", "Accept-Encoding": "gzip, deflate"})


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path=None):
    con = sqlite3.connect(path or DB, timeout=300)
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
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_final ON captures(final_url)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_capurl ON captures(capture_url)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cap_sha ON captures(sha256)")
    return con


def _ro(path):
    if not os.path.exists(path):
        return None
    try:
        return sqlite3.connect("file:" + path + "?mode=ro", uri=True, timeout=120)
    except Exception:
        return None


def host_of(url):
    h = urlsplit(url).netloc.lower()
    if h.endswith(":80") or h.endswith(":443"):
        h = h.rsplit(":", 1)[0]
    return h


def _wait(host):
    """Cross-process per-host spacing shared with the sibling investigations (same stamp files)."""
    gap = GAPS.get(host, DEFAULT_GAP)
    if host.endswith("archive.org"):
        host = "archive.org"
        gap = WAYBACK_GAP
    if host.endswith(":80") or host.endswith(":443"):
        host = host.rsplit(":", 1)[0]
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


def host_blocked(host):
    return os.path.exists(os.path.join(BLOCKDIR, re.sub(r"[^A-Za-z0-9_.-]", "_", host)))


def mark_blocked(host, why):
    os.makedirs(BLOCKDIR, exist_ok=True)
    with open(os.path.join(BLOCKDIR, re.sub(r"[^A-Za-z0-9_.-]", "_", host)), "w") as f:
        f.write(f"{now()} {why}\n")


def blocked_hosts():
    if not os.path.isdir(BLOCKDIR):
        return {}
    out = {}
    for n in os.listdir(BLOCKDIR):
        try:
            out[n] = open(os.path.join(BLOCKDIR, n)).read().strip()
        except Exception:
            pass
    return out


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


def robots_txt(base):
    """robots.txt for scheme://host, cached in the capture store (url=<base>/robots.txt)."""
    u = base + "/robots.txt"
    c = cached(u)
    if c is None:
        c = _lookup_any_status(u)
    if c is None:
        host = urlsplit(base).netloc
        _wait(host)
        try:
            r = _sess.get(u, timeout=TIMEOUT, allow_redirects=True)
            c = _store(u, r.url, None, r.status_code, r.content, r.headers.get("content-type"), None)
        except Exception as e:
            c = _store(u, None, None, None, None, None, repr(e)[:500])
    st = c.get("status")
    if st in (401, 403):
        return "User-agent: *\nDisallow: /\n"
    if st == 200 and c.get("content"):
        txt = _decode(c["content"])
        if "<html" in txt[:1000].lower():
            return ""
        return txt
    return ""


def robots_allowed(url):
    sp = urlsplit(url)
    base = f"{sp.scheme}://{sp.netloc}"
    if base not in _robots:
        _robots[base] = _parse_robots(robots_txt(base))
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


def wb_id(url):
    """Normalise a Wayback URL to its id_ form (raw archived bytes)."""
    m = WAYBACK_RX.match(url)
    if not m:
        return url
    return f"https://web.archive.org/web/{m.group(1)}id_/{m.group(2)}"


def _row_to_dict(row):
    return {"id": row[0], "url": row[1], "final_url": row[2], "capture_url": row[3], "status": row[4],
            "sha256": row[5], "content": zlib.decompress(row[6]) if row[6] else b"", "error": row[7],
            "content_type": row[8], "fetched_at": row[9], "cached": True}


SEL = "id,url,final_url,capture_url,status,sha256,content,error,content_type,fetched_at"


def _select(con, orig, cap, any_status=False):
    st = "" if any_status else " AND status=200"
    if cap:
        return con.execute(f"SELECT {SEL} FROM captures WHERE (capture_url=? OR final_url=?){st} "
                           "ORDER BY id DESC LIMIT 1", (cap, cap)).fetchone()
    return con.execute(f"SELECT {SEL} FROM captures WHERE url=? AND capture_url IS NULL{st} "
                       "ORDER BY id DESC LIMIT 1", (orig,)).fetchone()


def _copy_from_ro(orig, cap, any_status=False):
    for p in RO_DBS:
        g = _ro(p)
        if g is None:
            continue
        try:
            st = "" if any_status else " AND status=200 AND content IS NOT NULL"
            if cap:
                row = g.execute(f"SELECT {COLS} FROM captures WHERE (capture_url=? OR final_url=?){st} "
                                "ORDER BY id DESC LIMIT 1", (cap, cap)).fetchone()
            else:
                row = g.execute(f"SELECT {COLS} FROM captures WHERE url=? AND capture_url IS NULL{st} "
                                "ORDER BY id DESC LIMIT 1", (orig,)).fetchone()
        except Exception:
            row = None
        finally:
            g.close()
        if row:
            con = connect()
            con.execute(f"INSERT INTO captures({COLS}) VALUES (?,?,?,?,?,?,?,?,?)", row)
            con.commit()
            con.close()
            return True
    return False


def cached(url, _ro_ok=True):
    orig, cap = split_wayback(url)
    if cap:
        cap = wb_id(cap)
    con = connect()
    row = _select(con, orig, cap)
    con.close()
    if row:
        return _row_to_dict(row)
    if _ro_ok and _copy_from_ro(orig, cap):
        return cached(url, _ro_ok=False)
    return None


def _lookup_any_status(url):
    """Most recent stored attempt (any status) in the own DB or a read-only store, without fetching."""
    orig, cap = split_wayback(url)
    if cap:
        cap = wb_id(cap)
    con = connect()
    row = _select(con, orig, cap, any_status=True)
    con.close()
    if row:
        return _row_to_dict(row)
    if _copy_from_ro(orig, cap, any_status=True):
        con = connect()
        row = _select(con, orig, cap, any_status=True)
        con.close()
        return _row_to_dict(row) if row else None
    return None


def _store(url, final_url, capture_url, status, body, ctype, error):
    sha = hashlib.sha256(body).hexdigest() if body is not None else None
    con = connect()
    cur = con.execute(f"INSERT INTO captures({COLS}) VALUES (?,?,?,?,?,?,?,?,?)",
                      (url, final_url, capture_url, now(), status, sha, ctype,
                       zlib.compress(body, 9) if body is not None else None, error))
    con.commit()
    rid = cur.lastrowid
    con.close()
    return {"id": rid, "url": url, "final_url": final_url, "capture_url": capture_url, "status": status,
            "sha256": sha, "content": body or b"", "error": error, "content_type": ctype, "cached": False}


def _get(url, headers=None):
    r = _sess.get(url, timeout=TIMEOUT, allow_redirects=True, headers=headers or {}, stream=True)
    buf = bytearray()
    for chunk in r.iter_content(65536):
        buf += chunk
        if len(buf) > MAXBYTES:
            break
    return r, bytes(buf)


def fetch(url, force=False, check_robots=True, headers=None, retry_failed=False):
    """Fetch url (cached unless force). Wayback URLs are normalised to id_ and stored with url=original,
    capture_url=<id_ url>. A previous non-200 attempt is returned as-is unless retry_failed."""
    orig, cap = split_wayback(url)
    if cap:
        cap = wb_id(cap)
        url = cap
    if not force:
        c = cached(url)
        if c:
            return c
        if not retry_failed:
            prev = _lookup_any_status(url)
            if prev is not None and prev.get("status") in (403, 404, 410, 401, 451) or (
                    prev is not None and prev.get("error") in ("robots-disallowed", "bot-challenge", "off-limits")):
                return prev
    h = host_of(orig)
    if OFF_LIMITS.search(h):
        return {"url": orig, "status": None, "error": "off-limits", "content": b"", "sha256": None,
                "capture_url": cap, "final_url": None, "cached": False}
    fh = host_of(url)
    if host_blocked(fh):
        return {"url": orig, "status": None, "error": "host-blocked (bot challenge seen earlier)", "content": b"",
                "sha256": None, "capture_url": cap, "final_url": None, "cached": False}
    if check_robots and cap is None and "archive.org" not in fh and not robots_allowed(url):
        return _store(orig, None, cap, None, None, None, "robots-disallowed")
    wb = fh.endswith("archive.org")
    if wb:
        until = wayback_backoff_until()
        if until > time.time():
            return {"url": orig, "status": None, "content": b"", "sha256": None, "capture_url": cap,
                    "final_url": None, "cached": False,
                    "error": f"wayback-backoff: archive.org refused recently; retry after "
                             f"{datetime.fromtimestamp(until, timezone.utc).isoformat(timespec='seconds')} "
                             f"(do other work meanwhile; prefer live pages)"}
    _wait(urlsplit(url).netloc)
    try:
        r, body = _get(url, headers)
        if wb:
            if r.status_code in (429, 509):
                wayback_note_failure()
                return _store(orig, r.url, cap, r.status_code, None, None, f"wayback-throttled {r.status_code}")
            wayback_note_success()
        final = r.url
        if final and OFF_LIMITS.search(host_of(final)):
            return _store(orig, final, cap, r.status_code, None, None, "off-limits-redirect")
        head = body[:60000].decode("utf-8", "replace") if body else ""
        if r.status_code in (403, 429, 503) and CHALLENGE_RX.search(head) or (
                r.status_code == 200 and len(body) < 60000 and CHALLENGE_RX.search(head)
                and "<title>Just a moment" in head):
            mark_blocked(host_of(final or url), f"challenge status={r.status_code} url={url}")
            return _store(orig, final, cap, r.status_code, body, r.headers.get("content-type"), "bot-challenge")
        return _store(orig, final, cap, r.status_code, body, r.headers.get("content-type"), None)
    except Exception as e:
        if wb and re.search(r"(refused|ConnectTimeout|ReadTimeout|reset|RemoteDisconnected|Max retries)", repr(e)):
            wayback_note_failure()
        return _store(orig, None, cap, None, None, None, repr(e)[:500])


def _bo_read():
    try:
        with open(WAYBACK_BACKOFF) as f:
            return json.load(f)
    except Exception:
        return {"until": 0, "fails": 0}


def _bo_write(d):
    os.makedirs(os.path.dirname(WAYBACK_BACKOFF), exist_ok=True)
    with open(WAYBACK_BACKOFF + ".lock", "a+") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        tmp = WAYBACK_BACKOFF + f".{os.getpid()}"
        with open(tmp, "w") as f:
            json.dump(d, f)
        os.replace(tmp, WAYBACK_BACKOFF)
        fcntl.flock(lf, fcntl.LOCK_UN)


def wayback_backoff_until():
    return float(_bo_read().get("until", 0))


def wayback_note_failure():
    d = _bo_read()
    fails = int(d.get("fails", 0)) + 1
    wait = min(900, 60 * (2 ** min(fails - 1, 4)))   # 60, 120, 240, 480, 900 s
    _bo_write({"until": time.time() + wait, "fails": fails, "at": now()})


def wayback_note_success():
    d = _bo_read()
    if d.get("fails"):
        _bo_write({"until": 0, "fails": 0, "at": now()})


def wayback_cdx(url, yearly=True, extra=""):
    """CDX listing of status-200 captures. yearly=True keeps the first capture per year (collapse=timestamp:4).
    Returns list of (timestamp, original)."""
    q = ("https://web.archive.org/cdx/search/cdx?url=" + urlquote(url, safe="")
         + "&output=json&filter=statuscode:200&fl=timestamp,original,digest"
         + ("&collapse=timestamp:4" if yearly else "&collapse=digest") + extra)
    r = fetch(q, check_robots=False)
    if r.get("status") != 200:
        print(f"WARNING: Wayback CDX failed for {url}: status={r.get('status')} error={r.get('error')}",
              file=sys.stderr)
    try:
        rows = json.loads(r["content"] or b"[]")[1:]
    except Exception:
        rows = []
    return [(x[0], x[1]) for x in rows]


def _decode(content):
    if isinstance(content, str):
        return content
    if content[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return content.decode("utf-16")
        except UnicodeDecodeError:
            pass
    if content[:3] == b"\xef\xbb\xbf":
        try:
            return content[3:].decode("utf-8")
        except UnicodeDecodeError:
            pass
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        pass
    m = re.search(rb'charset=["\']?([A-Za-z0-9_-]+)', content[:3000])
    if m:
        try:
            return content.decode(m.group(1).decode())
        except Exception:
            pass
    return content.decode("latin-1")


def is_pdf(content):
    return isinstance(content, bytes) and content[:5] == b"%PDF-"


def pdf_text(content):
    p = subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", "-", "-"], input=content,
                       capture_output=True, timeout=120)
    return p.stdout.decode("utf-8", "replace")


def is_html(txt):
    head = txt[:3000].lower()
    return "<html" in head or "<!doctype html" in head or "<body" in head or "<div" in head or "<p>" in head


def soup_of(content):
    from bs4 import BeautifulSoup
    txt = _decode(content)
    soup = BeautifulSoup(txt, "lxml")
    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    return soup


def page_text(content):
    """Whitespace-collapsed text: visible text for HTML, pdftotext for PDF, raw for JSON/XML/plain."""
    if is_pdf(content):
        return re.sub(r"\s+", " ", pdf_text(content)).strip()
    txt = _decode(content)
    if is_html(txt):
        txt = soup_of(content).get_text(" ")
    return re.sub(r"\s+", " ", txt).strip()


def raw_text(content):
    if is_pdf(content):
        return page_text(content)
    return re.sub(r"\s+", " ", _decode(content)).strip()


def actual_capture(row):
    """The Wayback id_ URL the bytes really came from (Wayback redirects to the nearest timestamp)."""
    fu = row.get("final_url") or ""
    if WAYBACK_RX.match(fu):
        return wb_id(fu)
    return row.get("capture_url")


def get_by_sha(sha, dbs=None):
    for p in (dbs or [DB] + RO_DBS):
        g = _ro(p)
        if g is None:
            continue
        try:
            row = g.execute("SELECT content FROM captures WHERE sha256=? AND content IS NOT NULL LIMIT 1",
                            (sha,)).fetchone()
        finally:
            g.close()
        if row:
            return zlib.decompress(row[0])
    return None


if __name__ == "__main__":
    for u in sys.argv[1:]:
        res = fetch(u)
        print(json.dumps({k: v for k, v in res.items() if k != "content"}))
        if res.get("content"):
            print(page_text(res["content"])[:3000])
        print("=" * 80)
