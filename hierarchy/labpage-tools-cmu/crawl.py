"""Phase 1 pre-crawl for the CMU lab-page pass (resumable, detached).

For each lab in labpage-input.json: fetch lab_url (Wayback id_ when the input gives a capture), discover
people/members and publications links (and lab/group site links one hop out), fetch those, and list yearly
Wayback captures (CDX) for the seed and the people candidates. Writes $LABPAGE_DB (a local file) and
crawl-summary.jsonl (one line per lab; a lab already in the summary is skipped on restart).

usage: LABPAGE_DB=<local sqlite> python -I crawl.py [--threads N] [--only PI ...]
"""
import argparse
import json
import os
import re
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit, urldefrag

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstore  # noqa: E402

HIER = capstore.HIER
INPUT = HIER + "/cmu/labpage-input.json"
SUMMARY = capstore.STATE + "/crawl-summary.jsonl"

PEOPLE_RX = re.compile(r"\b(people|members?|team|students|personnel|who we are|folks|alumni|advisees|"
                       r"our group|the group|lab members|group members|current members|researchers|staff)\b", re.I)
PEOPLE_PATH_RX = re.compile(r"(people|member|team|student|personnel|alumni|folks|group\.html|/group/?$)", re.I)
PUBS_RX = re.compile(r"\b(publications?|papers|pubs|bibliography|selected papers|research output)\b", re.I)
PUBS_PATH_RX = re.compile(r"(publication|papers|pubs|bibliograph)", re.I)
LAB_RX = re.compile(r"\b(lab|laboratory|group|research group|research lab|center|centre)\b", re.I)
SKIP_HOST_RX = re.compile(r"(scholar\.google|dblp|twitter\.com|x\.com|linkedin|facebook|youtube|instagram|"
                          r"github\.com$|orcid\.org|researchgate|semanticscholar|arxiv\.org|doi\.org|acm\.org|"
                          r"ieee\.org|springer|amazon\.|wikipedia|medium\.com|bsky|mastodon|kilthub|figshare)", re.I)
SKIP_EXT_RX = re.compile(r"\.(pdf|ps|gz|zip|png|jpe?g|gif|mp4|mov|pptx?|docx?|bib|txt|tar|tgz)$", re.I)

lock = threading.Lock()
NO_CDX = False


def done_labs():
    s = set()
    if os.path.exists(SUMMARY):
        for line in open(SUMMARY):
            try:
                s.add(json.loads(line)["pi"])
            except Exception:
                pass
    return s


def links_of(row, base_url):
    out = []
    try:
        soup = capstore.soup_of(row["content"])
    except Exception:
        return out
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "javascript:", "tel:")):
            continue
        u = urldefrag(urljoin(base_url, href))[0]
        # links inside a Wayback id_ page are original URLs already; strip any wayback prefix
        orig, cap = capstore.split_wayback(u)
        if cap:
            u = orig
        if not u.startswith("http"):
            continue
        txt = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        out.append((u, txt))
    return out


def classify(links, seed):
    seed_host = capstore.host_of(seed)
    people, pubs, labs = [], [], []
    for u, t in links:
        h = capstore.host_of(u)
        if SKIP_HOST_RX.search(h) or SKIP_EXT_RX.search(urlsplit(u).path):
            continue
        path = urlsplit(u).path
        tl = t.lower()
        if len(t) <= 40 and PEOPLE_RX.search(t) or PEOPLE_PATH_RX.search(path) and len(t) <= 40:
            if not re.search(r"(faculty|directory|/people/faculty|/ri-faculty|news|events|apply|admission|join)", u + " " + tl, re.I) \
                    or h != seed_host:
                people.append((u, t))
        if len(t) <= 40 and PUBS_RX.search(t) or PUBS_PATH_RX.search(path) and len(t) <= 60:
            pubs.append((u, t))
        if len(t) <= 80 and LAB_RX.search(t) and (h != seed_host or path.rstrip("/") != urlsplit(seed).path.rstrip("/")):
            if not re.search(r"(cmu\.edu/?$|www\.cs\.cmu\.edu/?$|ri\.cmu\.edu/?$|ml\.cmu\.edu/?$|lti\.cmu\.edu/?$|"
                             r"hcii\.cmu\.edu/?$|csd\.cmu\.edu/?$)", u):
                labs.append((u, t))

    def dedup(xs, n):
        seen, out = set(), []
        for u, t in xs:
            k = u.rstrip("/")
            if k in seen or k == seed.rstrip("/"):
                continue
            seen.add(k)
            out.append((u, t))
        return out[:n]
    return dedup(people, 6), dedup(pubs, 4), dedup(labs, 4)


