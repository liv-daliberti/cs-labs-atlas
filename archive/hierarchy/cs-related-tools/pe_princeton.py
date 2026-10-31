"""Princeton CS-related scope review, supplement (2026-10-26): the candidates of the current DBLP-based
hierarchy/princeton/cs-related-candidates.json that the first review (hierarchy/princeton/cs-related-review.json, built from
the venue-based list by princeton_build.py) does not cover, plus one re-decision (Ronnie Sircar, rejected there only as
not CS-related, which the DBLP list contradicts). The first review's rows are left as they are.

Evidence: department faculty-list captures of claude-princeton-listings-20261022 (copied unchanged), DataSpace dissertation
records (hierarchy/princeton/thesis-captures.sqlite), and pages fetched into hierarchy/princeton/cs-related-captures.sqlite.
Every quote is checked as an exact substring of that store's text view.
-> <work>/princeton-additions-new.json, princeton-periods.json, princeton-home-departments.json, princeton-review-supplement.json
usage: pe_princeton.py <work_dir>
"""
import collections, json, re, sqlite3, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pecap  # noqa: E402
import helpers  # noqa: E402
import princeton_lib as L  # noqa: E402

HERE = pecap.HERE
W = Path(sys.argv[1])
pecap.use('princeton')
STORE = 'hierarchy/princeton/cs-related-captures.sqlite'
LST = L.LST
THESIS = HERE / 'hierarchy/princeton/thesis-captures.sqlite'
ADDED = 'cs_related_scope_20261022'
problems = []
C = json.load(open(HERE / 'hierarchy/princeton/cs-related-candidates.json'))
OLD = json.load(open(HERE / 'hierarchy/princeton/cs-related-review.json'))['decisions']
TI = json.load(open(W / 'princeton-thesis-index.json'))
LE = json.load(open(W / 'princeton-listing-entries.json'))


def fold(s):
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    if s.count(',') == 1:
        a, b = s.split(','); s = b + ' ' + a
    return ' '.join(re.findall(r'[a-z]+', s))


old_ids, old_names = set(), set()
for d in OLD:
    old_ids |= {o.rsplit('/', 1)[-1] for o in d.get('openalex') or []}
    old_names |= {fold(x) for x in [d['name']] + list(d.get('aliases') or [])}
UNCOV = [c for c in C if c['author'].rsplit('/', 1)[-1] not in old_ids and not any(fold(x) in old_names for x in c['names'])]
REDECIDE = [c for c in C if c['name'] == 'Ronnie Sircar']

