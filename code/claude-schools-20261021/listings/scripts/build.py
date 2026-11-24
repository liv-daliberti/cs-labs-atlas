"""Build listings.json, pages.json, coverage.json, gaps.json, ambiguous.json for one school.

usage: build.py <school>
Reads listings/<school>/captures.sqlite (plan + captures), the school's listings-input JSON and
config_<school>.py; writes into listings/<school>/. Offline: never touches the network.
"""
import calendar
import collections
import datetime
import importlib
import json
import os
import re
import sqlite3
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
import extract
import match
import profiles

YEARS = list(range(2016, 2027))
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTHS.update({"sept": 9})
FUT_RX = re.compile(r"\b(will join|will be joining|joining|joins|to join|starting|starts|will start|begins|beginning|"
                    r"effective|arriving|arrives|incoming|appointment (?:starts|begins)|as of|from)\b", re.I)


def future_start(quote, observed):
    """A listing that announces an appointment starting after the capture date (needs a join/start cue)."""
    if not FUT_RX.search(quote):
        return None
    od = datetime.date.fromisoformat(observed)
    dates = []
    for m in re.finditer(r"\b(?:(\d{1,2})\s+)?([A-Z][a-z]{2,8})\.?\s+(?:(\d{1,2}),?\s+)?(\d{4})\b", quote):
        mon = MONTHS.get(m.group(2).lower())
        if not mon:
            continue
        day = int(m.group(1) or m.group(3) or 1)
        try:
            dates.append((datetime.date(int(m.group(4)), mon, min(day, 28)), m.group(0)))
        except ValueError:
            pass
    for m in re.finditer(r"\b(fall|autumn|spring|summer|winter)\s+(?:of\s+)?(\d{4})\b", quote, re.I):
        start = {"spring": 1, "winter": 1, "summer": 6, "fall": 9, "autumn": 9}[m.group(1).lower()]
        dates.append((datetime.date(int(m.group(2)), start, 1), m.group(0)))
    for m in re.finditer(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", quote):
        try:
            dates.append((datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))), m.group(0)))
        except ValueError:
            pass
    if dates:
        fut = [d for d in dates if d[0] > od]
        return (FUT_RX.search(quote).group(0) + " … " + fut[0][1]) if fut else None
    m = re.search(r"\b(will join|will be joining|joining|to join|incoming|will start|appointment (?:starts|begins))\b", quote, re.I)
    return m.group(0) if m else None


def load(school):
    cfg = importlib.import_module(f"config_{school}")
    pis = json.load(open(wb.input_path(school)))["pis"]
    extra_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_aliases.json")
    extra = json.load(open(extra_path)).get(school, {}) if os.path.exists(extra_path) else {}
    extra = {k: v["aliases"] for k, v in extra.items()}
    return cfg, pis, extra


def region_bounds(blocks, slot, page_url=""):
    """Listing region of a capture: slot['regions'] is a list of {url, start, end} whose `url` regex
    picks the site era and whose start/end regexes are matched against 'kind:text' of each block
    (e.g. 'h1:Professors', 'h3:News'). Returns (lo, hi, has_region); without a region the whole page
    is searched and only entries with their own faculty title count."""
    u = re.sub(r":(80|443)(?=/)", "", page_url)
    for reg in slot.get("regions", []):
        if reg.get("url") and not re.search(reg["url"], u):
            continue
        lo, hi = None, len(blocks)
        for i, (k, t) in enumerate(blocks):
            kt = f"{k}:{t}"
            if lo is None and re.search(reg["start"], kt):
                lo = i
            elif lo is not None and reg.get("end") and re.search(reg["end"], kt):
                hi = i
                break
        if lo is not None:
            return lo, hi, True
    return 0, len(blocks), False


def page_flags(blocks, slot):
    heads = " | ".join(t for k, t in blocks if k in ("h1", "h2", "h3"))
    return {"emeritus": slot.get("kind") == "emeritus" and bool(re.search(r"emerit|honorary|retired", heads, re.I)),
            "visiting": slot.get("kind") == "visiting" and bool(re.search(r"visit", heads, re.I))}


def ambiguous_initials(text, hit):
    """For an initials-tier match: other names on the page with the same surname and first initial?"""
    toks = match.norm(hit["name_as_written"])
    if not toks:
        return []
    sur, ini = toks[-1], toks[0][0]
    found = set()
    for m in re.finditer(r"\b([A-Z][\w\-]*\.?)\s+(?:[A-Z][\w\-]*\.?\s+){0,2}" + re.escape(hit["name_as_written"].split()[-1]) + r"\b", text):
        first = match.norm(m.group(1))
        if first and first[0][0] == ini:
            found.add(" ".join(m.group(0).split()))
    return sorted(found)


