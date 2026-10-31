"""Missing-PI review (2026-10-22): advisers of CS theses who are not PIs (hierarchy/thesis-harvest-report.json
non_pi_advisers), decided one by one against the owner's PI rule, plus one CMU byline alias.

Rule: a PI is a faculty member of a computing department (Princeton CS; CMU's seven SCS departments; MIT EECS, CS+AI side;
EPFL IC; Berkeley EECS, CS division) with stated PhD advising in 2016-2026 or a lab they head. Centres, initiatives and
multi-PI groups are not labs. EPFL MERs count when they head their own lab or are stated PhD thesis directors.

Evidence: every quote below is an exact substring of a capture in hierarchy/missing-pi-captures.sqlite (pages fetched by
mpcap.py, or rows copied unchanged from earlier sweeps' stores with copied_from set); an 'absent' item records that a
named capture does not contain the name. This script re-verifies all of them before writing anything.

Writes (idempotent: rows/entries tagged by this pass are replaced, everything else is kept):
  census/mit-additions.json        + John Tsitsiklis
  census/epfl-additions.json       + Pearl Pu, Mathieu Salzmann (new file)
  hierarchy/census-overrides.json  cmu 'Fernando De La Torre Frade' aliases; epfl periods for Pearl Pu and Mathieu Salzmann
  hierarchy/<school>/missing-pi-review.json  every decision of the school, with its evidence
"""
import json, os, re, sqlite3, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpcap  # noqa: E402

HERE = mpcap.HERE
TAG = 'missing_pi_review_20261022'
TODAY = '2026-10-22'
CAPS = 'hierarchy/missing-pi-captures.sqlite'
con = sqlite3.connect(f'file:{mpcap.DB}?mode=ro', uri=True)
ROWS = {}
for url, cap, sha, fa, text, cf in con.execute('SELECT url, capture_url, sha256, fetched_at, text, copied_from FROM captures WHERE status=200 AND error IS NULL'):
    ROWS[url] = dict(sha256=sha, fetched_at=fa, text=text or '', copied_from=cf)
WB = re.compile(r'/web/(\d{4})(\d{2})(\d{2})')


def observed(url):
    m = WB.search(url)
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ROWS[url]['fetched_at'][:10]


def span(url, start, end=None, n=None):
    """The exact text of the capture from `start` through the first `end` after it (or n characters)."""
    t = ROWS[url]['text']
    i = t.find(start)
    assert i >= 0, (url, start)
    if end is not None:
        j = t.find(end, i)
        assert j >= 0, (url, end)
        return t[i:j + len(end)]
    return t[i:i + (n or len(start))]


def ev(url, quote, kind, note=None):
    r = ROWS[url]
    assert quote in r['text'], (url, quote)
    out = dict(url=url, sha256=r['sha256'], quote=quote, observed=observed(url), kind=kind)
    if note:
        out['note'] = note
    if r['copied_from']:
        out['capture_copied_from'] = r['copied_from']
    return out


def absent(url, name, kind, note=None):
    r = ROWS[url]
    assert name not in r['text'], (url, name)
    out = dict(url=url, sha256=r['sha256'], absent=name, observed=observed(url), kind=kind)
    if note:
        out['note'] = note
    return out


def window(url, name, extra=60):
    """name plus the listing text after it, cut at a word boundary (an exact substring)."""
    t = ROWS[url]['text']; i = t.find(name)
    assert i >= 0, (url, name)
    m = re.compile(r'\[email protected\]|\S+@epfl\.ch').search(t, i + len(name), i + len(name) + 120)  # a listing entry ends at its email
    if m:
        return t[i:m.end()]
    s = t[i:i + len(name) + extra]
    return s[:s.rfind(' ')] if len(t) > i + len(name) + extra else s


WAY = 'https://web.archive.org/web/'
BK_CS = [WAY + ts + 'id_/https://www2.eecs.berkeley.edu/Faculty/Lists/CS/faculty.html' for ts in
         ('20191014112202', '20210302054536', '20230926194702', '20250425124321', '20260311194209')] + ['https://www2.eecs.berkeley.edu/Faculty/Lists/CS/faculty.html']
BK_EECS = {y: WAY + ts for y, ts in [(2016, '20160327023702id_/http://www.eecs.berkeley.edu:80/Faculty/Lists/list.shtml'),
                                     (2017, '20171101140017id_/https://www2.eecs.berkeley.edu/Faculty/Lists/faculty.html'),
                                     (2019, '20190919131344id_/https://www2.eecs.berkeley.edu/Faculty/Lists/faculty.html'),
                                     (2021, '20210417150618id_/https://www2.eecs.berkeley.edu/Faculty/Lists/faculty.html'),
                                     (2025, '20250327042312id_/https://www2.eecs.berkeley.edu/Faculty/Lists/faculty.html'),
                                     (2026, '20260417001407id_/https://www2.eecs.berkeley.edu/Faculty/Lists/faculty.html')]}
