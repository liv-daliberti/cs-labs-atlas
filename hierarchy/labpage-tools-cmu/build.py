"""Build hierarchy/cmu/labpage-evidence.json and labpage-pubs.jsonl.gz from decisions/*.py + the capture stores,
then re-verify every quote against the stored bytes (sha256 lookup + exact substring + name/title in quote).

usage: python -I build.py [--dry] [--only MODULE ...] [--partial] [--quiet]
  --dry      resolve + verify, do not write outputs
  --only     restrict to decisions modules (e.g. b07); implies --partial
  --partial  do not complain about labs without a decision
Captures are resolved through capstore (own DB = $LABPAGE_DB, then the read-only stores).
"""
import argparse
import glob
import gzip
import importlib
import json
import os
import re
import sys
from collections import defaultdict

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
sys.path.insert(0, TOOLS + "/decisions")
import capstore  # noqa: E402
import names  # noqa: E402
import pubx  # noqa: E402

INPUT = str(capstore.P.data("labpage-input.json", "cmu"))
OUT_EV = str(capstore.P.data("labpage-evidence.json", "cmu"))
OUT_PUBS = str(capstore.P.data("labpage-pubs.jsonl.gz", "cmu"))
LAB_PAPERS = str(capstore.P.data("lab_papers.jsonl.gz", "cmu"))
STUDENTS = str(capstore.P.data("students.json", "cmu"))
MAXQ = 1500
ROLES = ("phd", "postdoc", "masters", "undergraduate", "staff", "visitor", "member", "other")

problems = []
_text_cache = {}


def collapse(s):
    return re.sub(r"\s+", " ", s or "").strip()


def capture_row(url):
    """Stored 200 capture for a live URL (url or final_url) or a Wayback URL (capture_url or final_url)."""
    orig, cap = capstore.split_wayback(url)
    if cap:
        r = capstore.cached(capstore.wb_id(url))
        return r
    r = capstore.cached(url)
    if r:
        return r
    con = capstore.connect()
    row = con.execute(f"SELECT {capstore.SEL} FROM captures WHERE final_url=? AND capture_url IS NULL AND status=200 "
                      "ORDER BY id DESC LIMIT 1", (url,)).fetchone()
    con.close()
    return capstore._row_to_dict(row) if row else None


_rows_cache = {}


def capture_rows(url):
    if url not in _rows_cache:
        _rows_cache[url] = _capture_rows(url)
    return _rows_cache[url]


def _capture_rows(url):
    """All stored 200 captures for url across the own DB and every read-only store (own DB newest first, then the
    read-only stores in capstore.RO_DBS order), so a quote written against an earlier copy of a page still
    resolves after the same URL was re-fetched into another store."""
    orig, cap = capstore.split_wayback(url)
    out, seen = [], set()
    for path in [capstore.DB] + capstore.RO_DBS:
        con = capstore._ro(path)
        if con is None:
            continue
        try:
            if cap:
                c = capstore.wb_id(url)
                rows = con.execute(f"SELECT {capstore.SEL} FROM captures WHERE (capture_url=? OR final_url=?) "
                                   "AND status=200 AND content IS NOT NULL ORDER BY id DESC", (c, c)).fetchall()
            else:
                rows = con.execute(f"SELECT {capstore.SEL} FROM captures WHERE (url=? OR final_url=?) AND "
                                   "capture_url IS NULL AND status=200 AND content IS NOT NULL ORDER BY id DESC",
                                   (url, url)).fetchall()
        except Exception:
            rows = []
        finally:
            con.close()
        for row in rows:
            if row[5] in seen:
                continue
            seen.add(row[5])
            out.append(capstore._row_to_dict(row))
    return out


def texts(r):
    k = r["sha256"]
    if k not in _text_cache:
        b = r["content"]
        _text_cache[k] = (capstore.page_text(b), capstore.raw_text(b))
    return _text_cache[k]


def source_of(r):
    out = {}
    if r.get("capture_url"):
        out["url"] = r["url"]
        out["capture_url"] = capstore.actual_capture(r)
    else:
        out["url"] = r.get("final_url") or r["url"]
    out["sha256"] = r["sha256"]
    return out


