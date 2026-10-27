"""First automatic pass for the lab-page pass: find each lab's site, people page(s) and publications page(s).

usage: discover.py SCHOOL SHARD NSHARDS     (resumable: labs already in the shard's output are skipped)
Writes discover/<school>-<shard>.jsonl, one line per lab: seeds, fetched pages (status, kind, stats), and ranked
people / publication page candidates. Set LPCAP_LOCAL_<SCHOOL> to a worker-local SQLite file.
Stats per fetched page: names (member-name candidates), held (candidates matching students_held), pubs (entries with
a 2016-2026 year), pubs_held (those matching a lab-paper title).
"""
import json
import os
import re
import sys
import traceback
from urllib.parse import urlsplit, urljoin

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import lpcap  # noqa: E402
import lpdom  # noqa: E402
import lplab  # noqa: E402
import lpnames  # noqa: E402
import lppubs  # noqa: E402

PEOPLE_TXT = re.compile(r"^\s*(our\s+)?(people|members?|lab members|group members|team|the team|our team|students|"
                        r"group|personnel|who we are|alumni|staff|researchers|current members|lab|the lab|"
                        r"advisees|current students|phd students|mentoring|students and postdocs)\s*$", re.I)
PEOPLE_HREF = re.compile(r"/(people|members?|team|group|students|alumni|staff|personnel|lab-?members|our-?team|"
                         r"group-?members|lab-?people|advisees|mentoring|current-?members)(/|\.s?html?|\.php|$|#|\?)", re.I)
PUBS_TXT = re.compile(r"^\s*(selected\s+|all\s+|recent\s+|full list of\s+)?(publications?|papers|pubs|bibliography|"
                      r"research papers|publication list)\s*$", re.I)
PUBS_HREF = re.compile(r"/(publications?|papers|pubs|bibliography|bib|research/publications)(/|\.s?html?|\.php|$|#|\?)",
                       re.I)
SHARED_HOSTS = {"www.epfl.ch", "people.eecs.berkeley.edu", "www.cs.berkeley.edu", "www.eecs.berkeley.edu",
                "www2.eecs.berkeley.edu", "sites.google.com", "inst.eecs.berkeley.edu", "people.epfl.ch",
                "www.stat.berkeley.edu", "people.ischool.berkeley.edu", "eecs.berkeley.edu", "github.com"}
SKIP_HOSTS = re.compile(r"(scholar\.google|dblp|twitter\.com|x\.com|linkedin|facebook|youtube|github\.com/[^/]+/?$|"
                        r"escholarship|search\.epfl\.ch|plan\.epfl\.ch|bair\.berkeley\.edu/?$)", re.I)


def same_site(home, link):
    a, b = urlsplit(home), urlsplit(link)
    if (a.hostname or "").replace("www.", "") != (b.hostname or "").replace("www.", ""):
        return False
    host = (a.hostname or "")
    if host in SHARED_HOSTS or host.endswith("github.io") and a.path.count("/") > 1:
        segs = [s for s in a.path.split("/") if s][:2 if host == "www.epfl.ch" else 1]
        pre = "/" + "/".join(segs)
        return b.path.startswith(pre) if segs else True
    return True


def fetch_any(school, url, wb=True):
    r = lpcap.fetch(school, url)
    if r.get("status") == 200 and r.get("content"):
        return r
    if wb and not lpcap.WAYBACK_RX.match(url) and not lpcap.blocked(url):
        w = lpcap.wayback_latest(school, url, frm="2016")
        if w:
            r2 = lpcap.fetch(school, w, check_robots=False)
            if r2.get("status") == 200:
                r2["live_status"] = r.get("status")
                r2["live_error"] = r.get("error")
                return r2
    return r


def page_stats(school, row, r, url):
    st = {}
    try:
        base = url if r.get("capture_url") else (r.get("final_url") or url)
        cands, _ = lpdom.member_candidates(r["content"], base)
        held = row.get("students_held") or []
        st["names"] = len(cands)
        st["held"] = sum(1 for c in cands if lpnames.match_held(c[1], held)[0])
    except Exception as e:
        st["names_err"] = repr(e)[:120]
    try:
        es = lppubs.parse(school, row, r, url)
        ins = [e for e in es if e["in_window"]]
        st["pubs"] = len(ins)
        st["pubs_held"] = sum(1 for e in ins if e["held"])
    except Exception as e:
        st["pubs_err"] = repr(e)[:120]
    return st


def links_of(r, url):
    base = url if r.get("capture_url") else (r.get("final_url") or url)
    if r.get("capture_url"):
        m = lpcap.WAYBACK_RX.match(r["capture_url"])
        base = m.group(2) if m else base
    try:
        out = []
        for fm in re.finditer(rb'<i?frame[^>]+src\s*=\s*["\']?([^"\' >]+)', r["content"][:200000], re.I):
            out.append((urljoin(base, lpcap.decode(fm.group(1))), "FRAME"))
        for bm in re.finditer(rb'(?:src|href|data-bib|bibfile|data-src)\s*=\s*["\']([^"\']+\.bib)["\']', r["content"], re.I):
            out.append((urljoin(base, lpcap.decode(bm.group(1))), "BIBFILE"))
        for h, t in lpcap.links(r["content"], base):
            m = lpcap.WAYBACK_RX.match(h)
            if m:
                h = m.group(2)
            out.append((h.split("#")[0], t))
        return out
    except Exception:
        return []


