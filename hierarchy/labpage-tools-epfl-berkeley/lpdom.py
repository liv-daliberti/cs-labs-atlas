"""HTML linearisation for the lab-page pass: lines with heading flags, member-name candidates, publication entries.

lines(content) -> [Line]: the page's visible text cut at block boundaries, in document order. Each Line has text
(whitespace-collapsed), tag (nearest block ancestor), heading level (1-6 for h1-h6, 7 for short bold/role-like lines),
and hrefs. The text views used by quotes come from lpcap.texts (whole-page get_text(" ")), so quotes are built from the
whole-page text, never from these lines; lines only locate things.
"""
import re
import warnings
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Comment, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BLOCK = {"p", "div", "li", "td", "th", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article",
         "header", "footer", "figcaption", "figure", "blockquote", "pre", "ul", "ol", "dl", "table", "tbody", "nav",
         "main", "aside", "form", "center", "address", "body", "html", "summary", "details", "caption", "label",
         "option", "select", "button"}
HEAD = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

ROLE_WORDS = (r"ph\.?\s?d\.?s?|doctoral|doctorate|post-?docs?|postdoctoral|students?|alumni|alumnae|alums?|members?|staff|"
              r"visitors?|visiting|interns?|master'?s?|msc|m\.s\.|undergrad\w*|bachelor|researchers?|scientists?|"
              r"engineers?|former|past|current|team|people|collaborators?|faculty|fellows?|graduates?|candidates?|"
              r"assistants?|associates?|administrat\w*|lab manager|group|advisees?|mentees?|semester project|"
              r"research staff|affiliates?")
ROLE_RX = re.compile(r"(?<!\w)(" + ROLE_WORDS + r")(?!\w)", re.I)

STOP_TOKENS = set("""
research lab laboratory group home news contact publications publication people team members member about projects
project teaching courses course software datasets dataset code join us open positions positions more read view all
university epfl berkeley eecs school institute department computer science engineering electrical sciences faculty
welcome page menu search back top skip content main navigation copyright rights reserved privacy policy accessibility
email phone office address map directions events seminar seminars talks blog awards links resources overview
alumni alumnae current former past students student postdocs postdoc postdoctoral visitors visitor staff phd ph.d
doctoral masters master undergraduate undergraduates researchers researcher scientists scientist engineers engineer
interns intern collaborators collaborator assistant associate professor lecturer director administrative admin
fellows fellow candidate candidates graduate graduates program programs center centre initiative machine learning
artificial intelligence systems theory security data network networks computing vision robotics language languages
information informatics communication communications distributed algorithms algorithm signal processing photo
photos gallery video videos twitter github linkedin scholar google website homepage cv bio biography profile
the and of for in on at to with by from a an our we you your this that is are be as or
january february march april may june july august september october november december spring summer fall autumn winter
lausanne switzerland california usa swiss federal technology polytechnique fédérale ecole école
award awards prize prizes fellowship fellowships scholarship honorable mention best paper finalist winner winners
laboratories labs centre institute institut universität université universidad universita college academy foundation
inc corp corporation company llc ltd gmbh technologies technology google microsoft meta apple amazon ibm intel nvidia
openai deepmind facebook adobe netflix uber twitter airbnb tesla samsung huawei qualcomm salesforce linkedin startup
founder cofounder co-founder cto ceo cso vp president provost chancellor
program project workshop conference journal press street road avenue building room campus division department
studio week month year seminar talk tutorial class lecture lectures keynote panel hackathon summit
graduation resident residency alumnus alumna next current present now visiting phds
stanford harvard mit cmu princeton yale cornell columbia oxford cambridge eth zurich toronto michigan
illinois berkeley ucla ucsd usc nyu tsinghua peking epfl inria skylabs tech delft sachs anthropic bsc msc
eindhoven ilmenau munich kaist postech
""".split())

PARTICLES = {"van", "von", "der", "den", "de", "del", "della", "di", "da", "dos", "das", "du", "la", "le", "el", "al",
             "bin", "ben", "ter", "ten", "zu", "y", "e", "d'", "mc"}

NAME_TOKEN = re.compile(r"^(?:[A-ZÀ-ÖØ-ÞĀ-ſ][\w'’`\-\.À-ÿĀ-ſ]*|[A-Z]\.(?:-?[A-Z]\.)?|d'[A-Z][\w\-]*|(?:" +
                        "|".join(sorted(PARTICLES, key=len, reverse=True)) + r"))$")


