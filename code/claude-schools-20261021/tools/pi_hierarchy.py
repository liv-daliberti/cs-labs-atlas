"""One school's PI hierarchy package (owner decisions 2026-10-21): department -> PI lab -> papers + students -> student papers.

pis        every census faculty member with is_pi; each gets one own lab (PI + advisees). A census lab unit is reused only
           when the collection unit has this PI as its single leader; otherwise a new own lab is proposed and the
           multi-leader / umbrella unit stays a collective (not a lab).
papers     an OpenAlex work from hierarchy/<school>/openalex-sweep.sqlite is the PI's lab paper when
             (a) an authorship matches the PI's name and its OWN institutions (lineage) or raw affiliation strings name the
                 school, and
             (b) that authorship is the PI: the work is on the PI's own DBLP person page (census PID; cached DBLP
                 publication lists, matched by DOI or title) or is one of the PI's DBLP-verified collection works, or a
                 stated advisee of the PI is a co-author, or the authorship's OpenAlex author id is anchored (it sits at the
                 PI's name on one of those works), and
             (c) the paper falls in the PI's appointment: contains() against a reviewed faculty period (the site's rule,
                 boundary years unresolved), else a captured department listing from the paper's own year that names the
                 PI (owner decision 2026-10-21; it proves that calendar year only).
           Works are matched to collection works by DOI, else normalized title within one year; the rest are new works.
students   people whose advising context names the PI (by person id, or by name), and direct lab memberships of a reused
           unit. Advising is the owner's lab model (PI + advisees); the relation and its sources are kept.
student    a lab paper with a lab student on its byline: the student's collection personLink (status kept), or for a new
papers     work an authorship that matches the student's name and lists the school (candidate).
-> hierarchy/<school>/pis.json, lab_papers.jsonl.gz, students.json, student_papers.jsonl.gz, report.json

usage: pi_hierarchy.py <school> [<school> ...]
"""
import calendar, collections, datetime, gzip, html, json, re, sqlite3, sys, unicodedata, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SITE = Path('/n/fs/resemble/maxent-grpo/princeton-live-20261015/atlas/data')
DBLP = {'cmu': 'claude-cmu-20261017', 'epfl': 'claude-epfl-20261019', 'mit': 'claude-mit-20261020', 'berkeley': 'claude-berkeley-20261021',
        'stanford': 'claude-stanford-20261027'}
INST = {'princeton': 'I20089843', 'cmu': 'I74973139', 'epfl': 'I5124864', 'mit': 'I63966007', 'berkeley': 'I95457486', 'stanford': 'I97018004'}
AFF = {'princeton': r'princeton\s+univ|univ\w*\.?\s+(?:of\s+)?princeton|princeton\.edu',
       'cmu': r'carnegie[\s-]+mellon|\bcmu\b|cmu\.edu',
       'epfl': r'\bepfl\b|polytechnique\s+f[ée]d[ée]rale\s+de\s+lausanne|swiss\s+federal\s+institute\s+of\s+technology\s+(?:in\s+|at\s+)?lausanne|epfl\.ch',
       'mit': r'massachusetts\s+institute\s+of\s+technology|\bmit\b|mit\.edu|csail',
       'berkeley': r'(?:university\s+of\s+california|\buc)[\s,]+berkeley|berkeley\.edu',
       # Stanford University (OpenAlex I97018004, ROR 00f54p054; 'Leland Stanford Junior University' is its legal name); not
       # SRI International (formerly Stanford Research Institute) nor Stanford Research Systems
       'stanford': r'stanford\.edu|\bstanford\b(?!\s+research\s+(?:institute|systems|international))'}
TODAY = datetime.date.today().isoformat()
COLLECTIVE = re.compile(r'\b(cent(?:er|re)|initiative|consortium|program(?:me)?|project|cluster|institute)\b', re.I)  # not labs (owner, 2026-10-21)
NOT_PAPERS = {'dataset', 'paratext', 'peer-review', 'erratum', 'supplementary-materials', 'other', 'grant', 'standard', 'retraction', 'reference-entry', 'libguides'}
ADV_RX = [re.compile(r'(?i:advis[eo]rs?)(?:\(s\))?(?!\s*\(AC\))\s*:?\s*([^;|]+?)(?=\s*(?:Degree:|Research Area|Readers?|Examiners?|;|\||$))'),
          re.compile(r'([A-Z][\w.\- ]+?)\s*\((?:Primary )?Advis[eo]r\)')]  # named adviser fields only, never readers or examiners
NICK = {'tom': 'thomas', 'matt': 'matthew', 'ben': 'benjamin', 'dan': 'daniel', 'ed': 'edward', 'mike': 'michael', 'rob': 'robert',
        'bob': 'robert', 'andy': 'andrew', 'dave': 'david', 'alex': 'alexander', 'zach': 'zachary', 'jen': 'jennifer', 'nick': 'nicholas',
        'sam': 'samuel', 'jon': 'jonathan', 'chris': 'christopher', 'bill': 'william', 'will': 'william', 'jim': 'james', 'joe': 'joseph',
        'steve': 'steven', 'greg': 'gregory', 'tony': 'anthony', 'kate': 'katherine', 'liz': 'elizabeth', 'pete': 'peter', 'rich': 'richard',
        'rick': 'richard', 'gabe': 'gabriel', 'ted': 'edward', 'stephen': 'steven', 'fred': 'frederick', 'larry': 'lawrence', 'jeff': 'jeffrey', 'phil': 'philip', 'ken': 'kenneth', 'don': 'donald'}


def _nick_pairs():
    """Given-name pairs that may be the same person: the public carltonnorthern/nicknames table (Apache-2.0,
    hierarchy/nicknames/names.csv) plus curated extras (extras.csv, each with its reason) and NICK. Direct pairs only:
    'ron' matches 'ronald' and 'aaron', but that never makes 'aaron' match 'ronald'."""
    import csv
    pairs = {frozenset((a, b)) for a, b in NICK.items()}
    for f in ('names.csv', 'extras.csv'):
        fp = Path(__file__).resolve().parents[1] / 'hierarchy/nicknames' / f
        if fp.exists():
            for r in csv.DictReader(open(fp)):
                if r.get('relationship') == 'has_nickname' and r.get('name1') and r.get('name2'):
                    pairs.add(frozenset((r['name1'].strip().lower(), r['name2'].strip().lower())))
    return pairs


NICK_MAP = None
DUMP_PERSONS = None  # hierarchy/dblp-dump-persons.json.gz, read once per process


def nick_ok(a, b):
    global NICK_MAP
    if a == b:
        return True
    if NICK_MAP is None:
        NICK_MAP = collections.defaultdict(set)
        for pr in _nick_pairs():
            x = sorted(pr)
            if len(x) == 2:
                NICK_MAP[x[0]].add(x[1]); NICK_MAP[x[1]].add(x[0])
    return b in NICK_MAP.get(a, ()) or given(a) == given(b)


def read(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


LETTERS = str.maketrans({'ı': 'i', 'ł': 'l', 'Ł': 'l', 'ø': 'o', 'Ø': 'o', 'đ': 'd', 'Đ': 'd', 'ß': 'ss', 'æ': 'ae', 'œ': 'oe', 'þ': 'th'})  # no NFKD decomposition


def toks(s):
    s = unicodedata.normalize('NFKD', str(s or '').translate(LETTERS)); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'\([^)]*\)', ' ', s)
    if ',' in s and s.count(',') == 1:  # "Last, First M."
        a, b = s.split(','); s = b + ' ' + a
    return [t for t in re.sub(r"[^a-z\- ]+", ' ', s.replace("'", '').replace('’', '').replace('‘', '').replace('`', '')).replace('-', ' ').split() if t]


def given(t):
    return NICK.get(t, t)


SUFFIX = {'jr', 'sr', 'ii', 'iii', 'iv'}


def nosuffix(t):
    """Name tokens without a trailing generational suffix (2026-10-29: 'John W. Fisher III' is John Fisher; the suffix had
    been read as the family name, so none of his 'Fisher III' bylines matched the PI)."""
    while len(t) >= 3 and t[-1] in SUFFIX:
        t = t[:-1]
    return t


DEGREE_JUNK = re.compile(r"\s*,?\s*(?:(?:Ph\.?\s?D|M\.?\s?Eng|S\.?\s?M|S\.?\s?B|Sc\.?\s?D|M\.?\s?B\.?\s?A|M\.?\s?S|Eng)\.?\s*)*"
                         r"(?:\([^)]*\)\s*)?(?:Massachusetts Institute of Technology|Sloan School of Management)\.?\s*")


def clean_person_name(name):
    """Catalogue author strings with the degree and school run in (MIT DSpace): 'Justin,M. Eng.(Justin K.)Massachusetts
    Institute of Technology. Yu' -> 'Justin Yu'; 'Ji Young, Ph. D. Massachusetts Institute of Technology Lee' -> 'Ji Young Lee'."""
    if 'Massachusetts Institute of Technology' not in name and 'Sloan School of Management' not in name and ',' not in name \
            and not re.search(r'\bauthor\b', name):
        return name
    t = re.sub(r'(?:^|,)\s*author\b\.?|\bauthor\.\s*', ' ', name)  # catalogue role words: 'author. Núñez López Carlos', 'Núñez López, Carlos, author'
    t = DEGREE_JUNK.sub(' ', t)
    t = re.sub(r'\([^)]*\)', ' ', t)                                   # '(Vladimir Lubenov)'
    t = re.sub(r',?\s*\b\d{4}-(?:\d{4})?', ' ', t)                       # birth years, '1979-'
    t = re.sub(r',?\s*\b(?:Jr|Sr|II|III|IV)\b\.?', ' ', t)               # generational suffixes
    t = re.sub(r'\s+', ' ', t).strip(' ,.')
    if t.count(',') == 1:  # 'Wang, Peng' left over
        a, b = t.split(',', 1); t = f'{b.strip()} {a.strip()}'
    return re.sub(r'\s+', ' ', t.replace(' .', ' ')).strip(' ,.')


ADVISING_LABEL = re.compile(r"Doctoral Dissertation (?:Co-)?Advisor \((?:AC|NonAC)\)|Doctoral Dissertation Reader \((?:AC|NonAC)\)"
                            r"|Doctoral \(Program\)|Master's Program Advisor|Undergraduate Major Advisor|Postdoctoral Faculty Sponsor"
                            r"|Postdoctoral Research Mentor")
WEAK_LABEL = re.compile(r"Reader|\(Program\)|Program Advisor|Major Advisor")


def advising_label(quote, names):
    """The Stanford Profiles advisee heading the student's name sits under in a quote ('Doctoral (Program) A, B
    Doctoral Dissertation Advisor (AC) C'), or None when the quote names no heading before the name."""
    q = unicodedata.normalize('NFKD', str(quote or '')).encode('ascii', 'ignore').decode()
    for nm in names:
        t = toks(nm)
        if not t:
            continue
        m = re.search(r'\b' + re.escape(t[-1]) + r'\b', q, re.I)
        if m:
            heads = [h for h in ADVISING_LABEL.finditer(q) if h.start() < m.start()]
            return heads[-1].group(0) if heads else None
    return None


ADVISER_NAMED = re.compile(r"advis[oe]rs?(?:\(s\))?\s*:\s*([^;\n]{3,120})|([A-Z][\w.'\- ]{2,40}?)\s*\(advis[oe]r\)", re.I)


def relation_names_other_adviser(r, pi_names):
    """Every source quote names the student's adviser(s), and none of them is this PI (2026-10-28: Princeton's roster
    line 'Kritkorn Karntikoon - Adviser(s): Bernard Chazelle' had been attached to Weinberg and Braverman too). Quotes
    that speak of co-advising or a primary advisor describe shared advising and never count as naming another."""
    fams = {unicodedata.normalize('NFKD', toks(n)[-1]).encode('ascii', 'ignore').decode().lower() for n in pi_names if toks(n)}
    quotes = [q.get('quote') or '' for q in r.get('sources') or []]
    if not quotes:
        return False
    for q in quotes:
        if re.search(r'co-?advis|primary advis', q, re.I):
            return False
        named = ' '.join((m.group(1) or m.group(2) or '') for m in ADVISER_NAMED.finditer(q))
        named = unicodedata.normalize('NFKD', named).encode('ascii', 'ignore').decode().lower()
        if not named or any(re.search(r'\b' + re.escape(f) + r'\b', named) for f in fams):
            return False
    return True


