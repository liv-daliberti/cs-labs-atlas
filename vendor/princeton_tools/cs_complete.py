# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools/cs_complete.py (sha256 0ac2b589f6932549bd32a6ea5cf169bbcc334cbf072b59d745452dcdb031dcdd); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Princeton Computer Science 2016–2026: every faculty identity, PhD student identity and paper.

Steps:
  advisees   CS faculty (cs-roster/faculty_roster.json) joined to their PhD advisees from the
             DataSpace doctoral dissertations (2016–2026; advisor matched by family + first given
             name, conflicting middle initials refused).
  anchor     advisee co-authorship anchor, labelled `official_advisee_coauthorship_anchor`: within
             Princeton's 2016–2026 OpenAlex works, an author ID carrying the faculty member's full
             name that co-authors with >=2 distinct official advisees on >=4 works, with no other
             full-name ID reaching half of either count. Each advisee's own author ID is the unique
             full-name ID on those shared works (`advisor_coauthorship_student_identity`).
             Faculty already verified by an earlier route keep that route.
  corpus     the CS research corpus (see corpus.__doc__).
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, re, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

STAGE = P.SWEEPS / 'claude-princeton-20261015'  # vendored: the data root (was Path(__file__).resolve().parents[1])
OUT = STAGE / 'cs-complete'
sys.path.insert(0, str(Path(__file__).resolve().parent))


def norm(text):
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def toks(name):
    t = norm(name).split()
    full = [x for x in t if len(x) > 1]
    return full if len(full) >= 2 else t


def advisor_key(name):
    if ',' not in name:
        return None, ''
    fam, giv = name.split(',', 1)
    f, g = norm(fam).split(), norm(giv).split()
    return ((f[-1], g[0]) if f and g else None), ''.join(x[0] for x in g[1:])


def person_key(name):
    t = norm(name).split()
    return ((t[-1], t[0]) if len(t) >= 2 else None), ''.join(x[0] for x in t[1:-1])


def student_name(dataspace_name):
    """'Family, Given Middle' -> 'Given Middle Family'."""
    if ',' not in dataspace_name:
        return dataspace_name
    fam, giv = dataspace_name.split(',', 1)
    return (giv.strip() + ' ' + fam.strip()).strip()


NICK = {'ben': 'benjamin', 'tom': 'thomas', 'mike': 'michael', 'dave': 'david', 'andy': 'andrew', 'rob': 'robert',
        'bob': 'robert', 'jen': 'jennifer', 'ed': 'edward', 'matt': 'matthew', 'chris': 'christopher', 'sam': 'samuel',
        'nick': 'nicholas', 'dan': 'daniel', 'joe': 'joseph', 'jim': 'james', 'bill': 'william', 'will': 'william',
        'alex': 'alexander', 'steve': 'steven', 'kate': 'katherine', 'liz': 'elizabeth', 'tony': 'anthony'}


def given_equal(a, b):
    """Same first given name, or a common nickname pair (used only with an exact, unique family name)."""
    return a == b or NICK.get(a) == b or NICK.get(b) == a


def advisees():
    OUT.mkdir(exist_ok=True)
    roster = json.loads((STAGE / 'cs-roster/faculty_roster.json').read_text())
    by_family = defaultdict(list)
    for f in roster:
        k, mid = person_key(f['name'])
        if k:
            by_family[k[0]].append(dict(f, middle=mid, given=k[1]))
    diss = json.loads((STAGE / 'dataspace/advising.json').read_text())
    out = defaultdict(list)
    held = Counter()
    for d in diss:
        y = d['issued'][:4]
        if not (y.isdigit() and 2016 <= int(y) <= 2026):
            continue
        for a in d['advisors']:
            k, mid = advisor_key(a)
            people = [p for p in by_family.get(k[0], []) if given_equal(p['given'], k[1])] if k else []
            people = [p for p in people if not (mid and p['middle'] and mid[0] != p['middle'][0])]
            if len(people) != 1:
                held['advisor_not_unique_cs_faculty' if people else 'advisor_not_cs_faculty'] += 1; continue
            out[people[0]['profile_id']].append(dict(student=student_name(d['student']), dataspace_name=d['student'], year=int(y),
                                                     title=d['title'], departments=d['departments'], dissertation=d['uri'] or d['handle'],
                                                     advisor_as_listed=a))
    (OUT / 'advisees.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(cs_faculty=len(roster), faculty_with_advisees=len(out), advisee_edges=sum(len(v) for v in out.values()),
                          distinct_students=len({s['dissertation'] for v in out.values() for s in v}), held=dict(held))))


