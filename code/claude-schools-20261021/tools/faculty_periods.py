"""Faculty appointment periods with verbatim evidence, for every lab-leading PI of a school (the gate the site's lab-paper
rule needs: a PI's paper counts for their lab only inside a reviewed faculty period).

PIs       the school's collection (princeton-live atlas/data/collection-<school>.json.gz): every unit leader, and every
          person the stage structure (people/structure.json) lists as faculty leading a unit; the person's profile URL,
          website and person-specific source pages.
fetch     each page once (robots.txt honoured, one request per 3 s per host, a Wayback copy when the live page is
          blocked or gone), kept with its sha256 in captures/<school>.sqlite (one container, not loose files). Linked CV
          PDFs on a homepage are fetched too (pdftotext).
extract   sentences that state an appointment at this school with a year: 'joined <school> in 2015', 'professor at
          <school> since 2012', 'Assistant Professor ... <school> ... 2015 - present' (CV lines), '<school> (2016-2021)'.
          The quote is the verbatim text around the match (the page's own words, whitespace collapsed).
accept    a start year is accepted when the quote names this school and an appointment word (professor, faculty,
          lecturer, chair) and states the year; when several pages state different years the earliest faculty-rank year
          is kept and the conflict is reported. Departure ('until', 'left', a closed range) sets facultyEnd. Everything
          else is a hold with the candidates found.
-> periods/<school>-faculty-periods.json (the site's facultyPeriods format), periods/<school>-holds.json
usage: faculty_periods.py fetch|extract <school>
"""
import gzip, hashlib, json, re, sqlite3, subprocess, sys, time, unicodedata, urllib.parse, urllib.robotparser
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK
ATLAS = P.SITE_DATA
STAGES = {'epfl': P.sweep('claude-epfl-20261019'), 'cmu': P.sweep('claude-cmu-20261017'),
          'mit': P.sweep('claude-mit-20261020'), 'berkeley': P.sweep('claude-berkeley-20261021')}
SCHOOL = {'epfl': r'EPFL|[ÉE]cole\s+[Pp]olytechnique\s+[Ff][ée]d[ée]rale\s+de\s+Lausanne|Swiss Federal Institute of Technology,?\s+(?:in\s+)?Lausanne',
          'cmu': r'Carnegie\s+Mellon|CMU', 'mit': r'Massachusetts\s+Institute\s+of\s+Technology|\bMIT\b',
          'berkeley': r'U\.?\s?C\.?\s+Berkeley|University\s+of\s+California,?\s+Berkeley|\bBerkeley\b'}
RANK = r'(?:[Pp]rofessor|[Ff]aculty|[Ll]ecturer|[Cc]hair\b)'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
HOME = re.compile(r'(?i)(?:personal\s+)?(?:web\s*site|home\s*page|web\s*page|homepage|personal\s+page|website)')


def now():
    return datetime.now(timezone.utc).isoformat()


def nt(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower())


def db_for(school):
    (HERE / 'captures').mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(HERE / 'captures' / f'{school}.sqlite'))
    db.execute('CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, fetched_url TEXT, status INTEGER, sha256 TEXT, text BLOB, at TEXT, kind TEXT)')
    return db


SOCIAL = re.compile(r'(?i)facebook|twitter|x\.com|linkedin|instagram|youtube|scholar\.google|github\.com/?$')


