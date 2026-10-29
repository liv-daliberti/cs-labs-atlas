"""Lab rows, slugs, seed URLs and stored-capture lookup for the lab-page pass."""
import gzip
import json
import os
import re
import sqlite3
import unicodedata
from functools import lru_cache

import lpcap
import lpnames

ROOT = lpcap.ROOT
TOOLS = os.path.dirname(os.path.abspath(__file__))
BASES = {"epfl": "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-epfl-20261019/people",
         "berkeley": "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-berkeley-20261021/people"}
CENSUS = "/n/fs/resemble/cs-atlas/work/census"


def slug(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


@lru_cache(maxsize=4)
def rows(school):
    return json.load(open(f"{ROOT}/{school}/labpage-input.json"))


def lab(school, key):
    rs = rows(school)
    if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
        return rs[int(key)]
    k = str(key)
    for r in rs:
        if slug(r["pi"]) == k:
            return r
    hits = [r for r in rs if lpnames.fold(k) in lpnames.fold(r["pi"])]
    if len(hits) == 1:
        return hits[0]
    raise KeyError(f"{key}: {len(hits)} matches")


def spec_path(school, row):
    return f"{TOOLS}/work/{school}/{slug(row['pi'])}.json"


@lru_cache(maxsize=4)
def census(school):
    d = json.load(open(f"{CENSUS}/{school}-faculty.json"))
    return d["faculty"] if isinstance(d, dict) else d


@lru_cache(maxsize=4)
def base_structure(school):
    return json.load(open(f"{BASES[school]}/structure.json"))


@lru_cache(maxsize=4)
def base_units(school):
    u = json.load(open(f"{BASES[school]}/units.json"))
    return u["units"] if isinstance(u, dict) else u


def _same(a, b):
    return lpnames.match_one(a, b) in ("exact", "reordered", "subset")


def seeds(school, row):
    out = []
    names = row.get("names") or [row["pi"]]
    if row.get("lab_url"):
        out.append(("input.lab_url", row["lab_url"]))
    for c in census(school):
        if any(_same(n, c.get("name", "")) for n in names):
            if c.get("profile_url"):
                out.append(("census.profile_url", c["profile_url"]))
            for k in ("homepage", "website", "lab_url"):
                if c.get(k):
                    out.append((f"census.{k}", c[k]))
    for p in base_structure(school).get("people", []):
        if "faculty" in " ".join(p.get("roles", [])) and any(_same(n, p["name"]) for n in names) and p.get("website"):
            out.append(("base.website", p["website"]))
    deps = {d.lower() for d in row.get("departments") or []}
    for u in base_units(school):
        leaders = list((u.get("leaders") or {}).keys())
        if any(_same(n, l) for n in names for l in leaders) or (u.get("acronym") or "").lower() in deps:
            for x in u.get("urls") or []:
                out.append((f"base.unit:{u.get('acronym') or u.get('name')}", x))
    seen, res = set(), []
    for k, u in out:
        if u and u not in seen:
            seen.add(u)
            res.append([k, u])
    return res


def stored(school, url):
    """Newest stored 200 capture for url (live url, final_url, or Wayback capture url), from the worker-local store,
    the main store, or a sister store (copied in)."""
    r = lpcap.cached(school, url)
    if r:
        return r
    for path in [lpcap.write_db(school), lpcap.DBS[school]]:
        if not os.path.exists(path):
            continue
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
        row = con.execute(f"SELECT {lpcap.COLS} FROM captures WHERE final_url=? AND capture_url IS NULL AND status=200 "
                          "AND content IS NOT NULL AND error IS NULL ORDER BY id DESC LIMIT 1", (url,)).fetchone()
        con.close()
        if row:
            return lpcap._row(row)
    return None


def spread(cdx_rows, n, lo=2016, hi=2026):
    """Up to n Wayback id_ URLs spread over the years lo..hi (earliest, latest, middle...)."""
    rs = [r for r in cdx_rows if lo <= int(r[0][:4]) <= hi]
    if not rs:
        return []
    by_year = {}
    for ts, orig, dig in rs:
        by_year.setdefault(ts[:4], (ts, orig))
    ys = sorted(by_year)
    if len(ys) <= n:
        pick = ys
    else:
        idx = sorted({round(i * (len(ys) - 1) / (n - 1)) for i in range(n)}) if n > 1 else [0]
        pick = [ys[i] for i in idx]
    return [lpcap.wayback_id(*by_year[y]) for y in pick]


@lru_cache(maxsize=4)
def lab_papers(school):
    by = {}
    with gzip.open(f"{ROOT}/{school}/lab_papers.jsonl.gz", "rt") as f:
        for l in f:
            d = json.loads(l)
            by.setdefault(d["pi"], []).append(d)
    return by
