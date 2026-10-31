"""Infoscience (EPFL DSpace-CRIS REST) thesis search by advisor, stored in hierarchy/epfl/few-students-captures.sqlite.
usage: infosci_epfl.py QUERY [--page N] [--all]     e.g. 'dc.contributor.advisor:Shokrollahi'
Prints thesis items: type | year | author | advisors | handle. URL printed for use with fsev.infoscience_theses.
"""
import json
import os
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fscap  # noqa: E402


def url_for(query, page=0, size=100):
    return "https://infoscience.epfl.ch/server/api/discover/search/objects?" + urlencode(
        {"query": query, "dsoType": "ITEM", "size": size, "page": page})


def run(query, page=0, show_all=False):
    u = url_for(query, page)
    r = fscap.fetch("epfl", u)
    try:
        j = json.loads(r["content"])
    except Exception:
        print("ERR", r.get("status"), r.get("error"))
        return None
    sr = j["_embedded"]["searchResult"]
    pg = sr["page"]
    print(f"# {query} page {page}/{pg['totalPages']} total {pg['totalElements']} url {u}")
    for o in sr["_embedded"]["objects"]:
        it = o["_embedded"]["indexableObject"]
        md = it.get("metadata") or {}
        v = lambda k, n=6: [x["value"] for x in md.get(k) or []][:n]
        typ = (v("dc.type", 1) or [""])[0]
        if not show_all and "thesis" not in typ.lower():
            continue
        print(f"  {typ} | {v('dc.date.issued',1)} | au={v('dc.contributor.author',2)} | adv={v('dc.contributor.advisor')} | {it.get('handle')}")
    return pg


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    page = 0
    for a in sys.argv[1:]:
        if a.startswith("--page="):
            page = int(a.split("=")[1])
    for q in args:
        run(q, page, "--all" in sys.argv)
