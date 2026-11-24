"""Princeton helpers for the CS-related review: accent-insensitive name search in a capture's text and listing quotes."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import re, sqlite3, unicodedata, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
LST = P.SWEEPS / 'claude-princeton-listings-20261022/captures/listings.sqlite'
LST_REL = 'claude-princeton-listings-20261022/captures/listings.sqlite'
TITLE = re.compile(r'Professor|Lecturer|Emerit|Dean\b|Chair\b|Provost|President|Instructor|Faculty|Associate|Assistant|Director|Scholar|Fellow', re.I)
STOP = re.compile(r'\s(?:[A-Z]?\d{2,}[A-Z]?\b|\(?\d{3}\)?[-. ]\d{3}|\S+@\S+|Research Interests?|Office|Phone|Email|Website|Room\b|Area[s:]|Fields?:|Ph\.?D\.?,? )')


def fold(s):
    """Accent-folded copy of s with a map from folded positions back to s."""
    out, idx = [], []
    for i, ch in enumerate(s):
        for c in unicodedata.normalize('NFKD', ch):
            if not unicodedata.combining(c):
                out.append(c); idx.append(i)
    return ''.join(out), idx


def name_rx(given, family):
    g = re.escape(fold(given)[0]); f = re.escape(fold(family)[0])
    return re.compile(r'\b' + g + r"(?:\s+(?:[A-Z]\.?|[A-Z][a-z]+\.?|\([A-Za-z]+\))){0,2}\s+" + f + r'(?![\w-])')


SECTION = re.compile(r'(Visiting Faculty|Emeritus Faculty|Emeriti|Faculty Emeriti|Lecturers|Associated Faculty|Affiliated Faculty|Research Staff|Postdoc\w*|Graduate Students|Visitors)\b')
TITLE1 = re.compile(r'Professor|Lecturer|Emerit|Dean\b|Chair\b|Provost|President|Instructor|Director|Scholar|Fellow', re.I)
CONT = re.compile(r"^(?:of|and|in|the|for|at|on|On|Leave|leave|Professor|Professors|Emeritus|Emerita|Emeriti|Associate|Assistant|Adjunct|Visiting|Chair|Co-Chair|Director|Dean|Deputy|Graduate|Undergraduate|Studies|School|Department|Program|Center|Centre|Institute|Electrical|Computer|Engineering|Applied|Science|Sciences|Mathematics|Mathematical|Computational|Psychology|Neuroscience|Sociology|Politics|Molecular|Biology|Operations|Research|Financial|Mechanical|Aerospace|Ecology|Evolutionary|Economics|Public|International|Affairs|Statistics|Machine|Learning|Data|Information|Energy|Environment|Andlinger|Faculty|Senior|Scholar|Representative|Jr\\.|Jr|Lecturer|University|Princeton|Neuroscience|Chemical|Biological|Civil|Environmental|Physics|Zoology|PACM|Mathematics/PACM|ORFE|ECE|MAE)$")
STOP2 = re.compile(r'\s(?:Tags:|Computing & |Biological & |Data & |Applied Physics|Integrated Circuits|Energy & |Security & |Photonics|Quantum|Materials & |Research Interests|Undergraduate Department)')


def find_listing_quote(text, forms, maxlen=140):
    """(quote, section) for the person's entry: the name as written + the title that directly follows it (cut before
    office/phone/email/research areas); for name-only sections (visiting/emeritus lists) the section heading through the
    name, when within 200 characters. None when absent."""
    ft, idx = fold(text)
    best = None
    for given, family in forms:
        for m in name_rx(given, family).finditer(ft):
            s, e = idx[m.start()], idx[m.end() - 1] + 1
            nm = text[s:e]
            tail = text[e:e + 200]
            t2 = tail.lstrip()
            if t2.startswith(nm):  # the name written twice (link text + heading)
                t2 = t2[len(nm):]
            secs = list(SECTION.finditer(text[max(0, s - 3000):s]))
            sec = secs[-1].group(1) if secs else None
            tm = TITLE1.search(t2)
            pre = t2[:tm.start()] if tm else ''
            if tm and tm.start() <= 60 and not SECTION.match(t2[tm.start():]) and not SECTION.search(pre) and not re.search(r'Faculty', pre):
                end = tm.end()
                for mt in re.finditer(r'\S+', t2[tm.end():]):
                    tok = mt.group(0); w = tok.strip(',;:()')
                    if '@' in tok or '[at]' in tok or tok.startswith('http'):
                        break
                    if CONT.match(w) or w == '' or w in ('&', '-', '–', '/'):
                        end = tm.end() + mt.end()
                    else:
                        break
                    if end - tm.end() > 90:
                        break
                lead = tail[:len(tail) - len(t2)]
                q = (nm + lead + t2[:end]).strip()
                if len(q) > maxlen:
                    q = q[:maxlen].rsplit(' ', 1)[0]
                q = q.rstrip(' ,;:-–|(')
                if q.count('(') > q.count(')'):
                    q = q[:q.rfind('(')].rstrip()
                if q in text:
                    return dict(quote=q, section=None, titled=True)
            if sec and best is None:
                j = text.rfind(sec, max(0, s - 200), s)
                if j >= 0:
                    best = dict(quote=text[j:e], section=sec, titled=False)
    return best


def listing_captures(page_like):
    con = sqlite3.connect(f'file:{LST}?mode=ro', uri=True)
    rows = con.execute('select department, page_url, capture_url, wayback_timestamp, sha256 from captures where http_status=200 and page_url like ? '
                       'order by wayback_timestamp', (page_like,)).fetchall()
    con.close()
    return rows


def listing_text(capture_url):
    import sys
    sys.path.insert(0, str(HERE / 'hierarchy/missing-pi-tools'))
    import mpcap
    con = sqlite3.connect(f'file:{LST}?mode=ro', uri=True)
    raw, ct = con.execute('select raw_zlib, content_type from captures where capture_url=?', (capture_url,)).fetchone()
    con.close()
    return mpcap.to_text(zlib.decompress(raw), ct or 'text/html')
