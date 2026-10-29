"""Automatic discovery of Stanford PIs' publication pages: fetch each PI's homepage seeds (live, lpcap; no Wayback here),
follow on-site links named publications/papers/pubs/bibliography, and score every stored page with lppubs.parse (auto):
entries, in-window entries, held. Output: one JSON row per PI with the pages tried and their scores.
usage: discover.py SEEDS.json OUT.json [--workers 8] [--only PI ...]"""
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit, urljoin

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stcap  # noqa: F401,E402  (registers the Stanford store)
import lpcap
import lppubs

S = "stanford"
BAD_SEED = re.compile(r"accessibility|visit\.stanford\.edu|stanford\.edu/search|/site/terms|/site/copyright|medcatalog|"
                      r"ted\.com|youtu|engineering\.stanford\.edu/(news|magazine)|semanticscholar|explorecourses|"
                      r"exploredegrees|news\.stanford|stanford\.edu/site/|apps\.apple|podcast|amazon\.|wikipedia|"
                      r"hai\.stanford\.edu/people|/(?:fellowship|phd)-program|youtube|vimeo|google\.com|nytimes|"
                      r"ed\.stanford\.edu/faculty|law\.stanford\.edu/directory|gsb\.stanford\.edu/faculty-research/faculty/|"
                      r"cs\.stanford\.edu/people-cs/|cs\.stanford\.edu/people/faculty|ee\.stanford\.edu/people/faculty|"
                      r"\.pdf$|doi\.org|arxiv\.org|mailto", re.I)
SEED_TEXT = re.compile(r"web ?site|web ?page|home ?page|\bsite\b|\blab\b|\bgroup\b|personal|\bpage\b|research|^https?://|"
                       r"laboratory|center|papers|publications|my |homepage|faculty page|project", re.I)
PUB_LINK = re.compile(r"publication|papers?\b|\bpubs?\b|bibliograph|selected work|research output|articles", re.I)
PUB_HREF = re.compile(r"publication|papers?(\.html?|/|$)|pubs?(\.html?|/|$)|bibliograph|biblio", re.I)
NOT_PUB = re.compile(r"scholar\.google|dblp|escholarship|semanticscholar|arxiv\.org|doi\.org|acm\.org|ieee|researchgate|"
                     r"\.pdf$|\.bib$|profiles\.stanford\.edu|github\.com/[^/]+/[^/]+|openreview|pubmed|ncbi|orcid|#", re.I)
lock = threading.Lock()
WB = "--wb" in sys.argv
# hosts on the Stanford CS network (171.64.x) that time out from this cluster on 2026-10-27: Wayback only
DEAD = {"cs.stanford.edu", "theory.stanford.edu", "graphics.stanford.edu", "www-graphics.stanford.edu", "robotics.stanford.edu",
        "ai.stanford.edu", "bejerano.stanford.edu", "crypto.stanford.edu", "hci.stanford.edu", "geometry.stanford.edu",
        "nlp.stanford.edu", "cvgl.stanford.edu", "smi-web.stanford.edu", "csb.stanford.edu", "www-isl.stanford.edu",
        "www-mrsrl.stanford.edu", "bdml.stanford.edu", "stat.stanford.edu", "snsg.stanford.edu", "platformlab.stanford.edu",
        "suif.stanford.edu", "infolab.stanford.edu", "snap.stanford.edu", "www.cs.stanford.edu", "vision.stanford.edu",
        "statweb.stanford.edu", "dawn.cs.stanford.edu", "hazyresearch.stanford.edu", "www-cs.stanford.edu",
        "theory.cs.stanford.edu", "web.cs.stanford.edu"}


def wb_newest(u):
    """Newest Wayback 200 capture (2016+) of u, fetched as an id_ URL; None when there is none."""
    rows = lpcap.wayback_cdx(S, u, frm="2016")  # no limit: a negative limit is applied before the status filter
    if not rows:
        alt = u[:-1] if u.endswith("/") else u + "/"
        rows = lpcap.wayback_cdx(S, alt, frm="2016")
    if not rows:
        return None
    ts, orig = rows[-1][0], rows[-1][1]
    r = lpcap.fetch(S, lpcap.wayback_id(ts, orig), check_robots=False)
    return r if r.get("status") == 200 else None


