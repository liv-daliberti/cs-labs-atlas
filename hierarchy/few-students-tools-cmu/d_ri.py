"""RI site search via the WordPress REST search endpoint (robots-allowed), all pages.

usage: d_ri.py QUERY [--sub ri-people|tribe_events|publications|...] [--fetch REGEX] [--grep REGEX]
  --fetch REGEX  fetch result pages whose title matches REGEX and print grep windows (--grep, default Committee|Advis)
"""
import argparse
import json
import re
import sys
from urllib.parse import quote

sys.path.insert(0, "/n/fs/resemble/cs-atlas/work/hierarchy/few-students-tools-cmu")
import capstore  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("q")
ap.add_argument("--sub", default=None)
ap.add_argument("--fetch", default=None)
ap.add_argument("--grep", default=r"Committee|Advis|Chair")
ap.add_argument("--w", type=int, default=500)
a = ap.parse_args()
res = []
for page in range(1, 11):
    u = f"https://www.ri.cmu.edu/wp-json/wp/v2/search?search={quote(a.q)}&per_page=100&page={page}"
    r = capstore.fetch(u)
    if r.get("status") != 200:
        break
    try:
        d = json.loads(r["content"])
    except Exception:
        break
    if not d:
        break
    res += d
    if len(d) < 100:
        break
for x in res:
    if a.sub and x.get("subtype") != a.sub:
        continue
    print(x.get("subtype"), "|", x.get("title"), "|", x.get("url"))
print(len(res), "results")
if a.fetch:
    for x in res:
        if a.sub and x.get("subtype") != a.sub:
            continue
        if not re.search(a.fetch, x.get("title") or "", re.I):
            continue
        r = capstore.fetch(x["url"])
        print("==", x["title"], x["url"], r.get("status"))
        if r.get("status") == 200:
            t = capstore.page_text(r["content"])
            n = 0
            for m in re.finditer(a.grep, t):
                print("  >>", t[max(0, m.start() - a.w // 2):m.end() + a.w])
                n += 1
                if n >= 2:
                    break
