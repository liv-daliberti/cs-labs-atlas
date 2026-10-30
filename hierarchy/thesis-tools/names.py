"""Name matching for the thesis hunt: the hierarchy builder's own rules (tools/pi_hierarchy.py: toks, Name, NICK), plus
adviser-field cleanup. A thesis adviser matches a PI when Name(pi.names).match(adviser) holds and the adviser's given
name is a full name (not an initial) or the initial is unique among the school's PIs with that surname."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json
import re
import sys
import unicodedata

sys.path.insert(0, str(P.TOOLS))
import pi_hierarchy as ph  # noqa: E402  (main is guarded; only helpers are used)

ROOT = str(P.HIERARCHY)
toks, Name, given = ph.toks, ph.Name, ph.given

TITLES = re.compile(r"^(?:prof(?:essor)?\.?|dr\.?|mr\.?|ms\.?|mrs\.?|sir)\s+", re.I)


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = s.replace("ł", "l").replace("Ł", "L").replace("ø", "o").replace("Ø", "O").replace("ß", "ss").replace("đ", "d")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def clean_adviser(a):
    """'Daniel Jackson.' / 'Rus, Daniela L' / 'Prof. Bryan Ford' / 'Jackson, Daniel, 1963-' -> a plain name string."""
    a = re.sub(r"\s+", " ", a or "").strip()
    a = re.sub(r",?\s*\d{4}-(?:\d{4})?\.?$", "", a)          # MARC life dates
    a = re.sub(r"\s*\((?:co-?)?(?:chair|advis[eo]r|supervisor|director|codirector|co-director|thèse)[^)]*\)\s*$", "", a, flags=re.I)
    a = TITLES.sub("", a)
    a = re.sub(r",?\s+(?:Jr|Sr|II|III|IV)\.?(?=\s*(?:,|$))", "", a)  # 'James L. Kirtley, Jr.' / 'Smith, John, Jr.'
    a = a.strip().rstrip(".").strip()
    if a.count(",") >= 2:  # "Last, First, Jr." -> keep the first two parts
        p = [x.strip() for x in a.split(",")]
        a = p[0] + ", " + p[1]
    return a


def nat(n):
    """'Last, First' -> 'First Last' (parenthesised expansions dropped)."""
    n = re.sub(r"\s*\([^)]*\)", "", n or "").strip().rstrip(".")
    if n.count(",") == 1:
        a, b = n.split(",", 1)
        return f"{b.strip()} {a.strip()}".strip()
    return n


# Reviewed given-name aliases (thesis catalogues write the legal given name): surname near-misses checked by hand.
ALIASES = {
    "princeton": {"Jianqing Fan": ["Jian Qing Fan"]},
    "epfl": {"Katerina Argyraki": ["Aikaterini Argyraki"],
             # Infoscience writes 'Millán Ruiz, José del Rocío' / 'Millán-Ruiz, José del Rocio' (2026-10-27)
             "José del R. Millán": ["José del Rocío Millán Ruiz", "José del Rocio Millán Ruiz", "José del Rocío Millán-Ruiz",
                                    "José del Rocio Millán-Ruiz"]},
    "cmu": {"Bhiksha Raj": ["Bhiksha Ramakrishnan", "Bhiksha Raj Ramakrishnan"], "Eduard Hovy": ["Ed Hovy"]},
    "mit": {"Srini Devadas": ["Srinivas Devadas"]},
}


def lev(a, b):
    """Levenshtein distance."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


# Reviewed pairs of DIFFERENT people whose name forms the shared Name rules let match each other (the 'S' of a hyphenated
# initial 'H.-S.' passes as the initial of 'S. Simon'): never one duplicate group; when both match an adviser string, the
# one whose full given name is in the string wins (2026-10-27).
DISTINCT = {"stanford": [("S Simon Wong", "H.-S. Philip Wong")]}


