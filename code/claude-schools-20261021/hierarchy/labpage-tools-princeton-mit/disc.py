"""Discovery crawl for the lab-page pass: for every lab in hierarchy/<school>/labpage-input.json, fetch the seed pages
(Princeton: the lab record's lab_pages + CS profile; MIT: lab_url + EECS/CSAIL profile guesses), follow profile
'website' links to the lab/personal site, and from each site page follow people/members/team and publications links
one or two hops (same site scope). JS-loaded directories: data files (.json/.yml/.csv) referenced from a page's
scripts on the same host are fetched too (robots.txt honoured by lpcap.fetch).

Writes tools/dossier_<school>.json: {pi: {seeds, pages:[{url, final_url, capture_url, status, sha256, kind, via,
title, chars, error}], people_links, pubs_links, site_links}}. Resumable: pages already stored are served from the
store (lpcap cache), and labs already in the dossier are skipped unless --redo.

Run with LPCAP_LOCAL set to a scratch SQLite (single writer: this process; threads share one insert lock), then merge
into hierarchy/<school>/labpage-captures.sqlite with merge.py.
usage: disc.py SCHOOL [--threads N] [--only PI ...] [--redo]
"""
import argparse
import json
import os
import re
import sys
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlsplit, urldefrag

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import lpcap  # noqa: E402

ROOT = lpcap.ROOT
LABREC = "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-labrecords-20261019/records/princeton"

EXTRA = {}
# one insert at a time inside this process
_ins_lock = threading.Lock()
_orig_insert = lpcap._insert


def _locked_insert(*a, **k):
    with _ins_lock:
        return _orig_insert(*a, **k)


lpcap._insert = _locked_insert
# thread-local sessions
_tl = threading.local()
_base_sess = lpcap._sess


class _SessProxy:
    def __getattr__(self, name):
        s = getattr(_tl, "s", None)
        if s is None:
            import requests
            s = requests.Session()
            s.headers.update(_base_sess.headers)
            _tl.s = s
        return getattr(s, name)


lpcap._sess = _SessProxy()

SOCIAL_RX = re.compile(r"(^|\.)(twitter\.com|x\.com|linkedin\.com|facebook\.com|instagram\.com|youtube\.com|youtu\.be|"
                       r"scholar\.google\.[a-z.]+|dblp\.org|dblp\.uni-trier\.de|orcid\.org|wikipedia\.org|bsky\.app|"
                       r"mastodon\.[a-z.]+|threads\.net|medium\.com|researchgate\.net|semanticscholar\.org|arxiv\.org|"
                       r"doi\.org|acm\.org|ieee\.org|springer\.com|github\.com|gitlab\.com|vimeo\.com|flickr\.com|"
                       r"google\.com|goo\.gl|bit\.ly|amazon\.com|tiktok\.com|apple\.com|microsoft\.com|nih\.gov|nsf\.gov|"
                       r"zoom\.us|calendly\.com|eventbrite\.com|openreview\.net|aclanthology\.org|neurips\.cc|icml\.cc|"
                       r"iclr\.cc|thecvf\.com|escholarship\.org)$", re.I)
PORTALS = {"mit.edu", "web.mit.edu", "www.mit.edu", "news.mit.edu", "computing.mit.edu", "engineering.mit.edu",
           "cap.csail.mit.edu", "eecseduportal.mit.edu", "mitcommlab.mit.edu", "accessibility.mit.edu", "whereis.mit.edu",
           "princeton.edu", "www.princeton.edu", "engineering.princeton.edu", "citp.princeton.edu",
           "csguide.cs.princeton.edu", "accessibility.princeton.edu", "cs.princeton.edu", "www.cs.princeton.edu",
           "www.eecs.mit.edu", "eecs.mit.edu", "www.csail.mit.edu", "csail.mit.edu"}


class _Social:
    @staticmethod
    def search(host):
        h = (host or "").lower()
        return bool(SOCIAL_RX.search(h)) or h in PORTALS


