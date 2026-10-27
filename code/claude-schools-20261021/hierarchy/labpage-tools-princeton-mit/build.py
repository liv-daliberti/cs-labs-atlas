"""Build hierarchy/<school>/labpage-evidence.json and labpage-pubs.jsonl.gz from the decision modules
dec_<school>_*.py (each defines D = {pi: lpev.Lab(...)}).

Members: rows are deduplicated by person (names.match among the lab's rows; later rows for the same person go into
the first row's `also` list as extra sources); the PI is dropped; each row is matched against the lab's students_held
(names.match) -> already_held: true, held_name, and aliases: [name as written] when it differs from the held name.
listed_year = year of the cited capture (Wayback timestamp, else fetch date).
Publications: every Pubs(url, spec) page is run through pubx.missing (2016-2026 entries whose normalized title is not
among the PI's lab papers); manual P(...) entries are compared the same way. Missing entries are written one per line.
usage: build.py SCHOOL [--partial]   (--partial: allow PIs without a decision; they get an empty row)
"""
import argparse
import glob
import gzip
import importlib
import json
import os
import re
import sqlite3
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import lpcap  # noqa: E402
import lpev  # noqa: E402
import names  # noqa: E402
import pubx  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("school")
ap.add_argument("--partial", action="store_true")
ap.add_argument("--out-suffix", default="")
ap.add_argument("--module", default=None, help="only this decision module (implies --partial); with --dry nothing is written")
ap.add_argument("--dry", action="store_true", help="print the summary (and member/pub details with -v) but write nothing")
ap.add_argument("-v", action="store_true")
ap.add_argument("--pi", nargs="*", help="with --dry: only these PIs (requires the module to honour LP_ONLY)")
a = ap.parse_args()
school = a.school
H = f"{lpcap.ROOT}/{school}"
labs = json.load(open(f"{H}/labpage-input.json"))

if a.pi:
    os.environ["LP_ONLY"] = json.dumps(a.pi)
D, origin = {}, {}
for path in sorted(glob.glob(f"{TOOLS}/dec_{school}_*.py")):
    mod = os.path.basename(path)[:-3]
    if a.module and mod != a.module:
        continue
    m = importlib.import_module(mod)
    for pi, v in m.D.items():
        if pi in D:
            sys.exit(f"{pi} decided twice ({origin[pi]}, {mod})")
        D[pi] = v
        origin[pi] = mod
inp_pis = [l["pi"] for l in labs]
extra = [p for p in D if p not in inp_pis]
if extra:
    sys.exit(f"decisions for PIs not in the input: {extra}")
miss = [p for p in inp_pis if p not in D]
if miss and not (a.partial or a.module):
    sys.exit(f"decisions missing for {len(miss)} PIs: {miss[:20]}")


def cap_year(row):
    m = re.search(r"/web/(\d{4})", row.get("capture_url") or "")
    if m:
        return int(m.group(1))
    con = sqlite3.connect(f"file:{lpcap.DBS[school]}?mode=ro", uri=True)
    try:
        f = con.execute("SELECT fetched_at FROM captures WHERE sha256=? AND status=200 ORDER BY id LIMIT 1", (row["sha256"],)).fetchone()
    finally:
        con.close()
    if not f:
        for p in lpev._dbs(school):
            c2 = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            f = c2.execute("SELECT fetched_at FROM captures WHERE sha256=? AND status=200 ORDER BY id LIMIT 1", (row["sha256"],)).fetchone()
            c2.close()
            if f:
                break
    return int(f[0][:4]) if f else None


def same_person(a_, b_):
    return names.match_one(a_, b_) is not None


