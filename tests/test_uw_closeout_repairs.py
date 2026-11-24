"""Source failures found by UW's independent closeout review."""
import hashlib
import json

import pytest

import atlas_paths as P
import labpage_audit as L
import listing_formats as F
from listing_rows import quote_of
from pihier.periods import not_faculty_row
import stage_gate as G


def test_incoming_directory_office_is_not_a_faculty_appointment():
    html = """<h2>Faculty</h2><div class='directory-name'><a href='/althoff'>Tim Althoff</a></div>
    <div class='directory-office'>Arriving January 2019</div>
    <div class='directory-name'><a href='/anderson'>Richard Anderson</a></div>
    <div class='directory-office'>CSE 582</div>"""
    a, b = F.uw_allen_directory(html)
    assert a['titles'] == ['Faculty', 'Arriving January 2019']
    assert b['titles'] == ['Faculty']
    quote = quote_of('Faculty Tim Althoff Arriving January 2019 Richard Anderson CSE 582', a)
    assert 'Arriving January 2019' in quote and not_faculty_row(quote)
    assert not not_faculty_row('Richard Anderson')


@pytest.mark.parametrize(('indexed', 'listed', 'primary'), [
    ('NormAd: A Framework for Measuring Cultural Adaptability',
     'NormAd: A Benchmark for Measuring Cultural Adaptability',
     'N ORM A D: A Benchmark for Measuring Cultural Adaptability'),
    ('CQA-Eval: Designing Reliable Evaluations of Multi-paragraph Clinical QA',
     'LONGQAEVAL: Designing Reliable Evaluations of Long-Form Clinical QA',
     'L ONG QAE VAL: Designing Reliable Evaluations of Long-Form Clinical QA'),
])
def test_original_pdf_title_wins_over_conflicting_index(monkeypatch, indexed, listed, primary):
    monkeypatch.setattr(L, 'arxiv_titles', lambda ids: {'1': indexed})
    row = dict(arxiv='1', title=indexed, listed_title=listed, title_basis='arxiv_oai',
               evidence=dict(pdf_sha256='a' * 64))
    L.fix_titles_from_arxiv([row], pages={'a' * 64: primary + '\n\nAuthors\n\nAbstract'})
    assert row['title'] == listed and row['title_basis'] == 'page1_verified_title'
    assert row['previous_metadata_title'] == indexed


def test_substantive_title_is_not_overwritten_without_version_evidence(monkeypatch):
    monkeypatch.setattr(L, 'arxiv_titles', lambda ids: {'1': 'A different version title'})
    row = dict(arxiv='1', title='An owned substantive citation title', evidence={})
    L.fix_titles_from_arxiv([row], pages={})
    assert row['title'] == 'An owned substantive citation title'


def test_author_only_title_can_use_index_fallback(monkeypatch):
    monkeypatch.setattr(L, 'arxiv_titles', lambda ids: {'1': 'The complete paper title'})
    row = dict(arxiv='1', title='Smith, Jane', title_basis='author_only', evidence={})
    L.fix_titles_from_arxiv([row], pages={})
    assert row['title'] == 'The complete paper title'


def test_source_version_review_replays_only_against_exact_retained_pdf():
    sha = 'b' * 64
    row = dict(pi='PI', key='paper:1', title='Latest version title',
               evidence=dict(url='https://example.edu/paper-v1.pdf', pdf_sha256=sha))
    review = dict(pi='PI', key='paper:1', primary_title='The original version title',
                  decision='correct_to_exact_represented_source_title', reviewed_by='independent', reviewed_on='2026-11-24',
                  evidence=dict(url=row['evidence']['url'], pdf_sha256=sha, quote='The original version title'))
    L.apply_paper_metadata_reviews([row], [review], {sha: 'The original version title\n\nAn Author'})
    assert row['title'] == review['primary_title']
    assert row['evidence']['title_metadata_review'] == review
    with pytest.raises(ValueError, match='Unverifiable'):
        L.apply_paper_metadata_reviews([row], [review], {sha: 'A different paper title'})