def load_index():
    return json.loads(gzip.decompress((STAGE / 'identity/works_index.json.gz').read_bytes()))


def anchor():
    roster = {f['profile_id']: f for f in json.loads((STAGE / 'cs-roster/faculty_roster.json').read_text())}
    adv = json.loads((OUT / 'advisees.json').read_text())
    works = load_index()['works']
    # name-token -> work ids, to avoid scanning every byline for every faculty member
    by_family = defaultdict(set)
    for wid, w in works.items():
        for aid, name, pos, insts in w['byline']:
            t = norm(name).split()
            if t:
                by_family[t[-1]].add(wid)
    faculty_ids, student_ids, gaps = [], [], []
    for pid, students in adv.items():
        f = roster[pid]
        ft = toks(f['name'])
        forms = [ft] + [toks(student_name(s['advisor_as_listed'])) for s in students]
        forms = [list(x) for x in {tuple(x) for x in forms if len(x) >= 2}]
        candidates = by_family.get(ft[-1], set())
        per_author = defaultdict(lambda: dict(works=set(), advisees=set()))
        shared = defaultdict(list)
        for wid in candidates:
            line = works[wid]['byline']
            fac = {aid for aid, name, _, _ in line if aid and any(all(t in norm(name).split() for t in form) for form in forms)}
            if not fac:
                continue
            for s in students:
                st = toks(s['student'])
                hits = [aid for aid, name, _, _ in line if aid and all(t in norm(name).split() for t in st)]
                if hits:
                    for a in fac:
                        per_author[a]['works'].add(wid); per_author[a]['advisees'].add(s['dissertation'])
                        shared[(a, s['dissertation'])].append((wid, hits))
        ranked = sorted(per_author.items(), key=lambda kv: (len(kv[1]['advisees']), len(kv[1]['works'])), reverse=True)
        if not ranked:
            gaps.append(dict(profile_id=pid, name=f['name'], advisees=len(students), reason='no co-authored Princeton work with an official advisee')); continue
        best, stats = ranked[0]
        na, nw = len(stats['advisees']), len(stats['works'])
        rival = any(len(s['advisees']) * 2 >= na or len(s['works']) * 2 >= nw for _, s in ranked[1:])
        if na < 2 or nw < 4 or rival:
            gaps.append(dict(profile_id=pid, name=f['name'], advisees=len(students), coauthored_advisees=na, works=nw,
                             reason='too weak' if not rival else 'competing full-name profile')); continue
        faculty_ids.append(dict(profile_id=pid, name=f['name'], author='https://openalex.org/' + best, method='official_advisee_coauthorship_anchor',
                                coauthored_advisees=na, shared_works=nw, units=f.get('units', [])))
        for s in students:
            pairs = shared.get((best, s['dissertation']), [])
            ids = Counter(a for _, hits in pairs for a in hits)
            if ids and len(ids) == 1:
                student_ids.append(dict(student=s['student'], dissertation=s['dissertation'], year=s['year'], advisor=f['name'],
                                        author='https://openalex.org/' + next(iter(ids)), shared_works=len(pairs),
                                        method='advisor_coauthorship_student_identity'))
    (OUT / 'faculty_identities.json').write_text(json.dumps(faculty_ids, indent=1, ensure_ascii=False))
    (OUT / 'student_identities.json').write_text(json.dumps(student_ids, indent=1, ensure_ascii=False))
    (OUT / 'anchor_gaps.json').write_text(json.dumps(gaps, indent=1, ensure_ascii=False))
    print(json.dumps(dict(faculty_verified=len(faculty_ids), students_identified=len(student_ids), gaps=len(gaps),
                          gap_reasons=dict(Counter(g['reason'] for g in gaps)))))




