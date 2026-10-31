"""Build hierarchy/<school>/gap-evidence.json from decisions_<school>.py and re-verify every quote against stored bytes.

usage: build.py SCHOOL [--check-only]
decisions_<school>.py defines ROWS: a list of dicts {pi, status, status_evidence, students, identity, collection_person_id,
appointment_notes, notes} whose evidence items were built with evlib (url, capture_url?, sha256, quote).
"""
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gapcap  # noqa: E402
from evlib import name_in  # noqa: E402

school = sys.argv[1]
ROOT = gapcap.ROOT
gi = json.load(open(f"{ROOT}/{school}/gap-input.json"))
out_path = f"{ROOT}/{school}/gap-evidence.json"

if "--check-only" in sys.argv:
    rows = json.load(open(out_path))
else:
    mod = importlib.import_module(f"decisions_{school}")
    rows = mod.ROWS

want = [r["pi"] for r in gi]
have = [r["pi"] for r in rows]
problems = []
if sorted(want) != sorted(have):
    problems.append(f"PI set differs: missing {set(want) - set(have)} extra {set(have) - set(want)}")

KEYS = ["pi", "status", "status_evidence", "students", "identity", "collection_person_id", "appointment_notes", "notes"]
n_q = 0
for r in rows:
    for k in KEYS:
        r.setdefault(k, [] if k in ("status_evidence", "students", "appointment_notes") else (None if k in ("collection_person_id", "notes") else {}))
    idn = {"dblp": r["identity"].get("dblp", []), "orcid": r["identity"].get("orcid", []),
           "openalex": r["identity"].get("openalex", []), "evidence": r["identity"].get("evidence", [])}
    if r["identity"].get("openalex_candidates"):  # matched only against a DBLP person page (the PI's own list is unavailable)
        idn["openalex_candidates"] = [a.rsplit("/", 1)[-1] for a in r["identity"]["openalex_candidates"]]
    r["identity"] = idn
    if r["status"] not in ("pi", "not_pi_in_window"):
        problems.append(f"{r['pi']}: bad status {r['status']}")
    if r["status"] == "not_pi_in_window" and not r["status_evidence"]:
        problems.append(f"{r['pi']}: not_pi_in_window without evidence")
    if r["status"] == "pi" and not r["students"] and not r.get("status_evidence"):
        problems.append(f"{r['pi']}: pi without a stated student or status evidence")
    items = [("status", r["pi"], e) for e in r["status_evidence"]] + [("appointment", r["pi"], e) for e in r["appointment_notes"]] \
        + [("identity", r["pi"], e) for e in r["identity"]["evidence"]] + [("student", s["name"], s) for s in r["students"]]
    for kind, nm, e in items:
        if not e.get("sha256") or not e.get("quote"):
            problems.append(f"{r['pi']} {kind} {nm}: missing sha/quote")
            continue
        ok, view = gapcap.verify_quote(school, e["sha256"], e["quote"])
        n_q += 1
        if not ok:
            problems.append(f"{r['pi']} {kind} {nm}: quote not verified ({view}): {e['quote'][:100]}")
        if not name_in(nm, e["quote"]) and not e.get("name_exempt"):
            problems.append(f"{r['pi']} {kind}: quote lacks name {nm!r}: {e['quote'][:100]}")
    for s in r["students"]:
        if s.get("role") not in ("phd", "postdoc", "masters", "undergraduate", "member", "other"):
            problems.append(f"{r['pi']} student {s['name']}: bad role {s.get('role')}")
        y = s.get("years")
        if y is not None and not (isinstance(y, list) and len(y) == 2 and all(isinstance(v, int) for v in y)):
            problems.append(f"{r['pi']} student {s['name']}: bad years {y}")
    r["identity"]["openalex"] = [a.rsplit("/", 1)[-1] for a in r["identity"]["openalex"]]

order = {p: i for i, p in enumerate(want)}
rows = sorted(rows, key=lambda r: order.get(r["pi"], 999))
rows = [{k: r[k] for k in KEYS} for r in rows]
print(f"{school}: {len(rows)} rows, {n_q} quotes checked, {len(problems)} problems")
for p in problems:
    print("  PROBLEM", p)
if "--check-only" not in sys.argv:
    if problems and "--force" not in sys.argv:
        print("not written (fix problems or pass --force)")
        sys.exit(1)
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    os.replace(tmp, out_path)
    print("wrote", out_path)