WIKI_Y = 'https://en.wikipedia.org/wiki/Leeat_Yariv'
WIKI_S = 'https://en.wikipedia.org/wiki/Halil_Mete_Soner'
WIKI_K = 'https://en.wikipedia.org/wiki/Yannis_Kevrekidis'
ECON = 'https://economics.princeton.edu/people/'
# accepted: home departments, listing name forms (given, family as written on the lists), adviser forms (DataSpace 'Family, Given'),
# period bounds (int year, 'first' = first dated listing, None) and extra evidence
A = {
 'Leeat Yariv': dict(dept=['Economics'], forms=[('Leeat', 'Yariv')], adv=['Yariv, Leeat'], start=2017,
                     live=[(ECON, 'Leeat Yariv Uwe E. Reinhardt Professor of Economics', 'Economics')],
                     start_ev=[(WIKI_Y, 'held positions at UCLA and Caltech prior to her move to Princeton in 2017'),
                               (WIKI_Y, 'From fall of 2016 to 2017, she started her career at Princeton University as a visiting professor in their Department of Economics.')],
                     note='Visiting professor in Economics 2016-2017, then on the faculty from 2017 (Wikipedia); no Economics faculty-list capture before 2026 is stored, so the 2026 live list is the dated listing.'),
 'Clarence W. Rowley': dict(dept=['Mechanical and Aerospace Engineering'], forms=[('Clarence', 'Rowley')], adv=['Rowley, Clarence']),
 'Ioannis G. Kevrekidis': dict(dept=['Chemical and Biological Engineering', 'Program in Applied and Computational Mathematics'], forms=[('Yannis', 'Kevrekidis')],
                               adv=['Kevrekidis, Ioannis', 'Kevrekidis, Yannis'], end=2017, aliases=['Yannis Kevrekidis', 'Yannis G. Kevrekidis'],
                               end_ev=[(WIKI_K, 'In 2007, he became the Pomeroy and Betty Perry Smith Professor of Engineering, a position which he held until 2017.')],
                               manual=[('Mathematics', 'Yannis Kevrekidis Pomeroy and Betty Perry Smith Professor', 'Mathematics (PACM associated faculty)')],
                               note='Chemical and Biological Engineering (his DataSpace PhD records are CBE dissertations); listed on the Mathematics/PACM associated-faculty page 2016-2017; Johns Hopkins from 2017.'),
 'John M. Mulvey': dict(dept=['Operations Research and Financial Engineering'], forms=[('John', 'Mulvey')], adv=['Mulvey, John']),
 'Elizaveta Rebrova': dict(dept=['Operations Research and Financial Engineering'], forms=[('Elizaveta', 'Rebrova')], adv=['Rebrova, Elizaveta'], start='first'),
 'H. Mete Soner': dict(dept=['Operations Research and Financial Engineering'], forms=[('Mete', 'Soner')], adv=['Soner, H', 'Soner, Halil', 'Soner, Mete'], start=2019,
                       aliases=['Mete Soner', 'Halil Mete Soner'],
                       start_ev=[(WIKI_S, 'From 2009 to 2019 he was a Professor of Financial Mathematics at ETH Zürich')],
                       note='ETH Zürich to 2019 (Wikipedia); ORFE faculty lists from 2020; department chair by 2025.'),
 'Nicholas B. Turk-Browne': dict(dept=['Psychology', 'Princeton Neuroscience Institute'], forms=[('Nicholas', 'Turk-Browne')], adv=['Turk-Browne, Nicholas'], end=2017,
                                 aliases=['Nicholas Turk-Browne'],
                                 end_ev=[('https://ntblab.yale.edu/', 'Turk-Browne Lab | Exploring the Mind and Brain at Yale University')],
                                 note='Psychology professor (2017 list) and PNI faculty; his lab is at Yale since 2017 (last Princeton listing 2017).'),
 'Ludovic Tangpi': dict(dept=['Operations Research and Financial Engineering'], forms=[('Ludovic', 'Tangpi')], adv=['Tangpi, Ludovic'], start='first'),
 'Hanin, Boris': dict(name='Boris Hanin', dept=['Operations Research and Financial Engineering'], forms=[('Boris', 'Hanin')], adv=['Hanin, Boris'], start='first'),
 'Ronnie Sircar': dict(dept=['Operations Research and Financial Engineering'], forms=[('Ronnie', 'Sircar')], adv=['Sircar, Ronnie', 'Sircar, K. Ronnie', 'Sircar, Ronnie K'],
                       note='Re-decision: the first review rejected him only as not CS-related (venue-based rule); he is on the DBLP-based candidate list.'),
}
RJ = {
 'Hongliang Zhang': ('not_faculty', 'Postdoctoral researcher with H. Vincent Poor in ECE (2020-2023 output); on no Princeton faculty list; adviser of no DataSpace dissertation.'),
 'Mingzhe Chen': ('not_faculty', 'Postdoctoral researcher with H. Vincent Poor in ECE (2019-2022 output); on no Princeton faculty list; adviser of no DataSpace dissertation.'),
 'Yang, Zhuoran': ('not_faculty', 'Princeton ORFE PhD student (dissertation 2022).', 'student'),
 'Zhiguo Ding': ('not_faculty', 'Visiting Research Collaborator in ECE (a professor at Newcastle/Lancaster/Manchester), not Princeton faculty.', 'ding'),
 'Colin Defant': ('not_faculty', 'Princeton Mathematics PhD student (dissertation 2022, adviser Noga Alon).', 'student'),
 'Mathieu Laurière': ('not_faculty', 'Postdoctoral research associate in ORFE (2018-2022 output); on no Princeton faculty list; adviser of no DataSpace dissertation.'),
 'R. M. Churchill': ('not_faculty', 'Research physicist at the Princeton Plasma Physics Laboratory (PPPL), not a university faculty member; on no department faculty list.'),
 'Moran, Shay': ('not_faculty', 'Postdoctoral researcher (Princeton/IAS 2017-2020); on no Princeton faculty list.'),
 'Azarakhsh Jalalvand': ('not_faculty', 'Research scholar in MAE (plasma control) 2020-2026; on no Princeton faculty list; adviser of no DataSpace dissertation.'),
 'Suresh Venkatesh': ('not_faculty', 'Postdoctoral research associate in ECE (Sengupta group) 2019-2024; on no Princeton faculty list.'),
 'P. N. Johnson-Laird': ('faculty_no_pi_evidence', 'Psychology emeritus throughout 2016-2026 (emeriti list); no DataSpace dissertation names him adviser in 2016-2025 and no lab of his own in the window.', 'jl'),
 'Biswadip Dey': ('not_faculty', 'Postdoctoral research associate in MAE (Leonard group) 2016-2020; on no Princeton faculty list.'),
 'Stephane Ethier': ('not_faculty', 'Computational physicist at PPPL, not a university faculty member; on no department faculty list.'),
 'Yang, Lin F.': ('not_faculty', 'Postdoctoral research associate in ORFE (2017-2019); now faculty at UCLA; on no Princeton faculty list.'),
 'Noah Kravitz': ('not_faculty', 'Princeton Mathematics PhD student (dissertation 2025, adviser Noga Alon).', 'student'),
 'Mark K. Ho': ('not_faculty', 'Postdoctoral researcher (Psychology/CS, Griffiths lab) 2019-2023; on no Princeton faculty list.'),
 'Linfeng Zhang': ('not_faculty', 'Princeton PACM PhD student (dissertation 2020, advisers Weinan E and Roberto Car).', 'student'),
 'Liang Wang': ('not_faculty', 'Postdoctoral/research staff author (2018-2023 output, mixed fields under one name); on no Princeton faculty list; adviser of no DataSpace dissertation.'),
 'Emir Ali Karahan': ('not_faculty', 'Princeton ECE PhD student (dissertation 2025, adviser Kaushik Sengupta).', 'student'),
 'Muhammad Tariq': ('not_faculty', 'Visiting researcher (ECE, with Poor); on no Princeton faculty list.'),
 'Zhang, Cyril': ('not_faculty', 'Princeton CS PhD student (dissertation 2020, adviser Elad Hazan).', 'student'),
 'Zheng Yu': ('not_faculty', 'Princeton ORFE PhD student (dissertation 2022, adviser Mengdi Wang).', 'student'),
 'Sivakanth Gopi': ('not_faculty', 'Princeton CS PhD student (dissertation 2018, adviser Zeev Dvir).', 'student'),
 'Christodoulos A. Floudas': ('not_at_school_in_window', 'Left Princeton for Texas A&M in February 2015 and died in August 2016; his 2016-2017 DataSpace advising records are of students finishing after his departure.', 'floudas'),
 'Lu, Zhou': ('not_faculty', 'Princeton CS PhD student (dissertation 2025, adviser Elad Hazan).', 'student'),
 'Ryne Beeson': ('faculty_no_pi_evidence', 'MAE assistant professor from 2021 (MAE lists 2021-2026), but no DataSpace dissertation through 2025 names him adviser (senior theses only) and no captured page states a lab he heads (mae.princeton.edu answered with a bot challenge).', 'beeson'),
 'Fred S. Roberts': ('not_at_school_in_window', 'Rutgers professor (DIMACS); the Princeton affiliation on some works is incidental; on no Princeton faculty list.', 'roberts'),
 'Kritkorn Karntikoon': ('not_faculty', 'Princeton CS PhD student (dissertation 2024, adviser Bernard Chazelle).', 'student'),
}