def resolve_quote(spec, who, must):
    cands = capture_rows(spec["url"])
    if not cands:
        r = capture_row(spec["url"])
        cands = [r] if r else []
    if not cands:
        problems.append(f"{who}: no 200 capture for {spec['url']}")
        return None
    sub = []
    for r in cands:
        res = _resolve_in(r, spec, who, must, sub)
        if res is not None:
            for p in sub:
                if not p.startswith("NOTFOUND"):
                    problems.append(p)
            return res
    problems.append(f"{who}: quote not found in {spec['url']} ({len(cands)} stored copies): "
                    f"{(spec.get('q') or spec.get('near') or (spec.get('s'), spec.get('e')))!r}")
    return None


def _resolve_in(r, spec, who, must, sub):
    pt, rt = texts(r)
    srcs = [rt] if spec.get("raw") else [pt, rt]
    quote = None
    name = spec.get("name")
    for t in srcs:
        if "q" in spec:
            if spec["q"] in t:
                quote = spec["q"]
                break
        elif "near" in spec:
            near = spec["near"]
            if name and name in near and near in t:
                quote = near
                break
            best = None
            for m in re.finditer(re.escape(name), t):
                i, j = m.start(), m.end()
                k = t.rfind(near, max(0, i - MAXQ), i)
                if k >= 0:
                    span = (k, j)
                    if best is None or span[1] - span[0] < best[1] - best[0]:
                        best = span
                k2 = t.find(near, j, j + 400)
                if k2 >= 0:
                    span = (i, k2 + len(near))
                    if best is None or span[1] - span[0] < best[1] - best[0]:
                        best = span
            if best:
                quote = t[best[0]:best[1]]
                break
        elif "s" in spec:
            base = 0
            if spec.get("after"):
                base = t.find(spec["after"])
                if base < 0:
                    continue
            i = t.find(spec["s"], base)
            if i < 0:
                continue
            j = t.find(spec["e"], i + len(spec["s"]))
            if j < 0:
                continue
            quote = t[i:j + len(spec["e"])]
            break
        else:
            sub.append(f"{who}: no quote spec")
            return None
    if quote is None:
        sub.append("NOTFOUND")
        return None
    if len(quote) > MAXQ:
        sub.append(f"{who}: quote too long ({len(quote)}) in {spec['url']}: {quote[:120]}...")
    for tok in must:
        if tok not in quote:
            sub.append(f"{who}: token {tok!r} missing from quote: {quote[:160]}")
    out = source_of(r)
    out["quote"] = quote
    return out


def load_modules(only=None):
    D, where = {}, {}
    mods = sorted(os.path.basename(p)[:-3] for p in glob.glob(TOOLS + "/decisions/*.py")
                  if not os.path.basename(p).startswith("_"))
    for m in mods:
        if only and m not in only:
            continue
        try:
            mod = importlib.import_module(m)
        except Exception as e:
            problems.append(f"module {m} failed to import: {e!r}")
            continue
        for k, v in getattr(mod, "D", {}).items():
            if k in D:
                problems.append(f"{k}: decided in more than one module ({where[k]}, {m})")
            D[k] = v
            where[k] = m
    return D, where


def held_index():
    """name -> set(PI) across students.json (people held under any CMU lab)."""
    idx = defaultdict(set)
    try:
        st = json.load(open(STUDENTS))
    except Exception:
        return idx
    for pi, rows in st.items():
        for r in rows:
            for n in [r.get("name")] + list(r.get("aliases") or []):
                if n:
                    idx[names.parse(n)["last"]].add((n, pi))
    return idx


def lab_titles():
    by = defaultdict(list)
    with gzip.open(LAB_PAPERS, "rt") as f:
        for line in f:
            d = json.loads(line)
            if d.get("title"):
                by[d["pi"]].append(d["title"])
    return by


def years_ok(y):
    return y is None or (isinstance(y, list) and len(y) == 2 and all(v is None or isinstance(v, int) for v in y))


