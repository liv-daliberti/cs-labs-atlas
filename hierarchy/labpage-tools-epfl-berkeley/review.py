"""Compact review of built specs: per lab, counts and the NEW names by section (held matches only counted).
usage: review.py SCHOOL [IDX,IDX,...|a-b] [--held] [--src]"""
import os, sys
TOOLS = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, TOOLS)
import lpbuild, lplab  # noqa: E402
school = sys.argv[1]
sel = None
if len(sys.argv) > 2 and not sys.argv[2].startswith("--"):
    a = sys.argv[2]
    sel = set(range(int(a.split("-")[0]), int(a.split("-")[1]) + 1)) if "-" in a else {int(x) for x in a.split(",")}
for i, row in enumerate(lplab.rows(school)):
    if sel is not None and i not in sel:
        continue
    out, pubs, prob = lpbuild.build_lab(school, row)
    st = out["students"]
    new = [s for s in st if not s["already_held"]]
    if "--wb-only" in sys.argv:
        new = [s for s in new if s.get("capture_url")]
    if "--man" in sys.argv:
        import json as _j
        man = _j.load(open(f"{TOOLS}/manual_pages.json")).get(school, {}).get(row["pi"], {})
        if man.get("people") is None and "--wb-only" not in sys.argv:
            continue
    print(f"#{i} {row['pi']} | held {len(row['students_held'])} | rows {len(st)} new {len(new)} "
          f"matched {len(st)-len(new)} | pubs {len(pubs)} | probs {len(prob)} | {out['people_page']}")
    by = {}
    for s in new:
        sec = (s.get("section") or "")[-45:]
        tag = s["role"][:4] + ("/a" if s["alumni"] else "")
        y = s.get("years")
        nm = s["name"] + (f"[{y[0] or ''}-{y[1] or ''}]" if y and y != [2026, 2026] else "")
        if s.get("possible_held"):
            nm += "{?" + "|".join(s["possible_held"]) + "}"
        by.setdefault((sec, tag), []).append(nm)
    for (sec, tag), names in by.items():
        print(f"   [{tag}] {sec}: " + ", ".join(names))
    if "--held" in sys.argv:
        print("   HELD: " + ", ".join(f"{s['name']}~{s['held_name']}" for s in st if s["already_held"] and s["name"] != s["held_name"]))
    for p in prob[:4]:
        print("   ! " + p[:150])