def pis(school):
    """[(person id, name, [urls])]: the census PIs when census/<school>-faculty.json exists, else every unit leader of the collection."""
    cen = HERE / 'census' / f'{school}-faculty.json'
    st = json.loads((STAGES[school] / 'people' / 'structure.json').read_text())
    sp = {nt(p['name']): p for p in st['people']}
    if cen.exists():
        out = []
        for p in json.loads(cen.read_text()):
            if not p.get('is_pi'):
                continue
            s = sp.get(nt(p.get('structure_name') or p['name'])) or {}
            urls = [p.get('profile_url')] + [s.get('website')] + [x['url'] for x in (s.get('sources') or []) if x.get('source_kind') in ('faculty_profile', 'homepage', 'cv', 'people_page') and x.get('url')]
            out.append(dict(name=p['name'], person=p.get('collection_person_id'), units=[u for u in p.get('lab_units') or [] if isinstance(u, str)],
                            urls=list(dict.fromkeys(u for u in urls if u and u.startswith('http') and not SOCIAL.search(u)))))
        return out
    C = json.loads(gzip.open(ATLAS / f'collection-{school}.json.gz').read())
    people = {p['id']: p for p in C['people']}
    byname = defaultdict(list)
    for p in C['people']:
        byname[nt(p['name'])].append(p['id'])
    out = {}
    for u in C['units']:
        for l in u.get('leaders') or []:
            ids = byname.get(nt(l), [])
            pid = ids[0] if len(ids) == 1 else None
            out.setdefault(l, dict(name=l, person=pid, units=[]))['units'].append(u['id'])
    for p in st['people']:  # faculty the structure has leading a unit of the collection
        if 'faculty' in (p.get('roles') or []) and set(p.get('units_led') or []) & {u['id'] for u in C['units']}:
            ids = byname.get(nt(p['name']), [])
            out.setdefault(p['name'], dict(name=p['name'], person=ids[0] if len(ids) == 1 else None, units=[]))['units'] += [u for u in p['units_led'] if u not in out.get(p['name'], {}).get('units', [])]
    for name, r in out.items():
        urls = []
        cp = people.get(r['person']) or {}
        urls += [cp.get('profileUrl')] if cp.get('profileUrl') else []
        s = sp.get(nt(name)) or {}
        urls += [s.get('website')] if s.get('website') else []
        urls += [x['url'] for x in (s.get('sources') or []) if x.get('source_kind') in ('faculty_profile', 'homepage', 'cv', 'people_page') and x.get('url')]
        r['urls'] = list(dict.fromkeys(u for u in urls if u and u.startswith('http')))
    return list(out.values())


ROBOTS = {}


def allowed(url):
    host = urllib.parse.urlsplit(url)
    base = f'{host.scheme}://{host.netloc}'
    if base not in ROBOTS:
        import requests  # RobotFileParser.read() has no timeout and hung on a slow host
        rp = urllib.robotparser.RobotFileParser(); rp.set_url(base + '/robots.txt')
        try:
            r = requests.get(base + '/robots.txt', headers={'User-Agent': UA}, timeout=(10, 20))
            if r.status_code in (401, 403):
                rp.disallow_all = True
            elif r.status_code == 200:
                rp.parse(r.text.splitlines())
            else:
                rp = None  # no robots.txt: allowed
        except Exception:
            rp = None
        ROBOTS[base] = rp
    rp = ROBOTS[base]
    return rp is None or rp.can_fetch(UA, url)


def fetch_one(s, url, last):
    import requests
    host = urllib.parse.urlsplit(url).netloc
    time.sleep(max(0, 3 - (time.monotonic() - last.get(host, 0)))); last[host] = time.monotonic()
    try:
        if not allowed(url):
            return None, 'robots', None
        r = s.get(url, timeout=(15, 60), allow_redirects=True)
    except requests.RequestException as e:
        return None, type(e).__name__, None
    if r.status_code != 200:
        return None, r.status_code, None
    return r, 200, r.url


def to_text(r):
    if 'pdf' in (r.headers.get('content-type') or '') or r.content[:4] == b'%PDF':
        p = subprocess.run(['pdftotext', '-q', '-l', '15', '-enc', 'UTF-8', '-', '-'], input=r.content, capture_output=True, timeout=120)
        return p.stdout.decode('utf-8', 'ignore'), 'pdf'
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, 'html.parser')
    for t in soup(['script', 'style', 'noscript']):
        t.decompose()
    return soup.get_text(' ', strip=True), 'html'


