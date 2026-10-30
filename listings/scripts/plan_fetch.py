"""Choose and fetch two captures per (slot, year): one Jan-Jun (H1), one Jul-Dec (H2).

usage: plan_fetch.py <school> [slot-substring ...]
Slots come from config_<school>.py. Writes table `plan` (one row per slot/year/half) in
listings/<school>/captures.sqlite. Resumable: rows already 'ok' / 'nocapture' / 'unusable' are skipped;
a CDX failure leaves the slot unplanned so a re-run retries it.
"""
import importlib
import json
import os
import re
import sys
import time
import urllib.parse
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
import extract
import match

YEARS = list(range(2016, 2027))


def ts_date(ts):
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"


def halves(y):
    return [("H1", f"{y}0101", f"{y}0630", f"{y}0401"), ("H2", f"{y}0701", f"{y}1231", f"{y}1001")]


def days(ts):
    return time.mktime(time.strptime(ts[:8], "%Y%m%d")) / 86400


def charter_config(school):
    """A school without config_<school>.py (protocol schools, 2026-10-29: Michigan first) takes its listing slots from
    its charter, schools/<key>.toml [[departments.listings]] (tools/school_config.py listing_slots)."""
    import types
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools"))
    import school_config
    return types.SimpleNamespace(SLOTS=school_config.listing_slots(school), DEPT_CODES={}, relevant_slots=lambda pi, n, s: True, CHARTER=True)


_CFG = {}


def charter_usable(con, cap, s, floor=5):
    """A charter school's capture must parse (tools/listing_formats.py) to at least `floor` person entries: Michigan's
    2023-2025 spring captures of the CSE list looked like 31 KB shells with title-like navigation lines (learned
    2026-10-29); they were gzip-encoded full lists read undecoded (learned 2026-10-30), so the bytes go through wb.body."""
    import zlib
    import listing_formats
    raw = con.execute("select raw_zlib from captures where capture_url=?", (cap,)).fetchone()[0]
    fmt, es = listing_formats.parse(wb.body(raw).decode("utf-8", "replace") if raw else "", s.get("format"))
    if len(es) < floor:
        return False, f"listing format {fmt} parses {len(es)} person entries (< {floor})"
    return True, None


def load(school):
    try:
        cfg = importlib.import_module(f"config_{school}")
    except ImportError:
        cfg = charter_config(school)
    _CFG[school] = cfg
    ip = wb.input_path(school)
    # a protocol school builds its census FROM the listings, so before stage 2 there is no input PI list: a capture is
    # then usable on its title lines alone (usable())
    pis = json.load(open(ip))["pis"] if os.path.exists(ip) else []
    return cfg, pis


_MS = {}


TITLE_LINE = re.compile(r"^([\w,&.()'-]+\s+){0,6}(Professor|Professeur|Lecturer|Instructor|Scientist)\b", re.I)


def usable(blocks, status, pis, school):
    """A capture is usable when it is a 200 and reads as a listing: it names an input PI, or it carries
    at least two title lines ('Associate Professor', 'Adjunct Professor of ...'). Script-rendered shells
    and landing pages carry neither."""
    if status != 200:
        return False, f"http status {status}"
    if school not in _MS:
        _MS[school] = match.Index(match.matchers(pis))
    ntitle = sum(1 for _, t in blocks if len(t) < 160 and TITLE_LINE.match(t))
    found = set()
    for d in match.all_block_matches(blocks, _MS[school]):
        found.update(d)
        if found:
            break
    if found or ntitle >= 2:
        return True, None
    return False, f"no listing in the capture ({len(blocks)} text blocks, {ntitle} title lines, no input PI name)"


def ensure_extracted(con, cap):
    st, raw, ct, bj = con.execute(
        "select http_status, raw_zlib, content_type, blocks_json from captures where capture_url=?", (cap,)).fetchone()
    if bj is None:
        b = extract.blocks(zlib.decompress(raw), ct, cap) if raw else []
        txt = "\n".join(t for _, t in b)
        con.execute("update captures set blocks_json=?, text=? where capture_url=?", (json.dumps(b), txt, cap))
        con.commit()
    else:
        b = json.loads(bj)
    return st, b


def candidates(s, con):
    cands = []
    for pri, spec in enumerate(s["urls"]):
        u, lo, hi = spec[:3]
        opt = spec[3] if len(spec) > 3 else {}
        params = {"url": u, "from": "2016", "to": "2026", "output": "json",
                  "fl": "timestamp,original,statuscode,mimetype,digest,length", "limit": "20000"}
        if opt.get("prefix"):
            params["matchType"] = "prefix"
        rows = wb.cdx(params, con)
        if rows is None:
            raise RuntimeError(f"CDX failed for {u}")
        for r in rows:
            if r["statuscode"] not in ("200", "-"):
                continue
            if opt.get("match") and not re.search(opt["match"], urllib.parse.unquote_plus(r["original"])):
                continue
            if not (lo <= r["timestamp"][:8] <= hi):
                continue
            if s.get("url_exact") and r["original"].split("://", 1)[-1].lower().rstrip("/") not in \
                    [x.lower().rstrip("/") for x in s["url_exact"]]:
                continue
            cands.append((pri, u, r))
    return cands