EE_LIVE = 'https://www2.eecs.berkeley.edu/Faculty/Lists/EE/faculty.html'
EE_VIS = 'https://www2.eecs.berkeley.edu/Faculty/Lists/EE/visiting.html'
EPFL_IC = [u for u in ROWS if 'ic.epfl.ch' in u and 'professors' in u or 'schools/ic/about/faculty-members' in u]
EPFL_EDIC = [u for u in ROWS if 'edic-thesis-directors' in u]
EPFL_IC.sort(key=lambda u: observed(u)); EPFL_EDIC.sort(key=lambda u: observed(u))
HARVEST = 'hierarchy/thesis-harvest-report.json (non_pi_advisers); records in hierarchy/<school>/thesis-captures.sqlite'
DSP = 'https://dspace.mit.edu/server/api/core/items/'


def review_berkeley():
    out = []
    cs_abs = lambda nm: [absent(u, nm, 'dept_listing:EECS-CS', 'the CS-division faculty list does not name them') for u in BK_CS]
    out.append(dict(
        name='Yi Ma', decision='does_not_qualify', reason='homed_outside_scope',
        summary=('EECS faculty 2018-2024 (Professor in Residence), but in the EE division: the EECS-wide lists name him every year '
                 '2019-2025 while no CS-division faculty list 2019-2026 does, and the live EE Visiting Faculty list names him. '
                 'Since January 2025 he is a Visiting Professor at Berkeley, having moved to the University of Hong Kong '
                 '(Director of HKU IDS since 2023-01, Chair Professor in AI since 2023-07). Outside the scope (EECS, CS division) '
                 'in every year of the window, so no lab is added. On advising alone he would qualify (15 EECS dissertations '
                 '2020-2025 name him adviser) if the owner widened Berkeley to the EE division.'),
        thesis_harvest=dict(theses=15, years='2020-2025', roles='phd and masters', source=HARVEST),
        appointment=dict(start='2018', professor_in_residence_until='2024-12', visiting_professor_from='2025-01'),
        evidence=[ev(BK_EECS[2019], 'Yi Ma Professor in Residence 333A Cory Hall', 'dept_listing:EECS (all divisions)'),
                  ev(BK_EECS[2025], 'Yi Ma Professor in Residence 333A Cory Hall', 'dept_listing:EECS (all divisions)'),
                  ev(WAY + '20251002003248id_/https://www2.eecs.berkeley.edu/Faculty/Lists/visiting.html', 'Yi Ma Visiting Professor 333A Cory Hall', 'dept_listing:EECS visiting'),
                  ev(EE_VIS, 'EE Visiting Faculty Yi Ma Visiting Professor', 'dept_listing:EECS-EE visiting'),
                  ev('https://www2.eecs.berkeley.edu/Faculty/Homepages/yima.html', 'He joins the faculty of EECS of UC Berkeley in 2018.', 'faculty_homepage'),
                  ev('https://people.eecs.berkeley.edu/~yima/', span('https://people.eecs.berkeley.edu/~yima/', 'I have officially moved to the University of Hong Kong', 'since January 2025.'), 'own_homepage'),
                  ev('https://people.eecs.berkeley.edu/~yima/', 'Director of the Institute of Data Science (IDS), the University of Hong Kong, since January 1, 2023.', 'own_homepage')]
                 + cs_abs('Yi Ma')))
    out.append(dict(
        name='Gopala Anumanchipalli', aliases=['Gopala Krishna Anumanchipalli'], decision='does_not_qualify', reason='homed_outside_scope',
        summary=('EECS faculty since spring 2021 (Assistant, now Associate Professor, Robert E. and Beverly A. Brooks Professor), '
                 'in the EE division: the live EE Faculty List names him, the EECS-wide lists name him 2020-2026, and no '
                 'CS-division faculty list 2021-2026 does. Outside the scope (EECS, CS division). On advising alone he would '
                 'qualify (8 EECS theses 2024-2026) if the owner widened Berkeley to the EE division.'),
        thesis_harvest=dict(theses=8, years='2024-2026', roles='phd and masters', source=HARVEST),
        evidence=[ev(EE_LIVE, 'EE Faculty List EE Faculty List', 'dept_listing:EECS-EE (page heading)'),
                  ev(EE_LIVE, 'Gopala Krishna Anumanchipalli Associate Professor 4371 Gateway Building', 'dept_listing:EECS-EE'),
                  ev(BK_EECS[2021], 'Gopala Krishna Anumanchipalli Assistant Professor gopala@berkeley.edu', 'dept_listing:EECS (all divisions)'),
                  ev(BK_EECS[2026], 'Gopala Krishna Anumanchipalli Assistant Professor 490A Cory Hall', 'dept_listing:EECS (all divisions)'),
                  ev('https://www2.eecs.berkeley.edu/Faculty/Homepages/gopala.html', 'he joined the faculty of the Department of Electrical Engineering and Computer Sciences at UC Berkeley in Spring 2021', 'faculty_homepage')]
                 + cs_abs('Anumanchipalli')))
    mh = 'https://www.stat.berkeley.edu/~mmahoney/'
    out.append(dict(
        name='Michael Mahoney', aliases=['Michael William Mahoney'], decision='does_not_qualify', reason='not_faculty_of_a_computing_department',
        summary=('Faculty of the Department of Statistics, and at ICSI and LBNL; his EECS tie is membership of RISELab/AMPLab, '
                 'not an appointment. No EECS faculty, emeritus or visiting list 2016-2026 names him (all captured lists '
                 'checked). He co-advised 8 EECS theses 2016-2023, which does not make a Statistics professor an EECS PI.'),
        thesis_harvest=dict(theses=8, years='2016-2023', roles='phd and masters', source=HARVEST),
        evidence=[ev(mh, span(mh, 'I am in the Department of Statistics at UC Berkeley;', 'Director of the Big Data Group )'), 'own_homepage'),
                  ev(mh, 'I am also in the RISELab (in the past AMPLab ) in the Department of EECS', 'own_homepage')]
                 + [absent(u, 'Mahoney', 'dept_listing:EECS (all divisions)') for u in BK_EECS.values()]
                 + [absent(u, 'Mahoney', 'dept_listing:EECS-CS') for u in BK_CS],
        note='Every captured EECS list page of 2016-2026 in listings/berkeley/captures.sqlite (faculty, CS faculty, emeritus, visiting, teaching, new) was also checked: none contains "Mahoney".'))
    return out


