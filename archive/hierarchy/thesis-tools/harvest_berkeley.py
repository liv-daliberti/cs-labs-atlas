"""Berkeley thesis harvest into hierarchy/berkeley/thesis-captures.sqlite (single writer; robots.txt allows /Pubs):
  1. EECS Ph.D. dissertations by year, https://www2.eecs.berkeley.edu/Pubs/Dissertations/Years/<Y>.html, 2016..2026:
     every entry is 'Title Student [advisor: A and B]';
  2. EECS technical reports by year, https://www2.eecs.berkeley.edu/Pubs/TechRpts/<Y>/, and every report page of those
     years: a thesis report carries 'Advisors: ...' and a BibTeX @phdthesis / @mastersthesis entry (first author =
     the thesis author).
Pages already stored by the few-students / gap investigations are copied in, not refetched. Resumable.
usage: setsid nohup python -I harvest_berkeley.py > logs/berkeley.log 2>&1 &
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

S = "berkeley"
YEARS = range(2016, 2027)


def get(u):
    for attempt in range(4):
        r = tcap.fetch(S, u, force=attempt > 0)
        if r.get("status") == 200 and r.get("content"):
            return r
        if r.get("http_status") == 404 or r.get("status") == 404 or r.get("error") in (
                "robots-disallowed", "off-limits-host", "host-challenged-skip", "bot-challenge"):
            return r
        wait = float(r.get("retry_after") or 0) + 5 if r.get("retry_after") else (30, 120, 600, 900)[attempt]
        print(json.dumps({"url": u, "status": r.get("http_status") or r.get("status"), "error": (r.get("error") or "")[:200], "wait": wait}), flush=True)
        time.sleep(wait)
    return r


def report_links(content):
    soup = BeautifulSoup(tcap.decode(content), "lxml")
    main = soup.find(id="site-main") or soup
    out = []
    for a in main.find_all("a", href=True):
        m = re.search(r"/Pubs/TechRpts/(\d{4})/(EECS-\d{4}-\d+)\.html", a["href"])
        if m:
            out.append(f"https://www2.eecs.berkeley.edu/Pubs/TechRpts/{m.group(1)}/{m.group(2)}.html")
    return list(dict.fromkeys(out))


if __name__ == "__main__":
    for y in YEARS:
        r = get(f"https://www2.eecs.berkeley.edu/Pubs/Dissertations/Years/{y}.html")
        print(json.dumps({"dissertations": y, "status": r.get("status"), "cached": r.get("cached")}), flush=True)
    reports = []
    for y in YEARS:
        r = get(f"https://www2.eecs.berkeley.edu/Pubs/TechRpts/{y}/")
        links = report_links(r["content"]) if r.get("status") == 200 else []
        print(json.dumps({"techrpts": y, "status": r.get("status"), "reports": len(links)}), flush=True)
        reports += links
    n = 0
    for u in reports:
        r = get(u)
        n += 1
        if n % 50 == 0:
            print(json.dumps({"report_pages": n, "of": len(reports), "last": u, "status": r.get("status")}), flush=True)
    print("ALLDONE", flush=True)
