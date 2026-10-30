"""Query theses_index.json (built by harvest_theses.py from reports-archive.adm.cs.cmu.edu, 2016-2026).

usage: theses.py REGEX [--any]
  default: theses whose committee names a chair/advisor matching REGEX (case-insensitive)
  --any:   theses whose committee text mentions REGEX anywhere (chair not marked, or plain member)
Prints report, degree, author/title head, chairs, committee, url.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json
import re
import sys

IDX = str(P.HIERARCHY / 'few-students-tools-cmu/theses_index.json')
rx = re.compile(sys.argv[1], re.I)
anyw = "--any" in sys.argv
rows = json.load(open(IDX))
n = 0
for r in rows:
    chairs = r.get("chairs") or []
    hit = any(rx.search(c) for c in chairs) if not anyw else bool(rx.search(r.get("committee") or ""))
    if hit:
        n += 1
        print(f"{r.get('report')} | {r.get('degree')} | {(r.get('head') or r.get('entry') or '')[-160:]}")
        print(f"    chairs={chairs}")
        print(f"    committee={(r.get('committee') or '')[:300]}")
        print(f"    {r['url']}")
print(n, "matches of", len(rows), "indexed theses")