def review_princeton():
    L16 = WAY + '20160406151830id_/https://www.cs.princeton.edu/people/faculty'
    L22 = WAY + '20220321143320id_/https://www.cs.princeton.edu/people/faculty'
    L22b = WAY + '20220916042410id_/https://www.cs.princeton.edu/people/faculty'
    E22 = WAY + '20220917162136id_/https://www.cs.princeton.edu/people/faculty?type=emeritus'
    L25 = WAY + '20251212150501id_/https://www.cs.princeton.edu/people/faculty'
    for u in (L16, L22, L22b, E22, L25):
        assert u in ROWS, u
    roster = ('claude-princeton-20261015/cs-people/rosters.json: 2,540 graduate-student rows and 6,347 graduate-alumni rows read '
              'from the CS rosters 2016-2026 (Wayback and live)')
    jps, dpd = 'https://www.cs.princeton.edu/people/profile/jps', 'https://www.cs.princeton.edu/people/profile/dpd'
    out = [dict(
        name='Jaswinder Pal Singh', aliases=['Jaswinder Singh', 'J. P. Singh'], decision='does_not_qualify', reason='no_phd_advising_and_no_own_lab_in_window',
        summary=('A CS professor throughout 2016-2026, but with no stated PhD advising in the window and no lab he heads. '
                 'Not in pis.json because tools/princeton_census.py takes the 91 own-lab PIs of the lab-by-lab records plus '
                 'faculty with a named PhD adviser field in 2016-2026 (ADDED), and he is in neither: his last PhD alumnus on the '
                 'CS roster graduated in 2014 (Adrian Soviani); no graduate-student roster row 2016-2026 names him adviser; '
                 'DataSpace has no 2016-2026 dissertation he advised (his 15 CS theses 2016-2023 are senior theses). '
                 'His one leadership role is co-director of DeCenter, a centre that Matt Weinberg directs, which is a '
                 'collective, not his lab. A 2026 postdoc (Aviv Yaish) is co-hosted with Weinberg; postdoc hosting is not PhD advising.'),
        thesis_harvest=dict(theses=15, years='2016-2023', roles='undergraduate (senior theses) only; 0 of 4,056 DataSpace PhD dissertation records 2016-2026 name him', source=HARVEST),
        roster_check=dict(source=roster, grad_student_rows_naming_him=0, grad_alumni_with_degree_2016_or_later=0, latest_phd_alumnus='Adrian Soviani, PhD 2014'),
        evidence=[ev(L16, 'Jaswinder Singh Professor Ph.D., Stanford University, 1993', 'dept_listing:Computer Science'),
                  ev(L25, 'Jaswinder Pal Singh Professor of Computer Science, Technology, and Societal Change', 'dept_listing:Computer Science'),
                  ev('https://www.cs.princeton.edu/people/gradalumni?page=21', 'Adrian Soviani Adviser(s): Jaswinder Pal Singh Degree: PhD, 2014', 'grad_alumni_roster', 'his latest PhD alumnus'),
                  ev(jps, 'He is a co-director of the Princeton Center for the Decentralization of Power Through Blockchain Technology (DeCenter)', 'faculty_profile'),
                  ev('https://decenter.princeton.edu/steering-committee/', 'Matt Weinberg Associate Professor of Computer Science and Director of the DeCenter', 'centre_page', 'DeCenter is a centre with its own director: a collective, not a lab'),
                  ev('https://decenter.princeton.edu/steering-committee/', 'Jaswinder Pal Singh Professor of Computer Science, Technology and Societal Change', 'centre_page')]),
        dict(
        name='David Dobkin', decision='does_not_qualify', reason='no_phd_advising_and_no_own_lab_in_window',
        summary=('CS professor until 2022 (Phillip Y. Goldman \'86 Professor), emeritus from fall 2022. No stated PhD advising in '
                 '2016-2026: his last PhD alumnus graduated in 2001 (Alejo Hausner); no graduate-student roster row 2016-2026 '
                 'names him adviser; DataSpace has no 2016-2026 dissertation he advised (his 5 CS theses 2016-2018 are senior '
                 'theses). In window PhD defences he appears on committees, not as adviser (e.g. examiner at Ohad Fried\'s FPO, 2017). The Graphics Group lists him '
                 'with three other faculty (a multi-PI group, not his lab). Not in pis.json for the same reason as Singh.'),
        thesis_harvest=dict(theses=5, years='2016-2018', roles='undergraduate (senior theses) only; 0 of 4,056 DataSpace PhD dissertation records 2016-2026 name him', source=HARVEST),
        roster_check=dict(source=roster, grad_student_rows_naming_him=0, grad_alumni_with_degree_2016_or_later=0, latest_phd_alumnus='Alejo Hausner, PhD 2001'),
        evidence=[ev(L22, "David Dobkin Phillip Y. Goldman '86 Professor Ph.D., Harvard University, 1973", 'dept_listing:Computer Science'),
                  absent(L22b, 'Dobkin', 'dept_listing:Computer Science', 'off the faculty list by 2022-09-16'),
                  ev(E22, "David Dobkin Phillip Y. Goldman '86 Professor, Emeritus", 'dept_listing:Computer Science (emeritus)'),
                  ev(dpd, "David Dobkin Phillip Y. Goldman '86 Professor, Emeritus", 'faculty_profile'),
                  ev('https://www.cs.princeton.edu/people/gradalumni?page=31', 'Alejo Hausner Adviser(s): David Dobkin Degree: PhD, 2001', 'grad_alumni_roster', 'his latest PhD alumnus'),
                  ev('https://lists.cs.princeton.edu/hyperkitty/list/talks@lists.cs.princeton.edu/thread/3HPYKS7ENMPH5G5HJWZS65RWGWGGPHI7/',
                     'Adam Finkelstein (adviser); readers: Tom Funkhouser and Eli Shechtman (Adobe); examiners: Szymon Rusinkiewicz and David Dobkin.', 'fpo_announcement', 'Ohad Fried FPO, May 2017'),
                  ev('https://gfx.cs.princeton.edu/gfx-people.php', 'Faculty David Dobkin Adam Finkelstein Felix Heide Szymon Rusinkiewicz', 'group_page', 'multi-PI group')])]
    return out


