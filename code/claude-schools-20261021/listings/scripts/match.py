"""Find each PI on each captured listing page (offline, from listings/<school>/captures.sqlite).

Ported from the Princeton listings sweep. Changes:
- a Matcher per PI built from `pi` + `aliases` (+ curated extra aliases with a recorded reason), with
  parenthetical / quoted nicknames, common English nicknames, umlaut transliteration (ä -> ae), hyphen
  and initial handling, suffixes (Jr., III), mononyms (exact block only) and an `initials` tier
  (surname exact, every given-name token equal or initial-compatible, first given name exact unless the
  input itself only has an initial). Surname alone never matches.
- every hit records its `match_basis`; `initials` hits are checked for ambiguity by build.py.
"""
import html
import re
import unicodedata

NICK = {
    "thomas": ["tom"], "tom": ["thomas"], "matthew": ["matt"], "matt": ["matthew"],
    "benjamin": ["ben"], "ben": ["benjamin"], "daniel": ["dan", "danny"], "dan": ["daniel"], "danny": ["daniel"],
    "edward": ["ed", "ted"], "ed": ["edward"], "michael": ["mike"], "mike": ["michael"],
    "robert": ["rob", "bob", "bobby"], "rob": ["robert"], "bob": ["robert"], "andrew": ["andy", "drew"],
    "andy": ["andrew"], "david": ["dave"], "dave": ["david"],
    "alexander": ["alex"], "alex": ["alexander", "alexandre"],
    "zachary": ["zach", "zack"], "zach": ["zachary"],
    "jennifer": ["jen", "jenn"], "jen": ["jennifer"], "nicholas": ["nick", "nic"],
    "nick": ["nicholas", "nic"], "nic": ["nick", "nicholas"], "samuel": ["sam"], "sam": ["samuel"],
    "jonathan": ["jon"], "jon": ["jonathan"], "christopher": ["chris"], "chris": ["christopher"],
    "william": ["bill", "will"], "bill": ["william"], "will": ["william"],
    "james": ["jim", "jamie"], "jim": ["james"], "jamie": ["james"],
    "joseph": ["joe"], "joe": ["joseph"], "richard": ["rick", "dick", "rich"], "rick": ["richard"],
    "steven": ["steve"], "stephen": ["steve"], "steve": ["steven", "stephen"],
    "kenneth": ["ken"], "ken": ["kenneth"], "gregory": ["greg"], "greg": ["gregory"],
    "anthony": ["tony"], "tony": ["anthony"], "katherine": ["kathy", "kate", "katie"], "kathy": ["katherine", "kathleen"],
    "kathleen": ["kathy"], "elizabeth": ["liz", "beth"], "patrick": ["pat"], "timothy": ["tim"], "tim": ["timothy"],
    "jeffrey": ["jeff"], "jeff": ["jeffrey"], "frederick": ["fred"], "frederic": ["fredo", "fred"], "fred": ["frederick", "frederic"],
    "lawrence": ["larry"], "larry": ["lawrence"], "charles": ["charlie", "chuck"], "susan": ["sue"],
    "peter": ["pete"], "philip": ["phil"], "phillip": ["phil"], "ronald": ["ron"], "ron": ["ronald"],
    "douglas": ["doug"], "doug": ["douglas"], "nathaniel": ["nate"], "nathan": ["nate"], "abraham": ["abe"],
    "constantinos": ["costis"], "konstantinos": ["costis"], "eugene": ["gene"], "leonard": ["len"],
    "raymond": ["ray"], "terrence": ["terry"], "terence": ["terry"], "gerald": ["jerry"],
    "margaret": ["maggie", "meg"], "deborah": ["deb"], "deb": ["deborah"], "rebecca": ["becky"],
    "jacob": ["jake"], "joshua": ["josh"], "josh": ["joshua"], "vincent": ["vince"], "mathew": ["matt"],
    "lorraine": ["lori"], "lori": ["lorraine"], "elizabeth": ["liz", "beth", "betsy"], "kristofer": ["kris"],
    "kris": ["kristofer", "kristopher"], "christos": ["christos"], "jeannette": ["jeannette"],
}
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}
TRANS = str.maketrans({"ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ß": "ss", "æ": "ae", "Æ": "Ae",
                       "œ": "oe", "Œ": "Oe", "ı": "i", "’": "'", "‘": "'", "`": "'", "´": "'", "‐": "-", "‑": "-",
                       "–": "-", "—": "-"})
UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})

TITLE_RX = re.compile(r"\b(Professor|Professeur\w*|Lecturer|Faculty|Emerit\w*|Scholar|Instructor|Chair|Dean|Director|Fellow|"
                      r"Researcher|Provost|President|Preceptor|Chief|Head|Co-?director|Member|Associate|Assistant|"
                      r"Senior|Visiting|Adjunct|Affiliated|Scientist|Principal|Teaching|Courtesy|Tenure|Ordinary|"
                      r"Full Professor|Titular|Lecturer|PI|Investigator|Engineer|Faculty Member|MER|Ma[iî]tre|Below the Line)\b", re.I)
NOT_TITLE_RX = re.compile(r"^(Research (Interests|Areas|Topics)|Tags:|E-?mail|Office|Phone|Tel|Fax|Homepage|Website|"
                          r"Web|Ph\.?\s?D|M\.?S\.?|B\.?S\.?|Profile|Room|Lab\b|Read more|Read full|More info|Learn more|"
                          r"Open in new window|P:|Download|CV|Contact|Areas?:|Interests?:)", re.I)
SECTION_RX = re.compile(r"^(?:(?:CS|EE|EECS|CSD|IC|HCII|RI|LTI|MLD|CSAIL|S3D|ISR|CBD|SCS|MIT|EPFL)\s+)?(Faculty|Associated|Associate Faculty|Emerit\w*|Visiting|Visitors|Affiliated|Joint|Core|Senior (Faculty|Scientists|Lecturers)|"
                        r"Junior|Lecturers?|Researchers?|Research Faculty|Research Scholars?|Research Staff|Staff|"
                        r"Teaching|Adjunct|People|Professors|In Memoriam|Postdoc\w*|Graduate|Instructors|Fellows|"
                        r"Members|Directory|Our Faculty|All Faculty|Former|Primary|Secondary|Courtesy|Ladder|"
                        r"Tenure|Administrative|Full Professors|Assistant Professors|Associate Professors|"
                        r"Tenure[- ]Track|Titular|Adjoint|Special Faculty|Systems Scientists|Principal Investigators|Ordinary|"
                        r"Professors Emerit\w*|Honorary|Voting|Research Professors|Professors of|Department Faculty|"
                        r"EECS Faculty|CS Faculty|Computer Science Faculty|Principal Investigators|Core/Dual|Lecturers|"
                        r"New Faculty|Scientists|(CS |EE |EECS )?Current Faculty|Honorary Professors|External|Courtesy Appointments|"
                        r"Emeriti|Professors and|Faculty Emerit\w*|Faculty Members|Professeurs?|MER\b|Collaborateurs|Nominations|"
                        r"Ma[iî]tres? d)\b", re.I)
NOT_SECTION_RX = re.compile(r"(\bmenu\b|navigation|^Search)|^(Research (Areas|Interests|Topics)|People Menu|Faculty Spotlight|Faculty & Research$|"
                            r"Faculty Resources|Faculty Books|Faculty Awards|Faculty Positions|Faculty Search|Faculty Openings|"
                            r"Faculty Hiring|Faculty News)", re.I)
NONFAC_RX = re.compile(r"Postdoc|Post-?doctoral|Graduate Student|Ph\.?D\.? (Student|Candidate)|Doctoral Student|"
                       r"\bStaff\b|Undergraduate|Alumni|In Memoriam|Memorial|Spotlight|\bNews\b|\bEvents?\b|"
                       r"Research (Associate|Collaborator|Specialist|Scholar)|Visiting (Fellow|Researcher|Scholar)|Student", re.I)
