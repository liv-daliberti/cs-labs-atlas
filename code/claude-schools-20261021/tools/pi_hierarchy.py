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
import calendar, collections, datetime, gzip, json, re, sqlite3, sys, unicodedata, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SITE = Path('/n/fs/similarity/maxent-grpo/princeton-live-20261015/atlas/data')
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
            t = toks(n)
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
        t = toks(raw)
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


def student_on_byline(nm, s_toks, raw):
    """A student's name on a byline: Name.match, or forms Name.match rejects but that are the same person on one lab paper:
    given names written joined or split ('Sangeon'/'Sang Eon Park'), a first given name that is a 3+ letter prefix of the
    other ('Divy'/'Divya', 'Themis'/'Themistoklis'), or the byline adding a first name before the known one ('Sergio
    Sebastian Pineda' for 'Sebastian Pineda'). The family name must agree in every case."""
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


def datebounds(value):
    value = str(value or '')
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


def not_faculty_row(text):
    """A dated listing row that lists the person as a student or postdoc, not as faculty: it proves no appointment
    (the same-year listing rule is about faculty listings; directories such as CMU's SCS list students too)."""
    t = text or ''
    return bool(NOT_FACULTY.search(t)) and not re.search(r'professor|lecturer|faculty', t, re.I)


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
        if not x.get('is_pi') or x.get('not_faculty'):
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
                        mergedCensusRows=x['mergedCensusRows'], rank=x.get('rank'), title=x.get('title_as_listed'),
                        departments=x.get('departments') or x.get('units') or [], piBasis=x.get('pi_basis'), lab=lab,
                        periods=[dict(id=p.get('id'), start=p.get('facultyStart'), end=p.get('facultyEnd'), asof=p.get('ongoingAsOf') or p.get('facultyLastConfirmed'),
                                      evidence=(p.get('evidence') or [])[:2]) for p in mine]
                                + [dict(q, asof=q.get('asof') or (None if q.get('end') else TODAY)) for q in o.get('periods') or []],  # reviewed periods (census-overrides.json)
                        listings=[listings[y] for y in sorted(listings)]))
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
                    if ids_ & set(p['personIds']) or any(a and nm[p['pi']].match(a) for a in advs) or (c.get('unit') and c.get('unit') == p['lab']['unitId'] and t == 'academic_advising'):
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
    for fn in ('few-students-evidence.json', 'thesis-evidence.json', 'labpage-evidence.json'):
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
    n['student_records_merged'] = merged_students
    # one id per person across the school's labs: a co-advised student (or one found by two sources) keeps one id, the
    # collection person's when there is one (the collections themselves list one person under several source ids). Same
    # name tokens, middle initials ignored; not for short two-part names ('Yang Yang', 'Wei Li'), which are too often
    # different people, nor across different full middle names ('William Wang' / 'William Wei Wang').
    groups = collections.defaultdict(list)
    for p in pis:
        for r in stu[p['pi']].values():
            t_ = [x for x in toks(r['name']) if len(x) > 1]  # middle initials dropped: 'Quanquan C. Liu' = 'Quanquan Liu'
            if len(t_) >= 2 and not (len(t_) == 2 and len(t_[0]) <= 4 and len(t_[1]) <= 4):
                groups[tuple(t_)].append((p['pi'], r))
    for key, recs in groups.items():
        ids = {r['person'] for _, r in recs}
        if len(ids) < 2:
            continue
        known = sorted(i for i in ids if i in Pid)  # the collections hold one person under several source ids (MIT: roster, thesis, audit)
        canon = known[0] if known else collections.Counter(r['person'] for _, r in recs).most_common(1)[0][0]
        for pi_, r in recs:
            if r['person'] != canon:
                old = r['person']; r.setdefault('merged', []).append(old); r['person'] = canon
                stu[pi_] = {(canon if k == old else k): v for k, v in stu[pi_].items()}
                n['student_ids_unified_across_labs'] += 1
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
        if any(an.match(o) for an in advisee_names[pi] for o in others):
            return 'advisee_coauthor'
        return None

    surname_only = []
    anchored = collections.defaultdict(collections.Counter)
    via_advisee = collections.defaultdict(collections.Counter)  # an author id on 2+ works the PI wrote with their own advisees anchors too
    reviewed_oa = {p['pi']: set(p.get('reviewedOpenAlex') or []) for p in pis}
    orcids = {p['pi']: set(p.get('orcid') or []) for p in pis}
    blocked = {p['pi']: set(p.get('notOpenAlex') or []) for p in pis}
    hits = []  # (pi, oa work, authorship, collection work, identity)
    for w in sweep_works(school):
        if w.get('type') in NOT_PAPERS:  # datasets, peer reviews, errata, supplements: not papers
            continue
        cw = None; done = set()
        for a in w.get('authorships') or []:
            raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
            t = toks(raw)
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
                if ident and ident != 'advisee_coauthor' and (a.get('author') or {}).get('id'):
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
                    hits.append((pi, w, a, cwork(w), ident, tied.get(w['id'])))
        n['pi_work_list_hits'] = len(hits) - k0
    funnel = collections.defaultdict(collections.Counter)

    # lab papers
    rows, seen = [], set()
    for pi, w, a, cw, ident, page1 in hits:
        p = pid0[pi]
        via = [i.get('display_name') for i in a.get('institutions') or [] if inst == i.get('id') or inst in (i.get('lineage') or [])] \
            + ['text: ' + z for z in a.get('raw_affiliation_strings') or [] if aff.search(z)]
        if page1 and not a.get('institutions') and not a.get('raw_affiliation_strings'):
            via = [f"page 1 ({page1['how']}): " + ' … '.join(page1['quotes'])]  # the paper's own first page ties the school to the PI
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
            continue
        seen.add(k)
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
        lead['editions'] = [dict(oa=x['oa'], work=x['work'], doi=x.get('doi'), year=x['year'], venue=x.get('venue')) for x in g[1:]]
        rows.append(lead)
    n['edition_records_merged'] = sum(len(g) - 1 for g in grouped.values())
    n['lab_papers'] = len(rows); n['lab_papers_in_collection'] = sum(bool(r['work']) for r in rows); n['lab_papers_new'] = n['lab_papers'] - n['lab_papers_in_collection']
    n['lab_papers_by_period'] = sum('periodId' in r['appointment'] for r in rows); n['lab_papers_by_listing'] = n['lab_papers'] - n['lab_papers_by_period']
    n.update({'identity:' + k: v for k, v in collections.Counter(r['identity'] for r in rows).items()})

    # student papers
    sp = []
    snm = {sid: Name([s['name']] + list(s.get('aliases') or [])) for v in stu.values() for sid, s in v.items()}
    stk = {sid: toks(s['name']) for v in stu.values() for sid, s in v.items()}
    for r in rows:
        S = stu.get(r['pi']) or {}
        if not S:
            continue
        for sid, s in S.items():
            l = next((l for l in pls[sid] if r['work'] and l['work'] == r['work']), None)
            if l:
                sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status=l.get('status'), basis='collection_person_link'))
            elif any(student_on_byline(snm[sid], stk[sid], b or '') for b in r['byline_school']):
                # the student's name on this lab paper's byline, on an authorship that lists the school
                sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='byline_name_with_school_affiliation'))
            elif near_relation(s, r['year']) and any(student_on_byline(snm[sid], stk[sid], b or '') for b in r['byline']):
                # the PI's own advisee named on the PI's lab paper (an authorship without affiliations, e.g. an ACL
                # Anthology record), within three years of the recorded advising
                sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='advisee_name_on_lab_paper_byline'))
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
    for name, data in (('lab_papers', rows), ('student_papers', sp)):
        with gzip.open(out / f'{name}.jsonl.gz', 'wt') as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    rep = dict(school=school, builtAt=datetime.datetime.utcnow().isoformat() + 'Z', counts=dict(n), excluded=excluded,
               pisWithoutPapers=sorted(p['pi'] for p in pis if not per_pi[p['pi']]),
               pisWithoutStudents=sorted(p['pi'] for p in pis if not stu[p['pi']]), censusNicknameMerges=nick_merges)
    json.dump(rep, open(out / 'report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(dict(school=school, **n)))


if __name__ == '__main__':
    for s in sys.argv[1:]:
        build(s)
