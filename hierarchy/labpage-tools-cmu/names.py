"""Name normalisation + held-person matching with nicknames and spelling variants (CMU lab-page pass)."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as AP  # noqa: E402
import csv
import re
import unicodedata
from collections import defaultdict

NICK_DIR = str(AP.HIERARCHY / 'nicknames')
TITLES = {"dr", "prof", "professor", "mr", "ms", "mrs", "miss", "sir"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "ph d", "md", "mba", "ms", "msc", "bs", "ba", "pe"}

_nick = None


def _load_nicks():
    global _nick
    if _nick is not None:
        return _nick
    g = defaultdict(set)
    for fn in ("names.csv", "extras.csv"):
        try:
            with open(f"{NICK_DIR}/{fn}", newline="") as f:
                for row in csv.DictReader(f):
                    a, b = (row.get("name1") or "").strip().lower(), (row.get("name2") or "").strip().lower()
                    if a and b:
                        g[a].add(b)
                        g[b].add(a)
        except FileNotFoundError:
            pass
    _nick = g
    return g


def strip_accents(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.replace("ł", "l").replace("Ł", "L").replace("ø", "o").replace("Ø", "O").replace("ß", "ss").replace("đ", "d")


def parse(name):
    """-> dict(first, last, middles, alts, tokens, key)"""
    s = strip_accents(name).strip()
    alts = set()
    for m in re.finditer(r"[\(\"“‘']([^\)\"”’']{2,20})[\)\"”’']", s):
        for t in re.split(r"[\s,/]+", m.group(1).lower()):
            t = re.sub(r"[^a-z-]", "", t)
            if t:
                alts.add(t.replace("-", ""))
    s = re.sub(r"[\(\"“‘][^\)\"”’]*[\)\"”’]", " ", s)
    s = re.sub(r",\s*(jr|sr|ii|iii|iv|ph\.?\s?d\.?|m\.?d\.?)\.?\s*$", "", s, flags=re.I)
    if s.count(",") == 1:
        last, first = [x.strip() for x in s.split(",")]
        if first and last and first.lower().strip(". ") not in SUFFIXES:
            s = first + " " + last
    s = s.lower().replace(".", " ").replace("'", "").replace("’", "")
    toks = [t for t in re.split(r"[\s,]+", s) if t]
    toks = [re.sub(r"[^a-z-]", "", t) for t in toks]
    toks = [t for t in toks if t and t.strip("-")]
    while toks and toks[0] in TITLES:
        toks = toks[1:]
    while len(toks) > 1 and toks[-1] in SUFFIXES:
        toks = toks[:-1]
    if not toks:
        return {"first": "", "last": "", "middles": [], "alts": alts, "tokens": [], "key": ""}
    first, last = toks[0], toks[-1]
    return {"first": first.replace("-", ""), "first_raw": first, "last": last.replace("-", ""), "last_raw": last,
            "middles": [t.replace("-", "") for t in toks[1:-1]], "alts": alts,
            "tokens": [t.replace("-", "") for t in toks],
            "key": " ".join(t.replace("-", "") for t in toks)}


def firsts_equiv(a, b):
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) == 1 or len(b) == 1:
        return a[0] == b[0]
    g = _load_nicks()
    if b in g.get(a, ()) or a in g.get(b, ()):
        return True
    # share a canonical form (Bill / Will -> William)
    common = g.get(a, set()) & g.get(b, set())
    if any(len(c) > max(len(a), len(b)) for c in common):
        return True
    if len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True
    return False


def lasts_equiv(F, H):
    if F["last"] == H["last"]:
        return True
    fl = F["last"]
    hl = H["last"]
    # compound / double surnames: "Valencia Valenc", "Garcia-Lopez" vs "Garcia"
    ft, ht = F["tokens"], H["tokens"]
    if len(ht) >= 3 and fl in ht[-2:]:
        return True
    if len(ft) >= 3 and hl in ft[-2:]:
        return True
    if "-" in F.get("last_raw", "") and hl in F["last_raw"].split("-"):
        return True
    if "-" in H.get("last_raw", "") and fl in H["last_raw"].split("-"):
        return True
    if len(fl) >= 6 and len(hl) >= 6 and (fl.startswith(hl) or hl.startswith(fl)):
        return True
    return False


def match(found, held):
    """-> 'exact' | 'variant' | None"""
    F, H = parse(found), parse(held)
    if not F["key"] or not H["key"]:
        return None
    if F["key"] == H["key"]:
        return "exact"
    if "".join(F["tokens"]) == "".join(H["tokens"]):
        return "variant"
    if len(F["tokens"]) >= 2 and sorted(F["tokens"]) == sorted(H["tokens"]):
        return "variant"
    if lasts_equiv(F, H):
        fa = {F["first"]} | F["alts"]
        ha = {H["first"]} | H["alts"]
        if any(firsts_equiv(x, y) for x in fa for y in ha):
            return "variant"
        # middle name used as the given name ("J. Andrew Bagnell" / "Drew Bagnell")
        if any(firsts_equiv(x, y) for x in F["middles"] for y in ha) or \
                any(firsts_equiv(x, y) for x in fa for y in H["middles"]):
            return "variant"
    # family-name-first order
    if F["first"] == H["last"] and F["last"] == H["first"]:
        return "variant"
    return None


def find_held(found, held_list):
    """-> (kind, [held names]) best match over the held list."""
    hits = []
    kind = None
    for h in held_list:
        k = match(found, h)
        if k == "exact":
            if kind != "exact":
                hits = []
            kind = "exact"
            hits.append(h)
        elif k == "variant" and kind != "exact":
            kind = "variant"
            hits.append(h)
    return kind, hits


def same_person_key(name):
    P = parse(name)
    return (P["first"][:1] + " " + P["last"]) if P["key"] else ""
