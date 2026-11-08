"""Membership survives; only source-stated advising can lend PI identity/affiliation."""
import copy
import gzip
import json

import pytest
import test_build_rules as B
from pihier import identity, links, papers

pytestmark = pytest.mark.usefixtures('layout')


@pytest.fixture(autouse=True)
def clear_dump(monkeypatch):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)


def change_member(root, relation_type, quote, *, advisor=None):
    path = B.put(root, 'collection.json.gz')
    collection = json.loads(gzip.decompress(path.read_bytes()))
    member = next(p for p in collection['people'] if p['id'] == 'p_alan')
    member['contexts'] = [dict(type=relation_type, role='phd', years=[2020], unit='u_ada',
                               sources=[B.src(quote)], **({'advisorName': advisor} if advisor else {}))]
    path.write_bytes(gzip.compress(json.dumps(collection).encode()))


def school_fixture(root, *, advising=False, quote=None, typ=None):
    sweep = [
        B.work('WOWN', 'An Independently Identified Lab Paper', 2020,
               [B.au('Ada Lovelace', 'A1'), B.au('Alan Turing', 'A9')]),
        B.work('WMEMBER', 'A Paper With An Unresolved PI Identity', 2020,
               [B.au('Ada Lovelace', 'A77'), B.au('Alan Turing', 'A9')]),
        B.work('WAFF', 'A Paper With An Unaffiliated PI Authorship', 2020,
               [B.au('Ada Lovelace', 'A1', school=False), B.au('Alan Turing', 'A9')]),
    ]
    B.write_school(root, sweep=sweep)
    change_member(root, typ or ('phd_advising' if advising else 'direct_lab_membership'),
                  quote or ('Alan Turing. Adviser: Ada Lovelace' if advising else 'Current PhD students: Alan Turing'),
                  advisor='Ada Lovelace' if advising else None)


@pytest.mark.parametrize('advising', [False, True])
def test_actual_identity_and_affiliation_consumers_need_stated_advising(tmp_path, advising):
    school_fixture(tmp_path, advising=advising)
    ctx = B.run_stages(tmp_path)
    rows = B.rows_of(ctx, 'Ada Lovelace')
    assert ('A Paper With An Unresolved PI Identity' in rows) is advising
    assert ('A Paper With An Unaffiliated PI Authorship' in rows) is advising
    if advising:
        assert rows['A Paper With An Unresolved PI Identity']['identity'] == 'advisee_coauthor'
    # A real lab member and their ordinary candidate link on an independently admitted paper survive.
    assert 'p_alan' in ctx.stu['Ada Lovelace']
    ordinary = rows['An Independently Identified Lab Paper']
    assert any(link['student'] == 'p_alan' and link['oa'] == ordinary['oa'] and link['status'] == 'candidate'
               for link in ctx.sp)
    # The same filtered full-name index serves R-PAP-12, not just the identity route.
    work = B.work('WUNAFF', 'A Fully Unaffiliated Preprint', 2020,
                  [B.au('Ada Lovelace', 'A1', school=False), B.au('Alan Turing', 'A9', school=False)])
    ctx.from_pw.add(('Ada Lovelace', work['id']))
    assert bool(papers.school_basis(ctx, 'Ada Lovelace', work, work['authorships'][0],
                                   'reviewed_openalex_author_id', None)[0]) is advising


@pytest.mark.parametrize('relationship', [None, 'advising', 'membership'])
def test_degree_generated_researched_advising_requires_exact_reviewed_decision(tmp_path, relationship):
    school_fixture(tmp_path)
    change_member(tmp_path, 'academic_advising', 'Current students: Alan Turing')
    source = dict(name='Alan Turing', role='phd', years=[2020], **B.src('Current students: Alan Turing'))
    if relationship:
        source['relationship'] = relationship
    B.put(tmp_path, 'few-students-evidence.json').write_text(json.dumps([dict(pi='Ada Lovelace', students=[source])]))
    ctx = B.run_stages(tmp_path)
    assert ('A Paper With An Unresolved PI Identity' in B.rows_of(ctx, 'Ada Lovelace')) is (relationship == 'advising')
    assert ctx.stu['Ada Lovelace']['p_alan']['roles'] == ['phd']