def meta_refresh(r, base):
    try:
        soup = capstore.soup_of(r["content"])
    except Exception:
        return None
    m = soup.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})
    if not m or not m.get("content"):
        return None
    mm = re.search(r"url\s*=\s*['\"]?([^'\";]+)", m["content"], re.I)
    if not mm:
        return None
    u = urljoin(base, mm.group(1).strip())
    o, cap = capstore.split_wayback(u)
    return o if u.startswith("http") else None


def fetch_page(url, wayback_ts=None):
    """Fetch url live; if it is part of a dead (Wayback-only) site, fetch it via Wayback at wayback_ts."""
    if wayback_ts:
        u = f"https://web.archive.org/web/{wayback_ts}id_/{url}"
        r = capstore.fetch(u)
    else:
        r = capstore.fetch(url)
    return r


def meta(r):
    return {k: r.get(k) for k in ("url", "final_url", "capture_url", "status", "sha256", "error")}


def ok_html(r):
    if r.get("status") != 200 or not r.get("content"):
        return False
    return not capstore.is_pdf(r["content"])


def do_lab(row):
    pi = row["pi"]
    rec = {"pi": pi, "lab_url": row.get("lab_url"), "seed": None, "people": [], "pubs": [], "labs": [], "cdx": {},
           "errors": []}
    seed = row.get("lab_url")
    if not seed:
        rec["note"] = "no lab_url"
        return rec
    orig, cap = capstore.split_wayback(seed)
    ts = None
    if cap:
        ts = capstore.WAYBACK_RX.match(seed).group(1)
    r = capstore.fetch(seed)
    if not cap and r.get("status") != 200:
        # dead live page: try the newest yearly Wayback capture
        rows = capstore.wayback_cdx(orig)
        rec["cdx"][orig] = [t for t, _ in rows]
        if rows:
            ts = rows[-1][0]
            r = capstore.fetch(f"https://web.archive.org/web/{ts}id_/{rows[-1][1]}")
    rec["seed"] = meta(r)
    if not ok_html(r):
        return rec
    base = orig
    # follow a meta refresh / tiny JS-free redirect page once
    mr = meta_refresh(r, orig)
    if mr:
        rec["meta_refresh"] = mr
        r2 = fetch_page(mr, ts)
        rec["seed_refresh"] = meta(r2)
        if ok_html(r2):
            r, base, orig = r2, mr, mr
    links = links_of(r, base)
    people, pubs, labs = classify(links, orig)
    rec["labs"] = [{"url": u, "text": t} for u, t in labs]
    # one hop out: lab/group sites
    for u, t in labs[:3]:
        rr = fetch_page(u, ts)
        rec["labs"][[x["url"] for x in rec["labs"]].index(u)]["fetch"] = meta(rr)
        if ok_html(rr):
            p2, b2, _ = classify(links_of(rr, u), u)
            people += p2
            pubs += b2
    seen = set()
    for kind, xs, n in (("people", people, 6), ("pubs", pubs, 5)):
        k = 0
        for u, t in xs:
            if u.rstrip("/") in seen:
                continue
            seen.add(u.rstrip("/"))
            if k >= n:
                break
            k += 1
            rr = fetch_page(u, ts)
            rec[kind].append({"url": u, "text": t, "fetch": meta(rr)})
    # yearly Wayback listings for the seed and the people candidates
    for u in ([] if NO_CDX else [orig] + [x["url"] for x in rec["people"][:3]]):
        if u in rec["cdx"]:
            continue
        try:
            rec["cdx"][u] = [t for t, _ in capstore.wayback_cdx(u)]
        except Exception as e:
            rec["errors"].append(f"cdx {u}: {e!r}"[:300])
    return rec


def run_one(row):
    try:
        rec = do_lab(row)
    except Exception as e:
        rec = {"pi": row["pi"], "fatal": repr(e)[:500], "tb": traceback.format_exc()[-1500:]}
    with lock:
        with open(SUMMARY, "a") as f:
            f.write(json.dumps(rec) + "\n")
    print(row["pi"], "done", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--batches", nargs="*", help="restrict to these batch ids (batches.json)")
    ap.add_argument("--no-cdx", action="store_true", help="skip yearly Wayback listings (Wayback is throttling)")
    a = ap.parse_args()
    global NO_CDX
    NO_CDX = a.no_cdx
    rows = json.load(open(INPUT))
    keep = set(a.only or [])
    if a.batches:
        B = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/batches.json"))
        keep |= {p for b in a.batches for p in B[b]}
    if keep:
        rows = [r for r in rows if r["pi"] in keep]
    done = done_labs()
    todo = [r for r in rows if r["pi"] not in done]
    print(len(todo), "labs to crawl", flush=True)
    with ThreadPoolExecutor(a.threads) as ex:
        list(ex.map(run_one, todo))
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
