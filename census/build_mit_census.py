"""MIT computer-science faculty census and PI determination, 2016-2026 (step 0 of the four-school build).

Scope: EECS faculty in computer science (EECS listings tagged CSAIL or a II- computer-science area before 2021, [CS] or
[AI+D] without [EE] after), EE faculty who lead a CSAIL group (flagged), and CSAIL principal investigators (the 2018-2021
CSAIL "PI" listings and the 2026 directory's Core/Dual and Emeritus), research scientists among them typed separately.

Sources (all read from existing captures; nothing is fetched again):
  eecs_faculty_advisors   EECS "Faculty & Advisors", Wayback yearly 2016-2021 (../claude-mit-20261020/raw/pages_people.sqlite)
  eecs_role_faculty       EECS faculty listing, Wayback yearly 2021-2026 (same cache)
  csail_pi                CSAIL people with role PI, Wayback yearly 2018-2021 (same cache)
  eecs_directory_2026     the EECS people directory, Codex's capture of 2026-10-19 (../mit-cs-deep-20261019/rosters)
  csail_directory_2026    the CSAIL directory API (Core/Dual, Emeritus, Researchers), Codex's capture of 2026-10-19
  csail_groups_2026       the CSAIL groups API (leads per group), Codex's capture; a group with three or more leads, a
                          community of research or a center is an umbrella, not anyone's own lab
  dspace_phd              EECS Ph.D./Sc.D. theses 2016-2026 with their advisers (Codex's DSpace@MIT metadata snapshot)
  codex_lab_audit         Codex's 101-unit MIT lab audit in the site (atlas/data/mit-lab-audit.json.gz), credited
Every source entry keeps the page URL, its sha256 and a verbatim quote (the page's own text, whitespace collapsed).

rank       from the most recent title as listed: emeritus; ladder_faculty (Assistant/Associate/full or chaired Professor);
           teaching (Lecturer, Instructor, Professor of the Practice); research_scientist_pi (a research scientist or
           engineer listed as a CSAIL PI or leading a group); adjunct_visiting; unknown.
is_pi      named_group: leads a CSAIL group with at most two leads (the groups API quote); own_group: a CSAIL PI listing
           (CSAIL's own "PI" designation) without a named group; advises_phd: an EECS Ph.D. thesis 2016-2026 names them
           adviser; none otherwise.
lab_units  the collection's research-group units they lead (at most two leaders); else a proposed "<Name> group" unit.
-> census/mit-faculty.json, census/mit-report.md
"""
import gzip, hashlib, html, json, re, sqlite3, sys, unicodedata, zlib
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import atlas_paths as P  # noqa: E402  (every path in one place)
SW = P.SWEEPS
STAGE, CODEX = SW / 'claude-mit-20261020', SW / 'mit-cs-deep-20261019'
SITE = P.SITE_DATA


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def toks(n):
    n = unicodedata.normalize('NFKD', n or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z ]', ' ', n).split()


def same_full(a, b):
    x, y = toks(a), toks(b)
    if len(x) < 2 or len(y) < 2 or x[-1] != y[-1]:
        return False
    f, g = x[0], y[0]
    return f == g or (min(len(f), len(g)) >= 3 and (f.startswith(g) or g.startswith(f)))


def flip(n):
    n = re.sub(r'\.$', '', (n or '').strip())
    return ' '.join(reversed([s.strip() for s in n.split(',', 1)])) if ',' in n else n


def cap_text(path):
    raw = gzip.open(path).read().decode('utf-8', 'ignore')
    return raw, clean(re.sub(r'<script.*?</script>|<style.*?</style>', ' ', raw, flags=re.S))


