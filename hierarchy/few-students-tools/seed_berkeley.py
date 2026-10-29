"""Berkeley few-students seed: fetch each PI's EECS profile and dissertations-by-faculty page; print dissertation
entries (2016+) and profile links. usage: seed_berkeley.py"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fscap, fsev  # noqa: E402
S = "berkeley"
SLUGS = dict(zip(["Jonathan Bachrach","Phillip Colella","John DeNero","Hany Farid","Marti Hearst","Nilah Ioannidis","John D. Kubiatowicz","Jennifer Listgarten","James O'Brien","Aditya Parameswaran","David A. Patterson","Jonathan Ragan-Kelley","Jonathan Shewchuk","Doug Tygar","Jean Walrand","Christian Borgs","Jennifer Chayes","Nika Haghtalab","Stella Yu","John Wright","Aditi Krishnapriyan","Irene Chen","Christopher Fletcher","Emma Pierson","Michael Franklin"],
 "bachrach colella denero hfarid hearst nilah kubiatowicz listgarten obrien adityagp patterson jrk shewchuk tygar walrand borgs jchayes nika stellayu jswright aditik iychen cwfletcher emmapierson franklin".split()))
out = {}
for pi, slug in SLUGS.items():
    prof = f"https://www2.eecs.berkeley.edu/Faculty/Homepages/{slug}.html"
    diss = f"https://www2.eecs.berkeley.edu/Pubs/Dissertations/Faculty/{slug}.html"
    rp = fscap.get(S, prof)
    rd = fscap.get(S, diss)
    links = []
    if rp.get("status") == 200:
        for h, t in fscap.links(rp["content"], prof):
            if any(x in h for x in ("eecs.berkeley.edu/Faculty/Awards", "/Research/Areas", "mailto:", "/Photos/")):
                continue
            if "www2.eecs.berkeley.edu" in h or "eecs.berkeley.edu/" in h and "people" not in h:
                if "Homepages" not in h and "Pubs" not in h:
                    continue
            links.append((h, t))
    dent = []
    if rd.get("status") == 200:
        t = fscap.page_text(rd["content"])
        dent = re.findall(r"([^\]]{5,200}?) \[(\d{4})\]", t[t.find("Ph.D. Dissertations - "):])
    out[pi] = {"slug": slug, "prof": {k: rp.get(k) for k in ("url", "capture_url", "status")},
               "diss": {k: rd.get(k) for k in ("url", "capture_url", "status")}, "links": links,
               "diss_recent": [(a[-90:], y) for a, y in dent if int(y) >= 2014]}
    print(pi, rp.get("status"), rd.get("status"), rd.get("capture_url"), "| recent diss:", [(a[-50:], y) for a, y in dent if int(y) >= 2014][:30], flush=True)
    print("   links:", [h for h, t in links][:25], flush=True)
json.dump(out, open("/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/bk/seed.json", "w"), indent=1)