@pytest.fixture
def accuracy_tree(tmp_path, monkeypatch):
    folder = tmp_path / 'u'
    folder.mkdir()
    acc = tmp_path / 'accuracy'
    acc.mkdir()
    monkeypatch.setattr(P, 'data', lambda name, school=None, **kw: folder / name)
    monkeypatch.setattr(G, 'ACCURACY_DIR', acc)
    for name in G.ACCURACY_FILES:
        (folder / name).write_text('[]')
    return folder, acc


def _summary(folder, names):
    hashes = {n: hashlib.sha256((folder / n).read_bytes()).hexdigest() for n in names}
    return dict(files=hashes, files_now=dict(hashes), lab_precision_uniform={'p': 1.0},
                student_precision_uniform={'p': 1.0}, lab_coverage={'p': 1.0})


def test_copy_refresh_does_not_invalidate_opted_out_attribution_but_rows_do(accuracy_tree, monkeypatch):
    folder, acc = accuracy_tree
    monkeypatch.setattr(G.S, 'get', lambda key: {'accuracy': {'bind_copies': False}})
    names = G.accuracy_files('u')
    assert len(names) == 4 and 'copies.json' not in names
    (acc / 'summary-u.json').write_text(json.dumps(_summary(folder, names)))
    (folder / 'copies.json').write_text('{"summary":{"local":1}}')
    assert G.g9('u')[0] == []
    (folder / 'students.json').write_text('{"changed":[]}')
    assert any('students.json differ' in item for item in G.g9('u')[0])


def test_other_schools_keep_five_file_binding(accuracy_tree, monkeypatch):
    folder, acc = accuracy_tree
    monkeypatch.setattr(G.S, 'get', lambda key: {})
    assert G.accuracy_files('u') == G.ACCURACY_FILES
    (acc / 'summary-u.json').write_text(json.dumps(_summary(folder, G.ACCURACY_FILES)))
    (folder / 'copies.json').write_text('{"summary":{"local":1}}')
    assert any('copies.json differ' in item for item in G.g9('u')[0])


def test_binding_option_is_not_truthy_string(monkeypatch):
    monkeypatch.setattr(G.S, 'get', lambda key: {'accuracy': {'bind_copies': 'false'}})
    with pytest.raises(ValueError, match='boolean'):
        G.accuracy_files('u')
def test_outgoing_directory_uses_specific_role_section_not_combined_title():
    from labpage_students_school import outgoing_directory_role
    text = ('Outgoing Ph.D.s & Postdocs Outgoing Postdocs Rohan Kadekodi Advisor(s): Baris Kasikci '
            'Outgoing Ph.D.s Alice Roe Advisor(s): Jane Doe')
    assert outgoing_directory_role(text, 'Rohan Kadekodi') == 'postdoc'
    assert outgoing_directory_role(text, 'Alice Roe') == 'phd'
    assert outgoing_directory_role('Outgoing Ph.D.s & Postdocs Pat Smith Advisor: Jane Doe', 'Pat Smith') is None
    assert outgoing_directory_role('PhD Students Pat Smith Advisor: Jane Doe', 'Pat Smith') is None


