"""OpenAlex helper (1 req/s; key from env, never printed or stored).

usage:
  oa.py authors "<name>"                 search authors, print id, name, works, last institutions, orcid
  oa.py works A123 [--from 2016] [--n 50]   list an author's works (year, title, institutions of that author)
  oa.py author A123                     one author record
  oa.py orcid 0000-...                  author by ORCID
  oa.py title "<title>" [--name X]      search works by title; show authorships matching name
"""
import argparse
import json
import sys

sys.path.insert(0, "/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-berkeley")
import capstore  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("cmd")
ap.add_argument("arg")
ap.add_argument("--from", dest="frm", type=int, default=2016)
ap.add_argument("--n", type=int, default=50)
ap.add_argument("--name", default=None)
ap.add_argument("--inst", default=None, help="filter author search by institution id (e.g. I95457486 = UC Berkeley)")
a = ap.parse_args()


def short_auth(au):
    insts = [i.get("display_name") for i in (au.get("last_known_institutions") or [])]
    return (f"{au['id'].rsplit('/',1)[-1]} | {au.get('display_name')} | works={au.get('works_count')} | "
            f"orcid={au.get('orcid')} | last={insts} | alt={au.get('display_name_alternatives', [])[:6]}")


if a.cmd == "authors":
    params = {"search": a.arg, "per-page": 25}
    if a.inst:
        params["filter"] = f"affiliations.institution.id:{a.inst}"
    row, j = capstore.openalex("authors", params)
    print("sha", row.get("sha256"), "status", row.get("status"))
    for au in (j or {}).get("results", []):
        print(short_auth(au))
elif a.cmd == "author":
    row, j = capstore.openalex("authors/" + a.arg)
    print("sha", row.get("sha256"))
    print(short_auth(j))
    aff = j.get("affiliations") or []
    for x in aff:
        print("  aff", x["institution"]["display_name"], x.get("years"))
elif a.cmd == "orcid":
    row, j = capstore.openalex("authors/orcid:" + a.arg)
    print("sha", row.get("sha256"), row.get("status"))
    if j and j.get("id"):
        print(short_auth(j))
elif a.cmd == "works":
    params = {"filter": f"author.id:{a.arg},from_publication_date:{a.frm}-01-01", "per-page": min(a.n, 200),
              "sort": "publication_year:desc", "select": "id,title,publication_year,authorships,doi"}
    row, j = capstore.openalex("works", params)
    print("sha", row.get("sha256"), "count", (j or {}).get("meta", {}).get("count"))
    for w in (j or {}).get("results", []):
        me = [x for x in w["authorships"] if (x["author"].get("id") or "").endswith(a.arg)]
        insts = [i.get("display_name") for x in me for i in x.get("institutions", [])]
        raw = [s for x in me for s in x.get("raw_affiliation_strings", [])]
        print(f"{w['publication_year']} | {w['id'].rsplit('/',1)[-1]} | {(w['title'] or '')[:110]} | inst={insts[:3]} | raw={[r[:60] for r in raw[:2]]} | raw_name={[x.get('raw_author_name') for x in me]}")
elif a.cmd == "title":
    params = {"filter": f"title.search:{a.arg}", "per-page": 10, "select": "id,title,publication_year,authorships,doi"}
    row, j = capstore.openalex("works", params)
    print("sha", row.get("sha256"))
    for w in (j or {}).get("results", []):
        print(f"{w['publication_year']} | {w['id'].rsplit('/',1)[-1]} | {(w['title'] or '')[:100]}")
        for x in w["authorships"]:
            nm = x["author"].get("display_name") or ""
            if a.name is None or any(p.lower() in nm.lower() for p in a.name.split("|")):
                print("     ", (x["author"].get("id") or "-").rsplit("/", 1)[-1], nm, [i.get("display_name") for i in x.get("institutions", [])][:2])
