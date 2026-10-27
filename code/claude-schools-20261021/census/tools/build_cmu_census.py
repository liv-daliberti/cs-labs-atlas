"""CMU School of Computer Science faculty census, 2016-2026, with the PI determination (step 0 of the four-school
build: every faculty member, then which of them lead a research group).

inputs    the CMU sweep's people/structure.json (967 faculty-role people, their units and the students' advisers) and the
          pages it captured (raw/pages_*.sqlite, by sha256 or URL; the students-repair captures), the collection
          (princeton-live-20261015/atlas/data/collection-cmu.json.gz: person ids, units), and census/captures-cmu.sqlite
          (yearly Wayback captures of the MLD, CSD and SCS-wide faculty listings the sweep lacked; tools/fetch_listings.py).
quotes    every source kept carries a verbatim quote: the captured page's own text (HTML to text, whitespace collapsed)
          around the person's name; a JSON source is quoted from its raw text around the person's andrew id. A source
          whose page does not name the person is dropped (listed in notes).
rank      from the titles the sources state (directory titles, profile titles) and the listing a person appears on:
          emeritus > visiting > adjunct_courtesy (listed only on adjunct / affiliated / courtesy / related listings, or an
          'Adjunct' / 'Courtesy' title) > teaching (Teaching Professor, Lecturer, Instructor) > research (Research
          Professor, Systems / Project / Research Scientist, special faculty) > ladder (Assistant / Associate / full /
          University Professor, chairs; core, voting and tenure-track listings) > unknown. The latest dated evidence wins.
pi        named_lab: a non-umbrella unit (laboratory or group; no center / institute / initiative / program / consortium
          in its name; at most three leaders) whose own page names the person a leader / director / head / primary
          faculty; own_group: a collection research unit led by the person alone; advises_phd: a PhD student or alumnus
          the sweep records with this adviser, quoted from the student's source page. Adjunct / courtesy faculty count
          only with a CMU unit (named_lab or own_group); external adjunct advising alone does not make a CMU group.
units     lab_units: collection unit ids the person leads (named labs and the per-adviser group units), else a proposed
          '<name> research group' with the evidence.
-> census/cmu-faculty.json, census/cmu-report.md, census/cmu-listing-only.json (names on listings the structure lacks)
"""
import gzip, json, re, sqlite3, unicodedata, zlib
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
STAGE = Path('/n/fs/similarity/maxent-grpo/.research-sweeps/claude-cmu-20261017')
REPAIR = Path('/n/fs/similarity/maxent-grpo/.research-sweeps/cmu-students-repair-20261019/rosters/captures')
COLL = Path('/n/fs/similarity/maxent-grpo/princeton-live-20261015/atlas/data/collection-cmu.json.gz')
UMBRELLA = re.compile(r'(?i)\b(center|centre|institute|initiative|program|consortium|alliance|collaborative|school|department|research areas?|cluster)\b')
GROUP_KINDS = {'department_listed_unit', 'scs_listed_unit', 'research_unit', 'project_lab_row'}
AFFIL_URL = re.compile(r'(?i)adjunct|affiliat|affilliat|related-faculty|courtesy|visiting|associated')


def toks(n):
    n = unicodedata.normalize('NFKD', n or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z ]', ' ', n).split()


def key(n):
    return ' '.join(toks(n))


def same_full(a, b):
    x, y = toks(a), toks(b)
    if len(x) < 2 or len(y) < 2 or x[-1] != y[-1]:
        return False
    f, g = sorted([x[0], y[0]], key=len)
    # a short form of the given name (Chris / Christopher), not a near-identical different name (Eunsu / Eunsuk)
    return f == g or (len(f) >= 3 and g.startswith(f) and len(g) - len(f) >= 2)


def name_match(a, b):
    """Same person's name: equal keys, same_full, or the same family name with one name's given name among the other's
    tokens ('Drew Bagnell' / 'J. Andrew (Drew) Bagnell')."""
    x, y = toks(a), toks(b)
    if not x or not y:
        return False
    if x == y or same_full(a, b):
        return True
    return len(x) >= 2 and len(y) >= 2 and x[-1] == y[-1] and ((len(x[0]) >= 3 and x[0] in y[:-1]) or (len(y[0]) >= 3 and y[0] in x[:-1]))


