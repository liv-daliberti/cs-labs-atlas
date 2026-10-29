"""Department profile pages (one-person listings by a department) for gap PI-years.

usage: profiles.py <school> [--check]
Targets come from profiles_config.targets(school): each is
  {"pi", "dept", "detail", "cdx": (prefix_url, from_year, to_year), "match": regex on the original URL,
   "years": [...]}.
One CDX prefix query per distinct (prefix, from, to) (cached in the school's sqlite); then for every target
year two captures (H1 Jan-Jun, H2 Jul-Dec) when they exist, nearest the half's midpoint. A capture is
usable when it is a 200 whose text names the PI (full name or a known variant) followed by a faculty title.
Plan rows go to table `pplan`. Resumable; transient failures leave the row unplanned.
"""
import importlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
import match
import plan_fetch as pf

STRICT_TITLE = re.compile(r"\b(Professor|Professeur\w*|Professorin|Lecturer|Instructor|Emerit\w*|Faculty)\b|"
                          r"Ma[iî]tre d.enseignement|\bMER\b", re.I)


def ensure_tables(con):
    con.execute("""create table if not exists pplan(
        pi text, dept text, detail text, year integer, half text, page_url text, capture_url text,
        wayback_timestamp text, status text, reason text, tried text,
        primary key(pi, detail, year, half))""")
    con.commit()


def profile_hit(blocks, m, window=16):
    """The PI on their own profile page: a hit whose title lines carry a faculty title, else the PI's name
    block followed within `window` blocks by a block stating a faculty title (people.epfl.ch puts
    'Edit profile', the e-mail and phone lines between the name and 'Full Professor, <lab>'). The quote is
    the contiguous run of blocks from the name to that title block."""
    for h in match.find(blocks, m):
        tl = " | ".join(h["title_lines"])
        if STRICT_TITLE.search(tl) and not match.STRONG_NONFAC_RX.search(tl):
            return h
    idx = match.Index([m])
    bm = match.all_block_matches(blocks, idx)
    for i, d in enumerate(bm):
        if 0 not in d:
            continue
        name, rem, basis = d[0][:3]
        for j in range(i + 1, min(len(blocks), i + 1 + window)):
            t = blocks[j][1]
            if len(t) > 200:
                continue
            if STRICT_TITLE.search(t) and not match.STRONG_NONFAC_RX.search(t):
                quote = " ".join(" ".join(x for _, x in blocks[i:j + 1]).split())
                return {"block_index": i, "name_as_written": name, "quote": quote, "title_lines": [t],
                        "section_heading": None, "match_basis": basis, "name_kind": blocks[i][0]}
    # biography sentence on the profile: '<Name> is (currently) an Assistant Professor ...'; the title must
    # come right after 'is', so 'X is Dean ... He has also served as professor at UCLA' does not count
    for i, (k, t) in enumerate(blocks):
        head = t[:300]
        r = match.split_name_prefix(head, m)
        if not r:
            continue
        name, rem, basis = r[:3]
        mm = BIO_RX.match(rem)
        if not mm:
            continue
        cut = len(head) - len(rem) + mm.end()
        quote = " ".join(head[:cut].split())
        if name in quote:
            return {"block_index": i, "name_as_written": name, "quote": quote, "title_lines": [mm.group("title")],
                    "section_heading": None, "match_basis": basis, "name_kind": k}
    return None


BIO_RX = re.compile(r"^\s*is (?:currently |now )?(?:an? |the )?(?P<title>(?:(?:Full|Associate|Assistant|Adjunct|"
                    r"Tenure[- ]Track|Titular|Visiting|Research|Teaching|Distinguished) )*(?:Assistant )?Professor)\b", re.I)