def listings():
    """[(kind, year, name, title, extra, source)] from the MIT sweep's cached yearly listing captures."""
    db = sqlite3.connect(f"file:{STAGE / 'raw/pages_people.sqlite'}?mode=ro", uri=True)
    out = []
    for url, sha, body in db.execute('SELECT url, sha256, body FROM pages WHERE status = 200'):
        m = re.search(r'/web/(\d{14})id_/', url)
        if not m or '/cdx/' in url:
            continue
        ts, year = m.group(1), int(m.group(1)[:4])
        text = zlib.decompress(body).decode('utf-8', 'ignore')
        src = lambda q: dict(url=url, sha256=sha, quote=q[:400], observed=ts)
        if 'faculty-advisors' in url:
            for row in re.split(r'<li class="views-row', text)[1:]:
                mm = re.search(r'card-title"><a href="([^"]*)">(.*?)</a>', row, re.S)
                if mm:
                    title = clean((re.search(r'field-person-title">\s*<div class="field-content">(.*?)</div>', row, re.S) or [None, ''])[1])
                    terms = [clean(t) for t in re.findall(r'<a href="/people/faculty-advisors/\d+">(.*?)</a>', row)]
                    rt = clean(row.split('</li>')[0]); nt_ = clean(mm.group(2)) + ' ' + title
                    q = nt_ if nt_ in rt else clean(mm.group(2))  # name and title as the row prints them (contact details left out)
                    out.append(('eecs_faculty_advisors', year, clean(mm.group(2)), title, dict(areas=terms, website=mm.group(1)), src(q)))
        elif 'role/faculty' in url:
            for e in re.split(r'class="people-entry', text)[1:]:
                mm = re.search(r'<h5><a href="([^"]+)"[^>]*>(.*?)</a></h5>\s*<p>(.*?)</p>', e, re.S)
                if mm:
                    out.append(('eecs_role_faculty', year, clean(mm.group(2)), clean(mm.group(3)), dict(areas=re.findall(r'\[([^\]]+)\]', clean(mm.group(3))), profile=mm.group(1)),
                                src(clean(mm.group(2)) + ' ' + clean(mm.group(3)))))
        elif 'role%3A299' in url:
            for card in re.split(r'class="card person-card', text)[1:]:
                mm = re.search(r'<a href="(/person/[^"]+)"[^>]*>\s*<h2 class="card-heading"><span[^>]*>(.*?)</span>', card, re.S)
                if mm:
                    title = clean((re.search(r'field--name-field-title[^>]*>(.*?)</div>', card, re.S) or [None, ''])[1])
                    role = clean((re.search(r'field--name-field-role[^>]*>(.*?)</div>', card, re.S) or [None, ''])[1])
                    q = clean(card); nt_ = clean(mm.group(2)) + ' ' + title
                    q = nt_ if nt_ in q else clean(mm.group(2))  # name and title as the card prints them (contact details left out)
                    out.append(('csail_pi', year, clean(mm.group(2)), title, dict(csail_role=role, profile='https://www.csail.mit.edu' + mm.group(1)), src(q)))
    return out


def codex_2026():
    out = []
    caps = {}
    for r in json.load(open(CODEX / 'rosters' / 'eecs-directory-entries.json')):
        s = r['directorySource']
        if s['capturePath'] not in caps:
            caps[s['capturePath']] = cap_text(s['capturePath'])[1]
        t = caps[s['capturePath']]; i = t.find(r['name'] + ' ' + r['roleAsListed'][:20])
        q = t[i:i + len(r['name']) + len(r['roleAsListed']) + 1] if i >= 0 else ''
        out.append(('eecs_directory_2026', 2026, r['name'], r['roleAsListed'], dict(areas=r.get('areas') or [], profile=r['profileUrl']),
                    dict(url=s['url'], sha256=s['sha256'], quote=q or None, observed=s['observedAt'], via='Codex mit-cs-deep-20261019 capture')))
    for r in json.load(open(CODEX / 'rosters' / 'csail-profiles.json')):
        dr = r.get('directoryRole') or ''
        if not dr:
            continue
        s = r['directorySource']
        if s['capturePath'] not in caps:
            caps[s['capturePath']] = gzip.open(s['capturePath']).read().decode('utf-8', 'ignore')
        raw = caps[s['capturePath']]
        j = raw.find('"ss_title":"' + r['name'] + '"')
        title_piece = '"ss_title":"' + r['name'] + '"'
        if j < 0 and r.get('profileUrl'):  # the record by its profile path when the listed name differs
            path = '/person/' + r['profileUrl'].rstrip('/').rsplit('/', 1)[-1]
            u_ = raw.find('"ss_url":"' + path + '"')
            j = raw.rfind('"ss_title":', 0, u_) if u_ >= 0 else -1
            mt = re.match(r'"ss_title":"[^"]*"', raw[j:]) if j >= 0 else None
            title_piece = mt.group(0) if mt else ''
        k = raw.rfind('"ss_name":', 0, j) if j >= 0 else -1
        m2 = re.match(r'"ss_name":"[^"]*",\s*"ss_field_title":"[^"]*"', raw[k:]) if k >= 0 else None
        # two verbatim pieces of the person's record, its directory role and title, and its name; the office fields between them are left out
        seg = (re.sub(r'\s+', ' ', m2.group(0)) + ' … ' + title_piece) if m2 and title_piece else ''
        out.append(('csail_directory_2026', 2026, r['name'], r.get('roleAsListed') or '', dict(directory_role=dr, profile=r.get('profileUrl'), aliases=r.get('aliases') or [],
                                                                                              personal=r.get('personalUrls') or []),
                    dict(url=s['url'], sha256=s['sha256'], quote=seg[:400] or None, observed=s['observedAt'], via='Codex mit-cs-deep-20261019 capture',
                         quote_note='two verbatim pieces of one JSON record, joined by " … "' if seg else None)))
    return out