def build_lab(row, d, hidx, ltitles):
    pi = row["pi"]
    held = list(row.get("students_held") or [])
    pi_parsed = [names.parse(n) for n in row.get("names") or [pi]]
    studs, bykey = [], {}
    for mm in d.get("members", []):
        who = f"{pi}/member {mm.get('name')}"
        if mm.get("role") not in ROLES:
            problems.append(f"{who}: bad role {mm.get('role')}")
        if not years_ok(mm.get("years")):
            problems.append(f"{who}: bad years {mm.get('years')!r}")
        y = mm.get("years")
        if y and y[1] is not None and y[1] < 2016:
            problems.append(f"{who}: years end before 2016 {y}")
        if any(names.match(mm["name"], p.get("key", "")) == "exact" for p in pi_parsed if p.get("key")):
            problems.append(f"{who}: is the PI")
            continue
        spec = dict(mm)
        ev = resolve_quote(spec, who, mm.get("must") or [mm["name"]])
        if not ev:
            continue
        rec = {"name": mm["name"], "role": mm["role"], "years": y}
        rec.update(ev)
        if mm.get("note"):
            rec["note"] = mm["note"]
        kind, hits = names.find_held(mm["name"], held)
        if kind:
            rec["already_held"] = True
            if any(collapse(mm["name"]).casefold() == collapse(h).casefold() for h in hits):
                pass
            else:
                rec["aliases"] = [mm["name"]]
                rec["held_as"] = hits
        else:
            # held under another CMU lab?
            P = names.parse(mm["name"])
            other = sorted({p for n, p in hidx.get(P["last"], ()) if p != pi and names.match(mm["name"], n)})
            if other:
                rec["held_under_other_pi"] = other
        P = names.parse(mm["name"])
        key = P["key"]
        dup = None
        for k2, j in bykey.items():
            if names.match(mm["name"], studs[j]["name"]):
                dup = j
                break
        if dup is not None:
            s0 = studs[dup]
            s0.setdefault("also_sources", []).append({k: v for k, v in rec.items()
                                                      if k in ("url", "capture_url", "sha256", "quote", "role", "years")})
            y0 = s0.get("years")
            if y and y0:
                s0["years"] = [min([v for v in (y0[0], y[0]) if v is not None], default=None),
                               max([v for v in (y0[1], y[1]) if v is not None], default=None)]
            elif y and not y0:
                s0["years"] = y
            if mm["name"] != s0["name"]:
                s0.setdefault("name_variants", [])
                if mm["name"] not in s0["name_variants"]:
                    s0["name_variants"].append(mm["name"])
            continue
        bykey[key] = len(studs)
        studs.append(rec)
    # publications
    pubs_out, stats = [], []
    idx = pubx.lab_index(ltitles.get(pi, []))
    seen_titles = set()
    surnames = {p["last"] for p in pi_parsed if p.get("last")}
    for ps in d.get("pubs", []):
        who = f"{pi}/pubs {ps['url']}"
        r = capture_row(ps["url"])
        if not r:
            problems.append(f"{who}: no 200 capture")
            continue
        try:
            ents = pubx.extract(r["content"], r["url"], mode=ps.get("mode", "auto"), title_css=ps.get("title_css"))
        except Exception as e:
            problems.append(f"{who}: extract failed {e!r}")
            continue
        pt, rt = texts(r)
        st = {"url": ps["url"], "mode": ps.get("mode", "auto"), "entries": len(ents), "in_window": 0, "no_year": 0,
              "matched": 0, "missing": 0, "no_quote": 0}
        for e in ents:
            if e["year"] is None:
                st["no_year"] += 1
                continue
            if not (2016 <= e["year"] <= 2026):
                continue
            st["in_window"] += 1
            if pubx.match_lab(e["title"], e["entry"], idx):
                st["matched"] += 1
                continue
            nt = pubx.norm_title(e["title"])
            if nt in seen_titles:
                continue
            q = e.get("quote")
            hay = rt if e.get("raw") else pt
            if not q or q not in hay and q not in rt:
                st["no_quote"] += 1
                continue
            if e["title"] not in q:
                if e["title"] in hay:
                    q = e["title"]
                else:
                    st["no_quote"] += 1
                    continue
            seen_titles.add(nt)
            st["missing"] += 1
            line = {"pi": pi, "title": e["title"], "year": e["year"], "venue": e.get("venue"), "links": e["links"]}
            line.update(source_of(r))
            line["quote"] = q
            ent_n = names.strip_accents(e["entry"]).lower()
            line["pi_named"] = any(s and re.search(r"\b" + re.escape(s) + r"\b", ent_n) for s in surnames)
            pubs_out.append(line)
        stats.append(st)
    ev = {"pi": pi, "lab_name": row.get("lab_name"), "lab_site": d.get("lab_site"),
          "people_page": d.get("people_page"), "students": studs, "notes": d.get("notes", "")}
    if d.get("people_pages"):
        ev["people_pages"] = d["people_pages"]
    if d.get("pubs"):
        ev["pubs_pages"] = stats
    if d.get("blocked"):
        ev["blocked"] = d["blocked"]
    return ev, pubs_out


