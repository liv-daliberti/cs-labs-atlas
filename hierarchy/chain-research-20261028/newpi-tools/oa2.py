"""Author inspection helpers on top of oa.get (cached in captures.sqlite)."""
import sys, re
from oa import get
def author(aid):
    return get("authors/" + aid)
def search(name, n=25):
    return get("authors", **{"filter": f"display_name.search:{name}", "per-page": str(n), "select": "id,display_name,works_count,orcid,last_known_institutions,affiliations"}).get("results", [])
def works(aid, n=50, sort="publication_year:desc"):
    return get("works", **{"filter": f"author.id:{aid}", "per-page": str(n), "sort": sort, "select": "id,title,publication_year,authorships,doi"}).get("results", [])
def show(aid, n=12, sort="publication_year:desc"):
    a = author(aid)
    print(aid, a.get("display_name"), "orcid=", a.get("orcid"), "w=", a.get("works_count"), "alts=", (a.get("display_name_alternatives") or [])[:6])
    print("   aff:", [(x["institution"]["display_name"], min(x["years"]), max(x["years"])) for x in (a.get("affiliations") or []) if x.get("years")][:8])
    for w in works(aid, n, sort):
        me = [au for au in w["authorships"] if (au["author"].get("id") or "").endswith(aid)]
        insts = [i["display_name"] for au in me for i in au.get("institutions", [])][:2]
        co = [au["author"]["display_name"] for au in w["authorships"]][:5]
        print("   ", w["publication_year"], (w["title"] or "")[:90], "|", insts, "|", co)
if __name__ == "__main__":
    for x in sys.argv[1:]:
        if re.match(r'^A\d+$', x): show(x)
        else:
            for a in search(x):
                print(a["id"].split("/")[-1], a["display_name"], a["works_count"], a.get("orcid"), [i["display_name"] for i in a.get("last_known_institutions") or []][:2])
def yearinst(aid, pages=4):
    """per-year: n works, institution counts for this author across up to pages*200 works"""
    from collections import Counter, defaultdict
    out = defaultdict(Counter); n = Counter(); titles = []
    for p in range(1, pages+1):
        r = get("works", **{"filter": f"author.id:{aid}", "per-page": "200", "page": str(p), "select": "id,title,publication_year,authorships"}).get("results", [])
        for w in r:
            y = w["publication_year"]; n[y] += 1
            titles.append((y, w["title"], w["id"].split("/")[-1]))
            for au in w["authorships"]:
                if (au["author"].get("id") or "").endswith(aid):
                    for i in au.get("institutions", []): out[y][i["display_name"]] += 1
        if len(r) < 200: break
    return n, out, titles