@dataclass
class Line:
    text: str
    tag: str
    level: int = 0          # 1-6 h-tags, 7 = bold/short role-like line, 0 = body
    hrefs: list = field(default_factory=list)
    idx: int = 0
    col: int = 0            # 0-based column of a td/th cell within its row (0 for non-cells)


CHROME_TOKENS = {"footer", "site-footer", "page-footer", "footer-container", "navbar", "nav", "navigation", "menu",
                 "main-menu", "nav-menu", "menu-main", "breadcrumb", "breadcrumbs", "sidebar", "site-header",
                 "cookie-banner", "cookie-notice", "skip-link", "top-bar", "topbar", "nav-main", "nav-container"}
CHROME_RX = re.compile(r"^$")  # kept for callers; token sets decide


def soup_of(content, strip_chrome=True):
    """Parsed page without scripts/styles/comments; with strip_chrome, also without <nav>/<footer> and elements whose
    class or id names a footer, nav bar, menu, breadcrumb or sidebar (site chrome repeats on every page)."""
    from lpcap import decode
    s = BeautifulSoup(decode(content) if isinstance(content, bytes) else content, "lxml")
    for t in s(["script", "style", "noscript", "template"]):
        t.decompose()
    for c in s.find_all(string=lambda x: isinstance(x, Comment)):
        c.extract()
    if strip_chrome:
        for t in s(["nav", "footer", "aside"]):
            t.decompose()
        for t in s.find_all(True):
            if getattr(t, "decomposed", False):
                continue
            attrs = getattr(t, "attrs", None)
            if not attrs:
                continue
            toks = {x.lower() for x in (attrs.get("class") or [])} | {(attrs.get("id") or "").lower()}
            if toks & CHROME_TOKENS and t.name not in ("body", "html", "main", "article"):
                t.decompose()
    return s