class Pages:
    """Captured pages by sha256 or URL; text cached per sha."""
    def __init__(self):
        self.by_sha, self.by_url, self.cache = {}, {}, {}
        for f in sorted((STAGE / 'raw').glob('pages_*.sqlite')):
            db = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            for u, sha, st in db.execute('SELECT url, sha256, status FROM pages'):
                if st == 200:
                    self.by_url.setdefault(u, (str(f), u, sha))
                    if sha:
                        self.by_sha.setdefault(sha, (str(f), u, sha))
            db.close()
        for p in REPAIR.iterdir():
            self.by_sha.setdefault(p.name.split('.')[0], ('file', str(p), p.name.split('.')[0]))
        cf = HERE / 'captures-cmu.sqlite'
        if cf.exists():
            db = sqlite3.connect(f'file:{cf}?mode=ro', uri=True)
            for u, sha in db.execute('SELECT url, sha256 FROM pages WHERE status=200'):
                self.by_url.setdefault(u, (str(cf), u, sha)); self.by_sha.setdefault(sha, (str(cf), u, sha))
            db.close()
        self.wayback_orig = defaultdict(list)  # original url -> wayback keys
        for u in self.by_url:
            m = re.match(r'https://web\.archive\.org/web/(\d+)(?:id_)?/(.+)$', u)
            if m:
                self.wayback_orig[re.sub(r'^https?://(www\.)?|:80|/$', '', m.group(2))].append(u)

    def locate(self, src):
        if src.get('sha256') and src['sha256'] in self.by_sha:
            return self.by_sha[src['sha256']]
        u = src.get('url') or ''
        if u in self.by_url:
            return self.by_url[u]
        k = re.sub(r'^https?://(www\.)?|:80|/$', '', u)
        if k in self.wayback_orig:
            return self.by_url[sorted(self.wayback_orig[k])[-1]]
        return None

    def text(self, loc):
        store, u, sha = loc
        ck = sha or u
        if ck in self.cache:
            return self.cache[ck]
        if store == 'file':
            raw = Path(u).read_bytes()
        else:
            db = sqlite3.connect(f'file:{store}?mode=ro', uri=True)
            row = db.execute('SELECT body FROM pages WHERE url=?', (u,)).fetchone(); db.close()
            raw = row[0] if row else b''
            try:
                raw = zlib.decompress(raw)
            except Exception:
                pass
        if raw[:4] == b'%PDF':
            t = ''
        elif raw.lstrip()[:1] in (b'{', b'['):
            t = ' '.join(raw.decode('utf-8', 'ignore').split())
        else:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, 'html.parser')
            for x in soup(['script', 'style', 'noscript']):
                x.decompose()
            t = ' '.join(soup.get_text(' ', strip=True).split())
        if len(self.cache) > 3000:
            self.cache.clear()
        self.cache[ck] = t
        return t


def quote_for(text, names, andrew=None, width=110):
    """Verbatim text around the first occurrence of one of the names (or the andrew id in JSON)."""
    if not text:
        return None
    cands = []
    for n in names:
        if not n:
            continue
        i = text.find(n)
        if i < 0:
            i = text.lower().find(n.lower())
        if i < 0 and ',' not in n and len(n.split()) >= 2:  # 'Last, First' listings
            parts = n.split(); rev = parts[-1] + ', ' + ' '.join(parts[:-1])
            i = text.find(rev)
        if i >= 0:
            cands.append(i)
    if not cands and andrew:
        for pat in (f'"{andrew}"', f'/{andrew}', andrew):
            i = text.find(pat)
            if i >= 0:
                cands.append(i); break
    if not cands:
        return None
    i = min(cands)
    return text[max(0, i - 40): i + width].strip()


