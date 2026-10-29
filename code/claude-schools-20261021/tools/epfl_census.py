"""EPFL IC faculty census and PI determination, 2016-2026 (step 0 of the four-school build, 2026-10-21).

Inputs, read only: the EPFL sweep (../claude-epfl-20261019): people/dept_ic.json (one row per observation of a person on a
page: IC faculty listings live and Wayback 2016-2026, the EDIC lab table, EDIC thesis directors, people.epfl.ch profiles,
lab pages, the frozen unit API) with the page bodies it cached (raw/pages_ic_people.sqlite), people/structure.json, and
the Infoscience OrgUnit search responses of the 2026-10-13 EPFL stage (crisou.director); the site collection
princeton-live-20261015/atlas/data/collection-epfl.json.gz (person ids, units). Nothing is fetched here.

person     dept_ic rows of role faculty, joined by people.epfl.ch handle, SCIPER or person_id.
rank       from the latest title a listing gives (the IC faculty page and its captures, then the profile, then the EDIC
           thesis-director list): Full Professor -> full_professor; Associate -> associate_professor; (Tenure Track)
           Assistant -> assistant_professor_tenure_track; Adjunct / External adjunct -> adjunct; Professeur titulaire ->
           titular_professor; Senior Scientist / MER -> mer_senior_scientist; Emeritus / Honorary -> emeritus; Courtesy
           Appointments, External faculty members, the EDIC table's outside-IC rows and thesis directors with no IC listing
           -> affiliated_other_school; visiting / academic hosts / guests -> unknown (noted).
PI         is_pi with the strongest basis: lab_head (the 2016-2019 faculty page card names the professor's lab, the EDIC
           lab table pairs the professor with a lab, or the sweep's unit records name them leader: Infoscience director,
           unit head); own_group (a professor whose profile position is a lab unit; never for senior scientists); advises_phd
           (EDIC thesis director or a profile listing PhD students, no lab found); none. Every basis quotes the page.
quotes     verbatim text of the cached page (HTML reduced to its text, whitespace collapsed) around the person's name.
lab_units  collection units the person leads (collection leaders, the structure's units_led, the lab acronym), else a
           proposed unit {name, acronym, url, evidence}.
-> census/epfl-faculty.json, census/epfl-report.md
"""
import gzip, json, re, sqlite3, unicodedata, zlib
from collections import Counter, defaultdict
from pathlib import Path

SW = Path('/n/fs/resemble/maxent-grpo/.research-sweeps')
ADMIN = re.compile(r'^(?:IC-|SIN-|SSC-|TBC$|TBD$|N/?A$|NANO-?TERA$)|deanship|teaching|committee', re.I)  # administrative or placeholder units, not labs
EP = SW / 'claude-epfl-20261019'
OUT = SW / 'claude-schools-20261021' / 'census'
STAGE = Path('/n/fs/resemble/homogenizing-science/data/reviews/unipapers/swiss-federal-institute-of-technology-lausanne')
COLL = Path('/n/fs/resemble/maxent-grpo/princeton-live-20261015/atlas/data/collection-epfl.json.gz')


def nt(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower())


def toks(n):
    return re.sub(r'[^a-z ]', ' ', unicodedata.normalize('NFKD', n or '').encode('ascii', 'ignore').decode().lower()).split()


def same_full(a, b):
    x, y = toks(a), toks(b)
    if len(x) < 2 or len(y) < 2 or x[-1] != y[-1]:
        return False
    f, g = x[0], y[0]
    return f == g or (min(len(f), len(g)) >= 3 and (f.startswith(g) or g.startswith(f)))


_PAGES, _DB = {}, None


def page_text(url):
    """The cached page reduced to text (whitespace collapsed), or ''."""
    global _DB
    if url in _PAGES:
        return _PAGES[url]
    if _DB is None:
        _DB = sqlite3.connect(f'file:{EP / "raw" / "pages_ic_people.sqlite"}?mode=ro', uri=True)
    row = _DB.execute('SELECT body, status FROM pages WHERE url = ? OR final_url = ?', (url, url)).fetchone()
    if not row and (OUT / 'raw' / 'profiles.sqlite').exists():  # profiles fetched for this census (tools/epfl_profiles.py)
        row = sqlite3.connect(f"file:{OUT / 'raw' / 'profiles.sqlite'}?mode=ro", uri=True).execute(
            'SELECT body, status FROM pages WHERE url = ? OR final_url = ?', (url, url)).fetchone()
    t = ''
    if row and row[0] and row[1] == 200:
        raw = row[0]
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass
        html = raw.decode('utf-8', 'ignore')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for x in soup(['script', 'style', 'noscript']):
            x.decompose()
        t = ' '.join(soup.get_text(' ').split())
    _PAGES[url] = t
    return t