def tsitsiklis_row():
    d16, d19 = DSP + 'fb617a5f-584f-42e0-aca6-f5c7e5048da9', DSP + '8a7b0ddb-a230-44b5-805e-f245a8818bd9'
    adv16 = '"dc.contributor.advisor" : [ { "value" : "Asuman Ozdaglar and John N. Tsitsiklis."'
    adv19 = '"dc.contributor.advisor" : [ { "value" : "David Gamarnik and John N. Tsitsiklis."'
    phd16 = 'Thesis: Ph. D., Massachusetts Institute of Technology, Department of Electrical Engineering and Computer Science, 2016.'
    phd19 = 'Thesis: Ph. D., Massachusetts Institute of Technology, Department of Electrical Engineering and Computer Science, 2019'
    b16, b19 = ev(d16, adv16, 'dspace_phd_thesis'), ev(d19, adv19, 'dspace_phd_thesis')
    basis = dict(kind='advises_phd', url=d16, sha256=b16['sha256'], quote=adv16, theses=2,
                 phd_theses=[dict(handle='1721.1/105663', student='Kimon Drakopoulos', year=2016, url=d16, sha256=b16['sha256'], quote_advisor=adv16, quote_degree=ev(d16, phd16, 'dspace_phd_thesis')['quote']),
                             dict(handle='1721.1/124124', student='Martín Zubeldía Suárez', year=2019, url=d19, sha256=b19['sha256'], quote_advisor=adv19, quote_degree=ev(d19, phd19, 'dspace_phd_thesis')['quote'])],
                 note=('EECS Ph.D. theses 2016 and 2019 name him co-adviser (DSpace@MIT item records). The earlier census snapshot '
                       'counted 0 theses for him. He directed LIDS (2018-2021 listings), a multi-PI laboratory, not his own lab.'))
    c = next(r for r in json.load(open(f'{HERE}/census/mit-faculty.json')) if r['name'] == 'John Tsitsiklis')
    return dict(name='John Tsitsiklis', aliases=['John N. Tsitsiklis'], collection_person_id=c['collection_person_id'],
                profile_url=c['profile_url'], dblp=c['dblp'], openalex=['https://openalex.org/A5108523422'], orcid=['0000-0003-2658-8239'],
                identity_note=('OpenAlex A5108523422 carries the name on 18 MIT works of the school sweep, 16 of them on the cached DBLP '
                               'records of pid 00/4563 (claude-mit-20261020/raw/dblp_pubs.json.gz); the ORCID is the one on that OpenAlex author record.'),
                rank=c['rank'], title_as_listed=c['title_as_listed'], departments=c['departments'], flags=c.get('flags', []),
                years_listed=c['years_listed'], sources=c['sources'], is_pi=True, pi_basis=basis,
                lab_units=[dict(proposed=True, name='John Tsitsiklis group', url=c['profile_url'], evidence=basis)], added=TAG)