TITLE = re.compile(r"((?:Distinguished |Founders |Herbert A\. Simon |University |Assistant |Associate |Full |Adjunct |Visiting |Research |Teaching |Courtesy |"
                   r"Affiliated |Emerit\w+ |Senior |Principal |Special |Systems |Project |Clinical )*(?:Professor|Lecturer|Scientist|Instructor|Faculty|Fellow|"
                   r"Post[- ]?[Dd]octoral \w+|Postdoc\w*|Ph\.?D\.? [Ss]tudent|Graduate [Ss]tudent|Director|Co-?[Ff]ounder|Chair|Dean)(?: (?:of|in) [A-Z][\w&,.\- ]{2,50}| Emerit\w+)?)")
NOT_FACULTY = re.compile(r'(?i)post[- ]?doctoral|postdoc|ph\.?d\.? student|graduate student|doctoral student|teaching assistant|research assistant|student intern|\bta\b')
JUNK = re.compile(r'(?i)\b(professor|college|institute|department|school|center|university|leader|specialist|director)\b|\bdean\b(?=\s*(?:,|&|of\b))')


def title_after(quote, names):
    for n in names:
        i = quote.find(n)
        if i >= 0:
            m = TITLE.search(quote[i + len(n): i + len(n) + 110])
            if m:
                return m.group(1).strip(' ,')
    return None


def title_window(text, names):
    """(quote, title) at the first mention of a name that a title directly follows: a CSD profile names the person in
    its header first and gives the title only at the second mention ('Samson Zhou Post Doctoral Fellow Office: ...')."""
    for n in names:
        for m in list(re.finditer(re.escape(n), text))[:6]:
            t = TITLE.match(text[m.end(): m.end() + 110].lstrip(' ,|-'))
            if t:
                return text[max(0, m.start() - 40): m.end() + 110].strip(), t.group(1).strip(' ,')
    return None, None


ROW_TITLE =re.compile(r'(?i)professor|lecturer|scientist|instructor|faculty|fellow|researcher|dean|chair|emerit|director')