@pytest.mark.parametrize('field,value', [
    ('url', 'https://example.edu/page/'), ('sha256', 'b' * 64),
    ('quote', 'A different captured entry'), ('name', 'Another Student'),
])
def test_stale_or_different_review_preimage_cannot_lend_identity(tmp_path, field, value):
    school_fixture(tmp_path)
    change_member(tmp_path, 'academic_advising', 'Current students: Alan Turing')
    ctx = B.run_stages(tmp_path, upto='students')
    before = copy.deepcopy(ctx.stu)
    row = dict(name='Alan Turing', role='phd', relationship='advising', **B.src('Current students: Alan Turing'))
    row[field] = value
    B.put(tmp_path, 'few-students-evidence.json').write_text(json.dumps([dict(pi='Ada Lovelace', students=[row])]))
    identity.anchors(ctx)
    identity.hits(ctx)
    papers.lab_papers(ctx)
    assert 'A Paper With An Unresolved PI Identity' not in B.rows_of(ctx, 'Ada Lovelace')
    assert ctx.stu == before


@pytest.mark.parametrize('quote', [
    'Doctoral Dissertation Reader (AC) Alan Turing',
    'Doctoral (Program) Alan Turing',
    'Alan Turing. Adviser: Grace Hopper',
    'Alan Turing. Program: PhD. Academic Advisor: Ada Lovelace',
    'Postdoctoral Faculty Sponsor Alan Turing',
])
def test_program_reader_and_other_adviser_cannot_lend_identity(tmp_path, quote):
    school_fixture(tmp_path, advising=True, quote=quote)
    ctx = B.run_stages(tmp_path, upto='papers')
    assert 'A Paper With An Unresolved PI Identity' not in B.rows_of(ctx, 'Ada Lovelace')


def test_named_co_adviser_remains_a_stated_advisee(tmp_path):
    school_fixture(tmp_path, advising=True, quote='Alan Turing. Adviser(s): Ada Lovelace; Grace Hopper')
    ctx = B.run_stages(tmp_path, upto='papers')
    assert 'A Paper With An Unresolved PI Identity' in B.rows_of(ctx, 'Ada Lovelace')


@pytest.mark.parametrize('quote', ['Alan Turing. Adviser: A. Lovelace', 'Alan Turing. Adviser: Lovelace'])
def test_expanded_collection_name_cannot_replace_initials_or_surname_source(tmp_path, quote):
    school_fixture(tmp_path, advising=True, quote=quote)
    ctx = B.run_stages(tmp_path, upto='papers')
    assert 'A Paper With An Unresolved PI Identity' not in B.rows_of(ctx, 'Ada Lovelace')


def test_literal_student_of_named_PI_is_not_just_a_degree_label(tmp_path):
    school_fixture(tmp_path)
    change_member(tmp_path, 'academic_advising', 'Alan Turing, PhD student of Ada Lovelace')
    ctx = B.run_stages(tmp_path, upto='papers')
    assert 'A Paper With An Unresolved PI Identity' in B.rows_of(ctx, 'Ada Lovelace')


@pytest.mark.parametrize('reviewed,owner,section,expected', [
    (True, 'Ada Lovelace', 'ADVISEES Current students', True),
    (False, 'Ada Lovelace', 'ADVISEES Current students', False),
    (True, 'Grace Hopper', 'ADVISEES Current students', False),
    (True, 'Ada Lovelace', 'Current PhD students', False),
])
def test_exact_owned_advising_context_recovers_compiler_omitted_heading(tmp_path, reviewed, owner, section, expected):
    school_fixture(tmp_path)
    change_member(tmp_path, 'academic_advising', 'Alan Turing (PhD)')
    row = dict(name='Alan Turing', role='phd', reviewed=reviewed, section=section, source_owner_PI=owner,
               PI_role_source=B.src('Ada Lovelace Professor'), **B.src('Alan Turing (PhD)'))
    B.put(tmp_path, 'few-students-evidence.json').write_text(json.dumps([dict(pi='Ada Lovelace', students=[row])]))
    ctx = B.run_stages(tmp_path, upto='papers')
    assert ('A Paper With An Unresolved PI Identity' in B.rows_of(ctx, 'Ada Lovelace')) is expected


