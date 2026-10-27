"""Build hierarchy/<school>/few-students-evidence.json from decisions_<school>.py.

decisions_<school>.py defines D = {pi: dict(students=[rows from fsev.S / parsers], lab_note=str, notes=str)} for every
input PI. Rows are deduplicated by person; a student already in students_already is kept only with its new source and
marked in its note. Every quote is re-verified (fsev checks at construction; verify.py re-checks the written file).
usage: build.py SCHOOL
"""
import importlib
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import fsev  # noqa: E402

school = sys.argv[1]
H = f"/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/{school}"
inp = json.load(open(f"{H}/few-students-input.json"))
mod = importlib.import_module(f"decisions_{school}")
D = mod.D


def key(n):
    k = [t for t in re.split(r"[^a-z]+", fsev.fold(re.sub(r"\([^)]*\)", " ", n))) if t]
    return (k[0], k[-1]) if k else ("", "")


out = []
missing = [r["pi"] for r in inp if r["pi"] not in D]
if missing:
    sys.exit(f"decisions missing for {missing}")
extra = [p for p in D if p not in {r["pi"] for r in inp}]
if extra:
    sys.exit(f"decisions for PIs not in the input: {extra}")
for r in inp:
    d = D[r["pi"]]
    held = {key(n) for n in r["students_already"]}
    held_last = {key(n)[1] for n in r["students_already"]}
    rows = fsev.dedupe(list(d.get("students", [])))
    for s in rows:
        assert s["role"] in fsev.ROLES, s
        if key(s["name"]) in held:
            s["note"] = "already held; new source. " + s.get("note", "")
            s["note"] = s["note"].strip()
    out.append({"pi": r["pi"], "students": rows, "lab_note": d.get("lab_note", ""), "notes": d.get("notes", "")})
json.dump(out, open(f"{H}/few-students-evidence.json", "w"), indent=1, ensure_ascii=False)
for o, r in zip(out, inp):
    held = {key(n) for n in r["students_already"]}
    new = [s for s in o["students"] if key(s["name"]) not in held]
    print(f"{o['pi']:<40} before {len(held):>2}  new {len(new):>3}  after {len(held) + len(new):>3}  rows {len(o['students'])}")
print("wrote", f"{H}/few-students-evidence.json")