def parse_listing(raw):
    """Page text (made as Pages.text makes it) and the person rows of a faculty listing: Drupal view tables (name cells
    and a title cell; 'Last, First' or separate cells) and the MLD heading pairs (a name heading, the title heading
    under it). Each row: name (given name first), title, href, and text, the row's own text, a substring of the page
    text, or None when the pair is not contiguous there."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw, 'html.parser')
    for x in soup(['script', 'style', 'noscript']):
        x.decompose()
    flat = lambda el: ' '.join(el.get_text(' ', strip=True).split())
    text, rows = flat(soup), []
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        cell = lambda pat: next((td for td in tds if re.search(pat, ' '.join(td.get('class') or []))), None)
        last, first, title = cell(r'last-name'), cell(r'first'), cell(r'title')
        nm = last or first
        if not nm:
            continue
        a = nm.find('a')
        if title:
            ttl = flat(title)
            s = flat(nm)
        elif a and flat(nm).startswith(flat(a)):  # 2026: '<a>Balcan, Maria</a><br>Cadence Design Systems Professor' in one cell
            s, ttl = flat(a), flat(nm)[len(flat(a)):].strip()
        else:
            continue
        if not ttl:
            continue
        if last and first:
            name = f'{flat(first)} {flat(last)}'
        else:
            name = ' '.join(x.strip() for x in reversed(s.split(',', 1))) if ',' in s else s
        rows.append(dict(name=name, title=ttl, href=a.get('href') if a else None, text=flat(tr)))
    for h in soup.find_all(['h1', 'h2']):
        nxt = h.find_next_sibling(['h2', 'h3'])
        if not nxt or int(nxt.name[1]) != int(h.name[1]) + 1 or 'collapsed' in (nxt.get('class') or []):
            continue
        name, title = flat(h), flat(nxt)
        if not ROW_TITLE.search(title) or not 2 <= len(name.split()) <= 5 or re.search(r'\d', name):
            continue
        a = h.find('a')
        pair = f'{name} {title}'
        rows.append(dict(name=name, title=title, href=a.get('href') if a else None, text=pair if pair in text else None))
    return text, rows


ADVISING = re.compile(r'(?i)advis|\bchair\b|supervis')


def pair_quote(text, student_names, adviser_names, span=600):
    """Verbatim text containing a student's name and the adviser's family name close together, with an advising word
    (advisor / adviser / chair / supervisor) in the quote; a bare name list is not advising evidence."""
    q = _pair_quote(text, student_names, adviser_names, span)
    return q if q and ADVISING.search(q) else None


def _pair_quote(text, student_names, adviser_names, span=600):
    fams = {toks(a)[-1] for a in adviser_names if toks(a)}
    low = text.lower()
    for sn in student_names:
        for m in re.finditer(re.escape(sn.lower()), low):
            lo, hi = max(0, m.start() - span), m.end() + span
            win = low[lo:hi]
            for f in fams:
                j = win.find(f)
                if j >= 0 and len(f) >= 3:
                    a, b = sorted([m.start(), lo + j])
                    return text[max(0, a - 30): max(b + len(f), m.end()) + 40].strip()
    # the student's own page (a thesis abstract or profile, not a listing): the adviser's line on it, e.g. the thesis
    # committee ('Thesis Committee: Takeo Kanade, Chair ...')
    if len(text) < 30000 and any(sn.lower() in low for sn in student_names) and 'read full bio' not in low:
        for a in adviser_names:
            i = text.find(a)
            if i < 0:
                fam = (toks(a) or [''])[-1]
                m = re.search(r'(?i)\b' + re.escape(fam) + r'\b', text) if len(fam) >= 3 else None
                i = m.start() if m else -1
            if i >= 0:
                return text[max(0, i - 120): i + 150].strip()
    return None


def year_of(src):
    u = src.get('url') or ''
    m = re.search(r'web\.archive\.org/web/(\d{4})', u)
    if m:
        return int(m.group(1))
    if src.get('capture'):
        return int(str(src['capture'])[:4])
    if src.get('fetched_at'):
        return int(src['fetched_at'][:4])
    return None


def title_cat(t):
    t = t or ''
    if re.search(r'(?i)emerit', t): return 'emeritus'
    if NOT_FACULTY.search(t) or re.search(r'(?i)graduate assistant', t): return 'not_faculty'
    if re.search(r'(?i)visiting|collaborating visitor', t): return 'visiting'
    if re.search(r'(?i)\badjunct\b|courtesy|affiliated', t): return 'adjunct_courtesy'
    if re.search(r'(?i)teaching|lecturer|instructor', t): return 'teaching'
    if re.search(r'(?i)research (?:assistant |associate )?prof|systems scientist|project scientist|research scientist|special faculty|principal scientist|senior scientist|research faculty|researcher associate', t): return 'research'
    if re.search(r'(?i)prof\.?\b|professor|\bchair\b', t): return 'ladder'
    return None


PREC = ['emeritus', 'ladder', 'research', 'teaching', 'adjunct_courtesy', 'visiting', 'not_faculty']


SCS_HOME = re.compile(r'(?i)robotics institute|human[- ]computer interaction|language technologies|machine learning|computer science department|'
                      r'school of computer science|software and societal systems|institute for software research|computational biology')


def listing_kind(u):
    # the SCS directory lists everyone; CSD files systems scientists, lecturers and career professors under
    # people/adjunct-faculty/, so that path says nothing about the appointment (the title does); the S3D faculty
    # index mixes core and affiliated faculty (their profile paths, core-faculty/ or affiliated-fac/, tell them apart)
    if re.search(r'(?i)scs_directory|directory/api|directory_all|/people/adjunct-faculty/|s3d\.cmu\.edu/people/faculty-index', u): return 'neutral'
    if re.search(r'(?i)postdoc|student|alumni|phd|fellows/', u): return 'other'
    if AFFIL_URL.search(u): return 'affiliated'
    return 'core'


def rank_of(titles, listings):
    """titles: [(year, title)] from directory / profile / listing sources; listings: [(year, url + kind + categories)].
    Returns (rank, SCS appointment: core | affiliated | unlisted)."""
    cats = [(y, title_cat(t)) for y, t in titles if title_cat(t)]
    ly = max([y for y, _ in cats] or [0])
    latest = {c for y, c in cats if y == ly}
    best = next((c for c in PREC if c in latest), None)
    kinds = {listing_kind(u) for _, u in listings}
    # a title naming an SCS department as the person's own (Professor, Robotics Institute ...) is a core appointment
    # even when the only listing is another department's affiliated list
    home = any(SCS_HOME.search(t) and title_cat(t) in ('ladder', 'research', 'teaching') and not re.search(r'(?i)affiliat|adjunct|courtesy|consulting|university of|federal university', t)
               for _, t in titles)
    appt = 'core' if 'core' in kinds or home else 'affiliated' if 'affiliated' in kinds else 'unlisted'
    if appt == 'affiliated' and best not in ('emeritus', 'visiting', 'not_faculty'):
        return 'adjunct_courtesy', appt
    return best or 'unknown', appt

def main():
    S = json.loads((STAGE / 'people' / 'structure.json').read_text())
    C = json.loads(gzip.decompress(COLL.read_bytes()))
    P = Pages()
    cp = defaultdict(list)
    for p in C['people']:
        for n in [p['name']] + list(p.get('aliases') or []):
            cp[key(n)].append(p['id'])
    cunits = {u['id']: u for u in C['units']}
    cunits_by_leader = defaultdict(list)
    for u in C['units']:
        for l in u.get('leaders') or []:
            cunits_by_leader[key(l)].append(u['id'])
    sunits = {u['id']: u for u in S['units']}
    # advising: students by adviser
    advisees = defaultdict(list)
    for p in S['people']:
        if set(p.get('roles') or []) & {'phd_student', 'phd_alumnus'}:
            for a in p.get('advisers') or []:
                advisees[key(a)].append(p)
    adv_by_fam = defaultdict(set)
    for a in advisees:
        if a:
            adv_by_fam[a.split()[-1]].add(a)
    fac = [p for p in S['people'] if 'faculty' in (p.get('roles') or [])]
    # new listing captures (census/captures-cmu.sqlite): text per page with year and kind
    listings = []
    cf = HERE / 'captures-cmu.sqlite'
    if cf.exists():
        db = sqlite3.connect(f'file:{cf}?mode=ro', uri=True)
        for u, ts, dept, kind, sha, body in db.execute('SELECT url, timestamp, dept, kind, sha256, body FROM pages WHERE status=200'):
            text, rows = parse_listing(zlib.decompress(body))
            listings.append(dict(url=u, year=int(ts[:4]), dept=dept, kind=kind, sha=sha, text=text, rows=rows))
        db.close()
    out, report_rows = [], Counter()
    for p in fac:
        names = list(dict.fromkeys([p['name']] + list(p.get('names') or [])))
        andrew = next((s.get('andrew_id') for s in p.get('sources') or [] if s.get('andrew_id')), None)
        sources, titles, lst, dropped = [], [], [], []
        for s in p.get('sources') or []:
            loc = P.locate(s)
            q = quote_for(P.text(loc), names, andrew) if loc else None
            y = year_of(s)
            kind = s.get('source_kind') or s.get('kind') or ''
            url = s.get('url') or s.get('page') or ''
            t = [x for x in ([s.get('title')] if s.get('title') else []) + list(s.get('titles') or []) if x]
            if q and loc and 'directory' in kind:  # the SCS directory JSON: the person's record through its "titl" list
                txt = P.text(loc)
                m = next((m for n in names for m in [re.search(r'"n":"' + re.escape(n) + r'"[^{}]{0,300}?"titl":\[([^\]]*)\]', txt)] if m), None)
                if m:
                    q = txt[max(0, m.start() - 60): m.end()]
                    try:
                        t = [x for x in json.loads('[' + m.group(1) + ']') if isinstance(x, str) and x]
                    except ValueError:
                        pass
            if q:
                pubkind = re.search(r'(?i)thesis|kilthub|publication|tech_report|dissertation|event|report', kind)
                if not pubkind:
                    titles += [(y or 0, x) for x in t]
                    ta = title_after(q, names)
                    if not t and not ta:
                        q2, ta = title_window(P.text(loc), names)
                        q = q2 or q
                    if ta and not t:
                        titles.append((y or 0, ta))
                sources.append(dict(url=url, sha256=loc[2], quote=q, observed=y, kind=kind))
                if re.search(r'(?i)listing|index|roster|directory|drupal_faculty|lti_faculty|mld_index|sc_people|csd_profile|scs_dir', kind) or re.search(r'/(?:core-faculty|affiliated-fac\w*)/', url):
                    lst.append((y or 0, url + ' ' + kind + ' ' + ' '.join(s.get('categories') or [])))
            else:
                dropped.append(dict(url=url, kind=kind, reason='page not on disk' if not loc else 'page does not name the person'))
        for L in listings:  # yearly listing captures the sweep lacked; the person's own row gives quote, title and href
            row = next((r for r in L['rows'] if any(name_match(r['name'], n) for n in names)), None)
            if row and row['text']:
                q, t = row['text'][:300], row['title']
            else:
                q = quote_for(L['text'], names)
                t = (row or {}).get('title') or (title_after(q, names) if q else None)
            if q:
                sources.append(dict(url=L['url'], sha256=L['sha'], quote=q, observed=L['year'], kind=f"wayback_{L['dept'].lower()}_{L['kind']}"))
                lst.append((L['year'], L['url'] + ' ' + L['kind'] + ' ' + (t or '')))  # 'Affiliated Faculty' on a core list is affiliated
                if t:
                    titles.append((L['year'], t))
        years = sorted({s['observed'] for s in sources if s['observed'] and 2016 <= s['observed'] <= 2026})
        rank, appointment = rank_of(titles, lst)
        ly = max([y for y, t in titles if title_cat(t)] or [0])
        latest_title = next((t for y, t in sorted(titles, reverse=True) if y == ly and title_cat(t) == rank), None) or \
            next((t for y, t in sorted(titles, reverse=True) if y == ly and title_cat(t)), sorted(titles)[-1][1] if titles else None)
        # PI
        basis = None
        led_named = []
        for uid in p.get('units_led') or []:
            u = sunits.get(uid)
            if not u or u['unitType'] == 'adviser_group_listing':
                continue
            leaders = [n for n, v in u['leaders'].items() if v.get('role') == 'leader']
            mine = next((n for n in leaders if any(same_full(n, x) for x in names)), None)
            if not mine or len(leaders) > 3 or UMBRELLA.search(u['name']):
                continue
            v = u['leaders'][mine]
            loc = P.locate(dict(sha256=v.get('sha256'), url=v.get('source')))
            q = quote_for(P.text(loc), [mine] + names) if loc else None
            if q:
                led_named.append(uid)
                basis = basis or dict(kind='named_lab', unit=uid, unit_name=u['name'], url=v.get('source'), quote=q, how=v.get('how'))
        own = [uid for uid in cunits_by_leader.get(key(p['name']), []) if cunits[uid].get('kind') == 'research_unit' and len(cunits[uid].get('leaders') or []) == 1]
        if not basis and own:
            u = sunits.get(own[0]) or {}
            v = next((v for n, v in (u.get('leaders') or {}).items() if any(same_full(n, x) for x in names)), None)
            loc = P.locate(dict(sha256=v.get('sha256'), url=v.get('source'))) if v else None
            q = quote_for(P.text(loc), names) if loc else None
            if q:
                basis = dict(kind='own_group', unit=own[0], unit_name=cunits[own[0]]['name'], url=v.get('source'), quote=q)
        if not basis:  # the person's own homepage or lab page listing their students / group (a captured page)
            solo = [uid for uid in (p.get('units_led') or []) if sunits.get(uid) and sum(1 for v in sunits[uid]['leaders'].values() if v.get('role') == 'leader') <= 1
                    and not UMBRELLA.search(sunits[uid]['name'])]
            for u in [p.get('website')] + [x for uid in solo for x in sunits[uid].get('urls') or []]:
                if not u:
                    continue
                loc = P.locate(dict(url=u))
                t = P.text(loc) if loc else ''
                fam = (toks(p['name']) or [''])[-1]
                if not t or fam not in t.lower():
                    continue
                # a heading followed by people's names ('Current PhD Students Anna Fang ...'), not course text
                m = next((mm for mm in re.finditer(r'(?:(?:Current|Former) )?(?:Ph\.?\s?D\.?|Doctoral|Graduate) [Ss]tudents(?: and [A-Z][a-z]+)?:?|Advisees:?|(?:Lab|Group) [Mm]embers:?', t)
                          if re.match(r'\s*:?\s*(?:\(?[^A-Za-z]{0,6})?[A-Z][a-z]+(?:[- ][A-Z][a-z]+)+', t[mm.end(): mm.end() + 60])), None)
                if m:
                    basis = dict(kind='own_group', unit=None, url=u, quote=t[max(0, m.start() - 80): m.end() + 200].strip())
                    break
        studs = [s for n in names for a in adv_by_fam.get((toks(n) or [''])[-1], []) if same_full(a, n) for s in advisees[key(a)]]
        studs = list({s['name']: s for s in studs}.values())
        if not basis and studs:
            for st in studs:
                for s in st.get('sources') or []:
                    loc = P.locate(s)
                    t = P.text(loc) if loc else ''
                    q = pair_quote(t, [st['name']] + list(st.get('names') or []), names) if t else None
                    if q:
                        basis = dict(kind='advises_phd', student=st['name'], url=s.get('url') or s.get('page'), quote=q[:700], students=len(studs)); break
                if basis:
                    break
        junk = bool(JUNK.search(p['name']) or re.search(r'(?i)^(?:contact us|send message|read more|home|people)$', p['name'])) or len(toks(p['name'])) < 2
        not_faculty = rank == 'not_faculty'
        if re.search(r'(?i)co-?founder|director of [A-Z]|\binc\b|corporation|microsoft|google|amazon|ibm\b', latest_title or '') and rank in ('unknown', 'research'):
            rank = 'adjunct_courtesy'  # an outside position on a department faculty listing
        if junk:
            rank = 'unknown'
        external_adjunct = rank == 'adjunct_courtesy' and re.search(r'(?i)\badjunct\b|co-?founder|director of|\binc\b', latest_title or '')
        # advising alone makes a CMU group only for someone who held a core SCS appointment at some point in 2016-2026
        # (faculty who left and now hold an adjunct title led CMU groups while they were here)
        is_pi = bool(basis) and not junk and not not_faculty and not (rank == 'adjunct_courtesy' and basis['kind'] == 'advises_phd' and external_adjunct and appointment != 'core')
        if rank in ('visiting',) and basis and basis['kind'] == 'advises_phd' and appointment != 'core':
            is_pi = False
        history = {}
        for y, t in titles:
            c = title_cat(t)
            if c and y and (y not in history or PREC.index(c) < PREC.index(history[y])):
                history[y] = c
        cids = list(dict.fromkeys(cp.get(key(p['name']), [])))
        led = [u for u in dict.fromkeys(list(p.get('units_led') or []) + cunits_by_leader.get(key(p['name']), [])) if u in cunits]
        # a lab unit is a group the person leads: not an umbrella (center, institute, research area) and at most three
        # leaders; the per-adviser listing units stay apart (advising is not lab membership)
        def group_like(uid):
            u, su = cunits[uid], sunits.get(uid) or {}
            n_lead = sum(1 for v in (su.get('leaders') or {}).values() if v.get('role') == 'leader') or len(u.get('leaders') or [])
            return u.get('kind') in GROUP_KINDS and not UMBRELLA.search(u['name']) and n_lead <= 3
        lab_units = [u for u in led if group_like(u)]
        adviser_units = [u for u in led if cunits[u].get('kind') == 'adviser_group_listing']
        if is_pi and not lab_units:
            lab_units = [dict(proposed=True, name=f"{p['name']} research group", url=p.get('website'), evidence=basis)]
        notes = []
        if dropped:
            notes.append(f"{len(dropped)} source(s) without a quote: " + '; '.join(sorted({d['reason'] for d in dropped})))
        if not sources:
            notes.append('no source page names the person (structure-only)')
        if len(cids) > 1:
            notes.append(f'{len(cids)} collection records carry this name')
        if junk:
            notes.append('not a person name (a title or unit string the sweep parsed as a name)')
        if not_faculty:
            notes.append('the latest stated titles are postdoc / student / TA titles: not faculty')
        out.append(dict(name=p['name'], aliases=[n for n in names if n != p['name']], collection_person_id=cids[0] if len(cids) == 1 else None,
                        structure_name=p['name'], profile_url=next((s['url'] for s in sources if re.search(r'profile|/people/(?:faculty|core-faculty)', s['kind'] + s['url'])), None),
                        dblp=(p.get('dblp') or [None])[0], rank=rank, rank_by_year={str(y): history[y] for y in sorted(history)}, title_as_listed=latest_title, titles_history=sorted({t for _, t in titles}),
                        departments=p.get('departments') or [], scs_appointment=appointment, years_listed=years, sources=sources, is_pi=is_pi, not_faculty=junk or not_faculty,
                        pi_basis=basis or dict(kind='none'), advised_phd=len(studs), lab_units=lab_units, adviser_group_units=adviser_units, notes=notes))
        report_rows[(rank, is_pi)] += 1
    # names on the new listings that the structure lacks
    known = {key(n) for p in S['people'] for n in [p['name']] + list(p.get('names') or [])}
    fam_known = defaultdict(set)
    for k in known:
        if k:
            fam_known[k.split()[-1]].add(k)
    def seen(x):
        xt = x.split()
        return x in known or any(name_match(x, k) for k in fam_known.get(xt[-1], ())) or any(k.split()[0][:1] == xt[0][:1] for k in fam_known.get(xt[-1], ()))
    listing_only = defaultdict(lambda: dict(years=set(), urls=set(), titles=[], quotes=[], depts=set()))
    for L in listings:
        for row in L['rows']:
            n = re.sub(r'^(?:Dr\.?|Prof\.?)\s+|,?\s+(?:Ph\.?D\.?|Jr\.?)$', '', row['name']).strip()
            t = toks(n)
            if len(t) < 2 or JUNK.search(n) or title_cat(row['title']) in (None, 'not_faculty') or seen(' '.join(t)):
                continue
            r = listing_only[key(n)]; r['name'] = n; r['years'].add(L['year']); r['urls'].add(L['url']); r['depts'].add(L['dept'])
            if row['title'] not in r['titles']:
                r['titles'].append(row['title'])
            if len(r['quotes']) < 2:
                q = (row['text'] or quote_for(L['text'], [row['name']]) or '')[:300]
                if q and q not in r['quotes']:
                    r['quotes'].append(q)
    lo = [dict(name=v['name'], departments=sorted(v['depts']), years=sorted(v['years']), titles=v['titles'], rank=rank_of([(max(v['years']), v['titles'][-1])], [])[0],
               urls=sorted(v['urls'])[:3], quotes=v['quotes']) for v in listing_only.values()]
    (HERE / 'cmu-faculty.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    (HERE / 'cmu-listing-only.json').write_text(json.dumps(sorted(lo, key=lambda x: x['name']), indent=1, ensure_ascii=False))
    print(json.dumps(dict(faculty=len(out), by_rank=dict(Counter(r['rank'] for r in out)), pis=sum(r['is_pi'] for r in out),
                          pi_basis=dict(Counter(r['pi_basis']['kind'] for r in out if r['is_pi'])), listing_only=len(lo),
                          no_sources=sum(1 for r in out if not r['sources']))))


if __name__ == '__main__':
    main()