# ---------------------------------------------------------------- corpus
PRINCETON = 'https://openalex.org/I20089843'
TYPES = {'article', 'conference-paper', 'review', 'preprint', 'report', 'data-paper', 'software-paper', 'proceedings-article'}


def fetch_authors(authors):
    """2016–2026 works per author (cursor paging, API key); reuses cs-pi-works pages already fetched."""
    import hashlib, os, time, requests
    (OUT / 'raw').mkdir(parents=True, exist_ok=True)
    state_path = OUT / 'fetch_state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    prior = STAGE / 'cs-pi-works/fetch_state.json'
    if prior.exists():
        for aid, s in json.loads(prior.read_text()).items():
            if s.get('complete'):
                state.setdefault(aid, s)
    session = requests.Session(); session.headers['User-Agent'] = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
    for author in sorted(authors):
        aid = author.rsplit('/', 1)[-1]
        s = state.setdefault(aid, dict(cursor='*', pages=[], complete=False))
        while not s['complete']:
            params = {'filter': f'authorships.author.id:{aid},from_publication_date:2016-01-01,to_publication_date:2026-10-12',
                      'per_page': 200, 'cursor': s['cursor'], 'api_key': os.environ['OPENALEX_API_KEY']}
            for attempt in range(5):
                try:
                    r = session.get('https://api.openalex.org/works', params=params, timeout=120)
                    if r.status_code in (429, 500, 502, 503, 504):
                        time.sleep(2 ** attempt); continue
                    r.raise_for_status(); break
                except requests.RequestException:
                    time.sleep(5 * (attempt + 1))
            data = r.json()
            path = OUT / 'raw' / f'{aid}_{len(s["pages"]):03d}.json.gz'
            path.write_bytes(gzip.compress(r.content, 6))
            s['pages'].append(dict(path=str(path), sha256=hashlib.sha256(r.content).hexdigest(), records=len(data.get('results', []))))
            s['cursor'] = data.get('meta', {}).get('next_cursor')
            s['complete'] = not data.get('results') or not s['cursor']
            state_path.write_text(json.dumps(state))
            time.sleep(0.12)
    return state


