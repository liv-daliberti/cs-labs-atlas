"""Princeton thesis harvest: DataSpace OAI-PMH (robots.txt allows /oai; it disallows the search pages) ListRecords,
metadataPrefix=dim, following resumption tokens, into hierarchy/princeton/thesis-captures.sqlite (single writer).
Pages already stored by the few-students / gap investigations (same URL) are copied in unchanged, not refetched.

Sets: the Doctoral Dissertations community (all departments, 2011-2025), the Master's Theses community (2022-2024), and the
senior-thesis collections of the departments our PIs advise in (CS, ECE, ORFE, MAE, Math, Psychology, Neuroscience, SPIA,
Sociology, Architecture, Music, Molecular Biology, Economics, Physics, Independent Concentration).
usage: setsid nohup python -I harvest_princeton.py > logs/princeton.log 2>&1 &
"""
import json
import os
import re
import sys
import time
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402

S = "princeton"
OAI = "https://dataspace.princeton.edu/oai/request?"
SETS = {
    "com_88435_dsp01td96k251d": ("dissertations", "Princeton University Doctoral Dissertations, 2011-2025"),
    "com_88435_dsp01kh04ds925": ("masters", "Princeton University Master's Theses, 2022-2024"),
    "col_88435_dsp01mp48sc83w": ("senior", "Computer Science, 1987-2024"),
    "col_88435_dsp010z709067j": ("senior", "Computer Science, 2023"),
    "col_88435_dsp0100000007x": ("senior", "Electrical and Computer Engineering, 1932-2024"),
    "col_88435_dsp011r66j119j": ("senior", "Operations Research and Financial Engineering, 2000-2024"),
    "col_88435_dsp01t722h887x": ("senior", "Mechanical and Aerospace Engineering, 1924-2024"),
    "col_88435_dsp01z029p4795": ("senior", "Mathematics, 1934-2024"),
    "col_88435_dsp01cz30ps722": ("senior", "Psychology, 1930-2024"),
    "col_88435_dsp01r781wj66b": ("senior", "Neuroscience, 2017-2024"),
    "col_88435_dsp0179407x233": ("senior", "Princeton School of Public and International Affairs, 1929-2024"),
    "col_88435_dsp01w0892999g": ("senior", "Sociology, 1954-2024"),
    "col_88435_dsp01x346d4232": ("senior", "Architecture School, 1968-2024"),
    "col_88435_dsp019593tv19m": ("senior", "Music, 1948-2024"),
    "col_88435_dsp01dz010q11z": ("senior", "Molecular Biology, 1954-2024"),
    "col_88435_dsp013n203z151": ("senior", "Economics, 1927-2024"),
    "col_88435_dsp01ng451h55q": ("senior", "Physics, 1936-2024"),
    "col_88435_dsp012r36tx59n": ("senior", "Independent Concentration, 1972-2024"),
}


def get(u):
    for attempt in range(5):
        r = tcap.fetch(S, u, force=attempt > 0)
        if r.get("status") == 200 and r.get("content"):
            return r
        if r.get("error") in ("robots-disallowed", "off-limits-host", "host-challenged-skip", "bot-challenge"):
            return None
        wait = float(r.get("retry_after") or 0) + 5 if r.get("retry_after") else (60, 180, 600, 900, 900)[attempt]
        print(json.dumps({"url": u, "status": r.get("http_status") or r.get("status"), "error": (r.get("error") or "")[:200], "wait": wait}), flush=True)
        time.sleep(wait)
    return None


def pages(params):
    url = OAI + urlencode(params)
    while url:
        r = get(url)
        if not r:
            print("FAIL", url, flush=True)
            return
        t = r["content"].decode("utf-8", "replace")
        yield url, r, t
        m = re.search(r"<resumptionToken[^>]*>([^<]+)</resumptionToken>", t)
        url = OAI + urlencode({"verb": params["verb"], "resumptionToken": m.group(1)}) if m else None


if __name__ == "__main__":
    for st, (kind, label) in SETS.items():
        n = p = 0
        for url, r, t in pages({"verb": "ListRecords", "metadataPrefix": "dim", "set": st}):
            p += 1
            n += len(re.findall(r"<record>", t))
        print(json.dumps({"set": st, "kind": kind, "label": label, "pages": p, "records": n}), flush=True)
    print("ALLDONE", flush=True)
