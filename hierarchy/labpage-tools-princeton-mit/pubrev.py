"""Review publication extraction for every Pubs page in plan_<school>.py: entries, in-window, missing, and sample
missing titles (to spot pages that need a spec). usage: pubrev.py SCHOOL [PI ...]"""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubx  # noqa: E402

school = sys.argv[1]
only = sys.argv[2:]
P = importlib.import_module(f"plan_{school}").P
for pi, plan in P.items():
    if only and pi not in only:
        continue
    for p in plan.get("pubs", []):
        if "pubs_page" not in p:
            continue
        try:
            r, ents = pubx.extract(school, p["pubs_page"], p.get("spec"))
            _, inwin, miss = pubx.missing(school, pi, p["pubs_page"], p.get("spec"))
        except Exception as e:
            print(f"== {pi} | {p['pubs_page']} ERROR {e!r}"[:300])
            continue
        print(f"== {pi} | {p['pubs_page']} | entries {len(ents)} in-window {len(inwin)} missing {len(miss)} | lab papers {len(pubx.lab_titles(school, pi))}")
        random.seed(1)
        for e in random.sample(miss, min(4, len(miss))):
            print(f"     {e['year']} | {e['title'][:100]} | {str(e.get('venue'))[:30]}")
