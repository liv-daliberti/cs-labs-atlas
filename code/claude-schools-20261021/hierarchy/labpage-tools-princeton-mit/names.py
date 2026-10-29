"""Name matching for the lab-page pass: is a member found on a lab page someone we already hold (students_held)?

Equivalences: case/diacritics/punctuation-insensitive; first names equal, or a nickname pair from
hierarchy/nicknames/names.csv + extras.csv (either direction), or a parenthesised alternative ("Weikun (William) Yang"),
or an initial ("J. Greenfield"); surnames equal ignoring hyphens/apostrophes/spaces, or one compound surname containing
the other ("Horta Ribeiro" / "Ribeiro"); "Last, First" is turned around; East-Asian order swaps are accepted; a
first-name-only listing ("liv") matches when exactly one held name has a compatible first name.
"""
import csv
import os
import re
import unicodedata

ROOT = "/n/fs/resemble/cs-atlas/work/hierarchy"
_pairs = None


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = s.replace("ł", "l").replace("Ł", "L").replace("ø", "o").replace("Ø", "O").replace("ß", "ss").replace("đ", "d")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def pairs():
    global _pairs
    if _pairs is None:
        _pairs = set()
        for f in ("names.csv", "extras.csv"):
            p = f"{ROOT}/nicknames/{f}"
            if not os.path.exists(p):
                continue
            for row in csv.DictReader(open(p, encoding="utf-8")):
                a, b = fold(row.get("name1", "")).strip(), fold(row.get("name2", "")).strip()
                if a and b:
                    _pairs.add((a, b))
                    _pairs.add((b, a))
    return _pairs


TITLES = re.compile(r"^(dr|prof|professor|mr|ms|mrs|sir|phd|jr|sr|ii|iii|iv)$")


def parse(name):
    """-> dict(first=[alternatives], last=str (compact), tokens=[...], alts=[parenthesised/quoted alternatives])"""
    n = name or ""
    alts = [fold(x).strip() for x in re.findall(r"[\(\"“]([^\)\"”]+)[\)\"”]", n)]
    n = re.sub(r"[\(\"“][^\)\"”]*[\)\"”]", " ", n)
    n = re.sub(r"\s+", " ", n).strip().strip(",")
    if "," in n:
        a, b = n.split(",", 1)
        if b.strip() and not re.search(r"\b(phd|ph\.d|jr|sr|md)\b", fold(b)):
            n = f"{b.strip()} {a.strip()}"
    toks = [t for t in re.split(r"[\s]+", fold(n)) if t]
    toks = [re.sub(r"[^a-z0-9'\-.]", "", t) for t in toks]
    toks = [t for t in toks if t and not TITLES.match(t.strip(".'-"))]
    return {"tokens": toks, "alts": [a for a in alts if a]}


def compact(s):
    return re.sub(r"[^a-z0-9]", "", fold(s))


def first_ok(a, b):
    a, b = compact(a), compact(b)
    if not a or not b:
        return False
    if a == b or (a, b) in pairs():
        return True
    if len(a) == 1 and b.startswith(a) or len(b) == 1 and a.startswith(b):
        return True
    return False


def surname_ok(at, bt):
    """at, bt: token lists (without the first name)."""
    if not at or not bt:
        return False
    a_last, b_last = compact(at[-1]), compact(bt[-1])
    if a_last and a_last == b_last:
        return True
    ca, cb = compact("".join(at)), compact("".join(bt))
    if ca == cb:
        return True
    # compound surname containing the other's last token (Horta Ribeiro / Ribeiro), min 4 chars
    for x, y in ((at, bt), (bt, at)):
        ys = compact(y[-1])
        if len(ys) >= 4 and any(compact(t) == ys for t in x):
            return True
        # last two tokens joined (de la Cruz / Delacruz)
        if len(x) >= 2 and compact("".join(x[-2:])) == ys:
            return True
    return False


def match_one(name, held):
    """Kind of match between a found name and one held name: 'exact' | 'variant' | None."""
    p, q = parse(name), parse(held)
    pt, qt = p["tokens"], q["tokens"]
    if not pt or not qt:
        return None
    if compact(" ".join(pt)) == compact(" ".join(qt)):
        return "exact"
    if len(pt) >= 2 and len(qt) >= 2:
        firsts_p = [pt[0]] + p["alts"]
        firsts_q = [qt[0]] + q["alts"]
        if surname_ok(pt[1:], qt[1:]) and any(first_ok(a, b) for a in firsts_p for b in firsts_q):
            return "variant"
        # middle name used as the given name ("S. Matthew Weinberg" style) or first two tokens hyphen-joined
        if surname_ok(pt[1:], qt[1:]) and (len(pt) >= 3 and first_ok(pt[1], qt[0]) or len(qt) >= 3 and first_ok(pt[0], qt[1])):
            return "variant"
        if compact("".join(pt[:2])) == compact(qt[0]) and len(pt) >= 3 and surname_ok(pt[2:], qt[1:]):
            return "variant"
        # swapped order (family name first)
        if len(pt) == 2 and len(qt) >= 2 and compact(pt[0]) == compact(qt[-1]) and first_ok(pt[1], qt[0]):
            return "variant"
    return None


def match(name, held_list):
    """-> (held_name, kind) or (None, None). kind: exact | variant | first-name-only."""
    best = None
    for h in held_list:
        k = match_one(name, h)
        if k == "exact":
            return h, "exact"
        if k == "variant" and best is None:
            best = (h, "variant")
    if best:
        return best
    pt = parse(name)["tokens"]
    if len(pt) == 1:
        cands = {h for h in held_list if parse(h)["tokens"] and
                 any(first_ok(pt[0], f) for f in [parse(h)["tokens"][0]] + parse(h)["alts"])}
        if len(cands) == 1:
            return cands.pop(), "first-name-only"
    return None, None


if __name__ == "__main__":
    tests = [("Liv G. d'Aliberti", ["Olivia d'Aliberti"]), ("liv", ["Olivia d'Aliberti", "Francesco Salvi"]),
             ("Ale Cuevas", ["Alejandro Cuevas"]), ("Matt Munoz", ["Matthew Muñoz"]), ("Weikun (William) Yang", ["Weikun Yang"]),
             ("Sixue (Cliff) Liu", ["Sixue Liu"]), ("Jerry Wei", ["Jerry Yu-Chieh Wei"]), ("Ribeiro, Manoel Horta", ["Manoel Horta Ribeiro"]),
             ("Mike He", ["Michael He"]), ("J. Greenfield", ["Jason Greenfield"]), ("Wei Jerry", ["Jerry Wei"]),
             ("Tim Alberdingk Thijm", ["Timothy Alberdingk Thijm"]), ("Marcelo Orenes Vera", ["Marcelo Orenes-Vera"]),
             ("John Smith", ["Jane Smith"])]
    for n, h in tests:
        print(f"{n!r:35} -> {match(n, h)}")
