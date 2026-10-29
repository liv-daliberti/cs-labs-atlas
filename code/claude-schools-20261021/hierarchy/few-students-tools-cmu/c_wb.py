"""Worker C: Wayback helper with polite back-off on refused connections (archive.org throttling).

usage: c_wb.py cdx URL [--prefix] [--from YYYY]      list distinct 200 captures (timestamp original)
       c_wb.py get WAYBACK_ID_URL [--grep RX] [--w N] [--head N]
"""
import re
import sys
import time

sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/few-students-tools-cmu")
import capstore  # noqa: E402

BACKOFF = [30, 90, 180]


def fetch_retry(url):
    r = capstore.fetch(url, check_robots=False)
    for b in BACKOFF:
        if r.get("status") is not None:
            return r
        print(f"  (error {str(r.get('error'))[:60]}; backing off {b}s)", flush=True)
        time.sleep(b)
        r = capstore.fetch(url, check_robots=False)
    return r


def cdx(url, prefix=False, frm=None):
    import json
    import requests
    q = ("https://web.archive.org/cdx/search/cdx?url=" + requests.utils.quote(url, safe="")
         + "&output=json&filter=statuscode:200&fl=timestamp,original,digest&collapse=digest")
    if prefix:
        q += "&matchType=prefix"
    if frm:
        q += "&from=" + frm
    r = fetch_retry(q)
    try:
        return [(x[0], x[1]) for x in json.loads(r["content"] or b"[]")[1:]]
    except Exception:
        return []


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "cdx":
        frm = a[a.index("--from") + 1] if "--from" in a else None
        rows = cdx(a[1], "--prefix" in a, frm)
        for ts, o in rows:
            if not re.search(r"\.(jpg|jpeg|png|gif|css|js|ico|woff2?)(\?|$)", o, re.I):
                print(ts, o)
        print(len(rows), "captures")
    else:
        r = fetch_retry(a[1])
        print({k: r.get(k) for k in ("url", "capture_url", "status", "sha256", "error")})
        if r.get("content"):
            t = capstore.page_text(r["content"])
            if "--grep" in a:
                rx = a[a.index("--grep") + 1]
                w = int(a[a.index("--w") + 1]) if "--w" in a else 400
                for m in list(re.finditer(rx, t, re.I))[:8]:
                    print("  >>", t[max(0, m.start() - w // 4):m.end() + w])
            else:
                h = int(a[a.index("--head") + 1]) if "--head" in a else 3000
                print(t[:h])
