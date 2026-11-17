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
# Owner-delegated 2026-11-09: a dated listing proves appointment for its own calendar year only, so these schools plan ONE capture per year and slot:
# the Jan-Jun capture; the Jul-Dec half is tried only when the first half has no usable capture (otherwise it is recorded out_of_scope).
ONE_CAPTURE_PER_YEAR = {"harvard", "toronto"}


CC_PREFIX = "commoncrawl:"  # capture_url of a Common Crawl record: commoncrawl:<warc filename>:<offset>:<length> (listings/scripts/cc.py)


def capture_stamp(cap, final_url, ts):
    """(capture timestamp, moved_away) for a fetched capture. A Wayback capture must end at its own web.archive.org/web/<ts>id_/ URL (its
    timestamp is then the final URL's); a Common Crawl record has no redirect rewriting, its timestamp is the crawl's and it never counts as moved."""
    if cap.startswith(CC_PREFIX):
        return ts, False
    m = re.match(r"https://web\.archive\.org/web/(\d{14})id_/", final_url or cap)
    return (m.group(1) if m else ts), not m


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


def slot_usable(con, cap, s, blocks, status, pis, school):
    """usable() first; a charter slot that names its own `format` (Tsinghua: Chinese titles and Chinese names, which the English title
    regexp and the Latin name matchers cannot see) is also usable when that format parses at least the floor of person entries."""
    good, why = usable(blocks, status, pis, school)
    if not good and status == 200 and s.get("format"):  # a config_<school>.py slot may name a format too (SJTU CS Chinese list, 2026-11-13)
        good, why2 = charter_usable(con, cap, s)
        why = None if good else why2 or why
    return good, why


def charter_usable(con, cap, s, floor=5):
    """A charter school's capture must parse (tools/listing_formats.py) to at least `floor` person entries: Michigan's
    2023-2025 spring captures of the CSE list looked like 31 KB shells with title-like navigation lines (learned
    2026-10-29); they were gzip-encoded full lists read undecoded (learned 2026-10-30), so the bytes go through wb.body."""
    import listing_formats
    raw = con.execute("select raw_zlib from captures where capture_url=?", (cap,)).fetchone()[0]
    html = wb.text(wb.body(raw)) if raw else ""
    fmt, es = listing_formats.parse(html, s.get("format"))
    # A rank-specific page can legitimately list fewer than five faculty.
    # Require an explicit parser and charter limit; never lower the default
    # shell guard for unreviewed or generic pages.
    if s.get('format') and isinstance(s.get('min_entries'), int) and 1 <= s['min_entries'] <= 5:
        floor = s['min_entries']
    if es and listing_formats.is_paged(html) and not s.get("prefix"):  # one page of several: a partial list passes the floor (UChicago CS 2017)
        return False, f"paged directory: this capture holds {len(es)} entries of one page (a listing_gaps entry records the year)"
    if len(es) < floor:
        return False, f"listing format {fmt} parses {len(es)} person entries (< {floor})"
    return True, None


