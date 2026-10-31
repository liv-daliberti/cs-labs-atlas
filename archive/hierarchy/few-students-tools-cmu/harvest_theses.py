"""Harvest SCS thesis abstracts (2016-2026) from reports-archive.adm.cs.cmu.edu and index their thesis committees.

Resumable: every page goes through capstore.fetch (cached in few-students-captures.sqlite), so a re-run only fetches
what is missing. Writes theses_index.json next to this script: one row per thesis abstract page with
  series, report, url, sha256, author, title, degree, committee (raw text), chairs [names marked Chair/Co-Chair].

usage: harvest_theses.py [--no-fetch]   (--no-fetch: rebuild the index from cached pages only)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json
import re
import sys
from urllib.parse import urljoin

TOOLS = str(P.HIERARCHY / 'few-students-tools-cmu')
sys.path.insert(0, TOOLS)
import capstore  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

BASE = "http://reports-archive.adm.cs.cmu.edu/"
INDEXES = ([("cs", f"{BASE}cs{y}.html") for y in range(2016, 2027)]
           + [("ml", f"{BASE}ml{y}.html") for y in range(2016, 2021)]
           + [("isr", f"{BASE}isr{y}.html") for y in range(2016, 2023)]
           + [("hcii", f"{BASE}hcii2007.html")])
OUT = TOOLS + "/theses_index.json"
NOFETCH = "--no-fetch" in sys.argv


def entries(series, url):
    r = capstore.fetch(url) if not NOFETCH else (capstore.cached(url) or {})
    if r.get("status") != 200:
        return []
    soup = BeautifulSoup(capstore._decode(r["content"]), "lxml")
    out, buf = [], []
    # walk the document text in order; an entry ends at its "Abstract" link
    for el in soup.body.descendants if soup.body else []:
        if isinstance(el, str):
            buf.append(el)
        elif el.name == "a" and el.get("href") and "abstracts/" in el["href"] and re.search(r"\d\d-\d{3}\.html", el["href"]):
            href = urljoin(url, el["href"])
            text = re.sub(r"\s+", " ", "".join(buf)).strip()
            buf = []
            m = re.search(r"/(\d\d)-\d{3}\.html", href)
            if series == "hcii" and m and int(m.group(1)) < 16:
                continue
            out.append((href, text[-600:]))
    return out


def parse_abstract(series, href, entry_text):
    r = capstore.fetch(href) if not NOFETCH else (capstore.cached(href) or {})
    row = {"series": series, "url": href, "status": r.get("status"), "sha256": r.get("sha256"), "entry": entry_text[-300:]}
    if r.get("status") != 200:
        return row
    t = capstore.page_text(r["content"])
    m = re.search(r"(CMU-[A-Z]+-\d\d-\d{3})", t)
    row["report"] = m.group(1) if m else None
    dm = re.search(r"(Ph\.\s?D\.|M\.\s?S\.|Masters?|Master's)\s+Thesis", t)
    row["degree"] = dm.group(0) if dm else None
    if dm:
        # header: "<report> <title> <author> Ph.D. Thesis <Month Year>"
        head = t[:dm.start()]
        if row["report"]:
            k = head.rfind(row["report"])
            head = head[k + len(row["report"]):] if k >= 0 else head
        row["head"] = head.strip()[-400:]
    cm = re.search(r"Thesis Committee:?(.*?)(?:,\s*Head,|,\s*Dean,|Return to:|$)", t)
    if not cm:
        cm = re.search(r"(?:Committee|Advisor)s?:(.*?)(?:,\s*Head,|,\s*Dean,|Return to:|$)", t)
    row["committee"] = cm.group(1).strip()[:800] if cm else None
    chairs = []
    if row["committee"]:
        for x in re.finditer(r"([A-Z][^()]{2,60}?)\s*\((?:Co-?\s?)?(?:[Cc]hair|[Aa]dvisor|[Ss]upervisor)[^)]*\)", row["committee"]):
            chairs.append(x.group(1).strip())
        for x in re.finditer(r"([A-Z][A-Za-z.\- ']{2,50}?),\s*(?:Co-?)?(?:[Cc]hair|[Aa]dvisor)", row["committee"]):
            chairs.append(x.group(1).strip())
    row["chairs"] = chairs
    return row


def main():
    rows = []
    for series, url in INDEXES:
        ents = entries(series, url)
        theses = [(h, e) for h, e in ents if re.search(r"Thesis", e.split("CMU-")[-1] if "CMU-" in e else e)]
        print(series, url, "entries", len(ents), "theses", len(theses), flush=True)
        for h, e in theses:
            rows.append(parse_abstract(series, h, e))
        json.dump(rows, open(OUT, "w"), indent=0, ensure_ascii=False)
    json.dump(rows, open(OUT, "w"), indent=0, ensure_ascii=False)
    print("done", len(rows), "theses;", sum(1 for r in rows if r.get("chairs")), "with chairs", flush=True)


if __name__ == "__main__":
    main()
