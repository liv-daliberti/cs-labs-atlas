"""CMU thesis harvest into hierarchy/cmu/thesis-captures.sqlite (single writer).
  A. SCS technical-report archive (reports-archive.adm.cs.cmu.edu): year indexes cs2016..cs2026, ml2016..ml2020,
     isr2016..isr2022, hcii2007 (HCII 2007-2026); the abstract page of every entry marked 'Thesis' (its 'Thesis
     Committee' names the Chair / Co-Chairs). ML after 2020, S3D after 2022, LTI, RI and CBD theses are not in this
     archive (their index pages 404 or end earlier) and come from KiltHub.
  B. KiltHub via the figshare API (KiltHub's web pages return a bot challenge; the API does not): POST
     /v2/articles/search {"group": 18614 (CMU theses), "item_type": 8, "published_since": "2016-01-01"} 1000 per page,
     then GET /v2/articles/<id> for every thesis (custom fields 'Advisor(s)', 'Thesis Department', 'Degree Type', 'Date').
Pages already stored by the few-students / gap investigations are copied in, not refetched. Resumable.
usage: setsid nohup python -I harvest_cmu.py [A] [B] > logs/cmu.log 2>&1 &
"""
import json
import os
import re
import sys
import time
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

S = "cmu"
BASE = "http://reports-archive.adm.cs.cmu.edu/"
INDEXES = ([("cs", f"{BASE}cs{y}.html") for y in range(2016, 2027)]
           + [("ml", f"{BASE}ml{y}.html") for y in range(2016, 2021)]
           + [("isr", f"{BASE}isr{y}.html") for y in range(2016, 2023)]
           + [("hcii", f"{BASE}hcii2007.html")])
FS = "https://api.figshare.com/v2/articles"


def get(u):
    for attempt in range(4):
        r = tcap.fetch(S, u, force=attempt > 0)
        if r.get("status") == 200 and r.get("content"):
            return r
        if r.get("http_status") in (404, 410) or r.get("status") in (404, 410) or r.get("error") in (
                "robots-disallowed", "off-limits-host", "host-challenged-skip", "bot-challenge"):
            return r
        wait = float(r.get("retry_after") or 0) + 5 if r.get("retry_after") else (30, 120, 600, 900)[attempt]
        print(json.dumps({"url": u, "status": r.get("http_status") or r.get("status"), "error": (r.get("error") or "")[:200], "wait": wait}), flush=True)
        time.sleep(wait)
    return r


def entries(series, url, content):
    """(abstract url, entry text) per report on an index page; an entry ends at its 'Abstract' link."""
    soup = BeautifulSoup(tcap.decode(content), "lxml")
    out, buf = [], []
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


def part_a():
    n = 0
    for series, url in INDEXES:
        r = get(url)
        if r.get("status") != 200:
            print(json.dumps({"index": url, "status": r.get("status")}), flush=True)
            continue
        ents = entries(series, url, r["content"])
        th = [(h, e) for h, e in ents if re.search(r"Thesis", e.split("CMU-")[-1] if "CMU-" in e else e)]
        for h, e in th:
            get(h)
            n += 1
        print(json.dumps({"index": url, "entries": len(ents), "theses": len(th), "abstract_pages_so_far": n}), flush=True)


def part_b():
    ids = []
    page = 1
    while True:
        r = None
        for attempt in range(4):
            r = tcap.post_json(S, FS + "/search", {"group": 18614, "item_type": 8, "published_since": "2016-01-01",
                                                   "page_size": 1000, "page": page}, force=attempt > 0)
            if r.get("status") == 200:
                break
            time.sleep((30, 120, 600, 900)[attempt])
        try:
            arts = json.loads(r["content"])
        except Exception:
            print(json.dumps({"search_page": page, "status": r.get("status"), "error": r.get("error")}), flush=True)
            break
        ids += [a["id"] for a in arts]
        print(json.dumps({"search_page": page, "items": len(arts), "total_ids": len(ids)}), flush=True)
        if len(arts) < 1000:
            break
        page += 1
    ids = list(dict.fromkeys(ids))
    for i, aid in enumerate(ids):
        r = get(f"{FS}/{aid}")
        if (i + 1) % 100 == 0:
            print(json.dumps({"articles": i + 1, "of": len(ids), "status": r.get("status"), "cached": r.get("cached")}), flush=True)


if __name__ == "__main__":
    parts = sys.argv[1:] or ["A", "B"]
    if "A" in parts:
        part_a()
    if "B" in parts:
        part_b()
    print("ALLDONE", flush=True)
