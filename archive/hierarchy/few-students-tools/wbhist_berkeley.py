"""Fetch one Wayback id_ capture per year (the last capture of each listed year) of a URL, and grep it.
usage: wbhist_berkeley.py URL YEARS(comma list or 'all') [--grep RX] [--chars N]"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fscap  # noqa: E402
ap = argparse.ArgumentParser()
ap.add_argument("url"); ap.add_argument("years")
ap.add_argument("--grep"); ap.add_argument("--chars", type=int, default=300); ap.add_argument("--head", type=int, default=0)
ap.add_argument("--school", default="berkeley")
a = ap.parse_args()
rows = fscap.wayback_cdx(a.school, a.url)
by = {}
for ts, orig, dig in rows:
    by[ts[:4]] = (ts, orig)
print("captures by year:", {y: v[0] for y, v in sorted(by.items())}, flush=True)
ys = sorted(by) if a.years == "all" else [y for y in a.years.split(",") if y in by]
for y in ys:
    ts, orig = by[y]
    w = fscap.wayback_id(ts, orig)
    r = fscap.fetch(a.school, w, check_robots=False)
    print("==", y, w, r.get("status"), r.get("sha256"), r.get("error"), flush=True)
    if r.get("status") == 200:
        t = fscap.page_text(r["content"], r.get("content_type"))
        if a.head:
            print("  ", t[:a.head])
        if a.grep:
            for m in list(re.finditer(a.grep, t, re.I))[:6]:
                print("   ...", t[max(0, m.start() - 60):m.end() + a.chars])
