"""Berkeley EECS technical reports by faculty: fetch each PI's listing (Pubs/TechRpts/Faculty/<slug>.html), then every
2016+ report with at most MAXA authors, and record the BibTeX type (@mastersthesis/@phdthesis/...), the 'Advisor(s):'
line and the author list. Resumable (captures are cached). Writes a summary JSON to the scratchpad.
usage: FSCAP_LOCAL=<scratch sqlite> techrpts_berkeley.py OUT.json
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fscap  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

S = "berkeley"
MAXA = 4
SLUGS = "bachrach colella denero hfarid hearst nilah kubiatowicz listgarten obrien adityagp patterson jrk shewchuk tygar walrand borgs jchayes nika stellayu jswright aditik iychen cwfletcher emmapierson franklin".split()
out = {}
for slug in SLUGS:
    u = f"https://www2.eecs.berkeley.edu/Pubs/TechRpts/Faculty/{slug}.html"
    r = fscap.fetch(S, u)
    ents = []
    if r.get("status") == 200:
        soup = BeautifulSoup(fscap.decode(r["content"]), "lxml")
        main = soup.find(id="site-main") or soup
        for p in main.find_all("p"):
            a = p.find("a", href=True)
            if not a or "/Pubs/TechRpts/" not in a["href"]:
                continue
            m = re.search(r"EECS-(\d{4})-\d+", a["href"])
            if not m or int(m.group(1)) < 2016:
                continue
            txt = fscap.collapse(p.get_text(" "))
            authors = txt.split(")", 1)[-1].strip() if ")" in txt else ""
            auth = [x.strip() for x in re.split(r",| and ", authors) if x.strip()]
            ents.append({"href": "https://www2.eecs.berkeley.edu" + a["href"] if a["href"].startswith("/") else a["href"],
                         "title": fscap.collapse(a.get_text(" ")), "year": int(m.group(1)), "authors": auth})
    out[slug] = {"listing_status": r.get("status"), "entries": ents}
    print(slug, r.get("status"), len(ents), flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
for slug in SLUGS:
    for e in out[slug]["entries"]:
        if len(e["authors"]) > MAXA:
            continue
        r = fscap.fetch(S, e["href"])
        if r.get("status") != 200:
            e["status"] = r.get("status")
            continue
        t = fscap.page_text(r["content"])
        bt = re.search(r"@(\w+)\{", t)
        adv = re.search(r"Advisors?: (.*?) BibTeX", t)
        e.update(status=200, bibtype=bt.group(1) if bt else None, advisor=adv.group(1) if adv else None)
        print(slug, e["year"], e.get("bibtype"), "|", e["authors"][:3], "| adv:", e.get("advisor"), flush=True)
    json.dump(out, open(sys.argv[1], "w"), indent=1)
print("DONE", flush=True)