FAC_RX = re.compile(r"Professor|Professeur|Lecturer|Faculty|Instructor|Emerit|Dean\b|Chair\b|Provost|President|"
                    r"Principal Investigator|Scientist|\bMER\b|Ma[iî]tre d|Below the Line", re.I)


def norm(s, umlaut=False):
    s = html.unescape(s)
    if umlaut:
        s = s.translate(UMLAUT)
    s = s.translate(TRANS)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[-.,;:/\"()\[\]]+", " ", s)
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    s = s.replace("'", "")
    return [t for t in s.split() if t not in SUFFIX]


def core(tokens):
    """drop initials (single letters)"""
    return [t for t in tokens if len(t) > 1]


def _paren_split(name):
    """'Dimitrios (Dimi) Apostolopoulos' -> ('Dimitrios Apostolopoulos', ['Dimi']); also "Red" in quotes."""
    nicks = re.findall(r"\(([^)]+)\)|\"([^\"]+)\"|“([^”]+)”", name)
    nicks = [next(x for x in t if x) for t in nicks]
    base = re.sub(r"\([^)]*\)|\"[^\"]*\"|“[^”]*”", " ", name)
    return " ".join(base.split()), nicks


class Matcher:
    def __init__(self, pi, extra_aliases=()):
        self.pi = pi["pi"]
        self.core = {}      # tuple(core tokens) -> basis
        self.full = {}      # tuple(tokens incl. initials) -> basis (names whose core has < 2 tokens)
        self.mononym = set()
        self.initial_forms = []  # (tokens incl. initials, first_given_is_initial)
        names = [(pi["pi"], "name")] + [(a, "alias") for a in pi.get("aliases", []) if a] + \
                [(a, "curated_alias") for a in extra_aliases]
        for nm, basis in names:
            base, nicks = _paren_split(nm)
            forms = [(nm, basis), (base, basis)] + [(n + " " + base.split()[-1], "nickname") for n in nicks if base.split()]
            for f, b in forms:
                for um in (False, True):
                    toks = norm(f, umlaut=um)
                    if not toks:
                        continue
                    c = core(toks)
                    if len(c) >= 2:
                        self._add(self.core, tuple(c), b)
                        for n in NICK.get(c[0], []):
                            self._add(self.core, tuple([n] + c[1:]), "nickname")
                        if len(c) == 3 and "-" not in f and len(toks) == 3:
                            # 'Adji Bousso Dieng' -> 'Adji Dieng' (three plain tokens only)
                            self._add(self.core, (c[0], c[2]), "middle_name_dropped")
                    elif len(toks) >= 2:
                        self._add(self.full, tuple(toks), b)
                    elif len(toks) == 1 and len(toks[0]) > 2:
                        self.mononym.add(toks[0])
                    if len(toks) >= 2 and (len(toks) != len(c) or len(c) >= 2):
                        self.initial_forms.append((tuple(toks), len(toks[0]) == 1))

    @staticmethod
    def _add(d, k, b):
        order = ["name", "alias", "curated_alias", "nickname", "middle_name_dropped"]
        if k not in d or order.index(b) < order.index(d[k]):
            d[k] = b

    def match(self, written):
        """basis if `written` (a candidate name string) is this PI, else None."""
        toks = norm(written)
        if not toks:
            return None
        c = tuple(core(toks))
        if len(c) >= 2 and c in self.core:
            return self.core[c]
        if tuple(toks) in self.full:
            return self.full[tuple(toks)]
        if len(toks) == 1 and toks[0] in self.mononym:
            return "mononym"
        # initials tier
        if len(toks) >= 2:
            for form, first_is_initial in self.initial_forms:
                if len(form) != len(toks) or form[-1] != toks[-1] or form == tuple(toks):
                    continue
                ok = True
                for a, b in zip(form[:-1], toks[:-1]):
                    if a == b:
                        continue
                    if (len(a) == 1 and b[0] == a) or (len(b) == 1 and a[0] == b):
                        continue
                    ok = False
                    break
                if not ok:
                    continue
                if not first_is_initial and form[0] != toks[0] and not (len(toks[0]) == 1 and False):
                    # the input spells the first name out: the page must spell it the same way
                    continue
                return "initials"
        return None


