"""MIT thesis harvest (2016-2026) from DSpace@MIT into hierarchy/mit/thesis-captures.sqlite (single writer).

DSpace@MIT has no EECS-specific thesis collection (the EECS department community holds no collections; theses are owned
by the MIT-wide Doctoral / Graduate / Undergraduate Theses collections, all departments and all years), so instead of
paging those whole collections over OAI-PMH we page the DSpace REST discover endpoint with the department and date
filters (robots.txt allows /server/api; it disallows only the /search UI):
  1. EECS: query dc.relation.orgunit:"Electrical Engineering and Computer Science", f.dateIssued=[Y TO Y] for each year
     2016..2026, sorted by dc.date.accessioned, 100 items per page (the server caps a page at 100: a single size=1000
     probe returned 100 items and reported totalElements=100; its items duplicate page 0 and are de-duplicated);
  2. other departments: dc.contributor.advisor:((First AND Last) OR ...) AND NOT <the EECS orgunit query>, for the
     school's PIs in groups, 2016-2026 — theses supervised by an EECS PI in Math, BCS, Media Arts, IDSS, ORC, CSE, etc.
  3. (2026-10-27) 'review': the adviser-name discover pages the CS-related review stored in
     hierarchy/mit/cs-related-captures.sqlite (PIs added from AeroAstro, CEE, Sloan, MechE, ChemE, Physics, Economics,
     Media Lab; same endpoint, same 2016-2026 / NOT-EECS filters) are copied in unchanged (same fetched_at, sha256 and
     bytes; copied_from set) instead of being requested again;
  4. (2026-10-27) 'pis NAME...': step 2 restricted to the named PIs of pis.json (PIs added after the step-2 run).
One request every 100 s (tcap's per-host spacing, shared across processes); on 429 wait Retry-After (+5 s) or 905 s.
Resumable: a page whose 200 response is already stored is not fetched again.
usage: setsid nohup python -I harvest_mit.py [eecs] [advisors] > logs/mit.log 2>&1 &
       python -I harvest_mit.py review ; python -I harvest_mit.py pis "Bart Van Parys" "Sinan Aral"  (append to a log)
"""
import json
import os
import re
import sys
import time
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402
import names  # noqa: E402

S = "mit"
BASE = "https://dspace.mit.edu/server/api/discover/search/objects?"
EECS_Q = 'dc.relation.orgunit:"Electrical Engineering and Computer Science"'
GROUP = 14
REVIEW = f"{tcap.ROOT}/mit/cs-related-captures.sqlite"
# the CS-related review's store: an exact discover URL stored there is copied in, not requested again (read-only)
tcap.SISTER[S] = list(dict.fromkeys(tcap.SISTER[S] + [REVIEW]))


SIZES = [100]  # DSpace@MIT caps discover results at 100 per request and then misreports totalElements for larger sizes (tested once: size=1000 -> 100 items, totalElements 100)
SIZE = [SIZES[0]]


def url_for(q, page, date_range, size=None):
    return BASE + urlencode({"query": q, "dsoType": "ITEM", "size": size or SIZE[0], "page": page,
                             "f.dateIssued": f"[{date_range[0]} TO {date_range[1]}],equals", "sort": "dc.date.accessioned,ASC"})


def get(u):
    for attempt in range(8):
        r = tcap.fetch(S, u)
        if r.get("status") == 200:
            return r
        if r.get("error") in ("robots-disallowed", "off-limits-host", "host-challenged-skip", "bot-challenge"):
            print(json.dumps({"url": u, "error": r.get("error")}), flush=True)
            return None
        if r.get("http_status") in (400, 413, 422) and SIZE[0] != SIZES[-1]:  # page size refused: step down
            SIZE[0] = SIZES[SIZES.index(SIZE[0]) + 1]
            print(json.dumps({"url": u, "status": r.get("http_status"), "page_size_now": SIZE[0]}), flush=True)
            return "resize"
        ra = r.get("retry_after")
        try:
            wait = float(ra) + 5 if ra else (905.0 if r.get("http_status") == 429 else 300.0)
        except ValueError:
            wait = 905.0
        print(json.dumps({"url": u, "status": r.get("http_status") or r.get("status"), "error": (r.get("error") or "")[:200], "wait": wait}), flush=True)
        time.sleep(wait)
    return None


