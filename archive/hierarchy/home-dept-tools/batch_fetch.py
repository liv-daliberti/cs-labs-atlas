"""Fetch a list of URLs (one per line in a file, or argv) round-robin across hosts; print a text window.

usage: batch_fetch.py [--grep REGEX] [--chars N] [--force] (--file F | URL...)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import argparse
import json
import re
import sys
from collections import defaultdict, deque
from urllib.parse import urlsplit

sys.path.insert(0, str(P.HIERARCHY / 'home-dept-tools'))
import capstore  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--file")
ap.add_argument("--grep", default=None)
ap.add_argument("--chars", type=int, default=1500)
ap.add_argument("--force", action="store_true")
ap.add_argument("--quiet", action="store_true")
ap.add_argument("urls", nargs="*")
a = ap.parse_args()
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
    r = capstore.fetch(u, force=a.force)
    meta = {k: r.get(k) for k in ("url", "final_url", "status", "sha256", "error", "cached")}
    print(json.dumps(meta))
    if r.get("content") and not a.quiet:
        t = capstore.page_text(r["content"])
        if a.grep:
            for m in re.finditer(a.grep, t, flags=re.I):
                s = max(0, m.start() - a.chars // 2)
                print("  ..." + t[s:m.end() + a.chars // 2] + "...")
        else:
            print(t[: a.chars])
    print("=" * 60, flush=True)
