"""Print the hunt's summary from hierarchy/thesis-harvest-report.json (or thesis-tools/out/ with --draft): per-school
counts, the PIs with the most additions, and non-PI advisers of 3+ CS-relevant theses (census status shown).
usage: summarize.py [--draft] [--min N]"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = str(P.HIERARCHY)
draft = "--draft" in sys.argv
mn = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 3
rep = json.load(open(f"{HERE}/out/thesis-harvest-report.json" if draft else f"{ROOT}/thesis-harvest-report.json"))
top = []
for s, r in rep["schools"].items():
    print(f"{s:10} harvested {r['theses_harvested']:6}  cs-relevant {r['theses_cs_relevant']:5}  with PI adviser {r['theses_with_pi_adviser']:5}  "
          f"pairs found {r['pairs_found']:5}  already held {r['pairs_already_held']:5}  added {r['pairs_added']:4}  "
          f"PIs with additions {r['pis_with_additions']:3}  quote failures {len(r['quote_failures'])}")
    ev = json.load(open(f"{HERE}/out/{s}-thesis-evidence.json" if draft else f"{ROOT}/{s}/thesis-evidence.json"))
    for e in ev:
        roles = {}
        for x in e["students"]:
            roles[x["role"]] = roles.get(x["role"], 0) + 1
        top.append((len(e["students"]), s, e["pi"], roles))
print("\nTop PIs by additions:")
for n, s, pi, roles in sorted(top, key=lambda x: -x[0])[:15]:
    print(f"  {n:3}  {s:9} {pi}  {roles}")
print(f"\nNon-PI advisers of {mn}+ CS-relevant theses:")
for s, L in rep["non_pi_advisers"].items():
    sel = [x for x in L if x["theses"] >= mn]
    print(f"  {s}: {len(sel)}")
    for x in sel:
        c = x.get("census") or {}
        tag = (f"census: {c.get('rank') or ''} {c.get('departments') or c.get('units') or ''} is_pi={c.get('is_pi')}" if c else "not in census")
        print(f"    {x['theses']:3}  {x['adviser']}  [{tag}]  years {min(x['years'])}-{max(x['years'])}")
