"""Name folding, nickname variants and matching against a lab's students_held (lab-page pass, 2026-10-22).

match_held(page_name, held_names) -> (held_name, how) or (None, None)
  how: exact | reordered | subset | nickname | initial | middle | fuzzy
A page name matches a held name when its surname is among the held name's tokens (or the reverse) and its given name
is equal to, a nickname/formal variant of, or an initial of a held token. Tokens are folded (accents, case), hyphens
and apostrophes split ("Bösel-Schmid" -> bosel, schmid). Comma forms ("Last, First") are reordered first.
'fuzzy' (one edit in a surname of 6+ letters, same given name) is reported as a candidate only; callers decide.
"""
import csv
import os
import re
import unicodedata
from functools import lru_cache

NICK_DIR = "/n/fs/resemble/cs-atlas/work/hierarchy/nicknames"
PARTICLES = {"van", "von", "der", "den", "de", "del", "della", "di", "da", "dos", "das", "du", "la", "le", "el", "al",
             "bin", "ben", "ter", "ten", "zu", "y", "e"}
TITLES = {"dr", "prof", "professor", "mr", "ms", "mrs", "phd", "ph", "d", "msc", "bsc", "jr", "sr", "ii", "iii", "iv"}


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    for a, b in (("ł", "l"), ("Ł", "L"), ("ø", "o"), ("Ø", "O"), ("ß", "ss"), ("đ", "d"), ("Đ", "D"), ("æ", "ae"),
                 ("œ", "oe"), ("ı", "i")):
        s = s.replace(a, b)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def reorder(name):
    """'Last, First Middle' -> 'First Middle Last' (only when there is exactly one comma)."""
    n = re.sub(r"\s+", " ", name or "").strip()
    if n.count(",") == 1:
        last, first = [x.strip() for x in n.split(",")]
        if first and last and not re.search(r"\b(phd|ph\.d|md|jr|sr|ii|iii)\b", fold(first)):
            return f"{first} {last}"
    return n


def tokens(name):
    """Folded tokens, parentheses kept as tokens too ('Yan (Rocky) Duan' -> yan, rocky, duan)."""
    n = reorder(name)
    n = fold(n).replace("(", " ").replace(")", " ").replace('"', " ").replace("“", " ").replace("”", " ")
    toks = [t for t in re.split(r"[^a-z0-9]+", n) if t]
    return [t for t in toks if t not in TITLES]


