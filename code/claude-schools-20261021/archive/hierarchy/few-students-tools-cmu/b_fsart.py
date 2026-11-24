"""Fetch figshare article JSON(s) and print author, date, degree, department, advisors. usage: b_fsart.py ID..."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, sys
sys.path.insert(0, str(P.HIERARCHY / 'few-students-tools-cmu'))
import capstore
for i in sys.argv[1:]:
    r = capstore.fetch("https://api.figshare.com/v2/articles/" + i)
    try:
        d = json.loads(r["content"])
    except Exception as e:
        print(i, "ERR", r.get("status"), e); continue
    cf = {c["name"]: c["value"] for c in d.get("custom_fields", [])}
    print(i, "|", [a["full_name"] for a in d.get("authors", [])], "|", cf.get("Date"), "|", cf.get("Degree Type"), "|",
          cf.get("Thesis Department"), "|", "ADV:", cf.get("Advisor(s)"), "|", d.get("title", "")[:70], "| inst", d.get("institution_id") if "institution_id" in d else "")
