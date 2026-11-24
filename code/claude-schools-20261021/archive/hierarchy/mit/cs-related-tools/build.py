"""Build the MIT CS-related scope outputs (owner decision 2026-10-22) from the reviewed decisions (decisions.py) and the
offline evidence gathered by the other tools in this directory:
  work/listing-matches.json  scan_listings.py   candidates x department faculty listings (Course Catalog, EECS lists)
  work/thesis-match.json     thesis_match.py    candidates x DSpace@MIT thesis records (dc.contributor.advisor)
  work/affiliations.json     affiliations.py    candidates' raw affiliation strings and ORCID in the MIT OpenAlex sweep
Every cited page is (copied into) hierarchy/mit/cs-related-captures.sqlite; every quote is checked to be an exact
substring of that capture's stored text and every sha256 to be the stored capture's.

Writes (only with --write; otherwise a dry run that prints the counts and problems):
  census/mit-additions.json                  accepted people appended (added = cs_related_scope_20261022; earlier rows of
                                             this scope are replaced, other rows kept)
  hierarchy/census-overrides.json -> mit     a reviewed appointment period for every accepted person (re-read right before
                                             writing; only this review's names under 'mit' are touched)
  hierarchy/mit/cs-related-home-departments.json
  hierarchy/mit/cs-related-review.json
usage: build.py [--write]
"""
import json, re, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import mpcap  # noqa: E402
from decisions import FACULTY, NOT_FACULTY_LISTED, UNLISTED, REASON, NOTES  # noqa: E402
from scan_listings_lib import natural  # noqa: E402

H = Path(mpcap.HERE)
W = Path(__file__).parent / 'work'
ADDED = 'cs_related_scope_20261022'
LEFT = str(H / 'hierarchy/cs-related-captures-mit.sqlite')
SRCDB = {'hierarchy/mit/thesis-captures.sqlite': str(H / 'hierarchy/mit/thesis-captures.sqlite'),
         'hierarchy/cs-related-captures-mit.sqlite': LEFT}
SLUG = {'aeronautics-astronautics': 'Aeronautics and Astronautics', 'media-arts-sciences': 'Media Arts and Sciences',
        'urban-studies-planning': 'Urban Studies and Planning', 'architecture': 'Architecture', 'biological-engineering': 'Biological Engineering',
        'chemical-engineering': 'Chemical Engineering', 'civil-environmental-engineering': 'Civil and Environmental Engineering',
        'data-systems-society': 'Institute for Data, Systems, and Society', 'harvard-mit-health-sciences-technology': 'Health Sciences and Technology',
        'materials-science-engineering': 'Materials Science and Engineering', 'mechanical-engineering': 'Mechanical Engineering',
        'nuclear-science-engineering': 'Nuclear Science and Engineering', 'anthropology': 'Anthropology',
        'comparative-media-studies-writing': 'Comparative Media Studies/Writing', 'economics': 'Economics',
        'linguistics-philosophy': 'Linguistics and Philosophy', 'music-theater-arts': 'Music and Theater Arts', 'political-science': 'Political Science',
        'science-technology-society': 'Science, Technology, and Society', 'biology': 'Biology', 'brain-cognitive-sciences': 'Brain and Cognitive Sciences',
        'chemistry': 'Chemistry', 'earth-atmospheric-planetary-sciences': 'Earth, Atmospheric and Planetary Sciences', 'mathematics': 'Mathematics',
        'physics': 'Physics', 'management': 'Sloan School of Management', 'EECS': 'EECS', 'electrical-engineering-computer-science': 'EECS'}
FULL = {'EECS': 'Department of Electrical Engineering and Computer Science', 'Sloan School of Management': 'MIT Sloan School of Management',
        'Media Arts and Sciences': 'Program in Media Arts and Sciences (MIT Media Lab)', 'Comparative Media Studies/Writing': 'Comparative Media Studies/Writing',
        'Institute for Data, Systems, and Society': 'Institute for Data, Systems, and Society (IDSS)',
        'Health Sciences and Technology': 'Harvard-MIT Program in Health Sciences and Technology'}
