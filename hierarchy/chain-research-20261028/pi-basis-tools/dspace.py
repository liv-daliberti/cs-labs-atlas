"""DSpace@MIT REST discover: theses 2016-2026 whose dc.contributor.advisor names a person. Prints PhD-ish hits."""
import json, re, sys, urllib.parse
from cap import fetch
def q(last, firsts, size=100):
    fq = " OR ".join(firsts)
    query = f"dc.contributor.advisor:({last} AND ({fq}))"
    u = ("https://dspace.mit.edu/server/api/discover/search/objects?" +
         urllib.parse.urlencode({"query": query, "dsoType": "ITEM", "size": size, "page": 0,
                                 "f.dateIssued": "[2016 TO 2026],equals", "sort": "dc.date.issued,ASC"}))
    return u
def hits(r):
    try: d = json.loads(r["raw_json"]) if "raw_json" in r else None
    except Exception: d = None
    return d
if __name__ == "__main__":
    last = sys.argv[1]; firsts = sys.argv[2].split(",")
    u = q(last, firsts)
    r = fetch(u, gap=10)
    print(r["status"], r["sha256"], r.get("error"), len(r["text"]))
    import sqlite3, zlib
    from cap import DB
    raw = zlib.decompress(sqlite3.connect(DB).execute("select raw from captures where sha256=? order by id desc limit 1", (r["sha256"],)).fetchone()[0])
    d = json.loads(raw)
    objs = d["_embedded"]["searchResult"]["_embedded"]["objects"]
    print("total", d["_embedded"]["searchResult"]["page"]["totalElements"])
    for o in objs:
        m = o["_embedded"]["indexableObject"]["metadata"]
        g = lambda k: [x["value"] for x in m.get(k, [])]
        print(g("dc.date.issued"), g("dc.contributor.author"), "| adv:", g("dc.contributor.advisor"), "| deg:", g("dc.description.degree"), "|", g("dc.contributor.department")[:2], "|", g("dc.identifier.uri"))
