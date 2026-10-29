import sys, json
from cap import fetch
from urllib.parse import quote
def authors(name, inst=None):
    u = "https://api.openalex.org/authors?search=" + quote(name) + "&per-page=25"
    if inst: u += "&filter=affiliations.institution.id:" + inst
    r = fetch(u); d = json.loads(r["text"]) if r["text"].startswith("{") else {"results": []}
    return u, r, d
if __name__ == "__main__":
    u, r, d = authors(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(u, r["sha256"])
    for a in d["results"]:
        aff = [(x["institution"]["display_name"], x["years"]) for x in a.get("affiliations", [])][:6]
        print(" ", a["id"].split("/")[-1], a["display_name"], a["works_count"], a.get("orcid"), aff)