def run_slot(school, s, con, pis, max_tries=2):
    print("==", s["slot"], flush=True)
    try:
        cands = candidates(s, con)
    except Exception as e:
        print("  skipping slot this run:", e, flush=True)
        return
    years = s.get("years", YEARS)
    for y in YEARS:
        for half, lo, hi, mid in halves(y):
            done = con.execute("select status from plan where slot=? and year=? and half=?",
                               (s["slot"], y, half)).fetchone()
            if done and done[0] in ("ok", "nocapture", "unusable", "out_of_scope"):
                continue
            if y not in years:
                con.execute("insert or replace into plan values(?,?,?,?,?,?,?,?,?,?)",
                            (s["slot"], s["dept"], y, half, None, None, None, "out_of_scope",
                             s.get("years_note", "listing not used in this year"), "[]"))
                con.commit()
                continue
            inhalf = [c for c in cands if lo <= c[2]["timestamp"][:8] <= hi]
            if not inhalf:
                con.execute("insert or replace into plan values(?,?,?,?,?,?,?,?,?,?)",
                            (s["slot"], s["dept"], y, half, None, None, None, "nocapture",
                             "no archived 200 capture of the listing URL(s) in this half-year", "[]"))
                con.commit()
                continue
            inhalf.sort(key=lambda c: (c[0], abs(days(c[2]["timestamp"]) - days(mid))))
            seen, order = set(), []
            for c in inhalf:  # de-duplicate by digest so retries look at different content
                k = (c[1], c[2]["digest"])
                if k in seen:
                    continue
                seen.add(k)
                order.append(c)
            tried, okcap, reason = [], None, None
            per_pri, picked = {}, []
            for c in order:  # at most `max_tries` captures per URL, so a dead URL era cannot starve the next one
                per_pri[c[0]] = per_pri.get(c[0], 0) + 1
                if per_pri[c[0]] <= max_tries:
                    picked.append(c)
            for pri, u, r in picked:
                cap = wb.fetch_capture(r["timestamp"], r["original"], u, s["dept"], con)
                st, b = ensure_extracted(con, cap)
                good, why = usable(b, st, pis, school)
                if good and getattr(_CFG.get(school), "CHARTER", False):
                    good, why = charter_usable(con, cap, s)
                fu = con.execute("select final_url from captures where capture_url=?", (cap,)).fetchone()[0] or cap
                m = re.match(r"https://web\.archive\.org/web/(\d{14})id_/", fu)
                fts = m.group(1) if m else r["timestamp"]
                if st == 200 and not m:
                    good, why = False, f"redirected away from the capture ({fu[:120]})"
                if good and not (lo <= fts[:8] <= hi):
                    good, why = False, f"redirected to capture {fts} outside the half-year"
                tried.append({"capture_url": cap, "status": st, "usable": good, "why": why})
                print(f"  {y}{half} {r['timestamp']} {u} -> {st} {'OK' if good else why}", flush=True)
                if good:
                    okcap = (cap, u, fts)
                    break
                reason = why
            if okcap:
                con.execute("insert or replace into plan values(?,?,?,?,?,?,?,?,?,?)",
                            (s["slot"], s["dept"], y, half, okcap[1], okcap[0], okcap[2], "ok", None, json.dumps(tried)))
            elif any(t["status"] in (-1, 429) for t in tried):  # a capture still 5xx after back-off counts as broken
                print(f"  {y}{half} transient failure; left unplanned for a re-run", flush=True)
                continue
            else:
                con.execute("insert or replace into plan values(?,?,?,?,?,?,?,?,?,?)",
                            (s["slot"], s["dept"], y, half, None, None, None, "unusable", reason, json.dumps(tried)))
            con.commit()


def missing(school, cfg, con):
    have = {(a, b, c) for a, b, c in con.execute("select slot, year, half from plan")}
    return [(s["slot"], y, h) for s in cfg.SLOTS for y in YEARS for h in ("H1", "H2") if (s["slot"], y, h) not in have]


def main(argv):
    school, filters = argv[0], argv[1:]
    cfg, pis = load(school)
    con = wb.db(school)
    if filters == ["--check"]:
        m = missing(school, cfg, con)
        print(school, "unplanned slot-halves:", len(m), m[:10], flush=True)
        sys.exit(3 if m else 0)
    for s in cfg.SLOTS:
        if filters and not any(f.lower() in s["slot"].lower() for f in filters):
            continue
        run_slot(school, s, con, pis)
    print("done", school, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
