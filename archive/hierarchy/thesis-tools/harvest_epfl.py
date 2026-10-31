"""EPFL thesis harvest: Infoscience (DSpace-CRIS 7) REST discover search (robots.txt allows /server/api; it disallows the
/search UI), 100 items per page, into hierarchy/epfl/thesis-captures.sqlite (single writer).
  doctoral: query dc.type:"thesis::doctoral thesis", f.dateIssued=[Y TO Y] for Y in 2016..2026 (every doctoral school)
  masters:  query dc.type:"student work::master thesis", same years
Each record carries dc.contributor.advisor (thesis directors), epfl.thesis.jury and epfl.thesis.doctoralSchool.
Resumable (pages are cached). usage: setsid nohup python -I harvest_epfl.py > logs/epfl.log 2>&1 &
"""
import json
import os
import sys
import time
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402

S = "epfl"
BASE = "https://infoscience.epfl.ch/server/api/discover/search/objects?"
QUERIES = {"doctoral": 'dc.type:"thesis::doctoral thesis"', "masters": 'dc.type:"student work::master thesis"'}


def url_for(q, page, y):
    return BASE + urlencode({"query": q, "dsoType": "ITEM", "size": 100, "page": page,
                             "f.dateIssued": f"[{y} TO {y}],equals", "sort": "dc.date.accessioned,ASC"})


def get(u):
    for attempt in range(5):
        r = tcap.fetch(S, u, force=attempt > 0)
        if r.get("status") == 200 and r.get("content"):
            return r
        if r.get("error") in ("robots-disallowed", "off-limits-host", "host-challenged-skip", "bot-challenge"):
            return None
        wait = float(r.get("retry_after") or 0) + 5 if r.get("retry_after") else (60, 180, 600, 900, 900)[attempt]
        print(json.dumps({"url": u, "status": r.get("http_status") or r.get("status"), "error": (r.get("error") or "")[:200], "wait": wait}), flush=True)
        time.sleep(wait)
    return None


if __name__ == "__main__":
    for kind, q in QUERIES.items():
        for y in range(2016, 2027):
            page = 0
            while True:
                r = get(url_for(q, page, y))
                if not r:
                    print(json.dumps({"kind": kind, "year": y, "page": page, "FAILED": True}), flush=True)
                    break
                pg = json.loads(r["content"])["_embedded"]["searchResult"]["page"]
                print(json.dumps({"kind": kind, "year": y, "page": page, "of": pg.get("totalPages"), "total": pg.get("totalElements"),
                                  "cached": r.get("cached")}), flush=True)
                page += 1
                if page >= (pg.get("totalPages") or 0):
                    break
    print("ALLDONE", flush=True)
