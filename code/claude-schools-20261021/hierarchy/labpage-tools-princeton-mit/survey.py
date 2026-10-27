"""Run autom.extract over every stored 200 HTML page of each lab's dossier (profile pages skipped) and summarise:
names found, held matched, unflagged new names. Writes T/survey_<school>.json; prints one block per lab.
usage: survey.py SCHOOL [PI ...]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autom  # noqa: E402
import lpcap  # noqa: E402

school = sys.argv[1]
only = sys.argv[2:]
T = os.path.dirname(os.path.abspath(__file__))
labs = json.load(open(f"{lpcap.ROOT}/{school}/labpage-input.json"))
dos = json.load(open(f"{T}/dossier_{school}.json"))
PROFILE = re.compile(r"(cs\.princeton\.edu/people/profile|eecs\.mit\.edu/people/|csail\.mit\.edu/person/)")
out = {}
for lab in labs:
    pi = lab["pi"]
    if only and pi not in only:
        continue
    d = dos.get(pi, {})
    res = []
    seen = set()
    for p in d.get("pages", []):
        if p.get("status") != 200 or not p.get("sha256") or p["sha256"] in seen:
            continue
        seen.add(p["sha256"])
        u = p.get("capture_url") or p["url"]
        if PROFILE.search(p["url"]) and not re.search(r"/~", p["url"]):
            continue
        try:
            rows = autom.extract(school, p["sha256"], pi, lab["students_held"])
        except Exception as e:
            res.append({"url": u, "kind": p["kind"], "error": repr(e)[:120]})
            continue
        held = {x["held"] for x in rows if x["held"]}
        new = [x["name"] for x in rows if not x["held"] and not x["flags"]]
        res.append({"url": u, "sha": p["sha256"], "kind": p["kind"], "chars": p.get("chars"), "names": len(rows),
                    "held": len(held), "new": len(new), "new_sample": new[:8],
                    "heads": sorted({x["head"] for x in rows if x["head"]})[:8]})
    out[pi] = {"held_total": len(lab["students_held"]), "pages": res, "people_links": d.get("people_links", []),
               "pubs_links": d.get("pubs_links", []), "site_links": d.get("site_links", [])}
json.dump(out, open(f"{T}/survey_{school}.json", "w"), indent=1, ensure_ascii=False)
for pi, v in out.items():
    print(f"=== {pi} (held {v['held_total']})")
    for r in v["pages"]:
        if r.get("error"):
            print(f"   ERR {r['url']} {r['error']}")
            continue
        if r["names"] == 0 and r["kind"] not in ("people",):
            print(f"   .   {r['kind']:<6} {r['chars']:>6}c {r['url']}")
            continue
        print(f"   {r['kind']:<6} {r['chars']:>6}c names {r['names']:>3} held {r['held']:>3} new {r['new']:>3} {r['url']}")
        if r["new"]:
            print(f"          new: {', '.join(r['new_sample'])}")
    print(f"   pubs_links: {v['pubs_links'][:4]}")