def relation_is_weak(r, names):
    """Program advising or a reader role only: every source quote puts the name under such a heading (or, with no
    quote heading, the relation's own role is one)."""
    labels = [advising_label(q.get('quote'), names) for q in r.get('sources') or []]
    labels = [l for l in labels if l] or ([r['role']] if ADVISING_LABEL.fullmatch(str(r.get('role') or '')) else [])
    return bool(labels) and all(WEAK_LABEL.search(l) for l in labels)


def near_relation(s, year):
    """The paper's year is within three years of the student's recorded advising or membership (no years: any)."""
    ys = [int(y) for rel in s.get('relations') or [] for y in rel.get('years') or [] if str(y).isdigit()]
    return not ys or not year or min(ys) - 3 <= int(year) <= max(ys) + 3


class Name:
    """A person's name forms: (first, last) pairs from the name and its aliases; compound surnames allowed."""
    def __init__(self, names):
        self.forms = set()
        names = list(names)
        self.mono = {toks(n)[0] for n in names if len(toks(n)) == 1}
        for n in list(names):  # "J. Andrew (Drew) Bagnell": the parenthetical nickname is a given name too
            for nick in re.findall(r'\(([^)]+)\)', str(n or '')):
                rest = toks(n)
                if rest and len(toks(nick)) == 1:
                    names.append(toks(nick)[0] + ' ' + rest[-1])
        for n in names:
            t = nosuffix(toks(n))
            if len(t) >= 3 and len(t[0]) == 1:  # "M. Frans Kaashoek" is also written "Frans Kaashoek"
                self.forms.add((t[1], t[-1]))
            if len(t) >= 3:  # "Jun-Yan Zhu" is also written "Junyan Zhu"
                self.forms.add((''.join(t[:-1]), t[-1]))
            if len(t) < 2:
                continue
            self.forms.add((t[0], t[-1]))
            self.forms.add((t[0], ''.join(t[1:])))      # compound surname, written together
            if len(t) >= 3:
                self.forms.add((t[0], ''.join(t[-2:])))
            self.forms.add((t[-1], t[0]))              # family-name-first order

    def match(self, raw):
        t = nosuffix(toks(raw))
        if len(t) == 1:  # a single-name person ("Arvind") matches only that single name
            return t[0] in self.mono
        if len(t) < 2:
            return False
        cands = {(t[0], t[-1]), (t[0], ''.join(t[1:])), (t[0], ''.join(t[-2:]))}
        if len(t) >= 3 and len(t[0]) == 1:  # a byline "S. Matthew Weinberg" is also "Matthew Weinberg"
            cands.add((t[1], t[-1]))
        for f, l in cands:
            for F, L in self.forms:
                if l == L and (nick_ok(f, F) or (len(f) == 1 and F.startswith(f)) or (len(F) == 1 and f.startswith(F))):
                    return True
        return False


def same_student(a, b):
    """Two student records of one lab that Name.match missed but are one person: the same family name and middle names
    with first given names that are nickname-equal or one a prefix (3+ letters) of the other ('Ali'/'Alireza',
    'Theo'/'Théophile', 'Subra'/'Subramanian'), or the same 3+ name tokens reordered ('Tan Nhat Bui'/'Nhat-Tan Bui').
    Two-token reorders ('Wei Li'/'Li Wei') and 1-2 letter prefixes ('Xi'/'Xinyi', 'Ru'/'Rui') are often different people."""
    ta, tb = toks(a), toks(b)
    if len(ta) < 2 or len(tb) < 2:
        return False
    if len(ta) >= 3 and sorted(ta) == sorted(tb):
        return True
    if ta[-1] != tb[-1]:
        return False
    x, y = sorted((ta[0], tb[0]), key=len)
    if nick_ok(x, y) or (len(x) >= 3 and y.startswith(x) and ta[1:-1] == tb[1:-1]):
        return True
    gx, gy = sorted((''.join(ta[:-1]), ''.join(tb[:-1])), key=len)  # 'Amir'/'Amirali Bagher', 'Kyutae'/'Kyu-Tae Thomas'
    return len(gx) >= 4 and gy.startswith(gx)


def byline_name(raw):
    """A byline string as 'Given Family': HTML entities decoded, and one 'Family, Given[, Middle]' comma form turned round."""
    s = html.unescape(str(raw or '')).strip()
    if s.count(',') >= 1 and not re.search(r',\s*(jr|sr|ii|iii|iv)\.?$', s, re.I):
        fam, rest = s.split(',', 1)
        s = f"{rest.replace(',', ' ').strip()} {fam.strip()}"
    return re.sub(r'\s+', ' ', s).strip()


def name_variants(name):
    """A student name with a parenthesized part, as its readings: 'Fatma Imamoglu (Deniz)' -> Fatma Imamoglu, Fatma
    Deniz; 'Fanglin(Linda) Liu' -> Fanglin Liu, Linda Liu; 'Xi (Peter) Chen' -> Xi Chen, Peter Chen."""
    m = re.match(r'^(.*?)\s*\(([^)]+)\)\s*(.*)$', name or '')
    if not m:
        return []
    before, inner, after = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    out = [re.sub(r'\s+', ' ', f'{before} {after}').strip()]
    if '/' in inner or not re.fullmatch(r"[A-Z][a-z'\-]+(?: [A-Z][a-z'\-]+)?", inner) or re.fullmatch(r'(?i)mech\w*|ece|eecs|phd|ms|bs|meng', inner):
        return [v for v in out if len(v.split()) >= 2]  # pronouns, departments, degrees: not a name
    if after:  # a given name ('Fanglin(Linda) Liu') or, after a lone given name, a maiden name ('Michelle (Karabin) Harter')
        out.append(f'{inner} {after}')
        if len(before.split()) == 1:
            out.append(f'{before} {inner}')
    elif len(before.split()) >= 2:  # a family name: 'Fatma Imamoglu (Deniz)'
        out.append(f'{before.split()[0]} {inner}')
    return [v for v in out if len(v.split()) >= 2]


def student_on_byline(nm, s_toks, raw):
    """A student's name on a byline: Name.match, or forms Name.match rejects but that are the same person on one lab paper:
    given names written joined or split ('Sangeon'/'Sang Eon Park'), a first given name that is a 3+ letter prefix of the
    other ('Divy'/'Divya', 'Themis'/'Themistoklis'), or the byline adding a first name before the known one ('Sergio
    Sebastian Pineda' for 'Sebastian Pineda'). The family name must agree in every case. A byline is read as a name first (byline_name:
    HTML entities decoded, 'Arye, Matvey' turned round)."""
    raw = byline_name(raw)
    if nm.match(raw):
        return True
    t = toks(raw)
    if len(t) < 2 or len(s_toks) < 2 or t[-1] != s_toks[-1]:
        return False
    if ''.join(t[:-1]) == ''.join(s_toks[:-1]):
        return True
    x, y = sorted((t[0], s_toks[0]), key=len)
    if len(x) >= 3 and y.startswith(x):
        return True
    if len(x) >= 6 and one_edit(x, y):  # 'Siddarth'/'Siddharth', 'Dhiyva'/'Dhivya'
        return True
    return len(t) >= 3 and s_toks[0] in t[1:-1] and len(s_toks[0]) >= 3


def one_edit(a, b):
    """a and b differ by one insertion, deletion, substitution or adjacent transposition."""
    if a == b or abs(len(a) - len(b)) > 1:
        return a == b
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    a, b = sorted((a, b), key=len)
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


# Chinese, Korean and Vietnamese family names (romanized). Under these a given name that is a prefix of another is a
# different common name, not a short form: 'Xin Li' / 'Xinyu Li', 'Xiao Liu' / 'Xiaoyuan Liu', 'Rui Zhao' / 'Ruihan
# Zhao', 'Seunghak Lee' / 'Seung Hyun Lee' (2026-10-29 review of the guard's kept prefixes)
EAST_ASIAN_FAMILY = set('''an bai bao cai cao cen chai chan chang chao chen cheng cheung chiang chien chin chiu cho choi chou chu
chung cui dai deng ding dong du duan fan fang feng fu gao ge geng gong gu guan guo ha han hao he ho hong hou hsieh hsu hu hua
huang hwang hyun ji jia jiang jiao jin jang jeon jeong jung kang kim ko koo kong kwak kwon lai lam lan lau lee lei leung li lian
liang liao lim lin ling liu lo long lou lu luo lv lyu ma mao meng min moon mu nam ng ngo nguyen ni nie oh ou pan pang park peng
pham qi qian qin qiu ren ryu seo shao shen sheng shi shim shin si song su sun tan tang tao teng tian tran tsai tseng tung wan
wang wei wen wong woo wu xi xia xiang xiao xie xin xing xiong xu xue yan yang yao ye yeh yi yin yoo yoon you yu yuan yue yun
zeng zha zhai zhan zhang zhao zheng zhong zhou zhu zou zuo'''.split())


def strict_name_one(n):
    """(first given name as written, hyphen parts joined; family name), middle names ignored, nicknames mapped:
    'Jun-Yan Zhu' -> ('junyan', 'zhu') and 'Jun Zhu' -> ('jun', 'zhu') differ; 'Steven Michael Chase' and 'Steven M. Chase'
    agree; 'Chris Atkeson' and 'Christopher G. Atkeson' agree."""
    s = unicodedata.normalize('NFKD', str(n or '')); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'\([^)]*\)', ' ', s); s = re.sub(r'\s+\d{4}$', '', s.strip())
    w = [re.sub(r'[^a-z]', '', x) for x in s.replace(',', ' ').split()]; w = [x for x in w if x]
    if len(w) < 2:
        return (''.join(w), '')
    g = next((x for x in w[:-1] if len(x) > 1), w[0])
    return (given(g), w[-1])


def strict_name(n):
    return {strict_name_one(n)}


def _words(n):
    s = unicodedata.normalize('NFKD', str(n or '')); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'\([^)]*\)', ' ', s); s = re.sub(r'\s+\d{4}$', '', s.strip())
    return [w for w in (re.sub(r"[^a-z\-]", '', x) for x in s.replace(',', ' ').split()) if w.strip('-')]


def name_conflict(pi_names, dblp_name):
    """A DBLP person id is someone else when, for every name form of the PI, either the PI's family name is absent from the
    DBLP name (not even as an initial), or the PI's hyphenated given name ('Jun-Yan') has a part the DBLP name lacks
    ('Jun Zhu'). Middle names, extra given names ('Fatma Zeynep Temel'), initials ('K. V. Rashmi') and nicknames pass."""
    d = _words(dblp_name); dt = {x for w in d for x in w.split('-') if x} | {w.replace('-', '') for w in d}
    dt |= {given(x) for x in list(dt)}
    for n in pi_names:
        w = _words(n)
        if len(w) < 2:
            continue
        fam = w[-1].replace('-', '')
        fam_ok = fam in dt or any(x in dt for x in w[-1].split('-')) or (fam[:1] in dt) or \
            any(x.replace('-', '') in dt for x in w[1:-1] if len(x) > 2 and x not in ('de', 'la', 'del', 'van', 'von', 'der', 'den'))  # double surnames
        g = w[0]; parts = [x for x in g.split('-') if x]
        given_ok = (len(parts) < 2 or g.replace('-', '') in dt or all(x in dt for x in parts)) and (given(parts[0]) in dt or parts[0] in dt or parts[0][:1] in dt or len(parts[0]) == 1)
        if fam_ok and given_ok:
            return False
    return True