class PIIndex:
    def __init__(self, school):
        self.school = school
        self.pis = json.load(open(f"{ROOT}/{school}/pis.json"))
        al = ALIASES.get(school, {})
        self.name = {p["pi"]: Name(list(dict.fromkeys([p["pi"]] + list(p.get("names") or []) + al.get(p["pi"], [])))) for p in self.pis}
        self.surnames = {}  # family name tokens as written in the PI's names (for alias review only)
        for p in self.pis:
            for n in [p["pi"]] + list(p.get("names") or []):
                t = toks(n)
                if len(t) >= 2:
                    self.surnames.setdefault(t[-1], set()).add(p["pi"])
                    self.surnames.setdefault("".join(t[1:]), set()).add(p["pi"])
        self.by_last = {}
        for p in self.pis:
            for f, l in self.name[p["pi"]].forms:
                self.by_last.setdefault(l, set()).add(p["pi"])
        # (given name, family name) as written, for the typo rule (no family-name-first or joined forms)
        self.natural = {}
        for p in self.pis:
            for n in [p["pi"]] + list(p.get("names") or []) + al.get(p["pi"], []):
                t = toks(n)
                if len(t) >= 2:
                    self.natural.setdefault(p["pi"], set()).add((given(t[0]), t[-1]))
                    if len(t[0]) == 1 and len(t) >= 3:
                        self.natural[p["pi"]].add((given(t[1]), t[-1]))
        # duplicate PI entries for one person (e.g. 'Dan Klein' and 'Daniel Klein'): canonical = the entry whose lab is
        # an existing single-leader unit, else the first; held checks look at every entry of the group
        self.dup = {}
        self.distinct = {frozenset(x) for x in DISTINCT.get(school, [])}
        names_of = {p["pi"]: [p["pi"]] + list(p.get("names") or []) for p in self.pis}
        unit = {p["pi"]: bool((p.get("lab") or {}).get("unitId")) for p in self.pis}
        for p in self.pis:
            grp = [q["pi"] for q in self.pis if q["pi"] == p["pi"] or (any(self.name[p["pi"]].match(n) for n in names_of[q["pi"]])
                                                                     and frozenset((p["pi"], q["pi"])) not in self.distinct)]
            if len(grp) > 1:
                canon = sorted(grp, key=lambda x: (not unit[x], [q["pi"] for q in self.pis].index(x)))[0]
                for g in grp:
                    self.dup[g] = (canon, tuple(grp))

    def canonical(self, pi):
        return self.dup.get(pi, (pi, (pi,)))[0]

    def group(self, pi):
        return list(self.dup.get(pi, (pi, (pi,)))[1])

    def match(self, adviser):
        return self.match_info(adviser)[0]

    def match_info(self, adviser):
        """(PIs whose name matches the adviser string, how). how: exact | ligature | second-given | fuzzy | ''."""
        if not hasattr(self, "_memo"):
            self._memo = {}
        if adviser not in self._memo:
            h, w = self._match_info(adviser)
            self._memo[adviser] = (list(h), w)
        h, w = self._memo[adviser]
        return list(h), w

    def _match_info(self, adviser):
        a = clean_adviser(adviser)
        t = toks(a)
        if len(t) == 1:  # a single-name person ("Arvind") matches only that single name
            return [pi for pi in sorted(self.name) if t[0] in self.name[pi].mono], "exact"
        if len(t) < 2:
            return [], ""
        cands = set()
        for l in {t[-1], "".join(t[1:]), "".join(t[-2:]), t[0]}:
            cands |= self.by_last.get(l, set())
        how = "exact"
        hits = [pi for pi in sorted(cands) if self.name[pi].match(a)]
        if not hits:  # PDF ligature loss in catalogued names: 'Jerey' for Jeffrey, 'Cliord' for Clifford
            how = "ligature"
            for pi in sorted(cands):
                if any(len(f) > 3 and re.sub(r"ffi|ffl|ff|fi|fl", "", f) == t[0] != f and l in (t[-1], "".join(t[1:]))
                       for f, l in self.name[pi].forms):
                    hits.append(pi)
        if not hits and len(t) == 3 and len(t[0]) > 1:  # 'Mohammad Amin Shokrollahi': known by the second given name
            how = "second-given"
            hits = [pi for pi in sorted(cands) if any((given(t[1]), t[-1]) == fl for fl in self.name[pi].forms)]
        if not hits and len(t[0]) > 2 and len(t[-1]) > 2:
            # typo in a catalogued name ('Vipual Goyal', 'Bernard Haeupler', 'Justin Sherry'): family name within 1 edit
            # and given name within 1 edit (2 when 6+ letters) of exactly one PI's name form
            how = "fuzzy"
            fz = set()
            for pi, forms in self.natural.items():
                for f, l in forms:
                    if len(f) < 3 or len(l) < 3:
                        continue
                    dl, df = lev(t[-1], l), lev(given(t[0]), f)
                    g0 = given(t[0])
                    if (dl <= (0 if len(l) <= 3 else 1) and df <= (1 if min(len(f), len(t[0])) <= 5 else 2)) or \
                            (dl == 0 and len(l) >= 5 and df <= 2 and f[0] == t[0][0]) or \
                            (dl == 0 and min(len(f), len(g0)) >= 4 and (f.startswith(g0) or g0.startswith(f))):  # 'Srinivas'/'Srini'
                        fz.add(pi)
            fz = {self.canonical(x) for x in fz}
            hits = sorted(fz) if len(fz) == 1 else []
        if not hits and len(t) >= 4:
            # several advisers run together without separators ('Barnabás Póczos Ruslan Salakhutdinov Alexander J. Smola'):
            # every PI whose given and family name occur as neighbours (a middle initial allowed between them)
            how = "embedded"
            emb = set()
            for pi, forms in self.natural.items():
                for f, l in forms:
                    for i in range(len(t) - 1):
                        if given(t[i]) == f and (t[i + 1] == l or (i + 2 < len(t) and len(t[i + 1]) == 1 and t[i + 2] == l)):
                            emb.add(self.canonical(pi))
            hits = sorted(emb)
            if hits:
                return hits, how
        if len(hits) > 1 and any(frozenset((x, y)) in self.distinct for x in hits for y in hits):
            full_ = [pi for pi in hits if any(len(f) > 1 and l == t[-1] and f in {given(x) for x in t[:-1]} for f, l in self.name[pi].forms)]
            if len(full_) == 1:
                return full_, how
        if len(hits) > 1:  # keep the PIs whose full first name agrees, if that disambiguates
            full = [pi for pi in hits if any(given(t[0]) == f for f, l in self.name[pi].forms)]
            if full and len({self.canonical(x) for x in full}) < len({self.canonical(x) for x in hits}):
                hits = full
        if len(hits) > 1 and len({self.canonical(x) for x in hits}) == 1:  # duplicate entries of one PI
            hits = [self.canonical(hits[0])]
        if hits and len(given(t[0])) == 1 and not (len(t) >= 3 and len(t[1]) > 1):  # initial-only given name
            return (hits, how) if len(hits) == 1 else ([], "")
        return hits, (how if hits else "")


