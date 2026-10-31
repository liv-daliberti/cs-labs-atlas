"""Build hierarchy/<school>/thesis-evidence.json and hierarchy/thesis-harvest-report.json from the thesis captures.

For every 2016-2026 thesis record (records.py) each adviser is matched to the school's PIs (names.PIIndex: the
hierarchy builder's own Name rules; co-advisers each count). A (PI, student) pair is 'held' when the student's name
matches one of the PI's students in hierarchy/<school>/students.json (Name rules: 'Last, First', middle names and
initials allowed); otherwise it becomes a student row {name, role, years, url, capture_url?, sha256, quote, note} whose
quote is an exact substring of the stored capture's whitespace-collapsed text naming the student and the adviser
relation. One row per pair: the evidence is the pair's most senior thesis (phd > masters > undergraduate, then latest);
years span all of the pair's theses (the others are listed in the note).
Advisers of CS-relevant theses that match no PI are counted per person and annotated from census/<school>-faculty.json.

usage: build.py [--final] [SCHOOL ...]   (default: all five; the report covers every school built so far;
       --final writes hierarchy/<school>/thesis-evidence.json and hierarchy/thesis-harvest-report.json)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import collections
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import names  # noqa: E402
import records  # noqa: E402

ROOT = names.ROOT
CENSUS = str(P.CENSUS)
SCHOOLS = ["princeton", "cmu", "epfl", "mit", "berkeley", "stanford"]
RANK = {"phd": 3, "masters": 2, "undergraduate": 1, "other": 0}
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
FINAL = "--final" in sys.argv  # without it, evidence and report go to thesis-tools/out/ (drafts)
# PIs that had no students before the 2026-10-27 zero-students pass (CS-related additions from non-CS departments): a row
# whose years do not overlap the PI's appointment (pis.json periods / listings) is dropped, not just reported. Rows of
# other PIs keep the earlier rule (reported under outside_pi_listing_years).
STRICT_YEARS = {
    "mit": {"Moe Z. Win", "Dara Entekhabi", "Pat Pataranutaporn", "Juan Pablo Vielma", "Konstantin Turitsyn", "Paul I. Barton",
            "Karen E. Willcox", "David E. Pritchard", "Jaime Peraire", "Qiqi Wang", "Drew Fudenberg", "Bart Van Parys",
            "Sinan Aral", "Nicholas C. Makris", "Duncan Simester"},
    "cmu": {"Cécile Péraire", "Yorie Nakahira", "Guannan Qu", "Michael D. Smith", "Daniel Yurovsky"},
    "epfl": {"José del R. Millán", "Andrea Cavallaro", "Andrew Sonta"},
    "princeton": {"Arash Adel", "Andrea Goldsmith"},
    # Stanford (gap 3, 2026-10-27): the 'cs_related_scope_20261022' additions (census/stanford-additions.json)
    "stanford": {"Yinyu Ye", "Kuang Xu", "Michael Saunders", "Brian A. Wandell", "Parag Mallick", "Gary Glover", "S Simon Wong", "Stephen Rock", "Nigam H. Shah", "Jose H. Blanchet", "Kay Giesecke", "Judith Degen", "Daniela Saban", "Gabriel Y. Weintraub", "E.J. Chichilnisky", "Kilian M. Pohl", "H.-S. Philip Wong", "Grace Gao", "Victor R. Lee", "Todd Coleman", "Wing Hung Wong", "Johan Ugander", "Per Enge", "Antony Jameson", "Fuhito Kojima", "Zachary Manchester", "Ingmar Riedel-Kruse", "Stefan Wager", "Md Tauhidul Islam", "Harikesh S. Nair"},
}
# Schools whose held pairs may carry EARLIER years (2026-10-27, Stanford: Profiles list only current advisees, so a student
# held from a 2023/2026 profile is often named on 2016-2022 Wayback captures too). For a pair already held, when the pair's
# records start before the held student's earliest year (from sources other than this file), one row with the record years
# and its quote goes to hierarchy/<school>/thesis-held-years-evidence.json; tools/pi_hierarchy.py merges it into the same
# lab's student record (within-lab name match), never across labs.
HELD_YEARS = {"stanford"}


def census(school):
    d = json.load(open(f"{CENSUS}/{school}-faculty.json"))
    L = d["faculty"] if isinstance(d, dict) else d
    out = []
    for x in L:
        al = x.get("aliases") or []
        if isinstance(al, str):
            try:
                al = json.loads(al.replace("'", '"'))
            except Exception:
                al = []
        out.append((names.Name([x["name"]] + list(al)), x))
    return out


def pkey(n):
    t = names.toks(n)
    return (names.given(t[0]), t[-1]) if len(t) >= 2 else (tuple(t), "")


def build(school):
    R = records.load(school)
    ix = names.PIIndex(school)
    stu = json.load(open(f"{ROOT}/{school}/students.json"))
    # students.json is rebuilt by tools/pi_hierarchy.py, which also reads thesis-evidence.json: a student held only through
    # an earlier version of this file is not 'already held' (keeps the build idempotent)
    own = set()
    if os.path.exists(f"{ROOT}/{school}/thesis-evidence.json"):
        for r_ in json.load(open(f"{ROOT}/{school}/thesis-evidence.json")):
            for s_ in r_["students"]:
                own.add(s_["sha256"])
    own_hy = set()  # rows of an earlier thesis-held-years-evidence.json never count as the held years
    if os.path.exists(f"{ROOT}/{school}/thesis-held-years-evidence.json"):
        for r_ in json.load(open(f"{ROOT}/{school}/thesis-held-years-evidence.json")):
            for s_ in r_["students"]:
                own_hy.add(s_["sha256"])

    def held_first(s_):
        ys = [y_ for rel in s_.get("relations") or [] if not all(src.get("sha256") in own_hy | own for src in rel.get("sources") or [{}])
              for y_ in rel.get("years") or [] if isinstance(y_, int)]
        return min(ys) if ys else None

    def independent(s_):
        srcs = [src for rel in s_.get("relations") or [] for src in rel.get("sources") or []]
        return not srcs or not all(src.get("sha256") in own for src in srcs)
    held = {pi: [names.Name([s_["name"]]) for g in ix.group(pi) for s_ in stu.get(g, []) if independent(s_)] for pi in ix.name}
    held_raw = {pi: [s_["name"] for g in ix.group(pi) for s_ in stu.get(g, []) if independent(s_)] for pi in ix.name}
    held_y = {pi: [(names.Name([s_["name"]]), s_["name"], held_first(s_)) for g in ix.group(pi) for s_ in stu.get(g, []) if independent(s_)]
              for pi in ix.name}
    active = {}
    for p_ in ix.pis:
        ys = {l_.get("year") for l_ in p_.get("listings") or [] if isinstance(l_.get("year"), int)}
        for per in p_.get("periods") or []:
            a_ = records.year_of(str(per.get("start") or ""))
            b_ = records.year_of(str(per.get("end") or "")) or 2026
            if a_:
                ys |= set(range(max(a_, 2010), b_ + 1))
        active[p_["pi"]] = (min(ys), max(ys)) if ys else None
    outside = []
    cen = census(school)
    stats = collections.Counter()
    uniq = collections.defaultdict(set)
    by_source = collections.Counter()
    by_year = collections.Counter()
    pairs = {}            # (pi, student key) -> list of (record, adviser_raw)
    held_pairs, ambiguous, failures = set(), [], []
    near = collections.Counter()  # adviser strings sharing a PI's surname but not matching the PI (alias review)
    inexact = collections.Counter()  # (adviser, PI, how) matched by the ligature / second-given-name / typo rules
    nonpi = collections.defaultdict(lambda: {"variants": collections.Counter(), "theses": set(), "years": collections.Counter(),
                                             "examples": []})
    for r in R:
        if not r.get("advisers") or not r.get("student"):
            continue
        tkey = (pkey(r["student"]), r["role"])  # one thesis seen in two sources (dissertation list + tech report) counts once
        stats["thesis_records"] += 1
        uniq["harvested"].add(tkey)
        by_source[r["source"]] += 1
        by_year[r["year"]] += 1
        if r["cs"]:
            uniq["cs"].add(tkey)
        matched = []
        for a in r["advisers"]:
            m, how = ix.match_info(a)
            if len(m) == 1 or (how == "embedded" and m):  # 'embedded': several advisers run together in one string
                for pi_ in m:
                    matched.append((a, pi_))
                    if how != "exact":
                        inexact[(a, pi_, how)] += 1
            elif len(m) > 1:
                ambiguous.append({"thesis": r["id"], "adviser": a, "pis": m})
            else:
                t_ = names.toks(names.clean_adviser(a))
                if len(t_) >= 2:
                    for pi_ in ix.surnames.get(t_[-1], set()) | ix.surnames.get("".join(t_[1:]), set()):
                        near[(names.clean_adviser(a), pi_)] += 1
            if not m and r["cs"]:
                k = pkey(names.clean_adviser(a))
                if not k[1]:
                    continue
                e = nonpi[k]
                e["variants"][names.clean_adviser(a)] += 1
                e["theses"].add(r["id"])
                e["years"][r["year"]] += 1
                if len(e["examples"]) < 3:
                    e["examples"].append({"student": r["student"], "year": r["year"], "role": r["role"], "id": r["id"], "url": r["url"]})
        if not matched:
            continue
        uniq["pi"].add(tkey)
        for a, pi in matched:
            if ix.name[pi].match(r["student"]):  # the PI's own thesis
                continue
            stats["thesis_pi_links"] += 1
            k = (pi, pkey(r["student"]))
            pairs.setdefault(k, []).append((r, a))
    rows = collections.defaultdict(list)
    added = 0
    no_overlap = []  # STRICT_YEARS rows dropped: their years do not overlap the PI's appointment
    fams = {p_["pi"]: names.pi_family_names(p_["pi"], p_.get("names"), school) for p_ in ix.pis}
    held_rows = collections.defaultdict(list)

    def make_row(pi, student, lst):
        lst = sorted(lst, key=lambda x: (RANK.get(x[0]["role"], 0), x[0]["year"]), reverse=True)
        row = None
        for r, a in lst:  # most senior thesis whose quote can be built
            try:
                quote = r["q"](a)
            except ValueError as e:
                failures.append({"pi": pi, "student": r["student"], "thesis": r["id"], "error": str(e)[:200]})
                continue
            if not names.has_tokens(quote, r["student"]) and not names.has_tokens(quote, names.nat(r["author_raw"])):
                failures.append({"pi": pi, "student": r["student"], "thesis": r["id"], "error": "quote lacks the student's name"})
                continue
            if not names.names_pi(quote, fams[pi]):
                failures.append({"pi": pi, "student": r["student"], "thesis": r["id"], "error": "quote does not name the PI (escaped JSON?)"})
                continue
            # the row's name must be named by its own quote (verify.py): the pair's first-seen name form, else this record's
            name_ = next((n_ for n_ in (student, r["student"]) if names.has_tokens(quote, n_)), None)
            if name_ is None:
                failures.append({"pi": pi, "student": r["student"], "thesis": r["id"], "error": "quote lacks the row's name form"})
                continue
            ys = sorted({y_ for x in lst for y_ in (x[0].get("years") or [x[0]["year"]])})  # a record may carry a span (berkeley_depts)
            others = [f"{x[0]['source']} {x[0]['id']} ({x[0]['year']}, {x[0]['role']})" for x in lst if x[0] is not r]
            how = ix.match_info(a)[1]
            note = (f"{r['source']} {r['id']} ({r['year']}, {r['role']}; {r['degree']}; {r['dept'][:80]}): "
                    f"'{r['title'][:100]}'; adviser '{a}' = {pi}" +
                    ({"ligature": " (catalogue lost the ff/fi ligature)", "second-given": " (PI known by the second given name)",
                      "fuzzy": " (catalogue misspells or shortens the PI's name)",
                      "embedded": " (one of several advisers run together in one catalogue field)"}.get(how, "")))
            if others:
                note += "; also " + "; ".join(sorted(set(others))[:4])
            row = {"name": name_, "role": r["role"] if r["role"] in RANK and r["role"] != "other" else "other",
                   "years": [ys[0], ys[-1]], "url": r["url"]}
            if r.get("capture_url"):
                row["capture_url"] = r["capture_url"]
            row.update({"sha256": r["sha256"], "quote": quote, "note": note})
            break
        return row

    for (pi, sk), lst in pairs.items():
        student = lst[0][0]["student"]
        if any(h.match(student) for h in held[pi]) or any(names.Name([student]).match(h) for h in held_raw[pi]):
            held_pairs.add((pi, sk))
            if school in HELD_YEARS:
                ys_ = [y_ for x in lst for y_ in (x[0].get("years") or [x[0]["year"]])]
                h1 = [hy for hn, hr, hy in held_y[pi] if (hn.match(student) or names.Name([student]).match(hr)) and hy]
                if ys_ and h1 and min(ys_) < min(h1):
                    hrow = make_row(pi, student, lst)
                    if hrow:
                        hrow["note"] = f"earlier years of a held student (held from {min(h1)}): " + hrow["note"]
                        act = active.get(pi)
                        if not (act and not (hrow["years"][0] <= act[1] and hrow["years"][1] >= act[0])):
                            held_rows[pi].append(hrow)
            continue
        row = make_row(pi, student, lst)
        if row:
            act = active.get(pi)
            if pi in STRICT_YEARS.get(school, ()) and act and not (row["years"][0] <= act[1] and row["years"][1] >= act[0]):
                no_overlap.append({"pi": pi, "student": row["name"], "years": row["years"], "pi_listed": list(act)})
                continue
            rows[pi].append(row)
            added += 1
            if act and not (act[0] - 1 <= row["years"][0] and row["years"][1] <= act[1] + 1):
                outside.append({"pi": pi, "student": row["name"], "years": row["years"], "pi_listed": list(act)})
    order = [p["pi"] for p in ix.pis]
    ev = []
    for pi in order:
        if not rows.get(pi):
            continue
        nheld = sum(1 for (p, _) in held_pairs if p == pi)
        srcs = sorted({re.match(r"(\S+)", r_["note"]).group(1) for r_ in rows[pi]})
        listing = set(srcs) & {"lab-roster", "lab-theses", "pi-homepage", "pi-cv", "dept-roster",
                                   "pi-profile", "dept-directory", "colleague-page"}  # berkeley_depts.py / lab_sources.py sources
        ev.append({"pi": pi, "students": sorted(rows[pi], key=lambda x: (x["years"][0], x["name"])),
                   "notes": ((f"Advisee hunt 2026-10-27: {len(rows[pi]) + nheld} students named as {pi}'s advisees, lab students "
                              f"or thesis students 2016-2026 ({', '.join(srcs)}); {nheld} already held, {len(rows[pi])} added here.")
                             if listing else
                             (f"Thesis hunt 2026-10-22: {len(rows[pi]) + nheld} students with a 2016-2026 thesis naming {pi} as "
                              f"adviser ({', '.join(srcs)}); {nheld} already held, {len(rows[pi])} added here."))})
    os.makedirs(STATE, exist_ok=True)
    json.dump(ev, open(f"{ROOT}/{school}/thesis-evidence.json" if FINAL else f"{STATE}/{school}-thesis-evidence.json", "w"),
              indent=1, ensure_ascii=False)
    if school in HELD_YEARS:
        hev = [{"pi": pi, "students": sorted(held_rows[pi], key=lambda x: (x["years"][0], x["name"])),
                "notes": f"Earlier advising years of {len(held_rows[pi])} students already held for {pi} (2026-10-27): dated captures that "
                         f"name them before the held sources do."} for pi in order if held_rows.get(pi)]
        json.dump(hev, open(f"{ROOT}/{school}/thesis-held-years-evidence.json" if FINAL else f"{STATE}/{school}-thesis-held-years-evidence.json", "w"),
                  indent=1, ensure_ascii=False)
    # non-PI advisers of CS-relevant theses
    np_list = []
    for k, e in nonpi.items():
        variant = e["variants"].most_common(1)[0][0]
        c = [x for n_, x in cen if n_.match(variant)]
        ce = None
        if c:
            x = c[0]
            ce = {k2: x.get(k2) for k2 in ("name", "rank", "title_as_listed", "departments", "units", "is_pi", "pi_basis", "years_listed",
                                           "scs_appointment", "flags") if x.get(k2) not in (None, "", [], "None")}
        np_list.append({"adviser": variant, "variants": dict(e["variants"]), "theses": len(e["theses"]),
                        "years": dict(sorted(e["years"].items())), "census": ce, "examples": e["examples"]})
    np_list.sort(key=lambda x: (-x["theses"], x["adviser"]))
    rep = {"theses_harvested": len(uniq["harvested"]), "theses_cs_relevant": len(uniq["cs"]),
           "theses_with_pi_adviser": len(uniq["pi"]), "thesis_records": stats["thesis_records"], "thesis_pi_links": stats["thesis_pi_links"],
           "pairs_found": len(pairs), "pairs_already_held": len(held_pairs), "pairs_added": added,
           "held_pairs_with_earlier_years": sum(len(v) for v in held_rows.values()),
           "pis_with_additions": len(ev), "quote_failures": failures, "ambiguous_adviser_matches": ambiguous[:50],
           "by_source": dict(by_source), "by_year": dict(sorted(by_year.items())),
           "inexact_adviser_matches": [{"adviser": a, "pi": p, "how": h, "theses": n} for (a, p, h), n in inexact.most_common()],
           "outside_pi_listing_years": outside, "dropped_no_appointment_overlap": no_overlap,
           "duplicate_pi_entries": sorted({g for g in ix.dup.values()}),
           "surname_near_misses": [{"adviser": a, "pi": p, "theses": n} for (a, p), n in near.most_common()],
           "top_pis_by_additions": sorted(([pi, len(v)] for pi, v in rows.items()), key=lambda x: -x[1])[:15]}
    os.makedirs(STATE, exist_ok=True)
    json.dump({"school": school, "report": rep, "non_pi_advisers": np_list}, open(f"{STATE}/{school}.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"school": school, **{k: v for k, v in rep.items() if not isinstance(v, (list, dict))},
                      "failures": len(failures), "ambiguous": len(ambiguous), "non_pi_advisers": len(np_list),
                      "non_pi_3plus": sum(1 for x in np_list if x["theses"] >= 3)}), flush=True)


SOURCES = {
    "stanford": "Stanford Digital Repository dissertations: DataCite REST list of SDR (10.25740) Dissertation DOIs -> each PURL's "
                "public MODS (degree supervisor = adviser), fetched by claude-stanford-20261027/tools/st_dissertations.py and copied "
                "in by harvest_stanford.py; SearchWorks answers bots with a JavaScript check and is not used; the SDR DOIs cover "
                "2025-2027 degrees only",
    "princeton": "DataSpace OAI-PMH ListRecords (metadataPrefix=dim, resumption tokens): Doctoral Dissertations community "
                 "(all departments, 2011-2025), Master's Theses community (2022-2024), senior-thesis collections of CS, ECE, "
                 "ORFE, MAE, Math, Psychology, Neuroscience, SPIA, Sociology, Architecture, Music, Molecular Biology, "
                 "Economics, Physics, Independent Concentration. CS-relevant = CS dissertation / senior / master's collections. "
                 "2026-10-27: lab and ECE people pages for PIs no DataSpace record names (lab_sources.py).",
    "cmu": "SCS report archive (reports-archive.adm.cs.cmu.edu: cs2016-2026, ml2016-2020, isr2016-2022, hcii 2016-2026; "
           "'Thesis Committee' Chair/Co-Chair = adviser) + KiltHub via the figshare API (group 18614, item_type thesis, "
           "published since 2016; custom field 'Advisor(s)'). CS-relevant = SCS archive series and KiltHub SCS departments "
           "(CSD, MLD, RI, LTI, HCII, ISR/S3D, CBD). 2026-10-27: lab / "
           "colleague / department-directory pages for PIs whose students KiltHub does not show (lab_sources.py).",
    "epfl": "Infoscience REST discover (dc.type doctoral thesis and student-work master thesis, issued 2016-2026, all "
            "doctoral schools/sections; dc.contributor.advisor = thesis directors). CS-relevant = EDIC theses and IC-section "
            "master theses. 2026-10-27: lab and "
            "people pages for PIs with no thesis yet (lab_sources.py).",
    "mit": "DSpace@MIT REST discover at 100 s per request: dc.relation.orgunit EECS, issued 2016..2026 by year, plus "
           "adviser-name queries for every PI outside EECS (dc.contributor.advisor = thesis supervisor). DSpace@MIT has no "
           "EECS-specific thesis collection to page over OAI-PMH. CS-relevant = EECS theses. 2026-10-27: the CS-related review's "
           "adviser-name pages copied in (harvest_mit.py review) and the same queries for PIs added since (harvest_mit.py pis), "
           "plus the PIs' own lab pages for PIs no catalogue covers (lab_sources.py).",
    "berkeley": "EECS Ph.D. dissertations by year (Pubs/Dissertations/Years/2016-2026, '[advisor: ...]') + every EECS "
                "technical report 2016-2026 whose BibTeX is @phdthesis/@mastersthesis ('Advisors:'). CS-relevant = all EECS. "
                "Outside EECS (berkeley_depts.py, 2026-10-27): Mathematics 'Past PhD Students' (student; advisor), I School "
                "'Completed Ph.D. Dissertations' ('Advisor(s):'), and the non-EECS PIs' own lab rosters, alumni lists and CVs "
                "(live and Wayback captures; quote = the stretch from the PI's name to the student's entry).",
}


COVERAGE = {
    "stanford": "Only the SDR dissertations with DataCite DOIs (degrees conferred 2025-2027, a handful earlier); no catalogue of "
                "2016-2024 Stanford dissertations with advisers is reachable without SearchWorks (bot check). Earlier advising "
                "comes from the Stanford Profiles advisee lists and curated faculty homepages (census/stanford-faculty.json).",
    "princeton": "DataSpace holds dissertations through part of 2025 and senior theses through 2024 (no 2025/2026 senior "
                 "collections yet); master's theses only 2022-2024.",
    "cmu": "SCS archive: 9 indexed thesis abstract pages return 404 (2016-2024); ML after 2020, S3D after 2022, RI, LTI and "
           "CBD come from KiltHub only (deposits are thin before 2018). 3 KiltHub records whose author or PI name is stored "
           "only as \\u-escaped JSON and 1 archive page with two authors run together have no usable quote (quote_failures).",
    "epfl": "Infoscience doctoral and master theses issued 2016-2026, every doctoral school/section.",
    "mit": "EECS theses (dc.relation.orgunit) by issue year, then adviser-name queries for PIs outside EECS; one request per "
           "100 s, slowed further by 429s (DSpace@MIT also serves the MIT full-text collector from this host). The orgunit "
           "tag misses some EECS theses (2016: 326 tagged theses); untagged theses supervised by a PI are reached by the "
           "adviser-name queries (step 2), so only the non-PI adviser counts undercount them.",
    "berkeley": "EECS Ph.D. dissertations 2016-2026 (complete lists by year) and the EECS technical reports that are theses; "
                "M.S. theses are covered only when published as a technical report. Non-EECS lab rosters date students by "
                "the stated (graduation / start / expected) year, else by the capture year of each Wayback capture listing them.",
}


def harvest_done(s):
    log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", f"{s}.log")
    return os.path.exists(log) and "ALLDONE" in open(log).read()


def report():
    out = {"generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "method": ("Theses of 2016-2026 with an adviser field, harvested per school into hierarchy/<school>/"
                      "thesis-captures.sqlite; advisers matched to hierarchy/<school>/pis.json by full name (co-advisers each "
                      "count); pairs checked against hierarchy/<school>/students.json; missing pairs written to "
                      "hierarchy/<school>/thesis-evidence.json. Non-PI advisers are counted over CS-relevant theses only."),
           "schools": {}, "non_pi_advisers": {}}
    for s in SCHOOLS:
        p = f"{STATE}/{s}.json"
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        r = d["report"]
        out["schools"][s] = {"sources": SOURCES[s], **{k: r[k] for k in (
            "theses_harvested", "thesis_records", "theses_cs_relevant", "theses_with_pi_adviser", "thesis_pi_links", "pairs_found",
            "pairs_already_held", "pairs_added", "pis_with_additions", "by_source", "by_year", "top_pis_by_additions")},
            "harvest_complete": harvest_done(s), "coverage_notes": COVERAGE[s],
            "adviser_match_review": {k: r.get(k) for k in ("inexact_adviser_matches", "duplicate_pi_entries", "outside_pi_listing_years",
                                                             "dropped_no_appointment_overlap")},
            "quote_failures": r["quote_failures"], "ambiguous_adviser_matches": r["ambiguous_adviser_matches"]}
        out["non_pi_advisers"][s] = d["non_pi_advisers"]
    json.dump(out, open(f"{ROOT}/thesis-harvest-report.json" if FINAL else f"{STATE}/thesis-harvest-report.json", "w"),
              indent=1, ensure_ascii=False)


if __name__ == "__main__":
    for s in ([a for a in sys.argv[1:] if not a.startswith("--")] or SCHOOLS):
        build(s)
    report()
