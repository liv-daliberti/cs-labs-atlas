"""Append rows for the PIs in decisions_newpis.py to hierarchy/cmu/gap-evidence.json, leaving every existing row unchanged,
then re-verify every quote of the new rows against the stored bytes (sha256 + exact substring + url/capture_url + name).

Rows are built exactly as build.py builds them (same resolve(), same row schema). Re-running replaces only the rows of the
PIs named in decisions_newpis.py. usage: append_newpis.py [--dry]
"""
import hashlib
import json
import sqlite3
import sys
import zlib

TOOLS = "/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-cmu"
sys.path.insert(0, TOOLS)
import build  # noqa: E402
import capstore  # noqa: E402
import decisions_newpis  # noqa: E402

HIER = "/n/fs/resemble/cs-atlas/work/hierarchy"
INPUT = HIER + "/new-pis-gap-input.json"
OUTPUT = HIER + "/cmu/gap-evidence.json"


def make_row(g, d):
    pi = g["pi"]
    pmust = d.get("pi_must") or build.surname_tokens(pi)
    row = {"pi": pi, "status": d["status"]}
    row["status_evidence"] = [x for x in (build.resolve(s, f"{pi}/status", pmust) for s in d.get("status_ev", [])) if x]
    studs = []
    for st in d.get("students", []):
        ev = build.resolve(st["ev"], f"{pi}/student {st['name']}", st.get("must") or build.surname_tokens(st["name"]))
        if not ev:
            continue
        o = {"name": st["name"], "role": st["role"], "years": st.get("years")}
        o.update(ev)
        if st.get("note"):
            o["note"] = st["note"]
        studs.append(o)
    row["students"] = studs
    ident = d.get("identity", {})
    iev = []
    for e in ident.get("evidence", []):
        x = build.resolve(e["ev"], f"{pi}/identity {e['kind']}", e["ev"].get("must") or pmust)
        if x:
            y = {"kind": e["kind"]}
            y.update(x)
            y["note"] = e.get("note", "")
            iev.append(y)
    row["identity"] = {"dblp": ident.get("dblp", []), "orcid": ident.get("orcid", []),
                       "openalex": ident.get("openalex", []), "evidence": iev}
    row["collection_person_id"] = d.get("collection_person_id")
    row["appointment_notes"] = [x for x in (build.resolve(s, f"{pi}/appointment", pmust) for s in d.get("appt", [])) if x]
    row["notes"] = d.get("notes", "")
    if d["status"] not in ("pi", "not_pi_in_window"):
        build.problems.append(f"{pi}: bad status {d['status']}")
    if not row["status_evidence"]:
        build.problems.append(f"{pi}: no status evidence")
    if d["status"] == "pi" and not studs:
        build.problems.append(f"{pi}: status pi without a student")
    return row


def strict_verify(rows):
    """Hash + exact substring + url/capture_url + name check for every quote of the given rows (as reverify.py)."""
    con = sqlite3.connect(f"file:{capstore.DB}?mode=ro", uri=True)
    n = bad = 0
    for r in rows:
        items = ([(e, r["pi"]) for e in r["status_evidence"]] + [(s, s["name"]) for s in r["students"]]
                 + [(e, r["pi"]) for e in r["identity"]["evidence"]] + [(e, r["pi"]) for e in r["appointment_notes"]])
        for it, who in items:
            n += 1
            row = con.execute("SELECT content, url, capture_url FROM captures WHERE sha256=? AND url=? AND content IS NOT NULL "
                              "LIMIT 1", (it["sha256"], it["url"])).fetchone()
            ok = False
            if row:
                c = zlib.decompress(row[0])
                ok = (hashlib.sha256(c).hexdigest() == it["sha256"]
                      and (it["quote"] in capstore.page_text(c) or it["quote"] in capstore.raw_text(c))
                      and row[2] == it.get("capture_url"))
            surname = who.replace("(", " ").split()[-1]
            if ok and surname not in it["quote"]:
                ok = False
            if not ok:
                bad += 1
                print("VERIFY FAIL", r["pi"], who, it.get("url"), it["quote"][:80])
    print(f"strict verification: {n - bad}/{n} new-row quotes pass (hash, substring, url/capture_url, name)")
    return bad


def main(dry=False):
    gap = [g for g in json.load(open(INPUT)) if g["school"] == "cmu"]
    D = decisions_newpis.D
    assert {g["pi"] for g in gap} == set(D), ({g["pi"] for g in gap}, set(D))
    new = [make_row(g, D[g["pi"]]) for g in gap]
    if build.problems:
        print("PROBLEMS:")
        for p in build.problems:
            print("  -", p)
        sys.exit(1)
    before_bytes = open(OUTPUT, "rb").read()
    existing = json.loads(before_bytes)
    names = {r["pi"] for r in new}
    kept = [r for r in existing if r["pi"] not in names]
    out = kept + new
    text = json.dumps(out, indent=1, ensure_ascii=False)
    # every pre-existing row must serialize byte-identically
    old_kept_text = json.dumps(kept, indent=1, ensure_ascii=False)
    assert text.startswith(old_kept_text[:-2]), "existing rows changed"
    if len(kept) == len(existing):
        assert before_bytes.decode("utf-8").rstrip("\n")[:-2] == old_kept_text[:-2], "existing file bytes differ"
    if dry:
        print(json.dumps(new, indent=1, ensure_ascii=False)[:4000])
    else:
        with open(OUTPUT, "w") as fh:
            fh.write(text)
        print("wrote", OUTPUT, len(existing), "->", len(out), "rows (kept", len(kept), "existing, added", len(new), ")")
    bad = strict_verify(new)
    build.verify(json.load(open(OUTPUT)) if not dry else new)
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(dry="--dry" in sys.argv) else 0)
