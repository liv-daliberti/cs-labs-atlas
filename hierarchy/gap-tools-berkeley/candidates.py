"""Scan the Berkeley OpenAlex sweep (read-only) for authorships whose name matches a gap PI and collect the
candidate OpenAlex author ids, observed ORCIDs, raw names and sample works. Writes candidates.json.

usage: candidates.py
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json
import re
import sqlite3
import unicodedata
import zlib
from collections import defaultdict

ROOT = str(P.HIERARCHY)
SWEEP = ROOT + "/berkeley/openalex-sweep.sqlite"
GAP = ROOT + "/berkeley/gap-input.json"
OUT = ROOT + "/gap-tools-berkeley/candidates.json"
BERKELEY = "https://openalex.org/I95457486"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z ]+", " ", s.lower().replace("-", " ")).split()


def key(name):
    t = norm(name)
    return (t[0], t[-1]) if t else None


gap = json.load(open(GAP))
keys = {}
for g in gap:
    for n in g["names"]:
        k = key(n)
        keys.setdefault(k, set()).add(g["pi"])
# common spelling variants
extra = {"Doug Tygar": [("j", "tygar"), ("doug", "tygar"), ("douglas", "tygar")],
         "Michael Franklin": [("michael", "franklin")],
         "Lotfi A. Zadeh": [("lotfi", "zadeh")],
         "Richard M. Karp": [("richard", "karp")],
         "Jason Lee": [("jason", "lee")]}
for pi, ks in extra.items():
    for k in ks:
        keys.setdefault(k, set()).add(pi)

cand = defaultdict(lambda: defaultdict(lambda: {"n": 0, "berkeley": 0, "names": set(), "orcids": set(),
                                                  "years": set(), "titles": []}))
con = sqlite3.connect(f"file:{SWEEP}?mode=ro", uri=True)
for (body,) in con.execute("SELECT body FROM pages"):
    try:
        works = json.loads(zlib.decompress(body))
    except Exception:
        works = json.loads(body)
    if isinstance(works, dict):
        works = works.get("results", [])
    for w in works:
        for au in w.get("authorships", []):
            nm = au.get("raw_author_name") or (au.get("author") or {}).get("display_name") or ""
            t = norm(nm)
            if not t:
                continue
            ks = {(t[0], t[-1]), (t[0][:1], t[-1])}
            dn = norm((au.get("author") or {}).get("display_name") or "")
            if dn:
                ks.add((dn[0], dn[-1]))
            hit = set()
            for k in ks:
                hit |= keys.get(k, set())
            # initial-only raw names, e.g. "J. D. Tygar"
            for pi in list(hit):
                pass
            if not hit:
                continue
            aid = ((au.get("author") or {}).get("id") or "-").rsplit("/", 1)[-1]
            inst = [i.get("id") for i in au.get("institutions", [])]
            lineage = [x for i in au.get("institutions", []) for x in (i.get("lineage") or [])]
            raw = " ".join(au.get("raw_affiliation_strings") or [])
            isb = BERKELEY in inst or BERKELEY in lineage or "berkeley" in raw.lower()
            for pi in hit:
                c = cand[pi][aid]
                c["n"] += 1
                c["berkeley"] += int(isb)
                c["names"].add(nm)
                if (au.get("author") or {}).get("orcid"):
                    c["orcids"].add(au["author"]["orcid"])
                c["years"].add(w.get("publication_year"))
                if len(c["titles"]) < 6:
                    c["titles"].append(f"{w.get('publication_year')} {w['id'].rsplit('/', 1)[-1]} {(w.get('title') or '')[:90]}")
out = {}
for pi, d in cand.items():
    out[pi] = sorted(({"id": k, "n": v["n"], "berkeley": v["berkeley"], "names": sorted(v["names"])[:5],
                       "orcids": sorted(v["orcids"]), "years": sorted(y for y in v["years"] if y),
                       "titles": v["titles"]} for k, v in d.items()), key=lambda x: -x["n"])
json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
for g in gap:
    rows = out.get(g["pi"], [])
    print(g["pi"], "->", [(r["id"], r["n"], r["berkeley"], r["orcids"][:1]) for r in rows[:6]])
