"""Interactive CLI over gapcap (all fetches stored in hierarchy/<school>/gap-captures.sqlite).

  f.py SCHOOL get URL [URL...] [--grep RX] [--chars N] [--force] [--norobots] [--links RX]
  f.py SCHOOL grep URL RX [--chars N]                 windows of a stored capture (url or capture_url)
  f.py SCHOOL wb URL [--from Y] [--to Y] [--require RX] [--max N] [--grep RX] [--prefix]
  f.py SCHOOL cdx URL [--from Y] [--to Y] [--prefix]  list Wayback captures
  f.py SCHOOL oa-authors NAME [--inst I...]          OpenAlex author search
  f.py SCHOOL oa-author A123                          one author (affiliations with years)
  f.py SCHOOL oa-orcid 0000-...                       author by ORCID
  f.py SCHOOL oa-works A123 [--from 2016] [--n 200] [--inst I]   works of an author (this author's institutions)
  f.py SCHOOL oa-name NAME [--inst I] [--from 2016]   works whose raw author name search matches, at institution
  f.py SCHOOL dblp-search NAME                        DBLP author search API
  f.py SCHOOL dblp-pid PID                            DBLP pid XML (summary)
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gapcap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("school")
ap.add_argument("cmd")
ap.add_argument("args", nargs="*")
ap.add_argument("--grep", default=None)
ap.add_argument("--chars", type=int, default=600)
ap.add_argument("--force", action="store_true")
ap.add_argument("--norobots", action="store_true")
ap.add_argument("--links", default=None)
ap.add_argument("--from", dest="frm", default=None)
ap.add_argument("--to", default=None)
ap.add_argument("--require", default=None)
ap.add_argument("--max", type=int, default=3)
ap.add_argument("--n", type=int, default=200)
ap.add_argument("--inst", default=None)
ap.add_argument("--prefix", action="store_true")
ap.add_argument("--head", type=int, default=1500)
a = ap.parse_args()
S = a.school


def show(res, grep=None, chars=600, head=1500, links=None):
    meta = {k: res.get(k) for k in ("url", "final_url", "capture_url", "status", "sha256", "error", "cached")}
    print(json.dumps(meta))
    c = res.get("content")
    if not c:
        return
    t = gapcap.page_text(c, res.get("content_type"))
    print("  len", len(t))
    if grep:
        n = 0
        for m in re.finditer(grep, t, flags=re.I):
            s = max(0, m.start() - chars // 2)
            print("  >>", t[s:m.end() + chars // 2])
            n += 1
            if n >= 25:
                print("  (more...)")
                break
        if n == 0:
            print("  (no match) head:", t[:300])
    else:
        print(t[:head])
    if links:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(gapcap._decode(c), "lxml")
        seen = set()
        for x in soup.find_all("a", href=True):
            h = x["href"]
            if re.search(links, h, re.I) and h not in seen:
                seen.add(h)
                print("  link:", h, "|", gapcap.collapse(x.get_text(" "))[:80])


if a.cmd == "get":
    for u in a.args:
        show(gapcap.fetch(S, u, force=a.force, check_robots=not a.norobots), a.grep, a.chars, a.head, a.links)
        print("=" * 70, flush=True)
elif a.cmd == "grep":
    r = gapcap.cached(S, a.args[0])
    if not r:
        print("NO CAPTURE"); sys.exit()
    show(r, a.args[1] if len(a.args) > 1 else a.grep, a.chars, a.head, a.links)
elif a.cmd in ("cdx", "wb"):
    rows = gapcap.wayback_cdx(S, a.args[0], frm=a.frm, to=a.to, match_prefix=a.prefix)
    print("captures:", len(rows))
    if a.cmd == "cdx":
        for r in rows:
            print(" ", r)
    else:
        tried = 0
        for ts, orig, dig in reversed(rows):
            if tried >= a.max:
                break
            tried += 1
            res = gapcap.fetch(S, gapcap.wayback_id(ts, orig), check_robots=False)
            if res.get("status") != 200:
                print("  fail", ts, res.get("status"), res.get("error")); continue
            t = gapcap.page_text(res["content"], res.get("content_type"))
            ok = a.require is None or re.search(a.require, t, re.I)
            print(("  OK  " if ok else "  skip"), res.get("capture_url"), res["sha256"][:12], len(t))
            if ok:
                show(res, a.grep, a.chars, a.head, a.links)
                break
elif a.cmd == "oa-authors":
    params = {"search": a.args[0], "per-page": 25}
    if a.inst:
        params["filter"] = f"affiliations.institution.id:{a.inst}"
    res, j = gapcap.openalex(S, "authors", params)
    print("sha", res.get("sha256"), res.get("status"))
    for au in (j or {}).get("results", []):
        insts = [i.get("display_name") for i in (au.get("last_known_institutions") or [])]
        affs = [(x["institution"]["display_name"], min(x.get("years") or [0]), max(x.get("years") or [0])) for x in au.get("affiliations") or []][:6]
        print(f"{au['id'].rsplit('/',1)[-1]} | {au.get('display_name')} | works={au.get('works_count')} | orcid={au.get('orcid')} | last={insts}")
        print("     affs:", affs)
elif a.cmd == "oa-author":
    res, j = gapcap.openalex(S, "authors/" + a.args[0])
    print("sha", res.get("sha256"), res.get("status"))
    if j:
        print(j.get("id"), j.get("display_name"), "works", j.get("works_count"), "orcid", j.get("orcid"))
        print("  alt:", (j.get("display_name_alternatives") or [])[:12])
        for x in j.get("affiliations") or []:
            print("  aff", x["institution"]["display_name"], x["institution"]["id"].rsplit("/", 1)[-1], sorted(x.get("years") or []))
elif a.cmd == "oa-orcid":
    res, j = gapcap.openalex(S, "authors/orcid:" + a.args[0])
    print("sha", res.get("sha256"), res.get("status"))
    if j:
        print(j.get("id"), j.get("display_name"), j.get("works_count"), j.get("orcid"))
elif a.cmd == "oa-works":
    aid = a.args[0]
    flt = f"author.id:{aid},from_publication_date:{a.frm or 2016}-01-01"
    if a.inst:
        flt += f",institutions.id:{a.inst}"
    params = {"filter": flt, "per-page": min(a.n, 200), "sort": "publication_year:desc",
              "select": "id,title,publication_year,publication_date,authorships,doi"}
    res, j = gapcap.openalex(S, "works", params)
    print("sha", res.get("sha256"), "count", (j or {}).get("meta", {}).get("count"))
    for w in (j or {}).get("results", []):
        me = [x for x in w["authorships"] if ((x.get("author") or {}).get("id") or "").endswith(aid)]
        insts = [i.get("display_name") for x in me for i in x.get("institutions", [])]
        raws = [z for x in me for z in x.get("raw_affiliation_strings") or []]
        rn = [x.get("raw_author_name") for x in me]
        print(f"  {w.get('publication_date')} {w['id'].rsplit('/',1)[-1]} | {(w.get('title') or '')[:110]} | {rn} | {insts[:3]} | {[r[:80] for r in raws[:2]]}")
elif a.cmd == "oa-name":
    flt = f"raw_author_name.search:{a.args[0]},from_publication_date:{a.frm or 2016}-01-01"
    if a.inst:
        flt += f",institutions.id:{a.inst}"
    params = {"filter": flt, "per-page": min(a.n, 200), "sort": "publication_year:desc",
              "select": "id,title,publication_year,authorships,doi"}
    res, j = gapcap.openalex(S, "works", params)
    print("sha", res.get("sha256"), res.get("status"), "count", (j or {}).get("meta", {}).get("count"))
    last = a.args[0].split()[-1].lower()
    for w in (j or {}).get("results", []):
        me = [x for x in w["authorships"] if last in (x.get("raw_author_name") or "").lower()]
        for x in me:
            print(f"  {w.get('publication_year')} {w['id'].rsplit('/',1)[-1]} | {(w.get('title') or '')[:90]} | {x.get('raw_author_name')} | "
                  f"{(x.get('author') or {}).get('id','').rsplit('/',1)[-1]} | {[i.get('display_name') for i in x.get('institutions', [])][:2]} | "
                  f"{[r[:70] for r in (x.get('raw_affiliation_strings') or [])[:1]]}")
elif a.cmd == "dblp-search":
    import urllib.parse
    u = "https://dblp.org/search/author/api?" + urllib.parse.urlencode({"q": a.args[0], "format": "json", "h": 30})
    res = gapcap.dblp(S, u)
    print("sha", res.get("sha256"), res.get("status"))
    try:
        j = json.loads(res["content"])
        for h in (j["result"]["hits"].get("hit") or []):
            info = h["info"]
            notes = info.get("notes", {}).get("note")
            print(" ", info.get("author"), "|", info.get("url"), "|", json.dumps(notes)[:300] if notes else "", "|", info.get("aliases"))
    except Exception as e:
        print("parse error", e, res.get("content", b"")[:300])
elif a.cmd == "dblp-pid":
    u = f"https://dblp.org/pid/{a.args[0]}.xml"
    res = gapcap.dblp(S, u)
    print("sha", res.get("sha256"), res.get("status"))
    c = res.get("content") or b""
    m = re.search(rb"<dblpperson[^>]*>", c)
    print(m.group(0).decode() if m else c[:300])
    for x in re.findall(rb"<person[^>]*>.*?</person>", c, flags=re.S)[:1]:
        print(gapcap.collapse(x.decode())[:1500])
    yrs = re.findall(rb"<year>(\d{4})</year>", c)
    print("pubs", len(yrs), "years", sorted(set(int(y) for y in yrs))[-12:])
else:
    print(__doc__)