def test_researched_ingestion_honors_review_holds_and_rejects_possessive_labels(monkeypatch, tmp_path):
    import collections
    import json
    from types import SimpleNamespace
    from pihier import students as ST

    monkeypatch.setattr(ST.P, 'data', lambda name, *a, **kw: tmp_path / name)
    monkeypatch.setattr(ST, 'renamed_pis', lambda *a: {})
    monkeypatch.setattr(ST, 'accepted_additions', lambda *a: [])
    rows = [dict(name=n, role='phd', years=[2026], url='https://example.edu/team',
                 sha256='a' * 64, quote=n + ', PhD student')
            for n in ['Pat Rejected', 'Pat Held', "Jane Doe's", "Alex O'Connor"]]
    rows += [dict(name=n, role='phd', years=y, alumni=True, url='https://example.edu/alumni',
                  sha256='b' * 64, quote=n + ', PhD alumnus')
             for n, y in [('Undated Alumnus', None), ('Old Alumnus', [2013]), ('Window Alumnus', [2019])]]
    rows[-1]['additional_sources'] = [dict(url='https://example.edu/degree', sha256='c' * 64,
                                         quote='Window Alumnus, PhD2019, University of Example')]
    (tmp_path / 'few-students-evidence.json').write_text(json.dumps([dict(pi='Jane Doe', students=rows)]))
    (tmp_path / 'student-decisions.json').write_text(json.dumps({'Jane Doe': {
        'Pat Rejected': dict(decision='not', why='Workshop speaker only'),
        'Pat Held': dict(decision='unclear', why='Shared roster with no adviser')}}))
    ctx = SimpleNamespace(here=tmp_path, school='fixture', pis=[dict(pi='Jane Doe')], ge={}, n=collections.Counter())
    stu = collections.defaultdict(dict)
    ST.researched(ctx, stu, {})
    assert [r['name'] for r in stu['Jane Doe'].values()] == ["Alex O'Connor", 'Window Alumnus']
    assert ctx.n['researched_students_review_excluded'] == 2
    assert ctx.n['researched_students_possessive_label_dropped'] == 1
    assert ctx.n['researched_students_without_window_year_held'] == 2
    alumnus = next(r for r in stu['Jane Doe'].values() if r['name'] == 'Window Alumnus')
    assert alumnus['relations'][0]['sources'][-1] == rows[-1]['additional_sources'][0]
    with pytest.raises(ValueError, match='additional source needs'):
        ST.reviewed_additional_sources({'additional_sources': [dict(url='https://example.edu/degree', quote='unhashed')]})


def test_resolved_lab_scoped_member_can_link_without_borrowing_collection_identity(monkeypatch, tmp_path):
    import collections
    import json
    from types import SimpleNamespace
    from pihier import students as ST, links

    monkeypatch.setattr(ST.P, 'data', lambda name, *a, **kw: tmp_path / name)
    monkeypatch.setattr(ST, 'renamed_pis', lambda *a: {})
    monkeypatch.setattr(ST, 'accepted_additions', lambda *a: [])
    row = dict(name='Jane Researcher', role='phd', years=[2026], lab_scoped_identity=True,
               url='https://example.edu/team', sha256='a' * 64, quote='PhD Students: Jane Researcher',
               reviewed_aliases=['Janey Researcher'], alias_evidence=[dict(url='https://example.edu/jane', sha256='b' * 64,
                   quote='Jane Researcher is also known as Janey Researcher.')])
    (tmp_path / 'few-students-evidence.json').write_text(json.dumps([dict(pi='Example PI', students=[row])]))
    ctx = SimpleNamespace(here=tmp_path, school='fixture', pis=[dict(pi='Example PI')], ge={}, n=collections.Counter())
    native = collections.defaultdict(dict)
    ST.researched(ctx, native, {'researcher': [dict(id='unproved-global-person', name='Jane Researcher')]})
    member, = native['Example PI'].values()
    assert member['person'] != 'unproved-global-person' and member['identityScope'] == 'lab'
    assert 'sourceRecordKey' not in member
    assert member['aliases'] == ['Janey Researcher']
    assert ST.external_member_id('fixture', 'Other PI', 'Jane Researcher', lab_scoped=True) != member['person']
    ctx.stu, ctx.pls = native, collections.defaultdict(list)
    ctx.rows = [dict(pi='Example PI', work='work-1', oa='W1', year=2026,
                     byline=['Example PI', 'Janey Researcher'],
                     _bylines=[(['Example PI', 'Janey Researcher'], ['Janey Researcher'])])]
    links.link_students(ctx)
    assert len(ctx.sp) == 1 and ctx.sp[0]['student'] == member['person']


def test_protected_profile_diagnosis_explains_only_the_live_identity_guard():
    import link_diagnosis as LD
    import chain_audit as CA
    member = dict(name='Ziyu Chen', sourceRecordKey='unresolved-doctoral-profile')
    hold = LD.source_profile_authorship_hold(member, [dict(work='W1')])
    diagnosis = dict(category='source_identity_unresolved', authorship_hold=hold)
    assert CA.valid_source_profile_hold(member, diagnosis)
    assert not CA.valid_source_profile_hold(dict(name='Ziyu Chen'), diagnosis)
    assert not CA.valid_source_profile_hold(dict(member, sourceRecordKey='other-profile'), diagnosis)
    assert LD.source_profile_authorship_hold(member, []) is None
    assert LD.source_profile_authorship_hold(dict(name='Ziyu Chen', identityScope='lab'), [dict(work='W1')]) is None


