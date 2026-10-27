"""Merge per-lab overrides into manual_pages.json. usage: setman.py SCHOOL < JSON {pi: {key: value}}"""
import json, os, sys
TOOLS = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, TOOLS)
import lplab  # noqa: E402
p = f"{TOOLS}/manual_pages.json"
M = json.load(open(p))
school = sys.argv[1]
upd = json.load(sys.stdin)
pis = {r["pi"] for r in lplab.rows(school)}
for pi, d in upd.items():
    if pi not in pis:
        sys.exit(f"unknown pi {pi!r}")
    M.setdefault(school, {}).setdefault(pi, {}).update(d)
json.dump(M, open(p, "w"), ensure_ascii=False, indent=1)
print("ok", len(M[school]))