def works_of(aid, state):
    import hashlib
    for p in state[aid]['pages']:
        raw = gzip.decompress(Path(p['path']).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == p['sha256']
        yield from json.loads(raw)['results']


def cs_people_names():
    """Every known Princeton CS student/member name -> roles (dissertations, lab members, theses, rosters)."""
    names = defaultdict(set)
    for pid, ss in json.loads((OUT / 'advisees.json').read_text()).items():
        for s in ss:
            names[' '.join(toks(s['student']))].add('phd_advisee')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cs_pi_works as C
    for lab, mem in C.members_by_lab().items():
        for key, m in mem.items():
            names[key].add('lab_member:' + (m.get('status') or ''))
    senior = STAGE / 'dataspace_senior_theses/advising.json'
    cols = json.loads((STAGE / 'dataspace_senior_theses/collections.json').read_text()) if (STAGE / 'dataspace_senior_theses/collections.json').exists() else {}
    if senior.exists():
        for d in json.loads(senior.read_text()):
            if 'Computer Science' in cols.get(d['collection_set'], '') and d['issued'][:4].isdigit() and int(d['issued'][:4]) >= 2016:
                names[' '.join(toks(student_name(d['student'])))].add('senior_thesis')
    rosters = STAGE / 'cs-people/rosters.json'
    if rosters.exists():
        for r in json.loads(rosters.read_text()):
            if r.get('roster') in ('grad_student', 'grad_alumni', 'researcher', 'postdoc'):
                names[' '.join(toks(r['name']))].add('roster:' + r['roster'])
    return {k: v for k, v in names.items() if len(k.split()) >= 2}


def corpus():
    faculty = json.loads((OUT / 'faculty_verified.json').read_text())
    fac_authors = {f['author'] for f in faculty}
    students = [s for s in json.loads((OUT / 'student_identities.json').read_text()) if s['author'] not in fac_authors]
    seen = {s['author'] for s in students}
    units_of = {p['person']: p['units'] for p in json.loads((OUT / 'people.json').read_text())}
    if (OUT / 'people_identities.json').exists():
        for s in json.loads((OUT / 'people_identities.json').read_text()):
            if s['author'] not in seen and s['author'] not in fac_authors:
                students.append(dict(s, units=units_of.get(s['person'], []))); seen.add(s['author'])
    state = fetch_authors(fac_authors | {s['author'] for s in students})
    people = cs_people_names()
    student_ids = {s['author']: s for s in students}
    fac_ids = {f['author']: f for f in faculty}
    items, counts = {}, Counter()
    def coauthor_people(w, skip):
        found = []
        for a in w.get('authorships') or []:
            au = a.get('author') or {}
            if au.get('id') == skip:
                continue
            nt = norm(au.get('display_name') or a.get('raw_author_name') or '').split()
            for key, roles in people.items():
                kk = key.split()
                if kk[0] in nt and kk[-1] in nt and all(t in nt for t in kk):
                    found.append(dict(name=au.get('display_name'), author=au.get('id'), roles=sorted(roles),
                                      princeton=any(i.get('id') == PRINCETON for i in a.get('institutions') or [])))
                    break
        return found
    def record(w, basis, faculty_names=(), student_names=(), units=()):
        it = items.setdefault(w['id'], dict(work=w['id'], doi=(w.get('doi') or '').replace('https://doi.org/', '').lower(),
                                           title=w.get('display_name') or '', year=w.get('publication_year'), type=w.get('type'),
                                           bases=set(), faculty=set(), students=set(), units=set()))
        it['bases'].add(basis); it['faculty'] |= set(faculty_names); it['students'] |= set(student_names); it['units'] |= set(units)
    for f in faculty:
        aid = f['author'].rsplit('/', 1)[-1]
        for w in works_of(aid, state):
            if w.get('type') not in TYPES or w.get('is_retracted') or w.get('is_paratext'):
                continue
            mine = [a for a in w.get('authorships') or [] if (a.get('author') or {}).get('id') == f['author']]
            if len(mine) != 1:
                continue
            insts = {i.get('id') for i in mine[0].get('institutions') or []}
            co = coauthor_people(w, f['author'])
            if PRINCETON in insts:
                basis = 'faculty_princeton_authorship'
            elif co and (not insts or any(c['princeton'] for c in co)):
                basis = 'faculty_with_cs_student_coauthor_affiliation_gap'
            else:
                counts['faculty_work_excluded'] += 1; continue
            counts[basis] += 1
            record(w, basis, [f['name']], [c['name'] for c in co], f.get('units', []))
    for s in students:
        aid = s['author'].rsplit('/', 1)[-1]
        if aid not in state:
            continue
        advisor = next((f for f in faculty if f['name'] == s.get('advisor')), None)
        person_units = s.get('units') or (advisor.get('units', []) if advisor else [])
        for w in works_of(aid, state):
            if w.get('type') not in TYPES or w.get('is_retracted') or w.get('is_paratext'):
                continue
            mine = [a for a in w.get('authorships') or [] if (a.get('author') or {}).get('id') == s['author']]
            if len(mine) != 1 or not any(i.get('id') == PRINCETON for i in mine[0].get('institutions') or []):
                counts['student_work_excluded'] += 1; continue
            counts['student_princeton_authorship'] += 1
            record(w, 'cs_student_or_member_princeton_authorship', [], [s['student']], person_units)
    rows = []
    for it in items.values():
        rows.append({**it, 'bases': sorted(it['bases']), 'faculty': sorted(it['faculty']), 'students': sorted(it['students']), 'units': sorted(it['units'])})
    (OUT / 'corpus_openalex.json').write_text(json.dumps(rows, ensure_ascii=False))
    print(json.dumps(dict(counts=dict(counts), works=len(rows), with_students=sum(1 for r in rows if r['students']),
                          with_units=sum(1 for r in rows if r['units']), by_year=sorted(Counter(r['year'] for r in rows).items()),
                          known_cs_people_names=len(people))))




# ---------------------------------------------------------------- co-authorship identity extensions
def _index_by_family():
    works = load_index()['works']
    by_family = defaultdict(set)
    for wid, w in works.items():
        for aid, name, pos, insts in w['byline']:
            t = norm(name).split()
            if t:
                by_family[t[-1]].add(wid)
    return works, by_family


def anchor_members():
    """Unverified CS faculty: full-name author ID co-authoring >=4 Princeton works with >=2 distinct people
    from that faculty member's own lab people pages or the department student/postdoc rosters, with no
    rival full-name ID reaching half of either count (`official_lab_member_coauthorship_anchor`)."""
    import cs_pi_works as C
    roster = json.loads((STAGE / 'cs-roster/faculty_roster.json').read_text())
    verified = {f['profile_id'] for f in json.loads((OUT / 'faculty_verified.json').read_text())}
    members = C.members_by_lab()
    people = json.loads((OUT / 'people.json').read_text())
    rostered = [p['person'].split() for p in people if any(r.startswith('department_roster') for r in p['roles'])]
    works, by_family = _index_by_family()
    found, gaps = [], []
    for f in roster:
        if f['profile_id'] in verified or 'ecturer' in f['position']:
            continue
        own = [k.split() for u in f.get('units', []) for k in members.get(u, {})]
        circle = [x for x in own + rostered if len(x) >= 2]
        if not circle:
            continue
        ft = toks(f['name'])
        stats = defaultdict(lambda: dict(works=set(), people=set()))
        for wid in by_family.get(ft[-1], ()):
            line = works[wid]['byline']
            fac = {aid for aid, name, _, _ in line if aid and all(t in norm(name).split() for t in ft)}
            if not fac:
                continue
            names = [norm(name).split() for aid, name, _, _ in line if aid not in fac]
            hit = {' '.join(c) for c in circle if any(all(t in n for t in c) for n in names)}
            for a in fac:
                if hit:
                    stats[a]['works'].add(wid); stats[a]['people'] |= hit
        ranked = sorted(stats.items(), key=lambda kv: (len(kv[1]['people']), len(kv[1]['works'])), reverse=True)
        if not ranked:
            gaps.append(dict(name=f['name'], reason='no co-authored Princeton work with own lab members or rostered students')); continue
        best, s = ranked[0]
        np_, nw = len(s['people']), len(s['works'])
        rival = any(len(x['people']) * 2 >= np_ or len(x['works']) * 2 >= nw for _, x in ranked[1:])
        if np_ < 2 or nw < 4 or rival:
            gaps.append(dict(name=f['name'], people=np_, works=nw, reason='competing profile' if rival else 'too weak')); continue
        found.append(dict(profile_id=f['profile_id'], name=f['name'], position=f['position'], units=f.get('units', []),
                          author='https://openalex.org/' + best, methods=['official_lab_member_coauthorship_anchor'],
                          coauthored_people=np_, shared_works=nw))
    allv = json.loads((OUT / 'faculty_verified.json').read_text()) + found
    (OUT / 'faculty_verified.json').write_text(json.dumps(allv, indent=1, ensure_ascii=False))
    (OUT / 'member_anchor_gaps.json').write_text(json.dumps(gaps, indent=1, ensure_ascii=False))
    print(json.dumps(dict(newly_verified=[(x['name'], x['coauthored_people'], x['shared_works']) for x in found],
                          total_verified=len(allv), gaps=len(gaps))))


def identify_people():
    """Known CS people (theses, lab pages, rosters): the full-name author ID on Princeton works co-authored
    with a verified CS faculty member, when unique across those works (`cs_faculty_coauthorship_identity`)."""
    faculty = {f['author'].rsplit('/', 1)[-1] for f in json.loads((OUT / 'faculty_verified.json').read_text())}
    works, by_family = _index_by_family()
    with_faculty = {wid for wid, w in works.items() if any(aid in faculty for aid, *_ in w['byline'])}
    people = json.loads((OUT / 'people.json').read_text())
    prior = {s['student'] for s in json.loads((OUT / 'student_identities.json').read_text())}
    out, counts = [], Counter()
    for p in people:
        t = p['person'].split()
        if len(t) < 2:
            continue
        ids = Counter()
        for wid in by_family.get(t[-1], set()) & with_faculty:
            for aid, name, _, _ in works[wid]['byline']:
                if aid and aid not in faculty and all(x in norm(name).split() for x in t):
                    ids[aid] += 1
        if not ids:
            counts['no_coauthorship_with_verified_faculty'] += 1; continue
        if len(ids) > 1 and sorted(ids.values())[-2] * 2 >= max(ids.values()):
            counts['ambiguous_profiles'] += 1; continue
        aid, n = ids.most_common(1)[0]
        counts['identified'] += 1
        out.append(dict(student=p['names'][0], person=p['person'], roles=p['roles'], author='https://openalex.org/' + aid,
                        shared_works_with_cs_faculty=n, advisor='', method='cs_faculty_coauthorship_identity'))
    (OUT / 'people_identities.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(counts=dict(counts), identified=len(out))))




# ---------------------------------------------------------------- package for the full-text catalog
FULLTEXT = P.STORES / 'princeton'
PACKAGE = FULLTEXT / 'discovery/claude-cs-complete-20261016'


def unit_resolver():
    import hashlib, re
    names = {}
    for f in (STAGE / 'cs-roster/final_units.json', STAGE / 'computer-science/claude/final_units.json'):
        if f.exists():
            for u in json.loads(f.read_text()):
                if not u.get('existing_id'):
                    names[norm(u['name'])] = 'new:' + (u.get('url') or u['name'])
    def site_id(key):
        return key if not key.startswith('new:') else 'lab_claude_csroster_' + hashlib.sha256(key[4:].encode()).hexdigest()[:16]
    def resolve(value):
        m = re.search(r'(lab_[A-Za-z0-9_]+)', value)
        if m:
            return [m.group(1)]
        if value.startswith('new:'):
            return [site_id(value)]
        text = re.sub(r'^(NEW|STAGED)\s*:\s*', '', value, flags=re.I)
        return [site_id(names[norm(part)]) for part in text.split(';') if norm(part) in names]
    return resolve


def package():
    import hashlib, re, sqlite3
    resolve = unit_resolver()
    rows = json.loads((OUT / 'corpus_openalex.json').read_text())
    faculty = json.loads((OUT / 'faculty_verified.json').read_text())
    fac_units = {f['name']: {u for v in f.get('units', []) for u in resolve(v)} for f in faculty}
    state = json.loads((OUT / 'fetch_state.json').read_text())
    full = {}
    for aid, s in state.items():
        for p in s['pages']:
            for w in json.loads(gzip.decompress(Path(p['path']).read_bytes()))['results']:
                full.setdefault(w['id'], (w, p['path']))
    db = sqlite3.connect(f'file:{FULLTEXT}/catalog.sqlite?mode=ro', uri=True, timeout=120)
    by_oa, by_doi = {}, {}
    for wid, doi, oa, graph in db.execute('SELECT id,doi,json_extract(oa_json,"$.id"),json_extract(graph_json,"$.openalex") FROM works'):
        for x in (oa, graph):
            if x: by_oa[x] = wid
        if doi: by_doi[doi.lower()] = wid
    (PACKAGE / 'evidence').mkdir(parents=True, exist_ok=True)
    def evidence(record):
        blob = json.dumps(record, sort_keys=True, ensure_ascii=False)
        path = PACKAGE / 'evidence' / (hashlib.sha256(blob.encode()).hexdigest() + '.json')
        path.write_text(blob)
        return str(path)
    assoc, new_works, cands, seen = [], [], [], set()
    for r in rows:
        w, page = full.get(r['work'], (None, None))
        if w is None:
            continue
        wid = by_oa.get(r['work']) or (by_doi.get(r['doi']) if r['doi'] else None)
        if wid is None:
            wid = 'paper_oa_' + r['work'].rsplit('/', 1)[-1]
            if wid not in seen:
                seen.add(wid)
                node = {'id': wid, 'type': 'paper', 'name': r['title'], 'year': r['year'], 'date': w.get('publication_date'), 'doi': r['doi'],
                        'openalex': r['work'], 'workType': r['type'], 'url': w.get('doi') or r['work'], 'sourceUrls': [r['work']],
                        'status': 'princeton_cs_verified_people_work'}
                new_works.append(dict(id=wid, node=node, metadata=w, source=page, rule='Princeton CS: verified faculty or identified CS student/member on the byline; ' + ', '.join(r['bases'])))
                for loc in w.get('locations') or []:
                    if not loc.get('is_oa'):
                        continue
                    url = loc.get('pdf_url'); landing = loc.get('landing_page_url') or ''
                    if not url and 'arxiv.org' in landing:
                        url = landing
                    if url and url.startswith('http'):
                        cands.append(dict(work_id=wid, url=url, landing_url=landing, license=loc.get('license'), version=loc.get('version'), metadata_source=page))
        units = set()
        for v in r['units']:
            units |= set(resolve(v))
        for lab in sorted(units):
            fac_here = [f for f in r['faculty'] if lab in fac_units.get(f, set())]
            kind = 'pi' if fac_here else 'member'
            person = fac_here[0] if fac_here else (r['students'][0] if r['students'] else '')
            ev = evidence(dict(lab_id=lab, work_id=wid, openalex_work=r['work'], kind=kind, person=person, bases=r['bases'],
                               faculty=r['faculty'], students_or_members=r['students'], title=r['title'], year=r['year']))
            assoc.append(dict(work_id=wid, lab_id=lab, kind=kind, person=person, source_url=r['work'], evidence_path=ev,
                              match='princeton_cs_' + ('verified_faculty' if kind == 'pi' else 'identified_student_or_member') + '_authorship'))
    registry = []
    resolve_names = {}
    for f in (STAGE / 'cs-roster/final_units.json', STAGE / 'computer-science/claude/final_units.json'):
        if f.exists():
            for u in json.loads(f.read_text()):
                if not u.get('existing_id'):
                    for sid in resolve('new:' + (u.get('url') or u['name'])):
                        resolve_names[sid] = u
    for sid, u in resolve_names.items():
        if any(a['lab_id'] == sid for a in assoc):
            registry.append(dict(id=sid, name=u['name'], departments=['Computer Science'], url=u.get('url', ''), source=u.get('url', ''),
                                 leaders=[x['name'] for x in u.get('leaders', [])], unitType=u.get('unit_type', 'research_group')))
    def write(name, items):
        (PACKAGE / name).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in items))
    write('associations.jsonl', assoc); write('new-works.jsonl', new_works); write('new-work-candidates.jsonl', cands)
    (PACKAGE / 'labs.json').write_text(json.dumps(registry, indent=1, ensure_ascii=False))
    (PACKAGE / 'work-ids.txt').write_text('\n'.join(sorted({a['work_id'] for a in assoc})) + '\n')
    summary = dict(associations=len(assoc), works=len({a['work_id'] for a in assoc}), new_works=len(new_works), candidates=len(cands),
                   labs=len({a['lab_id'] for a in assoc}), provisional_units=len(registry), by_kind=dict(Counter(a['kind'] for a in assoc)))
    (PACKAGE / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary))


def import_catalog():
    import sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parent))
    import cs_pi_works as C
    C.PACKAGE = PACKAGE
    C.import_catalog()


if __name__ == '__main__':
    {'advisees': advisees, 'anchor': anchor, 'corpus': corpus, 'anchor-members': anchor_members,
     'identify-people': identify_people, 'package': package, 'import': import_catalog}[sys.argv[1]]()