SOCIAL = _Social()
PROFILE_HOST = re.compile(r"^(www\.)?(eecs\.mit\.edu|csail\.mit\.edu|cs\.princeton\.edu)$", re.I)
PEOPLE_RX = re.compile(r"\b(people|members?|team|our team|the team|group|students|advisees|personnel|alumni|former|"
                       r"lab members|current members|who we are|our people|mentees|researchers|staff|crew|family)\b", re.I)
PEOPLE_HREF = re.compile(r"(people|member|team|group|student|advisee|alumni|personnel|former)", re.I)
NOT_PEOPLE = re.compile(r"\b(join|joining|opening|openings|position|positions|prospective|apply|hiring|contact|"
                        r"news|event|seminar|reading group|google group|mailing)\b", re.I)
PUBS_RX = re.compile(r"\b(publications?|papers?|pubs|bibliography|selected works|research outputs?)\b", re.I)
PUBS_HREF = re.compile(r"(publication|papers|pubs|bibliograph)", re.I)
SITE_RX = re.compile(r"\b(web ?site|home ?page|personal (page|site)|lab|laboratory|group|research group|here)\b", re.I)
DATA_RX = re.compile(r"""["'(]([^"'()\s<>]{1,200}\.(?:json|ya?ml|csv))(?:\?[^"'()\s<>]*)?["')]""", re.I)
META_REFRESH = re.compile(rb"""<meta[^>]+http-equiv=["']?refresh["']?[^>]*content=["']?\s*\d+\s*;\s*url=([^"'>]+)""", re.I)
LABLINK_RX = re.compile(r"^\s*(the |our |my )?(lab|group|research group|lab members|students|my students)\s*$", re.I)
BAD_EXT = re.compile(r"\.(pdf|ps|gz|zip|tar|tgz|pptx?|docx?|xlsx?|mp4|mov|png|jpe?g|gif|svg|bib|tex|mp3|ics)$", re.I)


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def slug(name):
    n = fold(name).replace(".", "")
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return n


def seeds_for(school, lab):
    out = []
    if school == "princeton":
        for d in sorted(os.listdir(LABREC)):
            p = f"{LABREC}/{d}/record.json"
            if not os.path.isfile(p):
                continue
            try:
                rec = json.load(open(p))
            except Exception:
                continue
            nm = rec.get("pi") if isinstance(rec.get("pi"), str) else (rec.get("pi") or {}).get("name")
            if nm == lab["pi"] or nm in lab.get("names", []):
                for x in rec.get("lab_pages") or []:
                    u = x.get("url")
                    if u and not BAD_EXT.search(urlsplit(lpcap.WAYBACK_RX.sub(r"\2", u)).path):
                        out.append(u)
                break
        pis = {p["pi"]: p for p in json.load(open(f"{ROOT}/princeton/pis.json"))}
        p = pis.get(lab["pi"]) or {}
        for per in p.get("periods") or []:
            for ev in per.get("evidence") or []:
                u = ev.get("url") or ""
                if re.search(r"cs\.princeton\.edu/people/profile/", u) and u not in out:
                    out.append(u)
    else:
        if lab.get("lab_url"):
            out.append(lab["lab_url"])
        for n in [lab["pi"]] + list(lab.get("names") or []):
            s = slug(n)
            if "EECS" in lab.get("departments", []):
                u = f"https://www.eecs.mit.edu/people/{s}/"
                if u not in out:
                    out.append(u)
            if "CSAIL" in lab.get("departments", []):
                u = f"https://www.csail.mit.edu/person/{s}"
                if u not in out:
                    out.append(u)
    # de-dup preserving order
    seen, res = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            res.append(u)
    return res


def title_of(content):
    m = re.search(rb"<title[^>]*>(.*?)</title>", content[:200000], re.I | re.S)
    return lpcap.collapse(lpcap.decode(m.group(1)))[:160] if m else ""


def scope_key(url):
    """Same-site scope: host plus the ~user (or /people/<x>/ for github-style) path prefix when present."""
    sp = urlsplit(url)
    m = re.match(r"^(/~[^/]+)", sp.path or "")
    return (sp.hostname or "").lower(), (m.group(1) if m else "")


