"""Polite Wayback client + per-school SQLite container (ported from the Princeton listings sweep).

- At most one request per MIN_GAP (6 s; never faster than the 1.5 s ceiling) to web.archive.org, shared across all processes via a lock file.
- Manual redirect handling so every hop is rate limited; never follows a redirect to a different page.
- Exponential back-off on 429 / 5xx / network errors; never retries a 403 or a challenge page.
- Only `id_` captures are fetched. All CDX responses and fetched captures live in
  listings/<school>/captures.sqlite (zlib bodies), never as loose files.
"""
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../listings
SCHOOLS = ("cmu", "epfl", "mit", "berkeley", "stanford")
HIER = os.path.join(os.path.dirname(ROOT), "hierarchy")
LOCK = "/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/wb.lock"
MIN_GAP = 6.0  # never faster than the 1.5 s ceiling; Wayback refused connections under load (other clients share this host), so ~10/min
UA = "Mozilla/5.0 (compatible; faculty-listing-archival-research/1.0)"


def school_dir(school):
    assert school in SCHOOLS, school
    return os.path.join(ROOT, school)


def db_path(school):
    return os.path.join(school_dir(school), "captures.sqlite")


def input_path(school):
    return os.path.join(HIER, f"listings-input-{school}.json")


def db(school):
    con = sqlite3.connect(db_path(school), timeout=120)
    con.execute("""create table if not exists cdx(
        query text primary key, fetched_at text, status integer, body text)""")
    con.execute("""create table if not exists captures(
        capture_url text primary key, page_url text, department text,
        wayback_timestamp text, final_url text, http_status integer,
        fetched_at text, sha256 text, nbytes integer, content_type text,
        raw_zlib blob, blocks_json text, text text, note text)""")
    con.execute("create index if not exists captures_sha on captures(sha256)")
    con.execute("""create table if not exists plan(
        slot text, dept text, year integer, half text, page_url text, capture_url text,
        wayback_timestamp text, status text, reason text, tried text,
        primary key(slot, year, half))""")
    con.execute("create table if not exists meta(k text primary key, v text)")
    return con


def _throttle():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        s = f.read().strip()
        try:
            last = float(s) if s else 0.0
        except ValueError:
            last = 0.0
        wait = last + MIN_GAP - time.time()
        if wait > 0:
            time.sleep(wait)
        f.seek(0)
        f.truncate()
        f.write(repr(time.time()))
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(NoRedirect)


def _orig(u):
    m = re.match(r"https?://web\.archive\.org/web/\d+(?:id_)?/(.*)$", u)
    o = m.group(1) if m else u
    o = re.sub(r"^https?://", "", o)
    o = re.sub(r"^(www\.)", "", o)
    o = re.sub(r":80(?=/)|:443(?=/)", "", o)
    return o.rstrip("/").lower()


def _same_page(a, b):
    if not b.startswith("https://web.archive.org/"):
        return False
    return _orig(a) == _orig(b)


def raw_get(url, max_hops=6, timeout=90):
    """Return (final_url, status, headers, body). Follows same-page redirects manually."""
    hops = 0
    backoff = 30
    while True:
        _throttle()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
        try:
            resp = _opener.open(req, timeout=timeout)
            body = resp.read()
            return url, resp.status, dict(resp.headers), body
        except urllib.error.HTTPError as e:
            code = e.code
            if code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location")
                if not loc or hops >= max_hops:
                    return url, code, dict(e.headers), b""
                nxt = urllib.parse.urljoin(url, loc)
                if not _same_page(url, nxt):
                    # never follow an archived redirect to a different page (e.g. a login or another listing)
                    return nxt, code, dict(e.headers), b""
                url = nxt
                hops += 1
                continue
            if code == 429 or code >= 500:
                # a capture that keeps failing is usually broken in Wayback: give up sooner than on CDX
                if backoff > (960 if "/cdx/" in url else 120):
                    return url, code, dict(e.headers), b""
                ra = e.headers.get("Retry-After")
                w = int(ra) if ra and ra.isdigit() else backoff
                print(f"  [{code}] backing off {w}s on {url}", flush=True)
                time.sleep(w)
                backoff *= 2
                continue
            try:
                b = e.read()
            except Exception:
                b = b""
            return url, code, dict(e.headers), b
        except Exception as e:  # timeouts, resets
            if backoff > 480:
                return url, -1, {}, repr(e).encode()
            print(f"  [err {e!r}] backing off {backoff}s on {url}", flush=True)
            time.sleep(backoff)
            backoff *= 2


def cdx(params, con, refresh=False):
    """Query the CDX API (json output); cached in sqlite."""
    q = "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(params)
    row = con.execute("select status, body from cdx where query=?", (q,)).fetchone()
    if row and not refresh and row[0] == 200:
        body = row[1]
    else:
        _, st, _, b = raw_get(q)
        body = b.decode("utf-8", "replace")
        con.execute("insert or replace into cdx values(?,?,?,?)",
                    (q, time.strftime("%Y-%m-%dT%H:%M:%S"), st, body))
        con.commit()
        if st != 200:
            print("  CDX status", st, q, body[:200], flush=True)
            return None
    body = body.strip()
    if not body:
        return []
    rows = json.loads(body)
    if not rows:
        return []
    hdr = rows[0]
    return [dict(zip(hdr, r)) for r in rows[1:]]


def fetch_capture(ts, original, page_url, department, con, refresh=False):
    cap = f"https://web.archive.org/web/{ts}id_/{original}"
    row = con.execute("select http_status, sha256 from captures where capture_url=?", (cap,)).fetchone()
    if row and not refresh and row[0] not in (-1, 429) and not (row[0] or 0) >= 500:
        return cap
    final, st, hdrs, body = raw_get(cap)
    sha = hashlib.sha256(body).hexdigest() if body else None
    con.execute("""insert or replace into captures(capture_url,page_url,department,wayback_timestamp,
        final_url,http_status,fetched_at,sha256,nbytes,content_type,raw_zlib,blocks_json,text,note)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cap, page_url, department, ts, final, st, time.strftime("%Y-%m-%dT%H:%M:%S"),
                 sha, len(body), hdrs.get("Content-Type") or hdrs.get("content-type"),
                 zlib.compress(body, 6) if body else None, None, None,
                 json.dumps({k: v for k, v in hdrs.items() if k.lower() in ("content-encoding", "content-type", "x-archive-src", "memento-datetime")})))
    con.commit()
    return cap
