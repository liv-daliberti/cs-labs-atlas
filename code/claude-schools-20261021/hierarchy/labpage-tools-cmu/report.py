"""Summary statistics for the CMU lab-page pass.

usage: python -I report.py                 read hierarchy/cmu/labpage-evidence.json + labpage-pubs.jsonl.gz
       python -I report.py --only b01 b02  build those decisions modules in memory (dry) and report on them
Prints: labs with / without a site, members added (total, top 15 labs), held people matched under a variant
(examples), missing publications (total, top 15 labs), blocked URLs, labs whose notes mention unreadable captures.
"""
import argparse
import collections
import gzip
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)


def from_files():
    import capstore
    evs = json.load(open(capstore.P.data("labpage-evidence.json", "cmu")))
    pubs = [json.loads(l) for l in gzip.open(capstore.P.data("labpage-pubs.jsonl.gz", "cmu"), "rt")]
    return evs, pubs


def from_build(only):
    import build
    inp = json.load(open(build.INPUT))
    D, _ = build.load_modules(only)
    hidx = build.held_index()
    lt = build.lab_titles()
    evs, pubs = [], []
    for row in inp:
        d = D.get(row["pi"])
        if d is None:
            continue
        ev, pl = build.build_lab(row, d, hidx, lt)
        evs.append(ev)
        pubs.extend(pl)
    if build.problems:
        print(f"({len(build.problems)} build problems; run build.py --dry to see them)")
    return evs, pubs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--json", help="also write the stats as JSON here")
    a = ap.parse_args()
    evs, pubs = from_build(a.only) if a.only else from_files()
    with_site = [e for e in evs if e.get("lab_site")]
    with_people = [e for e in evs if e.get("people_page")]
    added = {e["pi"]: sum(1 for s in e["students"] if not s.get("already_held")) for e in evs}
    held = {e["pi"]: sum(1 for s in e["students"] if s.get("already_held")) for e in evs}
    variants = [(e["pi"], s["name"], s.get("held_as")) for e in evs for s in e["students"] if s.get("aliases")]
    other = [(e["pi"], s["name"], s.get("held_under_other_pi")) for e in evs for s in e["students"]
             if s.get("held_under_other_pi")]
    roles = collections.Counter(s["role"] for e in evs for s in e["students"] if not s.get("already_held"))
    pc = collections.Counter(p["pi"] for p in pubs)
    pnamed = sum(1 for p in pubs if p.get("pi_named"))
    blocked = [(e["pi"], b) for e in evs for b in (e.get("blocked") or [])]
    stats = {
        "labs": len(evs), "labs_with_site": len(with_site), "labs_without_site": len(evs) - len(with_site),
        "labs_with_people_page": len(with_people),
        "labs_with_pubs_page": sum(1 for e in evs if e.get("pubs_pages")),
        "members_recorded": sum(len(e["students"]) for e in evs), "members_added": sum(added.values()),
        "members_already_held": sum(held.values()), "held_variant_matches": len(variants),
        "added_but_held_under_other_pi": len(other), "added_by_role": dict(roles),
        "labs_with_members_added": sum(1 for v in added.values() if v),
        "missing_pubs": len(pubs), "missing_pubs_pi_named": pnamed, "labs_with_missing_pubs": len(pc),
        "top_added": sorted(added.items(), key=lambda x: -x[1])[:15],
        "top_missing_pubs": pc.most_common(15),
        "variant_examples": variants[:25],
        "blocked": blocked,
        "labs_without_site_list": [e["pi"] for e in evs if not e.get("lab_site")],
    }
    for k, v in stats.items():
        if isinstance(v, list) and len(v) > 0 and k not in ("labs_without_site_list",):
            print(f"{k}:")
            for x in v:
                print("   ", x)
        elif k == "labs_without_site_list":
            print(f"{k} ({len(v)}): {'; '.join(v)}")
        else:
            print(f"{k}: {v}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(stats, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
