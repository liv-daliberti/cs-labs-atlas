"""Automatic member extraction from a stored people page (proposals for review; the decision modules record the result).

The page's visible text (lpcap.html_text) is cut into a sequence of markers found in document order: section headings
(h1-h6, and short elements whose whole text is a people heading such as "PhD Students" or "Alumni") and person-like
names (short capitalised strings from leaf-ish elements). Each name gets
  descriptor = the text between it and the next marker (<= 250 chars),
  role       = from the descriptor, else from the section heading (postdoc | undergraduate | masters | phd | other | member),
  years      = a stated range or degree year in the descriptor,
  quote      = name + descriptor through the role words when the descriptor states a role, else heading..name when
               within 1500 chars, else name + up to 100 chars of descriptor (flagged 'weak').
Everything is a proposal: faculty/collaborator sections, other institutions, non-names and pre-2016 alumni are flagged
or dropped here, and the reviewer drops the rest.

usage: autom.py SCHOOL "PI" SRC [SRC ...]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap  # noqa: E402
import lpev  # noqa: E402
import names  # noqa: E402

_dict = None


def common_words():
    global _dict
    if _dict is None:
        _dict = set()
        try:
            for w in open("/usr/share/dict/words", encoding="utf-8", errors="ignore"):
                w = w.strip()
                if w and w.islower():
                    _dict.add(w)
        except OSError:
            pass
    return _dict


_first = None


def first_names():
    global _first
    if _first is None:
        import csv
        _first = set()
        for f in ("names.csv", "extras.csv"):
            p = f"{names.ROOT}/nicknames/{f}"
            if os.path.exists(p):
                for row in csv.DictReader(open(p, encoding="utf-8")):
                    _first.add(names.fold(row.get("name1", "")))
                    _first.add(names.fold(row.get("name2", "")))
    return _first


STOPTOK = set("""
people members member team students student phd ph.d ph.d. alumni alumnus alumna former current research researcher researchers
publications publication lab labs laboratory group groups contact home news university universitat universidad institute
department dept school college center centre professor prof assistant associate postdoc postdocs postdoctoral graduate
undergraduate undergraduates undergrad undergrads masters master visitors visitor visiting staff faculty fellow fellows
director principal investigator join us about teaching collaborators collaborator affiliates affiliated scientist scientists
engineer engineers intern interns meng scholar scholars program programs project projects software code data events talks
course courses office hours spring fall summer winter autumn selected recent machine learning computer vision science
sciences systems robotics engineering electrical mechanical computational theory language languages processing natural
networks network security privacy policy law design human interaction intelligence artificial ai ml nlp hci biology
medicine health inc corp llc google microsoft meta amazon apple nvidia ibm openai deepmind facebook adobe intel
mit csail eecs princeton stanford harvard berkeley cmu yale cornell oxford cambridge toronto epfl eth tsinghua
email cv bio website homepage twitter github linkedin scholar orcid more read learn back top menu search skip main
content page pages copyright rights reserved trustees view all show hide previous next photo photos gallery
award awards best paper papers thesis theses dissertation open positions position opening openings hiring apply
prospective now currently previously moved co-advised coadvised advised advisor advisors mentor mentors with and the of
in at for on to from by a an new our my his her their seminar workshop conference symposium journal proceedings
arxiv preprint pdf slides video poster abstract bibtex demo blog press media resources links friends family
quantum optimization algorithms algorithm statistics mathematics math physics chemistry economics operations finance
""".split())
PARTICLES = {"de", "van", "von", "da", "del", "della", "la", "le", "di", "bin", "al", "el", "dos", "das", "du", "ter", "der",
             "den", "y", "e", "ibn", "binti", "van der", "zu"}
HEAD_RX = re.compile(r"^\s*((current|former|past|our|lab|group|research|graduate|undergraduate|doctoral|phd|ph\.d\.?|"
                     r"master'?s?|meng|m\.eng\.?|postdoctoral|visiting|affiliated|alumni|alumnae|staff|team|people|members?|"
                     r"students?|postdocs?|post-docs?|researchers?|scientists?|engineers?|visitors?|interns?|collaborators?|"
                     r"faculty|advisees?|mentees?|fellows?|scholars?|undergrads?|grad students?|sophomores?|juniors?|"
                     r"seniors?|urops?|superurops?|reus?|thesis|senior thesis|research assistants?|alums?|past members?|"
                     r"former members?|previous members?|lab alumni|group alumni|and|&|/|,|-|–|\(|\)|\d{4}|present|"
                     r"principal investigator|pi|director|administrative|admin|support|associates?|affiliates?|"
                     r"m\.s\.|ms|sm|s\.m\.|b\.s\.|bs|ug|mse|undergraduate researchers|graduate researchers)\s*)+[:]?\s*$", re.I)
HEADWORD = re.compile(r"\b(students?|post-?docs?|post-doctoral|postdoctoral|alumni|alumnae|alums?|members?|people|team|staff|"
                      r"visitors?|graduated|former|current|undergrad\w*|ph\.?\s?d\.?|masters?|m\.?eng|researchers?|"
                      r"scientists?|engineers?|fellows?|interns?|advisees?|group|lab|collaborators?|faculty|affiliates?|"
                      r"scholars?|associates?|visiting|thesis|urops?|graduates?|past|previous)\b", re.I)


def heady(txt):
    if not txt or len(txt) > 50 or namey(txt):
        return False
    if re.match(r"^(now|currently|formerly|previously|then|later)\b", txt, re.I) or re.search(r"\s(at|@)\s", txt):
        return False  # a later-job description, not a section heading
    toks = txt.split()
    if namey(" ".join(toks[:2])) or namey(" ".join(toks[:3])):
        return False
    return bool(HEAD_RX.match(txt)) or bool(HEADWORD.search(txt))


EXCL_HEAD = re.compile(r"\b(collaborators?|faculty|affiliated faculty|co-?pis?|friends|advisors?|committee|sponsors?|"
                       r"funding|partners?|external|other labs?|principal investigators?)\b", re.I)
ROLE_RULES = [
    ("postdoc", r"post-?docs?\b|postdoctoral|post-doctoral|post doc"),
    ("undergraduate", r"undergrad|\burops?\b|superurop|senior thesis|junior (?:paper|iw|independent)|independent work|\breu\b|"
                      r"\bb\.?s\.?e?\.?(?=[\s,)']|$)|\bs\.?b\.?(?=[\s,)']|$)|\bug\b|class of|bachelor|sophomore|freshman|"
                      r"\bjunior\b|\bsenior\b(?! (?:research|scientist|engineer|lecturer|software|staff))"),
    ("masters", r"master'?s|\bm\.?\s?eng\b|\bs\.?m\.?(?=[\s,)']|$)|\bmse\b|\bm\.?s\.?(?=[\s,)']|$)|\bmsc\b|\bmpp\b|\bmba\b|"
                r"\bm\.?a\.? student"),
    ("phd", r"ph\.?\s?d|doctoral|graduate student|grad student|graduate researcher|doctorate|\bdphil\b|\bg[1-7]\b"),
    ("other", r"visit|research scientist|research engineer|engineer|\bstaff\b|programmer|research assistant|lab manager|"
              r"scientist|technician|specialist|research associate|research fellow|research scholar|developer|"
              r"administrator|coordinator|manager|\bra\b|intern\b|affiliate"),
]
ROLE_RX = [(r, re.compile(p, re.I)) for r, p in ROLE_RULES]
ALUMNI_RX = re.compile(r"\b(alumni|alumnae|alumnus|alumna|former|past|previous|alums?|graduates|graduated|completed|"
                       r"emeriti|moved on|where are they now)\b", re.I)
FACULTY_DESC = re.compile(r"^\W{0,3}((assistant|associate|full|adjunct|visiting|emeritus)?\s*professor|faculty|lecturer|"
                          r"principal investigator|director\b|pi\b)", re.I)


def namey(t):
    t = t.strip(" ,;:|·•-–—*")
    if not (4 <= len(t) <= 45) or re.search(r"\d|@|http|[{}<>=_/\\#©®™:;!?]", t):
        return False
    t2 = re.sub(r"\s*\([^)]{1,25}\)\s*", " ", t).strip()
    toks = t2.split()
    if not (2 <= len(toks) <= 5):
        return False
    core = []
    for w in toks:
        w2 = w.strip(".,'’\"“”")
        if not w2:
            return False
        lw = names.fold(w2)
        if lw in PARTICLES or re.match(r"^[a-z]{1,3}['’][A-Z]", w2):
            continue
        if lw in STOPTOK:
            return False
        if not (w2[0].isupper() or (w2[0].isalpha() and not w2[0].isascii() and w2[0] == w2[0].upper())):
            return False
        if len(w2) > 1 and w2.isupper() and len(w2) > 14:
            return False
        core.append(lw)
    if len(core) < 2 and not (len(core) == 1 and len(toks) >= 2):
        return False
    if all(len(c) > 2 and w.strip(".,'’\"“”").isupper() for c, w in zip(core, [w for w in toks if names.fold(w.strip(".,'’\"“”")) not in PARTICLES])):
        return False  # ALL-CAPS phrases are headings or labels
    cw, fn = common_words(), first_names()
    real = [c for c in core if len(c.strip(".")) > 1]
    if real and all(c in cw and c not in fn for c in real):
        return False
    return True


EXTERNAL = re.compile(r"^\W{0,3}(at|@|in|with)\s+(?!princeton|mit\b|m\.i\.t|csail|eecs|the (?:lab|group))", re.I)
NOWISH = re.compile(r"\b(now|currently|then|went on|moved to|next|later|joined|→|->|⇒)\b|→|->|⇒", re.I)


def _role(s, external_ok=True):
    """First role word in s; when external_ok is False a role word that is followed by 'at <another place>' or that
    comes after 'now'/'→' (a later job) is ignored."""
    for r, rx in ROLE_RX:
        for m in rx.finditer(s or ""):
            if not external_ok:
                if EXTERNAL.match(s[m.end():m.end() + 40]):
                    continue
                if NOWISH.search(s[:m.start()]):
                    continue
            return r, m
    return None, None


YEAR = r"(?:19[89]\d|20[0-2]\d)"


def _years(desc):
    d = desc or ""
    m = re.search(r"(%s)\s*(?:-|–|—|to|until)+\s*(?:[A-Z][a-z]{2,8}\.?\s+)?(%s|present|now|current|today)" % (YEAR, YEAR), d, re.I)
    if m:
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2)[:2] in ("19", "20") else None
        return [a, b]
    m = re.search(r"(?:ph\.?\s?d|m\.?\s?eng|s\.?m\.?|m\.?s\.?|b\.?s\.?|s\.?b\.?|graduated|class of|postdoc|masters?)\D{0,12}(%s)\b" % YEAR, d, re.I)
    if m:
        return [None, int(m.group(1))]
    m = re.search(r"(?:ph\.?\s?d|m\.?\s?eng|s\.?m|b\.?s|s\.?b|class of)\s*['’](\d\d)\b", d, re.I)
    if m:
        return [None, 2000 + int(m.group(1))]
    return None


def markers(school, src):
    """[(start, end, kind, text)] over the page's html text view, in order."""
    from bs4 import BeautifulSoup
    r, views = lpev.cap(school, src)
    parser = "html.parser" if views.get("html_p") else "lxml"
    t = views.get("html_p") or views.get("html") or ""
    soup = BeautifulSoup(lpcap.decode(r["content"]), parser)
    for x in soup(["script", "style", "noscript", "template"]):
        x.decompose()
    items = []
    seen_el = set()
    from bs4 import NavigableString, Tag
    for el in (soup.body or soup).descendants:
        if not isinstance(el, Tag):
            # a stray text node directly inside a container that holds a list ("Past graduate advisees: <ul>...")
            if type(el) is NavigableString and el.parent is not None and el.parent.name in (
                    "li", "dt", "div", "p", "td", "dd", "body", "section", "article", "main") \
                    and el.parent.find(["ul", "ol", "dl", "table"]) is not None:
                own = lpcap.collapse(str(el))
                if own and heady(own.rstrip(":")):
                    items.append(("head", own, 8))
            continue
        if id(el) in seen_el:
            continue
        if el.name in ("nav", "header") or (el.get("class") and re.search(r"(^|[-_ ])(nav|navbar|menu|breadcrumb)", " ".join(el.get("class") or []), re.I)
                                             and el.name in ("ul", "ol")):
            for d in el.find_all(True):  # navigation menus are not section headings or member lists
                seen_el.add(id(d))
            continue
        txt = lpcap.collapse(el.get_text(" "))
        if not txt:
            continue
        if re.fullmatch(r"h[1-6]", el.name) or (len(txt) <= 60 and heady(txt.rstrip(":")) and
                                                el.name in ("strong", "b", "p", "dt", "th", "div", "span", "summary", "button",
                                                            "label", "u", "em", "li", "a", "td", "font")):
            if not namey(txt):
                items.append(("head", txt, int(el.name[1]) if re.fullmatch(r"h[1-6]", el.name) else 7))
                for d in el.find_all(True):
                    seen_el.add(id(d))
                continue
        if el.name in ("a", "strong", "b", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "span", "p", "div", "figcaption", "dt", "dd",
                       "em", "i", "u", "font", "th", "label", "small", "caption", "article", "section"):
            if el.find(["div", "p", "li", "td", "table", "ul", "ol", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6"]) is not None \
                    and el.name in ("div", "li", "td", "section", "article", "p"):
                continue
            first = re.split(r"\s+[,|·•–—]\s+|\s+\(|,\s+(?=[A-Z])|\s+-\s+", txt)[0] if txt else ""
            for c in (txt, first):
                c = c.strip(" ,;:|·•-–—*")
                if c and namey(c):
                    items.append(("name", c, 0))
                    for d in el.find_all(True):  # the same name again in a child element is not a new item
                        seen_el.add(id(d))
                    break
    out, pos = [], 0
    levels = {}
    for kind, s, lv in items:
        i = t.find(s, pos)
        if i < 0:
            continue
        if out and s == out[-1][3]:  # a repeat of the previous item would jump ahead to a later occurrence
            continue
        if out and kind == "name" and out[-1][2] == "name" and out[-1][0] == i:
            continue
        out.append((i, i + len(s), kind, s))
        if kind == "head":
            levels[i] = lv
        pos = i + len(s)
    markers.levels = levels
    return r, t, out


_all_pis = {}


def school_pis(school):
    if school not in _all_pis:
        _all_pis[school] = [l["pi"] for l in json.load(open(f"{lpcap.ROOT}/{school}/labpage-input.json"))]
    return _all_pis[school]


def extract(school, src, pi=None, held=(), span=None):
    """span=(start, end): only the part of the page text from the first occurrence of `start` to the next occurrence
    of `end` (or the end of the page when end is None/not found)."""
    r, t, mk = markers(school, src)
    if span:
        a = t.find(span[0])
        if a < 0:
            raise ValueError(f"span start {span[0]!r} not in {src}")
        b = t.find(span[1], a + len(span[0])) if span[1] else -1
        b = b if b >= 0 else len(t)
        mk = [m_ for m_ in mk if a <= m_[0] < b]
        if not mk or mk[0][2] != "head":
            mk = [(a, a + len(span[0]), "head", span[0])] + mk
    # a short role label right after a name ("Jason Greenfield PhD Student") is that name's descriptor, not a heading
    consumed = set()
    for k in range(len(mk) - 1):
        i, e, kind, s = mk[k]
        i2, e2, kind2, s2 = mk[k + 1]
        if kind == "name" and kind2 == "head" and i2 - e <= 3 and len(s2) <= 45 and not re.search(r"(s|i|ae)\W*$", s2) and \
                (_role(s2)[0] or re.search(r"principal investigator|\bpi\b|director|mascot", s2, re.I)):
            consumed.add(k + 1)
    mk = [m_ for k, m_ in enumerate(mk) if k not in consumed]
    rows = []
    head, head_pos = None, None
    pi_names = [pi] if pi else []
    others = [p for p in school_pis(school) if p != pi]
    role_head = None
    alumni_ctx = False
    levels = getattr(markers, "levels", {})
    stack = []  # (level, alumni heading?, current heading?) of the enclosing headings
    for k, (i, e, kind, s) in enumerate(mk):
        if kind == "head":
            head, head_pos = s, i
            lv = levels.get(i, 7)
            if lv >= 7 and _role(s)[0] and len(s) <= 40 and not re.search(r"(s|i|ae)\W*$", s) \
                    and not ALUMNI_RX.search(s) and not re.search(r"\b(current|present)\b", s, re.I):
                continue  # a singular role label ("PhD Student") between cards is a descriptor, not a section
            while stack and stack[-1][0] >= lv:
                stack.pop()
            cur = bool(re.search(r"\b(current|present|active)\b", s, re.I))
            alu = bool(ALUMNI_RX.search(s)) and not cur and len(s) <= 60 and "::" not in s and " | " not in s
            stack.append((lv, alu, cur))
            alumni_ctx = False
            for _lv, _alu, _cur in reversed(stack):
                if _cur:
                    break
                if _alu:
                    alumni_ctx = True
                    break
            if _role(s)[0] or ALUMNI_RX.search(s) or EXCL_HEAD.search(s) or \
                    re.search(r"\b(members?|people|team|current|students?|group|researchers?|advisees?|lab)\b", s, re.I):
                role_head = s
            continue
        nxt = mk[k + 1][0] if k + 1 < len(mk) else len(t)
        mp0 = re.match(r"^(.*?\S)\s*\(([^)]*)\)\s*$", s)
        if mp0 and (" " in mp0.group(2).strip() or "," in mp0.group(2)):  # "Kendall Olszowka (MAE, BLUEniverse)"
            s = mp0.group(1)
            e = i + len(s)
        mc = re.search(r"\s*\([a-z]\)$", s)  # "Julia Balla (c)" (a co-advised marker)
        if mc:
            s = s[:mc.start()]
            e = i + len(s)
        if "(" in s and ")" not in s:  # "Kendall Olszowka (MAE" cut at a line break
            s = s.split("(")[0].rstrip()
            e = i + len(s)
        if ", " in s:  # "Ben Silverman, Tracer"
            s = s.split(", ")[0]
            e = i + len(s)
        md = re.match(r"^(?:Dr|Prof|Professor)\.?\s+", s)
        if md:
            i = i + md.end()
            s = s[md.end():]
        mt = re.search(r"\s+[a-z]$", s)  # a stray icon letter ("Chris Hodsdon e")
        if mt:
            s = s[:mt.start()]
            e = i + len(s)
        if s.endswith(".") and len(s.split()[-1]) > 3:
            s = s[:-1]
            e = i + len(s)
        mp = re.match(r"^(.*?\S)\s*\(([^)]*)\)\s*$", s)
        if mp and (" " in mp.group(2).strip() or names.fold(mp.group(2)).strip() in STOPTOK or _role(mp.group(2))[0]):
            s = mp.group(1)
            e = i + len(s)
        desc = t[e:nxt][:250].strip()
        if pi_names and any(names.match_one(s, p) for p in pi_names):
            continue
        role, m = _role(desc[:90], external_ok=False)
        src_of_role = "descriptor"
        if not role:
            role, _ = _role(head or "")
            src_of_role = "heading" if role else None
        if not role and role_head and role_head != head:
            role, _ = _role(role_head)
            src_of_role = "parent heading" if role else None
        if not role:
            role = "member"
        years = _years(desc[:200]) or _years(head or "")
        if years is None and head and re.fullmatch(r"\D{0,30}(%s)\D{0,10}" % YEAR, head) and (role == "undergraduate" or
                                                                                         (role_head and role_head != head)):
            y = int(re.search(YEAR, head).group(0))
            years = [y, y]
        flags = []
        excl = lambda h_: bool(h_ and EXCL_HEAD.search(h_) and not ALUMNI_RX.search(h_) and not _role(h_)[0])
        bare = not head or bool(re.fullmatch(r"\W*(%s)?\W*(%s)?\W*" % (YEAR, YEAR), head or ""))
        if excl(head) or (bare and excl(role_head)):
            flags.append("excluded-heading")
        if FACULTY_DESC.match(desc) and not (head and ALUMNI_RX.search(head)):
            flags.append("faculty-desc")
        if years and years[1] is not None and years[1] < 2016:
            flags.append("pre-2016")
        if any(names.match_one(s, p) for p in others):
            flags.append("is-a-PI")
        if m is not None and src_of_role == "descriptor":
            q = t[i:e + (desc and t.find(desc, e) - e if desc else 0) + m.end()].strip() if False else None
            j = t.find(desc, e) if desc else e
            q = t[i:j + m.end()].strip()
            qkind = "name+role"
        elif head is not None and head_pos is not None and e - head_pos <= 1500:
            q = t[head_pos:e].strip()
            qkind = "heading..name"
        else:
            q = (t[i:e] + t[e:e + min(len(desc) + 1, 100)]).strip()
            qkind = "weak"
            flags.append("weak-quote")
        h, hk = names.match(s, list(held))
        rows.append({"name": s, "role": role, "years": years, "head": head if head == role_head or not role_head else f"{role_head} > {head}", "desc": desc[:120], "quote": q,
                     "qkind": qkind, "flags": flags, "alumni": alumni_ctx, "held": h, "held_kind": hk, "url": r["url"],
                     "capture_url": r.get("capture_url"), "sha256": r["sha256"]})
    return rows


def main():
    short = "--short" in sys.argv
    if short:
        sys.argv.remove("--short")
    school, pi = sys.argv[1], sys.argv[2]
    labs = {l["pi"]: l for l in json.load(open(f"{lpcap.ROOT}/{school}/labpage-input.json"))}
    held = labs[pi]["students_held"] if pi in labs else []
    for src in sys.argv[3:]:
        rows = extract(school, src, pi, held)
        print(f"### {src}  ({len(rows)} names)")
        last = object()
        for x in rows:
            if x["head"] != last:
                print(f"  ## {x['head']}{'  [alumni]' if x['alumni'] else ''}")
                last = x["head"]
            tag = f"H:{x['held']}" if x["held"] else ""
            if short:
                print(f"    {x['name']} [{x['role']}{' ' + str(x['years']) if x['years'] else ''}{' ' + ','.join(x['flags']) if x['flags'] else ''}] {tag}")
            else:
                print(f"    {x['name']:<30} {x['role']:<13} {x['years'] or ''} {','.join(x['flags'])} {tag} | {x['desc'][:60]}")


if __name__ == "__main__":
    main()
