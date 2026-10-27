"""Lab-page decisions for princeton labs, built from the reviewed plan plan_princeton.py (people pages, Wayback history in
wb_princeton.json, reviewer corrections, publication pages) by lpauto.rows_for: every member row is an lpev.M row whose quote
is an exact substring of the stored capture and contains the name. See lpauto.py for the rules applied.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpauto  # noqa: E402
from lpev import Lab  # noqa: E402
from plan_princeton import P  # noqa: E402

SCH = "princeton"
_labs = {l["pi"]: l for l in json.load(open(f"{lpauto.lpev.lpcap.ROOT}/{SCH}/labpage-input.json"))}
_only = json.loads(os.environ.get("LP_ONLY", "null"))
D = {}
for _pi, _plan in P.items():
    if _only and _pi not in _only:
        continue
    _ppl = (_plan.get("people") or [None])[0]
    D[_pi] = Lab(lab_site=_plan.get("site"), people_page=_plan.get("people_page", _ppl),
                 students=lpauto.rows_for(SCH, _pi, _labs[_pi]["students_held"], _plan), pubs=_plan.get("pubs", []),
                 notes=_plan.get("notes", ""), other_pages=_plan.get("other_pages", []))
