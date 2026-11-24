"""DSpace@MIT discover searches by thesis supervisor (dc.contributor.advisor), 2016-2026, for the few-students MIT PIs.

Runs detached with FSCAP_LOCAL=<scratchpad sqlite> (merged into hierarchy/mit/few-students-captures.sqlite by merge.py).
fscap spaces dspace.mit.edu requests 100 s apart; on 429 we wait Retry-After (+5 s) or 905 s. Resumable: a query page
whose 200 response is already stored (locally, in the main store, or in the sister store) is not fetched again.
usage: setsid nohup env FSCAP_LOCAL=... python -I dspace_mit.py [QUERY ...] > log 2>&1 &
"""
import json
import os
import sys
import time
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fscap  # noqa: E402

BASE = "https://dspace.mit.edu/server/api/discover/search/objects?"
QUERIES = [
    "dc.contributor.advisor:(Terman OR Sipser OR Berners OR Goemans OR Sussman OR Cheng-Zhi OR (Huang AND Anna))",  # sister's
    "dc.contributor.advisor:(Jaillet)",
    "dc.contributor.advisor:(Corrigan OR Hopkins OR Huttenlocher OR Magnanti OR Micali OR Wainwright OR Bucinca OR Ghaffari)",
    "dc.contributor.advisor:(Zue OR Rosenholtz OR Peh OR Moshkovitz OR (Jack AND Dennis))",
]


def url_for(q, page=0):
    return BASE + urlencode({"query": q, "dsoType": "ITEM", "size": 100, "page": page,
                             "f.dateIssued": "[2016 TO 2026],equals", "sort": "dc.date.issued,ASC"})


def run(q, page=0):
    u = url_for(q, page)
    for attempt in range(4):
        r = fscap.fetch("mit", u)
        if r.get("status") == 200:
            return r
        ra = r.get("retry_after")
        try:
            wait = float(ra) + 5 if ra else (905.0 if r.get("http_status") == 429 else 180.0)
        except ValueError:
            wait = 905.0
        print(json.dumps({"query": q, "page": page, "status": r.get("http_status") or r.get("status"),
                          "error": r.get("error"), "wait": wait}), flush=True)
        if r.get("error") in ("robots-disallowed", "off-limits-host", "host-challenged-skip", "bot-challenge"):
            return None
        time.sleep(wait)
    return None


for q in ([a for a in sys.argv[1:] if a.strip()] or QUERIES):
    r = run(q)
    if not r:
        continue
    d = json.loads(r["content"])
    pg = d["_embedded"]["searchResult"]["page"]
    print(json.dumps({"query": q, "url": url_for(q), "sha256": r["sha256"], "cached": r.get("cached"), "page": pg}), flush=True)
    for p in range(1, pg.get("totalPages") or 1):
        r2 = run(q, p)
        if r2:
            print(json.dumps({"query": q, "page": p, "url": url_for(q, p), "sha256": r2["sha256"]}), flush=True)
print("DONE", flush=True)
