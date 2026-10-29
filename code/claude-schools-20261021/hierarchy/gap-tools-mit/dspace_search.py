"""DSpace@MIT discover searches by thesis supervisor (dc.contributor.advisor), 2016-2026, stored in gap-captures.sqlite.

DSpace@MIT tolerates about 10 requests per 15 minutes: one request per 120 s, Retry-After honoured on 429.
Resumable: a query whose 200 response is already stored is skipped. Run detached:
  setsid nohup python -I dspace_search.py > dspace_search.log 2>&1 &
"""
import json
import sys
import time
from urllib.parse import urlencode

sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-mit")
import capstore  # noqa: E402

capstore.GAP["dspace.mit.edu"] = 120.0
BASE = "https://dspace.mit.edu/server/api/discover/search/objects?"
QUERIES = [
    "dc.contributor.advisor:(Grimson OR Liskov OR Lampson OR Saltzer OR Willsky OR Seneff OR Leighton OR Adelson OR Kaiming OR Khattab OR Nigam OR Bobu OR Bucinca OR Corbato OR Jaffe OR Brewer)",
    "dc.contributor.advisor:((Anant AND Agarwal) OR (Albert AND Meyer) OR (Joel AND Moses) OR (Rodney AND Brooks) OR (Jas AND Brooks) OR (Mitchell AND Gordon))",
    "dc.contributor.advisor:(Ward AND (Stephen OR Steve))",
    "dc.contributor.advisor:(Long AND (William OR Bill))",
    "dc.contributor.advisor:(Arvind NOT Satyanarayan)",
]


def url_for(q, page=0):
    return BASE + urlencode({"query": q, "dsoType": "ITEM", "size": 100, "page": page,
                             "f.dateIssued": "[2016 TO 2026],equals", "sort": "dc.date.issued,ASC"})


def run(q, page=0):
    u = url_for(q, page)
    for attempt in range(4):
        r = capstore.fetch(u)
        if r.get("status") == 200:
            return r
        ra = r.get("retry_after")
        wait = 905.0
        try:
            wait = float(ra) + 5 if ra else (905.0 if r.get("status") == 429 else 180.0)
        except ValueError:
            pass
        print(json.dumps({"query": q, "page": page, "status": r.get("status"), "error": r.get("error"), "wait": wait}), flush=True)
        time.sleep(wait)
    return None


extra = [l.strip() for l in sys.argv[1:] if l.strip()]
for q in (extra or QUERIES):
    r = run(q)
    if not r:
        continue
    d = json.loads(r["content"])
    pg = d["_embedded"]["searchResult"]["page"]
    print(json.dumps({"query": q, "sha256": r["sha256"], "cached": r.get("cached"), "page": pg}), flush=True)
    for p in range(1, pg.get("totalPages") or 1):
        r2 = run(q, p)
        if r2:
            print(json.dumps({"query": q, "page": p, "sha256": r2["sha256"]}), flush=True)
print("DONE", flush=True)
