"""An onboarding school's reviewed census overrides live in its own file; the shared tracked file is never written for it."""
import json

import atlas_paths as P
import census_overrides as CO

def by_path(name):
    """tools/<name>.py by path: an earlier test may have left another checkout's copy of the module in sys.modules."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('by_path_' + name, Path(__file__).resolve().parents[1] / 'tools' / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def setup(tmp_path, monkeypatch, status):
    monkeypatch.setattr(P, 'data', lambda name, school=None, root=None, **k: tmp_path / ((school or '_') + '-' + name))
    monkeypatch.setattr(P, 'data_w', lambda name, school=None, **k: P.data(name, school))
    monkeypatch.setattr(CO.S, 'get', lambda k: {'status': status})
    shared = tmp_path / '_-census-overrides.json'
    shared.write_text(json.dumps({'u': {'Ann': {'why': 'shared'}}, 'mit': {'Bo': {}}}, indent=1))
    return shared


def test_onboarding_writes_its_own_file_and_reads_both(tmp_path, monkeypatch):
    shared = setup(tmp_path, monkeypatch, 'onboarding')
    before = shared.read_text()
    sec, save = CO.open_section('u')
    sec['Cy'] = {'periods': [1]}
    save()
    assert shared.read_text() == before                      # the tracked shared file is untouched
    assert json.loads((tmp_path / 'u-census-overrides-school.json').read_text()) == {'Cy': {'periods': [1]}}
    assert CO.section('u') == {'Ann': {'why': 'shared'}, 'Cy': {'periods': [1]}}
    (tmp_path / 'u-census-overrides-school.json').write_text(json.dumps({'Ann': {'periods': [2]}}))
    assert CO.section('u')['Ann'] == {'why': 'shared', 'periods': [2]}


def test_a_released_school_still_edits_the_shared_file(tmp_path, monkeypatch):
    shared = setup(tmp_path, monkeypatch, 'released')
    sec, save = CO.open_section('mit')
    sec['Di'] = {}
    save()
    ov = json.loads(shared.read_text())
    assert set(ov['mit']) == {'Bo', 'Di'} and 'u' in ov and not (tmp_path / 'mit-census-overrides-school.json').exists()


def test_oa_identity_review_file_is_optional(tmp_path, monkeypatch):
    O = by_path('oa_identity_school')
    monkeypatch.setattr(O.P, 'data', lambda name, school=None, **k: tmp_path / name)
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': []}))
    (tmp_path / 'cs-related-review.json').write_text(json.dumps({'decisions': []}))
    assert O.wanted('u') == {}


def test_adviser_directory_reads_student_and_adviser_from_the_page(monkeypatch):
    L = by_path('labpage_students_school')
    html = ('<p><strong>Ann Lee</strong><br /><strong>B.S.:</strong> X<br /><strong>Advisor:</strong> Yury Makarychev, Nati Srebro<br />'
            '<a href="mailto:a@b.c">Email</a></p><p><strong>No Adviser</strong><br /><strong>B.S.:</strong> Y<br /></p>')
    flat = 'Ann Lee B.S.: X Advisor: Yury Makarychev, Nati Srebro Email No Adviser B.S.: Y'
    monkeypatch.setattr(L.S, 'field', lambda cfg, f, d=None: ['ttic.test/students/'])
    monkeypatch.setattr(L.S, 'get', lambda k: {})
    monkeypatch.setattr(L.W, 'con', lambda k: None)
    monkeypatch.setattr(L.W, 'cdx_rows', lambda c, d, collapse=None: [dict(timestamp='20240101000000', original=d)])
    monkeypatch.setattr(L.W, 'capture', lambda c, ts, o, d, dept: ('cap-' + ts, 200, 'sha', []))
    monkeypatch.setattr(L.W, 'raw_html', lambda c, cap: html)
    monkeypatch.setattr(L.W, 'flat', lambda b: flat)
    rows = L.adviser_directory('u', [('Yury Makarychev', 'Yury Makarychev'), ('Nati Srebro', 'Nati Srebro'), ('Other PI', 'Other PI')])
    assert [(r['student'], r['pi']) for r in rows] == [('Ann Lee', 'Nati Srebro'), ('Ann Lee', 'Yury Makarychev')]
    assert rows[0]['quote'].startswith('Ann Lee') and rows[0]['quote'].endswith('Nati Srebro') and rows[0]['years'] == [2024, 2024]


def test_adviser_directory_second_markup(monkeypatch):
    L = by_path('labpage_students_school')
    html = '<h3 class="media-heading">Ann Lee</h3>\n<p><strong>B.S.:</strong> X<br />\n<strong>Advisor:</strong> Nati Srebro<br />\n<a href="mailto:a@b.c">Email</a></p>'
    flat = 'Ann Lee B.S.: X Advisor: Nati Srebro Email'
    for k, v in (('field', lambda cfg, f, d=None: ['t/']), ('get', lambda k: {})):
        monkeypatch.setattr(L.S, k, v)
    monkeypatch.setattr(L.W, 'con', lambda k: None)
    monkeypatch.setattr(L.W, 'cdx_rows', lambda c, d, collapse=None: [dict(timestamp='20220101000000', original=d)])
    monkeypatch.setattr(L.W, 'capture', lambda c, ts, o, d, dept: ('cap', 200, 'sha', []))
    monkeypatch.setattr(L.W, 'raw_html', lambda c, cap: html)
    monkeypatch.setattr(L.W, 'flat', lambda b: flat)
    assert [(r['student'], r['pi']) for r in L.adviser_directory('u', [('Nati Srebro', 'Nati Srebro')])] == [('Ann Lee', 'Nati Srebro')]


def test_roster_alone_or_coauthorship_alone_is_not_evidence(tmp_path, monkeypatch):
    import gzip
    L = by_path('labpage_students_school')
    lp = tmp_path / 'lab_papers.jsonl.gz'
    with gzip.open(lp, 'wt') as f:
        f.write(json.dumps({'pi': 'Pia Lee', 'year': '2021', 'title': 'A paper', 'byline': ['Sam Roe', 'Pia Lee']}) + '\n')
        f.write(json.dumps({'pi': 'Pia Lee', 'year': '2021', 'title': 'B paper', 'byline': ['Pia Lee', 'Tom Poe']}) + '\n')
    monkeypatch.setattr(L.P, 'data', lambda name, school=None, **k: lp)
    monkeypatch.setattr(L.S, 'field', lambda cfg, f, d=None: [{'url': 'r/alumni/', 'kind': 'alumni_by_year'}])
    monkeypatch.setattr(L.S, 'get', lambda k: {})
    monkeypatch.setattr(L.W, 'con', lambda k: None)
    monkeypatch.setattr(L.W, 'cdx_rows', lambda c, d, collapse=None: [dict(timestamp='20260101000000', original=d)])
    monkeypatch.setattr(L.W, 'capture', lambda c, ts, o, d, dept: ('cap', 200, 'sha', []))
    monkeypatch.setattr(L.W, 'flat', lambda b: '2022 Sam Roe, Googler 2021 Ann Only, Meta 2020 Zed Zero 2010 Old Timer')   # Tom Poe: co-author, not on the roster; Ann Only: roster, no paper
    rows = L.roster_coauthor_students('u', [('Pia Lee', 'Pia Lee')])
    assert [(r['student'], r['pi'], r['years']) for r in rows] == [('Sam Roe', 'Pia Lee', [None, 2022])] and rows[0]['quote'].startswith('Sam Roe')


def test_alumni_blocks_name_the_student_from_their_own_heading(monkeypatch):
    L = by_path('labpage_students_school')
    html = ('<h3 class="media-heading">Lingyu Gao</h3><p>PhD - 2024<br />\nAdvisor - Kevin Gimpel<br />\nResearch Interests: NLP<br />\n'
            'Employment at time of graduation: Microsoft<br />\nThesis: <a href="x">T (August 2024)</a></p>'
            '<p><strong>Old Person</strong><br />PhD - 2010<br />Advisor - Kevin Gimpel</p>')
    flat = 'Lingyu Gao PhD - 2024 Advisor - Kevin Gimpel Research Interests: NLP Employment at time of graduation: Microsoft Thesis: T Old Person PhD - 2010 Advisor - Kevin Gimpel'
    monkeypatch.setattr(L.S, 'field', lambda cfg, f, d=None: ['t/alumni/'])
    monkeypatch.setattr(L.S, 'get', lambda k: {})
    monkeypatch.setattr(L.W, 'con', lambda k: None)
    monkeypatch.setattr(L.W, 'cdx_rows', lambda c, d, collapse=None: [dict(timestamp='20260101000000', original=d)])
    monkeypatch.setattr(L.W, 'capture', lambda c, ts, o, d, dept: ('cap', 200, 'sha', []))
    monkeypatch.setattr(L.W, 'raw_html', lambda c, cap: html)
    monkeypatch.setattr(L.W, 'flat', lambda b: flat)
    rows = L.adviser_alumni('u', [('Kevin Gimpel', 'Kevin Gimpel')])
    assert [(r['student'], r['years']) for r in rows] == [('Lingyu Gao', [None, 2024])] and rows[0]['quote'].startswith('Lingyu Gao PhD - 2024')


def test_student_audit_writes_an_onboarding_school_to_its_own_file(tmp_path, monkeypatch):
    SA = by_path('student_audit')
    written = {}
    monkeypatch.setattr(SA, 'audit', lambda s: {'school': s, 'counts': {'n': 1}})
    monkeypatch.setattr(SA.P, 'data_w', lambda name, school=None, **k: tmp_path / f'{school}-{name}')
    monkeypatch.setattr(SA.P, 'hfile_w', lambda H, name, school=None: tmp_path / name)
    monkeypatch.setattr('census_overrides.onboarding', lambda k: k == 'newu')
    SA.main(['newu', 'old'])
    assert json.loads((tmp_path / 'newu-student-audit-school.json').read_text())['school'] == 'newu'
    assert [r['school'] for r in json.loads((tmp_path / 'student-audit.json').read_text())] == ['old'] and not written


def test_roster_drops_pre_window_graduates_and_late_namesake_papers(tmp_path, monkeypatch):
    import gzip
    L = by_path('labpage_students_school')
    lp = tmp_path / 'lab_papers.jsonl.gz'
    with gzip.open(lp, 'wt') as f:
        for who, yr in (('Old Timer', '2016'), ('Sam Roe', '2024'), ('Ann Only', '2021')):
            f.write(json.dumps({'pi': 'Pia Lee', 'year': yr, 'title': 'T ' + who, 'byline': [who, 'Pia Lee']}) + '\n')
    monkeypatch.setattr(L.P, 'data', lambda name, school=None, **k: lp)
    monkeypatch.setattr(L.S, 'field', lambda cfg, f, d=None: [{'url': 'r/alumni/', 'kind': 'alumni_by_year'}])
    monkeypatch.setattr(L.S, 'get', lambda k: {})
    monkeypatch.setattr(L.W, 'con', lambda k: None)
    monkeypatch.setattr(L.W, 'cdx_rows', lambda c, d, collapse=None: [dict(timestamp='20260101000000', original=d)])
    monkeypatch.setattr(L.W, 'capture', lambda c, ts, o, d, dept: ('cap', 200, 'sha', []))
    monkeypatch.setattr(L.W, 'flat', lambda b: '2022 Sam Roe, Googler 2021 Ann Only, Meta 2010 Old Timer')
    rows = L.roster_coauthor_students('u', [('Pia Lee', 'Pia Lee')])
    # Old Timer graduated 2010 (before 2016): dropped; Sam Roe graduated 2022 but the paper is 2024: dropped; Ann Only 2021 with a 2021 paper: kept
    assert [(r['student'], r['years']) for r in rows] == [('Ann Only', [None, 2021])]


def test_a_single_paper_where_the_pi_is_not_last_is_not_advising(tmp_path, monkeypatch):
    import gzip
    L = by_path('labpage_students_school')
    lp = tmp_path / 'lab_papers.jsonl.gz'
    with gzip.open(lp, 'wt') as f:
        f.write(json.dumps({'pi': 'Pia Lee', 'year': '2021', 'title': 'A', 'byline': ['Pia Lee', 'Sam Roe', 'Zed Last']}) + '\n')
        f.write(json.dumps({'pi': 'Pia Lee', 'year': '2021', 'title': 'B', 'byline': ['Ann Only', 'Pia Lee']}) + '\n')
    monkeypatch.setattr(L.P, 'data', lambda name, school=None, **k: lp)
    monkeypatch.setattr(L.S, 'field', lambda cfg, f, d=None: [{'url': 'r/', 'kind': 'students'}])
    monkeypatch.setattr(L.S, 'get', lambda k: {})
    monkeypatch.setattr(L.W, 'con', lambda k: None)
    monkeypatch.setattr(L.W, 'cdx_rows', lambda c, d, collapse=None: [dict(timestamp='20210101000000', original=d)])
    monkeypatch.setattr(L.W, 'capture', lambda c, ts, o, d, dept: ('cap', 200, 'sha', []))
    monkeypatch.setattr(L.W, 'flat', lambda b: 'Sam Roe PhD Student Ann Only PhD Student')
    rows = L.roster_coauthor_students('u', [('Pia Lee', 'Pia Lee')])
    assert [r['student'] for r in rows] == ['Ann Only']


def test_gate_related_takes_the_school_out_of_an_argonne_only_authorship():
    """D3: Argonne (a lineage child) ties an authorship to the school only with a matching raw string, or for a PI with a cited joint appointment."""
    import re
    from pihier import common as C
    gate = ({'I7'}, re.compile(r'University of Chicago', re.I), 'https://openalex.org/I1')
    arg = lambda: {'id': 'https://openalex.org/I7', 'lineage': ['https://openalex.org/I7', 'https://openalex.org/I1']}
    uc = lambda: {'id': 'https://openalex.org/I1', 'lineage': ['https://openalex.org/I1']}

    def w(insts, raws, name='Ian Foster'):
        return {'authorships': [{'raw_author_name': name, 'institutions': insts, 'raw_affiliation_strings': raws}]}
    only = C.gate_related(w([arg()], ['Argonne National Laboratory']), gate)
    assert 'https://openalex.org/I1' not in only['authorships'][0]['institutions'][0]['lineage']
    named = C.gate_related(w([arg()], ['Argonne National Laboratory; University of Chicago']), gate)
    assert 'https://openalex.org/I1' in named['authorships'][0]['institutions'][0]['lineage']
    joint = C.gate_related(w([arg()], ['Argonne National Laboratory']), gate, {'ian foster': {'I7'}})
    assert 'https://openalex.org/I1' in joint['authorships'][0]['institutions'][0]['lineage']
    both = C.gate_related(w([uc(), arg()], ['x']), gate)
    assert both['authorships'][0]['institutions'][0]['lineage'] == ['https://openalex.org/I1']


def test_pi_works_can_come_from_the_snapshot_without_the_api(tmp_path, monkeypatch):
    import sqlite3
    M = by_path('pi_fulltext_affiliation')
    monkeypatch.setattr(M.P, 'data', lambda name, school=None, **k: tmp_path / name)
    (tmp_path / 'pis.json').write_text(json.dumps([{'pi': 'A', 'oaAuthorIds': ['https://openalex.org/A1', 'https://openalex.org/A2'], 'reviewedOpenAlex': []}]))
    import oa_snapshot as O
    monkeypatch.setattr(O, 'works_by_author', lambda a: iter([{'id': 'W1', 'publication_year': 2020}, {'id': 'W0', 'publication_year': 2010}] if a == 'A1' else []))
    missing = M.works_from_snapshot('u')
    assert missing == ['A2'] and sqlite3.connect(str(M.db('u').execute('pragma database_list').fetchall()[0][2])).execute('select id from works').fetchall() == [('W1',)]


def test_label_prefixes_and_hiring_sections_are_not_part_of_a_student():
    L = by_path('labpage_students_school')
    assert L.clean_student_name('Research Fellowship Lingyu Gao') == 'Lingyu Gao'
    assert L.clean_student_name('Microsoft Taehwan Kim') == 'Taehwan Kim'
    assert L.clean_student_name('Structured Prediction Shubhendu Trivedi') == 'Shubhendu Trivedi'
    assert L.clean_student_name('Ann Lee') == 'Ann Lee' and L.clean_student_name('Google') == 'Google'
    assert L.NOT_STUDENT_HEAD.match('Hiring') and L.NOT_STUDENT_HEAD.match('Open positions') and not L.NOT_STUDENT_HEAD.match('PhD students')


def test_all_faculty_names_reads_every_schools_pis(tmp_path, monkeypatch):
    L = by_path('labpage_students_school')
    monkeypatch.setattr(L.S, 'keys', lambda: ['a', 'b'])
    monkeypatch.setattr(L.P, 'data', lambda name, school=None, **k: tmp_path / f'{school}-pis.json')
    (tmp_path / 'a-pis.json').write_text(json.dumps([{'pi': 'Samir Khuller', 'names': ['S. Khuller']}]))
    assert 'samir khuller' in L.all_faculty_names()


def test_a_department_people_page_is_not_a_lab_page():
    L = by_path('labpage_students_school')
    fac = {'ann lee', 'bo wu', 'cy roe', 'di fox', 'ed gray', 'flo hart', 'gus ito'}
    page = 'People Ann Lee Professor Bo Wu Professor Cy Roe Di Fox Ed Gray Flo Hart Graduate students Sam Poe'
    assert L.is_department_roster(page, fac, 6)
    assert not L.is_department_roster('Ann Lee group: students Sam Poe, Tia Kim; collaborator Bo Wu', fac, 6)


def test_student_decisions_exclude_not_and_unclear_only():
    import student_decisions as SD
    dec = {'Pia': {'Ann Lee': {'decision': 'not'}, 'Bo Roe': {'decision': 'unclear'}, 'Cy Poe': {'decision': 'uchicago'}}}
    assert SD.excluded(dec, 'Pia', 'ann  LEE') and SD.excluded(dec, 'Pia', 'Bo Roe')
    assert not SD.excluded(dec, 'Pia', 'Cy Poe') and not SD.excluded(dec, 'Pia', 'Dee') and not SD.excluded(dec, 'Other', 'Ann Lee')


def test_defense_lists_name_the_chair_and_respect_the_appointment_window(monkeypatch):
    L = by_path('labpage_students_school')
    html = ('<table><tr><td>Defense: "T"</td><td>Ann Lee (Finance)</td><td>Monday, June 5, 2023</td><td>Pia Roe (Chair), Bo Wu, and Cy Fox</td></tr>'
            '<tr><td>Proposal: "U"</td><td>Dee Kim (Statistics)</td><td>Friday, May 6, 2016</td><td>Pia Roe (Chair), Bo Wu</td></tr></table>')
    flat = 'Defense: "T" Ann Lee (Finance) Monday, June 5, 2023 Pia Roe (Chair), Bo Wu, and Cy Fox Proposal: "U" Dee Kim (Statistics) Friday, May 6, 2016 Pia Roe (Chair), Bo Wu'
    monkeypatch.setattr(L.S, 'field', lambda cfg, f, d=None: ['x/defenses'])
    monkeypatch.setattr(L.S, 'get', lambda k: {})
    monkeypatch.setattr(L.W, 'con', lambda k: None)
    monkeypatch.setattr(L.W, 'cdx_rows', lambda c, d, collapse=None: [dict(timestamp='20260101000000', original=d)])
    monkeypatch.setattr(L.W, 'capture', lambda c, ts, o, d, dept: ('cap', 200, 'sha', []))
    monkeypatch.setattr(L.W, 'raw_html', lambda c, cap: html)
    monkeypatch.setattr(L.W, 'flat', lambda b: flat)
    rows = L.defense_lists('u', [('Pia Roe', 'Pia Roe')], {'Pia Roe': 2020})
    assert [(r['student'], r['years']) for r in rows] == [('Ann Lee', [None, 2023])]      # the 2016 proposal precedes her first listing in 2020
    assert rows[0]['quote'].startswith('Ann Lee') and rows[0]['quote'].endswith('Pia Roe (Chair') or 'Pia Roe' in rows[0]['quote']


def test_cv_students_reads_an_advising_section_with_years_and_the_window():
    CVS = by_path('cv_students')
    text = ("EDUCATION\nPhD MIT 2001\n\nPh.D. STUDENTS ADVISED\nAnn Lee (2019); Wei Zhang (2012); Maria Garcia (2022), John Smith (2024)\n\nTEACHING\nCS 101\n"
            "Current students\nEddie Gray, Flora Hart\n")
    got = {n: y for n, y, h, q in CVS.parse(text, 2016)}
    assert got['Ann Lee'] == [None, 2019] and 'Wei Zhang' not in got and got['Maria Garcia'] == [None, 2022] and got['John Smith'] == [None, 2024]
    assert got['Eddie Gray'] == [None, None]   # a 'current' heading needs no year


def test_people_links_stay_in_the_pis_own_space():
    L = by_path('labpage_students_school')
    dh = {'cs.uchicago.edu', 'ttic.edu'}
    assert not L.in_own_space('https://cs.uchicago.edu/academics/phd/graduate-student-leadership/', 'Ann Lee', dh)
    assert L.in_own_space('http://people.cs.uchicago.edu/~alee/students.html', 'Ann Lee', dh)
    assert L.in_own_space('https://cs.uchicago.edu/people/ann-lee-students/', 'Ann Lee', dh)
    assert L.in_own_space('https://leelab.github.io/people', 'Ann Lee', dh)


def test_defense_student_name_keeps_the_nickname_and_drops_the_area():
    L = by_path('labpage_students_school')
    assert L.AREA_PREFIX.sub('', 'Operations Management Ebru Kasikaralar') == 'Ebru Kasikaralar'
    assert L.AREA_PREFIX.sub('', 'Econometrics & Statistics Ming Gao') == 'Ming Gao'