def test_recent_phd_alumnus_is_a_student_but_not_a_current_doctoral_student():
    from pihier import students as ST, links
    import student_recall as R
    row = dict(roles=['phd_alumnus'], relations=[dict(role='phd_alumnus', years=[2026])])
    assert links.student_role_ok(row)
    assert not R.is_current_phd(row)
    assert ST.reviewed_relationship_type({}, 'phd_alumnus') == 'researched_advising'
    assert ST.reviewed_relationship_type({'relationship': 'membership'}, 'phd_alumnus') == 'researched_membership'


def test_link_diagnosis_dates_local_dblp_deposit_before_checking_appointment(tmp_path, monkeypatch):
    import gzip
    import chain_audit as A
    import link_diagnosis as D
    from pihier import identity
    school = tmp_path / 'princeton'
    school.mkdir()
    pi, name = 'Ada Lovelace', 'Jane Doe'
    (school / 'pis.json').write_text(json.dumps([dict(pi=pi, dblp=['p/1'], reviewedOpenAlex=['A1'],
                                                     periods=[], listings=[dict(year=2019)])]))
    (school / 'students.json').write_text(json.dumps({pi: [dict(person='s1', name=name, roles=['phd'])]}))
    for filename in ['lab_papers.jsonl.gz', 'student_papers.jsonl.gz']:
        with gzip.open(school / filename, 'wt'):
            pass
    with gzip.open(school / 'dblp-dump-persons-school.json.gz', 'wt') as stream:
        json.dump(dict(persons={'p/1': dict(pubs=[dict(key='conf/venue/1', title='A research result', year=2018)])}), stream)
    inst = 'https://openalex.org/' + D.INST['princeton']
    work = dict(id='W1', title='A research result', type='preprint', publication_year=2019,
                publication_date='2019-06-01', authorships=[dict(author=dict(id=aid), raw_author_name=n,
                institutions=[dict(id=inst)]) for aid, n in [('A1', pi), ('A2', name)]])
    monkeypatch.setattr(D, 'H', tmp_path)
    monkeypatch.setattr(D, 'sweep_works', lambda school: iter([work]))
    monkeypatch.setattr(D.P, 'data', lambda filename, school=None, **kw: tmp_path / filename)
    monkeypatch.setattr(identity, 'DUMP_PERSONS', {})
    monkeypatch.setattr(A, 'audit', lambda *a, **kw: dict(checks=dict(links=dict(unexplained=[
        dict(pi=pi, student=name, id='s1', years=[2018, 2018], roles=['phd'])]))))
    D.run('princeton')
    result = json.loads((school / 'link-diagnosis.json').read_text())['students'][pi + ' | s1']
    assert result['category'] == 'with_pi_outside_appointment'
    assert result['works'][0]['appointment_date'] == '2018'



def test_prior_biography_degree_does_not_date_lab_membership():
    row = dict(name='Liam Han', role=None, years=[None, 2016], years_basis='stated_in_entry',
               quote='Liam Han earned his BS in Mechanical Engineering from Virginia Tech in 2016')
    fixed = L.withhold_bio_degree_role(row)
    assert fixed['years'] is None and fixed['years_basis'] == 'withheld_bio_degree_sentence'
    current = dict(row, years=[2026, 2026], years_basis='capture_year_current')
    assert L.withhold_bio_degree_role(current)['years'] == [2026, 2026]
    joined = dict(row, quote='Liam Han earned his BS in 2016 and joined as a PhD student in 2021', years=[2021, None])
    assert L.withhold_bio_degree_role(joined)['years'] == [2021, None]


def test_completed_doctoral_degree_precedes_later_employment_role():
    role_of = lambda text: ('other', None)
    assert L.entry_role(', Ph.D. 2019 -> Postdoc at UW -> Researcher at Amazon', 'Ph.D. Alumni', role_of) == ('phd', 'entry')
    assert L.entry_role('MS student -> postgraduate researcher in CS', 'Students', role_of) == ('other', 'entry')


