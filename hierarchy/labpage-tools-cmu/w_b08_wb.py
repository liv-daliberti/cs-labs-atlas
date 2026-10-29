"""b08 helper: Wayback CDX / capture fetch with polite backoff on connection errors (web.archive.org has been
refusing connections intermittently). All fetches go through capstore (rate limit, caching).

  w_b08_wb.py cdx URL [URL ...] [--all]     yearly (or all distinct) 200 captures; prints ERROR on failure
  w_b08_wb.py get CAPTURE_URL [...]         fetch Wayback id_ captures (stored in LABPAGE_DB); prints status
"""
import sys
import os
import time
import json
from urllib.parse import quote as urlquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstore  # noqa: E402

BACKOFF = [15, 45, 90]


def cdx(url, yearly=True):
    q = ("https://web.archive.org/cdx/search/cdx?url=" + urlquote(url, safe="")
         + "&output=json&filter=statuscode:200&fl=timestamp,original,digest"
         + ("&collapse=timestamp:4" if yearly else "&collapse=digest"))
    for i in range(len(BACKOFF) + 1):
        r = capstore.fetch(q, check_robots=False)
        if r.get("status") == 200:
            try:
                rows = json.loads(r["content"] or b"[]")[1:]
            except Exception:
                rows = []
            return [(x[0], x[1]) for x in rows], None
        err = r.get("error") or f"status={r.get('status')}"
        if i < len(BACKOFF):
            time.sleep(BACKOFF[i])
    return None, err


def get(cap):
    for i in range(len(BACKOFF) + 1):
        r = capstore.fetch(cap)
        if r.get("status") is not None:
            return r
        if i < len(BACKOFF):
            time.sleep(BACKOFF[i])
    return r


def main():
    a = sys.argv[1:]
    cmd = a.pop(0)
    allc = "--all" in a
    a = [x for x in a if x != "--all"]
    if cmd == "cdx":
        for u in a:
            rows, err = cdx(u, yearly=not allc)
            if rows is None:
                print(f"== {u}: ERROR {err[:120]}", flush=True)
                continue
            print(f"== {u}: {len(rows)} captures", flush=True)
            for ts, o in rows:
                print(f"   {ts} https://web.archive.org/web/{ts}id_/{o}", flush=True)
    elif cmd == "get":
        for u in a:
            r = get(u)
            print(f"{r.get('status')} err={str(r.get('error'))[:80]} cached={r.get('cached')} {u}", flush=True)


if __name__ == "__main__":
    main()