def matchers(pis, extra=None):
    extra = extra or {}
    return [Matcher(p, extra.get(p["pi"], [])) for p in pis]


HONORIFIC = re.compile(r"^(Prof\.?|Professor|Dr\.?|Dr\.? Prof\.?|Prof\.? Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+")


def split_name_prefix(block, m):
    """If block starts with this PI's name (or 'Last, First'), return (name_as_written, remainder, basis)."""
    if not hasattr(m, "_idx"):
        m._idx = Index([m])
    return block_matches(block, m._idx).get(0)


def mononym_remainder_ok(rem):
    r = rem.strip()
    if not r:
        return True
    if r[0] in "(,;:|-–—/":
        return True
    return bool(TITLE_RX.match(r))


def remainder_ok(rem):
    r = rem.strip()
    if not r:
        return True
    if r[0] == "(":
        return True  # "(on leave)", "(appointment starts July 1, 2017)"
    if r[0] in ",;:|-–—/":
        rest = r.lstrip(",;:|-–—/ ")
        if not rest:
            return True
        return bool(re.match(r"^(\S+\s+){0,3}" + TITLE_RX.pattern, rest, re.I)) and len(rest) <= 300
    if r[0].islower():
        return False  # bio sentence: "X is a composer ..."
    # title in the same block as the name ("Dan Trueman Professor of Music"): first words must be a title
    return bool(re.match(r"^(\S+\s+){0,4}" + TITLE_RX.pattern, r, re.I)) and len(r) <= 300


def _compat(form, toks, first_is_initial):
    if len(form) != len(toks) or form[-1] != toks[-1] or form == tuple(toks):
        return False
    for a, b in zip(form[:-1], toks[:-1]):
        if a == b:
            continue
        if (len(a) == 1 and b[0] == a) or (len(b) == 1 and a[0] == b):
            continue
        return False
    if not first_is_initial and form[0] != toks[0]:
        return False  # the input spells the first name out: the page must spell it the same way
    return True


class Index:
    """All PIs' name variants in one lookup table: written name -> {matcher index: basis}."""

    def __init__(self, ms):
        import collections
        self.ms = ms
        self.core = collections.defaultdict(list)
        self.full = collections.defaultdict(list)
        self.mono = collections.defaultdict(list)
        self.ini = collections.defaultdict(list)
        for mi, m in enumerate(ms):
            for k, b in m.core.items():
                self.core[k].append((mi, b))
            for k, b in m.full.items():
                self.full[k].append((mi, b))
            for t in m.mononym:
                self.mono[t].append((mi, "mononym"))
            for form, fi in m.initial_forms:
                self.ini[form[-1]].append((mi, form, fi))
        self._cache = {}

    def lookup(self, written):
        r = self._cache.get(written)
        if r is not None:
            return r
        toks = norm(written)
        res = {}
        if toks:
            c = tuple(core(toks))
            if len(c) >= 2:
                for mi, b in self.core.get(c, []):
                    res.setdefault(mi, b)
            for mi, b in self.full.get(tuple(toks), []):
                res.setdefault(mi, b)
            if len(toks) == 1:
                for mi, b in self.mono.get(toks[0], []):
                    res.setdefault(mi, b)
            if len(toks) >= 2:
                for mi, form, fi in self.ini.get(toks[-1], []):
                    if mi not in res and _compat(form, tuple(toks), fi):
                        res[mi] = "initials"
        if len(self._cache) > 200000:
            self._cache.clear()
        self._cache[written] = res
        return res