def store_row(url):
    con = sqlite3.connect(f"file:{HERE / STORE}?mode=ro", uri=True)
    r = con.execute('select id, sha256, text, fetched_at from captures where (url=? or capture_url=?) and status=200 and error is null order by id desc limit 1',
                    (url, url)).fetchone()
    con.close()
    return r


def ev(url, quote, what, **kw):
    r = store_row(url)
    if not r or not quote or quote not in (r[2] or ''):
        problems.append(f'{what}: quote not in stored capture {url}: {(quote or "")[:90]}')
        return None
    return dict(url=url, sha256=r[1], quote=quote, **kw)


def bring(url, kind):
    if pecap.cached(url):
        return pecap.cached(url)
    return pecap.copy_from(str(LST) if kind == 'listing' else str(THESIS), url, kind)


def listing_rows(forms, dept_pref):
    want = {fold(g + ' ' + f) for g, f in forms}
    rows = [e for e in LE if fold(e['name']) in want and 2016 <= e['year'] <= 2026]
    by = {}
    for e in sorted(rows, key=lambda e: (e['dept'] in dept_pref, e['ts'])):
        by[e['year']] = e
    out = []
    for y in sorted(by):
        e = by[y]
        bring(e['capture_url'], 'listing')
        r = store_row(e['capture_url'])
        q = L.find_listing_quote(r[2], forms) if r else None
        if not q or not q.get('titled'):
            problems.append(f"listing quote not found {forms} {e['capture_url']}"); continue
        if re.search(r'Visiting|Emerit', q['quote']):
            continue
        x = ev(e['capture_url'], q['quote'], f'listing {forms}', observed=f"{e['ts'][:4]}-{e['ts'][4:6]}-{e['ts'][6:8]}", kind=f"dept_listing:{e['dept']}",
               rank=e['title'][:80], store=STORE, capture_copied_from='claude-princeton-listings-20261022/captures/listings.sqlite')
        if x:
            out.append(x)
    return out