def fetch_pages(con, s, cap, html, lo, hi, dept, min_entries=1):
    """The other pages of a paged directory capture (R3). Page links come from the capture (listing_formats.page_links); each page is the archived
    capture of that exact URL nearest in time to `cap` within the half-year [lo, hi] (the slot's own date window). -> ({n: (url, capture_url, ts)}, [missing n]).
    A page counts only when it is a 200 that parses to at least one entry."""
    import listing_formats
    base = con.execute("select page_url from captures where capture_url=?", (cap,)).fetchone()[0]
    m = re.match(r"https://web\.archive\.org/web/(\d{14})id_/(.*)", cap)
    ts0, original = m.group(1), m.group(2)
    def collect(links):
        got, missing = {}, []
        for n, u in links.items():
            want = u.split("://", 1)[-1]
            rows = wb.cdx({"url": want, "from": lo, "to": hi, "output": "json", "fl": "timestamp,original,statuscode,digest", "limit": "200"}, con)
            if rows is None:
                raise RuntimeError(f"CDX failed for {want}")
            rows = [r for r in rows if r["statuscode"] in ("200", "-") and lo <= r["timestamp"][:8] <= hi]
            rows.sort(key=lambda r: abs(days(r["timestamp"]) - days(ts0)))
            ok = None
            for r in rows[:2]:
                pc = wb.fetch_capture(r["timestamp"], r["original"], base, dept, con)
                st, _ = ensure_extracted(con, pc)
                raw = con.execute("select raw_zlib from captures where capture_url=?", (pc,)).fetchone()[0]
                if st == 200 and raw and len(listing_formats.parse(wb.text(wb.body(raw)), s.get("format"))[1]) >= min_entries:
                    ok = (u, pc, r["timestamp"])
                    break
            if ok:
                got[n] = ok
            else:
                missing.append(n)
        return got, missing

    got, missing = collect(listing_formats.page_links(html, original))
    # A "Show More" listing names only its next page. Follow each saved
    # page's pager until it ends; the first linked page is not the full roster.
    while not missing:
        links = {}
        for page_url, page_cap, _ in list(got.values()):
            raw = con.execute('select raw_zlib from captures where capture_url=?', (page_cap,)).fetchone()[0]
            for number, url in listing_formats.page_links(wb.text(wb.body(raw)), page_url).items():
                if number not in got:
                    links[number] = url
        if not links:
            break
        if len(got) + len(links) > 100:
            raise RuntimeError('faculty pager exceeds 100 pages; manual source review required')
        extra, missing = collect(links)
        got.update(extra)
    if missing:  # `?page=N` pages are often unarchived where the A-Z letter pages are: the union of every linked letter is the whole directory
        letters = listing_formats.letter_links(html, original)
        if letters:
            lgot, lmiss = collect(letters)
            if not lmiss:
                return lgot, []
            if len(lmiss) < len(missing):
                return lgot, lmiss
    return got, missing


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
            if school in ONE_CAPTURE_PER_YEAR and half == "H2" and y in years:
                h1 = con.execute("select status from plan where slot=? and year=? and half='H1'", (s["slot"], y)).fetchone()
                if h1 and h1[0] == "ok":
                    con.execute("insert or replace into plan values(?,?,?,?,?,?,?,?,?,?)",
                                (s["slot"], s["dept"], y, half, None, None, None, "out_of_scope",
                                 "year already proven by its Jan-Jun capture (one capture per calendar year)", "[]"))
                    con.commit()
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
                good, why = slot_usable(con, cap, s, b, st, pis, school)
                pages = {}
                if (good or (why or '').startswith('paged directory')) and getattr(_CFG.get(school), "CHARTER", False):
                    good, why = charter_usable(con, cap, s)
                    if not good and why and why.startswith("paged directory"):
                        # R3: a paged directory is one listing: fetch every page of the same half-year and keep the plan row only when all are archived
                        html = wb.text(wb.body(con.execute("select raw_zlib from captures where capture_url=?", (cap,)).fetchone()[0]))
                        pages, miss = fetch_pages(con, s, cap, html, lo, hi, s["dept"])
                        if not pages and not miss:
                            good, why = False, "paged directory: no page links found"
                        elif miss:
                            good, why = False, f"paged directory: pages {miss} of {len(pages) + len(miss) + 1} not archived in this half-year (page numbers or A-Z letters)"
                        else:
                            good, why = True, None
                fu = con.execute("select final_url from captures where capture_url=?", (cap,)).fetchone()[0] or cap
                fts, moved = capture_stamp(cap, fu, r["timestamp"])
                if st == 200 and moved:
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
                con.execute("delete from plan_pages where slot=? and year=? and half=?", (s["slot"], y, half))
                for n, (pu, pc, pts) in pages.items():
                    con.execute("insert into plan_pages values(?,?,?,?,?,?,?)", (s["slot"], y, half, n, pu, pc, pts))
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