@lru_cache(maxsize=1)
def _nick_table():
    groups = {}
    for fn in ("names.csv", "extras.csv"):
        p = os.path.join(NICK_DIR, fn)
        if not os.path.exists(p):
            continue
        with open(p, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                a, b = fold(row.get("name1", "")).strip(), fold(row.get("name2", "")).strip()
                if not a or not b:
                    continue
                groups.setdefault(a, set()).add(b)
                groups.setdefault(b, set()).add(a)
    return groups


def variants(given):
    """A given name's nickname/formal variants (one hop both ways, plus siblings sharing a formal name)."""
    g = fold(given)
    t = _nick_table()
    out = {g} | t.get(g, set())
    for v in list(t.get(g, set())):
        out |= t.get(v, set()) if len(t.get(v, set())) < 40 else set()
    return out


def _edit1(a, b):
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    if len(a) > len(b):
        a, b = b, a
    for i in range(len(b)):
        if b[:i] + b[i + 1:] == a:
            return True
    return False


def _split(name):
    t = tokens(name)
    if not t:
        return None, None, []
    core = [x for x in t if x not in PARTICLES] or t
    return core[0], core[-1], t


def _surname_ok(page_toks, page_last, held_toks):
    if page_last in held_toks:
        return True
    # compound surnames: "Da Cruz Baptista Dias" vs page "Duarte Dias"
    return False


def match_one(page_name, held_name):
    pf, pl, pt = _split(page_name)
    hf, hl, ht = _split(held_name)
    if not pt or not ht:
        return None
    sp, sh = set(pt), set(ht)
    if pt == ht:
        return "exact"
    if sp == sh:
        return "reordered"
    if len(pt) >= 2 and len(ht) >= 2 and (sp <= sh or sh <= sp):
        # every token of the shorter name occurs in the longer one (middle names, double surnames, reversed order)
        short = pt if len(sp) <= len(sh) else ht
        if len([x for x in short if len(x) > 1]) >= 2:
            return "subset"
    # surname present on both sides (any position, handles family-name-first held forms)
    surname_hit = [x for x in pt[1:] if len(x) > 1 and x in sh] or ([pt[0]] if pt[0] in sh and pt[-1] in sh else [])
    if not surname_hit and len(pt) >= 2 and pt[0] in sh and len(pt[0]) > 1:
        # page in family-name-first order ("Zeyu Shen" held, page "Shen Zeyu") is caught by 'reordered'; this covers
        # page "Shen Z." style
        surname_hit = [pt[0]]
    if not surname_hit:
        return None
    rest_p = [x for x in pt if x not in surname_hit]
    rest_h = [x for x in ht if x not in surname_hit]
    if not rest_p or not rest_h:
        return None
    for g in rest_p:
        for h in rest_h:
            if len(g) == 1 and h.startswith(g):
                return "initial"
            if len(h) == 1 and g.startswith(h):
                return "initial"
            if len(g) > 1 and len(h) > 1 and (h in variants(g) or g in variants(h)):
                return "nickname"
    # given name matches a held middle name ("Rocky Duan" vs "Yan (Rocky) Duan" is subset; "Peter Chen" vs
    # "Xi (Peter) Chen" too). Here: page "Matt" vs held "John Matthew Smith"
    return None


def fuzzy_one(page_name, held_name):
    pf, pl, pt = _split(page_name)
    hf, hl, ht = _split(held_name)
    if not pt or not ht or len(pt) < 2 or len(ht) < 2:
        return False
    if pf == hf and pl != hl and len(pl) >= 6 and len(hl) >= 6 and _edit1(pl, hl):
        return True
    if pl == hl and pf != hf and len(pf) >= 5 and len(hf) >= 5 and _edit1(pf, hf):
        return True
    return False


def match_held(page_name, held):
    """Best held match for page_name: (held_name, how) or (None, None). Ambiguous (2+ held names) -> (None, 'ambiguous')."""
    order = ["exact", "reordered", "subset", "nickname", "initial"]
    hits = {}
    for h in held:
        m = match_one(page_name, h)
        if m:
            hits.setdefault(m, []).append(h)
    for k in order:
        if k in hits:
            cands = hits[k]
            # several held strings can be aliases of one person ("Carlos Florensa", "Carlos Florensa Campo")
            if len(cands) > 1 and not all(match_one(a, b) or match_one(b, a)
                                          for i, a in enumerate(cands) for b in cands[i + 1:]):
                # 'Xue Bin (Jason) Peng' covers both held strings 'Xue Bin Peng' and 'Jason Peng'
                pt = set(tokens(page_name))
                if "(" in page_name and all(set(tokens(c)) <= pt for c in cands):
                    return cands[0], k
                return None, "ambiguous"
            return cands[0], k
    return None, None


def fuzzy_held(page_name, held):
    return [h for h in held if fuzzy_one(page_name, h)]


if __name__ == "__main__":
    tests = [("Liv d'Aliberti", ["Olivia d'Aliberti"]), ("Matt Smith", ["Matthew Smith"]), ("Ale Gomez", ["Alejandro Gomez"]),
             ("Shen Zeyu", ["Zeyu Shen"]), ("Rocky Duan", ["Yan (Rocky) Duan"]), ("Popescu, George", ["George Popescu"]),
             ("Alejandro Escontrela", ["Alejandro Escontrela Dieguez"]), ("Nicolaj Bösel-Schmid", ["Nicolaj Bösel-Schmid"]),
             ("Lucas Wälti", ["Lucas Cédric Wälti"]), ("J. Tobin", ["Josh Tobin", "Joshua Tobin"]),
             ("Peter Chen", ["Xi (Peter) Chen"]), ("Jason Peng", ["Xue Bin Peng"]), ("Blagovesta Kostova", ["Kostova Blagovesta Hristova"]),
             ("Gorica Tapandjieva", ["Tapandjieva Sekulovska Gorica"]), ("Bob Jones", ["Robert Jones"]), ("Kate Li", ["Katherine Li"])]
    for p, h in tests:
        print(p, "->", match_held(p, h))
