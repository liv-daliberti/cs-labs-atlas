"""Wayback history for a lab page: list the distinct-digest 200 captures of URL (CDX, trailing-slash and http/https
variants tried) and fetch up to N id_ captures spread over the years (earliest in the window, latest, and evenly in
between), stored in the capture store like any other fetch. Prints each capture's id_ URL, sha256 and text head.

usage: wb3.py SCHOOL URL [--n 3] [--from 2016] [--to 2026] [--head 600] [--grep RX] [--list]
  --list   only list the CDX captures by year (no fetch of captures)
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("school", choices=lpcap.SCHOOLS)
ap.add_argument("url")
ap.add_argument("--n", type=int, default=3)
ap.add_argument("--from", dest="frm", default="2016")
ap.add_argument("--to", default="2026")
ap.add_argument("--head", type=int, default=600)
ap.add_argument("--grep", default=None)
ap.add_argument("--chars", type=int, default=300)
ap.add_argument("--list", action="store_true")
a = ap.parse_args()

u = a.url
variants = [u]
if u.endswith("/"):
    variants.append(u.rstrip("/"))
else:
    variants.append(u + "/")
rows = []
for v in variants:
    rows = lpcap.wayback_cdx(a.school, v, frm=a.frm, to=a.to)
    if rows:
        break
by_year = {}
for ts, orig, dig in rows:
    by_year.setdefault(ts[:4], []).append((ts, orig, dig))
print(f"{len(rows)} distinct captures; per year: " + ", ".join(f"{y}:{len(v)}" for y, v in sorted(by_year.items())))
if a.list or not rows:
    sys.exit(0)
years = sorted(by_year)
pick = []
if len(rows) <= a.n:
    pick = list(rows)
elif len(years) < a.n:
    idx = sorted({round(i * (len(rows) - 1) / (a.n - 1)) for i in range(a.n)})
    pick = [rows[i] for i in idx]
elif len(years) == a.n:
    pick = [by_year[y][-1] for y in years]
else:
    idx = sorted({round(i * (len(years) - 1) / (a.n - 1)) for i in range(a.n)}) if a.n > 1 else [len(years) - 1]
    pick = [by_year[years[i]][-1] for i in idx]
for ts, orig, dig in pick:
    w = lpcap.wayback_id(ts, orig)
    r = lpcap.fetch(a.school, w, check_robots=False)
    print({"capture_url": w, "status": r.get("status"), "sha256": r.get("sha256"), "error": r.get("error")}, flush=True)
    if r.get("status") == 200 and r.get("content"):
        t = lpcap.page_text(r["content"], r.get("content_type"))
        print(f"  [len {len(t)}]")
        if a.grep:
            n = 0
            for m in re.finditer(a.grep, t, re.I):
                print("  ...", t[max(0, m.start() - a.chars):m.end() + a.chars], "...")
                n += 1
                if n >= 10:
                    break
        elif a.head:
            print(" ", t[:a.head])
    print("-" * 80, flush=True)
