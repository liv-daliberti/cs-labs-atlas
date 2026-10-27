"""b07 helper: print a slice of the cached raw HTML of a URL (cache only, never fetches).
usage: w_b07_raw.py URL [--grep RX] [--start N] [--len N]
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstore  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("url")
p.add_argument("--grep")
p.add_argument("--start", type=int, default=0)
p.add_argument("--len", type=int, default=3000)
a = p.parse_args()
r = capstore.cached(a.url)
if not r:
    print("not cached")
    sys.exit(1)
html = capstore._decode(r.get("content") or b"")
print("len", len(html))
if a.grep:
    for m in list(re.finditer(a.grep, html))[:20]:
        s = max(0, m.start() - 200)
        print("@", m.start(), repr(html[s:m.end() + 300]))
else:
    print(html[a.start:a.start + a.len])
