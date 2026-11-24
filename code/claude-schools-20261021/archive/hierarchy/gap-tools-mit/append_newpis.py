"""Append rows for the PIs in spec_newpis.py to hierarchy/mit/gap-evidence.json, leaving every existing row unchanged, then
re-verify the whole file with verify_gap_evidence.verify plus a strict per-quote check of the new rows (stored row with that
sha256 has the cited url/capture_url). Rows have the same keys as build_gap_evidence.py writes.
Re-running replaces only the rows of the PIs in spec_newpis.py. usage: append_newpis.py [--dry]
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib
import json
import sqlite3
import sys
import zlib

sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-mit'))
import capstore  # noqa: E402
import spec_newpis  # noqa: E402
import verify_gap_evidence  # noqa: E402
from evlib import has_name  # noqa: E402

HIER = str(P.HIERARCHY)
INPUT = HIER + "/new-pis-gap-input.json"
OUTPUT = HIER + "/mit/gap-evidence.json"


def make_row(g, s, ex):
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
    row["status_basis"] = ex.get("status_basis")
    row["needs_before_research"] = g.get("needs")
    row["needs_after_research"] = ex.get("needs_after_research", [])
    row["pipeline_actions"] = ex.get("pipeline_actions") or []
    assert row["status"] in ("pi", "not_pi_in_window"), row["status"]
    assert row["status_evidence"], g["pi"] + ": no status evidence"
    assert row["status"] != "pi" or row["students"], g["pi"] + ": pi without students"
    return row


def strict(rows):
    con = sqlite3.connect(f"file:{capstore.DB}?mode=ro", uri=True)
    n = bad = 0
    for r in rows:
        items = ([(e, e.get("name_check") or r["pi"], "s") for e in r["status_evidence"]]
                 + [(e, e["name"], "st") for e in r["students"]]
                 + [(e, e.get("name_check") or r["pi"], "id") for e in r["identity"]["evidence"]]
                 + [(e, r["pi"].split()[-1], "ap") for e in r["appointment_notes"]])
        for e, name, kind in items:
            n += 1
            # status/student rows carry url (+capture_url); identity/appointment rows carry url = capture or live url
            if kind in ("s", "st"):
                q = ("SELECT content FROM captures WHERE sha256=? AND url=? AND "
                     + ("capture_url=?" if e.get("capture_url") else "capture_url IS NULL") + " AND content IS NOT NULL LIMIT 1")
                args = (e["sha256"], e["url"]) + ((e["capture_url"],) if e.get("capture_url") else ())
            else:
                q = ("SELECT content FROM captures WHERE sha256=? AND (capture_url=? OR (url=? AND capture_url IS NULL)) "
                     "AND content IS NOT NULL LIMIT 1")
                args = (e["sha256"], e["url"], e["url"])
            row = con.execute(q, args).fetchone()
            ok = bool(row) and hashlib.sha256(zlib.decompress(row[0])).hexdigest() == e["sha256"] \
                and e["quote"] in capstore.page_text(zlib.decompress(row[0])) and has_name(e["quote"], name)
            if not ok:
                bad += 1
                print("STRICT FAIL", r["pi"], kind, name, e.get("url"), e["quote"][:80])
    print(f"strict check of new rows: {n - bad}/{n} quotes pass (stored url/capture_url + sha256 + substring + name)")
    return bad


def main(dry=False):
    gap = [g for g in json.load(open(INPUT)) if g["school"] == "mit"]
    assert {g["pi"] for g in gap} == set(spec_newpis.SPEC) == set(spec_newpis.EXTRA)
    new = [make_row(g, spec_newpis.SPEC[g["pi"]], spec_newpis.EXTRA[g["pi"]]) for g in gap]
    before = open(OUTPUT, "rb").read().decode("utf-8")
    existing = json.loads(before)
    names = {r["pi"] for r in new}
    kept = [r for r in existing if r["pi"] not in names]
    kept_text = json.dumps(kept, indent=1, ensure_ascii=False)
    if len(kept) == len(existing):
        assert before.rstrip("\n")[:-2] == kept_text[:-2], "existing file does not round-trip byte-identically"
    out_text = json.dumps(kept + new, indent=1, ensure_ascii=False)
    assert out_text.startswith(kept_text[:-2])
    bad = strict(new)
    if dry:
        for r in new:
            print(r["pi"], r["status"], len(r["students"]), "students;", len(r["identity"]["evidence"]), "identity quotes")
        return bad
    with open(OUTPUT, "w") as fh:
        fh.write(out_text)
    print("wrote", OUTPUT, len(existing), "->", len(kept) + len(new), "rows")
    bad += verify_gap_evidence.verify(OUTPUT)
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(dry="--dry" in sys.argv) else 0)