def site_key(u):
    h = (urlsplit(u).hostname or "").lower()
    return h


def same_site(a, b):
    ha, hb = site_key(a), site_key(b)
    if ha == hb:
        return True
    ra, rb = ".".join(ha.split(".")[-2:]), ".".join(hb.split(".")[-2:])
    return ra == rb and ra not in ("github.io", "google.com")


def score(pi, cap, url):
    try:
        es = lppubs.parse(S, {"pi": pi}, cap, url, mode="auto")
    except Exception as e:  # parser failure on odd markup
        return {"err": repr(e)[:200]}
    w = [e for e in es if e["in_window"]]
    return {"entries": len(es), "in_window": len(w), "held": sum(1 for e in w if e["held"]),
            "sample": [e["title"][:110] for e in w[:4]]}


def one(row):
    try:
        return _one(row)
    except Exception as e:
        print(json.dumps({"pi": row["pi"], "crash": repr(e)[:300]}), flush=True)
        return {"pi": row["pi"], "crash": repr(e)[:300], "pages": [], "best": None}


def _one(row):
    pi = row["pi"]
    seeds = []
    for k, u in row["seeds"]:
        if "profiles.stanford.edu" in u or BAD_SEED.search(u):
            continue
        if k.startswith("profile.link:") and not SEED_TEXT.search(k[13:]):
            continue
        seeds.append((k, u))
    seeds = seeds[:5]
    pages, tried = [], set()

    def visit(u, via):
        if u in tried or len(tried) >= 14:
            return None
        tried.add(u)
        h = (urlsplit(u).hostname or "").lower()
        r = {"status": None, "error": "dead-host-skip-live"} if h in DEAD else lpcap.fetch(S, u)
        if WB and r.get("status") != 200 and "robots" not in str(r.get("error")) and r.get("error") not in ("bot-challenge", "off-limits-host"):
            r2 = wb_newest(u)
            if r2 is not None:
                r = r2
        st = {"url": u, "via": via, "status": r.get("status"), "error": r.get("error"), "final": r.get("final_url"),
              "capture_url": r.get("capture_url")}
        if r.get("status") == 200 and r.get("content"):
            k = lpcap.kind_of(r["content"], r.get("content_type"))
            st["kind"] = k
            if k in ("html", "pdf", "text"):
                st.update(score(pi, r, u))
        pages.append(st)
        return r

    for k, u in seeds:
        r = visit(u, k)
        if r is not None and r.get("status") is None and u.startswith("http://") and "robots" not in str(r.get("error")):
            r = visit("https://" + u[7:], k + ":https")
        if not r or r.get("status") != 200 or not r.get("content"):
            continue
        if lpcap.kind_of(r["content"], r.get("content_type")) != "html":
            continue
        base = u if r.get("capture_url") else (r.get("final_url") or u)
        cand = []
        for h, t in lpcap.links(r["content"], base):
            h = h.split("#")[0]
            if not h.startswith("http") or NOT_PUB.search(h) or h.rstrip("/") == base.rstrip("/"):
                continue
            if not (PUB_LINK.search(t) and len(t) <= 60 or PUB_HREF.search(urlsplit(h).path)):
                continue
            if not same_site(h, base) and not PUB_LINK.search(t):
                continue
            if h not in cand:
                cand.append(h)
        for h in cand[:5]:
            visit(h, "link:" + base)
    best = None
    for p in pages:
        if p.get("in_window", 0) and (best is None or (p["in_window"], p.get("held", 0)) > (best["in_window"], best.get("held", 0))):
            best = p
    out = {"pi": pi, "seeds": seeds, "pages": pages, "best": best and best["url"]}
    with lock:
        print(json.dumps({"pi": pi, "best": out["best"], "n": best and best["in_window"], "held": best and best.get("held"),
                          "tried": len(pages)}, ensure_ascii=False), flush=True)
    return out


def main():
    a = sys.argv[1:]
    seeds = json.load(open(a[0]))
    out = a[1]
    workers = int(a[a.index("--workers") + 1]) if "--workers" in a else 8
    if "--only" in a:
        only = set(a[a.index("--only") + 1:])
        seeds = [r for r in seeds if r["pi"] in only]
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, seeds))
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