def fetch(school):
    """Each PI page once; from a PI page its homepage link (kind home_of:<page>) and CV PDF (kind cv_of:<page>); from a homepage its CV."""
    import requests
    from bs4 import BeautifulSoup
    db = db_for(school); s = requests.Session(); s.headers['User-Agent'] = UA; last = {}
    db.execute('CREATE TABLE IF NOT EXISTS linkcheck (url TEXT PRIMARY KEY)')
    have = {u: (st, k) for u, st, k in db.execute('SELECT url, status, kind FROM pages')}
    checked = {u for (u,) in db.execute('SELECT url FROM linkcheck')}
    mine = list(dict.fromkeys(u for r in pis(school) for u in r['urls']))
    # new pages, and PI pages fetched before links were followed (their links were not kept, so read them again)
    queue = [(u, None) for u in mine if u not in have or (have[u][0] == 200 and have[u][1] == 'html' and u not in checked)]
    print(json.dumps(dict(school=school, pages=len(queue))), flush=True)

    def store(url, r, final, kind):
        text, k = to_text(r)
        db.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?)', (url, final, 200, hashlib.sha256(r.content).hexdigest(), gzip.compress(text.encode()), now(), kind or k))
        return k

    i = 0
    while i < len(queue):
        url, parent = queue[i]; i += 1
        r, status, final = fetch_one(s, url, last)
        if r is None and status not in ('robots',):
            r, status2, final = fetch_one(s, 'https://web.archive.org/web/2026id_/' + url, last)
            status = status2 if r is not None else status
        if r is None:
            if url not in have:
                db.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?)', (url, None, status if isinstance(status, int) else -1, None, None, now(), str(status)))
            db.commit(); continue
        k = store(url, r, final, ('home_of:' + parent) if parent else None)
        if k == 'html' or (parent and 'pdf' not in (r.headers.get('content-type') or '')):
            soup = BeautifulSoup(r.text, 'html.parser')
            links = [(' '.join(a.get_text(' ').split()), urllib.parse.urljoin(final, a['href'])) for a in soup.find_all('a', href=True)]
            cv = next((h for t, h in links if re.search(r'(?i)\bcv\b|curriculum|vitae|resume', t + ' ' + h) and h.lower().split('?')[0].endswith('.pdf')), None)
            if cv and cv not in have:
                r2, st2, f2 = fetch_one(s, cv, last)
                if r2 is not None:
                    store(cv, r2, f2, 'cv_of:' + url); have[cv] = (200, 'cv')
            if parent is None:  # a PI page: follow its homepage link once
                home = next((h for t, h in links if HOME.fullmatch(t) and h.startswith('http') and not SOCIAL.search(h)
                             and urllib.parse.urlsplit(h).netloc != urllib.parse.urlsplit(final).netloc), None)
                if home and home not in have and all(home != q for q, _ in queue):
                    queue.append((home, url))
        db.execute('INSERT OR REPLACE INTO linkcheck VALUES (?)', (url,))
        db.commit()
        if i % 25 == 0:
            print(json.dumps(dict(fetched=i, of=len(queue))), flush=True)
    print(json.dumps(dict(finished=now())), flush=True)


def candidates(text, school):
    """[(start, end, quote, pattern)] appointment statements naming the school."""
    sch = SCHOOL[school]; t = ' '.join(text.split()); out = []
    pats = [
        ('joined', rf'(?:joined|joining|came to|moved to|arrived at)\s+(?:the\s+)?(?:faculty\s+(?:of|at)\s+)?[^.;]{{0,80}}?(?:{sch})[^.;]{{0,80}}?\b(?:in|since)\s+(?:\w+\s+)?((?:19|20)\d\d)'),
        ('since', rf'{RANK}[^.;]{{0,120}}?(?:{sch})[^.;]{{0,60}}?\bsince\s+(?:\w+\s+)?((?:19|20)\d\d)'),
        ('since_rev', rf'(?:{sch})[^.;]{{0,60}}?\bsince\s+(?:\w+\s+)?((?:19|20)\d\d)[^.;]{{0,40}}?{RANK}'),
        ('range', rf'((?:19|20)\d\d)\s*(?:[-–—]|to)\s*((?:19|20)\d\d|[Pp]resent|[Nn]ow|[Tt]oday)?\s*[,:]?\s*[^.;]{{0,60}}?{RANK}[^.;]{{0,100}}?(?:{sch})'),
        ('range_rev', rf'{RANK}[^.;]{{0,100}}?(?:{sch})[^.;]{{0,40}}?\(?((?:19|20)\d\d)\s*(?:[-–—]|to)\s*((?:19|20)\d\d|[Pp]resent|[Nn]ow)?\)?'),
    ]
    for name, p in pats:
        for mm in re.finditer(p, t):
            g = mm.groups(); start = g[0]; end = g[1] if len(g) > 1 and g[1] and g[1][:1].isdigit() else None
            q = t[max(0, mm.start() - 60): mm.end() + 60]
            if name == 'joined':  # joining the school is an appointment only with a rank word in the sentence and no student/postdoc role
                sent = t[mm.start(): mm.end() + 120].split('. ')[0]
                if not re.search(RANK, sent) or re.search(r'(?i)ph\.?d\.? student|graduate student|post-?doc|undergraduate|master', sent):
                    continue
            out.append((start, end, q, name))
    return out


