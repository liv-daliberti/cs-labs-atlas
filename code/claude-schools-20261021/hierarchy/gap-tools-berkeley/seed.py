"""Seed pass: for every gap PI fetch the EECS faculty profile and the EECS dissertations-by-faculty page
(live, else newest Wayback id_ capture), and extract the personal-homepage links and dissertation entries.

Resumable: fetches are cached in the capture DB. Writes gap-tools-berkeley/seed.json.
usage: seed.py
"""
import json
import re
import sys
from urllib.parse import urljoin

sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-berkeley")
import capstore  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

ROOT = "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021"
GAP = ROOT + "/hierarchy/berkeley/gap-input.json"
CENSUS = ROOT + "/census/berkeley-faculty.json"
OUT = ROOT + "/hierarchy/gap-tools-berkeley/seed.json"


def wb_latest(url):
    rows = capstore.wayback_cdx(url)
    if not rows:
        return None
    ts, orig = rows[-1]
    return f"https://web.archive.org/web/{ts}id_/{orig}"


def get(url):
    r = capstore.fetch(url)
    if r.get("status") != 200 or not r.get("content"):
        w = wb_latest(url)
        if w:
            r2 = capstore.fetch(w)
            if r2.get("status") == 200:
                return r2
    return r


def main_soup(content):
    soup = BeautifulSoup(capstore._decode(content), "lxml")
    return soup.find(id="site-main") or soup.find("main") or soup


def profile_links(r, base):
    out = []
    if r.get("status") != 200:
        return out
    m = main_soup(r["content"])
    for a in m.find_all("a", href=True):
        txt = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        href = urljoin(base, a["href"])
        if href.startswith("mailto:") or "/Faculty/Awards/" in href or "/Research/Areas/" in href or "/Photos/" in href:
            continue
        out.append({"href": href, "text": txt})
    return out


def dissertations(r):
    out = []
    if r.get("status") != 200:
        return out
    m = main_soup(r["content"])
    for p in m.find_all("p"):
        a = p.find("a")
        txt = re.sub(r"\s+", " ", p.get_text(" ")).strip()
        mm = re.search(r"^(.*?)\s*\[(\d{4})\]\s*$", txt)
        if not a or not mm:
            continue
        title = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        rest = mm.group(1)
        student = rest[len(title):].strip() if rest.startswith(title) else rest
        out.append({"title": title, "student": student, "year": int(mm.group(2)), "href": urljoin("https://www2.eecs.berkeley.edu/", a.get("href", ""))})
    return out


def main():
    gap = json.load(open(GAP))
    census = {c["name"]: c for c in json.load(open(CENSUS))}
    try:
        seed = json.load(open(OUT))
    except Exception:
        seed = {}
    for g in gap:
        pi = g["pi"]
        if pi in seed and seed[pi].get("done"):
            continue
        c = census.get(pi, {})
        prof = c.get("profile_url")
        slug = prof.rsplit("/", 1)[-1].replace(".html", "") if prof else None
        rec = {"pi": pi, "slug": slug, "profile_url": prof}
        if prof:
            rp = get(prof)
            rec["profile"] = {k: rp.get(k) for k in ("url", "capture_url", "status", "sha256")}
            rec["links"] = profile_links(rp, prof)
            du = f"https://www2.eecs.berkeley.edu/Pubs/Dissertations/Faculty/{slug}.html"
            rd = get(du)
            rec["diss_page"] = {k: rd.get(k) for k in ("url", "capture_url", "status", "sha256")}
            rec["dissertations"] = dissertations(rd)
        rec["done"] = True
        seed[pi] = rec
        with open(OUT, "w") as fh:
            json.dump(seed, fh, indent=1, ensure_ascii=False)
        print(pi, slug, rec.get("profile", {}).get("status"), rec.get("diss_page", {}).get("status"),
              len(rec.get("dissertations", [])), flush=True)


if __name__ == "__main__":
    main()