def adviser_rows(adv):
    return [a for a in TI['advisers'] if a['role'] == 'phd' and 2016 <= (a['year'] or 0) <= 2026 and a['quote'] and any(a['adviser'].startswith(p) for p in adv)]


def rank_of(t):
    t = t or ''
    if re.search(r'Assistant Professor', t):
        return 'assistant'
    if re.search(r'Associate Professor', t):
        return 'associate'
    if re.search(r'Emerit', t):
        return 'emeritus'
    return 'ladder'


additions, periods, homes, review = [], {}, [], []
for c in UNCOV + REDECIDE:
    nm = c['name']; aid = c['author'].rsplit('/', 1)[-1]
    if nm in A:
        s = A[nm]; name = s.get('name', nm)
        sources = listing_rows(s['forms'], s['dept'])
        for dl, q, dname in s.get('manual', []):
            con = sqlite3.connect(f'file:{LST}?mode=ro', uri=True)
            seen = set()
            for cu, ts, raw, ct in con.execute('select capture_url, wayback_timestamp, raw_zlib, content_type from captures where http_status=200 and department=? order by wayback_timestamp', (dl,)):
                txt = pecap.mpcap.to_text(__import__('zlib').decompress(raw), ct or 'text/html')
                if q in txt and ts[:4] not in seen and 2016 <= int(ts[:4]) <= 2026:
                    bring(cu, 'listing')
                    x = ev(cu, q, f'{name} manual listing', observed=f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}', kind=f'dept_listing:{dname}', rank=q.split(name.split()[-1], 1)[-1].strip(),
                           store=STORE, capture_copied_from='claude-princeton-listings-20261022/captures/listings.sqlite')
                    if x:
                        sources.append(x); seen.add(ts[:4])
            con.close()
        for url, q, dept in s.get('live', []):
            fa = store_row(url)
            x = ev(url, q, f'{name} live list', observed=fa[3][:10] if fa else None, kind=f'dept_listing:{dept}', store=STORE)
            if x:
                sources.append(x)
        years = sorted({int(x['observed'][:4]) for x in sources})
        title = (sources[-1].get('rank') or sources[-1]['quote'].split(name.split()[-1], 1)[-1].strip()) if sources else None
        if s.get('live'):
            title = 'Uwe E. Reinhardt Professor of Economics'
        ar = adviser_rows(s['adv']); first = sorted([a for a in ar if a['pos'] == 0], key=lambda a: a['year']) or sorted(ar, key=lambda a: a['year'])
        pi = None
        if first:
            p = first[-1]; bring(p['url'], 'thesis')
            x = ev(p['url'], p['quote'], f'{name} thesis')
            if x:
                pi = dict(kind='advises_phd', url=x['url'], sha256=x['sha256'], quote=x['quote'], observed='2026-10-22', store=STORE,
                          note=f"Named adviser of {len(ar)} Princeton PhD dissertation record(s) {min(a['year'] for a in ar)}-{max(a['year'] for a in ar)} in DataSpace (Doctoral Dissertations, all departments); quoted: {p['student']} ({p['year']}, {p['dept']}).",
                          record=dict(id=p['id'], student=p['student'], year=p['year'], dept=p['dept'], title=p['title']))
        if not pi:
            problems.append(f'{name}: no PI basis')
        per = None
        if s.get('start') or s.get('end'):
            evid = []
            st, en = s.get('start'), s.get('end')
            if st == 'first' and sources:
                st = int(sources[0]['observed'][:4]); evid.append({k: sources[0][k] for k in ('url', 'sha256', 'quote', 'observed')} | dict(kind='first_dated_faculty_listing'))
            for url, q in s.get('start_ev', []) + s.get('end_ev', []):
                if not pecap.cached(url):
                    pecap.fetch(url)
                x = ev(url, q, f'{name} period')
                if x:
                    evid.append(x)
            if isinstance(en, int):
                last = [x for x in sources if int(x['observed'][:4]) == en]
                if last:
                    evid.append({k: last[-1][k] for k in ('url', 'sha256', 'quote', 'observed')} | dict(kind='last_dated_faculty_listing'))
            slug = re.sub(r'[^a-z0-9]+', '_', fold(name)).strip('_')
            per = dict(id=f'override_period_princeton_{slug}', start=str(st) if st else None, end=str(en) if en else None, asof=None, evidence=evid)
            periods[name] = dict(periods=[per])
        orc = helpers.orcids('princeton', [c['author']])
        aliases = list(dict.fromkeys([n for n in c['names'] if n != name and ',' not in n] + s.get('aliases', [])))
        row = dict(name=name, aliases=aliases, collection_person_id=None, profile_url=None, dblp=[], openalex=[c['author']], orcid=orc,
                   identity_note=(f"OpenAlex {aid} carries the name ({', '.join(c['names'][:3])}) on {c['works']} Princeton-affiliated works 2016-2026, "
                                  f"{c['dblp_works']} of them DBLP-indexed ({', '.join(c['top_venues'][:3])})" + (f"; ORCID {', '.join(orc)} from that author record." if orc else '.')),
                   rank=rank_of(title), title_as_listed=title, departments=s['dept'], years_listed=years, sources=sources, is_pi=True, pi_basis=pi,
                   lab_units=[], added=ADDED,
                   cs_related=dict(basis='hierarchy/princeton/cs-related-candidates.json (DBLP-indexed works)', school_works=c['works'], dblp_works=c['dblp_works'],
                                   cs_share=c['cs_share'], top_venues=c['top_venues'][:5]))
        if s.get('note'):
            row['review_note'] = s['note']
        additions.append(row)
        hev = sources[-1] if sources else None
        homes.append(dict(school='princeton', name=name, home_department=s['dept'][0], also=s['dept'][1:], no_academic_department=False, status='accepted',
                          evidence={k: hev[k] for k in ('url', 'sha256', 'quote')} if hev else None, note=s.get('note', '')))
        review.append(dict(name=name, aliases=aliases, candidate_sources=['cs-related-candidates (DBLP-based, 2026-10-22)'], openalex=[c['author']],
                           decision='accepted', reason='accepted', home_department=s['dept'][0], rank=row['rank'], years_listed=years,
                           pi_basis_kind=(pi or {}).get('kind'), phd_records=dict(n=len(ar), years=sorted({a['year'] for a in ar})),
                           period=(dict(start=per['start'], end=per['end']) if per else None), summary=s.get('note', ''),
                           supersedes=('first review: does_not_qualify / not_cs_related' if nm == 'Ronnie Sircar' else None),
                           evidence=[x for x in [pi and {k: pi[k] for k in ('url', 'sha256', 'quote')}] + [{k: y[k] for k in ('url', 'sha256', 'quote', 'observed', 'kind')} for y in sources[:1] + sources[-1:]] if x]))
    else:
        dec, summ, *flag = RJ[nm]
        flag = flag[0] if flag else None
        evid = []
        t = re.findall(r'[a-z]+', fold(nm)); fam, giv = t[-1], t[0]
        if flag == 'student':
            st = [a for a in TI['authors'] if a['role'] == 'phd' and a['quote'] and re.findall(r'[a-z]+', fold(a['author_raw']))[-1:] == [fam] and giv in fold(a['author_raw'])]
            for a in st[:1]:
                bring(a['url'], 'thesis')
                x = ev(a['url'], a['quote'], f'{nm} thesis author')
                if x:
                    evid.append(dict(x, kind='phd_dissertation_author', record=dict(id=a['id'], year=a['year'], dept=a['dept'], advisers=a['advisers'])))
        elif flag == 'ding':
            con = sqlite3.connect(f'file:{LST}?mode=ro', uri=True)
            for cu, txt in con.execute("select capture_url, text from captures where http_status=200 and department like '%Electrical%' order by wayback_timestamp"):
                bring(cu, 'listing'); r = store_row(cu)
                m = re.search(r'Zhiguo Ding Visiting Research Collaborator[^@]{0,80}', r[2] or '')
                if m:
                    x = ev(cu, m.group(0).strip(), f'{nm} listing')
                    if x:
                        evid.append(dict(x, kind='dept_listing:Electrical and Computer Engineering (visitors)')); break
            con.close()
        elif flag == 'jl':
            con = sqlite3.connect(f'file:{LST}?mode=ro', uri=True)
            for cu, in con.execute("select capture_url from captures where http_status=200 and department='Psychology' order by wayback_timestamp"):
                bring(cu, 'listing'); r = store_row(cu)
                i = (r[2] or '').find('Philip Johnson-Laird')
                if i >= 0:
                    j = r[2].rfind('Emerit', 0, i)
                    if j >= 0 and i - j < 2500:
                        x = ev(cu, 'Philip Johnson-Laird phil@princeton.edu', f'{nm} emeritus list')
                        if x:
                            evid.append(dict(x, kind='dept_listing:Psychology (emeriti)', section=r[2][j:j + 40])); break
            con.close()
        elif flag == 'floudas':
            x = ev('https://en.wikipedia.org/wiki/Christodoulos_Floudas', 'From February 2015, he was the director of the Energy Institute at Texas A&M University', nm)
            if x:
                evid.append(x)
        elif flag == 'roberts':
            x = ev('https://en.wikipedia.org/wiki/Fred_S._Roberts', 'he joined the Rutgers faculty in 1972.', nm)
            if x:
                evid.append(x)
        elif flag == 'beeson':
            evid += listing_rows([('Ryne', 'Beeson')], ['Mechanical and Aerospace Engineering'])[-1:]
        if not evid:
            evid.append(dict(kind='absence', note='No stored Princeton department faculty list 2016-2026 (non-CS lists of claude-princeton-listings-20261022) names the person with a faculty title, and no DataSpace doctoral dissertation 2016-2025 names them adviser or author.'))
        review.append(dict(name=nm, aliases=[n for n in c['names'] if n != nm], candidate_sources=['cs-related-candidates (DBLP-based, 2026-10-22)'],
                           openalex=[c['author']], decision=dec, reason=dec, summary=summ, evidence=evid))

json.dump(additions, open(W / 'princeton-additions-new.json', 'w'), indent=1, ensure_ascii=False)
json.dump(periods, open(W / 'princeton-periods.json', 'w'), indent=1, ensure_ascii=False)
json.dump(homes, open(W / 'princeton-home-departments.json', 'w'), indent=1, ensure_ascii=False)
json.dump(review, open(W / 'princeton-review-supplement.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(dict(uncovered=len(UNCOV), redecided=len(REDECIDE), accepted=len(additions), periods=len(periods),
                      by_decision=collections.Counter(r['decision'] for r in review), problems=problems), indent=1, ensure_ascii=False))
