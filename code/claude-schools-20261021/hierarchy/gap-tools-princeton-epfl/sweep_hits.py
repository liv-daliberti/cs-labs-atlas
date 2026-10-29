"""For each gap PI, list name-matching authorships in hierarchy/<school>/openalex-sweep.sqlite (read-only):
author id, year, school affiliation, raw name, title. Output: gap-tools-princeton-epfl/sweep_hits_<school>.json and a summary.
usage: sweep_hits.py SCHOOL [PI ...]
"""
import collections
import json
import re
import sqlite3
import sys
import zlib

TOOLS = "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/tools"
sys.path.insert(0, TOOLS)
from pi_hierarchy import Name, toks, INST, AFF  # noqa: E402

ROOT = "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy"
school = sys.argv[1]
only = set(sys.argv[2:])
gi = json.load(open(f"{ROOT}/{school}/gap-input.json"))
pis = [r for r in gi if not only or r["pi"] in only]
nm = {r["pi"]: Name(r["names"]) for r in pis}
by_sur = collections.defaultdict(list)
for r in pis:
    for f, l in nm[r["pi"]].forms:
        by_sur[l].append(r["pi"])
inst = "https://openalex.org/" + INST[school]
aff = re.compile(AFF[school], re.I)
hits = collections.defaultdict(list)
c = sqlite3.connect(f"file:{ROOT}/{school}/openalex-sweep.sqlite?mode=ro", uri=True)
for (body,) in c.execute("select body from pages order by year, page"):
    for w in json.loads(zlib.decompress(body)):
        for a in w.get("authorships") or []:
            raw = a.get("raw_author_name") or (a.get("author") or {}).get("display_name") or ""
            t = toks(raw)
            if len(t) < 2:
                continue
            for pi in set(by_sur.get(t[-1], []) + by_sur.get("".join(t[1:]), []) + by_sur.get(t[0], [])):
                if not nm[pi].match(raw):
                    continue
                via = [i.get("display_name") for i in a.get("institutions") or [] if inst == i.get("id") or inst in (i.get("lineage") or [])] \
                    + ["text" for z in a.get("raw_affiliation_strings") or [] if aff.search(z)]
                hits[pi].append(dict(w=w["id"].rsplit("/", 1)[-1], y=w.get("publication_year"), d=w.get("publication_date"),
                                     t=(w.get("title") or "")[:100], raw=raw, aid=((a.get("author") or {}).get("id") or "").rsplit("/", 1)[-1],
                                     orcid=(a.get("author") or {}).get("orcid"), school=bool(via),
                                     insts=[i.get("display_name") for i in a.get("institutions") or []][:3],
                                     rawaff=[z[:90] for z in (a.get("raw_affiliation_strings") or [])[:2]], doi=w.get("doi")))
json.dump(hits, open(f"{ROOT}/gap-tools-princeton-epfl/sweep_hits_{school}.json", "w"), indent=0)
for r in pis:
    h = hits.get(r["pi"], [])
    ids = collections.Counter((x["aid"], x["school"]) for x in h)
    print(f"== {r['pi']}  hits={len(h)} school={sum(x['school'] for x in h)}")
    for (aid, sch), n in ids.most_common(12):
        ys = sorted(x["y"] for x in h if x["aid"] == aid and x["school"] == sch)
        oc = {x["orcid"] for x in h if x["aid"] == aid} - {None}
        print(f"   {aid or '-'} school={sch} n={n} years={ys[0]}-{ys[-1]} orcid={oc} raw={collections.Counter(x['raw'] for x in h if x['aid']==aid).most_common(2)}")
