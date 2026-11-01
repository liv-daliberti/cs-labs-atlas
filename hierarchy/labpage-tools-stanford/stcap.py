"""Stanford support for the lab-page publication pass (2026-10-27): reuses the EPFL/Berkeley modules unchanged
(../labpage-tools-epfl-berkeley: lpcap store + polite fetcher, lppubs parser, lpdom, lplab) and only registers the
Stanford store:
  hierarchy/stanford/labpage-captures.sqlite   (lpcap schema; this pass is its only writer)
  sister stores (read-only, copied in unchanged with copied_from): hierarchy/stanford/thesis-captures.sqlite
  base-sweep live store (read-only): claude-stanford-20261027/raw/captures.sqlite table live -> copied in unchanged
  (same bytes, sha256 and fetched_at; copied_from='claude-stanford-20261027/raw/captures.sqlite:live').
Rate limiting is lpcap's: flock'd per-host stamps in the shared gap-ratelimit directory (archive.org shared by all
workers), robots.txt honoured, bot challenges stored and never retried, dblp/eScholarship/Scholar refused.
Import this module before lplab/lppubs."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib
import os
import sqlite3
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
EB = os.path.join(os.path.dirname(HERE), "labpage-tools-epfl-berkeley")
if EB not in sys.path:
    sys.path.insert(0, EB)
import lpcap  # noqa: E402

S = "stanford"
lpcap.DBS[S] = lpcap.data("labpage-captures.sqlite", S)
lpcap.SISTER[S] = [lpcap.data("thesis-captures.sqlite", S)]
BASE_LIVE = str(P.SWEEPS / 'claude-stanford-20261027/raw/captures.sqlite')

_orig_cached = lpcap.cached


def cached(school, url, sister=True):
    r = _orig_cached(school, url, sister)
    if r or school != S or not sister or lpcap.WAYBACK_RX.match(url) or not os.path.exists(BASE_LIVE):
        return r
    b = sqlite3.connect(f"file:{BASE_LIVE}?mode=ro", uri=True, timeout=60)
    try:
        row = b.execute("SELECT url, fetched_at, status, sha256, content_type, raw_zlib FROM live WHERE url=? AND status=200 "
                        "AND raw_zlib IS NOT NULL", (url,)).fetchone()
    finally:
        b.close()
    if not row:
        return None
    body = zlib.decompress(row[5])
    if hashlib.sha256(body).hexdigest() != row[3]:
        return None
    con = lpcap.connect(school)
    rid, _ = lpcap._insert(con, row[0], row[0], None, 200, body, row[4], None, fetched_at=row[1],
                           copied_from="claude-stanford-20261027/raw/captures.sqlite:live", sha=row[3])
    con.close()
    return {"id": rid, "url": row[0], "final_url": row[0], "capture_url": None, "status": 200, "sha256": row[3],
            "content_type": row[4], "content": body, "error": None, "fetched_at": row[1], "cached": True,
            "copied_from": BASE_LIVE}


lpcap.cached = cached

_orig_fetch = lpcap.fetch


def fetch(school, url, *a, **k):
    """lpcap.fetch, plus: a response that redirected to an off-limits host (Scholar, dblp, eScholarship) is not kept
    (content discarded, error recorded) and is returned as an error."""
    r = _orig_fetch(school, url, *a, **k)
    fu = r.get("final_url") or ""
    if fu and lpcap.blocked(fu) and r.get("content"):
        if r.get("id"):
            con = lpcap.connect(school)
            con.execute("UPDATE captures SET content=NULL, status=NULL, error=? WHERE id=?",
                        ("redirected-to-off-limits-host; content discarded", r["id"]))
            con.commit()
            con.close()
        return {"url": r.get("url"), "capture_url": r.get("capture_url"), "status": None,
                "error": "redirected-to-off-limits-host", "content": b""}
    return r


lpcap.fetch = fetch
