"""EPFL: the faculty-list captures of hierarchy/cs-related-captures-epfl.sqlite as (url, school, year, text, normalized text),
and name presence/quotes on them."""
import re, sqlite3, sys, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import cscap

SCHOOL_OF = [('www.epfl.ch/research/faculty-members', 'EPFL'), ('edee-electrical-engineering', 'EDEE'), ('sti.epfl.ch', 'STI'), ('/schools/sti', 'STI'), ('/schools/sb', 'SB'), ('sb.epfl.ch', 'SB'), ('/schools/sv', 'SV'), ('sv.epfl.ch', 'SV'),
             ('enac', 'ENAC'), ('/schools/cdm', 'CDM'), ('cdm.epfl.ch', 'CDM'), ('/schools/ic', 'IC'), ('ic.epfl.ch', 'IC'), ('edic', 'IC'),
             ('/schools/cdh', 'CDH'), ('cdh.epfl.ch', 'CDH')]


def norm(s):
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def lists():
    cscap.use('epfl')
    con = sqlite3.connect(cscap.mpcap.DB)
    out = []
    for cid, url, text, fa in con.execute("select id, url, text, fetched_at from captures where status=200 and error is null and text is not null"):
        if 'people.epfl.ch' in url or 'robots.txt' in url or 'cdx/search' in url or 'infoscience' in url:
            continue
        sch = next((s for k, s in SCHOOL_OF if k in url), None)
        if not sch:
            continue
        m = re.search(r'/web/(\d{4})(\d{2})(\d{2})', url)
        y, obs = (int(m.group(1)), f'{m.group(1)}-{m.group(2)}-{m.group(3)}') if m else (int(fa[:4]), fa[:10])
        out.append(dict(id=cid, url=url, school=sch, year=y, observed=obs, text=text, ntext=norm(text)))
    return out


def present(L, given, family):
    """Captures whose text names given+family in either order (accent-insensitive)."""
    g, f = norm(given), norm(family)
    rx = re.compile(r'\b' + re.escape(g) + r'\s+(?:[a-z.\-]+\s+){0,2}?' + re.escape(f) + r'\b|\b' + re.escape(f) + r'\s+' + re.escape(g) + r'\b')
    return [c for c in L if rx.search(c['ntext'])]


_VAR = {}


def _cls(ch):
    if not _VAR:
        for cp in list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + list(range(0xC0, 0x250)):
            c = chr(cp); b = norm(c)
            if len(b) == 1 and b.isalpha():
                _VAR.setdefault(b, set()).update({c, c.upper(), c.lower()})
    b = norm(ch)
    if len(b) == 1 and b in _VAR:
        return '[' + ''.join(sorted(re.escape(x) for x in _VAR[b])) + ']'
    if ch in ' -':
        return r'[\s\-]+'
    return re.escape(ch)


def name_rx(given, family):
    g = ''.join(_cls(c) for c in given); f = ''.join(_cls(c) for c in family)
    return re.compile(r'(?<![\w])(?:' + g + r'(?:\s+[\w.\-’\']+){0,2}?\s+' + f + r'|' + f + r'(?:\s+[\w\-]+)?\s+' + g + r')(?![\w])')


RANK = (r'(?:Tenure[\s\-]Track Assistant Professor|Assistant Professor Tenure Track|Full Professor|Associate Professor|Assistant Professor|'
        r'Adjunct Professor|Titular Professor|Professor Emeritus|Emeritus Professor|Honorary Professor|Senior Scientist|Professeure? ordinaire|'
        r'Professeure? associée?|Professeure? assistante? tenure track|Professeure? titulaire|Professeure? boursier|Professeure? adjointe?|MER|'
        r'Research Professor|Lecturer|Professor|Senior Lecturer|Scientist|Chargée? de cours)')