def review_mit(tsit):
    l16 = WAY + '20160104094659id_/http://www.eecs.mit.edu/people/faculty-advisors'
    l17 = WAY + '20170507163814id_/http://www.eecs.mit.edu/people/faculty-advisors'
    dz = DSP + '93dba851-bc4c-469d-baf5-68f68c90f859'
    wk = 'https://en.wikipedia.org/wiki/Matei_Zaharia'
    return [dict(name='John Tsitsiklis', decision='qualifies', added_to='census/mit-additions.json',
                 summary=('EECS faculty [AI+D] listed every year 2016-2026; stated PhD advising in the window: co-adviser of the EECS '
                          'Ph.D. theses of Kimon Drakopoulos (2016) and Martín Zubeldía Suárez (2019). The census had is_pi False only '
                          'because its DSpace snapshot found none of his theses. His LIDS directorship is a multi-PI lab, so his own lab '
                          'is a new "John Tsitsiklis group". The listings cover every year, so no reviewed period is needed.'),
                 evidence=[tsit['pi_basis']['phd_theses'][0], tsit['pi_basis']['phd_theses'][1]]),
            dict(name='Matei Zaharia', aliases=['Matei A. Zaharia'], decision='does_not_qualify', reason='no_phd_advising_and_no_own_lab_in_window',
                 summary=('An MIT EECS assistant professor only until 2016 (listed 2016-01, gone by 2017-05; Stanford from 2016). His '
                          'MIT advising in the window is five 2016 M.Eng. theses; no MIT Ph.D. thesis 2016-2026 names him, and no '
                          'capture shows a lab he headed at MIT. Master\'s-only advising does not make a PI. (He is now Berkeley EECS '
                          'faculty, which is the Berkeley census\'s concern, not MIT\'s.)'),
                 thesis_harvest=dict(theses=5, years='2016', roles='masters (M.Eng.) only', source=HARVEST),
                 evidence=[ev(l16, 'Matei Zaharia Douglas Ross (1954) Career Development Professor of Software Technology', 'dept_listing:EECS'),
                           absent(l17, 'Zaharia', 'dept_listing:EECS', 'not on the EECS faculty list by 2017-05-07'),
                           ev(dz, '"dc.contributor.advisor" : [ { "value" : "Matei Zaharia."', 'dspace_thesis'),
                           ev(dz, 'Thesis: M. Eng., Massachusetts Institute of Technology, Department of Electrical Engineering and Computer Science, 2016.', 'dspace_thesis'),
                           ev(wk, 'He joined the faculty of MIT in 2015, and then became an assistant professor of computer science at Stanford University in 2016.', 'encyclopedia', 'secondary source; consistent with the listings')])]


def epfl_sources(name, needle):
    out = []
    for u in EPFL_IC:
        if needle in ROWS[u]['text']:
            out.append(ev(u, window(u, needle, 45), 'dept_listing:IC'))
    for u in EPFL_EDIC:
        if needle in ROWS[u]['text']:
            out.append(ev(u, window(u, needle, 35), 'edic_thesis_directors'))
    return out


