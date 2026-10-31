"""Worker C: KiltHub (figshare API) thesis lookup. usage: c_fs.py "<search phrase>" SURNAME_REGEX [--pages N]
Searches theses (item_type 8) for the phrase, fetches each article JSON (cached in the capture DB), and prints
those whose Advisor(s) field matches SURNAME_REGEX: id, date, author(s), department, degree, advisors.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json
import re
import sys

sys.path.insert(0, str(P.HIERARCHY / 'few-students-tools-cmu'))
import capstore  # noqa: E402

q, rx = sys.argv[1], re.compile(sys.argv[2], re.I)
pages = int(sys.argv[sys.argv.index("--pages") + 1]) if "--pages" in sys.argv else 1
ids = []
for p in range(1, pages + 1):
    payload = {"search_for": q, "page_size": 100, "item_type": 8}
    if p > 1:
        payload["page"] = p
    r = capstore.post_json("https://api.figshare.com/v2/articles/search", payload)
    try:
        arr = json.loads(r["content"])
    except Exception:
        print("search failed", r.get("status"), r.get("error"))
        break
    ids += [a["id"] for a in arr]
    if len(arr) < 100:
        break
print(len(ids), "theses for", q)
for i in ids:
    r = capstore.fetch(f"https://api.figshare.com/v2/articles/{i}")
    try:
        d = json.loads(r["content"])
    except Exception:
        print("  fetch failed", i, r.get("status"))
        continue
    cf = {c["name"]: c.get("value") for c in d.get("custom_fields", [])}
    adv = cf.get("Advisor(s)") or ""
    if isinstance(adv, list):
        adv = ", ".join(adv)
    if not rx.search(adv):
        continue
    au = "; ".join(a["full_name"] for a in d.get("authors", []))
    print(f"  {i} | {cf.get('Date')} | {au} | {cf.get('Thesis Department')} | {cf.get('Degree Name')} | adv: {adv} | {d.get('title','')[:80]}")