def run(q, date_range, label):
    page, total = 0, None
    while True:
        u = url_for(q, page, date_range)
        r = get(u)
        while r == "resize":
            page = 0
            u = url_for(q, page, date_range)
            r = get(u)
        if not r:
            print(json.dumps({"label": label, "page": page, "FAILED": True}), flush=True)
            return
        try:
            d = json.loads(r["content"])
            pg = d["_embedded"]["searchResult"]["page"]
        except Exception as e:
            print(json.dumps({"label": label, "page": page, "parse_error": repr(e)[:200]}), flush=True)
            return
        total = pg.get("totalPages") or 0
        n = len(d["_embedded"]["searchResult"]["_embedded"].get("objects") or [])
        print(json.dumps({"label": label, "page": page, "of": total, "items": n, "total": pg.get("totalElements"),
                          "cached": r.get("cached"), "sha256": r.get("sha256")}), flush=True)
        page += 1
        if page >= total:
            return


def pi_terms(only=None):
    """One Solr clause per PI: (last-name tokens AND (given name OR its nicknames)), over the PI's name forms."""
    ix = names.PIIndex(S)
    if only:
        miss = set(only) - {p["pi"] for p in ix.pis}
        if miss:
            raise SystemExit(f"not in pis.json: {sorted(miss)}")
    rev = {}
    for k, v in names.ph.NICK.items():
        rev.setdefault(v, set()).add(k)
    terms = []
    for p in ix.pis:
        if only and p["pi"] not in only:
            continue
        by_last = {}
        for n in [p["pi"]] + list(p.get("names") or []):
            t = [x for x in re.split(r"[^A-Za-z]+", names.fold(re.sub(r"\([^)]*\)", " ", n))) if x]
            if len(t) == 1:
                by_last.setdefault((t[0],), set())
                continue
            if len(t) < 2:
                continue
            first = next((x for x in t[:-1] if len(x) > 1), t[0])
            last = tuple(x for x in re.split(r"[^A-Za-z]+", names.fold(n.split()[-1])) if x)
            g = names.given(first)
            by_last.setdefault(last, set()).update({first, g} | rev.get(g, set()))
        cl = []
        for last, firsts in sorted(by_last.items()):
            if not firsts:
                cl.append("(" + " AND ".join(last) + ")")
            else:
                cl.append("(" + " AND ".join(last) + " AND (" + " OR ".join(sorted(firsts)) + "))")
        terms.append(" OR ".join(cl))
    return terms


if __name__ == "__main__":
    years = list(range(2016, 2027))
    only = sys.argv[1:]
    if not only or "eecs" in only:
        for y in years:
            run(EECS_Q, (y, y), f"eecs-{y}")
    if not only or "advisors" in only:
        terms = pi_terms()
        for i in range(0, len(terms), GROUP):
            q = "dc.contributor.advisor:(" + " OR ".join(terms[i:i + GROUP]) + ") AND NOT " + EECS_Q
            run(q, (2016, 2026), f"advisors-{i // GROUP}")
    if "review" in only:
        import sqlite3
        con = sqlite3.connect(f"file:{REVIEW}?mode=ro", uri=True, timeout=120)
        us = [u for (u,) in con.execute("SELECT DISTINCT url FROM captures WHERE url LIKE ? AND status=200 AND error IS NULL "
                                       "AND content IS NOT NULL ORDER BY id", (BASE + "%",))]
        con.close()
        for u in us:
            r = tcap.fetch(S, u)  # tcap.cached() copies the review's row; nothing is requested
            print(json.dumps({"label": "review", "url": u[-120:], "status": r.get("status"), "copied_from": r.get("copied_from"),
                              "cached": r.get("cached"), "sha256": r.get("sha256")}), flush=True)
    if only and only[0] == "pis":
        terms = pi_terms(only[1:])
        for i in range(0, len(terms), GROUP):
            q = "dc.contributor.advisor:(" + " OR ".join(terms[i:i + GROUP]) + ") AND NOT " + EECS_Q
            run(q, (2016, 2026), f"pis-{i // GROUP}")
    print("ALLDONE", flush=True)