def test_same_canonical_arxiv_doi_keeps_versions_and_all_bylines():
    from collections import Counter
    from pihier import papers
    a = dict(pi='Example PI', title='Which Echo Chamber?', oa='labpage:first', work=None,
             doi='10.48550/arxiv.2107.00055', year=2021, venue='arXiv', type='preprint',
             byline=['Roy Dong', 'Lillian Ratliff'], byline_school=['Lillian Ratliff'])
    b = dict(a, title='Approximate Regions of Attraction', oa='labpage:later', year=2023,
             byline=['Roy Dong', 'Heling Zhang', 'Lillian Ratliff'])
    rows = papers.merge_editions([a, b], Counter())
    assert len(rows) == 1 and len(rows[0]['editions']) == 1
    assert {tuple(names) for names, _ in rows[0]['_bylines']} == {tuple(a['byline']), tuple(b['byline'])}
    conflict = dict(b, byline=['Unrelated Person'])
    assert len(papers.merge_editions([a, conflict], Counter())) == 2
    assert len(papers.merge_editions([a, dict(b, doi='10.48550/arxiv.2107.00056')], Counter())) == 2
    assert len(papers.merge_editions([a, dict(b, pi='Other PI')], Counter())) == 2


@pytest.mark.parametrize('text', [
    'This SIG will provide CHI attendees with an opportunity to discuss ethical challenges.',
    'In this panel, Executive Board members will discuss equity. Panelists and audience members will engage in dialogue.',
    'In this SIG we propose to discuss visualization grammars with participants.',
    'The first aim of this workshop at CHI2021 is to bring together researchers to discuss dark patterns.',
])
def test_planned_event_is_not_research(text):
    from pihier.papers import planned_session_description
    assert planned_session_description(text)


@pytest.mark.parametrize('text', [
    'We conducted a panel study of250participants and report longitudinal findings.',
    'This paper presents a visualization grammar. Future work will discuss extensions.',
    'A solar panel will provide power for the sensor network.',
    'We analyze transcripts from a SIG meeting and report three themes.',
    'Our course study compares student learning across two conditions.',
    'This paper reports a controlled study of interface panels with twenty participants. Our panel will provide tailored recommendations to participants in the next deployment.',
    'This paper reports a controlled study of interface panels with twenty participants. Our panel will provide tailored recommendations to participants in the next deployment. We discuss implications for interface design.',
])
def test_event_vocabulary_does_not_drop_empirical_research(text):
    from pihier.papers import planned_session_description
    assert not planned_session_description(text)


def test_source_session_filter_keeps_abstract_out_of_native_preimage():
    import collections
    from pihier.papers import drop_not_papers
    row = dict(pi='A', oa='W1', title='Ethical research', type='conference-paper', doi='', byline=['A','B'])
    n = collections.Counter()
    kept, samples = drop_not_papers([row], {'A': {}}, n,
        source_texts={('A','W1'): 'This SIG will provide attendees an opportunity to discuss ethical challenges.'})
    assert kept == [] and n['not_paper:planned_conference_session'] == 1
    assert samples['planned_conference_session'][0]['oa'] == 'W1'


def test_session_sources_use_same_work_original_abstract_and_compressed_page():
    import zlib
    from types import SimpleNamespace
    from pihier.papers import paper_source_texts
    raw = dict(id='W1', abstract_inverted_index={'This': [0], 'SIG': [1], 'will': [2], 'discuss': [3]})
    ctx = SimpleNamespace(hits=[('A', raw)], page_read={'W1': ('ok', zlib.compress(b'Primary page'), 'https://x/p.pdf')})
    assert paper_source_texts(ctx) == {('A', 'W1'): 'This SIG will discuss\nPrimary page'}


@pytest.mark.parametrize('desc', ['(Mentoring, MIT PhD 2026)', '(Mentoring, Stanford PhD 2024, went to Roblox)'])
def test_foreign_mentee_award_does_not_date_mentoring(desc):
    assert L.entry_years(desc, 'Previous Students and Mentoring') == (None, 'none')