def extract(school):
    db = db_for(school); rows = list(db.execute('SELECT * FROM pages'))
    pages = {u: (st, sha, gzip.decompress(tx).decode() if tx else '', at) for u, f, st, sha, tx, at, k in rows}; kinds = {u: k or '' for u, f, st, sha, tx, at, k in rows}
    C = json.loads(gzip.open(ATLAS / f'collection-{school}.json.gz').read())
    have = {nt(p['name']) for p in C['facultyPeriods']}
    periods, holds = [], []
    nid = 1 + max([int(p['id'].rsplit('_', 1)[1]) for p in C['facultyPeriods'] if re.search(r'_\d+$', p['id'])] or [-1])
    for r in pis(school):
        if nt(r['name']) in have:
            continue
        found = []
        own = set(r['urls']) | {k for k in pages if kinds.get(k, '').startswith('home_of:') and kinds[k][8:] in r['urls']}
        own |= {k for k in pages if kinds.get(k, '').startswith('cv_of:') and kinds[k][6:] in own}
        for u in list(own) + [k for k in pages if pages[k][0] == 200 and any(k.startswith(x.rstrip('/')) for x in r['urls'])]:
            st, sha, text, at = pages.get(u, (None, None, '', None))
            if st == 200 and text:
                fam = (r['name'].split() or [''])[-1]
                if fam.lower() not in text.lower():
                    continue  # not this person's page
                found += [dict(url=u, sha256=sha, quote=q, start=s, end=e, pattern=pn, observedAt=at) for s, e, q, pn in candidates(text, school)]
        found = list({(f['url'], f['quote']): f for f in found}.values())
        if not found:
            holds.append(dict(name=r['name'], person=r['person'], units=r['units'], reason='no appointment statement found', pages=r['urls'])); continue
        starts = sorted({int(f['start']) for f in found})
        best = min(found, key=lambda f: int(f['start']))
        ends = sorted({int(f['end']) for f in found if f.get('end')})
        if not r['person']:
            holds.append(dict(name=r['name'], units=r['units'], reason='no unique collection person', candidates=found[:5])); continue
        periods.append(dict(id=f'{school}_faculty_period_{nid}', personId=r['person'], name=r['name'], school=school.upper() if school == 'epfl' else school, unitIds=r['units'],
                            facultyStart=str(starts[0]), facultyEnd=str(ends[-1]) if ends and ends[-1] < 2026 else None, labStart=None, labEnd=None,
                            datePrecision='year', endDatePrecision='year' if ends and ends[-1] < 2026 else None,
                            evidence=[{k: best[k] for k in ('url', 'sha256', 'quote', 'observedAt')}] + [{k: f[k] for k in ('url', 'sha256', 'quote', 'observedAt')} for f in found if f is not best][:2],
                            facultyPeriodStatus='supported_start', labPeriodStatus='unresolved', boundaryYearUncertain=True, boundaryMonthUncertain=True,
                            conflictingStartYears=starts if len(starts) > 1 else [], addedBy='claude-faculty-periods-20261021',
                            qualification='Appointment year from the page\'s own statement naming the school; the earliest stated faculty year is kept. '
                                          'Faculty appointment evidence is separate from leadership of each named unit.'))
        nid += 1
    (HERE / 'periods').mkdir(exist_ok=True)
    (HERE / 'periods' / f'{school}-faculty-periods.json').write_text(json.dumps(periods, indent=1, ensure_ascii=False))
    (HERE / 'periods' / f'{school}-holds.json').write_text(json.dumps(holds, indent=1, ensure_ascii=False))
    print(json.dumps(dict(school=school, periods=len(periods), holds=len(holds), conflicts=sum(1 for p in periods if p['conflictingStartYears']))))


if __name__ == '__main__':
    {'fetch': fetch, 'extract': extract}[sys.argv[1]](sys.argv[2])