def epfl_rows():
    cen = {r['name']: r for r in json.load(open(f'{HERE}/census/epfl-faculty.json'))}
    pu, sz = cen['Pearl Pu'], cen['Mathieu Salzmann']
    mem, ppu = 'https://www.epfl.ch/labs/gr-pu/members/', 'https://people.epfl.ch/pearl.pu?lang=en'
    edic20 = WAY + '20201125024227id_/https://www.epfl.ch/education/phd/edic-computer-and-communication-sciences/edic-computer-and-communication-sciences/edic-thesis-directors/'
    pu_lab = ev(mem, 'Members Head of the HCI Group Pearl Pu', 'lab_page')
    pu_phd = ev(ppu, span(ppu, 'Past EPFL PhD Students Li Chen (2008)', 'Jiyong Zhang (2008)'), 'faculty_profile')
    pu_edic = ev(edic20, window(edic20, 'Pearl Pu', 30), 'edic_thesis_directors')
    pu_basis = dict(kind='lab_head', url=mem, sha256=pu_lab['sha256'], quote=pu_lab['quote'],
                    thesis_director=dict(profile=pu_phd, edic_list=pu_edic,
                                         note='sole thesis director of Sintsova 2016, Yürüten 2017, Xie 2022, Svikhnushina 2023, Welivita 2023; co-director of Boia 2016, Kulev 2020'),
                    note='MER (Senior Scientist) heading her own group, the HCI Group (unit GR-PU), and an EDIC thesis director 2020-2024')
    pu_srcs = epfl_sources('Pearl Pu', 'Pearl Pu')
    pu_row = dict(name='Pearl Pu', aliases=['Pearl Pu Faltings'], collection_person_id=pu['collection_person_id'], structure_name=pu.get('structure_name'),
                  sciper=pu.get('sciper'), profile_url=pu['profile_url'], dblp=pu['dblp'], openalex=['https://openalex.org/A5048864545'], orcid=['0000-0001-8841-4416'],
                  identity_note=('OpenAlex A5048864545 carries the name on 47 EPFL works of the school sweep, 42 of them on the cached DBLP records of '
                                 'pid 76/2682 (claude-epfl-20261019/raw/dblp_pubs.json.gz); the ORCID is the one on that OpenAlex author record.'),
                  rank='mer_senior_scientist', title_as_listed='Senior Scientist', departments=['IC'], units=['GR-PU', 'HCI'],
                  years_listed=sorted({int(s['observed'][:4]) for s in pu_srcs if s['kind'] == 'dept_listing:IC'}),
                  sources=pu_srcs, is_pi=True, pi_basis=pu_basis,
                  lab_units=[dict(name='Human-Computer Interaction Group', acronym='GR-PU', url='https://www.epfl.ch/labs/gr-pu/', evidence=pu_lab)],
                  notes='IC Senior Scientist (MER) 2016-2026; off the live IC list and an "Invited guest" on her profile by 2026-10; no 2018 capture of the IC list exists (the reviewed period covers it)',
                  added=TAG)
    psz = 'https://people.epfl.ch/mathieu.salzmann?lang=en'
    edic23 = WAY + '20231218080116id_/https://www.epfl.ch/education/phd/edic-computer-and-communication-sciences/edic-computer-and-communication-sciences/edic-thesis-directors/'
    sz_phd = ev(psz, span(psz, 'Teaching & PhD PhD Students Pierre Victor Ancey', 'Past EPFL PhD Students Chen Zhao (2025)'), 'faculty_profile')
    sz_co = ev(psz, span(psz, 'Past EPFL PhD Students as codirector Jan Bednarík (2022)', 'Kaicheng Yu (2021)'), 'faculty_profile')
    sz_edic = ev(edic23, window(edic23, 'Mathieu Salzmann', 30), 'edic_thesis_directors')
    sz_basis = dict(kind='advises_phd', url=psz, sha256=sz_phd['sha256'], quote=sz_phd['quote'],
                    thesis_director=dict(edic_list=sz_edic, codirector=sz_co),
                    note=('Stated PhD thesis director: his profile lists ten current PhD students and Chen Zhao (2025) as directed, and '
                          'the EDIC thesis-director list names him from 2023-12. Co-leader of CVLab with Pascal Fua in the collection '
                          '(two leaders: a collective, as for Fua), so his own lab is a new "Mathieu Salzmann group".'))
    sz_srcs = epfl_sources('Mathieu Salzmann', 'Mathieu Salzmann')
    sz_row = dict(name='Mathieu Salzmann', aliases=[], collection_person_id=sz['collection_person_id'], structure_name=sz.get('structure_name'),
                  sciper=sz.get('sciper'), profile_url=sz['profile_url'], dblp=sz['dblp'], openalex=['https://openalex.org/A5049300388'], orcid=['0000-0002-8347-8637'],
                  identity_note=('OpenAlex A5049300388 carries the name on 234 EPFL works of the school sweep, 205 of them on the cached DBLP records of '
                                 'pid 18/4533 (claude-epfl-20261019/raw/dblp_pubs.json.gz); the ORCID is the one on that OpenAlex author record.'),
                  rank='adjunct', title_as_listed='Adjunct Professor', departments=['IC'], units=['CVLAB'],
                  years_listed=sorted({int(s['observed'][:4]) for s in sz_srcs if s['kind'] == 'dept_listing:IC'}),
                  sources=sz_srcs, is_pi=True, pi_basis=sz_basis, lab_units=['epfl_unit_cvlab'],
                  notes='IC Senior Scientist (MER) from 2023 (first IC listing 2023-12-05), Adjunct Professor by 2026-10; before 2023 a CVLab researcher, not IC faculty; Deputy Chief Data Scientist of SDSC since 2024-03',
                  added=TAG)
    return pu_row, sz_row