def groups():
    meta = json.load(open(CODEX / 'rosters' / 'groups-api-pages.json'))[0]['source']
    raw = gzip.open(meta['capturePath']).read().decode('utf-8', 'ignore')
    out = []
    for g in json.load(open(CODEX / 'rosters' / 'csail-groups-raw.json')):
        names = []
        j = raw.find('"ss_title":"' + g['name'].strip())
        i = raw.rfind('"sm_leads_title"', 0, j) if j >= 0 else -1
        m = re.search(r'"sm_leads_title":\[(.*?)\]', raw[i:j], re.S) if i >= 0 else None  # the capture breaks lines inside the list
        if m:
            names = re.findall(r'"([^"]+)"', m.group(1))
        q = (re.sub(r'\s+', ' ', m.group(0)) + ' … ' + '"ss_title":"' + g['name'].strip() + '"') if m else ''  # two verbatim pieces of one JSON record
        kind = 'umbrella' if g['groupType'] != 'group' or len(names) >= 3 else 'research_group'
        out.append(dict(name=g['name'].strip(), url=g.get('sourceUrl'), group_type=g['groupType'], leads=names, kind=kind,
                        source=dict(url=meta['url'], sha256=meta['sha256'], quote=q[:500] or None, observed=meta['observedAt'], via='Codex mit-cs-deep-20261019 capture',
                                    quote_note='two verbatim pieces of one JSON record, joined by " … "')))
    return out


_PROFILE_TEXT = {}


def profile_lead_quote(names, group):
    """A verbatim '<group> ... Leads ... <name>' window from the person's CSAIL profile page (Codex's capture)."""
    if not _PROFILE_TEXT:
        for r in json.load(open(CODEX / 'rosters' / 'all-profiles-raw.json')):
            for src in r.get('sources') or []:
                if src.get('capturePath') and 'csail.mit.edu/person/' in (src.get('url') or ''):
                    _PROFILE_TEXT.setdefault(r['name'], []).append(src)
    for n in names:
        for src in _PROFILE_TEXT.get(n, []):
            try:
                t = cap_text(src['capturePath'])[1]
            except Exception:
                continue
            g = html.unescape(group)
            for m in re.finditer(re.escape(g), t):
                w = t[m.start(): m.start() + 600]
                L = w.find('Leads')
                if L >= 0:
                    nm = next((x for x in names if x in w[L:L + 200]), None)
                    if nm:
                        e = w.find(nm, L) + len(nm)
                        return dict(url=src['url'], sha256=src.get('sha256'), quote=w[:e] if e < 400 else g + ' … ' + w[L:e])
    return None


def theses():
    items = json.load(open(STAGE / 'people' / 'mit_theses.json'))['theses']
    snap = CODEX / 'repository' / 'repository-items.json.gz'
    sha = hashlib.sha256(snap.read_bytes()).hexdigest()
    by = defaultdict(list)
    for t in items:
        for a in t['advisers']:
            by[flip(a)].append(dict(url=t['source']['url'], sha256=sha, quote=f"dc.contributor.advisor: {a} | dc.title: {t['title']}"[:300], observed=str(t['year']),
                                    via='Codex DSpace@MIT metadata snapshot (repository-items.json.gz)'))
    return by


LEAD = re.compile(r'\b(?:co-?lead(?:er)?s?|leads?|leader|director|head|principal investigator|PI)\b', re.I)