def quote(url, name, near=None, width=200):
    """Verbatim text around the person's name on the cached page (the name as printed, given-first or family-first),
    preferring an occurrence followed within `width` characters by `near` (a title or lab acronym)."""
    t = page_text(url)
    if not t:
        return None
    parts = name.split()
    variants = list(dict.fromkeys([name, ' '.join(parts[-1:] + parts[:-1]), ' '.join(parts[1:] + parts[:1]),
                                   f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else name, f"{parts[0]}, {' '.join(parts[1:])}" if len(parts) > 1 else name]))
    for v in variants:
        hits = [m.start() for m in re.finditer(re.escape(v), t)]
        if near:
            close = [i for i in hits if near in t[i: i + len(v) + width]]
            hits = close or hits
        if hits:
            i = hits[0]
            return t[max(0, i - 60): i + len(v) + width].strip()
    return None


def is_json_quote(stage_body, unit_acr, director):
    """Verbatim JSON text of an Infoscience OrgUnit record naming the director, near the unit acronym."""
    i = stage_body.find(f'"value" : "{unit_acr}"')
    if i < 0:
        return None
    j = stage_body.find(director, max(0, i - 4000), i + 6000)
    return stage_body[max(0, j - 120): j + len(director) + 40] if j >= 0 else None


def rank_of(title, section, scope):
    t = (title or '').lower(); s = (section or '').lower()
    if 'emerit' in t or 'emerit' in s or 'honorary' in s or 'honoraire' in t:
        return 'emeritus'
    if 'senior scientist' in t or 'senior scientist' in s or re.search(r'\bmer\b', t):
        return 'mer_senior_scientist'
    if 'visiting' in t or 'visiting' in s or 'academic host' in s or 'academic guest' in t or 'guest' in t or 'host professor' in t or t == 'lecturer':
        return 'unknown'
    if 'courtesy' in s or 'external faculty' in s or scope == 'edic_affiliated_outside_ic':
        return 'affiliated_other_school'
    if 'adjunct' in t or 'adjunct' in s:
        return 'adjunct'
    if 'titulaire' in t:
        return 'titular_professor'
    if 'full professor' in t or t == 'professor' or 'professeur ordinaire' in t:
        return 'full_professor'
    if 'associate professor' in t or 'associé' in t:
        return 'associate_professor'
    if 'assistant professor' in t or 'tenure track' in t:
        return 'assistant_professor_tenure_track'
    return None


def year_of(src):
    return int((src.get('capture') or src.get('fetched_at') or '2026')[:4])