def test_explicit_mentoring_interval_survives_later_degree():
    assert L.entry_years('(Mentoring 2022-2024, MIT PhD 2026)', 'Previous Students and Mentoring')[0] == [2022,2024]


def test_current_section_uses_exact_capture_point_without_inventing_start():
    row = dict(name='A Person', head='Current Doctoral Students', years=None, alumni=False, sha256='a'*64)
    capture = dict(status=200,sha256='a'*64,fetched_at='2026-11-24T01:00:00Z',capture_url=None)
    assert L.current_capture_point(row,capture) == [2026,2026]
    archive = dict(capture,capture_url='https://web.archive.org/web/20170623124500id_/https://x/team',fetched_at='2026-11-24')
    assert L.current_capture_point(row,archive) == [2017,2017]
    assert L.current_capture_point(row,dict(archive,capture_url=archive['capture_url'].replace('id_','if_'))) == [2017,2017]
    assert L.current_capture_point(row,dict(archive,capture_url='https://web.archive.org/web/2017/https://x/team')) == [2017,2017]
    assert L.current_capture_point(row,dict(archive,capture_url='https://web.archive.org/web/20150101000000if_/https://x/team')) is None
    assert L.current_capture_point(row,dict(archive,capture_url='https://web.archive.org/web/not-a-stamp/https://x/team')) is None
    for changed in [dict(row,alumni=True),dict(row,head='Previous Students'),dict(row,years=[2019,2021]),dict(row,head='Publications')]:
        assert L.current_capture_point(changed,capture) is None
    assert L.current_capture_point(row,dict(capture,sha256='b'*64)) is None
    assert L.current_capture_point(row,dict(capture,status=404)) is None
    assert L.current_capture_point(row,dict(capture,fetched_at='')) is None


def test_current_capture_point_rejects_candidate_bio_in_former_section():
    row = dict(name='A Person',head='Former Students',desc='PhD candidate',years=None,alumni=False,sha256='a'*64)
    capture = dict(status=200,sha256='a'*64,fetched_at='2026-11-24')
    assert L.current_capture_point(row,capture) is None


def test_last_modified_numeric_date_is_a_stale_roster_marker():
    assert L.stale_footer_year('Current graduate students Ryan Georgi. Last modified6/15/2014') == 2014
    assert L.stale_footer_year('Current graduate students Ryan Georgi. Last modified 6/15/2014') == 2014
    assert L.stale_footer_year('Current students: Jane Roe2019. Last modified6/15/2014') is None


def test_institution_initiative_is_not_a_roster_person():
    assert L.NONPERSON_NAME.search('UW Community-Engaged Computing Initiative')
    assert not L.NONPERSON_NAME.search('Jane Roe')


def test_pdf_verified_index_can_complete_truncated_owned_subtitle(monkeypatch):
    short = 'How Well Do Models Represent Values Across Cultures?'
    complete = short + ' Empirical Analysis Based on Cultural Dimensions'
    monkeypatch.setattr(L, 'arxiv_titles', lambda ids: {'1': complete})
    row = dict(arxiv='1',title=short,listed_title=short,evidence=dict(pdf_sha256='c'*64))
    L.fix_titles_from_arxiv([row],pages={'c'*64: complete+'\nAuthors\nAbstract'})
    assert row['title'] == complete and row['title_basis'] == 'page1_verified_title'
    assert row['previous_metadata_title'] == short
    other = dict(arxiv='1',title=short,listed_title=short,evidence=dict(pdf_sha256='d'*64))
    L.fix_titles_from_arxiv([other],pages={'d'*64: short+'\nAuthors\nAbstract'})
    assert other['title'] == short


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('case', ['institution', 'raw_affiliation', 'no_affiliation', 'no_primary_tie',
                                 'other_primary_tie', 'no_owned_work', 'distant_title_year', 'blocked_id',
                                 'conflicting_full_name'])
