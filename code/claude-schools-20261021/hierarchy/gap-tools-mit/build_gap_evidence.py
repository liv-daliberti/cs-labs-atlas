"""Build hierarchy/mit/gap-evidence.json (one row per gap-input PI) from spec_mit.py, then re-verify every quote.
usage: build_gap_evidence.py [--allow-missing]"""
import json
import sys

sys.path.insert(0, "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-mit")
import spec_mit  # noqa: E402
import verify_gap_evidence  # noqa: E402

HERE = "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/mit/"
gap = json.load(open(HERE + "gap-input.json"))
out, missing = [], []
for g in gap:
    s = spec_mit.SPEC.get(g["pi"])
    if s is None:
        missing.append(g["pi"])
        continue
    idn = s.get("identity") or {}
    row = {
        "pi": g["pi"],
        "status": s["status"],
        "status_evidence": s.get("status_evidence") or [],
        "students": s.get("students") or [],
        "identity": {"dblp": idn.get("dblp") or [], "orcid": idn.get("orcid") or [], "openalex": idn.get("openalex") or [],
                     "evidence": idn.get("evidence") or []},
        "collection_person_id": s.get("collection_person_id", (g.get("collection_person_ids") or [None])[0]),
        "appointment_notes": s.get("appointment_notes") or [],
        "notes": s.get("notes") or "",
    }
    if idn.get("variants"):
        row["identity"]["variants"] = idn["variants"]
    ex = spec_mit.EXTRA.get(g["pi"]) or {}
    row["status_basis"] = ex.get("status_basis")
    row["needs_before_research"] = g.get("needs")
    row["needs_after_research"] = ex.get("needs_after_research", s.get("needs_after_research") or [])
    row["pipeline_actions"] = ex.get("pipeline_actions") or []
    out.append(row)
assert set(spec_mit.EXTRA) == {g["pi"] for g in gap}, set(spec_mit.EXTRA) ^ {g["pi"] for g in gap}
if missing and "--allow-missing" not in sys.argv:
    raise SystemExit("spec missing for: " + ", ".join(missing))
json.dump(out, open(HERE + "gap-evidence.json", "w"), indent=1, ensure_ascii=False)
print("wrote", len(out), "rows; missing", missing)
bad = verify_gap_evidence.verify(HERE + "gap-evidence.json")
print("verification failures:", bad)