def discover(school, row):
    res = {"pi": row["pi"], "slug": lplab.slug(row["pi"]), "seeds": lplab.seeds(school, row), "pages": [],
           "homes": [], "people": [], "pubs": []}
    homes, profiles = [], []
    for kind, u in res["seeds"]:
        if "people.epfl.ch" in u or "/Faculty/Homepages/" in u:
            profiles.append(u)
        else:
            homes.append(u)
    guesses = set()
    if school == "epfl":
        for d in row.get("departments") or []:
            acro = re.sub(r"[^a-z0-9-]", "", d.lower())
            if acro:
                guesses |= {f"https://www.epfl.ch/labs/{acro}/", f"https://{acro}.epfl.ch/"}
                homes += [f"https://www.epfl.ch/labs/{acro}/", f"https://{acro}.epfl.ch/"]
    fetched = {}

    def get(u, kind):
        if u in fetched:
            return fetched[u]
        r = fetch_any(school, u, wb=u not in guesses)
        fetched[u] = r
        info = {"url": u, "kind": kind, "status": r.get("status"), "error": r.get("error"),
                "capture_url": r.get("capture_url"), "final_url": r.get("final_url")}
        if r.get("status") == 200 and r.get("content"):
            info.update(page_stats(school, row, r, u))
        res["pages"].append(info)
        return r

    for p in profiles:
        r = get(p, "profile")
        if r.get("status") != 200:
            continue
        for h, t in links_of(r, p):
            if SKIP_HOSTS.search(h) or not h.startswith("http"):
                continue
            if "/Faculty/Homepages/" in p and re.search(r"^\s*personal home ?page\s*$", t, re.I):
                homes.insert(0, h)
            if "people.epfl.ch" in p and (t.strip() == h or t.strip().rstrip("/") == h.rstrip("/")) and \
                    "people.epfl.ch" not in h and not re.search(r"(sin|ssc|sc|ic|edic|go)\.epfl\.ch/?$|go\.epfl\.ch", h):
                homes.insert(0, h)
    seen_h = []
    for h in homes:
        if h not in seen_h:
            seen_h.append(h)
    homes = seen_h[:6]
    people_c, pubs_c = [], []
    hi = 0
    while hi < len(homes):
        h = homes[hi]
        hi += 1
        r = get(h, "home")
        if r.get("status") != 200:
            continue
        res["homes"].append(h)
        hb = r.get("final_url") or h
        if r.get("capture_url"):
            hb = h
        for lk, t in links_of(r, h):
            if SKIP_HOSTS.search(lk) or not lk.startswith("http") or not same_site(hb, lk):
                continue
            if t == "FRAME" and lk not in homes and len(homes) < 10:
                homes.append(lk)
                continue
            sc_p = (2 if PEOPLE_TXT.match(t or "") else 0) + (1 if PEOPLE_HREF.search(lk) else 0)
            sc_b = (2 if PUBS_TXT.match(t or "") else 0) + (1 if PUBS_HREF.search(lk) else 0) + \
                (3 if t == "BIBFILE" else 0)
            if sc_p:
                people_c.append((sc_p, lk, t))
            if sc_b:
                pubs_c.append((sc_b, lk, t))
        if len(res["homes"]) >= 3:
            break

    def top(c, n):
        seen, out = set(), []
        for sc, lk, t in sorted(c, key=lambda x: -x[0]):
            k = lk.rstrip("/")
            if k in seen:
                continue
            seen.add(k)
            out.append((sc, lk, t))
        return out[:n]
    for sc, lk, t in top(people_c, 4):
        get(lk, "people?")
        res["people"].append({"url": lk, "text": t, "score": sc})
    for sc, lk, t in top(pubs_c, 3):
        r = get(lk, "pubs?")
        res["pubs"].append({"url": lk, "text": t, "score": sc})
        if r.get("status") == 200 and r.get("content") and not lk.endswith(".bib"):
            for b, t2 in links_of(r, lk):
                if t2 == "BIBFILE" and len(res["pubs"]) < 6 and same_site(lk, b):
                    get(b, "pubs?")
                    res["pubs"].append({"url": b, "text": "BIBFILE", "score": 3})
    return res


def main():
    school, shard, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    os.makedirs(f"{TOOLS}/discover", exist_ok=True)
    out = f"{TOOLS}/discover/{school}-{shard}.jsonl"
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try:
                done.add(json.loads(l)["pi"])
            except Exception:
                pass
    rows = lplab.rows(school)
    for i, row in enumerate(rows):
        if i % n != shard or row["pi"] in done:
            continue
        try:
            res = discover(school, row)
        except Exception as e:
            res = {"pi": row["pi"], "slug": lplab.slug(row["pi"]), "error": traceback.format_exc()[-800:]}
        res["index"] = i
        with open(out, "a") as f:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
        print(i, row["pi"], len(res.get("pages", [])), "pages", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
