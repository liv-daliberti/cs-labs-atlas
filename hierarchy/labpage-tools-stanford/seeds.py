"""Seed URLs per Stanford PI for the lab-page publication pass: the base sweep's homepage (people/persons.json), the
census rows' homepage/profile fields, and the 'Links' anchors (Lab Website, Personal Website, ...) of the PI's Stanford
Profiles page as stored by the base sweep (raw/captures.sqlite table live; read-only, no fetching here).
usage: seeds.py OUT.json"""
import html
import json
import re
import sqlite3
import sys
import zlib
from urllib.parse import urlsplit

R = "/n/fs/resemble/cs-atlas/work"
B = "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-stanford-20261027"
SKIP = re.compile(r"doi\.org|isiknowledge|ncbi\.nlm|pubmed|orcid\.org|cap\.stanford\.edu|profiles\.stanford\.edu|"
                  r"scholar\.google|dblp|escholarship|linkedin|twitter\.com|x\.com/|facebook|youtube|instagram|"
                  r"^https?://(www\.)?stanford\.edu/?$|med\.stanford\.edu/profiles|searchworks|purl\.stanford|"
                  r"stanfordhealthcare|maps\.google|github\.com/?$|mailto:", re.I)


def main(out):
    P = json.load(open(f"{R}/hierarchy/stanford/pis.json"))
    persons = json.load(open(f"{B}/people/persons.json"))
    pf = json.load(open(f"{B}/people/profile_fetch.json"))
    csr = json.load(open(f"{B}/people/cs_related_profiles.json"))
    cen = json.load(open(f"{R}/census/stanford-faculty.json"))["faculty"] + json.load(open(f"{R}/census/stanford-additions.json"))
    byname = {}
    for p in persons:
        for n in set((p.get("names") or []) + [p["name"]] + (p.get("aliases") or [])):
            byname.setdefault(n, []).append(("persons.homepage", p.get("homepage")))
    for c in cen:
        for n in set([c["name"]] + (c.get("aliases") or [])):
            for k in ("homepage", "website", "lab_url", "profile_url"):
                if c.get(k):
                    byname.setdefault(n, []).append(("census." + k, c[k]))
            for s in c.get("sources") or []:
                if s.get("kind") == "stanford_profiles":
                    byname.setdefault(n, []).append(("census.profile_url", s["url"]))
    for n, v in pf.items():
        if v.get("url"):
            byname.setdefault(n, []).append(("census.profile_url", v["url"]))
    for v in csr.values():
        for n in v.get("names") or []:
            if v.get("url"):
                byname.setdefault(n, []).append(("census.profile_url", v["url"]))
    b = sqlite3.connect(f"file:{B}/raw/captures.sqlite?mode=ro", uri=True)
    res = []
    for p in P:
        seeds = []
        for n in p["names"]:
            seeds += [x for x in byname.get(n, []) if x[1]]
        for k in ("url",):
            u = (p.get("lab") or {}).get(k)
            if u and "web.archive.org" not in u:
                seeds.append(("lab.url", u))
        profs = sorted({u for k, u in seeds if "profiles.stanford.edu" in u})
        links = []
        for pu in profs:
            row = b.execute("SELECT raw_zlib FROM live WHERE url=? AND status=200", (pu,)).fetchone()
            if not row:
                continue
            h = zlib.decompress(row[0]).decode("utf-8", "replace")
            for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', h, re.S):
                u = html.unescape(m.group(1)).strip()
                t = re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()
                if SKIP.search(u) or not t or len(t) > 80:
                    continue
                links.append(("profile.link:" + t, u))
        seeds += links
        seen, out_s = set(), []
        for k, u in seeds:
            if u not in seen:
                seen.add(u)
                out_s.append([k, u])
        res.append({"pi": p["pi"], "departments": p.get("departments"), "rank": p.get("rank"), "seeds": out_s})
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    print(len(res), sum(1 for r in res if any(not k.startswith("census.profile") for k, _ in r["seeds"])))


if __name__ == "__main__":
    main(sys.argv[1])
