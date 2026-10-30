"""Build the Princeton outputs of the CS-related scope review (owner decision 2026-10-22) from princeton_decisions.py:

census/princeton-additions.json          one census row per qualifier (shape of census/<school>-additions.json); read by
                                         tools/pi_hierarchy.py, which appends census/<school>-additions.json to the census
listings/princeton/listings.json         yearly department-listing rows of the qualifiers (keys of listings/<school>/listings.json)
hierarchy/princeton/cs-related-review.json   every decision (qualifies / does_not_qualify) with reason and evidence

Every quote is checked as an exact substring of the capture stored in hierarchy/cs-related-captures-princeton.sqlite
(listing captures copied from claude-princeton-listings-20261022/captures/listings.sqlite, DataSpace OAI pages copied from
hierarchy/princeton/thesis-captures.sqlite, Wayback pages fetched by this review).
usage: princeton_build.py <csrel_dir> <work_dir>
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import collections, datetime, json, re, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cscap  # noqa: E402
import helpers  # noqa: E402
import princeton_lib as L  # noqa: E402
import princeton_decisions as D  # noqa: E402
from helpers import Name, toks  # noqa: E402

HERE = Path(__file__).resolve().parents[2]
STORE = 'hierarchy/cs-related-captures-princeton.sqlite'
THESIS_DB = str(HERE / 'hierarchy/princeton/thesis-captures.sqlite')
THESIS_REL = 'hierarchy/princeton/thesis-captures.sqlite'
ADDED = 'cs_related_scope_20261022'
csrel, work = Path(sys.argv[1]), Path(sys.argv[2])
cscap.use('princeton')
T = {r['name']: r for r in json.load(open(csrel / 'princeton-triage.json'))}
PA = json.load(open(csrel / 'princeton-phd-advising.json'))
EV = json.load(open(work / 'princeton-evidence.json'))
TI = json.load(open(work / 'princeton-thesis-index.json'))
A = helpers.index('princeton')
problems = []


def store_id(url):
    con = sqlite3.connect(f"file:{HERE / STORE}?mode=ro", uri=True)
    r = con.execute('select id, fetched_at from captures where (url=? or capture_url=?) and status=200 and error is null order by id desc limit 1', (url, url)).fetchone()
    con.close()
    return r


def ensure_listing(cu):
    if not cscap.cached(cu):
        cscap.copy_listing(str(L.LST), cu, L.LST_REL)
    return cscap.cached(cu)


def ensure_thesis(url):
    if not cscap.cached(url):
        cscap.copy_thesis(THESIS_DB, url, THESIS_REL)
    return cscap.cached(url)


def checked(url, quote, what):
    if not cscap.quote_ok(url, quote):
        problems.append(f'{what}: quote not in capture {url}: {quote[:80]}')
        return False
    return True


def observed(ts):
    return f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}'


def dept_name(d, page_url):
    if 'ece.princeton' in page_url or 'ee.princeton' in page_url:
        return 'Electrical and Computer Engineering'
    if 'math.princeton' in page_url:
        return 'Mathematics'
    if 'orfe.princeton' in page_url:
        return 'Operations Research and Financial Engineering'
    if 'psych' in page_url:
        return 'Psychology'
    if 'sociology' in page_url:
        return 'Sociology'
    if 'mae.princeton' in page_url:
        return 'Mechanical and Aerospace Engineering'
    if 'lsi.princeton' in page_url:
        return 'Lewis-Sigler Institute for Integrative Genomics'
    if 'eeb.princeton' in page_url:
        return 'Ecology and Evolutionary Biology'
    if 'cs.princeton' in page_url:
        return 'Computer Science'
    return d


# ------------------------------------------------------------------ listing hits for qualifiers
def caps_for(pattern):
    rows = [dict(src='listings', page_url=pu, capture_url=cu, ts=ts) for _, pu, cu, ts, _ in L.listing_captures(pattern)]
    con = sqlite3.connect(f"file:{HERE / STORE}?mode=ro", uri=True)
    like = '%' + pattern.strip('%') + '%'
    for cu, in con.execute("select distinct capture_url from captures where capture_url like ? and status=200 and error is null", (like,)):
        if not re.search(r'/people(?:-list)?/faculty/?$', cu):
            continue  # only department faculty lists, never a person's profile page
        if not any(r['capture_url'] == cu for r in rows):
            rows.append(dict(src='review', page_url=cu.split('id_/', 1)[-1], capture_url=cu, ts=re.search(r'/web/(\d{14})', cu).group(1)))
    con.close()
    return rows


_texts = {}


def text_of(r):
    if r['capture_url'] not in _texts:
        _texts[r['capture_url']] = L.listing_text(r['capture_url']) if r['src'] == 'listings' else cscap.text(r['capture_url'])
    return _texts[r['capture_url']]


def written_name(quote, forms):
    ft, idx = L.fold(quote)
    for given, fam in forms:
        m = L.name_rx(given, fam).search(ft)
        if m:
            return quote[idx[m.start()]:idx[m.end() - 1] + 1]
    return None


def listing_rows(name, q):
    hits = []
    for pat in q['pages']:
        for r in caps_for(pat):
            f = L.find_listing_quote(text_of(r), [tuple(x) for x in q['forms']])
            if not f:
                continue
            quote, sec, titled = f['quote'], f['section'], f['titled']
            emer = bool(re.search(r'Emerit', quote)) or (not titled and sec in ('Emeritus Faculty', 'Emeriti', 'Faculty Emeriti'))
            visiting = bool(re.search(r'\bVisiting\b', quote)) or (not titled and sec == 'Visiting Faculty')
            if not titled and not emer:
                continue  # name-only entries outside an emeritus section (visiting, lecturer lists) prove nothing
            if visiting:
                continue
            fut = 'Joining the Department' in quote
            if not fut:
                t_ = text_of(r); i_ = t_.find(quote)
                m_ = re.match(r'\s*(Joining the Department of \w+ in \w+)', t_[i_ + len(quote):i_ + len(quote) + 80]) if i_ >= 0 else None
                if m_:
                    fut = True; quote = t_[i_:i_ + len(quote) + m_.end()]
            hits.append(dict(r, quote=quote, emeritus=emer, future=fut, titled=titled, section=sec if not titled else None))
    hits.sort(key=lambda h: h['ts'])
    rows, seen = [], set()
    for h in hits:
        y = int(h['ts'][:4]); half = 'H1' if int(h['ts'][4:6]) <= 6 else 'H2'
        if (y, half) in seen or not (2016 <= y <= 2026):
            continue
        if h['src'] == 'listings':
            ensure_listing(h['capture_url'])
        if not checked(h['capture_url'], h['quote'], name):
            continue
        seen.add((y, half))
        st = cscap.cached(h['capture_url'])
        nm_written = written_name(h['quote'], q['forms']) or name
        if h['titled']:
            rest = h['quote'][h['quote'].find(nm_written) + len(nm_written):].strip()
            if rest.startswith(nm_written):
                rest = rest[len(nm_written):].strip()
            rank = rest
        else:
            rank = 'Emeritus Faculty'
        rows.append(dict(pi=name, department=dept_name(None, h['page_url']), page_url=('https://' + h['page_url']) if not h['page_url'].startswith('http') else h['page_url'],
                         capture_url=h['capture_url'], wayback_timestamp=h['ts'], observed_on=observed(h['ts']), year=y, sha256=st['sha256'], quote=h['quote'],
                         rank_as_listed=rank[:120] or None, section_heading=h['section'], name_as_written=nm_written,
                         emeritus=h['emeritus'], visiting=False,
                         future_start_note=('listed in advance of the start: "Joining the Department of Psychology in July"' if h['future'] else None),
                         outside_pi_departments=True, listing=dept_name(None, h['page_url']) + ' faculty list', half=half, match_basis='name',
                         listing_source=ADDED, store=f"{STORE}#{store_id(h['capture_url'])[0]}",
                         capture_copied_from=L.LST_REL if h['src'] == 'listings' else None))
    return rows


# ------------------------------------------------------------------ PI basis from DataSpace
JOINED = re.compile(r'[a-z][A-Z]')


def phd_records(names):
    nm = Name(names)
    out = [p for p in PA if p['role'] == 'phd' and p['quote'] and nm.match(p['adviser']) and len(toks(p['adviser'])) <= 4 and not JOINED.search(p['adviser'].replace('Mc', 'Mc_'))]
    return sorted(out, key=lambda p: (p['year'], p['student']))


def pi_basis(name, q):
    if q.get('pi'):
        x = q['pi']
        st = cscap.cached(x['url'])
        if not st:
            problems.append(f'{name}: PI capture not stored {x["url"]}'); return None, None
        checked(x['url'], x['quote'], name + ' pi_basis')
        sid = store_id(x['url'])
        return dict(kind=x['kind'], url=x['url'], sha256=st['sha256'], quote=x['quote'], observed=observed(re.search(r'/web/(\d{14})', x['url']).group(1)) if '/web/' in x['url'] else sid[1][:10],
                    store=f'{STORE}#{sid[0]}', note=x['note']), dict(n=0)
    recs = phd_records([name] + [q['t']] + list(q.get('aliases') or []))
    if not recs:
        problems.append(f'{name}: no DataSpace PhD record'); return None, None
    r = recs[-1]
    ensure_thesis(r['url'])
    checked(r['url'], r['quote'], name + ' pi_basis')
    sid = store_id(r['url'])
    yrs = sorted({p['year'] for p in recs})
    note = (f"Named adviser of {len(recs)} Princeton PhD dissertation record(s) {yrs[0]}-{yrs[-1]} in DataSpace (Doctoral Dissertations community, "
            f"all departments); quoted: {r['student']} ({r['year']}, {r['dept']}), {r['handle'] or r['id']}.")
    return dict(kind='advises_phd', url=r['url'], sha256=r['sha256'], quote=r['quote'], observed=sid[1][:10], store=f'{STORE}#{sid[0]}', note=note,
                record=dict(id=r['id'], handle=r['handle'], student=r['student'], year=r['year'], dept=r['dept'], title=r['title'])), dict(n=len(recs), years=yrs)


# ------------------------------------------------------------------ collection person
import gzip  # noqa: E402
C = json.load(gzip.open(str(P.SITE_ROOT / 'atlas/data/collection-princeton.json.gz'), 'rt'))
PEOPLE = C['people'] if isinstance(C['people'], list) else list(C['people'].values())
PIS = json.load(open(HERE / 'hierarchy/princeton/pis.json'))
PI_PERSONS = {i for p in PIS for i in p['personIds']}


def person_of(names, oa_ids):
    nm = Name(names)
    c = [p for p in PEOPLE if nm.match(p['name']) and p['id'] not in PI_PERSONS]
    lead = [p for p in c if p['id'].startswith('leader_') and 'PI / faculty' in (p.get('roles') or [])]
    if len(lead) == 1:
        return lead[0]['id']
    src = [p for p in c if any(p['id'].endswith(a) for a in oa_ids)]
    if len(src) == 1:
        return src[0]['id']
    cs = [p for p in c if p['id'].startswith('member_cs_structure_')]
    if len(cs) == 1:
        return cs[0]['id']
    return None


# ------------------------------------------------------------------ CS basis
def cs_basis(q):
    ids = ['https://openalex.org/' + i for i in q['oa']]
    ws, seen = [], set()
    for w in helpers.cs_works('princeton', ids):
        k = (w['venue'], w['year']) if 'eBooks' in w['venue'] or w['title'].startswith('Chapter') else w['oa']
        if k not in seen:
            seen.add(k); ws.append(w)
    raw = sum(A[i]['cs'] for i in ids if i in A); n = sum(A[i]['n'] for i in ids if i in A)
    ex = sorted(ws, key=lambda w: -w['year'])[:5]
    return dict(basis=q['basis'], cs_venue_works=raw, cs_venue_works_distinct_listed=len(ws), school_works=n,
                definition='works 2016-2026 whose own authorship lists Princeton (institution lineage) in a venue of hierarchy/cs-venues.json (repositories never count); author index hierarchy/cs-related-tools/author_index.py over hierarchy/princeton/openalex-sweep.sqlite',
                examples=[dict(oa=w['oa'], year=w['year'], venue=w['venue'], title=w['title']) for w in ex]), ids


# ------------------------------------------------------------------ qualifiers
additions, listing_out, decisions = [], [], []
for name, q in D.QUALIFIES.items():
    rows = listing_rows(name, q)
    good = [r for r in rows if not r['future_start_note']]
    years = sorted({r['year'] for r in good})
    if not years:
        problems.append(f'{name}: no listing year')
    pb, pstat = pi_basis(name, q)
    csb, ids = cs_basis(q)
    orc = helpers.orcids('princeton', ids)
    main = A.get(ids[0], {})
    ident = (f"OpenAlex {ids[0].rsplit('/', 1)[-1]} carries the name ({', '.join(list(main.get('raw', {}))[:2])}) on {main.get('n')} Princeton-affiliated works 2016-2026 "
             f"({', '.join(list(main.get('venues', {}))[:3])})" + (f"; the split author ids {', '.join(i.rsplit('/', 1)[-1] for i in ids[1:])} carry the same ORCID" if len(ids) > 1 else '')
             + (f"; ORCID {', '.join(orc)} from those author records." if orc else '.'))
    srcs, sy = [], set()
    for r in good:
        if r['year'] in sy:
            continue
        sy.add(r['year'])
        srcs.append(dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed_on'], kind='dept_listing:' + r['department'],
                         rank=r['rank_as_listed'], emeritus=r['emeritus'], store=r['store'], **({'capture_copied_from': r['capture_copied_from']} if r['capture_copied_from'] else {})))
    last = good[-1] if good else None
    lab_units = []
    if q.get('lab') and pb:
        if checked(pb['url'], q['lab']['quote'], name + ' lab'):
            lab_units = [dict(name=q['lab']['name'], url=pb['url'], evidence=dict(url=pb['url'], sha256=pb['sha256'], quote=q['lab']['quote'], kind='faculty_profile'))]
    row = dict(name=name, aliases=list(dict.fromkeys([a for a in [q['t']] + list(q.get('aliases') or []) if a != name])),
               collection_person_id=person_of([name] + list(q.get('aliases') or []), q['oa']),
               profile_url=(q['pi']['url'].split('id_/', 1)[-1] if q.get('pi') else None), dblp=[], openalex=ids, orcid=orc, identity_note=ident,
               rank=q['rank'], title_as_listed=(last['rank_as_listed'] if last else None), departments=q['dept'], years_listed=years, sources=srcs,
               is_pi=True, pi_basis=pb, lab_units=lab_units, cs_related=csb, added=ADDED, flags=['cs_related_outside_computing'] + list(q.get('flags') or []))
    if q.get('note'):
        row['note'] = q['note']
    additions.append(row)
    listing_out += rows
    ev = [dict(url=pb['url'], sha256=pb['sha256'], quote=pb['quote'], observed=pb['observed'], kind='pi_basis:' + pb['kind'])] if pb else []
    ev += [dict(url=s['url'], sha256=s['sha256'], quote=s['quote'], observed=s['observed'], kind=s['kind']) for s in (srcs[:1] + srcs[-1:] if len(srcs) > 1 else srcs)]
    decisions.append(dict(name=name, aliases=row['aliases'], candidate_sources=T[q['t']]['sources'], openalex=ids, decision='qualifies', reason='qualifies',
                          home_department=q['dept'][0], rank=q['rank'], years_listed=years, pi_basis_kind=pb['kind'] if pb else None,
                          phd_records=pstat, cs_basis=dict(basis=csb['basis'], cs_venue_works=csb['cs_venue_works'], school_works=csb['school_works']),
                          flags=row['flags'], summary=q.get('note') or '', evidence=ev))


# ------------------------------------------------------------------ rejections
def thesis_ev(rec, kind):
    if not rec or not rec.get('quote'):
        return None
    ensure_thesis(rec['url'])
    if not checked(rec['url'], rec['quote'], kind):
        return None
    sid = store_id(rec['url'])
    return dict(url=rec['url'], sha256=rec['sha256'], quote=rec['quote'], observed=sid[1][:10], kind=kind,
                note=f"DataSpace {rec['id']} ({rec['year']}, {rec['role']}; {rec['dept'][:80]})")


def listing_ev(x):
    ensure_listing(x['capture_url'])
    if not checked(x['capture_url'], x['quote'], 'reject listing'):
        return None
    st = cscap.cached(x['capture_url'])
    return dict(url=x['capture_url'], sha256=st['sha256'], quote=x['quote'], observed=observed(x['ts']), kind='dept_listing:' + dept_name(x['dept'], x['page_url']),
                capture_copied_from=L.LST_REL)


ABSENCE_PAGES = {  # department lists whose captures show the person absent (one per period)
    'cs': ['%cs.princeton.edu/people/faculty'], 'ece': D.ECE, 'orfe': ['%orfe.princeton.edu/people/faculty%'],
}


def absence_ev(surname, which, years=(2016, 2019, 2022, 2025)):
    out = []
    for key in which:
        caps = [c for pat in ABSENCE_PAGES[key] for c in L.listing_captures(pat)]
        for y in years:
            c = next((c for c in caps if int(c[3][:4]) == y), None)
            if not c:
                continue
            ensure_listing(c[2])
            t = cscap.text(c[2])
            if surname in L.fold(t)[0]:
                continue
            st = cscap.cached(c[2])
            out.append(dict(url=c[2], sha256=st['sha256'], absent=surname, observed=observed(c[3]), kind='dept_listing:' + dept_name(c[0], c[1]), capture_copied_from=L.LST_REL))
    return out


def index_ev(r):
    ids = r['oa']
    return dict(kind='author_index', openalex=[i.rsplit('/', 1)[-1] for i in ids], school_works=sum(A[i]['n'] for i in ids if i in A),
                cs_venue_works=sum(A[i]['cs'] for i in ids if i in A), cs_venue_works_distinct=r.get('cs_distinct'),
                source='hierarchy/cs-related-tools/author_index.py over hierarchy/princeton/openalex-sweep.sqlite and hierarchy/cs-venues.json (Princeton-affiliated authorships 2016-2026)')


ABSENT = {'Samir M. Perlaza': ('Perlaza', ['ece']), 'Sahil Singla': ('Singla', ['cs']), 'Sayash Kapoor': ('Kapoor', ['cs']), 'Wen-Xin Zhou': ('Zhou', ['orfe']),
          'Elizabeth Anne Watkins': ('Watkins', ['cs']), 'Marshini Chetty': ('Chetty', ['cs']), 'David M Blei': ('Blei', ['cs']), 'Rebecca Fiebrink': ('Fiebrink', ['cs']),
          'Moses S Charikar': ('Charikar', ['cs']), 'Theodore Kim': ('Theodore Kim', ['cs']), 'Daniel R Licata': ('Licata', ['cs'])}
MPR = json.load(open(HERE / 'hierarchy/princeton/missing-pi-review.json'))
for name, (reason, summary) in D.REJECTS.items():
    r = T[name]; e = EV[name]
    ev = []
    if reason == 'not_faculty_student':
        for a in e['authored'][:1]:
            x = thesis_ev(a, 'dataspace_author_record')
            if x:
                ev.append(x)
    if reason in ('not_faculty_postdoc', 'not_faculty_lecturer', 'not_faculty_visiting', 'not_faculty_research_staff', 'not_pi_in_window', 'not_cs_related', 'not_faculty_student'):
        ls = [x for x in e['listings'] if x.get('titled') or x.get('section') in ('Visiting Faculty',)]
        ls = [x for x in ls if not re.search(r'Graduate Students|Undergraduate Students', x['quote'])]
        for x in (ls[:1] + ls[-1:] if len(ls) > 1 else ls):
            y = listing_ev(x)
            if y:
                ev.append(y)
    if name in ABSENT:
        ev += absence_ev(*ABSENT[name])
    if reason in ('name_parse_artifact', 'not_at_school', 'not_faculty_research_staff', 'not_pi_in_window', 'not_cs_related', 'not_faculty_lecturer'):
        exs = [x for x in e['adv_examples'] if x['role'] == 'phd'] or e['adv_examples']
        for a in exs[:1]:
            x = thesis_ev(a, 'dataspace_adviser_record')
            if x:
                ev.append(x)
    if reason in ('not_pi_in_window',) and name not in ('Jaswinder Singh', 'David Dobkin'):
        ev.append(dict(kind='dataspace_phd_records', absent=name, note='no record of the Doctoral Dissertations community 2016-2025 (all departments; 4,599 adviser-dissertation pairs) names them adviser',
                       source=THESIS_REL))
    if name in ('Jaswinder Singh', 'David Dobkin'):
        d = next(d for d in MPR['decisions'] if d['name'].split()[-1] == name.split()[-1])
        ev.append(dict(kind='missing_pi_review', source='hierarchy/princeton/missing-pi-review.json', decision=d['decision'], reason=d['reason']))
    ev.append(index_ev(r))
    decisions.append(dict(name=name, aliases=r['aliases'], candidate_sources=r['sources'], openalex=[i.rsplit('/', 1)[-1] for i in r['oa']][:4],
                          decision='does_not_qualify', reason=reason, summary=summary,
                          dataspace_advising=e['adv_roles'], evidence=ev))

# ------------------------------------------------------------------ write
cnt = collections.Counter(d['reason'] for d in decisions if d['decision'] == 'does_not_qualify')
review = dict(reviewed='2026-10-22',
              rule=('Owner decision 2026-10-22: "All universities should include all faculty that work on CS-related topics / publish in CS venues (Even if not in CS)." '
                    'A Princeton person qualifies when (1) a faculty member of any department in some year 2016-2026 (professor ranks, incl. emeriti; lecturers without PhD advising, '
                    'research scholars, instructors, postdocs, students and visitors do not), (2) a PI: stated PhD advising 2016-2026 (a named adviser field of a DataSpace doctoral '
                    'dissertation record, or advisees named on their department profile) or a lab they head alone; senior-thesis advising never makes a PI, and (3) CS-related: on '
                    'hierarchy/princeton/cs-related-candidates.json, or at least 5 works 2016-2026 with a Princeton-affiliated authorship in a venue of hierarchy/cs-venues.json '
                    '(chapters of one book count once). Appointment years are dated department faculty-list captures (one row per year and half); visiting-faculty entries and '
                    'advance listings are not used. Faculty already in hierarchy/princeton/pis.json are not candidates.'),
              captures=STORE, tools='hierarchy/cs-related-tools/ (princeton_*.py, cscap.py, helpers.py, author_index.py, universe.py)',
              candidates=dict(universe='cs-related-candidates.json (24) + thesis-harvest non-PI advisers (98) = 121 names after merging',
                              department_list_scan='non-CS Princeton faculty lists stored by claude-princeton-listings-20261022 (ECE, ORFE, Mathematics, MAE, Psychology, Sociology, SPIA, LSI, Music, Architecture) matched to the author index (>=5 CS-venue works, not in pis.json): 20 more names',
                              author_index_scan='every other Princeton OpenAlex author with >=5 CS-venue works checked by hand (182, all students/postdocs/research staff except Daniel I. Rubenstein)'),
              counts=dict(reviewed=len(decisions), qualifies=sum(d['decision'] == 'qualifies' for d in decisions), does_not_qualify=sum(cnt.values()), by_reason=dict(cnt.most_common())),
              notes=['tools/princeton_census.py does not read additions; tools/pi_hierarchy.py appends census/princeton-additions.json to census/princeton-faculty.json, and reads listings/princeton/listings.json for yearly listings.',
                     'Live princeton.edu department pages (ece., eeb.) answered with a bot challenge (stored with error=bot-challenge, not retried); department lists come from Wayback captures.',
                     f"Flag {D.NONCOMP}: the person meets the 5-work bar only through venues of cs-venues.json that are not computing venues (Cell Systems, statistics or psychology journals)."],
              decisions=decisions)
json.dump(additions, open(HERE / 'census/princeton-additions.json', 'w'), indent=1, ensure_ascii=False)
(HERE / 'listings/princeton').mkdir(exist_ok=True)
json.dump(listing_out, open(HERE / 'listings/princeton/listings.json', 'w'), indent=1, ensure_ascii=False)
json.dump(review, open(HERE / 'hierarchy/princeton/cs-related-review.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(dict(additions=len(additions), listing_rows=len(listing_out), decisions=len(decisions), counts=review['counts'], problems=problems), indent=1))