def block_matches(block, idx):
    """{matcher index: (name_as_written, remainder, basis)} for every PI whose name starts this block."""
    raw = block.strip()
    hm = HONORIFIC.match(raw)
    raw2 = raw[hm.end():] if hm and not re.match(r"^Professor\s+(of|in|and|emerit)", raw, re.I) else raw
    words = raw2.split()
    out = {}
    for k in range(min(8, len(words)), 0, -1):
        pref = " ".join(words[:k]).rstrip(",;:|")
        if not pref:
            continue
        res = idx.lookup(pref)
        for mi, b in res.items():
            if mi in out:
                continue
            rem = raw2[raw2.index(pref) + len(pref):] if pref in raw2 else " ".join(words[k:])
            if b == "mononym" and not mononym_remainder_ok(rem):
                continue
            out[mi] = (pref, rem, b)
    mm = re.match(r"^([^,]{2,40}),\s*([^,;|]{2,60})(.*)$", raw2)
    if mm:
        last, first, rest = mm.group(1), mm.group(2), mm.group(3)
        fw = first.split()
        for k in range(len(fw), 0, -1):
            for mi, b in idx.lookup(" ".join(fw[:k]) + " " + last).items():
                if mi in out or b == "mononym":
                    continue
                out[mi] = (f"{last}, {' '.join(fw[:k])}", (" " + " ".join(fw[k:]) if k < len(fw) else "") + rest, b)
    return out


def all_block_matches(blocks, idx, max_block=400, split_cells=False):
    """Per-block matches. With split_cells (tables whose rows put 'Last' and 'First' in separate cells,
    e.g. the 2016-2019 CSD directory), a short block followed by a short block is also tried as
    'Last' + 'First'; such a match spans two blocks and is written 'Last First' as on the page."""
    bm = [block_matches(t, idx) if len(t) <= max_block else {} for _, t in blocks]
    if split_cells:
        for i in range(len(blocks) - 1):
            a, b = blocks[i][1], blocks[i + 1][1]
            if bm[i] or not (1 <= len(a.split()) <= 3 and 1 <= len(b.split()) <= 4) or re.search(r"[\d@,:;|]", a + b):
                continue
            for mi, basis in idx.lookup(b + " " + a).items():
                if basis != "mononym":
                    bm[i][mi] = (a + " " + b, "", basis, 2)
    return bm


def find_pi(blocks, bm, mi):
    """Hits for one PI (matcher index mi) given precomputed block matches."""
    hits = []
    n = len(blocks)
    pos = 0
    for i in [x for x in range(n) if mi in bm[x]]:
        if i < pos:
            continue
        name_written, rem, basis = bm[i][mi][:3]
        if not remainder_ok(rem):
            continue
        start = i
        j = i
        while j + 1 < n and mi in bm[j + 1] and not bm[j + 1][mi][1].strip() and len(bm[j][mi]) == 3:
            j += 1  # skip duplicate name blocks (image alt / heading then link)
        if j != i:
            start = j
            name_written, rem, basis = bm[j][mi][:3]
        span = bm[start][mi][3] if len(bm[start][mi]) > 3 else 1
        kind = blocks[start][0]
        title_lines = []
        if rem.strip(" ,;:|-–—"):
            title_lines.append(rem.strip(" ,;:|-–—"))
        k = start + span
        name_h = kind if kind.startswith("h") else None
        while k < n and len(title_lines) < 4:
            kk, tt = blocks[k]
            deeper = bool(name_h) and kk.startswith("h") and kk > name_h  # e.g. h2 title under an h1 name
            if kk.startswith("h") and kk <= "h4" and not deeper and (not TITLE_RX.search(tt) or
                                                                     (SECTION_RX.search(tt) and len(tt.split()) <= 4)):
                break
            if NOT_TITLE_RX.search(tt) or len(tt) > 220 or not TITLE_RX.search(tt):
                break
            if bm[k]:
                break  # the next block starts with a (any) PI's name
            if re.match(r"^(Prof\.?|Dr\.?)\s+[A-Z]", tt) and not re.match(
                    r"^Prof\.?\s+(of|in|and|emerit|titular|ordinary|associate|assistant|adjunct|full)\b", tt, re.I):
                break  # 'Prof. Jane Doe': another person, not a title
            title_lines.append(tt)
            k += 1
        end = k - 1 if k - 1 >= start + span - 1 else start + span - 1
        quote = " ".join(" ".join(t for _, t in blocks[start:end + 1]).split())
        name_level = kind if kind.startswith("h") else None
        section = None
        for b in range(start - 1, -1, -1):
            bk, bt = blocks[b]
            if not bk.startswith("h"):
                continue
            if name_level and bk > name_level:
                continue
            if bm[b]:
                continue
            if len(bt.split()) <= 8 and SECTION_RX.search(bt) and not NOT_SECTION_RX.search(bt):
                section = bt
                break
        hits.append({"block_index": start, "name_as_written": name_written, "quote": quote,
                     "title_lines": title_lines, "section_heading": section, "match_basis": basis,
                     "name_kind": kind})
        pos = end + 1
    return hits


