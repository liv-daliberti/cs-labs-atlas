"""Find Wayback captures (CDX, status 200, distinct digests) of URL and fetch id_ captures newest-first
until one's text matches REQUIRE regex (and not REJECT regex). Stores every fetch in the capture DB.
usage: wayback_fetch.py URL [--require RX] [--reject RX] [--max N]
"""
import argparse, json, re, sys
sys.path.insert(0, "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/home-dept-tools")
import capstore

ap = argparse.ArgumentParser()
ap.add_argument("url")
ap.add_argument("--require", default=None)
ap.add_argument("--reject", default=r"Access denied|You must log in")
ap.add_argument("--max", type=int, default=4)
a = ap.parse_args()
cdx = ("https://web.archive.org/cdx/search/cdx?url=" + capstore.requests.utils.quote(a.url, safe="")
       + "&output=json&filter=statuscode:200&fl=timestamp,digest&collapse=digest")
r = capstore.fetch(cdx, check_robots=False)
rows = []
try:
    rows = json.loads(r["content"] or b"[]")[1:]
except Exception as e:
    print("CDX parse error", e, (r.get("content") or b"")[:200])
print("captures:", len(rows), [x[0] for x in rows[-8:]])
tried = 0
for ts, dig in reversed(rows):
    if tried >= a.max:
        break
    tried += 1
    u = f"https://web.archive.org/web/{ts}id_/{a.url}"
    res = capstore.fetch(u, check_robots=False)
    if res.get("status") != 200:
        print("  fail", u, res.get("status"), res.get("error")); continue
    t = capstore.page_text(res["content"])
    ok = (a.require is None or re.search(a.require, t, re.I)) and not (a.reject and re.search(a.reject, t, re.I))
    print(("  OK  " if ok else "  skip"), u, res["sha256"][:12], len(t))
    if ok:
        print("RESULT", json.dumps({"capture_url": u, "sha256": res["sha256"]}))
        break