def test_primary_pdf_candidate_requires_independent_work_identity(tmp_path, case):
    import sqlite3
    import zlib
    import test_build_rules as T
    from pihier import common, identity, names

    T.write_school(tmp_path, sweep=[])
    ctx = T.run_stages(tmp_path, upto='anchors')
    title = 'An independently owned publication outside the provider author cluster'
    author = T.au('Ada Lovelace', 'A999', school=case != 'raw_affiliation',
                  raw=['Princeton University'] if case == 'raw_affiliation' else None)
    if case == 'no_affiliation':
        author = T.au('Ada Lovelace', 'A999', school=False)
    if case == 'conflicting_full_name':
        ctx.pid0['Ada Lovelace']['names'].append('A. Lovelace')
        ctx.nm['Ada Lovelace'] = names.Name(ctx.pid0['Ada Lovelace']['names'])
        author['raw_author_name'] = author['author']['display_name'] = 'Anita Lovelace'
    work = T.work('W999', title, 2020, [author])
    if case != 'no_owned_work':
        ctx.dblp_title['Ada Lovelace'][common.norm_title(title)] = 2016 if case == 'distant_title_year' else 2020
    if case == 'blocked_id':
        ctx.pid0['Ada Lovelace']['notOpenAlex'].append(T.OA + 'A999')
    quote = 'Grace Hopper, Princeton University' if case == 'other_primary_tie' else 'Ada Lovelace, Princeton University'
    dbpath = T.put(tmp_path, 'pi-works.sqlite')
    con = sqlite3.connect(dbpath)
    con.executescript('create table works(id text primary key,body blob); '
                     'create table pages(work text,url text,status text,pdf_sha256 text,page1 blob,school_named int,quote text);')
    con.execute('insert into works values(?,?)', (work['id'], zlib.compress(json.dumps(work).encode())))
    con.execute('insert into pages values(?,?,?,?,?,?,?)',
                (work['id'], 'https://example.edu/original.pdf', 'ok', T.SHA, zlib.compress(quote.encode()),
                 case != 'no_primary_tie', json.dumps(dict(how='named', quotes=[quote]))))
    con.commit(); con.close()
    before = dbpath.read_bytes()
    identity.hits(ctx)
    accepted = case in {'institution', 'raw_affiliation', 'no_affiliation'}
    assert bool(ctx.hits) is accepted
    if accepted:
        assert ctx.hits[0][4] == 'dblp_person_page_title'
        assert ctx.from_pw == {('Ada Lovelace', work['id'])}
        assert not ctx.anchored['Ada Lovelace']
    assert dbpath.read_bytes() == before


@pytest.mark.parametrize('change', ['complete', 'wrong_title', 'wrong_doi', 'other_pi', 'explicit_conflict'])
def test_school_only_projection_does_not_hide_exact_original_book_type(change):
    import collections
    import copy
    from types import SimpleNamespace
    from pihier import papers
    import test_build_rules as T
    w = T.work('W991', 'An Authored English Research Book', 2022, [T.au('Ada Lovelace', None)],
               typ='book', doi='10.1000/book')
    row = dict(pi='Ada Lovelace', key='labpage:book', title=w['title'], year=2022,
               doi=w['doi'], byline=['Ada Lovelace'], venue='Publisher eBooks')
    ev = dict(oa=w['id'], openalex_work=dict(id=w['id'], authorships=copy.deepcopy(w['authorships'])))
    pi = dict(pi='Ada Lovelace', names=['Ada Lovelace'])
    if change == 'wrong_title': w['title'] = 'A Different Book'
    elif change == 'wrong_doi': w['doi'] = '10.1000/other'
    elif change == 'explicit_conflict':
        ev['openalex_work'].update(title=row['title'], doi=row['doi'], type='editorial')
    owner = 'Grace Hopper' if change == 'other_pi' else pi['pi']
    ctx = SimpleNamespace(n=collections.Counter(), hits=[(owner, w, w['authorships'][0], None, None, None)])
    before = copy.deepcopy((row, ev, w))
    result = papers.recovered_source_metadata(ctx, pi, row, ev, 'labpage_addition', strict=True,
                                             binding=dict(publications=[], compatible=[]))
    if change == 'complete':
        assert result['type'] == 'book'
        assert result['quality_views'][0]['type'] == 'book'
    elif change == 'explicit_conflict':
        assert result['type'] == 'editorial'
    else:
        assert result is None
        assert ctx.recovered_source_quality[-1]['hold_reason'] == 'new_alternate_type_unproven'
    assert (row, ev, w) == before
