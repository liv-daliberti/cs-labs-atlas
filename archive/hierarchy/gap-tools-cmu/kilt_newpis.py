"""(copy of few-students-tools-cmu/d_kilt.py writing to the gap capture store; new-PI gap research 2026-10-22)
KiltHub (figshare API) thesis search: list theses matching QUERY published >= 2016, fetch each article JSON and
print author, date, department, Advisor(s); flag those whose advisor field matches ADVISOR_REGEX.

usage: d_kilt.py QUERY ADVISOR_REGEX [--all]   (--all: also print non-matching theses)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json
import re
import sys

sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-cmu'))
import capstore  # noqa: E402

q, arx = sys.argv[1], re.compile(sys.argv[2], re.I)
show_all = "--all" in sys.argv
r = capstore.post_json("https://api.figshare.com/v2/articles/search", {"search_for": q, "page_size": 200, "item_type": 8})
try:
    arts = json.loads(r["content"])
except Exception:
    print("search failed", r.get("status"), r.get("error"))
    sys.exit()
print(len(arts), "theses for", q)
for a in arts:
    pd = (a.get("published_date") or "")[:10]
    if pd[:4] < "2016":
        continue
    rr = capstore.fetch("https://api.figshare.com/v2/articles/%d" % a["id"])
    try:
        d = json.loads(rr["content"])
    except Exception:
        print("  fetch failed", a["id"])
        continue
    cf = {c["name"]: c.get("value") for c in d.get("custom_fields", [])}
    adv = cf.get("Advisor(s)") or ""
    if isinstance(adv, list):
        adv = ", ".join(adv)
    hit = bool(arx.search(adv))
    if hit or show_all:
        authors = ", ".join(x.get("full_name", "") for x in d.get("authors", []))
        print(("HIT " if hit else "    "), a["id"], cf.get("Date"), "|", authors, "|", cf.get("Thesis Department"), "|", cf.get("Degree Type"), "| Advisor(s):", adv, "|", (d.get("title") or "")[:80])
