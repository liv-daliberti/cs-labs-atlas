"""Princeton DataSpace OAI-PMH harvester (robots allows /oai; the JSPUI search is disallowed). Resumable: every page is
stored in hierarchy/princeton/gap-captures.sqlite and re-read from there; a rerun continues from the last stored token.

usage: oai.py sets                         list all setSpec/setName pairs (follows resumption tokens)
       oai.py harvest SET [SET ...]        ListRecords metadataPrefix=dim for each set
       oai.py find SURNAME [SET ...]       records whose contributor.advisor matches SURNAME (from stored pages)
"""
import os
import re
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gapcap  # noqa: E402

BASE = "https://dataspace.princeton.edu/oai/request?"
S = "princeton"


def pages(params):
    url = BASE + urlencode(params)
    while url:
        r = gapcap.fetch(S, url)
        if r.get("status") != 200:
            print("FAIL", url, r.get("status"), r.get("error"), flush=True)
            return
        t = r["content"].decode("utf-8", "replace")
        yield url, r, t
        m = re.search(r"<resumptionToken[^>]*>([^<]+)</resumptionToken>", t)
        url = BASE + urlencode({"verb": params["verb"], "resumptionToken": m.group(1)}) if m else None


def records(t):
    for rec in re.findall(r"<record>(.*?)</record>", t, flags=re.S):
        f = lambda el, q=None: [gapcap.collapse(re.sub(r"<[^>]+>", "", v)) for v in re.findall(
            r'<dim:field mdschema="dc" element="%s"%s[^>]*>(.*?)</dim:field>' % (el, (' qualifier="%s"' % q) if q else ""), rec, flags=re.S)]
        yield dict(id=(re.findall(r"<identifier>([^<]+)</identifier>", rec) or [""])[0], title=(f("title") or [""])[0],
                   author=f("contributor", "author"), advisor=f("contributor", "advisor"), issued=(f("date", "issued") or [""])[0],
                   uri=(f("identifier", "uri") or [""])[0], sets=re.findall(r"<setSpec>([^<]+)</setSpec>", rec))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sets":
        for url, r, t in pages({"verb": "ListSets"}):
            for s, n in re.findall(r"<setSpec>([^<]+)</setSpec><setName>([^<]+)</setName>", t):
                print(s, n)
    elif cmd == "harvest":
        for st in sys.argv[2:]:
            n = 0
            for url, r, t in pages({"verb": "ListRecords", "metadataPrefix": "dim", "set": st}):
                n += len(re.findall(r"<record>", t))
                print(st, n, r["sha256"][:12], flush=True)
            print("DONE", st, n, flush=True)
    elif cmd == "find":
        sur = sys.argv[2].lower()
        for st in sys.argv[3:]:
            for url, r, t in pages({"verb": "ListRecords", "metadataPrefix": "dim", "set": st}):
                for x in records(t):
                    if any(sur in a.lower() for a in x["advisor"]):
                        print(st, x["issued"][:10], x["author"], "| adv:", x["advisor"], "|", x["title"][:80], "|", x["uri"], "| page", url)