def epfl_periods(pu_row, sz_row):
    ppu = 'https://people.epfl.ch/pearl.pu?lang=en'
    ic26 = WAY + '20260418062144id_/https://www.epfl.ch/schools/ic/about/faculty-members/'
    ic16 = WAY + '20160108114526id_/http://ic.epfl.ch:80/professors'
    ic_live = 'https://www.epfl.ch/schools/ic/about/faculty-members/'
    pu = dict(id='override_period_epfl_pearl_pu', start='1999', end='2026', asof=None, datePrecision='year',
              evidence=[dict(ev(ppu, span(ppu, 'Past EPFL PhD Students Li Chen (2008)', 'Denis Lalanne (1999)'), 'faculty_start_lower_bound'),
                             note='lower bound: the first EPFL PhD she directed finished in 1999 (her group lists him as a PhD student at HCI 1994-1998)'),
                        ev(ic16, window(ic16, 'Pearl Pu', 40), 'dept_listing:IC', 'earliest IC listing capture in the window'),
                        ev(ic26, window(ic26, 'Pearl Pu', 30), 'dept_listing:IC', 'latest IC listing that names her'),
                        absent(ic_live, 'Pearl Pu', 'dept_listing:IC', 'the live IC faculty list (2026-10-22) no longer names her'),
                        ev(ppu, 'Invited guest , SCI IC PFP Group', 'faculty_profile', 'her profile status by 2026-10: end of the MER appointment in 2026')])
    ic22 = WAY + '20221210042229id_/https://www.epfl.ch/schools/ic/about/faculty-members/'
    ic23 = WAY + '20231205010540id_/https://www.epfl.ch/schools/ic/about/faculty-members/'
    ed22 = WAY + '20221205105214id_/https://www.epfl.ch/education/phd/edic-computer-and-communication-sciences/edic-computer-and-communication-sciences/edic-thesis-directors/'
    sz = dict(id='override_period_epfl_mathieu_salzmann', start='2023', end=None, asof=None, datePrecision='year',
              evidence=[absent(ic22, 'Salzmann', 'dept_listing:IC', 'not on the IC faculty list of 2022-12-10'),
                        absent(ed22, 'Salzmann', 'edic_thesis_directors', 'not on the EDIC thesis-director list of 2022-12-05'),
                        ev(ic23, window(ic23, 'Mathieu Salzmann', 25), 'dept_listing:IC', 'first IC listing (Senior Scientist), 2023-12-05'),
                        ev(ic_live, window(ic_live, 'Mathieu Salzmann', 25), 'dept_listing:IC', 'live IC list 2026-10-22: ongoing'),
                        ev('https://people.epfl.ch/mathieu.salzmann?lang=en', 'Mathieu Salzmann is the Deputy Chief Data Scientist of the Swiss Data Science Center (SDSC) and a Senior Scientist and Lecturer at EPFL.', 'faculty_profile')],
              note='start is the year of the first IC listing (between the 2022-12-10 and 2023-12-05 captures); before that he was a CVLab researcher, not IC faculty')
    return pu, sz


def review_epfl(pu_row, sz_row):
    ps = 'https://people.epfl.ch/mirjana.stojilovic?lang=en'
    return [dict(name='Pearl Pu', aliases=['Pearl Pu Faltings'], decision='qualifies', added_to='census/epfl-additions.json; period in hierarchy/census-overrides.json',
                 summary=('IC Senior Scientist (MER) listed 2016-2026 who heads her own lab ("Head of the HCI Group", unit GR-PU) and is a '
                          'stated thesis director (EDIC list 2020-2024; sole director of five PhDs 2016-2023). Appointment ended in 2026 '
                          '(off the live IC list, "Invited guest" on her profile); reviewed period 1999 (lower bound) to 2026.'),
                 evidence=[pu_row['lab_units'][0]['evidence'], pu_row['pi_basis']['thesis_director']['profile'], pu_row['pi_basis']['thesis_director']['edic_list']]),
            dict(name='Mathieu Salzmann', decision='qualifies', added_to='census/epfl-additions.json; period in hierarchy/census-overrides.json',
                 summary=('IC Senior Scientist (MER) from 2023, Adjunct Professor by 2026-10, and a stated PhD thesis director (EDIC list '
                          'from 2023-12; ten current PhD students and one directed PhD on his profile). Faculty only from 2023, so the '
                          'reviewed period starts 2023; his 2021-2022 co-directed theses predate the appointment.'),
                 evidence=[sz_row['pi_basis']['thesis_director']['edic_list'], {k: sz_row['pi_basis'][k] for k in ('url', 'sha256', 'quote')}]),
            dict(name='Mirjana Stojilovic', decision='does_not_qualify', reason='not_faculty_of_a_computing_department',
                 summary=('A Scientist and Lecturer in Babak Falsafi\'s PARSA lab, not an IC faculty member: no IC faculty list 2016-2026 '
                          'and no EDIC thesis-director list 2020-2026 names her, and her profile gives her position as "Scientist". '
                          'She co-directed three PhD theses with Falsafi (2023, 2024, 2026); co-direction by a scientist does not make a '
                          'faculty PI. She is not in census/epfl-faculty.json at all (the brief listed her as an MER with is_pi False).'),
                 thesis_harvest=dict(theses=3, years='2023-2026', roles='phd, co-director with Babak Falsafi', source=HARVEST),
                 evidence=[ev(ps, 'Mirjana Stojilovic Elle - She/her', 'faculty_profile'),
                           ev(ps, 'Scientist , Parallel Systems Architecture Laboratory EPFL IC IINFCOM PARSA', 'faculty_profile')]
                 + [absent(u, 'Stojilovi', 'dept_listing:IC') for u in EPFL_IC] + [absent(u, 'Stojilovi', 'edic_thesis_directors') for u in EPFL_EDIC])]


