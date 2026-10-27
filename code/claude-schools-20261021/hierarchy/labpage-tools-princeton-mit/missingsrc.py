"""List plan people/pubs URLs (live, not Wayback) that have no stored 200 capture. usage: missingsrc.py SCHOOL"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpev  # noqa: E402

school = sys.argv[1]
P = importlib.import_module(f"plan_{school}").P
for pi, plan in P.items():
    for u in list(plan.get("people", [])) + list(plan.get("auto", [])) + [p.get("pubs_page") for p in plan.get("pubs", []) if p.get("pubs_page")]:
        try:
            lpev.cap(school, u)
        except KeyError:
            print(u)