def find(blocks, m, max_block=400):
    idx = Index([m])
    return find_pi(blocks, all_block_matches(blocks, idx, max_block), 0)


STRONG_NONFAC_RX = re.compile(r"Postdoc|Post-?doctoral|Graduate Student|Ph\.?D\.? (Student|Candidate)|Doctoral Student|"
                              r"Undergraduate|Alumn|Student|Research (Associate|Collaborator|Specialist)|"
                              r"Visiting (Fellow|Researcher|Scholar|Student)|Project (Staff|Manager)|"
                              r"Commercialization|Programmer|Administrative|Coordinator|Assistant to", re.I)
SEC_FAC_RX = re.compile(r"facult|professor|professeur|emerit|lecturer|principal investigator|core/dual|voting|"
                        r"\bMER\b|honorary|courtes", re.I)


def classify(hit, slot, flags=None, untitled_ok=False):
    """(is_faculty_listing, reason_if_not, emeritus, visiting).

    An entry counts when
    - its own title lines carry a faculty title (Professor, Lecturer, Faculty, Instructor, Emeritus, ...), or
    - it carries some other title (Director, Department Head, an external job for an adjunct) and sits under
      a faculty section heading of the listing ('Core Faculty', 'Adjunct Faculty', 'Voting Faculty'), or
    - the listing's entries carry no titles at all and the slot declares `untitled_ok` for a verified
      listing region ('heading': only entries whose name is a heading, which excludes filter drop-downs).
    Titles naming students, postdocs, staff roles or visiting scholars never count.
    """
    flags = flags or {}
    tl = " | ".join(hit["title_lines"])
    sec = hit["section_heading"] or ""
    ctx = tl + " || " + sec
    emeritus = bool(re.search(r"emerit|honorary|honoraire|retired", ctx, re.I)) or flags.get("emeritus", False)
    visiting = bool(re.search(r"\bvisiting\b|\bvisitors?\b", ctx, re.I)) or flags.get("visiting", False)
    memoriam = bool(re.search(r"memoriam|memorial|deceased|passed away", ctx, re.I))
    has_fac_title = bool(FAC_RX.search(tl))
    strong_nonfac = bool(STRONG_NONFAC_RX.search(tl)) and not re.search(r"Professor|Lecturer|Faculty|Emerit", tl, re.I)
    weak_nonfac = bool(NONFAC_RX.search(tl)) and not re.search(r"Professor|Lecturer|Faculty|Emerit", tl, re.I)
    sec_fac = bool(SEC_FAC_RX.search(sec)) and not NONFAC_RX.search(re.sub(r"(?i)facult\w*", "", sec))
    if not sec and slot.get("kind") in ("main", "sub", "emeritus") and re.search(r"facult", slot.get("slot", ""), re.I):
        sec_fac = True  # a faculty-only listing page without section headings
    if memoriam:
        return False, "in memoriam", emeritus, visiting
    if strong_nonfac:
        return False, f"non-faculty title: {tl}", emeritus, visiting
    if has_fac_title and not weak_nonfac:
        return True, None, emeritus, visiting
    if tl and sec_fac:
        return True, None, emeritus, visiting
    if weak_nonfac:
        return False, f"non-faculty title: {tl}", emeritus, visiting
    if untitled_ok and not tl and (untitled_ok != "heading" or hit.get("name_kind", "b").startswith("h")):
        return True, None, emeritus, visiting
    return False, f"no faculty title (title={tl!r}, section={sec!r})", emeritus, visiting