def run(school):
    cfg = importlib.import_module("profiles_config")
    pis = {p["pi"]: p for p in json.load(open(wb.input_path(school)))["pis"]}
    extra = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_aliases.json"))).get(school, {})
    con = wb.db(school)
    ensure_tables(con)
    targets = cfg.targets(school)
    groups = {}
    for t in targets:
        groups.setdefault(tuple(t["cdx"]), []).append(t)
    for (prefix, a, b), ts in groups.items():
        rows = wb.cdx({"url": prefix, "matchType": "prefix", "from": str(a), "to": str(b), "output": "json",
                       "fl": "urlkey,timestamp,original,statuscode,digest", "limit": "50000"}, con)
        if rows is None:
            print("CDX failed; skipping group", prefix, flush=True)
            continue
        rows = [r for r in rows if r["statuscode"] in ("200", "-")]
        print("==", prefix, a, b, len(rows), "rows,", len(ts), "targets", flush=True)
        for t in ts:
            m = match.Matcher(pis[t["pi"]], extra.get(t["pi"], {}).get("aliases", []))
            mine = [r for r in rows if re.search(t["match"], r["original"], re.I)]
            for y in t["years"]:
                for half, lo, hi, mid in pf.halves(y):
                    done = con.execute("select status from pplan where pi=? and detail=? and year=? and half=?",
                                       (t["pi"], t["detail"], y, half)).fetchone()
                    if done:
                        continue
                    if t.get("one_half_per_year") and half == "H2" and con.execute(
                            "select 1 from pplan where pi=? and detail=? and year=? and half='H1' and status='ok'",
                            (t["pi"], t["detail"], y)).fetchone():
                        # the year is already proven by its H1 capture: record the H2 half as skipped, fetch nothing
                        con.execute("insert or replace into pplan values(?,?,?,?,?,?,?,?,?,?,?)",
                                    (t["pi"], t["dept"], t["detail"], y, half, None, None, None, "skipped",
                                     "year already proven by the H1 capture (one_half_per_year)", "[]"))
                        con.commit()
                        continue
                    inhalf = sorted([r for r in mine if lo <= r["timestamp"][:8] <= hi],
                                    key=lambda r: abs(pf.days(r["timestamp"]) - pf.days(mid)))
                    seen, cands = set(), []
                    for r in inhalf:
                        if r["digest"] in seen:
                            continue
                        seen.add(r["digest"])
                        cands.append(r)
                    if not cands:
                        con.execute("insert or replace into pplan values(?,?,?,?,?,?,?,?,?,?,?)",
                                    (t["pi"], t["dept"], t["detail"], y, half, None, None, None, "nocapture",
                                     "no archived 200 capture of the profile page in this half-year", "[]"))
                        con.commit()
                        continue
                    tried, ok, transient = [], None, False
                    for r in cands[:2]:
                        cap = wb.fetch_capture(r["timestamp"], r["original"], r["original"], t["dept"], con)
                        st, blocks = pf.ensure_extracted(con, cap)
                        fu = con.execute("select final_url from captures where capture_url=?", (cap,)).fetchone()[0] or cap
                        mm = re.match(r"https://web\.archive\.org/web/(\d{14})id_/", fu)
                        fts = mm.group(1) if mm else r["timestamp"]
                        why = None
                        if st in (-1, 429):
                            transient, why = True, f"http status {st}"
                        elif (st or 0) >= 500:
                            why = f"http status {st} (Wayback error after back-off)"
                        elif st != 200 or not mm:
                            why = f"http status {st}" if st != 200 else "redirected away from the capture"
                        elif not (lo <= fts[:8] <= hi):
                            why = f"redirected to capture {fts} outside the half-year"
                        elif not profile_hit(blocks, m):
                            why = "page does not show the PI with a faculty title"
                        tried.append({"capture_url": cap, "status": st, "usable": why is None, "why": why})
                        print(f"  {t['pi']} {y}{half} {r['timestamp']} -> {st} {'OK' if why is None else why}", flush=True)
                        if why is None:
                            ok = (cap, r["original"], fts)
                            break
                    if ok:
                        con.execute("insert or replace into pplan values(?,?,?,?,?,?,?,?,?,?,?)",
                                    (t["pi"], t["dept"], t["detail"], y, half, ok[1], ok[0], ok[2], "ok", None, json.dumps(tried)))
                    elif transient:
                        continue
                    else:
                        con.execute("insert or replace into pplan values(?,?,?,?,?,?,?,?,?,?,?)",
                                    (t["pi"], t["dept"], t["detail"], y, half, None, None, None, "unusable",
                                     tried[-1]["why"] if tried else None, json.dumps(tried)))
                    con.commit()
    print("done", school, flush=True)


def check(school):
    cfg = importlib.import_module("profiles_config")
    con = wb.db(school)
    ensure_tables(con)
    have = {(a, b, c, d) for a, b, c, d in con.execute("select pi, detail, year, half from pplan")}
    miss = [(t["pi"], y, h) for t in cfg.targets(school) for y in t["years"] for h in ("H1", "H2")
            if (t["pi"], t["detail"], y, h) not in have]
    print(school, "unplanned profile halves:", len(miss), miss[:5], flush=True)
    return not miss


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if check(sys.argv[1]) else 3)
    run(sys.argv[1])