out, pub_lines, summary = [], [], []
for lab in labs:
    pi = lab["pi"]
    if (a.module or a.pi) and pi not in D:
        continue
    if a.pi and pi not in a.pi:
        continue
    d = D.get(pi) or lpev.Lab(notes="no decision recorded")
    held = list(lab.get("students_held") or [])
    pi_names = [pi] + list(lab.get("names") or [])
    rows = []
    for s in d["students"]:
        assert s["role"] in lpev.ROLES, (pi, s)
        if any(same_person(s["name"], p) for p in pi_names):
            continue
        hit = None
        for r in rows:
            if same_person(s["name"], r["name"]) or (r.get("held_name") and same_person(s["name"], r["held_name"])):
                hit = r
                break
        stoks = names.parse(s["name"])["tokens"]
        if hit is None and len(stoks) == 1:
            # a first-name-only listing (e.g. a directory of first names) joins the one row whose given name is
            # compatible: equal, a nickname pair, or a one-letter misspelling ('mattew' / 'Matthew')
            import difflib
            def given_ok(r):
                ft = names.parse(r["name"])["tokens"]
                if len(ft) < 2:
                    return False
                a_, b_ = names.compact(stoks[0]), names.compact(ft[0])
                return names.first_ok(a_, b_) or (len(a_) >= 5 and difflib.SequenceMatcher(None, a_, b_).ratio() >= 0.85)
            cands = [r for r in rows if given_ok(r)]
            if len(cands) == 1:
                hit = cands[0]
        if hit:
            ev = {k: s[k] for k in ("name", "role", "years", "url", "capture_url", "sha256", "quote") if k in s}
            ev["listed_year"] = cap_year(s)
            hit.setdefault("also", []).append(ev)
            ys = [y for y in (hit.get("years") or []) + (s.get("years") or []) if y]
            if ys and (s.get("years") or hit.get("years")):
                hit["years"] = [min(ys), max(ys)]
            continue
        row = dict(s)
        row["listed_year"] = cap_year(s)
        h, kind = names.match(s["name"], held)
        if h:
            row["already_held"] = True
            row["held_name"] = h
            row["match"] = kind
            if lpev.fold(re.sub(r"\s+", " ", s["name"]).strip()) != lpev.fold(h):
                row["aliases"] = [s["name"]]
        rows.append(row)
    # also-rows written under a variant spelling become aliases of the held person
    for r in rows:
        if r.get("already_held"):
            for e in r.get("also", []):
                if lpev.fold(e["name"]) != lpev.fold(r["held_name"]) and e["name"] not in r.get("aliases", []):
                    r.setdefault("aliases", []).append(e["name"])
    # publications
    find = pubx.matcher(school, pi)
    pubs_pages, seen = [], set()
    for p in d["pubs"]:
        if "pubs_page" in p:
            r, inwin, miss_ = pubx.missing(school, pi, p["pubs_page"], p.get("spec"), tuple(p.get("years") or (2016, 2026)))
            pp = {"url": r["url"], "sha256": r["sha256"], "entries_in_window": len(inwin), "matched": len(inwin) - len(miss_),
                  "missing": 0}
            if r.get("capture_url"):
                pp["capture_url"] = r["capture_url"]
            if p.get("note"):
                pp["note"] = p["note"]
            for e in miss_:
                k = pubx.norm_title(e["title"])
                if k in seen:
                    continue
                seen.add(k)
                line = {"pi": pi, "title": e["title"], "year": e["year"], "venue": e.get("venue"), "links": e["links"],
                        "url": r["url"], "sha256": r["sha256"], "quote": e["quote"]}
                if r.get("capture_url"):
                    line["capture_url"] = r["capture_url"]
                pub_lines.append(line)
                pp["missing"] += 1
            pubs_pages.append(pp)
        else:  # manual P entry
            if p.get("year") is not None and not (2016 <= p["year"] <= 2026):
                continue
            k = pubx.norm_title(p["title"])
            if k in seen or find(p["title"]):
                continue
            seen.add(k)
            line = {"pi": pi, "title": p["title"], "year": p.get("year"), "venue": p.get("venue"), "links": p.get("links") or [],
                    "url": p["url"], "sha256": p["sha256"], "quote": p["quote"]}
            if p.get("capture_url"):
                line["capture_url"] = p["capture_url"]
            pub_lines.append(line)
    o = {"pi": pi, "lab_site": d.get("lab_site"), "people_page": d.get("people_page"), "students": rows,
         "notes": d.get("notes", "")}
    if d.get("other_pages"):
        o["other_pages"] = d["other_pages"]
    if pubs_pages:
        o["pubs_pages"] = pubs_pages
    out.append(o)
    new = [r for r in rows if not r.get("already_held")]
    var = [r for r in rows if r.get("already_held") and r.get("aliases")]
    summary.append((pi, len(held), len(new), len(var), sum(1 for x in pub_lines if x["pi"] == pi), origin.get(pi, "-")))

if a.dry:
    for o in out:
        print(f"== {o['pi']}: site {o['lab_site']} | people {o['people_page']}")
        if a.v:
            for r in o["students"]:
                tag = (f"HELD({r['match']}: {r['held_name']})" if r.get("already_held") else "NEW")
                print(f"   {tag:<45} {r['role']:<13} {r['name']} {r.get('years')} +{len(r.get('also', []))} src")
            for x in [x for x in pub_lines if x["pi"] == o["pi"]][:400]:
                print(f"   PUB {x['year']} | {x['title'][:110]} | {str(x.get('venue'))[:40]}")
    for pi, nh, nn, nv, npub, mod in summary:
        print(f"{pi:<36} held {nh:>3}  new {nn:>3}  variant-matched {nv:>2}  missing pubs {npub:>4}  [{mod}]")
    sys.exit(0)
ev_path = f"{H}/labpage-evidence{a.out_suffix}.json"
pubs_path = f"{H}/labpage-pubs{a.out_suffix}.jsonl.gz"
json.dump(out, open(ev_path + ".tmp", "w"), indent=1, ensure_ascii=False)
os.replace(ev_path + ".tmp", ev_path)
with gzip.open(pubs_path + ".tmp", "wt", encoding="utf-8") as f:
    for line in pub_lines:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
os.replace(pubs_path + ".tmp", pubs_path)
for pi, nh, nn, nv, npub, mod in summary:
    print(f"{pi:<36} held {nh:>3}  new {nn:>3}  variant-matched {nv:>2}  missing pubs {npub:>4}  [{mod}]")
print(f"labs {len(out)}; new members {sum(s[2] for s in summary)}; variant matches {sum(s[3] for s in summary)}; "
      f"missing pubs {len(pub_lines)}")
print("wrote", ev_path, pubs_path)