def verify(evs, pubs):
    """Independent re-check: every quote is an exact substring of the whitespace-collapsed text of the bytes with
    that sha256, and contains the person's name / the publication title."""
    bad = 0
    cache = {}

    def txt(sha):
        if sha not in cache:
            b = capstore.get_by_sha(sha)
            cache[sha] = None if b is None else (capstore.page_text(b), capstore.raw_text(b))
        return cache[sha]
    n = 0
    for ev in evs:
        for s in ev["students"]:
            for src in [s] + s.get("also_sources", []):
                n += 1
                t = txt(src["sha256"])
                nm = s["name"] if src is s else None
                if t is None or (src["quote"] not in t[0] and src["quote"] not in t[1]):
                    bad += 1
                    problems.append(f"VERIFY {ev['pi']}/{s['name']}: quote not in stored text")
                elif nm and nm not in src["quote"]:
                    bad += 1
                    problems.append(f"VERIFY {ev['pi']}/{s['name']}: name not in quote")
    for p in pubs:
        n += 1
        t = txt(p["sha256"])
        if t is None or (p["quote"] not in t[0] and p["quote"] not in t[1]):
            bad += 1
            problems.append(f"VERIFY pub {p['pi']}/{p['title'][:60]}: quote not in stored text")
        elif p["title"] not in p["quote"]:
            bad += 1
            problems.append(f"VERIFY pub {p['pi']}/{p['title'][:60]}: title not in quote")
    return n, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--pi", nargs="*", help="restrict to these PIs")
    a = ap.parse_args()
    partial = a.partial or bool(a.only)
    inp = json.load(open(INPUT))
    D, where = load_modules(a.only)
    pis = {r["pi"] for r in inp}
    for k in D:
        if k not in pis:
            problems.append(f"decision for unknown PI {k!r} ({where[k]})")
    hidx = held_index()
    lt = lab_titles()
    evs, pubs = [], []
    for row in inp:
        if a.pi and row["pi"] not in a.pi:
            continue
        d = D.get(row["pi"])
        if d is None:
            if not partial:
                problems.append(f"{row['pi']}: no decision")
            continue
        ev, pl = build_lab(row, d, hidx, lt)
        evs.append(ev)
        pubs.extend(pl)
    n, bad = verify(evs, pubs)
    added = sum(1 for e in evs for s in e["students"] if not s.get("already_held"))
    variants = sum(1 for e in evs for s in e["students"] if s.get("aliases"))
    print(f"labs={len(evs)} members={sum(len(e['students']) for e in evs)} added={added} held_variants={variants} "
          f"missing_pubs={len(pubs)} verified={n} bad={bad} problems={len(problems)}")
    if not a.quiet:
        for e in evs:
            ps = e.get("pubs_pages") or []
            print(f"  {e['pi']}: members={len(e['students'])} new={sum(1 for s in e['students'] if not s.get('already_held'))}"
                  f" held={sum(1 for s in e['students'] if s.get('already_held'))} pubs_missing="
                  f"{sum(p['missing'] for p in ps)} pubs_matched={sum(p['matched'] for p in ps)}"
                  f" no_year={sum(p['no_year'] for p in ps)} no_quote={sum(p['no_quote'] for p in ps)}")
            for s in e["students"]:
                if s.get("aliases"):
                    print(f"      variant: {s['name']!r} = held {s['held_as']}")
                if partial:
                    tag = "HELD" if s.get("already_held") else "NEW "
                    oth = f" (held under {s['held_under_other_pi']})" if s.get("held_under_other_pi") else ""
                    q = s["quote"] if len(s["quote"]) <= 220 else s["quote"][:100] + " ... " + s["quote"][-100:]
                    print(f"      {tag} {s['name']} [{s['role']}, {s.get('years')}]{oth} <- {s.get('capture_url') or s['url']}"
                          f"\n           q({len(s['quote'])}): {q}")
    for p in problems:
        print("PROBLEM", p)
    if not a.dry and not partial:
        with open(OUT_EV + ".tmp", "w") as f:
            json.dump(evs, f, indent=1, ensure_ascii=False)
        os.replace(OUT_EV + ".tmp", OUT_EV)
        with gzip.open(OUT_PUBS + ".tmp", "wt") as f:
            for p in pubs:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        os.replace(OUT_PUBS + ".tmp", OUT_PUBS)
        print("wrote", OUT_EV, OUT_PUBS)


if __name__ == "__main__":
    main()
