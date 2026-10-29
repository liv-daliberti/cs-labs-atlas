"""Fetch URLs into a school's labpage capture store and print text windows.

usage: f.py SCHOOL [--grep RX] [--chars N] [--head N] [--force] [--wb] [--links RX] [--file F] URL...
  --wb        when the live fetch is not a 200 (or robots-disallowed / challenged), use the newest Wayback id_ capture
  --wbfrom/--wbto YYYY   restrict the Wayback fallback to captures in that range
  --grep RX   print windows of --chars around each match (case-insensitive) instead of the page head
  --links RX  print hrefs whose URL or anchor text matches RX
URLs on different hosts are interleaved so per-host spacing overlaps.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict, deque
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap as fscap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("school", choices=fscap.SCHOOLS)
ap.add_argument("--file")
ap.add_argument("--grep", default=None)
ap.add_argument("--chars", type=int, default=500)
ap.add_argument("--head", type=int, default=1500)
ap.add_argument("--force", action="store_true")
ap.add_argument("--wb", action="store_true")
ap.add_argument("--wbfrom", default=None)
ap.add_argument("--wbto", default=None)
ap.add_argument("--links", default=None)
ap.add_argument("--maxhits", type=int, default=12)
ap.add_argument("urls", nargs="*")
a = ap.parse_intermixed_args()
urls = list(a.urls)
if a.file:
    urls += [l.strip() for l in open(a.file) if l.strip() and not l.startswith("#")]
byhost = defaultdict(deque)
for u in urls:
    byhost[urlsplit(u).netloc].append(u)
order = []
while any(byhost.values()):
    for h in list(byhost):
        if byhost[h]:
            order.append(byhost[h].popleft())

for u in order:
    if a.wb:
        r = fscap.fetch(a.school, u, force=a.force)
        if r.get("status") != 200 and not fscap.WAYBACK_RX.match(u):
            w = fscap.wayback_latest(a.school, u, frm=a.wbfrom, to=a.wbto)
            if w:
                r = fscap.fetch(a.school, w, check_robots=False)
    else:
        r = fscap.fetch(a.school, u, force=a.force)
    meta = {k: r.get(k) for k in ("url", "final_url", "capture_url", "status", "sha256", "error", "cached")}
    print(json.dumps(meta), flush=True)
    if r.get("content") and r.get("status") == 200:
        t = fscap.page_text(r["content"], r.get("content_type"))
        print("  [len %d]" % len(t))
        if a.grep:
            n = 0
            for m in re.finditer(a.grep, t, re.I):
                s, e = max(0, m.start() - a.chars), min(len(t), m.end() + a.chars)
                print("  ...", t[s:e], "...")
                n += 1
                if n >= a.maxhits:
                    break
            if n == 0:
                print("  (no match)")
        elif a.head:
            print(" ", t[:a.head])
        if a.links:
            seen = set()
            for href, txt in fscap.links(r["content"], r.get("final_url") or u):
                if (re.search(a.links, href, re.I) or re.search(a.links, txt, re.I)) and href not in seen:
                    seen.add(href)
                    print("  LINK", href, "|", txt[:100])
    print("=" * 100, flush=True)