def in_scope(url, key):
    h, pre = scope_key(url)
    if h != key[0] and h.replace("www.", "") != key[0].replace("www.", ""):
        return False
    return (not key[1]) or (urlsplit(url).path or "").startswith(key[1])


def name_hit(url, lab):
    toks = set()
    for n in [lab["pi"]] + list(lab.get("names") or []):
        toks |= {t for t in re.split(r"[^a-z]+", fold(n)) if len(t) >= 4}
    h = fold(url)
    return any(t in h for t in toks)


def crawl(school, lab, max_pages=18):
    pi = lab["pi"]
    pages, people_links, pubs_links, site_links = [], [], [], []
    done = set()

    def get(u, kind, via):
        u = urldefrag(u)[0]
        if u in done or len([p for p in pages if p.get("status") == 200]) >= max_pages:
            return None
        done.add(u)
        r = lpcap.fetch(school, u)
        if r.get("status") != 200 and not lpcap.WAYBACK_RX.match(u) and kind in ("people", "pubs", "site") \
                and r.get("error") not in ("off-limits-host",):
            pass
        c = r.get("content") or b""
        rec = {"url": r.get("url") or u, "final_url": r.get("final_url"), "capture_url": r.get("capture_url"),
               "status": r.get("status"), "sha256": r.get("sha256"), "kind": kind, "via": via,
               "title": title_of(c) if c else "", "error": r.get("error"),
               "chars": len(lpcap.page_text(c, r.get("content_type"))) if c and r.get("status") == 200 else 0}
        pages.append(rec)
        if r.get("status") == 200 and c and lpcap.kind_of(c, r.get("content_type")) == "html":
            m = META_REFRESH.search(c[:5000])
            if m:
                tgt = urljoin(r.get("final_url") or u, lpcap.decode(m.group(1)).strip().strip("'\""))
                if tgt.startswith("http") and urldefrag(tgt)[0] not in done:
                    r2 = get(tgt, kind, u)
                    if r2:
                        return r2
        return r if r.get("status") == 200 and c else None

    def is_html(r):
        return lpcap.kind_of(r["content"], r.get("content_type")) == "html"

    seeds = seeds_for(school, lab) + [u for u in EXTRA.get(pi, []) if u not in seeds_for(school, lab)]
    site_queue = []
    for s in seeds:
        r = get(s, "seed", None)
        if not r or not is_html(r):
            continue
        base = r.get("final_url") or s
        if lpcap.WAYBACK_RX.match(s):
            base = lpcap.WAYBACK_RX.match(s).group(2)
        host = urlsplit(base).hostname or ""
        if PROFILE_HOST.match(host) and not re.search(r"/~", base):
            for href, txt in lpcap.links(r["content"], base):
                hh = urlsplit(href).hostname or ""
                if not href.startswith("http") or BAD_EXT.search(urlsplit(href).path):
                    continue
                if PROFILE_HOST.match(hh):
                    if not re.search(r"/~", href):
                        continue
                elif SOCIAL.search(hh):
                    continue
                if SITE_RX.search(txt) or name_hit(href, lab) or re.search(r"/~", href):
                    if href not in site_links:
                        site_links.append(href)
                        site_queue.append((href, s))
        else:
            site_queue.insert(0, (s if not lpcap.WAYBACK_RX.match(s) else s, None))
    # site pages: home + people/pubs links
    visited_sites = set()
    qi = 0
    while qi < len(site_queue) and qi < 8:
        su, via = site_queue[qi]
        qi += 1
        if su in visited_sites:
            continue
        visited_sites.add(su)
        r = get(su, "site", via) if su not in done else lpcap.cached(school, su)
        if not r or not is_html(r):
            continue
        base = r.get("final_url") or su
        wb = lpcap.WAYBACK_RX.match(su)
        if wb:
            base = wb.group(2)
        key = scope_key(base)
        lks = lpcap.links(r["content"], base)
        for href, txt in lks:
            href = urldefrag(href)[0]
            if not href.startswith("http") or BAD_EXT.search(urlsplit(href).path):
                continue
            hh = urlsplit(href).hostname or ""
            if not in_scope(href, key) and SOCIAL.search(hh):
                continue
            if in_scope(href, key):
                tail = urlsplit(href).path.rsplit("/", 2)
                if (PEOPLE_RX.search(txt) or LABLINK_RX.match(txt) or PEOPLE_HREF.search("/".join(tail[-2:]))) \
                        and not NOT_PEOPLE.search(txt):
                    if href not in people_links:
                        people_links.append(href)
                elif PUBS_RX.search(txt) or PUBS_HREF.search("/".join(tail[-2:])):
                    if href not in pubs_links:
                        pubs_links.append(href)
            elif re.search(r"\b(lab|laboratory|group|team)\b", txt, re.I) and len(txt) < 80 and \
                    (hh.endswith(".edu") or hh.endswith(".io") or name_hit(href, lab)) and len(visited_sites) < 6:
                if href not in [x for x, _ in site_queue] and href not in site_links:
                    site_links.append(href)
                    site_queue.append((href, su))
        # JS data files on the same host
        raw = lpcap.decode(r["content"])
        if len(lpcap.page_text(r["content"], r.get("content_type"))) < 2500 or re.search(r"fetch\(|\$\.getJSON|axios", raw):
            for m in DATA_RX.finditer(raw):
                du = urljoin(base, m.group(1))
                if in_scope(du, key) and not re.search(r"manifest|package|tsconfig|composer|search-?index|sw\.js", du, re.I):
                    get(du, "data", su)
    for u in people_links[:6]:
        r = get(u, "people", "site")
        if r and is_html(r):
            raw = lpcap.decode(r["content"])
            base = r.get("final_url") or u
            key = scope_key(base)
            for href, txt in lpcap.links(r["content"], base):
                href = urldefrag(href)[0]
                if in_scope(href, key) and re.search(r"\b(alumni|former|past|previous)\b", txt + " " + href, re.I) \
                        and href not in people_links and not BAD_EXT.search(urlsplit(href).path):
                    people_links.append(href)
                    get(href, "people", u)
            if len(lpcap.page_text(r["content"], r.get("content_type"))) < 2500 or re.search(r"fetch\(|\$\.getJSON|axios", raw):
                for m in DATA_RX.finditer(raw):
                    du = urljoin(base, m.group(1))
                    if in_scope(du, key) and not re.search(r"manifest|package|tsconfig|composer|search-?index", du, re.I):
                        get(du, "data", u)
    for u in pubs_links[:3]:
        get(u, "pubs", "site")
    return {"seeds": seeds, "pages": pages, "people_links": people_links, "pubs_links": pubs_links,
            "site_links": site_links}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("school", choices=lpcap.SCHOOLS)
    ap.add_argument("--threads", type=int, default=10)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--extra", default=None, help="JSON {pi: [extra seed urls]}")
    a = ap.parse_args()
    if a.extra:
        EXTRA.update(json.load(open(a.extra)))
    labs = json.load(open(f"{ROOT}/{a.school}/labpage-input.json"))
    out_path = f"{TOOLS}/dossier_{a.school}.json"
    dossier = json.load(open(out_path)) if os.path.exists(out_path) else {}
    todo = [l for l in labs if (a.only is None or l["pi"] in a.only) and (a.redo or l["pi"] not in dossier)]
    lock = threading.Lock()
    print(f"{a.school}: {len(todo)} labs to crawl", flush=True)
    with ThreadPoolExecutor(a.threads) as ex:
        futs = {ex.submit(crawl, a.school, l): l["pi"] for l in todo}
        for f in as_completed(futs):
            pi = futs[f]
            try:
                d = f.result()
            except Exception as e:
                d = {"error": repr(e)[:500]}
            with lock:
                dossier[pi] = d
                tmp = out_path + ".tmp"
                json.dump(dossier, open(tmp, "w"), indent=1, ensure_ascii=False)
                os.replace(tmp, out_path)
            n200 = len([p for p in d.get("pages", []) if p.get("status") == 200])
            print(f"{pi}: {n200} pages, people {len(d.get('people_links', []))}, pubs {len(d.get('pubs_links', []))}"
                  f"{' ERROR ' + d['error'] if 'error' in d else ''}", flush=True)


if __name__ == "__main__":
    main()