def same_person(a, b):
    return Name([a]).match(b) or Name([b]).match(a)


# 'Van Parys, Bart P.G.' / 'Das Gupta, Shuvomoy' / 'del Alamo, Jesus': a family name led by particles is one 'Last, First'
# person (2026-10-27), not two people separated by a comma
PARTICLE_SURNAME = re.compile(r"^(?:(?:van|von|der|den|de|del|della|dela|di|da|das|dos|du|le|la|ter|ten|bin|al|el|st\.?)\s+){1,2}\S+$", re.I)
SPLIT_RX = re.compile(r"\s*;\s*|\s+and\s+|\s+abd\s+|\s*&\s*|\s+with\s+", re.I)


def split_advisers(value, style="natural"):
    """One catalogue adviser value -> person strings. style 'inverted': every value is one 'Last, First' person (DSpace,
    Infoscience, DataSpace); 'natural': 'A B, C D and E F' lists (MIT 'X and Y.', Berkeley, KiltHub)."""
    import html as _html
    raw = _html.unescape(_html.unescape(value or "")).replace("&eacute", "é")
    lines = [x for x in re.split(r"[\r\n]+", raw) if x.strip()]
    if len(lines) > 1:  # one adviser per line (KiltHub)
        return [p for x in lines for p in split_advisers(x, style)]
    v = re.sub(r"\s+", " ", raw).strip()
    if not v:
        return []
    if style == "inverted":
        return [v]
    v = re.sub(r",?\s+(Jr|Sr|II|III|IV)\.?(?=\s*(?:,|;|\band\b|$))", r" \1", v)
    out = []
    for part in SPLIT_RX.split(v):
        part = part.strip().strip(",").strip()
        if not part:
            continue
        bits = [b.strip() for b in part.split(",") if b.strip()]
        # 'Last, First' (one comma, two short sides) is one person; otherwise commas separate people
        if len(bits) == 2 and (len(bits[0].split()) == 1 or PARTICLE_SURNAME.match(bits[0])) and 1 <= len(bits[1].split()) <= 3 and len(bits[1].split()[0].rstrip(".")) >= 1 \
                and (PARTICLE_SURNAME.match(bits[0]) or not any(len(b.split()) >= 2 and len(b.split()[0]) > 2 for b in bits[:1])):
            out.append(part)
        else:
            out.extend(bits)
    return [o for o in out if o]


def has_tokens(quote, name):
    """Every token (2+ chars) of the name occurs as a word in the quote (case/diacritics-insensitive, any order)."""
    q = fold(quote)
    n = re.sub(r"\([^)]*\)", " ", name or "")
    toks_ = [t for t in re.split(r"[^a-z0-9]+", fold(n)) if len(t) > 1]
    return bool(toks_) and all(re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", q) for t in toks_)


def pi_family_names(pi, pi_names, school):
    nm = Name([pi] + list(pi_names or []) + ALIASES.get(school, {}).get(pi, []))
    return {f[1] for f in nm.forms} | {toks(x)[-1] for x in [pi] + list(pi_names or []) if toks(x)}


def names_pi(quote, fams):
    """The quote names the PI: one of the PI's family names occurs as a word (or inside a joined compound)."""
    fq = fold(quote)
    words = re.sub(r"[^a-z]+", " ", fq)
    joined = re.sub(r"[^a-z]", "", fq)
    return any(re.search(r"(?<![a-z])" + re.escape(f) + r"(?![a-z])", words) or (len(f) > 4 and f in joined) for f in fams if len(f) > 1)