def main():
    d = json.load(open(EP / 'people' / 'dept_ic.json'))
    rows = d['people']
    st = json.load(open(EP / 'people' / 'structure.json'))
    C = json.loads(gzip.open(COLL).read())
    # Infoscience OrgUnit search responses (crisou.director), for verbatim JSON quotes
    stage_bodies = {}
    for line in (STAGE / 'infoscience' / 'sources.jsonl').open():
        s = json.loads(line)
        if 'configuration=orgunit' in s.get('requested_url', '') and s.get('http_status') == 200:
            p = Path('/n/fs/resemble/homogenizing-science') / s['snapshot_path'] if not s['snapshot_path'].startswith('/') else Path(s['snapshot_path'])
            if p.exists():
                b = p.read_bytes()
                stage_bodies[s['source_id']] = (s['requested_url'], s['sha256'], (gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b).decode('utf-8', 'ignore'))
    orgunits = {o['acronym']: o for o in json.load(open(STAGE / 'infoscience' / 'orgunits.json')) if o.get('acronym')}
    # people: faculty rows grouped (handle / sciper / person_id)
    fac_ids = {r['person_id'] for r in rows if r['role'] == 'faculty'}
    groups, alias = defaultdict(list), {}
    for r in rows:
        if r['person_id'] not in fac_ids:
            continue
        k = alias.get(('h', r.get('handle'))) or alias.get(('s', r.get('sciper'))) or r['person_id']
        for a in (('h', r.get('handle')), ('s', r.get('sciper'))):
            if a[1]:
                alias.setdefault(a, k)
        groups[k].append(r)
    # collection
    cpeople = C['people']; c_by_sciper = {p.get('sciper'): p['id'] for p in cpeople if p.get('sciper')}
    c_by_name = defaultdict(list)
    for p in cpeople:
        c_by_name[nt(p['name'])].append(p['id'])
    cunits = {u['id']: u for u in C['units']}
    s_by_name = {nt(p['name']): p for p in st['people']}
    core = lambda x: re.sub(r'laborator(?:y|ies|e)|lab|chair of|chaire|group|groupe|the|of|and|for|in', '', nt(x or ''))
    by_acr = {nt(u['acronym']): u['id'] for u in C['units'] if u.get('acronym')}
    by_core = defaultdict(set)
    for u in C['units']:
        if u.get('kind') != 'adviser_group_listing':
            by_core[core(u['name'])].add(u['id'])
    for u in d['units']:  # the sweep's units: name -> acronym
        if u.get('acronym') and nt(u['acronym']) in by_acr:
            by_core[core(u['name'])].add(by_acr[nt(u['acronym'])])
    host_acr = {}
    for u in d['units']:
        if u.get('url') and u.get('acronym') and nt(u['acronym']) in by_acr:
            host_acr.setdefault(re.sub(r'^www\.', '', (re.sub(r'^https?://', '', u['url']).split('/')[0])), by_acr[nt(u['acronym'])])

    def resolve_unit(label, url):
        if nt(label) in by_acr:
            return by_acr[nt(label)]
        ids = by_core.get(core(label)) or set()
        if len(ids) == 1:
            return next(iter(ids))
        if url:
            h = re.sub(r'^www\.', '', re.sub(r'^https?://', '', url).split('/')[0])
            return host_acr.get(h)
        return None
    extra = {}
    if (OUT / 'raw' / 'profiles.sqlite').exists():
        pc = sqlite3.connect(f"file:{OUT / 'raw' / 'profiles.sqlite'}?mode=ro", uri=True)
        for url, sha, fetched in pc.execute('SELECT url, sha256, fetched_at FROM pages WHERE status = 200'):
            t = page_text(url)
            m = re.search(r'(Tenure Track Assistant Professor|Associate Professor|Full Professor|Adjunct Professor|Host Professor|Senior Scientist|Lecturer)\s*,\s*([^,]{3,80}?)(?:\s+EPFL\b|$)', t)
            if m:
                extra[url] = dict(title=m.group(1), unit=m.group(2).strip(), sha=sha, fetched=fetched)
    out = []
    for k, rs in groups.items():
        rs.sort(key=lambda r: year_of(r['source']))
        names = sorted({r['name'] for r in rs}, key=lambda n: -sum(1 for r in rs if r['name'] == n))
        name = names[0]
        sciper = next((r.get('sciper') for r in rs if r.get('sciper')), None)
        handle = next((r.get('handle') for r in rs if r.get('handle')), None)
        listing = [r for r in rs if r['source']['kind'] in ('ic_faculty_page', 'ic_faculty_page_wayback')]
        edic_dir = [r for r in rs if r['source']['kind'].startswith('edic_thesis_directors')]
        edic_lab = [r for r in rs if r['source']['kind'] == 'edic_lab_table']
        prof = [r for r in rs if r['source']['kind'] in ('faculty_profile', 'faculty_profile_wayback') and r.get('profile_role') in (None, 'owner') and r['name'] and same_full(r['name'], name)]
        for url, e in extra.items():  # profiles fetched for this census
            hs = {h for h in (handle_ for handle_ in [r.get('handle') for r in rs] + [r.get('sciper') for r in rs]) if h}
            if any(f'/{h}?' in url for h in hs):
                prof.append(dict(name=name, title=e['title'], positions=[dict(title=e['title'], unit=e['unit'], path=['EPFL', 'IC'])],
                                 source=dict(kind='faculty_profile', url=url, sha256=e['sha'], fetched_at=e['fetched'], capture=None)))
        years = sorted({year_of(r['source']) for r in listing + edic_dir + edic_lab})
        # rank: latest listing title (with its section), else profile title, else EDIC director title
        cand = [(year_of(r['source']), r.get('title'), r.get('listing_section'), r.get('scope'), r) for r in listing if r.get('title') or r.get('listing_section')]
        cand += [(year_of(r['source']) - 0.5, r.get('title'), None, None, r) for r in prof if r.get('title')]
        cand += [(year_of(r['source']) - 0.7, r.get('title'), None, r.get('scope'), r) for r in edic_dir if r.get('title')]
        cand += [(year_of(r['source']) - 0.9, None, None, r.get('scope'), r) for r in edic_lab]
        cand.sort(key=lambda c: c[0])
        rank, title, trow = None, None, None
        for y, t, sec, sc, r in reversed(cand):
            rk = rank_of(t, sec, sc)
            if rk:
                rank, title, trow = rk, t or sec, r; break
        if not listing and rank in (None, 'full_professor', 'associate_professor', 'assistant_professor_tenure_track', 'adjunct', 'titular_professor') and \
                all(r.get('scope') in (None, 'edic_thesis_director', 'edic_affiliated_outside_ic') for r in edic_dir + edic_lab) and \
                not any(r.get('scope') == 'ic_faculty' for r in edic_lab) and not any('IC' in (p.get('path') or []) for r in prof for p in r.get('positions') or []):
            rank = 'affiliated_other_school'  # no IC faculty listing and no IC position: another school's faculty
        rank = rank or 'unknown'
        sources = []
        def add_source(r, near=None):
            q = quote(r['source']['url'], r['name'], near)
            if q:
                e = dict(url=r['source']['url'], sha256=r['source'].get('sha256'), quote=q, observed=(r['source'].get('capture') or r['source'].get('fetched_at') or '')[:8])
                if e not in sources:
                    sources.append(e)
                return e
        if trow:
            add_source(trow, title)
        for r in (listing[:1] + listing[-1:] + edic_lab[:1] + edic_dir[-1:]):
            add_source(r, r.get('title') or r.get('lab_as_listed'))
        # units and PI basis
        labs = []  # (acronym or name, url, basis kind, evidence)
        mer = rank == 'mer_senior_scientist'
        inactive_sec = re.compile(r'emerit|honorary|senior scientist|visiting|host', re.I)
        for r in listing:
            # a card in the Emeritus / Honorary / Senior Scientists / visiting sections names the lab a person belongs to,
            # not one they head; a senior scientist heads a group only where a unit record names them head
            if r.get('lab_as_listed') and not mer and not inactive_sec.search(r.get('listing_section') or ''):
                e = add_source(r, r['lab_as_listed'])
                labs.append((r['lab_as_listed'], r.get('lab_url'), 'lab_head', e, 'faculty page card (2016-2019) names the professor\'s lab'))
        for r in edic_lab:
            if r.get('lab_as_listed') and r.get('scope') in ('ic_faculty', 'edic_affiliated_outside_ic') and not mer:  # outside IC: their own lab in another school
                e = add_source(r, r['lab_as_listed'])
                labs.append((r['lab_as_listed'], r.get('lab_url'), 'lab_head', e, 'EDIC affiliated-labs table pairs the professor with the lab'
                             + (' (a lab of another school)' if r.get('scope') == 'edic_affiliated_outside_ic' else '')))
        for u in d['units']:
            lev = [x for k_, v_ in (u.get('leader_evidence') or {}).items() if same_full(k_, name) for x in v_]
            if mer and not any(re.search(r'infoscience_director', x) for x in lev):
                continue  # a senior scientist heads a unit only where its record or its own page names them head
            if any(same_full(l, name) for l in u.get('leaders') or []):
                ev = None
                o = orgunits.get(u.get('acronym'))
                if o and o.get('source_id') in stage_bodies:
                    url, sha, body = stage_bodies[o['source_id']]
                    for dname in o.get('directors') or []:
                        q = is_json_quote(body, u['acronym'], dname)
                        if q:
                            ev = dict(url=url, sha256=sha, quote=q, observed='20261013'); break
                if ev is None:
                    for s in u.get('sources') or []:
                        if s.get('kind') in ('lab_page', 'lab_page_wayback', 'faculty_profile', 'edic_lab_table'):
                            q = quote(s['url'], name, u.get('acronym'))
                            if q:
                                ev = dict(url=s['url'], sha256=None, quote=q, observed=''); break
                labs.append((u.get('acronym') or u['name'], u.get('url'), 'lab_head', ev, 'unit record names the person leader: ' + ', '.join(u.get('leader_evidence', {}).get(name, []) or ['leader'])))
        if rank not in ('mer_senior_scientist', 'unknown', 'emeritus'):
            for r in prof:
                for p in r.get('positions') or []:
                    path = p.get('path') or []
                    if ('IC' in path or rank == 'affiliated_other_school') and re.search(r'professor', p.get('title') or '', re.I) and not re.search(r'host|visiting', p.get('title') or '', re.I) \
                            and len(path) >= 3 and re.search(r'lab|laborator|group|chair', p.get('unit') or '', re.I):
                        e = add_source(r, p.get('unit'))
                        labs.append((path[-1], None, 'own_group', e, f"profile position: {p.get('title')}, {p.get('unit')}"))
        director_of = [r for r in rows if name in (r.get('advisers') or []) or any(same_full(a, name) for a in r.get('advisers') or [])]
        basis = None
        for kind in ('lab_head', 'own_group'):
            hit = next((l for l in labs if l[2] == kind and l[3]), None)
            if hit:
                basis = dict(kind=kind, url=hit[3]['url'], quote=hit[3]['quote'], note=hit[4]); break
        if basis is None and director_of and rank != 'mer_senior_scientist':
            r = next((r for r in edic_dir if quote(r['source']['url'], r['name'])), None)
            if r:
                basis = dict(kind='advises_phd', url=r['source']['url'], quote=quote(r['source']['url'], r['name'], r.get('title')),
                             note=f'EDIC thesis director with {len({x["name"] for x in director_of})} directed doctoral students on record')
        if basis is None and rank == 'mer_senior_scientist':
            hit = next((l for l in labs if l[2] == 'lab_head' and l[3]), None)
            if hit:
                basis = dict(kind='lab_head', url=hit[3]['url'], quote=hit[3]['quote'], note=hit[4])
        # an emeritus is a PI in the window only if a listing gives an active rank in 2016 or later
        active = any(year_of(r['source']) >= 2016 and rank_of(r.get('title'), r.get('listing_section'), r.get('scope')) not in (None, 'emeritus', 'unknown')
                     for r in listing + prof + edic_dir)
        is_pi = bool(basis) and (rank != 'emeritus' or active)
        if rank == 'emeritus' and not active:
            basis = dict(kind='none', url=None, quote=None, note='emeritus throughout 2016-2026 in every listing')
        # collection ids and units
        cid = c_by_sciper.get(sciper) if sciper else None
        if not cid:
            ids = list(dict.fromkeys(i for n in names for i in c_by_name.get(nt(n), [])))
            cid = ids[0] if len(ids) == 1 else None
        sp = s_by_name.get(nt(name)) or next((s_by_name.get(nt(n)) for n in names if s_by_name.get(nt(n))), None)
        lab_units, proposed = [], []
        for uid, u in cunits.items():
            if any(same_full(l, name) for l in u.get('leaders') or []):
                lab_units.append(uid)
        for uid in (sp or {}).get('units_led') or []:
            if uid in cunits and uid not in lab_units:
                lab_units.append(uid)
        for acr, url, kind, e, note in labs:
            if ADMIN.search(acr or ''):
                continue
            uid = resolve_unit(acr, url)
            if uid:
                if uid not in lab_units:
                    lab_units.append(uid)
            elif kind == 'lab_head' and e and not any(p['acronym'] == acr for p in proposed):
                proposed.append(dict(name=(orgunits.get(acr) or {}).get('title') or acr, acronym=acr, url=url, evidence=e, outside_ic='another school' in note))
        if (rank == 'emeritus' and not active) or (rank == 'mer_senior_scientist' and not is_pi):
            lab_units, proposed = [], []  # no head evidence: the structure's leader list alone does not make one
        listings = [u for u in lab_units if cunits[u].get('kind') == 'adviser_group_listing']
        lab_units = [u for u in lab_units if u not in listings]
        units = list(dict.fromkeys(f"{acr}" for acr, *_ in labs))
        out.append(dict(name=name, aliases=[n for n in names if n != name], collection_person_id=cid, structure_name=(sp or {}).get('name'), sciper=sciper,
                        profile_url=f'https://people.epfl.ch/{handle}' if handle else (f'https://people.epfl.ch/{sciper}' if sciper else None),
                        dblp=(sp or {}).get('dblp') or [], rank=rank, title_as_listed=title, units=units, years_listed=years, sources=sources,
                        is_pi=is_pi, pi_basis=basis or dict(kind='none', url=None, quote=None),
                        lab_units=lab_units + proposed, adviser_listing_units=listings, notes=('visiting / academic host' if rank == 'unknown' and title and re.search(r'visit|host|guest', title, re.I) else '')
                        + ('; no IC faculty listing (EDIC only)' if not listing else '')
                        + ('; former: listed under Professors 2016-2019 with no rank stated, profile gone' if rank == 'unknown' and listing and max(years or [0]) <= 2019 else '') + ('; listing gap: no 2018 capture of the faculty page exists' if years and min(years) <= 2017 and max(years) >= 2019 else '')))
    out.sort(key=lambda x: x['name'])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'epfl-faculty.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    # report
    rk = Counter(x['rank'] for x in out); pis = [x for x in out if x['is_pi']]
    sfac = {nt(p['name']): p['name'] for p in st['people'] if 'faculty' in (p.get('roles') or [])}
    cen = {nt(n) for x in out for n in [x['name']] + x['aliases']}
    listed = {nt(n) for x in out if any('faculty-members' in s['url'] or 'professors' in s['url'] for s in x['sources']) for n in [x['name']] + x['aliases']}
    edic_only = {nt(n) for x in out if not any('faculty-members' in s['url'] or 'professors' in s['url'] for s in x['sources']) for n in [x['name']] + x['aliases']}
    s_not_confirmed = sorted(v for k, v in sfac.items() if k not in listed and k not in cen)
    s_edic_only = sorted(v for k, v in sfac.items() if k not in listed and k in cen)
    listing_not_in_structure = sorted(x['name'] for x in out if not x['structure_name'])
    no_quote = [x['name'] for x in out if not x['sources']]
    lines = ['# EPFL IC faculty census (2016-2026)', '', f'{len(out)} people; {len(pis)} PIs.', '', '## By rank', '']
    lines += [f'- {k}: {v} ({sum(1 for x in out if x["rank"] == k and x["is_pi"])} PIs)' for k, v in rk.most_common()]
    lines += ['', '## PI basis', ''] + [f'- {k}: {v}' for k, v in Counter(x['pi_basis']['kind'] for x in out).most_common()]
    lines += ['', f'## Structure faculty no source confirms ({len(s_not_confirmed)})', ''] + [f'- {n}' for n in s_not_confirmed]
    lines += ['', f'## Structure faculty confirmed only by EDIC pages or profiles, not the IC faculty listing ({len(s_edic_only)})', '',
              'Mostly faculty of other schools who direct EDIC theses or host IC labs (rank affiliated_other_school / unknown).', '']
    lines += [f"- {n} ({next((x['rank'] for x in out if nt(x['name']) == nt(n) or nt(n) in map(nt, x['aliases'])), '?')})" for n in s_edic_only]
    lines += ['', f'## Census people the structure lacks ({len(listing_not_in_structure)})', ''] + [f'- {n}' for n in listing_not_in_structure]
    props = [(x['name'], u) for x in out for u in x['lab_units'] if isinstance(u, dict)]
    lines += ['', f'## Units to create ({len(props)})', '', 'IC labs the collection lacks; entries marked "outside IC" are an affiliated person\'s own lab in another school (record only, not an IC unit).', '']
    lines += [f"- {u['acronym']} ({u['name']}) for {n}: {u.get('url') or ''}{' — outside IC' if u.get('outside_ic') else ''}" for n, u in props]
    lines += ['', f'## People without a quotable source ({len(no_quote)})', ''] + [f'- {n}' for n in no_quote]
    lines += ['', '## Gaps', '', '- No Wayback capture of the IC faculty page exists for 2018 (2017 and 2019 captures bracket it).',
              '- Infoscience directors are often abbreviated ("Bossaerts, P."); a director quote is used only when it sits in the unit\'s own record.']
    (OUT / 'epfl-report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(dict(people=len(out), pis=len(pis), ranks=dict(rk), basis=dict(Counter(x['pi_basis']['kind'] for x in out)),
                          structure_not_confirmed=len(s_not_confirmed), not_in_structure=len(listing_not_in_structure), proposed_units=len(props), no_quote=len(no_quote))))


if __name__ == '__main__':
    main()