full = lambda d: FULL.get(d, f'Department of {d}')
PROF_HEADS = {'Professors', 'Associate Professors', 'Assistant Professors', 'Professors of the Practice', 'Professors Emeriti'}
BAD = re.compile(r'\b(Visiting|Adjunct)\b|Research Scientist|Research Associate (of|in)\b|Research Engineer|\bLecturer\b|\bInstructor\b|Affiliate')
# start dates the first listing does not give (announcements / profile captures); value: (start, [(url, quote)])
PERIOD_START = {
    'Navid Azizan': ('2021-09', [('https://azizan.mit.edu/', 'Assistant Professor, Sep 2021 – Jun 2026 Department of Mechanical Engineering')]),
    'Gioele Zardini': ('2024-09', [('https://web.archive.org/web/20231107072207id_/https://gioele.science/', 'I am thrilled to share that I will join MIT as a faculty in Fall 2024.')]),
    'Pat Pataranutaporn': ('2025-09', [('https://web.archive.org/web/20250804173145id_/https://www.media.mit.edu/people/patpat/overview/', 'For Press + Media Pat Pataranutaporn Postdoctoral Associate'),
                                       ('https://web.archive.org/web/20250913060047id_/https://www.media.mit.edu/people/patpat/overview/', 'For Press + Media Pat Pataranutaporn Assistant Professor of Media Arts and Sciences')]),
}
PROBLEMS = []


def stored(url):
    h = mpcap.cached(url)
    if not h:
        raise KeyError(f'not in store: {url}')
    return h


def ev(url, quote, **kw):
    h = stored(url)
    if quote not in h['text']:
        PROBLEMS.append(f'quote not in capture: {url} :: {quote[:80]}')
    return dict(url=url, sha256=h['sha256'], quote=quote, **kw)


def copy_left(url):
    s = sqlite3.connect(f'file:{LEFT}?mode=ro', uri=True)
    r = s.execute('select content_type from captures where url=? and status=200 order by id desc limit 1', (url,)).fetchone()
    s.close()
    if r is None:
        return stored(url)
    return mpcap.copy(LEFT, url, 'select fetched_at, sha256, content from captures where url=? and status=200 order by id desc limit 1', (url,),
                      'hierarchy/cs-related-captures-mit.sqlite', ctype=r[0] or 'text/html')


def thesis_ev(t):
    """Copy the thesis record's DSpace capture into the store (unchanged) and cut its quotes."""
    if t['db'] in SRCDB:
        mpcap.copy(SRCDB[t['db']], t['url'], 'select fetched_at, sha256, content from captures where id=?', (t['capture_id'],), t['db'], ctype='application/json')
    h = stored(t['url'])
    for q in (t['quote_advisor'], t['quote_degree']):
        if not q or q not in h['text']:
            PROBLEMS.append(f"thesis quote missing: {t['handle']} {str(q)[:60]}")
    return dict(handle=t['handle'], student=t['student'], year=t['year'], url=t['url'], sha256=h['sha256'],
                quote_advisor=t['quote_advisor'], quote_degree=t['quote_degree'])


def trim(q, url):
    if 'eecs.mit.edu' in url:
        m = re.search(r'\s\S+@\S+', q)
        q = q[:m.start()] if m else q
    return q.strip()


def faculty_row(r):
    if BAD.search(r['quote']):
        return False
    return r['heading'] in PROF_HEADS or bool(re.search(r'\bProfessor', r['quote']))


def observed(r):
    ts = r['observed']
    return ts if '/web/' in r['url'] else f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}'


def kind(r):
    if 'eecs.mit.edu' in r['url']:
        return 'eecs_faculty_advisors' if 'faculty-advisors' in r['url'] else 'eecs_role_faculty'
    return 'mit_catalog_faculty:' + SLUG.get(r['dept'], r['dept'])


def title_of(q):
    m = re.match(r"^[^,]{3,60}?, (?:(?:MM|MD|MS|MArch|BArch|EdD|BA|SM|MBA|MA), )*(?:PhD|ScD|EdD|BArch|BA|MS|MM|MArch)\s+(.*)$", q)
    if m:
        return m.group(1)
    return q