def listing_quote(text, given, family, lab_ok=False):
    """'Name Rank' (or, on lists without ranks, 'Family Given Lab...') as written in text; None if absent."""
    rx = name_rx(given, family)
    best = None
    for m in rx.finditer(text):
        tail = text[m.end():m.end() + 140]
        r = re.match(r'\s*(?:,\s*)?(' + RANK + r')\b', tail)
        if r:
            return text[m.start():m.end() + r.end()]
        if lab_ok and best is None:
            r2 = re.match(r'\s+((?:[A-Z][\w&/\-’\']*|of|for|and|in|the|on|des|de|du|et|la|le|\(\w+\)|&)(?:\s+(?:[A-Z][\w&/\-’\']*|of|for|and|in|the|on|des|de|du|et|la|le|\(\w+\)|&)){0,9})', tail)
            if r2 and re.search(r'(?i)lab|laboratory|group|chair|LIDIAP|institute|centre|center', r2.group(1)):
                q = text[m.start():m.end() + r2.end()]
                best = re.sub(r'\s+\S+$', '', q) if len(q) > 130 else q
    return best


_BLK = {}


def blocks_of(cid):
    """Text blocks of a stored capture (listings/scripts/extract.py)."""
    if cid not in _BLK:
        import zlib
        sys.path.insert(0, str(cscap.HERE / 'listings/scripts'))
        import extract
        con = sqlite3.connect(cscap.mpcap.DB)
        b, ct = con.execute('select content, content_type from captures where id=?', (cid,)).fetchone()
        _BLK[cid] = [t for _, t in extract.blocks(zlib.decompress(b), ct)]
    return _BLK[cid]


LABW = re.compile(r'(?i)\b(lab|laboratory|laboratoire|group|groupe|chair|chaire|LIDIAP|institute|centre|center|unit)\b')


def block_quote(c, given, family):
    """'Name Rank' / 'Name Lab' read from adjacent text blocks of capture c, checked as a substring of the stored text."""
    rx = name_rx(given, family)
    B = blocks_of(c['id'])
    for i, b in enumerate(B):
        m = rx.search(b)
        if not m or len(b) > len(m.group(0)) + 60:
            continue
        parts = [b]
        for nb in B[i + 1:i + 4]:
            parts.append(nb)
            q = ' '.join(parts)
            if re.search(RANK, nb) or LABW.search(nb):
                if q in c['text'] and len(nb) < 120:
                    return q, nb
                break
        r = re.search(RANK, b[m.end():])
        if r and b in c['text']:
            return b, r.group(0)
    q = listing_quote(c['text'], given, family)
    return (q, None) if q else (None, None)


STI_NEW = re.compile(r'sti\.epfl\.ch/(?:faculty-members|fr/corps-professoral|iem/faculty-members|igm/faculty-members)/')
RANK_START = re.compile(r'^(?:Position\s+)?(' + RANK + r')\b')


def valid_quotes(c, given, family):
    """Listing entries for the person on capture c: [(quote, rank_or_unit)], each 'Name Rank' (or, on the STI lists that
    give no rank, 'Family Given Lab') read from adjacent text blocks and checked as a substring of the stored text."""
    rx = name_rx(given, family)
    B = blocks_of(c['id']); out = []
    for i, b in enumerate(B):
        m = rx.match(b.strip())
        if not m:
            continue
        rest = b.strip()[m.end():].strip(' ,')
        if rest:
            r = RANK_START.match(rest)
            if r and len(rest) < 120:
                q = b.strip()[:m.end()] + b.strip()[m.end():m.end() + (len(b.strip()[m.end():]) - len(b.strip()[m.end():].lstrip(' ,'))) + r.end()]
                if q in c['text']:
                    out.append((q, r.group(1)))
            continue
        nxt = B[i + 1:i + 3]
        if not nxt:
            continue
        r = RANK_START.match(nxt[0])
        if r:
            q = b.strip() + ' ' + nxt[0][:r.end()]
            if q in c['text']:
                out.append((q, r.group(1)))
            continue
        if nxt[0] in ('Position', 'Fonction') and len(nxt) > 1:
            r = RANK_START.match(nxt[1])
            if r:
                q = b.strip() + ' ' + nxt[0] + ' ' + nxt[1][:r.end()]
                if q in c['text']:
                    out.append((q, r.group(1)))
            continue
        if STI_NEW.search(c['url']) and len(nxt[0]) < 100 and not RANK_START.match(nxt[0]):
            q = b.strip() + ' ' + nxt[0]
            if q in c['text']:
                out.append((q, None))
    return out