def norm_title(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()


SEASON = {'spring': ('01-01', '05-31'), 'summer': ('06-01', '08-31'), 'fall': ('08-01', '12-31'), 'autumn': ('08-01', '12-31')}


def datebounds(value):
    """A date's earliest and latest day. A reviewed value may carry a note after the date ('2020 (Fall)', '2022-12 (first
    dated observation; ...)'): the leading date counts, narrowed to the term when the note names a season."""
    value = str(value or '').strip()
    m = re.fullmatch(r'(\d{4}(?:-\d{2}){0,2})\s*\((.*)\)', value)
    if m:
        value = m.group(1); term = SEASON.get(m.group(2).strip().lower()) if len(value) == 4 else None
        if term:
            return f'{value}-{term[0]}', f'{value}-{term[1]}'
    if re.fullmatch(r'\d{4}', value):
        return value + '-01-01', value + '-12-31'
    if re.fullmatch(r'\d{4}-\d{2}', value):
        y, m = map(int, value.split('-')); return value + '-01', value + '-' + str(calendar.monthrange(y, m)[1])
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return value, value
    return None


def contains(start, end, date, asof=None):
    """The site's rule (reconcile-lab-identities-periods.py): every possible publication date fits the period."""
    sb = datebounds(start); eb = datebounds(end or asof); pb = datebounds(date)
    if not sb or not eb or not pb:
        return 'unresolved'
    lo, hi = pb; hi = min(hi, TODAY)
    if lo > hi:
        return 'unresolved'
    if hi < sb[0] or lo > eb[1]:
        return 'outside'
    return 'supported' if lo >= sb[1] and hi <= eb[0] else 'boundary_unresolved'


def same_year(date):
    b = datebounds(date)
    return int(b[0][:4]) if b and b[0][:4] == b[1][:4] else None


def source_year(s):
    m = re.search(r'/web/(\d{4})\d{4,10}', s.get('url') or '')
    if m:
        return int(m.group(1))
    o = str(s.get('observed') or s.get('observedAt') or s.get('date') or '')
    return int(o[:4]) if re.match(r'\d{4}', o) else None


def sweep_works(school):
    c = sqlite3.connect(f'file:{HERE}/hierarchy/{school}/openalex-sweep.sqlite?mode=ro', uri=True)
    for (body,) in c.execute('select body from pages order by year, page'):
        yield from json.loads(zlib.decompress(body))


NOT_FACULTY = re.compile(r'\b(ph\.?\s?d\.?\s+(student|candidate)|graduate student|doctoral (student|candidate)|master.?s student|'
                         r'post-?docs?|postdoctoral|post-doctoral)\b', re.I)
OTHER_INST = re.compile(r'univ|institut|college|polytechn|[ée]cole|laborator|\blabs?\b|\binc\b|corp|\bltd\b|gmbh|\bllc\b|hospital|academy|'
                        r'cent(?:er|re)\b|google|microsoft|\bmeta\b|amazon|\bibm\b|nvidia|openai|deepmind|foundation|\bcnrs\b|\binria\b|'
                        r'\beth\b|max planck|national|company', re.I)  # an affiliation string that names some institution, not a department
# the school's own units whose names hold an institution word (2026-10-29: CMU's 'Neuroscience Institute' had made the
# HALPER authorship of Andreas Pfenning read as another institution): a raw affiliation string made only of such unit
# names and department words names no other institution
OWN_UNITS = {'cmu': re.compile(r'\b(?:robotics|neuroscience|language technologies|human-computer interaction|software research|'
                               r'information networking|integrated innovation)\s+institute\b|\binstitute\s+for\s+software\s+research\b', re.I)}


def names_other_inst(z, school):
    u = OWN_UNITS.get(school)
    return bool(OTHER_INST.search(u.sub(' ', z) if u else z))


INCOMING = re.compile(r'\b(incoming|future faculty|will join|joining (?:us )?(?:in )?(?:the )?(?:fall|spring|summer|\d{4})|'
                      r'starting (?:in )?(?:(?:fall|spring|summer|autumn|january|july|september) )?\d{4}|arriving)\b', re.I)


def not_faculty_row(text):
    """A dated listing row that lists the person as a student or postdoc, not as faculty: it proves no appointment
    (the same-year listing rule is about faculty listings; directories such as CMU's SCS list students too). Nor does a
    row announcing a future appointment ('incoming', 'will join', 'starting 2025'): 'Acting' and other held titles count."""
    t = text or ''
    return bool(INCOMING.search(t)) or (bool(NOT_FACULTY.search(t)) and not re.search(r'professor|lecturer|faculty', t, re.I))


def basis_advisees(quote):
    """Students a PI's basis quote names as their Ph.D. advisees, with the year when the quote dates it: a DSpace record
    ('"dc.contributor.author" : [ { "value" : "Huang, Qingqing, Ph. D. Massachusetts ...'), an SCS thesis page
    ('Kirstin Early August 2017 Ph.D. Thesis'), or a Stanford Profiles advisee heading ('Doctoral Dissertation Advisor
    (AC) Edward Gan, Sahaana Suri'; co-advisor too, never readers or program advisers)."""
    q = quote or ''; out = []
    for m in re.finditer(r'dc\.contributor\.author"\s*:\s*\[\s*\{\s*"value"\s*:\s*"([^"]+)', q):
        v = re.sub(r'\s*\([^)]*\)', '', m.group(1)); v = re.split(r',\s*Ph\.?\s*D\b', v)[0].strip().rstrip('.')
        if ',' in v:
            last, first = [x.strip() for x in v.split(',', 1)]; v = f'{first} {last}'
        out.append((v, None))
    m = re.match(r'\s*([A-Z][\w.\'\- ]+?)\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+((?:19|20)\d\d)\s+Ph\.?\s*D\.?\s+Thesis', q)
    if m:
        out.append((m.group(1).strip(), int(m.group(2))))
    m = re.search(r'Doctoral Dissertation (?:Co-)?Advisor \(AC\)\s+(.+?)(?=\s+(?:Doctoral|Postdoctoral|Master|Undergraduate|Reader|Orals|Current)|\s*$)', q)
    if m:
        out += [(x.strip(), None) for x in m.group(1).split(',') if len(x.strip().split()) >= 2]
    return [(clean_person_name(a), y) for a, y in out if a]


def as_list(v):
    """An identity field as a list: census rows give a single DBLP/ORCID/OpenAlex id as a string, list() would split it into characters."""
    return [v] if isinstance(v, str) else list(v or [])


def build(school):
    out = HERE / 'hierarchy' / school
    cf = HERE / f'census/{school}-faculty-hierarchy.json'  # a school whose census path another chain owns (Berkeley) keeps its own
    census = read(cf if cf.exists() else HERE / f'census/{school}-faculty.json')
    census = census.get('faculty', census) if isinstance(census, dict) else census
    if (HERE / f'census/{school}-additions.json').exists():  # listed faculty the census missed (tools/listed_not_in_census.py)
        census = list(census) + read(HERE / f'census/{school}-additions.json')
    own_c = HERE / 'hierarchy' / school / 'collection.json.gz'  # a school without a site collection (Berkeley) brings its own
    C = read(own_c if own_c.exists() else SITE / f'collection-{school}.json.gz')
    people = C['people'] if isinstance(C['people'], list) else list(C['people'].values())
    Pid = {p['id']: p for p in people}; units = {u['id']: u for u in C['units']}; works = C['works']
    periods = list(C.get('facultyPeriods') or [])
    pf = HERE / f'periods/{school}-faculty-periods.json'
    if pf.exists():
        x = read(pf); periods += x if isinstance(x, list) else x.get('periods', [])
    inst = 'https://openalex.org/' + INST[school]; aff = re.compile(AFF[school], re.I)
    n = collections.Counter()

    # collection works by DOI and title
    by_doi, by_title = {}, collections.defaultdict(list)
    for wid, w in works.items():
        for d in [w.get('doi')] + [a for a in (w.get('aliases') or []) if str(a).startswith('10.') or 'doi.org' in str(a)]:
            if d:
                by_doi.setdefault(ndoi(d), wid)
        if w.get('title'):
            by_title[norm_title(w['title'])].append(wid)

    def cwork(oa):
        d = ndoi(oa.get('doi'))
        if d and d in by_doi:
            return by_doi[d]
        for wid in by_title.get(norm_title(oa.get('title')), []):
            y = works[wid].get('year')
            if not y or not oa.get('publication_year') or abs(int(str(y)[:4]) - oa['publication_year']) <= 1:
                return wid
        return None

    pls = collections.defaultdict(list)
    for l in C['personLinks']:
        pls[l['person']].append(l)

    # PIs
    yearly = collections.defaultdict(list)  # listings/<school>/listings.json: verified yearly department listings (one row per person-year)
    lf = HERE / 'listings' / school / 'listings.json'
    for r in (read(lf) if lf.exists() else []):
        if not r.get('future_start_note') and r.get('sha256') and r.get('quote'):
            yearly[r['pi']].append(r)
    ov = read(HERE / 'hierarchy/census-overrides.json').get(school, {}) if (HERE / 'hierarchy/census-overrides.json').exists() else {}
    ge = {r['pi']: r for r in read(HERE / 'hierarchy' / school / 'gap-evidence.json')} if (HERE / 'hierarchy' / school / 'gap-evidence.json').exists() else {}
    for pi_, r in ge.items():  # researched gap labs: status, identity, the PI's collection person
        o = ov.setdefault(pi_, {})
        if r.get('status') == 'not_pi_in_window' and r.get('status_evidence'):
            o.setdefault('exclude', True); o.setdefault('why', 'Researched: not a PI at the school in 2016-2026 (gap-evidence.json): ' + str(r.get('notes') or '')[:200])
        idn = r.get('identity') or {}
        o['openalex'] = list(o.get('openalex') or []) + [a if a.startswith('http') else 'https://openalex.org/' + a for a in idn.get('openalex') or []]
        o['orcid'] = as_list(o.get('orcid')) + as_list(idn.get('orcid'))
        o['dblp'] = as_list(o.get('dblp')) + as_list(idn.get('dblp'))
        if r.get('collection_person_id') and not o.get('collection_person_id'):
            o['collection_person_id'] = r['collection_person_id']
    pis = []
    dblp_of = lambda x: as_list(x.get('dblp'))
    merged, first, by_family, nick_merges = collections.defaultdict(list), {}, collections.defaultdict(list), []
    for x in census:  # census duplicate pairs (one person listed twice): same DBLP PID or same collection person
        if not (x.get('is_pi') or (ov.get(x['name']) or {}).get('is_pi')) or x.get('not_faculty'):  # a reviewed is_pi wins
            continue
        nk = 'name:' + ' '.join(toks(x['name']))  # spelling variants of one name ("O’Toole" / "O'Toole") are one person too
        k = next((first[q] for q in dblp_of(x) + [x.get('collection_person_id'), nk] if q and q in first), None)
        t = toks(x['name'])
        if not k and len(t) >= 2:  # "Dan Klein" / "Daniel Klein", "David A. Wagner" / "David Wagner": same family name, nickname-equal given name
            k = next((k_ for g_, k_ in by_family[t[-1]] if g_ == t[0] or nick_ok(g_, t[0])), None)
            if k:
                n['census_rows_merged_by_nickname'] += 1; nick_merges.append([merged[k][0]['name'], x['name']])
        k = k or x['name']
        for q in dblp_of(x) + [x.get('collection_person_id'), nk]:
            if q:
                first.setdefault(q, k)
        if len(t) >= 2:
            by_family[t[-1]].append((t[0], k))
        merged[k].append(x)
    excluded = []
    for group in merged.values():
        hit = next((ov[g['name']] for g in group if ov.get(g['name'], {}).get('exclude')), None)
        if hit:  # reviewed: no faculty appointment at the school in the window
            excluded.append(dict(pi=group[0]['name'], why=hit.get('why'))); continue
        x = dict(group[0]); x['aliases'] = list(dict.fromkeys(list(x.get('aliases') or []) + [g['name'] for g in group[1:]] + [a for g in group[1:] for a in g.get('aliases') or []]))
        x['sources'] = [s_ for g in group for s_ in g.get('sources') or []]; x['lab_units'] = [l for g in group for l in g.get('lab_units') or []]
        x['dblp'] = list(dict.fromkeys(q for g in group for q in dblp_of(g)))
        x['collection_person_id'] = next((g['collection_person_id'] for g in group if g.get('collection_person_id') in Pid), None)
        x['mergedCensusRows'] = [g['name'] for g in group[1:]]
        o = ov.get(x['name'], {})  # reviewed corrections: aliases, person, identity (hierarchy/census-overrides.json)
        if o.get('collection_person_id'):
            x['collection_person_id'] = o['collection_person_id']
        x['aliases'] = list(x.get('aliases') or []) + list(o.get('aliases') or [])
        x['dblp'] = list(dict.fromkeys(list(x['dblp']) + as_list(o.get('dblp'))))
        x['openalex'] = list(dict.fromkeys(as_list(x.get('openalex')) + as_list(o.get('openalex'))))
        x['orcid'] = list(dict.fromkeys(re.sub(r'^https?://orcid\.org/', '', z) for z in as_list(x.get('orcid')) + as_list(o.get('orcid'))))  # additions give one ORCID as a string
        ids = [i for i in [x.get('collection_person_id')] + list(x.get('collection_person_candidates') or []) if i and i in Pid][:1]
        names = [x['name']] + list(x.get('aliases') or []) + [Pid[i]['name'] for i in ids]
        listings = {}
        for s in x.get('sources') or []:
            y = source_year(s); sur = toks(x['name'])[-1] if toks(x['name']) else ''
            if y and 2016 <= y <= 2026 and s.get('sha256') and s.get('quote') and sur and sur in ' '.join(toks(s['quote'])) and not not_faculty_row(s['quote']):
                listings.setdefault(y, dict(url=s['url'], sha256=s['sha256'], quote=s['quote'], kind=s.get('kind') or '', year=y))
        for nm_ in [x['name']] + list(x.get('mergedCensusRows') or []):
            for r in yearly.get(nm_, []):
                if not_faculty_row(r.get('rank_as_listed') or r.get('quote')):
                    n['listing_rows_not_faculty'] += 1; continue
                listings.setdefault(int(r['year']), dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], kind='dept_listing:' + (r.get('department') or ''),
                                                         year=int(r['year']), rank=r.get('rank_as_listed'), emeritus=r.get('emeritus'), visiting=r.get('visiting')))
        mine = [p for p in periods if p.get('personId') in ids or Name([p.get('name') or '']).match(x['name'])]
        # a listing after an evidenced departure is a stale page, not an appointment (2026-10-29): Princeton ECE kept Mung
        # Chiang (left 2017) and Yuxin Chen (left 2021) on its faculty list through 2026; kept aside as listingsAfterMove.
        # A later period (collection or reviewed) that covers the year keeps the listing.
        yr = lambda v: int(str(v)[:4]) if str(v or '')[:4].isdigit() else None
        moved = [yr(q['facultyEnd']) for q in mine if yr(q.get('facultyEnd')) and any('end_moved' in (e.get('kind') or '') for e in q.get('evidence') or [])]
        spans = [(yr(q.get('facultyStart')), yr(q.get('facultyEnd'))) for q in mine] + [(yr(q.get('start')), yr(q.get('end'))) for q in o.get('periods') or []]
        covered = lambda y: any(s and s <= y and (e is None or y <= e) for s, e in spans)
        after_move = {y: l for y, l in listings.items() if moved and y > max(moved) and not covered(y)}
        n['listing_years_after_move'] += len(after_move)
        lab = None
        collective = lambda nm_: bool(COLLECTIVE.search(nm_ or '')) and not re.search(r'\b(lab|laboratory|group)\b', nm_ or '', re.I)
        for lu in x.get('lab_units') or []:
            if isinstance(lu, str) and lu in units:
                u = units[lu]; leaders = [l if isinstance(l, str) else l.get('person') or l.get('id') or l.get('name') for l in u.get('leaders') or []]
                if len(leaders) == 1 and not collective(u['name']) and (leaders[0] in ids or Name(names).match(Pid[leaders[0]]['name'] if leaders[0] in Pid else leaders[0])):
                    lab = dict(unitId=lu, name=u['name'], basis='single_leader_unit'); break
        if lab is None:
            prop = next((lu for lu in x.get('lab_units') or [] if isinstance(lu, dict) and not collective(lu.get('name'))), None)
            lab = dict(unitId=None, name=(prop or {}).get('name') or f"{x['name']} group", url=(prop or {}).get('url') or x.get('profile_url'),
                       basis='new_own_lab', evidence=(prop or {}).get('evidence') or x.get('pi_basis'),
                       collectives=[lu for lu in x.get('lab_units') or [] if isinstance(lu, str)])
        pis.append(dict(pi=x['name'], personIds=ids, names=list(dict.fromkeys(names)), dblp=x['dblp'], reviewedOpenAlex=x['openalex'], orcid=x['orcid'],
                        notOpenAlex=list(o.get('not_openalex') or []),  # reviewed namesake author ids: never this PI
                        # reviewed mixed author ids (2026-10-29): OpenAlex records of another person that also hold some of the
                        # PI's works (Song Mei's Berkeley papers sit in five Chinese namesakes' records); such an id neither
                        # anchors nor blocks: each of its authorships needs per-work evidence (DBLP page, ORCID, advisee)
                        mixedOpenAlex=list(o.get('mixed_openalex') or []),
                        mergedCensusRows=x['mergedCensusRows'], rank=x.get('rank'), title=x.get('title_as_listed'),
                        departments=x.get('departments') or x.get('units') or [], piBasis=o.get('pi_basis') or x.get('pi_basis'), lab=lab,  # a reviewed basis (census-overrides.json) wins
                        periods=[dict(id=p.get('id'), start=p.get('facultyStart'), end=p.get('facultyEnd'), asof=p.get('ongoingAsOf') or p.get('facultyLastConfirmed'),
                                      evidence=(p.get('evidence') or [])[:2]) for p in mine]
                                + [dict(q, asof=q.get('asof') or (None if q.get('end') else TODAY)) for q in o.get('periods') or []],  # reviewed periods (census-overrides.json)
                        listings=[listings[y] for y in sorted(listings) if y not in after_move],
                        listingsAfterMove=[after_move[y] for y in sorted(after_move)]))
    n['pis_excluded_by_review'] = len(excluded)
    n['pis'] = len(pis); n['pis_without_person'] = sum(not p['personIds'] for p in pis)
    n['labs_reused'] = sum(p['lab']['unitId'] is not None for p in pis); n['labs_new'] = n['pis'] - n['labs_reused']

    pid0 = {p['pi']: p for p in pis}
    by_unit = collections.defaultdict(list)
    for p in pis:
        if p['lab']['unitId']:
            by_unit[p['lab']['unitId']].append(p['pi'])
    nm = {p['pi']: Name(p['names']) for p in pis}
    by_sur = collections.defaultdict(list)
    for p in pis:
        for f, l in nm[p['pi']].forms:
            by_sur[l].append(p['pi'])

    # an adviser field names a PI by full given name only through the PI's full-name forms (an 'H. Balakrishnan' alias of
    # Hamsa must not take 'Balakrishnan, Hari' theses, 2026-10-28); an initials-only field goes to no PI when another PI of
    # the school shares that family name and initial
    nm_full = {p['pi']: Name([x for x in p['names'] if len((toks(x) or [''])[0]) > 1] or p['names']) for p in pis}

    def adviser_is(pi, a):
        t_ = toks(a)
        if not t_:
            return False
        if len(t_[0]) > 1:
            return nm_full[pi].match(a)
        return nm[pi].match(a) and not any(q != pi and nm[q].match(a) for q in by_sur.get(t_[-1], []))

    # students: advising contexts naming the PI, and memberships of a reused unit
    stu = collections.defaultdict(dict)
    for person in people:
        for c in person.get('contexts') or []:
            t = c.get('type') or ''
            if 'advis' in t:
                advs = [c.get('advisorName') or c.get('advisor')] + list(c.get('advisors') or [])
                for s_ in c.get('sources') or []:  # adviser fields written in the quote (rosters, alumni pages, FPO announcements)
                    for rx in ADV_RX:  # senior-thesis advising counts for students (never for PI status, which the census decides)
                        for m_ in rx.finditer(s_.get('quote') or ''):
                            g = m_.group(1).strip()
                            if re.fullmatch(r"[^,]{2,40}, [^,]{2,40}", g) and all(len(toks(z)) <= 2 for z in g.split(',')):
                                advs.append(g)  # "Kernighan, Brian": one name, family name first
                            else:
                                advs += [x.strip() for x in re.split(r',| and ', g) if x.strip()]
                ids_ = {c.get('advisorPersonId'), c.get('advisorPerson'), c.get('advisorSuggestedPersonId')} - {None}
                cand = {q for a in advs if a for t_ in [toks(a)] if t_ for q in by_sur.get(t_[-1], []) + by_sur.get(''.join(t_[1:]), []) + by_sur.get(t_[0], [])}  # one-word advisers too ("Arvind.")
                cand |= {p['pi'] for p in pis if ids_ & set(p['personIds'])} | set(by_unit.get(c.get('unit'), []))
                for p in (pid0[q] for q in cand):
                    if person['id'] in p['personIds']:
                        continue
                    if ids_ & set(p['personIds']) or any(a and adviser_is(p['pi'], a) for a in advs) or (c.get('unit') and c.get('unit') == p['lab']['unitId'] and t == 'academic_advising'):
                        r = stu[p['pi']].setdefault(person['id'], dict(person=person['id'], name=person['name'], roles=person.get('roles') or [], relations=[]))
                        r['relations'].append(dict(type=t, years=c.get('years') or ([c['year']] if c.get('year') else []), role=c.get('role'),
                                                   sources=(c.get('sources') or [])[:2], work=c.get('work')))
            elif t == 'direct_lab_membership':
                for p in pis:
                    if p['lab']['unitId'] and c.get('unit') == p['lab']['unitId'] and person['id'] not in p['personIds']:
                        r = stu[p['pi']].setdefault(person['id'], dict(person=person['id'], name=person['name'], roles=person.get('roles') or [], relations=[]))
                        r['relations'].append(dict(type=t, years=c.get('years') or ([c['year']] if c.get('year') else []), role=c.get('role'), sources=(c.get('sources') or [])[:2]))
    by_name = collections.defaultdict(list)
    for person in people:
        for t_ in [toks(person['name'])]:
            if len(t_) >= 2:
                by_name[t_[-1]].append(person)
    fe = collections.defaultdict(lambda: dict(students=[]))  # researched students: thin labs and the thesis hunt
    for fn in ('few-students-evidence.json', 'thesis-evidence.json', 'labpage-evidence.json',
               'thesis-held-years-evidence.json'):
        if (HERE / 'hierarchy' / school / fn).exists():
            for r in read(HERE / 'hierarchy' / school / fn):
                fe[r['pi']]['students'] = list(fe[r['pi']]['students']) + list(r.get('students') or [])
    for p in pis:  # researched students (gap-evidence.json, few-students-evidence.json): a stated advisee or lab member, with its quote
        for s_ in list((ge.get(p['pi']) or {}).get('students') or []) + list((fe.get(p['pi']) or {}).get('students') or []):
            if not (s_.get('name') and s_.get('quote') and s_.get('sha256')):
                continue
            t_ = toks(s_['name']); nm_ = Name([s_['name']])
            match_ = [q for q in by_name.get(t_[-1] if t_ else '', []) if nm_.match(q['name'])]
            sid = match_[0]['id'] if len(match_) == 1 else f"ext:{school}:{re.sub('[^a-z0-9]+', '-', s_['name'].lower()).strip('-')}"
            r = stu[p['pi']].setdefault(sid, dict(person=sid, name=match_[0]['name'] if len(match_) == 1 else s_['name'], roles=[s_.get('role') or 'student'], relations=[]))
            r['relations'].append(dict(type='researched_' + ('membership' if s_.get('role') == 'member' else 'advising'), years=[y for y in (s_.get('years') or []) if y],
                                       role=s_.get('role'), sources=[dict(url=s_.get('capture_url') or s_['url'], sha256=s_['sha256'], quote=s_['quote'])]))
    for p in pis:  # advisees named in the PI's own reviewed basis quote (census-overrides.json pi_basis, kind advises_phd)
        b = p.get('piBasis') or {}
        if b.get('kind') != 'advises_phd' or not (b.get('quote') and b.get('sha256')):
            continue
        for sname, yr in basis_advisees(b['quote']):  # not 'nm': that is the PI name table
            t_ = toks(sname); nm_ = Name([sname])
            match_ = [q for q in by_name.get(t_[-1] if t_ else '', []) if nm_.match(q['name'])]
            sid = match_[0]['id'] if len(match_) == 1 else f"ext:{school}:{re.sub('[^a-z0-9]+', '-', sname.lower()).strip('-')}"
            r = stu[p['pi']].setdefault(sid, dict(person=sid, name=match_[0]['name'] if len(match_) == 1 else sname, roles=['phd'], relations=[]))
            r['relations'].append(dict(type='pi_basis_advising', years=[y for y in (yr or source_year(b),) if y], role='phd',
                                       sources=[dict(url=b['url'], sha256=b['sha256'], quote=b['quote'])]))
            n['pi_basis_advisees'] += 1
    merged_students = 0
    for p in pis:  # one record per student and lab: nickname or spelling variants ("Liv" / "Olivia d'Aliberti") merge
        for r in stu[p['pi']].values():
            fixed = clean_person_name(r['name'])
            if fixed != r['name']:
                r.setdefault('aliases', []).append(r['name']); r['name'] = fixed; n['student_names_cleaned'] += 1
        recs = list(stu[p['pi']].values())
        recs.sort(key=lambda r: (str(r['person']).startswith('ext:'), -len(r['relations'])))  # a collection person wins
        keep = []
        for r in recs:
            tgt = next((k for k in keep if Name([k['name']] + k.get('aliases', [])).match(r['name']) or Name([r['name']]).match(k['name'])
                        or any(same_student(r['name'], q) for q in [k['name']] + k.get('aliases', []))), None)
            if tgt is None:
                keep.append(r)
            else:
                tgt['relations'] += r['relations']; tgt.setdefault('aliases', []).append(r['name']); tgt.setdefault('merged', []).append(r['person']); merged_students += 1
        stu[p['pi']] = {r['person']: r for r in keep}
    # reviewed identities (hierarchy/student-identity-review.json, from the same-name research): two records of one lab
    # that are one person merge under the canonical name; 'different_people' verdicts only feed the chain audit
    rev = read(HERE / 'hierarchy/student-identity-review.json') if (HERE / 'hierarchy/student-identity-review.json').exists() else []
    for x in rev:
        if x.get('school') != school or x.get('verdict') != 'same_person' or x.get('pi') not in stu:
            continue
        S = stu[x['pi']]
        find = lambda i: next((k for k, r in S.items() if k == i or i in (r.get('merged') or [])), None)
        a, b = find(x['a'][0]), find(x['b'][0])
        if not a or not b or a == b:
            continue
        keep_, drop_ = (a, b) if str(b).startswith('ext:') or not str(a).startswith('ext:') else (b, a)
        k, d = S[keep_], S.pop(drop_)
        k['relations'] += d['relations']; k.setdefault('aliases', []).extend([k['name'], d['name']] + list(d.get('aliases') or []))
        k.setdefault('merged', []).extend([d['person']] + list(d.get('merged') or []))
        k['name'] = x.get('canonical_name') or k['name']; k['aliases'] = [s for s in dict.fromkeys(k['aliases']) if s != k['name']]
        k.setdefault('identityReview', []).append(dict(merged=d['person'], reason=x.get('reason'), evidence=x.get('evidence')))
        merged_students += 1
    # reviewed record corrections (hierarchy/student-corrections.json): drop a misplaced student from a lab, rename a
    # record keyed to the wrong person (the old name stays an alias), or replace a relation's mis-cut evidence
    corr = read(HERE / 'hierarchy/student-corrections.json') if (HERE / 'hierarchy/student-corrections.json').exists() else []
    for x in corr:
        S = stu.get(x.get('pi')) if x.get('school') == school else None
        k = next((k for k, r in (S or {}).items() if k == x['student'] or x['student'] in (r.get('merged') or [])), None)
        if not k:
            continue
        r = S[k]
        if x['action'] == 'drop':
            S.pop(k)
        elif x['action'] == 'rename':
            r.setdefault('aliases', []).append(r['name']); r['name'] = x['name']
            if x.get('person'):
                r.setdefault('merged', []).append(k); r['person'] = x['person']; S[x['person']] = S.pop(k)
        elif x['action'] == 'replace_sources':
            r['relations'] = [dict(type=x.get('type', 'researched_advising'), years=x['years'], role=x.get('role'), sources=x['sources'])]
        r.setdefault('corrections', []).append(dict(action=x['action'], reason=x['reason'], evidence=x.get('evidence')))
        n['student_corrections_' + x['action']] += 1
    n['student_records_merged'] = merged_students
    # the PI is not their own student (2026-10-29): lab rosters list their head ('Jim Glass' and 'John W. Fisher III' as
    # principal_investigator, 'Christos Faloutsos' as faculty). A record whose full first given name and family name are
    # the PI's own (nickname-equal, generational suffix ignored, initials never count) and that holds no student or
    # postdoc role is the PI; it leaves the lab's students (kept in the report as pisListedAsOwnStudent).
    def full_pair(nm_):
        t_ = nosuffix(toks(nm_))
        return (t_[0], t_[-1]) if len(t_) >= 2 and len(t_[0]) > 1 else None
    studentish = re.compile(r'phd|student|master|undergrad|postdoc|graduate|thesis|visitor|intern', re.I)
    self_listed = []
    for p in pis:
        own = {full_pair(x) for x in p['names']} - {None}
        for sid, r in list(stu[p['pi']].items()):
            fp = full_pair(r['name'])
            roles_ = [str(x) for x in list(r.get('roles') or []) + [rel.get('role') for rel in r['relations']] if x]
            if fp and any(fp[1] == o[1] and nick_ok(fp[0], o[0]) for o in own) and not any(studentish.search(x) for x in roles_):
                self_listed.append(dict(pi=p['pi'], student=sid, name=r['name'], roles=sorted(set(roles_))))
                del stu[p['pi']][sid]
    n['pi_listed_as_own_student_dropped'] = len(self_listed)
    # Across labs, a matching name alone does not make one person (owner 2026-10-27: merge name variants only within a
    # lab, under the same PI; AGENTS.md: consolidate alternate names only with explicit identity evidence). Records in
    # several labs share an id only when their sources already resolved to the same person record; same-name records
    # in other labs are counted here and listed by tools/student_audit.py (across_labs) as candidates for review.
    seen_names = collections.defaultdict(set)
    for p in pis:
        for r in stu[p['pi']].values():
            t_ = [x for x in toks(r['name']) if len(x) > 1]
            if len(t_) >= 2:
                seen_names[tuple(t_)].add(r['person'])
    n['student_same_name_other_labs_unmerged'] = sum(len(v) > 1 for v in seen_names.values())
    n['pis_with_students'] = sum(bool(stu[p['pi']]) for p in pis); n['students'] = len({s for v in stu.values() for s in v}); n['lab_student_pairs'] = sum(len(v) for v in stu.values())

    # identity anchors: the PI's own DBLP publication list, the PI's DBLP-verified collection works, a stated advisee as co-author
    verified = {p['pi']: {l['work'] for i in p['personIds'] for l in pls[i] if l.get('status') == 'verified' and l.get('role', 'author') == 'author'} for p in pis}
    dblp_doi, dblp_title = collections.defaultdict(set), collections.defaultdict(dict)
    dp = HERE.parent / DBLP.get(school, '') / 'raw/dblp_pubs.json.gz'
    if (HERE / 'hierarchy' / school / 'raw/dblp_pubs.json.gz').exists():  # Princeton: converted from the lab records' cached DBLP answers
        dp = HERE / 'hierarchy' / school / 'raw/dblp_pubs.json.gz'
    if dp.exists() and dp.name == 'dblp_pubs.json.gz' and (DBLP.get(school) or 'hierarchy' in str(dp)):
        pubs = read(dp)['pubs']
        by_dname = collections.defaultdict(set)  # a PI without a census DBLP id: the one DBLP person of exactly that name, if unique
        for rec in pubs.values():
            for q, dn in (rec.get('authors') or {}).items():
                if not re.search(r'\d{4}$', dn or ''):
                    by_dname[' '.join(toks(dn))].add(q)
        dname = collections.defaultdict(set)
        for rec in pubs.values():
            for q, dn in (rec.get('authors') or {}).items():
                dname[q].add(re.sub(r'\s+\d{4}$', '', dn or ''))
        n['dblp_ids_dropped_name_mismatch'] = 0
        for p in pis:  # a census DBLP id whose person never carries the PI's name is someone else's (e.g. 'Jun Zhu' for Jun-Yan Zhu)
            keep = [q for q in p['dblp'] if q not in dname or any(not name_conflict(p['names'], dn) for dn in dname[q])]
            if len(keep) < len(p['dblp']):
                n['dblp_ids_dropped_name_mismatch'] += len(p['dblp']) - len(keep); p['dblpDropped'] = sorted(set(p['dblp']) - set(keep)); p['dblp'] = keep
        for p in pis:
            if not p['dblp']:
                c_ = {q for n_ in p['names'] for q in by_dname.get(' '.join(toks(n_)), set())}
                if len(c_) == 1:
                    p['dblp'] = sorted(c_); p['dblpBasis'] = 'unique DBLP person of that exact name among the cached publication co-authors'
        owner = collections.defaultdict(list)
        for p in pis:
            for q in p['dblp']:
                owner[q].append(p['pi'])
        for rec in pubs.values():
            for q in rec.get('authors') or {}:
                for pi in owner.get(q, []):
                    if rec.get('doi'):
                        dblp_doi[pi].add(ndoi(rec['doi']))
                    dblp_title[pi][norm_title(rec.get('title', '').rstrip('.'))] = rec.get('year')
    # the PI's full DBLP person page from DBLP's own dump (tools/dblp_dump_persons.py -> hierarchy/dblp-dump-persons.json.gz;
    # 2026-10-29): the cached lists above hold only what the census queries returned, so a PI found as a co-author there
    # (Song Mei: 13 of 96 records) or added to the census later had a partial or empty list. Every record of the PI's
    # DBLP person anchors identity by DOI or title, as the cached lists do; a PI still without a DBLP id takes the one
    # person record of exactly that name in the dump when no other record carries the name (no homonyms); a census id
    # whose dump names never carry the PI's name is dropped as with the cached lists. ORCIDs on the person record (DBLP's
    # curated person links) join the PI's ORCIDs.
    dd_f = HERE / 'hierarchy' / 'dblp-dump-persons.json.gz'
    if dd_f.exists():
        global DUMP_PERSONS
        if DUMP_PERSONS is None:
            DUMP_PERSONS = read(dd_f)
        DP, DN = DUMP_PERSONS['persons'], DUMP_PERSONS['by_name']
        for p in pis:
            keep = [q for q in p['dblp'] if q not in DP or any(not name_conflict(p['names'], re.sub(r'\s+\d{4}$', '', dn)) for dn in DP[q]['names'])]
            if len(keep) < len(p['dblp']):
                n['dblp_ids_dropped_name_mismatch'] += len(p['dblp']) - len(keep)
                p['dblpDropped'] = sorted(set(p.get('dblpDropped') or []) | (set(p['dblp']) - set(keep))); p['dblp'] = keep
            if not p['dblp']:
                c_ = {q for n_ in p['names'] for q in DN.get(' '.join(toks(n_)), [])}
                if len(c_) == 1 and not any(DP[q].get('disambiguation') for q in c_):
                    p['dblp'] = sorted(c_); p['dblpBasis'] = 'unique DBLP person of that exact name in the DBLP dump'; n['dblp_ids_from_dump_name'] += 1
            for q in p['dblp']:
                rec_ = DP.get(q)
                if not rec_:
                    continue
                k0 = len(dblp_title[p['pi']])
                for r_ in rec_['pubs']:
                    for d_ in r_.get('dois') or []:
                        dblp_doi[p['pi']].add(ndoi(d_))
                    t_ = norm_title(html.unescape(r_.get('title') or '').rstrip('.'))
                    if t_:
                        dblp_title[p['pi']].setdefault(t_, r_.get('year'))
                n['dblp_dump_titles_added'] += len(dblp_title[p['pi']]) - k0
                new_orcid = [o_ for o_ in rec_.get('orcid') or [] if o_ not in p['orcid']]
                if new_orcid:
                    p['orcid'] = list(p['orcid']) + new_orcid; p['orcidFromDblp'] = new_orcid; n['pis_orcid_from_dblp'] += 1
    n['pis_with_dblp_list'] = sum(bool(dblp_title[p['pi']]) for p in pis)
    own_list = collections.defaultdict(dict)  # the PI's own institutional publication list (hierarchy/<school>/pi-publication-lists.json)
    pl_f = HERE / 'hierarchy' / school / 'pi-publication-lists.json'
    for pi_, rows_ in (read(pl_f) if pl_f.exists() else {}).items():
        for r_ in rows_:
            own_list[pi_][norm_title(r_['title'])] = r_.get('year')
    n['pis_with_own_publication_list'] = sum(bool(own_list[p['pi']]) for p in pis)
    lab_page = collections.defaultdict(list)  # the lab's own publications page (labpage-pubs.jsonl.gz): citation strings, title inside
    lp_f = HERE / 'hierarchy' / school / 'labpage-pubs.jsonl.gz'
    for line in (gzip.open(lp_f, 'rt') if lp_f.exists() else []):
        r_ = json.loads(line)
        if r_.get('sha256') and r_.get('quote'):
            lab_page[r_['pi']].append((norm_title(r_.get('title')), r_.get('year')))
    n['pis_with_lab_publication_page'] = sum(bool(lab_page[p['pi']]) for p in pis)
    advisee_names = {p['pi']: [Name([s_['name']]) for s_ in stu[p['pi']].values()] for p in pis}
    adv_full = {p['pi']: {fp_ for s_ in stu[p['pi']].values() for nm_ in [s_['name']] + list(s_.get('aliases') or []) for fp_ in [full_pair(clean_person_name(nm_))] if fp_} for p in pis}

    def identity_of(pi, w, a, cw):
        if (a.get('author') or {}).get('id') in blocked[pi]:
            return None
        if (a.get('author') or {}).get('id') in reviewed_oa[pi]:
            return 'reviewed_openalex_author_id'
        if re.sub(r'^https?://orcid\.org/', '', (a.get('author') or {}).get('orcid') or '') in orcids[pi]:
            return 'pi_orcid'
        if cw and cw in verified[pi]:
            return 'dblp_verified_collection_work'
        if ndoi(w.get('doi')) in dblp_doi[pi]:
            return 'dblp_person_page_doi'
        y = dblp_title[pi].get(norm_title(w.get('title')))
        if y is not None and (not y or not w.get('publication_year') or abs(int(y) - w['publication_year']) <= 1):
            return 'dblp_person_page_title'
        y = own_list[pi].get(norm_title(w.get('title')), -1)
        if y != -1 and (not y or not w.get('publication_year') or abs(int(y) - w['publication_year']) <= 1):
            return 'pi_institutional_publication_list'
        t_ = norm_title(w.get('title'))
        if len(t_) >= 30 and any(t_ in c_ and (not y_ or not w.get('publication_year') or abs(int(y_) - w['publication_year']) <= 1) for c_, y_ in lab_page[pi]):
            return 'lab_publication_page'  # the title inside a citation the PI's lab lists (title, authors, venue run together)
        others = [(x.get('raw_author_name') or (x.get('author') or {}).get('display_name') or '') for x in w.get('authorships') or [] if x is not a]
        # two initials prove nothing (2026-10-29: 'M. Wang' with 'J. Zhang' on EAST plasma papers made a Hefei M. Wang
        # Mengdi Wang's, and 'Y. L. Chen' with 'H. Hu' a Nanjing Y. L. Chen Yuxin Chen's): the PI or the advisee must be
        # written with a full given name
        def full(x):
            t_ = nosuffix(toks(byline_name(x)))
            return len(t_) >= 2 and len(t_[0]) > 1
        pi_full = full(a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or '')
        if any(an.match(o) and (pi_full or full(o)) for an in advisee_names[pi] for o in others):
            return 'advisee_coauthor'
        return None

    surname_only = []
    anchored = collections.defaultdict(collections.Counter)
    via_advisee = collections.defaultdict(collections.Counter)  # an author id on 2+ works the PI wrote with their own advisees anchors too
    reviewed_oa = {p['pi']: set(p.get('reviewedOpenAlex') or []) for p in pis}
    orcids = {p['pi']: set(p.get('orcid') or []) for p in pis}
    blocked = {p['pi']: set(p.get('notOpenAlex') or []) - set(p.get('mixedOpenAlex') or []) for p in pis}
    mixed = {p['pi']: set(p.get('mixedOpenAlex') or []) for p in pis}
    # another PI's reviewed author id is never this PI's (2026-10-28: S. Simon Wong's advisees co-wrote with H.-S. Philip
    # Wong, so the advisee rule anchored Philip Wong's reviewed id to Simon Wong through the 'S.' in 'H.-S.')
    all_reviewed = collections.Counter(a for s_ in reviewed_oa.values() for a in s_)
    for p in pis:
        blocked[p['pi']] |= {a for a in all_reviewed if a not in reviewed_oa[p['pi']]}
    n['other_pi_reviewed_ids_blocked'] = sum(len(v) for v in blocked.values())
    hits = []  # (pi, oa work, authorship, collection work, identity)
    for w in sweep_works(school):
        if w.get('type') in NOT_PAPERS:  # datasets, peer reviews, errata, supplements: not papers
            continue
        cw = None; done = set()
        for a in w.get('authorships') or []:
            raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
            t = nosuffix(toks(raw))  # "John Fisher III" is looked up under Fisher
            if len(t) < 2:
                continue
            for pi in set(by_sur.get(t[-1], []) + by_sur.get(''.join(t[1:]), []) + by_sur.get(t[0], [])):
                if pi in done:
                    continue
                if not nm[pi].match(raw):
                    if (a.get('author') or {}).get('id'):  # "Zhiwei Steven Wu" for Steven Wu: decided once the PI's ids are anchored
                        surname_only.append((pi, w, a))
                    continue
                if cw is None:
                    cw = cwork(w) or ''
                done.add(pi)
                ident = identity_of(pi, w, a, cw)
                if (a.get('author') or {}).get('id') in mixed[pi]:
                    pass  # a mixed record never anchors
                elif ident and ident != 'advisee_coauthor' and (a.get('author') or {}).get('id'):
                    anchored[pi][a['author']['id']] += 1
                elif ident == 'advisee_coauthor' and (a.get('author') or {}).get('id'):
                    via_advisee[pi][a['author']['id']] += 1
                hits.append((pi, w, a, cw or None, ident, None))
    for pi, c in via_advisee.items():
        for aid, k in c.items():
            if k >= 2:
                anchored[pi][aid] += 0.5  # weaker than a DBLP- or review-anchored id; recorded apart in the identity label
    n['sweep_name_hits'] = len(hits)
    seen_pw = {(h[0], h[1]['id']) for h in hits}
    for pi, w, a in surname_only:  # the same surname under an author id anchored (or reviewed) for this PI
        aid = a['author']['id']
        if (pi, w['id']) in seen_pw or aid in blocked[pi] or not (anchored[pi].get(aid, 0) >= 1 or aid in reviewed_oa[pi]):
            continue
        seen_pw.add((pi, w['id'])); hits.append((pi, w, a, cwork(w) or None, 'reviewed_openalex_author_id' if aid in reviewed_oa[pi] else 'anchored_author_id', None))
        n['surname_only_hits_by_anchored_id'] += 1
    # the PI's own works outside the sweep (hierarchy/<school>/pi-works.sqlite, tools/pi_fulltext_affiliation.py): an
    # authorship with no recorded institution whose page 1 ties the school to the PI, and works over the sweep's author cap
    pw = HERE / 'hierarchy' / school / 'pi-works.sqlite'
    tied, from_pw = {}, set()
    if pw.exists():
        con = sqlite3.connect(f'file:{pw}?mode=ro', uri=True)
        tied = {r[0]: dict(json.loads(r[1]), url=r[2], pdf_sha256=r[3]) for r in con.execute('select work, quote, url, pdf_sha256 from pages where school_named=1')}
        in_sweep = {h[1]['id'] for h in hits}
        owner = collections.defaultdict(list)
        for p in pis:
            for a_ in set(anchored[p['pi']]) | reviewed_oa[p['pi']]:
                owner[a_].append(p['pi'])
        k0 = len(hits)
        for (b_,) in con.execute('select body from works'):
            w = json.loads(zlib.decompress(b_))
            if w['id'] in in_sweep or w.get('type') in NOT_PAPERS:
                continue
            for a in w.get('authorships') or []:
                aid = (a.get('author') or {}).get('id')
                for pi in owner.get(aid, []):
                    raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
                    if aid in blocked[pi] or not nm[pi].match(raw):
                        continue
                    ident = 'reviewed_openalex_author_id' if aid in reviewed_oa[pi] else ('anchored_author_id' if anchored[pi][aid] >= 1 else 'advisee_anchored_author_id')
                    hits.append((pi, w, a, cwork(w), ident, tied.get(w['id']))); from_pw.add((pi, w['id']))
        n['pi_work_list_hits'] = len(hits) - k0
    funnel = collections.defaultdict(collections.Counter)

    # lab papers
    rows, seen, row_at = [], set(), {}
    for pi, w, a, cw, ident, page1 in hits:
        p = pid0[pi]
        via = [i.get('display_name') for i in a.get('institutions') or [] if inst == i.get('id') or inst in (i.get('lineage') or [])] \
            + ['text: ' + z for z in a.get('raw_affiliation_strings') or [] if aff.search(z)]
        if page1 and not a.get('institutions') and not a.get('raw_affiliation_strings'):
            via = [f"page 1 ({page1['how']}): " + ' … '.join(page1['quotes'])]  # the paper's own first page ties the school to the PI
        elif not via and tied.get(w['id']) and any(toks(n_)[-1] in toks(' '.join(tied[w['id']]['quotes'])) for n_ in p['names'] if toks(n_)):
            # a sweep work whose OpenAlex record gives the PI no school (none, a garbled footnote string, or a co-author's
            # institution misassigned by position) while the paper's own first page, read by tools/pi_fulltext_affiliation.py,
            # ties the school to this PI by name (2026-10-29: Chi Jin, Karthik Narasimhan, Adam Perer); the primary
            # source outranks OpenAlex's derived affiliation
            page1 = tied[w['id']]; via = [f"page 1 ({page1['how']}): " + ' … '.join(page1['quotes'])]
        if not via and not a.get('institutions') and not any(names_other_inst(z, school) for z in a.get('raw_affiliation_strings') or []):
            # the PI's authorship names no institution (none, or a department only, as recent preprints do) and a stated
            # advisee of the PI on the same byline lists the school: the paper is the lab's (identity and appointment still apply)
            co = [x.get('raw_author_name') for x in w.get('authorships') or [] if x is not a and x.get('raw_author_name')
                  and (inst in [i.get('id') for i in x.get('institutions') or []] + [l for i in x.get('institutions') or [] for l in i.get('lineage') or []]
                       or any(aff.search(z) for z in x.get('raw_affiliation_strings') or []))
                  and any(an.match(byline_name(x['raw_author_name'])) for an in advisee_names[pi])]
            if co:
                via = [f'advisee at the school on the byline: {co[0]}']; n['school_via_advisee_coauthor'] += 1
        if not via and (pi, w['id']) in from_pw and not any(x.get('institutions') or x.get('raw_affiliation_strings') for x in w.get('authorships') or []):
            # (2026-10-29, owner) a work of the PI's own (anchored or reviewed) OpenAlex id whose byline carries no
            # institution or affiliation at all (typically an arXiv record) is the lab's when a stated advisee of the PI
            # is on that byline by full name (first given name and family name written out); identity, the appointment
            # and the paper-type checks below still apply
            co = [x.get('raw_author_name') for x in w.get('authorships') or [] if x is not a and x.get('raw_author_name')
                  and full_pair(byline_name(x['raw_author_name'])) in adv_full[pi]]
            if co:
                via = [f'advisee on an unaffiliated byline: {co[0]}']; n['school_via_unaffiliated_byline_advisee'] += 1
        school_aff = bool(via)
        funnel[pi]['name_hits'] += 1
        if not school_aff:
            n['hit_without_school_affiliation'] += 1; continue
        funnel[pi]['school_affiliated'] += 1
        aid = (a.get('author') or {}).get('id')
        identity = None if aid in blocked[pi] else ident or (('anchored_author_id' if anchored[pi][aid] >= 1 else 'advisee_anchored_author_id') if aid and anchored[pi].get(aid) else None)
        if identity is None:
            n['hit_without_identity'] += 1; continue
        funnel[pi]['identity'] += 1
        date = w.get('publication_date') or str(w.get('publication_year') or '')
        per = next((q for q in p['periods'] if contains(q['start'], q['end'], date, q['asof'] or TODAY) == 'supported'), None)
        lst = None
        if per is None:
            y = same_year(date); lst = next((l for l in p['listings'] if l['year'] == y), None) if y else None
        if per is None and lst is None:
            n['outside_appointment'] += 1; funnel[pi]['outside_appointment_' + str(w.get('publication_year'))] += 1; continue
        funnel[pi]['in_appointment'] += 1
        k = (pi, cw or w['id'])
        if k in seen:
            # a second OpenAlex record of the same collection work (2026-10-29): kept as an edition of the row already
            # made, with its own byline, so the lab's students on it are seen (EPFL 'Lê-Nguyên, Hoang', CMU 'Cui, Catherine')
            if k in row_at and w['id'] != rows[row_at[k]]['oa']:
                rows[row_at[k]].setdefault('_dups', []).append(dict(
                    oa=w['id'], work=cw, doi=ndoi(w.get('doi')), year=w.get('publication_year'), venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
                    byline=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []],
                    byline_school=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []
                                   if inst in [i.get('id') for i in x.get('institutions') or []] + [l for i in x.get('institutions') or [] for l in i.get('lineage') or []]
                                   or any(aff.search(z) for z in x.get('raw_affiliation_strings') or [])]))
            continue
        seen.add(k); row_at[k] = len(rows)
        rows.append(dict(pi=pi, work=cw, oa=w['id'], doi=ndoi(w.get('doi')), title=w.get('title'), year=w.get('publication_year'), date=date, type=w.get('type'),
                         venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
                         landing=(w.get('primary_location') or {}).get('landing_page_url'),
                         byline=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []],
                         byline_school=[(x.get('raw_author_name') or (x.get('author') or {}).get('display_name')) for x in w.get('authorships') or []
                                        if inst in [i.get('id') for i in x.get('institutions') or []] + [l for i in x.get('institutions') or [] for l in i.get('lineage') or []]
                                        or any(aff.search(z) for z in x.get('raw_affiliation_strings') or [])],
                         authorship=dict(position=a.get('author_position'), raw_name=a.get('raw_author_name'), author_id=aid,
                                         institutions=[i.get('display_name') for i in a.get('institutions') or []], raw_affiliations=a.get('raw_affiliation_strings') or [],
                                         school_via=via[:3], page1=dict(url=page1['url'], pdf_sha256=page1['pdf_sha256'], how=page1['how'], quotes=page1['quotes']) if page1 and via[0].startswith('page 1') else None),
                         identity=identity, appointment=dict(periodId=per['id']) if per else dict(listing=lst)))
    # papers on the PI's own DBLP page that only DOI-resolved OpenAlex records or the paper's first page tie to the school
    # (tools/dblp_recover.py -> hierarchy/<school>/dblp-recovered.jsonl.gz), and likewise papers the PI's own lab
    # publications page lists (tools/labpage_recover.py -> hierarchy/<school>/labpage-recovered.jsonl.gz, key 'labpage:<sha1>')
    for kind, label in (('dblp', 'dblp_person_page'), ('labpage', 'labpage_listing')):
        rf = HERE / 'hierarchy' / school / f'{kind}-recovered.jsonl.gz'
        for x in (json.loads(l) for l in gzip.open(rf, 'rt')) if rf.exists() else []:
            p = pid0.get(x['pi'])
            if not p:
                continue
            ev = x['evidence']; date = str(x['year'])
            via = ev.get('school_via') or [f"page 1 ({ev.get('how')}): " + ' … '.join(ev.get('quotes') or [])]
            per = next((q for q in p['periods'] if contains(q['start'], q['end'], date, q['asof'] or TODAY) == 'supported'), None)
            lst = None if per else next((l for l in p['listings'] if l['year'] == int(x['year'])), None)
            if per is None and lst is None:
                n[f'{kind}_recovered_outside_appointment'] += 1; continue
            cw = cwork(dict(doi=x.get('doi'), title=(x.get('title') or '').rstrip('.'), publication_year=x['year'])) or None
            oa_id = ev.get('oa') or (f"https://dblp.org/rec/{x['dblp_key']}" if kind == 'dblp' else x['key'])
            if (x['pi'], cw or oa_id) in seen:
                continue
            seen.add((x['pi'], cw or oa_id))
            rows.append(dict(pi=x['pi'], work=cw, oa=oa_id, doi=x.get('doi'), title=(x.get('title') or '').rstrip('.'), year=x['year'], date=date, type='article',
                             venue=x.get('venue'), landing=ev.get('url'), byline=x.get('byline') or [], byline_school=[],
                             authorship=dict(position=None, raw_name=None, author_id=None, institutions=[], raw_affiliations=[], school_via=via[:3],
                                             page1=dict(url=ev.get('url'), pdf_sha256=ev.get('pdf_sha256'), how=ev.get('how'), quotes=ev.get('quotes')) if ev.get('how') else None),
                             identity=label, appointment=dict(periodId=per['id']) if per else dict(listing=lst), source=f'{kind}_recover:' + ev['basis']))
            n[f'{kind}_recovered_lab_papers'] += 1
    # namesake PIs (2026-10-28: Philip / Simon Wong, Hari / Hamsa Balakrishnan, Jean-Philippe / Patrick Thiran): when two
    # PIs claim one paper through the same byline name, the PI holding that author id as a reviewed id keeps it; else the
    # PI whose given names the byline spells out; a byline with initials only that no reviewed id settles goes to neither
    def given_words(names, raw=None):
        out = set()
        for nm_ in ([raw] if raw is not None else names):
            t_ = [w for w in re.split(r"[\s.\-]+", unicodedata.normalize('NFKD', str(nm_ or '')).encode('ascii', 'ignore').decode().lower().replace(',', ' ')) if w]
            if ',' in str(nm_):  # 'Wong, H. -S. Philip'
                t_ = t_[1:] + t_[:1]
            out |= {w for w in t_[:-1] if len(w) > 1}
        return out
    pi_given = {p['pi']: given_words(p.get('names') or [p['pi']]) for p in pis}
    claims = collections.defaultdict(list)
    for i, r in enumerate(rows):
        a = r.get('authorship') or {}
        if a.get('raw_name'):
            claims[(r['oa'], a['raw_name'].lower(), a.get('position'))].append(i)
    drop = set()
    for k, ix in claims.items():
        if len({rows[i]['pi'] for i in ix}) < 2:
            continue
        aid = (rows[ix[0]].get('authorship') or {}).get('author_id')
        owners = [i for i in ix if aid and aid in reviewed_oa[rows[i]['pi']]]
        if not owners:
            words = given_words(None, rows[ix[0]]['authorship']['raw_name'])
            owners = [i for i in ix if words and words <= pi_given[rows[i]['pi']]] if words else []
        if len({rows[i]['pi'] for i in owners}) != 1:
            owners = []
        drop |= set(ix) - set(owners)
    n['namesake_claims_dropped'] = len(drop)
    rows = [r for i, r in enumerate(rows) if i not in drop]
    # one record per unique paper and lab: editions (arXiv preprint, conference, journal version) share a normalized
    # title; the published edition leads (a DOI that is not arXiv's, then a collection work), the rest are its editions
    def rank(r):
        d = r.get('doi') or ''
        return (0 if d and not d.startswith('10.48550') else 1, 0 if r['work'] else 1, -(int(r['year'] or 0)))
    grouped = collections.defaultdict(list)
    for r in rows:
        grouped[(r['pi'], norm_title(r.get('title'))[:150] or r['oa'])].append(r)
    rows = []
    for g in grouped.values():
        g.sort(key=rank); lead = dict(g[0])
        dups = [d for x in g for d in x.get('_dups') or []]
        lead['editions'] = [dict(oa=x['oa'], work=x['work'], doi=x.get('doi'), year=x['year'], venue=x.get('venue')) for x in g[1:]] \
            + [{k_: d[k_] for k_ in ('oa', 'work', 'doi', 'year', 'venue')} for d in dups]
        # every edition's byline counts for the lab's students (2026-10-29): a lead record can carry a cut byline (Freedman's
        # 'Poor Video Streaming Performance Explained' lead names only him) or another name form than its preprint
        lead['_bylines'] = [(x['byline'], x['byline_school']) for x in g] + [(d['byline'], d['byline_school']) for d in dups]
        lead.pop('_dups', None)
        rows.append(lead)
    n['edition_records_merged'] = sum(len(g) - 1 for g in grouped.values())
    n['lab_papers'] = len(rows); n['lab_papers_in_collection'] = sum(bool(r['work']) for r in rows); n['lab_papers_new'] = n['lab_papers'] - n['lab_papers_in_collection']
    n['lab_papers_by_period'] = sum('periodId' in r['appointment'] for r in rows); n['lab_papers_by_listing'] = n['lab_papers'] - n['lab_papers_by_period']
    n.update({'identity:' + k: v for k, v in collections.Counter(r['identity'] for r in rows).items()})

    # student papers
    sp = []
    # every reading of a student's name: the name, its aliases, and parenthesized forms ('Fatma Imamoglu (Deniz)')
    forms = {sid: [f for f in dict.fromkeys([s['name']] + list(s.get('aliases') or []) + [v_ for x_ in [s['name']] + list(s.get('aliases') or []) for v_ in name_variants(x_)])
                   if '(' not in f] or [s['name']] for v in stu.values() for sid, s in v.items()}
    snm = {sid: [(Name([f]), toks(f)) for f in fs] for sid, fs in forms.items()}

    def on_byline(sid, b):
        return any(student_on_byline(nm_, tk_, b or '') for nm_, tk_ in snm[sid])

    def full_name_on(sid, b):
        """The byline spells the student's first given name and family name out in full (no initials)."""
        t = toks(byline_name(b))
        return len(t) >= 2 and any(len(tk_) >= 2 and len(tk_[0]) > 1 and t[0] == tk_[0] and t[-1] == tk_[-1] for _, tk_ in snm[sid])

    def wide_relation(s, year):
        """Two years before to six after the recorded advising: recorded years are often a single roster observation."""
        ys = [int(y) for rel in s.get('relations') or [] for y in rel.get('years') or [] if str(y).isdigit()]
        return not ys or not year or min(ys) - 2 <= int(year) <= max(ys) + 6
    # (2026-10-29, owner) every byline link passes a given-name guard: a byline whose first given name is a full word that
    # differs from every full given-name reading of the student is someone else ('Wei-Ning Chen' had been linked via
    # 'Wei-Chen Chen'). A middle name used as the preferred given name ('Xiang Lisa Li' / 'Lisa Li'), hyphen/space
    # variants ('Hong-Xing Yu' / 'Hongxing Yu'), nickname pairs and an order swap ('Zhang Wei') stay links.
    guard_n = collections.Counter()

    def gwords(x):
        """Name words with hyphenated parts joined ('Wei-Ning Chen' -> ['weining', 'chen']), accents and LETTERS folded."""
        x = byline_name(str(x or '').translate(LETTERS).replace('\u2013', '-').replace('\u2014', '-').replace('\u2010', '-'))
        x = unicodedata.normalize('NFKD', x); x = re.sub(r'\([^)]*\)', ' ', ''.join(c for c in x if not unicodedata.combining(c)).lower())
        w = [re.sub(r'[^a-z]', '', t) for t in re.split(r'[\s.]+', x.replace("'", ''))]
        return nosuffix([t for t in w if t])

    def given_conflict(sid, raw, strict=False):
        """The byline's first given name is a full word that no full-given-name reading of the student allows. Allowed:
        equal, a nickname pair, hyphen/space variants, a middle name used as the preferred name, the family name written
        first on either side, and (unless strict, the owner's literal guard) a 3+ letter prefix ('Avi'/'Avinash',
        'Gen'/'Gene'; not under an East Asian family name) or a one-letter spelling variant of a 4+ letter name ('Johann'/'Johan', 'Katherina'/'Katharina');
        'Wei-Ning' / 'Wei-Chen' differ by three letters and conflict."""
        bt = gwords(raw)
        if len(bt) < 2 or len(bt[0]) <= 1:
            return False
        for f in forms[sid]:
            st = gwords(clean_person_name(f))
            if len(st) < 2 or len(st[0]) <= 1:
                return False
            a, b = st[0], bt[0]
            if a == b or nick_ok(a, b) or nick_ok(b, a) or ''.join(st[:-1]) == ''.join(bt[:-1]) or b in st[1:-1] or a in bt[1:-1] \
                    or (bt[0] == st[-1] and bt[-1] == st[0]):  # family name first on either side ('Paiton Dylan' / 'Dylan M. Paiton')
                return False
            if not strict:
                x, y = sorted((a, b), key=len)
                if (len(x) >= 3 and y.startswith(x) and st[-1] not in EAST_ASIAN_FAMILY and bt[-1] not in EAST_ASIAN_FAMILY) \
                        or (len(x) >= 4 and one_edit(a, b)):
                    return False
        return True

    def byline_ok(sid, raw, how):
        return how(sid, raw) and not given_conflict(sid, raw)
    guard_samples, guard_kept_samples = [], []

    # (2026-10-29, owner) within-lab byline matching (the link_sweep.py measurement as a rule): a byline author who is
    # exactly one student of the lab by family name (the last token, or for a 3+ token student name the second-to-last,
    # a two-part family name the byline cuts: 'Bruno Schmitt Antunes' / 'Bruno Schmitt'; either half of a hyphenated
    # one; letters normalized with LETTERS) and given name (equal, an initial, a nickname pair, or the same letters
    # without hyphens); the order swap only for two-token names; family names of 2+ letters; within two years before to
    # six after the recorded years
    def sw_forms(t, student):
        if len(t) < 2:
            return []
        out = [(t[-1], t[0])]
        if len(t) == 2:
            out.append((t[0], t[1]))
        elif student:
            out.append((t[-2], t[0]))
        if '-' in t[-1]:
            out += [(q, t[0]) for q in t[-1].split('-')]
        return [(f.replace('-', ''), g) for f, g in out if len(f.replace('-', '')) >= 2]

    def sw_toks(x):
        x = unicodedata.normalize('NFKD', byline_name(str(x or '').translate(LETTERS)).replace('\u2013', '-').replace('\u2014', '-'))
        x = re.sub(r'\([^)]*\)', ' ', ''.join(c for c in x if not unicodedata.combining(c)).lower())
        return [t for t in re.split(r"[^a-z\-]+", x.replace("'", '')) if t and t not in ('jr', 'sr', 'ii', 'iii', 'iv', 'phd', 'dr')]

    def sw_given(a, b):
        a2, b2 = a.replace('-', ''), b.replace('-', '')
        return a2 == b2 or nick_ok(a2, b2) or (len(a2) == 1 and b2.startswith(a2)) or (len(b2) == 1 and a2.startswith(b2))

    sw_names = {sid: [sw_toks(clean_person_name(f)) for f in fs] for sid, fs in forms.items()}  # catalogue junk cleaned ('Li,M. Eng.Massachusetts ... Wang')
    sw_index = {}  # per lab: family-name reading -> students
    for pi_, S_ in stu.items():
        ix = collections.defaultdict(set)
        for sid in S_:
            for st in sw_names[sid]:
                for f_, _ in sw_forms(st, True):
                    ix[f_].add(sid)
        sw_index[pi_] = ix

    def sw_same(sid, bt):
        return any(f1 == f2 and sw_given(g1, g2) for st in sw_names[sid] for f1, g1 in sw_forms(st, True) for f2, g2 in sw_forms(bt, False))

    for r in rows:
        S = stu.get(r['pi']) or {}
        if not S:
            continue
        done_ = set(); linked_by_collection = {}
        for sid, s in S.items():
            l = next((l for l in pls[sid] if r['work'] and l['work'] == r['work']), None)
            if l:
                done_.add(sid); linked_by_collection[sid] = True
                sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status=l.get('status'), basis='collection_person_link'))
            elif any(byline_ok(sid, b, on_byline) for _, bs in r['_bylines'] for b in bs):
                # the student's name on this lab paper's byline, on an authorship that lists the school
                done_.add(sid); sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='byline_name_with_school_affiliation'))
            elif near_relation(s, r['year']) and any(byline_ok(sid, b, on_byline) for bl, _ in r['_bylines'] for b in bl):
                # the PI's own advisee named on the PI's lab paper (an authorship without affiliations, e.g. an ACL
                # Anthology record), within three years of the recorded advising
                done_.add(sid); sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='advisee_name_on_lab_paper_byline'))
            elif wide_relation(s, r['year']) and any(byline_ok(sid, b, full_name_on) for bl, _ in r['_bylines'] for b in bl):
                # the lab's own student by full name on the lab's own paper, outside the narrow window (2026-10-28:
                # recorded years are often one roster observation; alumni keep publishing with the lab)
                done_.add(sid); sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='full_name_on_lab_paper_byline'))
        for sid, s in S.items():  # links the guard took away (counted, with a sample, in the report)
            bl_all = [b for bl, _ in r['_bylines'] for b in bl]
            if sid in done_:
                used = [b for b in bl_all if on_byline(sid, b) or full_name_on(sid, b)]
                if not linked_by_collection.get(sid) and used and all(given_conflict(sid, b, strict=True) for b in used):
                    guard_n['kept_prefix_or_spelling_variant'] += 1  # the literal guard would have removed it
                    if len(guard_kept_samples) < 40:
                        guard_kept_samples.append(dict(pi=r['pi'], student=s['name'], byline=used[0], oa=r['oa']))
                continue
            unguarded = [b for _, bs in r['_bylines'] for b in bs if on_byline(sid, b)] \
                + ([b for b in bl_all if on_byline(sid, b)] if near_relation(s, r['year']) else []) \
                + ([b for b in bl_all if full_name_on(sid, b)] if wide_relation(s, r['year']) else [])
            if unguarded:
                b0 = unguarded[0]; hy = '-' in byline_name(b0).split(' ')[0] or any('-' in str(f).split(' ')[0] for f in forms[sid])
                guard_n['removed_' + ('hyphenated_given' if hy else 'different_full_given')] += 1
                if len(guard_samples) < 40:
                    guard_samples.append(dict(pi=r['pi'], student=s['name'], byline=b0, oa=r['oa']))
        for raw in dict.fromkeys(b for bl, _ in r['_bylines'] for b in bl):
            bt = sw_toks(raw)
            cand_ = {sid for f2, _ in sw_forms(bt, False) for sid in sw_index.get(r['pi'], {}).get(f2, ())}
            hits_ = [sid for sid in cand_ if sw_same(sid, bt)]
            if len(hits_) == 1 and hits_[0] not in done_ and wide_relation(S[hits_[0]], r['year']) and not given_conflict(hits_[0], raw):
                sid = hits_[0]; done_.add(sid)
                sp.append(dict(pi=r['pi'], student=sid, name=S[sid]['name'], work=r['work'], oa=r['oa'], status='candidate', basis='within_lab_byline_match', byline=raw))
    n.update({'link_guard_' + k: v for k, v in guard_n.items()})
    # Program advising and readers (owner 2026-10-28): a student whose only tie to the lab is a "Doctoral (Program)" or
    # "Reader" listing stays only when they co-authored one of the lab's papers; the dropped pairs are kept in the report
    linked = {(x['pi'], x['student']) for x in sp}
    weak_dropped = []
    for p in pis:
        for sid, s in list(stu[p['pi']].items()):
            if (p['pi'], sid) not in linked and s['relations'] and all(relation_is_weak(r, [s['name']] + list(s.get('aliases') or []))
                                                                       or relation_names_other_adviser(r, p.get('names') or [p['pi']]) for r in s['relations']):
                weak_dropped.append(dict(pi=p['pi'], student=sid, name=s['name'], roles=sorted({advising_label(q.get('quote'), [s['name']] + list(s.get('aliases') or [])) or r.get('role') or '' for r in s['relations'] for q in r.get('sources') or []})))
                del stu[p['pi']][sid]
    n['students_dropped_program_or_reader_only'] = len(weak_dropped)
    # recount after the drops: the counts taken when the students were gathered still held the dropped pairs
    n['pis_with_students'] = sum(bool(stu[p['pi']]) for p in pis); n['students'] = len({s for v in stu.values() for s in v})
    n['lab_student_pairs'] = sum(len(v) for v in stu.values())
    n['student_paper_links'] = len(sp); n['labs_with_student_papers'] = len({x['pi'] for x in sp})
    n.update({'student_link:' + k: v for k, v in collections.Counter(x['basis'] for x in sp).items()})

    per_pi = collections.Counter(r['pi'] for r in rows)
    for p in pis:
        p['oaAuthorIds'] = [a for a, _ in anchored[p['pi']].most_common()]
        p['funnel'] = dict(funnel[p['pi']], dblpTitles=len(dblp_title[p['pi']]), dblpDois=len(dblp_doi[p['pi']]), verifiedWorks=len(verified[p['pi']]))
        p['counts'] = dict(verifiedWorks=len(verified[p['pi']]), labPapers=per_pi[p['pi']], students=len(stu[p['pi']]),
                           studentPaperLinks=sum(1 for x in sp if x['pi'] == p['pi']))
    n['pis_with_lab_papers'] = sum(bool(per_pi[p['pi']]) for p in pis)
    n['pis_complete_chain'] = sum(bool(p['counts']['labPapers'] and p['counts']['students'] and p['counts']['studentPaperLinks']) for p in pis)
    json.dump(pis, open(out / 'pis.json', 'w'), indent=1, ensure_ascii=False)
    json.dump({k: list(v.values()) for k, v in stu.items()}, open(out / 'students.json', 'w'), indent=1, ensure_ascii=False)
    for r in rows:
        r.pop('_bylines', None)
    for name, data in (('lab_papers', rows), ('student_papers', sp)):
        with gzip.open(out / f'{name}.jsonl.gz', 'wt') as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    rep = dict(school=school, builtAt=datetime.datetime.utcnow().isoformat() + 'Z', counts=dict(n), excluded=excluded,
               pisWithoutPapers=sorted(p['pi'] for p in pis if not per_pi[p['pi']]),
               pisWithoutStudents=sorted(p['pi'] for p in pis if not stu[p['pi']]), censusNicknameMerges=nick_merges,
               droppedProgramOrReaderOnly=weak_dropped, pisListedAsOwnStudent=self_listed, linkGuardSamples=guard_samples,
               linkGuardKeptVariantSamples=guard_kept_samples)
    json.dump(rep, open(out / 'report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(dict(school=school, **n)))


if __name__ == '__main__':
    for s in sys.argv[1:]:
        build(s)
