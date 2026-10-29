"""Fetch one Wayback id_ capture per year (distinct digests, status 200) of URL and print grep windows.

usage: wbscan.py URL [--grep RX] [--years 2016-2026] [--w 400] [--prefix]  (--prefix: url is a prefix match)
"""
import argparse
import re
import sys

sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-berkeley")
import capstore  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("url")
ap.add_argument("--grep", default=None)
ap.add_argument("--years", default="2016-2026")
ap.add_argument("--w", type=int, default=400)
ap.add_argument("--max", type=int, default=3)
ap.add_argument("--head", type=int, default=600)
ap.add_argument("--list", action="store_true")
a = ap.parse_args()
y0, y1 = map(int, a.years.split("-"))
rows = capstore.wayback_cdx(a.url)
print("captures:", len(rows))
byyear = {}
for ts, orig in rows:
    y = int(ts[:4])
    if y0 <= y <= y1:
        byyear[y] = (ts, orig)  # keep the latest of each year
if a.list:
    for ts, orig in rows:
        print(" ", ts, orig)
for y in sorted(byyear):
    ts, orig = byyear[y]
    u = f"https://web.archive.org/web/{ts}id_/{orig}"
    r = capstore.fetch(u, check_robots=False)
    print(f"== {y} {u} status={r.get('status')} sha={(r.get('sha256') or '')[:12]}")
    if r.get("status") != 200 or not r.get("content"):
        continue
    t = capstore.page_text(r["content"])
    if a.grep:
        n = 0
        for m in re.finditer(a.grep, t, flags=re.I):
            print("  >>", t[max(0, m.start() - a.w // 4):m.end() + a.w])
            n += 1
            if n >= a.max:
                break
        if n == 0:
            print("  (no match)", t[:200])
    else:
        print("  ", t[:a.head])