def write_json(path, obj):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.tmp-', suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False); f.write('\n')
    os.replace(tmp, path)


def main():
    tsit = tsitsiklis_row()
    pu_row, sz_row = epfl_rows()
    pu_per, sz_per = epfl_periods(pu_row, sz_row)
    cmu_alias = [ev('http://reports-archive.adm.cs.cmu.edu/anon/2024/abstracts/24-105.html', 'Thesis Committee: Fernando De la Torre (Chair)', 'cmu_tech_report'),
                 ev('http://reports-archive.adm.cs.cmu.edu/anon/2026/abstracts/26-122.html', 'Thesis Committee: Fernando De la Torre (Chair)', 'cmu_tech_report')]
    reviews = {'berkeley': review_berkeley(), 'princeton': review_princeton(), 'mit': review_mit(tsit), 'epfl': review_epfl(pu_row, sz_row),
               'cmu': [dict(name='Fernando De La Torre Frade', decision='alias_added', added_to='hierarchy/census-overrides.json (cmu aliases)',
                            summary=('Already a PI (RI, Human Sensing Lab), but bylines, DBLP and CMU theses write "Fernando De la Torre": the name '
                                     'rule needs a form ending in "torre", and "De La Torre Frade" yields only forms ending in "frade". '
                                     'DBLP pid d/FernandoDelaTorre is named "Fernando De la Torre" on 150 cached records 2016-2026 '
                                     '(claude-cmu-20261017/raw/dblp_pubs.json.gz).'),
                            evidence=cmu_alias)]}
    # additions
    p = f'{HERE}/census/mit-additions.json'
    rows = [r for r in json.load(open(p)) if r.get('added') != TAG and r['name'] != tsit['name']] + [tsit]
    write_json(p, rows)
    p = f'{HERE}/census/epfl-additions.json'
    old = json.load(open(p)) if os.path.exists(p) else []
    write_json(p, [r for r in old if r.get('added') != TAG and r['name'] not in (pu_row['name'], sz_row['name'])] + [pu_row, sz_row])
    # overrides (re-read just before writing; only our keys change)
    p = f'{HERE}/hierarchy/census-overrides.json'
    ov = json.load(open(p))
    e = ov['cmu'].setdefault('Fernando De La Torre Frade', {})
    e['aliases'] = list(dict.fromkeys(list(e.get('aliases') or []) + ['Fernando De la Torre']))
    e['why_aliases'] = ('bylines, DBLP (pid d/FernandoDelaTorre) and CMU thesis committees write "Fernando De la Torre"; without the alias '
                        'only 1 of his 38 verified works became a lab paper (missing-pi review 2026-10-22, hierarchy/cmu/missing-pi-review.json)')
    for name, per in (('Pearl Pu', pu_per), ('Mathieu Salzmann', sz_per)):
        e = ov['epfl'].setdefault(name, {})
        e['periods'] = [q for q in e.get('periods') or [] if q.get('id') != per['id']] + [per]
        e['why_periods'] = 'reviewed faculty period (missing-pi review 2026-10-22, hierarchy/epfl/missing-pi-review.json)'
    write_json(p, ov)
    for school, items in reviews.items():
        write_json(f'{HERE}/hierarchy/{school}/missing-pi-review.json',
                   dict(reviewed=TODAY, rule=__doc__.split('Rule: ')[1].split('\n\nEvidence:')[0].replace('\n', ' '),
                        captures=CAPS + ' (fetched or copied pages; quotes are exact substrings of the stored text, whitespace collapsed)',
                        tools='hierarchy/missing-pi-tools/{mpcap.py,build_review.py}', decisions=items))
    print(json.dumps({s: [(x['name'], x['decision']) for x in v] for s, v in reviews.items()}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