def main(write):
    C = json.load(open(H / 'hierarchy/mit/cs-related-candidates.json'))
    L = json.load(open(W / 'listing-matches.json'))
    T = json.load(open(W / 'thesis-match.json'))
    A = json.load(open(W / 'affiliations.json'))
    census = {r['name']: r for r in json.load(open(H / 'census/mit-faculty.json'))}
    overrides_mit = json.load(open(H / 'hierarchy/census-overrides.json')).get('mit', {})
    for u in ['https://www.media.mit.edu/research/?filter=groups', 'https://tsl.mit.edu/', 'https://zardini.mit.edu/', 'https://mraghavan.github.io/', 'https://azizan.mit.edu/']:
        copy_left(u)
    ncap = sqlite3.connect(f'file:{mpcap.DB}?mode=ro', uri=True).execute(
        "select count(*) from captures where status=200 and (url like '%catalog.mit.edu%/schools/%/%/' or url like '%eecs.mit.edu/people/faculty-advisors%' or url like '%eecs.mit.edu/role/faculty%')").fetchone()[0]
    adds, homes, review, periods = [], [], [], {}
    for c in C:
        cn, aid = c['name'], c['author']
        rows = [dict(r, quote=trim(r['quote'], r['url'])) for r in L.get(aid, [])]
        th = T[aid]
        phd = sorted([t for t in th['theses'] if t['phd'] and t['year'] and 2016 <= t['year'] <= 2026 and t.get('quote_advisor')],
                     key=lambda t: -t['year'])
        aff = A[aid]
        base = dict(name=cn, openalex=[aid], cs_basis=dict(works=c['works'], dblp_works=c['dblp_works'], cs_share=c['cs_share']),
                    phd_records=dict(n=len({t['handle'] for t in phd}), years=sorted({t['year'] for t in phd})))
        if cn in FACULTY:
            spec = FACULTY[cn]
            fr = [r for r in rows if faculty_row(r) and not (spec.get('skip_rows') and re.search(spec['skip_rows'], r['quote']))]
            if not fr:
                review.append(dict(base, decision='unresolved', reason='no professor-rank listing row survived the filter')); continue
            home = spec['home']
            pref = lambda r: (SLUG.get(r['dept']) == home, r['observed'])
            by_year = {}
            for r in sorted(fr, key=pref, reverse=True):
                by_year.setdefault(r['year'], r)
            years = sorted(by_year)
            sources = [ev(r['url'], r['quote'], observed=observed(r), kind=kind(r)) for _, r in sorted(by_year.items())]
            last = max(fr, key=pref)
            also = sorted({SLUG.get(r['dept'], r['dept']) for r in fr} - {home})
            practice = spec.get('practice') or 'of the Practice' in last['quote']
            rank = 'emeritus' if re.search(r'Emerit', last['quote']) else ('teaching' if practice else 'ladder_faculty')
            basis, kind_ = None, None
            if phd:
                tev = [thesis_ev(t) for t in phd[:3]]
                basis = dict(kind='advises_phd', url=tev[0]['url'], sha256=tev[0]['sha256'], quote=tev[0]['quote_advisor'],
                             theses=base['phd_records']['n'], phd_theses=tev,
                             note=f"DSpace@MIT thesis records name {spec['name']} as thesis supervisor (dc.contributor.advisor) on {base['phd_records']['n']} doctoral theses issued "
                                  f"{base['phd_records']['years'][0]}-{base['phd_records']['years'][-1]}; the three most recent are quoted.")
            elif spec.get('phd_url'):
                u, q = spec['phd_url']
                basis = dict(kind='advises_phd', **ev(u, q), note='Stated PhD advising: the faculty page lists current and former Ph.D. students; no DSpace@MIT doctoral thesis 2016-2026 names them yet.')
            elif spec.get('lab') and not practice:
                u, q, lab = spec['lab']
                basis = dict(kind='lab_head', **ev(u, q), lab=lab, note=f'Heads the {lab} ({"a Media Lab research group, one head" if "media.mit.edu" in u else "own lab"}); no DSpace@MIT doctoral thesis 2016-2026 names them as adviser.')
            if basis is None:
                why = ('professor of the practice with no PhD advising found (DSpace@MIT adviser query 2016-2026)' if practice else
                       'no doctoral thesis 2016-2026 in DSpace@MIT names them as adviser, and no lab or group they head alone was found')
                review.append(dict(base, decision='faculty_no_pi_evidence', reason=why, home_department=home, rank=rank, years_listed=years,
                                   evidence=[sources[0], sources[-1]], note=spec.get('note'))); continue
            # appointment period: first and last professor-rank listing (or a dated announcement)
            first, lastl = by_year[years[0]], by_year[years[-1]]
            start = str(years[0]); pev = [dict(url=s_['url'], sha256=s_['sha256'], quote=s_['quote']) for s_ in (sources[0],)]
            if spec['name'] in PERIOD_START:
                start, extra = PERIOD_START[spec['name']]
                pev = [ev(u, q) for u, q in extra]
            end = None if years[-1] >= 2026 else str(years[-1])
            pev.append(dict(url=sources[-1]['url'], sha256=sources[-1]['sha256'], quote=sources[-1]['quote']))
            per = dict(id='override_period_mit_' + re.sub(r'[^a-z0-9]+', '_', natural(spec['name']).lower()).strip('_'), start=start, end=end,
                       asof=None if end else f"{lastl['observed'][:4]}-{lastl['observed'][4:6]}-{lastl['observed'][6:8]}",
                       evidence=pev)
            periods[spec['name']] = per
            cen = census.get(spec.get('census') or '')
            orcid = [aff['orcid'][0][0]] if aff.get('orcid') else []
            names = list(dict.fromkeys([natural(n) for n in [cn] + c['names']] + spec.get('aliases', [])))
            row = dict(name=spec['name'], aliases=[n for n in names if n != spec['name']],
                       collection_person_id=(cen or {}).get('collection_person_id'), profile_url=(cen or {}).get('profile_url'),
                       dblp=list((cen or {}).get('dblp') or []), openalex=[aid], orcid=orcid,
                       identity_note=(f"OpenAlex {aid.split('/')[-1]} carries the name ({', '.join(c['names'][:4])}) on {c['works']} MIT-affiliated works 2016-2026 of the school sweep, "
                                      f"{c['dblp_works']} of them DBLP-indexed (top venues: {'; '.join(c['top_venues'][:3])}); "
                                      + (f"ORCID {orcid[0]} is on that author record's authorships. " if orcid else '')
                                      + (f"Already in census/mit-faculty.json as {cen['name']} (is_pi false); this row adds the PI evidence." if cen else '')).strip(),
                       rank=rank, title_as_listed=title_of(last['quote']), departments=[home], flags=['cs_related_outside_census_scope' if home != 'EECS' else 'cs_related_scope'],
                       years_listed=years, sources=sources, is_pi=True, pi_basis=basis, lab_units=[], added=ADDED)
            adds.append(row)
            hl = next((r for r in sorted(fr, key=lambda r: r['observed'], reverse=True) if SLUG.get(r['dept']) == home), last)
            homes.append(dict(school='mit', name=spec['name'], home_department=full(home), also=[full(a) for a in also], no_academic_department=False,
                              status='accepted', evidence=ev(hl['url'], hl['quote']),
                              note=(f"Course Catalog / department faculty listing: {title_of(hl['quote'])[:160]}" + (f" {spec['note']}" if spec.get('note') else ''))))
            review.append(dict(base, decision='accepted', reason='faculty (professor rank in a dated department listing), PI by ' + basis['kind'],
                               home_department=home, rank=rank, years_listed=years, period=dict(start=per['start'], end=per['end']), pi_basis_kind=basis['kind'],
                               evidence=[dict(kind='pi_basis:' + basis['kind'], url=basis['url'], sha256=basis['sha256'], quote=basis['quote']),
                                         sources[0], sources[-1]], note=spec.get('note')))
        elif cn in NOT_FACULTY_LISTED:
            nr = [r for r in rows if not faculty_row(r)] or rows
            r = max(nr, key=lambda r: r['observed'])
            review.append(dict(base, decision='not_faculty', reason=NOT_FACULTY_LISTED[cn],
                               evidence=[ev(r['url'], r['quote'], observed=observed(r), kind=kind(r))]))
        elif cn in UNLISTED:
            code = UNLISTED[cn]
            if rows:
                PROBLEMS.append(f'unlisted decision but listing rows exist: {cn}')
            dec = 'not_faculty'
            review.append(dict(base, decision=dec, reason=REASON[code] + (f'. {NOTES[cn]}' if cn in NOTES else ''), category=code,
                               evidence=[dict(kind='listing_absence', note=f'No entry in any of the {ncap} department faculty listings captured in hierarchy/mit/cs-related-captures.sqlite '
                                                                          '(MIT Course Catalog "Faculty and Teaching Staff" pages of every school, 2016-2026 Wayback editions plus the live 2026 pages; EECS faculty lists 2016-2026).'),
                                         dict(kind='openalex_affiliations', source='hierarchy/mit/openalex-sweep.sqlite (raw_affiliation_strings on the author\'s MIT works)',
                                              top=aff['top'][:4], years=aff['years'])]))
        else:
            review.append(dict(base, decision='unresolved', reason='no reviewed decision'))
            PROBLEMS.append(f'no decision: {cn}')
    # overlap checks
    for k in FACULTY:
        if k not in {c['name'] for c in C}:
            PROBLEMS.append(f'FACULTY key not a candidate: {k}')
    for k in list(NOT_FACULTY_LISTED) + list(UNLISTED):
        if k not in {c['name'] for c in C}:
            PROBLEMS.append(f'decision key not a candidate: {k}')
    import collections
    counts = collections.Counter(r['decision'] for r in review)
    print(json.dumps(dict(counts=counts, accepted=len(adds), problems=len(PROBLEMS)), default=dict))
    for p in PROBLEMS:
        print('PROBLEM', p)
    for a in adds:
        p = periods[a['name']]
        print(f"  {a['name']:28} {a['departments'][0]:36} {a['pi_basis']['kind']:12} {p['start']}-{p['end'] or ''} yrs={a['years_listed'][0]}-{a['years_listed'][-1]}({len(a['years_listed'])})")
    for r in review:
        if r['decision'] in ('faculty_no_pi_evidence', 'unresolved'):
            print('  ', r['decision'], r['name'], '|', r['reason'][:120])
    if not write or PROBLEMS:
        return
    out = dict(reviewed='2026-10-27', school='mit',
               rule=('Owner decision 2026-10-22: "All universities should include all faculty that work on CS-related topics / publish in CS venues (Even if not in CS)." '
                     'An MIT candidate (hierarchy/mit/cs-related-candidates.json) qualifies when (1) a professor-rank entry (Professor, Associate/Assistant Professor, '
                     'Professor of the Practice with PhD advising, Professor Emeritus) names them in a dated department faculty listing 2016-2026 (MIT Course Catalog '
                     '"Faculty and Teaching Staff" pages; EECS faculty lists) - research scientists, Lincoln Laboratory staff, lecturers, instructors, visiting and adjunct '
                     'appointments and HST-affiliated HMS faculty do not count; (2) a PI: a DSpace@MIT doctoral thesis record 2016-2026 names them as thesis supervisor '
                     '(dc.contributor.advisor), or a page states their current PhD advisees, or they head a lab / Media Lab research group alone. The appointment period '
                     'runs from the first to the last professor-rank listing (a dated announcement or profile capture where the listings start late).'),
               captures='hierarchy/mit/cs-related-captures.sqlite', tools='hierarchy/mit/cs-related-tools/ (decisions.py, build.py, scan_listings.py, thesis_index.py, thesis_match.py, affiliations.py, dspace_queries.py, copy_listings.py, mpcap.py)',
               counts=counts, decisions=review,
               notes=['Department listings: MIT Course Catalog department pages captured by the leftover 2026-10-22 session (hierarchy/cs-related-captures-mit.sqlite) and EECS lists from listings/mit/captures.sqlite, copied unchanged (sha256 kept, copied_from set).',
                      'Thesis supervision: DSpace@MIT discover records already captured (hierarchy/mit/thesis-captures.sqlite EECS harvest, leftover adviser queries) plus five new adviser queries (dspace_queries.py, 100 s per request).',
                      'Catalog editions are captured early in each calendar year, so a listing year is the year the capture shows the appointment; appointments that began mid-year start at the next listing unless an announcement dates them.'])
    json.dump(out, open(H / 'hierarchy/mit/cs-related-review.json', 'w'), indent=1, ensure_ascii=False, default=dict)
    json.dump(homes, open(H / 'hierarchy/mit/cs-related-home-departments.json', 'w'), indent=1, ensure_ascii=False)
    af = H / 'census/mit-additions.json'
    cur = [r for r in json.load(open(af)) if r.get('added') != ADDED]
    clash = {r['name'] for r in cur} & {a['name'] for a in adds}
    if clash:
        print('NAME CLASH with existing additions', clash); return
    json.dump(cur + adds, open(af, 'w'), indent=1, ensure_ascii=False)
    of = H / 'hierarchy/census-overrides.json'
    d = json.load(open(of))  # re-read right before writing: other agents edit other schools' keys
    m = d.setdefault('mit', {})
    for name, per in periods.items():
        e = m.setdefault(name, {})
        e['periods'] = [per]
        e.setdefault('why', 'Reviewed appointment period (MIT CS-related scope review 2026-10-27, hierarchy/mit/cs-related-review.json): dated department listings.')
    json.dump(d, open(of, 'w'), indent=1, ensure_ascii=False)
    print('written', len(adds), 'additions,', len(periods), 'periods')


main('--write' in sys.argv)
