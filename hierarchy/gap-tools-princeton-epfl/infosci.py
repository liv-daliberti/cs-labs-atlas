"""EPFL Infoscience (DSpace-CRIS REST) search: list items with type, year, authors, advisors, jury, unit.

usage: infosci.py "QUERY" [--size 100] [--max-pages 5] [--all]   (e.g. 'dc.contributor.advisor:"Filipovic, Damir"')
Every page is stored in hierarchy/epfl/gap-captures.sqlite.
"""
import argparse
import json
import os
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gapcap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("query")
ap.add_argument("--size", type=int, default=100)
ap.add_argument("--max-pages", type=int, default=5)
ap.add_argument("--all", action="store_true", help="print non-thesis items too")
ap.add_argument("--extra", default="", help="extra query string, e.g. configuration=researchoutputs")
a = ap.parse_args()


def v(md, k, n=6):
    return [x["value"] for x in md.get(k) or []][:n]


page = 0
while page < a.max_pages:
    q = {"query": a.query, "dsoType": "ITEM", "size": a.size, "page": page}
    url = "https://infoscience.epfl.ch/server/api/discover/search/objects?" + urlencode(q) + (("&" + a.extra) if a.extra else "")
    r = gapcap.fetch("epfl", url)
    try:
        j = json.loads(r["content"])
    except Exception:
        print("ERR", r.get("status"), r.get("error"), (r.get("content") or b"")[:200]); break
    sr = j["_embedded"]["searchResult"]
    pg = sr["page"]
    print(f"# page {page} of {pg['totalPages']} total {pg['totalElements']} sha {r['sha256'][:12]} url {url}")
    for o in sr["_embedded"]["objects"]:
        it = o["_embedded"]["indexableObject"]; md = it.get("metadata") or {}
        typ = (v(md, "dc.type", 1) or [""])[0]
        if not a.all and "thesis" not in typ:
            continue
        print(f"  {typ} | {v(md,'dc.date.issued',1)} | au={v(md,'dc.contributor.author',3)} | adv={v(md,'dc.contributor.advisor')} | "
              f"school={v(md,'epfl.thesis.doctoralSchool',1)} unit={v(md,'epfl.thesis.originalUnit',2)} | {it.get('name','')[:80]} | {it.get('handle')}")
    page += 1
    if page >= pg["totalPages"]:
        break