def dossier_lead_quotes():
    """[(url, quote, sha256, file)] from Codex's MIT lab dossiers (../mit-*-2026101*, ../mit-*-2026102*): quoted page
    text that names a leadership role; a quote is cut before any e-mail address."""
    import glob, os
    out = []
    for f in sorted(glob.glob(str(SW / 'mit-*-2026101*' / '*.json')) + glob.glob(str(SW / 'mit-*-2026102*' / '*.json'))):
        if os.path.getsize(f) > 30_000_000:
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        stack = [d]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                q = x.get('quote') or x.get('excerpt')
                if isinstance(q, str) and x.get('url') and LEAD.search(q):
                    q = re.split(r'\s(?:E-?mail:?|\S+@\S+)', q)[0].strip()
                    out.append((x['url'], q[:300], x.get('sha256'), f))
                stack.extend(x.values())
            elif isinstance(x, list):
                stack.extend(x)
    return list({(u, q): (u, q, s, f) for u, q, s, f in out}.values())


RANK = [('emeritus', r'emerit'), ('teaching', r'lecturer|instructor|of the practice|teaching'), ('adjunct_visiting', r'adjunct|visiting|affiliate'),
        ('research_scientist_pi', r'research scientist|research engineer|scientist|researcher'),
        ('ladder_faculty', r'\bprofessor\b|\bdirector\b')]


def rank_of(titles):
    for t in titles:  # most recent first
        for r, pat in RANK:
            if re.search(pat, t or '', re.I):
                return r
    return 'unknown'