def collapse(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _block_of(node):
    p = node.parent
    while p is not None and p.name not in BLOCK:
        p = p.parent
    return p


def _is_bold(node, blk):
    p = node.parent
    while p is not None and p is not blk:
        if p.name in ("strong", "b") or (p.get("class") and any(re.search(r"title|head|name", c, re.I) for c in p.get("class"))):
            return True
        p = p.parent
    return False


def lines(content, base_url=None):
    s = soup_of(content)
    out = []
    cur_blk, buf, bold_all, hrefs = None, [], True, []
    body = s  # whole document: some pages close </body> and open a second <body>
    for h in s.find_all("head"):
        h.decompose()

    def flush():
        nonlocal buf, bold_all, hrefs
        t = collapse(" ".join(buf))
        if t:
            tag = cur_blk.name if cur_blk is not None else ""
            lvl = HEAD.get(tag, 0)
            if not lvl and len(t) <= 60 and bold_all and len(t.split()) <= 8:
                lvl = 7
            col = 0
            if tag in ("td", "th"):
                col = len([c for c in cur_blk.find_previous_siblings(["td", "th"])])
            out.append(Line(t, tag, lvl, hrefs, len(out), col))
        buf, bold_all, hrefs = [], True, []

    for node in body.descendants:
        if isinstance(node, NavigableString) and not isinstance(node, Comment):
            txt = str(node)
            if not txt.strip():
                continue
            blk = _block_of(node)
            if blk is not cur_blk:
                flush()
                cur_blk = blk
            buf.append(txt)
            if not _is_bold(node, blk):
                bold_all = False
            a = node.find_parent("a")
            if a is not None and a.get("href") and base_url:
                hrefs.append(urljoin(base_url, a["href"]))
        elif getattr(node, "name", None) == "br":
            # <br> splits a block into lines
            flush()
    flush()
    return out


NOT_HEAD_RX = re.compile(r"^(next|now|currently|then|later|went to|joined)\b|\s(at|in|from|with|@)\s|,|\bnow\b", re.I)


SECTION_LABEL_RX = re.compile(r"\b(students|post-?docs|postdoctoral (researchers|fellows|scholars|associates)|alumni|alumnae|"
                              r"alums|members|staff|visitors|interns|researchers|scientists|engineers|fellows|team|"
                              r"people|former|past|current|graduates|undergraduates|undergrads|candidates|phds|"
                              r"ph\.?d\.?s|associates|advisees|group|lab)\b", re.I)


def is_heading(line):
    if line.level and line.level <= 6 and len(line.text) <= 80:
        return True
    if NOT_HEAD_RX.search(line.text):
        return False
    if line.level == 7 and SECTION_LABEL_RX.search(line.text) and len(line.text.split()) <= 6:
        return True
    if line.level == 7 and len(line.text.split()) <= 4 and re.search(
            r"^(selected |recent |all |our )?(publications?|papers|preprints|talks|news|teaching|courses|projects|"
            r"software|awards|honors|service|contact|bio|biography|research)\b", line.text, re.I):
        return True
    if len(line.text) <= 40 and len(line.text.split()) <= 5 and SECTION_LABEL_RX.search(line.text) and \
            re.match(r"^(current |former |past |our )?[A-Z]", line.text) and not looks_like_name(line.text):
        # "PhD Students", "Alumni", "Postdoctoral Researchers"
        return bool(re.fullmatch(r"[\w\s\.'’&/\-:()]+", line.text)) and not re.search(r"\d{4}", line.text)
    return False


def looks_like_name(s):
    s = collapse(s).strip(" ,;:·•|-–—")
    if not (4 <= len(s) <= 45):
        return False
    if re.search(r"[0-9@/\\|<>{}\[\]=+*#$%&!?;:]", s):
        return False
    toks = s.replace(" ", " ").split()
    if not (2 <= len(toks) <= 5):
        return False
    caps = 0
    for t in toks:
        tt = t.strip(",")
        if not NAME_TOKEN.match(tt):
            return False
        low = tt.lower().strip(".")
        if low in STOP_TOKENS and low not in PARTICLES:
            return False
        if tt[0].isupper():
            caps += 1
        if len(tt) > 3 and tt.isupper() and not re.search(r"[À-ÿ]", tt):
            # all-caps words: acronyms (EPFL, IEEE) unless the whole line is an upper-case name
            if not all(x.isupper() for x in toks):
                return False
    if caps < 2:
        return False
    if all(len(t.strip(".")) == 1 for t in toks[:-1]) and len(toks) > 2:
        return False
    return True


SPLIT_RX = re.compile(r"\s*(?:,|\(|\s[-–—|·•:]\s|\s/\s)\s*")


PAREN_NICK = re.compile(r"^((?:[A-ZÀ-ÖØ-Þ][\w\-'’.À-ÿ]*\s+)+)\(([A-ZÀ-ÖØ-Þ][\w\-'’. À-ÿ]{0,25})\)((?:\s+[A-ZÀ-ÖØ-Þ\w][\w\-'’.À-ÿ]*)+)")


def name_prefix(text):
    """The leading 'First Last' of a line like 'Jane Doe, PhD student (2018-2022)' -> ('Jane Doe', rest).
    A parenthesised nickname inside the name is kept: 'Xue Bin (Jason) Peng (2021)' -> 'Xue Bin (Jason) Peng'."""
    t = collapse(text).lstrip("•·▪◦*–—-> ").strip()
    t = re.sub(r",?\s+(BSc|B\.Sc\.?|MSc|M\.Sc\.?|PhD|Ph\.D\.?|MD|MEng|M\.Eng\.?)\b\.?$", "", t)
    mt = re.match(r"^(?:Dr\.?|Prof\.?|Professor|Mr\.?|Ms\.?|Mrs\.?)\s+(.*)$", t)
    if mt:
        return name_prefix(mt.group(1))
    m0 = PAREN_NICK.match(t)
    if m0 and (re.search(r"\d", m0.group(2)) or ROLE_RX.search(m0.group(2))):
        m0 = None  # "(PhD May 2025)" is a note, not a nickname
    if m0:
        first, nick, last = m0.group(1).strip(), m0.group(2), m0.group(3).strip()
        # take the longest leading run of 'last' that keeps a name shape
        lt = last.split()
        for k in range(min(3, len(lt)), 0, -1):
            cand = first + " " + " ".join(lt[:k])
            if looks_like_name(cand):
                full = f"{first} ({nick}) {' '.join(lt[:k])}"
                rest = t[len(full):].strip(" ,")
                if t.startswith(full):
                    return full, rest
                break
    if looks_like_name(t):
        return t, ""
    m = SPLIT_RX.search(t)
    if m and m.start() > 0:
        head = t[:m.start()].strip()
        if looks_like_name(head):
            return head, t[m.start():].strip(" ,")
    return None, None


YEAR_RANGE = re.compile(r"((?:19|20)\d{2})\s*(?:[-–—]|to|until)\s*((?:19|20)\d{2}|present|now|today|current)?", re.I)
YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def years_in(text):
    m = YEAR_RANGE.search(text or "")
    if m:
        a = int(m.group(1))
        b = m.group(2)
        if b and b[:2].isdigit():
            return [a, int(b)]
        if b:
            return [a, 2026]
        return [a, None]
    ys = [int(y) for y in YEAR.findall(text or "")]
    if ys:
        return [min(ys), max(ys)]
    return None


ROLE_MAP = [
    (r"undergrad|bachelor|b\.?sc\b|\bbs student|\burap\b|summer student|\bsurf\b|\bbs semester", "undergraduate"),
    (r"post-?doc|postdoctoral|post doctoral", "postdoc"),
    (r"ph\.?\s?d|doctoral|doctorate|\bgraduate student|\bgrad student|\bgraduate researcher", "phd"),
    (r"master|m\.?sc\b|m\.s\.|\bms student|\bmeng\b|m\.eng|\bms\b|semester project|\bm\.a\.", "masters"),
    (r"visit|guest|exchange", "visitor"),
    (r"\bintern", "intern"),
    (r"^\s*(administrative |executive |lab |group )?assistant\s*$|administrat|secretary|coordinator|assistant to|office manager|executive assistant|business manager|"
     r"program manager|financ|\bhr\b", "admin"),
    (r"scientist|engineer|research staff|research associate|research assistant|researcher|staff|manager|developer|"
     r"programmer|technician|specialist", "research_staff"),
    (r"professor|faculty|lecturer|\bpi\b|principal investigator|director|head of|co-?lead", "faculty"),
]


def role_of(*texts):
    for t in texts:
        if not t:
            continue
        for rx, r in ROLE_MAP:
            if re.search(rx, t, re.I):
                return r
    return None


ALUMNI_RX = re.compile(r"alumn|\balums?\b|former|past|previous|graduated|emerit|old members|ex-members", re.I)


def heading_rank(line):
    return line.level if line.level else 8


LABEL_RX = re.compile(r"^([A-Za-z][A-Za-z .'’/&()-]{1,40}?)\s*[:：]\s*(.+)$")
LIST_SEP = re.compile(r"\s*(?:,|;|·|•|\||\s\band\b\s|/)\s*")


def split_list(text):
    """'Ann Lee (co-advised with X), Bo Xu , Cy Wu' -> [('Ann Lee', '(co-advised with X)'), ('Bo Xu', ''), ...]"""
    prot, depth, cur = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        cur += ch if not (depth and ch in ",;|/") else {",": "\u0001", ";": "\u0002", "|": "\u0003", "/": "\u0004"}[ch]
    out = []
    for piece in LIST_SEP.split(cur):
        piece = piece.translate({1: ",", 2: ";", 3: "|", 4: "/"}).strip()
        if not piece:
            continue
        nm, rest = name_prefix(piece)
        out.append((nm, rest or "") if nm else (None, piece))
    return out


def member_candidates(content, base_url=None):
    """[(heading_path, name, rest_of_line, next_line, line_idx)] in document order. heading_path is the list of
    enclosing headings (h1-h6 by level, then bold/role-like lines), outermost first."""
    ls = lines(content, base_url)
    out = []
    stack = []  # (rank, text)
    for i, ln in enumerate(ls):
        if (is_heading(ln) or (ln.level and ln.level <= 6 and len(ln.text) <= 80)) and \
                (not looks_like_name(ln.text) or (ln.level and ln.level <= 6 and ROLE_RX.search(ln.text))):
            rk = heading_rank(ln)
            while stack and stack[-1][0] >= rk:
                stack.pop()
            stack.append((rk, ln.text))
            continue
        if ln.col > 0 and ln.tag in ("td", "th"):
            # in a table only the first column names people; later columns hold destinations, years, topics
            prev_first = [x for x in ls[max(0, i - 4):i] if x.tag in ("td", "th") and x.col == 0]
            if prev_first and name_prefix(prev_first[-1].text)[0]:
                continue
        # inline lists: "PhD: Ann Lee, Bo Xu (co-advised), Cy Wu" or a role section holding "Ann Lee, Bo Xu, Cy Wu"
        lab_m = LABEL_RX.match(ln.text)
        label = lab_m.group(1) if lab_m and ROLE_RX.search(lab_m.group(1)) and not looks_like_name(lab_m.group(1)) else None
        body_txt = lab_m.group(2) if label else ln.text
        in_role = label or any(ROLE_RX.search(h) for _, h in stack)
        if in_role and len(body_txt) <= 3000 and not re.search(r"[“\"]", body_txt):
            parts = split_list(body_txt)
            names = [(n, r) for n, r in parts if n]
            if len(names) >= 2 and len(names) >= 0.5 * len(parts) or (label and names):
                path = [t for _, t in stack] + ([label] if label else [])
                for n, r in names:
                    out.append((path, n, r, "", i))
                continue
        name, rest = name_prefix(ln.text)
        if name and ln.tag in ("td", "th") and ln.col == 0:
            # table row: the other cells of the row are this person's details (class year, destination...)
            cells = []
            for x in ls[i + 1:i + 12]:
                if x.tag not in ("td", "th") or x.col == 0:
                    break
                cells.append(x.text)
            if cells:
                rest = ((rest + " | ") if rest else "") + " | ".join(cells)
        if name:
            nxt = ls[i + 1].text if i + 1 < len(ls) else ""
            if i + 1 < len(ls) and (is_heading(ls[i + 1]) or (ls[i + 1].level and ls[i + 1].level <= 6)):
                nxt = ""
            out.append(([t for _, t in stack], name, rest, nxt if len(nxt) <= 160 else nxt[:160], i))
    return out, ls


# ------------------------------------------------------------------ publications
ENTRY_TAGS = ("li", "p", "tr", "dd", "div", "article", "td", "dt", "section", "blockquote")


def norm_title(s):
    from lpnames import fold
    s = fold(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def pub_entries(content, base_url=None, min_len=40, max_len=2500):
    """Innermost block elements that look like one publication each: (text, element). Also splits <p>/<div> blocks that
    hold several <br>-separated entries when each piece has a year."""
    s = soup_of(content)
    body = s
    cands = []
    for el in body.find_all(ENTRY_TAGS):
        t = collapse(el.get_text(" "))
        if not (min_len <= len(t) <= max_len):
            continue
        # innermost: no descendant candidate block holding most of the text
        inner = False
        for d in el.find_all(ENTRY_TAGS):
            dt = collapse(d.get_text(" "))
            if len(dt) >= min_len and len(dt) >= 0.6 * len(t):
                inner = True
                break
        if inner:
            continue
        cands.append(el)
    return cands, s


def heading_years(s):
    """Map element -> nearest preceding year heading (h1-h6/strong/dt whose text is just a year)."""
    return None


_LEX = None


def _lex():
    global _LEX
    if _LEX is None:
        import json, os
        d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "name_lexicon.json")))
        eng = set()
        try:
            for w in open("/usr/share/dict/words", encoding="utf-8", errors="ignore"):
                w = w.strip()
                if w and w.islower() and w.isalpha():
                    eng.add(w)
        except OSError:
            pass
        _LEX = (d["given"], d["family"], eng)
    return _LEX


def plausible_person(name):
    """A page string looks like a real person's name: its given name (or, for family-name-first forms, its family
    name) is one that occurs in the bylines/rosters behind name_lexicon.json, and it is not a common English word
    that merely heads a phrase ('Working Papers', 'Global Health')."""
    from lpnames import tokens
    given, family, eng = _lex()
    toks = [t for t in tokens(name) if len(t) > 1 and t not in PARTICLES]
    if len(toks) < 2:
        return False
    f, l = toks[0], toks[-1]
    if given.get(f, 0) >= 20:
        return True
    if f in eng and l in eng:
        return False
    if f in given and f not in eng:
        return True
    if f in given and l in family and l not in eng:
        return True
    if l in given and f in family and f not in eng:  # "Popescu George"
        return True
    if f not in eng and l in family and l not in eng:
        return True
    return False
