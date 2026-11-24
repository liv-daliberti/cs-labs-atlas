"""Match every candidate (hierarchy/mit/cs-related-candidates.json) against the department faculty listings in the review
store (Course Catalog department pages, EECS faculty lists): one row per (candidate, capture) with the section heading
the entry sits under (rank), the listing year and an exact quote cut from the stored text.
usage: scan_listings.py <out.json>
"""
import json, re, sqlite3, sys, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import mpcap  # noqa: E402

H = mpcap.HERE
HEADINGS = ['Professors of the Practice', 'Adjunct Associate Professors', 'Adjunct Assistant Professors', 'Adjunct Professors',
            'Visiting Associate Professors', 'Visiting Assistant Professors', 'Visiting Professors', 'Associate Professors',
            'Assistant Professors', 'Professors Emeriti', 'Professors Post-Tenure', 'Senior Lecturers', 'Visiting Lecturers', 'Lecturers',
            'Technical Instructors', 'Moore Instructors', 'Instructors', 'Principal Research Scientists', 'Senior Research Scientists',
            'Research Scientists', 'Senior Research Engineers', 'Research Engineers', 'Research Associates', 'Research Staff',
            'Affiliated Faculty', 'Professors']
HRX = re.compile(r'(?<![\w,])(' + '|'.join(re.escape(h) for h in HEADINGS) + r')(?= [A-Z])')
DEG = r'(?:PhD|ScD|MM|MEd|EdM|MSEE|MD|MS|SM|MA|MBA|MArch|MCP|MFA|BS|BA|SB|AB|JD|DPhil|EdD|MEng|DrEng|MPhil|MLA|MSc|BArch|MPA|MPP|DSc|DEng|DrSc|Dr|MDes|MPH|BFA|BSc|MSE|PE|LLB|LLM|DDes|DrPH|EngD|MAUD)'
STOP = (r'(?:Sciences?|Engineering|Astronautics|Society|Technology|Systems|Management|Planning|Studies|Design|Economics|Mathematics|'
        r'Physics|Media|Arts|Program|Writing|Architecture|Computation|Medicine|Biology|Chemistry|Policy|Research|Laboratory|Center|'
        r'Institute|Development|Professor|Practice|Leave|Emeritus|Emerita|Head|Director|Chair|Dean|Fall|Spring|Sabbatical|Innovation|'
        r'Entrepreneurship|Finance|Accounting|Marketing|Strategy|Statistics|Operations|Analytics|Health|Energy|Environment)\b')
NEXT = re.compile(r" (?=(?!" + STOP + r")[A-Z][\w.'’-]*(?: (?!" + STOP + r")[A-Z][\w.'’()-]*){1,4},? " + DEG + r'\b)')


def fold(s):
    return ''.join((unicodedata.normalize('NFKD', ch)[0] if unicodedata.normalize('NFKD', ch) else ch) for ch in s)


def natural(n):
    n = re.sub(r'\s+', ' ', n).strip()
    if n.count(',') == 1:
        a, b = [x.strip() for x in n.split(',')]
        if a and b and not re.match(r'^(Jr|Sr|II|III)\.?$', b):
            return f'{b} {a}'
    return n


def patterns(names):
    pats = set()
    for n in names:
        t = [x for x in re.split(r'\s+', fold(natural(n)).replace('.', '. ')) if x]
        t = [x for x in t if not re.match(r'^(Jr|Sr|II|III)\.?$', x)]
        if len(t) < 2:
            continue
        sur = t[-1]
        givens = [g for g in t[:-1] if len(g.rstrip('.')) > 1][:1]
        if not givens:
            continue
        g = givens[0]
        mids = r"(?:\s+(?:[A-Z]\.|[A-Z][\w'’-]+|\([^)]{1,20}\))){0,3}"
        pats.add((sur, r"(?<![\w-])(?:[A-Z]\.\s+)?" + re.escape(g) + mids + r'\s+' + re.escape(sur) + r"(?![\w-])"))
        if '-' in sur:  # Youcef-Toumi / Youcef Toumi
            pats.add((sur.split('-')[-1], r"(?<![\w-])" + re.escape(g) + mids + r'\s+' + re.escape(sur.replace('-', ' ')) + r"(?![\w-])"))
    return [(s_, re.compile(p)) for s_, p in pats]


EXTRA = {  # listing spellings the candidate's OpenAlex names lack (reviewed)
    'https://openalex.org/A5081457786': ['Patricia Maes'],
}


def main(out):
    cands = json.load(open(f'{H}/hierarchy/mit/cs-related-candidates.json'))
    for c in cands:
        c['names'] = list(c.get('names') or []) + EXTRA.get(c['author'], [])
    con = sqlite3.connect(f'file:{mpcap.DB}?mode=ro', uri=True)
    caps = con.execute("select id, url, sha256, text, fetched_at from captures where status=200 and error is null and (url like '%catalog.mit.edu%/schools/%' "
                       "or url like '%eecs.mit.edu%')").fetchall()
    pre = []
    for cid, url, sha, text, fa in caps:
        m = re.search(r'/web/(\d{14})id_/', url)
        ts = m.group(1) if m else re.sub(r'\D', '', fa)[:14]
        dept = re.sub(r'^.*catalog\.mit\.edu(?::80)?/schools/[^/]+/([^/]+)/.*$', r'\1', url) if 'catalog.mit.edu' in url else 'EECS'
        i = text.find('Faculty and Teaching Staff') if 'catalog' in url else 0
        if 'catalog' in url and i < 0:
            continue
        heads = [(h.start(), h.group(1)) for h in HRX.finditer(text)] if 'catalog' in url else []
        pre.append((cid, url, sha, text, fold(text), ts, dept, i, heads))
    res = {}
    for c in cands:
        rows = []
        for sur, p in patterns([c['name']] + c.get('names', [])):
            for cid, url, sha, text, ftext, ts, dept, i, heads in pre:
                if sur not in ftext:
                    continue
                for m in p.finditer(ftext, i):
                    a = m.start()
                    if 'catalog' in url:
                        tail = text[m.end():m.end() + 400]
                        if not re.match(r',? ' + DEG + r'\b', tail) and not re.match(r',? \w', tail):
                            continue
                        nx = NEXT.search(text, m.end() + 3, m.end() + 300)
                        hx = HRX.search(text, m.end() + 3, m.end() + 300)
                        e = min([x.start() for x in (nx, hx) if x] + [m.end() + 220])
                        head = next((h for s_, h in reversed(heads) if s_ < a), None)
                    else:
                        e = m.end() + 160; head = None
                    q = text[a:e].strip()
                    if 'eecs' in url:
                        q = re.split(r'\s(?:Email|Phone|Office|Website|Read more)\b', q)[0][:160].strip()
                    rows.append(dict(capture_id=cid, url=url, sha256=sha, year=int(ts[:4]), observed=ts, dept=dept, heading=head, quote=q))
        seen = set(); uniq = []
        for r in sorted(rows, key=lambda r: (r['dept'], r['observed'])):
            k = (r['capture_id'], r['quote'])
            if k not in seen:
                seen.add(k); uniq.append(r)
        res[c['author']] = uniq
    json.dump(res, open(out, 'w'), indent=0, ensure_ascii=False)
    print(sum(bool(v) for v in res.values()), 'of', len(res), 'candidates matched')


main(sys.argv[1])