def main():
    obs = listings() + codex_2026()
    gs = groups()
    adv = theses()
    C = json.loads(gzip.open(SITE / 'collection-mit.json.gz').read())
    st = json.load(open(STAGE / 'people' / 'structure.json'))
    audit = json.loads(gzip.open(SITE / 'mit-lab-audit.json.gz').read())
    lead_quotes = dossier_lead_quotes()
    # people: one entry per name, joined by full-name match
    people = []
    def find(name):
        for p in people:
            if any(same_full(name, n) or (len(toks(name)) == 1 and name == n) for n in [p['name']] + p['aliases']):
                return p
        return None
    single = {p['name'] for p in st['people'] if len(toks(p['name'])) == 1}
    for kind, year, name, title, extra, src in sorted(obs, key=lambda o: -o[1]):
        if not name or (len(toks(name)) < 2 and name not in single):
            continue
        p = find(name)
        if p is None:
            p = dict(name=name, aliases=[], obs=[]); people.append(p)
        elif name != p['name'] and name not in p['aliases']:
            p['aliases'].append(name)
        for a in extra.get('aliases') or []:
            if a not in p['aliases'] and a != p['name']:
                p['aliases'].append(a)
        p['obs'].append(dict(kind=kind, year=year, title=title, extra=extra, source=src))
    # merge entries that are one person by explicit evidence: a shared profile URL, or one structure person's own name list
    def profiles(p):
        return {re.sub(r'^https?://(www\.)?', '', x['extra'].get('profile') or '').rstrip('/') for x in p['obs'] if x['extra'].get('profile')} - {''}
    struct_names = [set(sp_['names']) | {sp_['name']} for sp_ in st['people'] if 'faculty' in sp_['roles']]
    merged = True
    while merged:
        merged = False
        for i in range(len(people)):
            for j in range(i + 1, len(people)):
                a_, b_ = people[i], people[j]
                na, nb = {a_['name']} | set(a_['aliases']), {b_['name']} | set(b_['aliases'])
                why = 'shared profile URL' if profiles(a_) & profiles(b_) else 'one structure person\'s name list' if any(na & ns and nb & ns for ns in struct_names) else None
                if why:
                    a_['aliases'] = sorted((set(a_['aliases']) | nb) - {a_['name']}); a_['obs'] += b_['obs']; a_.setdefault('merge_basis', []).append(dict(merged=b_['name'], basis=why))
                    people.pop(j); merged = True; break
            if merged:
                break
    # scope
    def cs_tagged(o):
        if o['kind'] == 'eecs_faculty_advisors':
            return 'CSAIL' in o['extra']['areas'] or any(a.startswith('II-') for a in o['extra']['areas'])
        if o['kind'] in ('eecs_role_faculty', 'eecs_directory_2026'):
            tags = set(re.findall(r'\bCS\b|AI\+D|\bEE\b', ' '.join(o['extra'].get('areas') or []) + ' ' + (o['title'] or '')))
            return 'CS' in tags or ('AI+D' in tags and 'EE' not in tags)
        return False
    leads = defaultdict(list)
    for g in gs:
        for n in g['leads']:
            leads[n].append(g)
    out = []
    coll_people = C['people']
    units = [u for u in C['units'] if u['kind'] == 'research_group']
    advising_units = defaultdict(list)
    for u in C['units']:
        if u['kind'] == 'adviser_group_listing':
            advising_units[flip(u['name'].split(' — ')[0])].append(u['id'])
    sp = {p['name']: p for p in st['people'] if 'faculty' in p['roles']}
    cu = {u['id']: u for u in C['units']}
    own_audit_units = [u for u in audit['units'] if len(u.get('leaders') or []) <= 2 and cu.get(u.get('mapUnit'), {}).get('kind', 'research_group') == 'research_group'
                       and not re.search(r'center|centre|institute|initiative|quest|laboratory\)|lincoln|sloan', u['name'], re.I)]
    for p in people:
        o = p['obs']
        csail_pi = [x for x in o if x['kind'] == 'csail_pi' or (x['kind'] == 'csail_directory_2026' and x['extra']['directory_role'] == 'Core/Dual')]
        csail_emeritus = [x for x in o if x['kind'] == 'csail_directory_2026' and x['extra']['directory_role'] == 'Emeritus']
        eecs_cs = [x for x in o if cs_tagged(x)]
        eecs_any = [x for x in o if x['kind'] in ('eecs_faculty_advisors', 'eecs_role_faculty', 'eecs_directory_2026')]
        my_groups = [g for n, gl in leads.items() if any(same_full(n, m) for m in [p['name']] + p['aliases']) for g in gl]
        researcher_lead = [x for x in o if x['kind'] == 'csail_directory_2026' and x['extra']['directory_role'] == 'Researchers'] and my_groups
        group_lead = [g for g in my_groups if g['kind'] == 'research_group']
        audit_lead = [u for u in own_audit_units if any(same_full(l, m) for l in u.get('leaders') or [] for m in [p['name']] + p['aliases'])]
        ee_lead = bool(eecs_any and not eecs_cs and (my_groups or csail_pi))
        if not (eecs_cs or csail_pi or csail_emeritus or researcher_lead or ee_lead or audit_lead or group_lead):
            continue
        titles = [x['title'] for x in sorted(o, key=lambda x: (-x['year'], x['kind'] != 'eecs_role_faculty'))]
        rank = rank_of(titles)
        if any(x['kind'] == 'csail_directory_2026' and x['extra']['directory_role'] == 'Emeritus' for x in o):
            rank = 'emeritus'
        if rank == 'research_scientist_pi' and not (csail_pi or my_groups or audit_lead):
            rank = 'unknown'
        own = [g for g in my_groups if g['kind'] == 'research_group']
        umb = [g for g in my_groups if g['kind'] == 'umbrella']
        theses_adv = next((v for k, v in adv.items() if any(same_full(k, m) for m in [p['name']] + p['aliases'])), [])
        if own:
            basis = dict(kind='named_group', url=own[0]['source']['url'], quote=own[0]['source']['quote'], sha256=own[0]['source']['sha256'], group=own[0]['name'])
            if not basis['quote']:
                pq = profile_lead_quote([p['name']] + p['aliases'], own[0]['name'])
                if pq:
                    basis.update(pq, via='the person\'s CSAIL profile page (Codex capture): the group card names its leads')
        elif audit_lead:
            u0 = audit_lead[0]; cu0 = cu.get(u0.get('mapUnit')) or {}; s0 = (cu0.get('sources') or [{}])[0]
            lq = next(((u_, q_, h_, f_) for u_, q_, h_, f_ in lead_quotes if any(m in q_ for m in [p['name']] + p['aliases'])
                       and re.search(r'(?:' + '|'.join(re.escape(m) for m in [p['name']] + p['aliases']) + r')[^.]{0,40}' + LEAD.pattern, q_, re.I)), None)
            if not lq:  # the person's CSAIL profile card for the unit ('<group> ... Leads ... <name>')
                pq = profile_lead_quote([p['name']] + p['aliases'], u0['name'])
                lq = (pq['url'], pq['quote'], pq['sha256'], 'CSAIL profile page (Codex capture)') if pq else None
            basis = dict(kind='named_group', group=u0['name'], url=lq[0] if lq else s0.get('url'), quote=lq[1] if lq else None, sha256=lq[2] if lq else s0.get('sha256'),
                         via="Codex's MIT lab audit (atlas/data/mit-lab-audit.json.gz) lists them as the unit's leader" + (f"; quote from {lq[3] if not str(lq[3]).startswith('/') else 'Codex dossier ' + Path(lq[3]).parent.name}" if lq else ''),
                         note=None if lq else 'leader as listed by the reviewed audit; no verbatim leadership quote in our captures')
            if not basis['quote'] and csail_pi:  # the person's own CSAIL principal-investigator listing stands as the verbatim PI evidence
                x = next((y for y in csail_pi if y['source'].get('quote')), csail_pi[0])
                basis.update(url=x['source']['url'], quote=x['source']['quote'], sha256=x['source'].get('sha256'),
                             note="group leadership from Codex's reviewed audit; the quote is the person's CSAIL principal-investigator listing")
        elif csail_pi:
            x = next((y for y in csail_pi if y['source'].get('quote')), csail_pi[0])
            basis = dict(kind='own_group', url=x['source']['url'], quote=x['source']['quote'], sha256=x['source'].get('sha256'), note='CSAIL lists this person as a principal investigator')
        elif theses_adv and rank in ('ladder_faculty', 'emeritus', 'research_scientist_pi'):
            basis = dict(kind='advises_phd', url=theses_adv[0]['url'], quote=theses_adv[0]['quote'], theses=len(theses_adv))
        else:
            basis = dict(kind='none')
        is_pi = basis['kind'] != 'none' and (rank not in ('teaching', 'adjunct_visiting') or bool(own))
        cid = [c['id'] for c in coll_people if any(same_full(c['name'], m) for m in [p['name']] + p['aliases'])]
        if len(cid) > 1:  # several collection records carry the name: the one with this person's profile URL
            prof_set = profiles(p)
            by_prof = [c['id'] for c in coll_people if c['id'] in cid and re.sub(r'^https?://(www\.)?', '', c.get('profileUrl') or '').rstrip('/') in prof_set]
            cid = by_prof if len(by_prof) == 1 else cid
        lab_units = [u['id'] for u in units if len(u.get('leaders') or []) <= 2 and any(same_full(l, m) for l in u['leaders'] for m in [p['name']] + p['aliases'])]
        stp = next((v for k, v in sp.items() if any(same_full(k, m) or k == m for m in [p['name']] + p['aliases'])), None)
        prof = next((x['extra'].get('profile') for x in o if x['extra'].get('profile')), None)
        out.append(dict(
            name=p['name'], aliases=p['aliases'], collection_person_id=cid[0] if len(cid) == 1 else None, collection_person_candidates=cid if len(cid) > 1 else [],
            structure_name=stp['name'] if stp else None, profile_url=prof, dblp=(stp or {}).get('dblp') or [],
            rank=rank, title_as_listed=titles[0] if titles else None,
            departments=sorted({'EECS' for x in eecs_any} | {'CSAIL' for x in o if x['kind'].startswith('csail')}),
            flags=[f for f, c in (('ee_faculty_leading_csail_group', ee_lead), ('research_staff_pi', rank == 'research_scientist_pi'),
                                   ('cs_tagged_eecs_faculty', bool(eecs_cs)), ('csail_pi_listing', bool(csail_pi))) if c],
            years_listed=sorted({x['year'] for x in o}),
            sources=[dict(kind=x['kind'], **x['source']) for x in sorted(o, key=lambda x: x['year'])],
            is_pi=is_pi, pi_basis=basis,
            lab_units=lab_units or ([dict(proposed=True, name=f"{p['name']} group", url=prof, evidence=basis)] if is_pi else []),
            umbrella_leads=[g['name'] for g in umb], adviser_listing_units=next((v for k, v in advising_units.items() if any(same_full(k, m) for m in [p['name']] + p['aliases'])), []),
            phd_theses_advised_2016_2026=len(theses_adv),
            notes=[f"merged {m['merged']} ({m['basis']})" for m in p.get('merge_basis', [])]))
    # report
    struct_fac = set(sp)
    in_census = {e['structure_name'] for e in out if e['structure_name']}
    lacking = [e['name'] for e in out if not e['structure_name']]
    unconfirmed = sorted(struct_fac - in_census)
    cu = {u['id']: u for u in C['units']}
    own_audit = [u for u in audit['units'] if len(u.get('leaders') or []) <= 2 and cu.get(u.get('mapUnit'), {}).get('kind', 'research_group') == 'research_group'
                 and not re.search(r'center|centre|institute|initiative|quest|laboratory\)|lincoln|sloan', u['name'], re.I)]
    audit_leaders = {l for u in own_audit for l in u.get('leaders') or []}
    all_audit_leaders = {l for u in audit['units'] for l in u.get('leaders') or []}
    audit_not_in = sorted(l for l in audit_leaders if not any(same_full(l, m) for e in out for m in [e['name']] + e['aliases']))
    pis_without_audit = sorted(e['name'] for e in out if e['is_pi'] and not any(same_full(e['name'], l) for l in audit_leaders))
    HERE.mkdir(exist_ok=True)
    (HERE / 'mit-faculty.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    rc = Counter(e['rank'] for e in out); pc = Counter(e['pi_basis']['kind'] for e in out if e['is_pi'])
    md = ['# MIT CS faculty census and PIs (2016-2026)', '', 'Built by `census/build_mit_census.py` from existing captures (see its docstring); every source carries URL, sha256 and a verbatim quote.', '',
          '## Counts', '', f'- People in scope: {len(out)}', f'- By rank: {dict(rc)}', f'- PIs: {sum(e["is_pi"] for e in out)} ({dict(pc)})',
          f'- With a unique collection person id: {sum(1 for e in out if e["collection_person_id"])}; ambiguous: {sum(1 for e in out if e["collection_person_candidates"])}',
          f'- Lead an existing collection research-group unit: {sum(1 for e in out if any(isinstance(u, str) for u in e["lab_units"]))}; units to create ("<Name> group"): {sum(1 for e in out if any(isinstance(u, dict) for u in e["lab_units"]))}',
          f'- EE faculty leading CSAIL groups (flagged): {sum(1 for e in out if "ee_faculty_leading_csail_group" in e["flags"])}; research-staff PIs: {sum(1 for e in out if "research_staff_pi" in e["flags"])}', '',
          '## Structure vs listings', '', f'- Structure faculty ({len(struct_fac)}) that no census listing confirms ({len(unconfirmed)}): ' + ', '.join(unconfirmed[:60]),
          f'- Census people the structure lacks ({len(lacking)}), by rank: {dict(Counter(e["rank"] for e in out if not e["structure_name"]))}: ' + ', '.join(sorted(lacking)[:80]),
          '  (the structure kept professors only: lecturers, research scientists leading groups and EE faculty listed as CSAIL PIs enter here)', '',
          '## Evidence gaps', '', f'- PIs whose named-group basis has no verbatim leadership quote in our captures: ' + ', '.join(sorted(e['name'] for e in out if e['pi_basis'].get('note', '') and 'no verbatim leadership quote' in (e['pi_basis'].get('note') or '') or "Codex's reviewed audit; the quote is" in (e['pi_basis'].get('note') or ''))),
          f'- Rank unknown: ' + ', '.join(f"{e['name']} ({e['title_as_listed']})" for e in out if e['rank'] == 'unknown'),
          f'- Collection person id ambiguous (several collection records, none with the profile URL): {sum(1 for e in out if e["collection_person_candidates"])}; no collection record: {sum(1 for e in out if not e["collection_person_id"] and not e["collection_person_candidates"])}', '',
          "## Codex's 101-unit lab audit", '', f"- Audit units that are someone's own lab (at most two leaders; centers, institutes, Lincoln Laboratory and Sloan groups excluded): {len(own_audit)} of {len(audit['units'])}",
          f"- Their leaders not in this census ({len(audit_not_in)}): " + ', '.join(audit_not_in[:60]),
          f"- Leaders of the other audit units (centers such as CCSE and CBMM, Lincoln Laboratory staff groups, Sloan, IDSS) are outside this census's scope: {len(all_audit_leaders - audit_leaders)} names",
          f'- Census PIs who lead no audited unit ({len(pis_without_audit)}): ' + ', '.join(pis_without_audit[:80]), '',
          "Codex's audit (atlas/data/mit-lab-audit.json.gz, credited) covers CSAIL research groups and communities; the census adds every CS faculty member and CSAIL PI, and proposes a \"<Name> group\" unit for PIs without one."]
    (HERE / 'mit-report.md').write_text('\n'.join(md) + '\n')
    print(json.dumps(dict(people=len(out), ranks=dict(rc), pis=sum(e['is_pi'] for e in out), pi_basis=dict(pc), structure_unconfirmed=len(unconfirmed),
                          structure_lacks=len(lacking), audit_leaders_missing=len(audit_not_in))))


if __name__ == '__main__':
    main()
