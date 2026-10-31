"""Names: the readings of a person's name and the matchers every stage uses (toks, Name, nick_ok, byline_name, the
given-name guard). Rules: R-PAP-07 (all_initials), R-PAP-08 (nosuffix), R-STU-05 (dedupe_tokens), R-STU-06 (hyphen_half),
R-LNK-02/02a/02b (given_conflict, EAST_ASIAN_FAMILY), R-LNK-04/04a (the nickname tables)."""
import collections, html, re, unicodedata

import atlas_paths as P  # every path in one place

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
        fp = P.data('nicknames') / f
        if fp.exists():
            with open(fp) as fh:
                for r in csv.DictReader(fh):
                    if r.get('relationship') == 'has_nickname' and r.get('name1') and r.get('name2'):
                        pairs.add(frozenset((r['name1'].strip().lower(), r['name2'].strip().lower())))
    return pairs


NICK_MAP = None


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


def _fold(s):
    return unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()


def names_full_form(text, pi_names):
    """One of the PI's full-name forms (a full first given name; accents folded; 'Family, Given' too) occurs in text as a run
    of whole tokens."""
    t = ' '.join(toks(_fold(text))); raw = _fold(text)
    for n in pi_names:
        tk = toks(n)
        if len(tk) < 2 or len(tk[0]) < 2:
            continue
        if re.search(r'(?:^| )' + re.escape(' '.join(tk)) + r'(?: |$)', t) or f'{tk[-1]}, {tk[0]}' in raw:
            return True
    return False


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
    if hyphen_half(a, b) or hyphen_half(b, a):
        return True
    if ta[-1] != tb[-1]:
        return False
    x, y = sorted((ta[0], tb[0]), key=len)
    if nick_ok(x, y) or (len(x) >= 3 and y.startswith(x) and ta[1:-1] == tb[1:-1]):
        return True
    gx, gy = sorted((''.join(ta[:-1]), ''.join(tb[:-1])), key=len)  # 'Amir'/'Amirali Bagher', 'Kyutae'/'Kyu-Tae Thomas'
    return len(gx) >= 4 and gy.startswith(gx)


def hyphen_half(a, b):
    """(R-STU-06, 2026-10-29, owner: accuracy sample) b's family name is one half of a's hyphenated family name and their
    first given names agree (equal or a nickname pair): 'Pablo José Ortiz-Lampier' / 'Pablo Ortiz' (MIT, Harrell's lab
    held both). Used within one lab only."""
    wa = str(a or '').split(); tb = toks(b)
    if len(wa) < 2 or len(tb) < 2 or '-' not in wa[-1]:
        return False
    halves = [toks(x)[0] for x in wa[-1].split('-') if toks(x)]
    ta = toks(' '.join(wa[:-1]))
    return len(halves) >= 2 and tb[-1] in halves and bool(ta) and nick_ok(ta[0], tb[0]) and len(tb[0]) > 1


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


def full_pair(nm_):
    """(first given name, family name) when the first given name is written out (no initial), generational suffix dropped."""
    t_ = nosuffix(toks(nm_))
    return (t_[0], t_[-1]) if len(t_) >= 2 and len(t_[0]) > 1 else None


def all_initials(names, raw):
    """The byline gives initials only, two or more, and they spell every given name of one of the PI's full-name forms
    (`names`: the PI's name forms). 'M.T. Islam' is Md Tauhidul Islam; 'Y. L. Chen' is not Yuxin Chen."""
    t_ = nosuffix(toks(byline_name(raw)))
    if len(t_) < 3 or any(len(x) != 1 for x in t_[:-1]):
        return False
    for f in names:
        ft = nosuffix(toks(f))
        if len(ft) >= 3 and ft[-1] == t_[-1] and all(len(x) > 1 for x in ft[:-1]) and [x[0] for x in ft[:-1]] == t_[:-1]:
            return True
    return False


def gwords(x):
    """Name words with hyphenated parts joined ('Wei-Ning Chen' -> ['weining', 'chen']), accents and LETTERS folded."""
    x = byline_name(str(x or '').translate(LETTERS).replace('–', '-').replace('—', '-').replace('‐', '-'))
    x = unicodedata.normalize('NFKD', x); x = re.sub(r'\([^)]*\)', ' ', ''.join(c for c in x if not unicodedata.combining(c)).lower())
    w = [re.sub(r'[^a-z]', '', t) for t in re.split(r'[\s.]+', x.replace("'", ''))]
    return nosuffix([t for t in w if t])


def given_conflict(student_forms, raw, strict=False, pi=None, recur=None, lab_names=None):
    """The given-name guard (2026-10-29, owner): the byline's first given name is a full word that no full-given-name
    reading of the student (`student_forms`: the student's name readings) allows. Allowed: equal, a nickname pair,
    hyphen/space variants, a middle name used as the preferred name, the family name written first on either side, and
    (unless strict, the owner's literal guard) a 3+ letter prefix ('Avi'/'Avinash', 'Gen'/'Gene'; not under an East
    Asian family name) or a one-letter spelling variant of a 4+ letter name ('Johann'/'Johan', 'Katherina'/'Katharina');
    'Wei-Ning' / 'Wei-Chen' differ by three letters and conflict. With `pi`, `recur` ((lab, byline name words) -> number
    of the lab's papers carrying it) and `lab_names` (lab -> the name words of its students), a recurring one-letter
    variant of a lab student is allowed too (see below)."""
    bt = gwords(raw)
    if len(bt) < 2 or len(bt[0]) <= 1:
        return False
    for f in student_forms:
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
            # a recurring co-author one letter from a lab student, on 3+ of the lab's papers, with no student of
            # the lab spelled that way, is the student under a roster misspelling (2026-10-29, owner: best judgement;
            # Yuxin Chen's roster says 'Gene Li', his papers say 'Gen Li')
            key = ' '.join(bt)
            if pi and len(x) >= 3 and st[-1] == bt[-1] and one_edit(a, b) and recur[(pi, key)] >= 3 and key not in lab_names[pi]:
                return False
    return True


def dedupe_tokens(name):
    """R7 (R-STU-05, 2026-10-29, owner: accuracy sample): a roster name with a doubled token ('Arjun Nitin Nitin Bhagoji')
    loses the repeat ('Arjun Nitin Bhagoji'); the first occurrence keeps its spelling."""
    w = str(name or '').split()
    out = [x for i, x in enumerate(w) if i == 0 or x.strip('.,').lower() != w[i - 1].strip('.,').lower()]
    return ' '.join(out) if len(w) >= 3 else str(name or '')