def test_explicit_membership_overrides_same_source_positive_context(tmp_path):
    school_fixture(tmp_path, advising=True)
    row = dict(name='Alan Turing', role='phd', relationship='membership', reviewed=True,
               section='ADVISEES', source_owner_PI='Ada Lovelace',
               PI_role_source=B.src('Ada Lovelace Professor'), **B.src('Alan Turing. Adviser: Ada Lovelace'))
    B.put(tmp_path, 'few-students-evidence.json').write_text(json.dumps([dict(pi='Ada Lovelace', students=[row])]))
    ctx = B.run_stages(tmp_path, upto='papers')
    assert 'p_alan' in ctx.stu['Ada Lovelace']
    assert 'A Paper With An Unresolved PI Identity' not in B.rows_of(ctx, 'Ada Lovelace')
    before = copy.deepcopy(ctx.stu)
    links.link_students(ctx)
    assert ctx.stu == before


def test_owned_context_cannot_borrow_another_PIs_role_source(tmp_path):
    school_fixture(tmp_path)
    change_member(tmp_path, 'academic_advising', 'Alan Turing (PhD)')
    row = dict(name='Alan Turing', role='phd', reviewed=True, section='ADVISEES',
               source_owner_PI='Ada Lovelace', PI_role_source=B.src('Grace Hopper Professor'),
               **B.src('Alan Turing (PhD)'))
    B.put(tmp_path, 'few-students-evidence.json').write_text(json.dumps([dict(pi='Ada Lovelace', students=[row])]))
    ctx = B.run_stages(tmp_path, upto='papers')
    assert 'A Paper With An Unresolved PI Identity' not in B.rows_of(ctx, 'Ada Lovelace')


@pytest.mark.parametrize('change,expected', [
    (None, True), ('source_hash', False), ('owned_url', False), ('other_PI', False),
    ('other_student', False), ('membership', False),
])
def test_finite_owned_first_person_advising_recovers_real_entry_context(tmp_path, change, expected):
    school_fixture(tmp_path)
    home, profile = 'https://lab.example/ada/', 'https://faculty.example/ada'
    quote = 'My master student Alan Turing received a research award.'
    if change == 'other_student':
        quote = 'My master student Another Person collaborated with Alan Turing.'
    change_member(tmp_path, 'academic_advising', quote)
    # The source citation is to the same owned page whose literal official link was reviewed.
    path = B.put(tmp_path, 'collection.json.gz')
    collection = json.loads(gzip.decompress(path.read_bytes()))
    next(p for p in collection['people'] if p['id'] == 'p_alan')['contexts'][0]['sources'] = [B.src(quote, home)]
    path.write_bytes(gzip.compress(json.dumps(collection).encode()))
    student = dict(name='Alan Turing', role='masters', reviewed=True, **B.src(quote, home))
    if change == 'membership':
        student['relationship'] = 'membership'
    context = dict(profile=profile, home=home,
                   official_role=B.src('Grace Hopper Professor' if change == 'other_PI' else 'Ada Lovelace Professor', profile),
                   owned_role=B.src('I am a Professor.', home), owned_named_PI_alias='Ada Lovelace',
                   official_outbound=dict(B.src(home, profile), literal_href=home))
    if change == 'source_hash':
        context['owned_role']['sha256'] = 'b' * 64
    if change == 'owned_url':
        context['owned_role']['url'] = home.rstrip('/')
    B.put(tmp_path, 'few-students-evidence.json').write_text(json.dumps([
        dict(pi='Ada Lovelace', students=[student], pi_context_evidence=context)]))
    ctx = B.run_stages(tmp_path, upto='papers')
    assert ('A Paper With An Unresolved PI Identity' in B.rows_of(ctx, 'Ada Lovelace')) is expected
    assert 'p_alan' in ctx.stu['Ada Lovelace']