def dept_ok(pi, dept, cfg):
    codes = getattr(cfg, "DEPT_CODES", {}).get(dept)
    if codes is None:
        return None
    return any(c in pi.get("departments", []) for c in codes)


def main(school):
    cfg, pis, extra = load(school)
    out = wb.school_dir(school)
    ms = match.matchers(pis, extra)
    idx = match.Index(ms)
    slots = {s["slot"]: s for s in cfg.SLOTS}
    con = sqlite3.connect(wb.db_path(school), timeout=120)
    plan = con.execute("select slot, dept, year, half, page_url, capture_url, wayback_timestamp, status, reason, tried "
                       "from plan order by dept, slot, year, half").fetchall()
    rows, ambiguous, nonfac = [], [], []
    pages = collections.defaultdict(lambda: {"slots": {}})
    caps_by_year = collections.defaultdict(list)   # year -> [(slot, entry, text)]
    for slot_name, dept, year, half, page_url, cap, ts, status, reason, tried in plan:
        if slot_name not in slots:
            continue
        slot = slots[slot_name]
        sl = pages[dept]["slots"].setdefault(slot_name, {"kind": slot.get("kind"), "captures": []})
        if status != "ok":
            sl["captures"].append({"year": year, "half": half, "status": status, "reason": reason,
                                   "tried": json.loads(tried or "[]")})
            continue
        final_url, sha, raw, ct, bj = con.execute(
            "select final_url, sha256, raw_zlib, content_type, blocks_json from captures where capture_url=?",
            (cap,)).fetchone()
        m = re.match(r"https://web\.archive\.org/web/(\d{14})id_/(.*)$", final_url or cap)
        wts, orig = (m.group(1), m.group(2)) if m else (ts, page_url)
        blocks = extract.blocks(zlib.decompress(raw), ct, cap)
        text = extract.collapse("\n".join(t for _, t in blocks))
        observed = f"{wts[:4]}-{wts[4:6]}-{wts[6:8]}"
        capture_url = f"https://web.archive.org/web/{wts}id_/{orig}"
        lo, hi, has_region = region_bounds(blocks, slot, orig)
        flags = page_flags(blocks, slot)
        entry = {"year": int(wts[:4]), "half": half, "status": "ok", "page_url": orig, "capture_url": capture_url,
                 "wayback_timestamp": wts, "observed_on": observed, "sha256": sha, "pis_listed": [],
                 "non_faculty_matches": []}
        if has_region and lo >= hi:
            entry["note"] = "listing region markers not found in this capture"
        by_block = collections.defaultdict(list)
        bm = match.all_block_matches(blocks, idx, split_cells=bool(slot.get("split_name_cells")))
        for mi in sorted({x for d in bm for x in d}):
            pi = pis[mi]
            for hit in match.find_pi(blocks, bm, mi):
                in_region = lo <= hit["block_index"] < hi
                if not in_region and has_region:
                    continue
                if slot.get("quote_require") and not re.search(slot["quote_require"], hit["quote"]):
                    continue
                by_block[hit["block_index"]].append((pi, hit))
        for bi, lst in sorted(by_block.items()):
            if len(lst) > 1:
                ambiguous.append({"kind": "one listing entry matches several input PIs",
                                  "pis": [p["pi"] for p, _ in lst], "bases": [h["match_basis"] for _, h in lst],
                                  "quote": lst[0][1]["quote"], "capture_url": capture_url, "listing": slot_name,
                                  "resolution": "rows kept for every input record (input duplicates of one person)"
                                  if len({h["name_as_written"] for _, h in lst}) == 1 else "rows kept"})
            for pi, hit in lst:
                if hit["match_basis"] == "initials":
                    others = [x for x in ambiguous_initials(text, hit)
                              if match.norm(x) != match.norm(hit["name_as_written"])]
                    if others:
                        ambiguous.append({"kind": "initials match with another same-surname, same-initial name on the page",
                                          "pi": pi["pi"], "name_as_written": hit["name_as_written"], "others": others,
                                          "capture_url": capture_url, "listing": slot_name,
                                          "resolution": "no row"})
                        continue
                ok, why, emer, visit = match.classify(hit, slot, flags, slot.get("untitled_ok", False) if has_region else False)
                if ok and (pi.get("drop_emeritus_rows") or slot.get("drop_emeritus")) and (
                        emer or visit or re.search(r"Professor of the Graduate School|\brecalled\b", " | ".join(hit["title_lines"]) + " || " + (hit["section_heading"] or ""), re.I)
                        or (re.search(r"Lecturer", " | ".join(hit["title_lines"]), re.I) and not re.search(r"Professor", " | ".join(hit["title_lines"]), re.I))):
                    # input PIs added by the appointment-period review (2026-10-26): emeritus / visiting entries are
                    # not appointment years and lecturer-only entries not PI years (owner rules), so they make no row; Berkeley's 'Professor of the Graduate School' is an emeritus title
                    ok, why = False, "emeritus, visiting or lecturer-only entry (drop_emeritus_rows / drop_emeritus)"
                if not ok:
                    entry["non_faculty_matches"].append({"pi": pi["pi"], "quote": hit["quote"],
                                                         "section_heading": hit["section_heading"], "reason": why})
                    nonfac.append((pi["pi"], int(wts[:4]), slot_name, why))
                    continue
                if (slot.get("listing_label") or slot.get("strict_title")) and \
                        not profiles.STRICT_TITLE.search(" | ".join(hit["title_lines"])):
                    entry["non_faculty_matches"].append({"pi": pi["pi"], "quote": hit["quote"],
                                                         "section_heading": hit["section_heading"],
                                                         "reason": "entry without a faculty title (strict listing)"})
                    nonfac.append((pi["pi"], int(wts[:4]), slot_name, "entry without a faculty title (strict listing)"))
                    continue
                fut = future_start(hit["quote"], observed)
                r = {"pi": pi["pi"], "department": dept, "page_url": orig, "capture_url": capture_url,
                     "wayback_timestamp": wts, "observed_on": observed, "year": int(wts[:4]), "sha256": sha,
                     "quote": hit["quote"],
                     "rank_as_listed": hit["title_lines"][0] if hit["title_lines"] else None,
                     "section_heading": hit["section_heading"],
                     "name_as_written": hit["name_as_written"],
                     "emeritus": emer, "visiting": visit,
                     "future_start_note": fut,
                     "outside_pi_departments": (None if dept_ok(pi, dept, cfg) is None else not dept_ok(pi, dept, cfg)),
                     "listing": slot_name, "half": half, "match_basis": hit["match_basis"]}
                if slot.get("listing_label"):
                    r["listing"] = slot["listing_label"]
                    r["listing_source"] = slot_name
                rows.append(r)
                entry["pis_listed"].append(pi["pi"])
        entry["pis_listed"] = sorted(set(entry["pis_listed"]))
        sl["captures"].append(entry)
        caps_by_year[int(wts[:4])].append((slot_name, dept, entry, text))
    # department profile pages (one-person listings) for gap PI-years, from table pplan (profiles.py)
    profile_checked = collections.defaultdict(list)
    try:
        pplan = con.execute("select pi, dept, detail, year, half, page_url, capture_url, wayback_timestamp, status, reason "
                            "from pplan order by pi, year, half").fetchall()
    except sqlite3.OperationalError:
        pplan = []
    pi_index = {p["pi"]: i for i, p in enumerate(pis)}
    for pname, dept, detail, year, half, page_url, cap, ts, status, reason in pplan:
        if pname not in pi_index:
            continue
        if status != "ok":
            profile_checked[(pname, year)].append(f"{detail} {half}: {reason}")
            continue
        pi = pis[pi_index[pname]]
        final_url, sha, raw, ct = con.execute(
            "select final_url, sha256, raw_zlib, content_type from captures where capture_url=?", (cap,)).fetchone()
        m = re.match(r"https://web\.archive\.org/web/(\d{14})id_/(.*)$", final_url or cap)
        wts, orig = (m.group(1), m.group(2)) if m else (ts, page_url)
        blocks = extract.blocks(zlib.decompress(raw), ct, cap)
        hit = profiles.profile_hit(blocks, ms[pi_index[pname]])
        if not hit:
            profile_checked[(pname, year)].append(f"{detail} {half}: no name + faculty title on the page")
            continue
        _tl = " | ".join(hit["title_lines"])
        if pi.get("drop_emeritus_rows") and (re.search(r"emerit|honorary|honoraire|retired|\bvisiting\b|Professor of the Graduate School|\brecalled\b", _tl, re.I)
                                             or (re.search(r"Lecturer", _tl, re.I) and not re.search(r"Professor", _tl, re.I))):
            profile_checked[(pname, year)].append(f"{detail} {half}: emeritus or visiting title (input drop_emeritus_rows)")
            continue
        observed = f"{wts[:4]}-{wts[4:6]}-{wts[6:8]}"
        tl = " | ".join(hit["title_lines"])
        rows.append({"pi": pname, "department": dept, "page_url": orig,
                     "capture_url": f"https://web.archive.org/web/{wts}id_/{orig}",
                     "wayback_timestamp": wts, "observed_on": observed, "year": int(wts[:4]), "sha256": sha,
                     "quote": hit["quote"], "rank_as_listed": hit["title_lines"][0] if hit["title_lines"] else None,
                     "section_heading": None, "name_as_written": hit["name_as_written"],
                     "emeritus": bool(re.search(r"emerit|honorary|honoraire|retired", tl, re.I)),
                     "visiting": bool(re.search(r"\bvisiting\b", tl, re.I)),
                     "future_start_note": future_start(hit["quote"], observed),
                     "outside_pi_departments": (None if dept_ok(pi, dept, cfg) is None else not dept_ok(pi, dept, cfg)),
                     "listing": "department profile page", "listing_source": detail, "half": half,
                     "match_basis": hit["match_basis"]})
        profile_checked[(pname, int(wts[:4]))].append(f"{detail} {half}: row")

    seen, dedup = set(), []
    for r in rows:
        k = (r["pi"], r["capture_url"], r["quote"], r["section_heading"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)
    rows = sorted(dedup, key=lambda r: (r["pi"], r["department"], r["observed_on"], r["listing"]))

    gaps = []
    for dept, d in pages.items():
        for slot_name, s in d["slots"].items():
            hist = collections.OrderedDict()
            for c in s["captures"]:
                if c.get("status") != "ok":
                    continue
                u = re.sub(r"^https?://(www2?\.)?", "", c["page_url"]).rstrip("/").lower()
                h = hist.setdefault(u, {"url": c["page_url"], "first_capture_used": c["observed_on"],
                                        "last_capture_used": c["observed_on"], "n_captures_used": 0})
                h["first_capture_used"] = min(h["first_capture_used"], c["observed_on"])
                h["last_capture_used"] = max(h["last_capture_used"], c["observed_on"])
                h["n_captures_used"] += 1
            s["url_history"] = sorted(hist.values(), key=lambda h: h["first_capture_used"])
            s["years_with_usable_capture"] = sorted({c["year"] for c in s["captures"] if c.get("status") == "ok"})
            for y in YEARS:
                cs = [c for c in s["captures"] if c["year"] == y]
                if not any(c.get("status") == "ok" for c in cs):
                    reasons = sorted({c.get("reason") or "" for c in cs if c.get("status") != "ok"})
                    gaps.append({"scope": "listing-year", "department": dept, "listing": slot_name,
                                 "listing_kind": s["kind"], "year": y,
                                 "reason": "; ".join(r for r in reasons if r) or "not planned"})

    # department-years with no usable capture of any main listing (sub-listings may still exist)
    dept_main_gaps = []
    for dept, d in pages.items():
        for y in YEARS:
            ok_main = any(c["year"] == y and c.get("status") == "ok" for sl, sv in d["slots"].items()
                          if sv["kind"] == "main" for c in sv["captures"])
            ok_any = any(c["year"] == y and c.get("status") == "ok" for sv in d["slots"].values() for c in sv["captures"])
            if not ok_main:
                g = {"scope": "department-year", "department": dept, "year": y,
                     "reason": "no usable capture of the department's main faculty listing in this year" +
                               (" (a sub-listing was captured)" if ok_any else "")}
                gaps.append(g)
                dept_main_gaps.append(f"{dept} {y}" + (" (sub-listing only)" if ok_any else ""))

    # coverage per PI
    cov = {}
    rows_by_pi = collections.defaultdict(list)
    for r in rows:
        rows_by_pi[r["pi"]].append(r)
    for pi in pis:
        prow = rows_by_pi.get(pi["pi"], [])
        by = collections.defaultdict(set)
        by_any = collections.defaultdict(set)
        fl = collections.defaultdict(lambda: collections.defaultdict(set))
        for r in prow:
            by_any[r["department"]].add(r["year"])
            if r["future_start_note"]:
                fl[r["department"]]["future_start_note"].add(r["year"])
                continue
            by[r["department"]].add(r["year"])
            for f in ("emeritus", "visiting", "outside_pi_departments"):
                if r[f]:
                    fl[r["department"]][f].add(r["year"])
            if r["rank_as_listed"] and re.search(r"lecturer|adjunct|affiliat|courtesy|consulting|special|adjoint", r["rank_as_listed"], re.I):
                fl[r["department"]]["non_ladder_title"].add(r["year"])
        cov[pi["pi"]] = {
            "departments": pi.get("departments"),
            "years_listed": {d: sorted(v) for d, v in sorted(by.items())},
            "all_years_listed_any_department": sorted(set().union(*by.values())) if by else [],
            "flags": {d: {k: sorted(v) for k, v in f.items()} for d, f in fl.items()},
            "years_only_with_future_start_note": {d: sorted(by_any[d] - by.get(d, set())) for d in by_any
                                                  if by_any[d] - by.get(d, set())},
        }

    # PI-year gaps: why is there no row?
    rel = getattr(cfg, "relevant_slots", None)
    nonfac_by = collections.defaultdict(list)
    for p, y, sname, why in nonfac:
        nonfac_by[(p, y)].append(f"{sname}: {why}")
    for pi in pis:
        years = set(cov[pi["pi"]]["all_years_listed_any_department"])
        fut = set().union(*cov[pi["pi"]]["years_only_with_future_start_note"].values()) \
            if cov[pi["pi"]]["years_only_with_future_start_note"] else set()
        mo = ms[pis.index(pi)]
        sur = match.norm(pi["pi"])[-1] if match.norm(pi["pi"]) else ""
        for y in YEARS:
            if y in years:
                continue
            relevant = [x for x in caps_by_year.get(y, []) if (rel is None or rel(pi, x[0], slots[x[0]]))]
            if y in fut:
                reason, kind = "named only with a future-start note in this year", "future_start_only"
            elif nonfac_by.get((pi["pi"], y)):
                reason, kind = "named, but not as faculty: " + "; ".join(sorted(set(nonfac_by[(pi["pi"], y)]))[:3]), "named_not_faculty"
            elif not relevant:
                reason, kind = "no usable capture of any listing for the PI's department(s) in this year", "no_capture"
            else:
                reason, kind = "captured listing(s) in this year do not name the PI", "no_match"
            g = {"scope": "pi-year", "pi": pi["pi"], "departments": pi.get("departments"), "year": y, "kind": kind,
                 "reason": reason,
                 "listings_checked": sorted({f"{x[0]} ({x[2]['observed_on']})" for x in relevant})}
            if profile_checked.get((pi["pi"], y)):
                g["profile_pages_checked"] = profile_checked[(pi["pi"], y)]
            if kind == "no_match" and sur:
                near = set()
                for _, _, _, text in relevant:
                    for m in re.finditer(r"(?:\S+\s+){0,3}" + re.escape(pi["pi"].split()[-1]) + r"\b", text, re.I):
                        near.add(m.group(0)[-80:])
                if near:
                    g["surname_seen_in"] = sorted(near)[:5]
            gaps.append(g)

    never = [p["pi"] for p in pis if not cov[p["pi"]]["all_years_listed_any_department"]]
    json.dump(rows, open(out / "listings.json", "w"), indent=1, ensure_ascii=False)
    json.dump(pages, open(out / "pages.json", "w"), indent=1, ensure_ascii=False)
    json.dump(gaps, open(out / "gaps.json", "w"), indent=1, ensure_ascii=False)
    json.dump(cov, open(out / "coverage.json", "w"), indent=1, ensure_ascii=False)
    json.dump(ambiguous, open(out / "ambiguous.json", "w"), indent=1, ensure_ascii=False)
    per_year = {y: len({r["pi"] for r in rows if r["year"] == y and not r["future_start_note"]}) for y in YEARS}
    summary = {"school": school, "captures_fetched": con.execute("select count(*) from captures where http_status=200").fetchone()[0],
               "captures_used": sum(1 for d in pages.values() for s in d["slots"].values() for c in s["captures"] if c.get("status") == "ok"),
               "rows": len(rows), "pis_in_input": len(pis), "pis_with_row": sum(1 for p in pis if cov[p["pi"]]["all_years_listed_any_department"]),
               "pis_listed_per_year": per_year, "pis_never_found": never,
               "ambiguous_entries": len(ambiguous),
               "department_years_without_main_listing": dept_main_gaps,
               "listing_year_gaps": [f"{g['listing']} {g['year']}" for g in gaps if g["scope"] == "listing-year"]}
    json.dump(summary, open(out / "summary.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("listing_year_gaps", "pis_never_found",
                                                                    "department_years_without_main_listing")}))
    print("never found:", len(never))


if __name__ == "__main__":
    main(sys.argv[1])
