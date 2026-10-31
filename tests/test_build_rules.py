"""The builder's rules (docs/RULES.md) on a small synthetic school, through the stage functions of tools/pihier/: one test
per rule id that had none before the split (ROADMAP item 8). The school is written to tmp_path in the layout the build
reads (census, collection, overrides, listings, researched evidence, an OpenAlex sweep), and the stages run as
pihier.build.build runs them, without writing a package. No project data is read: the charter tables of 'princeton' (and
'cmu' for its own units) come from schools/*.toml, which CI has."""
import collections, gzip, json, sqlite3, zlib

import pytest

from pihier import census, common, identity, links, names, papers, periods, students

SCHOOL = 'princeton'
INST = 'https://openalex.org/' + common.INST[SCHOOL]
OA = 'https://openalex.org/'
SHA = 'a' * 64


@pytest.fixture(autouse=True)
def fresh_caches(monkeypatch):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)  # a dump read by another test must not leak into this one


def src(quote, url='https://example.edu/page'):
    return dict(url=url, sha256=SHA, quote=quote)


def au(name, aid, school=True, pos='middle', raw=None):
    """An OpenAlex authorship; school=True lists Princeton (institution lineage and raw string)."""
    return dict(author_position=pos, raw_author_name=name, author=dict(id=OA + aid if aid else None, display_name=name),
                institutions=[dict(id=INST, display_name='Princeton University', lineage=[INST])] if school else [],
                raw_affiliation_strings=(raw if raw is not None else (['Princeton University'] if school else [])))


def work(wid, title, year, auths, typ='article', doi=None):
    return dict(id=OA + wid, title=title, publication_year=year, publication_date=f'{year}-05-01', type=typ, doi=doi,
                primary_location=dict(source=dict(display_name='Journal X', type='journal'), landing_page_url='https://x/' + wid),
                authorships=auths)


def advisee(pid, name, pi, quote=None, years=(2020,), typ='phd_advising'):
    return dict(id=pid, name=name, roles=['phd'], contexts=[dict(type=typ, advisorName=pi, years=list(years), role='phd',
                                                                 sources=[src(quote or f'{name}, PhD student. Adviser: {pi}')])])


CENSUS = [
    dict(name='Ada Lovelace', is_pi=True, lab_units=['u_ada'], collection_person_id='p_ada', departments=['Computer Science']),
    dict(name='Grace Hopper', is_pi=True, lab_units=['u_center'], collection_person_id='p_grace', departments=['Computer Science']),
    dict(name='Dan Klein', is_pi=True, departments=['Computer Science']),
    dict(name='Daniel Klein', is_pi=True, departments=['Computer Science']),   # one person listed twice (nickname)
    dict(name='Not Apie', is_pi=False),
]
PEOPLE = [
    dict(id='p_ada', name='Ada Lovelace', roles=['faculty'], contexts=[]),
    dict(id='p_grace', name='Grace Hopper', roles=['faculty'], contexts=[]),
    dict(id='p_ada_roster', name='Ada Lovelace', roles=['member'],     # the lab roster lists its head (R-HIER-04)
         contexts=[dict(type='direct_lab_membership', unit='u_ada', role='principal_investigator', sources=[src('Lovelace Lab: Ada Lovelace (PI)')])]),
    advisee('p_alan', 'Alan Turing', 'Ada Lovelace'),
    advisee('p_bruno', 'Bruno Schmitt Antunes', 'Ada Lovelace'),
    advisee('p_linus', 'Linus Linked', 'Ada Lovelace'),
    advisee('p_bob', 'Bob Smith', 'Ada Lovelace', quote='Doctoral Dissertation Reader (AC) Bob Smith'),   # R-STU-02
    advisee('p_wz1', 'Wei Zhang', 'Ada Lovelace'),
    advisee('p_wz2', 'Wei Zhang', 'Grace Hopper'),                      # a namesake in another lab (R-HIER-03)
    advisee('p_mm1', 'Mary Major', 'Ada Lovelace'),
    advisee('p_mm2', 'Mary Minor', 'Ada Lovelace'),                     # one person, reviewed (R-STU-04)
    advisee('p_carl', 'Carl Drop', 'Ada Lovelace'),                     # dropped by a reviewed correction (R-STU-04)
]
UNITS = [dict(id='u_ada', name='Lovelace Lab', leaders=['p_ada']),
         dict(id='u_center', name='Center for Computing', leaders=['p_grace'])]   # a single-leader collective (R-HIER-02)
WORKS = {'cw1': dict(title='Learning to Compute', doi='10.1/w1', year=2020)}
SWEEP = [
    work('W1', 'Learning to Compute', 2020, [au('Ada Lovelace', 'A1', pos='first'), au('Alan Turing', 'A9'),
                                             au('Bruno Schmitt', None, school=False), au('Linus Linked', 'A8')], doi='10.1/w1'),
    work('W2', 'Learning to Compute', 2020, [au('Ada Lovelace', 'A1'), au('Alan Turing', 'A9')], typ='preprint',
         doi='https://doi.org/10.48550/arxiv.2001.00001'),                  # the preprint edition (R-PAP-16)
    work('W3', 'The Advisee Route', 2020, [au('Ada Lovelace', 'A1', school=False), au('Alan Turing', 'A9')]),   # R-PAP-11
    work('W4', 'Some Dataset', 2020, [au('Ada Lovelace', 'A1')], typ='dataset'),                                # R-PAP-17
    work('W6', 'Before the Appointment', 2010, [au('Ada Lovelace', 'A1')]),                                     # R-PAP-01
    work('W7', 'A Listed Year', 2020, [au('Grace Hopper', 'A2')]),
    work('W8', 'A Student Row Year', 2021, [au('Grace Hopper', 'A2')]),                                          # R-PAP-02
    work('W9', 'Mixed Record Paper', 2020, [au('Ada Lovelace', 'A77'), au('Alan Turing', 'A9')]),                 # R-PAP-06
]
OVERRIDES = {SCHOOL: {
    'Ada Lovelace': dict(openalex=[OA + 'A1'], mixed_openalex=[OA + 'A77'],
                         periods=[dict(id='reviewed:ada-lovelace:1', start='2015', end=None, evidence=[src('Ada Lovelace joined Princeton in 2015.')])]),
    'Grace Hopper': dict(openalex=[OA + 'A2']),
}}
LISTINGS = [dict(pi='Grace Hopper', year=2020, capture_url='https://web.archive.org/web/20200301000000/https://cs.example.edu/people',
                 sha256=SHA, quote='Grace Hopper Professor of Computer Science', rank_as_listed='Professor', department='Computer Science'),
            dict(pi='Grace Hopper', year=2021, capture_url='https://web.archive.org/web/20210301000000/https://cs.example.edu/people',
                 sha256=SHA, quote='Grace Hopper PhD student', rank_as_listed='PhD student', department='Computer Science')]


def write_school(root, sweep=SWEEP):
    H = root / 'hierarchy'
    (H / SCHOOL / 'raw').mkdir(parents=True)
    (root / 'census').mkdir()
    (root / 'listings' / SCHOOL).mkdir(parents=True)
    (root / 'census' / f'{SCHOOL}-faculty.json').write_text(json.dumps(CENSUS))
    coll = dict(people=PEOPLE, units=UNITS, works=WORKS, facultyPeriods=[],
                personLinks=[dict(person='p_linus', work='cw1', status='verified', role='author')])
    (H / SCHOOL / 'collection.json.gz').write_bytes(gzip.compress(json.dumps(coll).encode()))
    (H / SCHOOL / 'raw' / 'dblp_pubs.json.gz').write_bytes(gzip.compress(json.dumps(dict(pubs={})).encode()))  # no cached DBLP lists
    (H / 'census-overrides.json').write_text(json.dumps(OVERRIDES))
    (root / 'listings' / SCHOOL / 'listings.json').write_text(json.dumps(LISTINGS))
    (H / SCHOOL / 'few-students-evidence.json').write_text(json.dumps([dict(pi='Grace Hopper', students=[dict(
        name='Rosa Researched', role='phd', years=[2020], url='https://example.edu/hopper', sha256=SHA,
        quote='Rosa Researched, PhD student of Grace Hopper')])]))
    (H / 'student-identity-review.json').write_text(json.dumps([dict(school=SCHOOL, pi='Ada Lovelace', verdict='same_person',
                                                                    a=['p_mm1'], b=['p_mm2'], canonical_name='Mary Major', reason='maiden name')]))
    (H / 'student-corrections.json').write_text(json.dumps([dict(school=SCHOOL, pi='Ada Lovelace', student='p_carl', action='drop',
                                                                reason='not a student of the lab')]))
    db = sqlite3.connect(str(H / SCHOOL / 'openalex-sweep.sqlite'))
    db.execute('create table pages (year int, page int, n int, fetched_at text, body blob, primary key (year, page))')
    for y in sorted({w['publication_year'] for w in sweep}):
        ws = [w for w in sweep if w['publication_year'] == y]
        db.execute('insert into pages values (?, 1, ?, ?, ?)', (y, len(ws), '2026-10-21', zlib.compress(json.dumps(ws).encode())))
    db.commit(); db.close()


def run_stages(root, upto='drop_weak'):
    ctx = common.Ctx(SCHOOL, here=root, site=root, out=root / 'out')
    steps = [('load', census.load), ('reviewed', census.reviewed_inputs), ('pis', census.pi_records), ('index', census.index_pis),
             ('students', students.gather), ('anchors', identity.anchors), ('hits', identity.hits), ('papers', papers.lab_papers),
             ('links', links.link_students), ('drop_weak', lambda c: students.drop_weak(c, c.sp))]
    for name, f in steps:
        f(ctx)
        if name == upto:
            break
    return ctx


@pytest.fixture
def built(tmp_path):
    write_school(tmp_path)
    return run_stages(tmp_path)


def rows_of(ctx, pi):
    return {r['title']: r for r in ctx.rows if r['pi'] == pi}


# ---- the hierarchy --------------------------------------------------------------------------------------------------

def test_R_HIER_01_one_own_lab_per_pi(built):
    pis = {p['pi']: p for p in built.pis}
    assert sorted(pis) == ['Ada Lovelace', 'Dan Klein', 'Grace Hopper']                   # is_pi rows only, one per person
    assert pis['Dan Klein']['mergedCensusRows'] == ['Daniel Klein'] and built.n['census_rows_merged_by_nickname'] == 1
    assert pis['Ada Lovelace']['lab'] == dict(unitId='u_ada', name='Lovelace Lab', basis='single_leader_unit')
    assert pis['Dan Klein']['lab']['basis'] == 'new_own_lab' and pis['Dan Klein']['lab']['name'] == 'Dan Klein group'
    # a unit with two leaders is no one's own lab
    two = dict(id='u2', name='Shared Lab', leaders=['p_ada', 'p_grace'])
    x = dict(name='Ada Lovelace', lab_units=['u2'])
    assert census.choose_lab(x, {'u2': two}, built.Pid, ['p_ada'], ['Ada Lovelace'])['basis'] == 'new_own_lab'


def test_R_HIER_02_collectives_are_not_labs(built):
    lab = {p['pi']: p for p in built.pis}['Grace Hopper']['lab']
    assert lab['basis'] == 'new_own_lab' and lab['unitId'] is None and lab['collectives'] == ['u_center']
    assert census.COLLECTIVE.search('Center for Computing') and census.COLLECTIVE.search('AI Initiative')
    group = dict(id='u3', name='Robotics Institute Vision Group', leaders=['p_ada'])   # says 'group': a lab after all
    assert census.choose_lab(dict(name='Ada Lovelace', lab_units=['u3']), {'u3': group}, built.Pid, ['p_ada'], ['Ada Lovelace'])['basis'] == 'single_leader_unit'


def test_R_HIER_03_no_merge_across_labs(built):
    assert 'p_wz1' in built.stu['Ada Lovelace'] and 'p_wz2' in built.stu['Grace Hopper']
    assert built.n['student_same_name_other_labs_unmerged'] == 1


def test_R_HIER_04_pi_is_not_their_own_student(built):
    assert 'p_ada_roster' not in built.stu['Ada Lovelace']
    assert [x['student'] for x in built.self_listed] == ['p_ada_roster'] and built.n['pi_listed_as_own_student_dropped'] == 1


# ---- which papers are a lab's papers ------------------------------------------------------------------------------

def test_R_PAP_01_appointment_period_or_same_year_listing(built):
    ada, grace = rows_of(built, 'Ada Lovelace'), rows_of(built, 'Grace Hopper')
    assert 'Before the Appointment' not in ada and built.n['outside_appointment'] >= 1     # 2010, before the 2015 period
    assert 'periodId' in ada['Learning to Compute']['appointment']
    assert grace['A Listed Year']['appointment']['listing']['year'] == 2020                 # the listing proves its own year
    assert periods.contains('2015', None, '2020-05-01', '2026-10-30') == 'supported'
    assert periods.contains('2015', '2018', '2018', None) == 'boundary_unresolved'          # boundary years stay unresolved
    assert periods.contains('2015', '2018', '2019-03-01', None) == 'outside'
    assert periods.same_year('2020-05') == 2020 and periods.same_year('2020') == 2020


def test_R_PAP_02_listings_that_prove_nothing(built):
    assert 'A Student Row Year' not in rows_of(built, 'Grace Hopper') and built.n['listing_rows_not_faculty'] == 1
    assert periods.not_faculty_row('PhD student, Computer Science') and periods.not_faculty_row('Incoming faculty, starting 2025')
    assert not periods.not_faculty_row('Acting Professor') and not periods.not_faculty_row('Professor; advises PhD students')
    assert periods.datebounds('2020 (Fall)') == ('2020-08-01', '2020-12-31') and periods.datebounds('2021-02') == ('2021-02-01', '2021-02-28')


def test_R_PAP_04_identity_order(built):
    ctx, pi = built, 'Ada Lovelace'
    w = dict(id=OA + 'Wx', title='A Fresh Title About Several Interesting Things', publication_year=2020, doi='10.9/x', authorships=[])
    a = au('Ada Lovelace', 'A1')
    assert identity.authorship_identity(ctx, pi, w, a, None) == 'reviewed_openalex_author_id'
    ctx.blocked[pi].add(OA + 'A1')
    assert identity.authorship_identity(ctx, pi, w, a, None) is None                        # reviewed as someone else's: never
    ctx.blocked[pi].discard(OA + 'A1')
    b = au('Ada Lovelace', 'Z7')
    assert identity.authorship_identity(ctx, pi, w, b, None) is None
    ctx.orcids[pi].add('0000-0001-2345-6789')
    assert identity.authorship_identity(ctx, pi, w, dict(b, author=dict(b['author'], orcid='https://orcid.org/0000-0001-2345-6789')), None) == 'pi_orcid'
    ctx.verified[pi].add('cw9')
    assert identity.authorship_identity(ctx, pi, w, b, 'cw9') == 'dblp_verified_collection_work'
    ctx.dblp_doi[pi].add('10.9/x')
    assert identity.authorship_identity(ctx, pi, w, b, None) == 'dblp_person_page_doi'
    ctx.dblp_doi[pi].discard('10.9/x')
    ctx.dblp_title[pi][common.norm_title(w['title'])] = 2021                                 # +-1 year
    assert identity.authorship_identity(ctx, pi, w, b, None) == 'dblp_person_page_title'
    del ctx.dblp_title[pi][common.norm_title(w['title'])]
    ctx.own_list[pi][common.norm_title(w['title'])] = 2020
    assert identity.authorship_identity(ctx, pi, w, b, None) == 'pi_institutional_publication_list'
    del ctx.own_list[pi][common.norm_title(w['title'])]
    ctx.lab_page[pi].append((common.norm_title('A. Lovelace and A. Turing. ' + w['title'] + '. In Proc X, 2020.'), 2020))
    assert identity.authorship_identity(ctx, pi, w, b, None) == 'lab_publication_page'
    ctx.lab_page[pi].clear()
    w2 = dict(w, authorships=[b, au('Alan Turing', 'A9')])
    assert identity.authorship_identity(ctx, pi, w2, b, None) == 'advisee_coauthor'
    # R-PAP-07: initials on both sides prove nothing
    bi = au('A. Lovelace', 'Z7')
    assert identity.authorship_identity(ctx, pi, dict(w, authorships=[bi, au('A. Turing', 'A9')]), bi, None) is None


def test_R_PAP_05_dblp_dump():
    pis = [dict(pi='Jun-Yan Zhu', names=['Jun-Yan Zhu'], dblp=['p/zj'], orcid=[]),
           dict(pi='Song Mei', names=['Song Mei'], dblp=[], orcid=[]),
           dict(pi='Wei Wang', names=['Wei Wang'], dblp=[], orcid=[])]
    dump = dict(persons={'p/zj': dict(names=['Jun Zhu'], pubs=[]),
                         'p/sm': dict(names=['Song Mei'], orcid=['0000-0001-0000-0001'],
                                      pubs=[dict(title='Mean-field Theory of Two-Layers Networks.', year=2019, dois=['10.1/mf'])]),
                         'p/ww1': dict(names=['Wei Wang 0001'], pubs=[], disambiguation=True)},
                by_name={'song mei': ['p/sm'], 'wei wang': ['p/ww1']})
    doi, title, n = collections.defaultdict(set), collections.defaultdict(dict), collections.Counter()
    identity.apply_dump(pis, dump, doi, title, n)
    assert pis[0]['dblp'] == [] and pis[0]['dblpDropped'] == ['p/zj'] and n['dblp_ids_dropped_name_mismatch'] == 1   # name_conflict
    assert pis[1]['dblp'] == ['p/sm'] and pis[1]['orcid'] == ['0000-0001-0000-0001'] and '10.1/mf' in doi['Song Mei']
    assert title['Song Mei'][common.norm_title('Mean-field Theory of Two-Layers Networks')] == 2019
    assert pis[2]['dblp'] == []                                                              # a disambiguation page is no person


def test_R_PAP_06_mixed_ids_neither_anchor_nor_block(built):
    assert OA + 'A77' not in built.blocked['Ada Lovelace'] and OA + 'A77' in built.mixed['Ada Lovelace']
    assert OA + 'A77' not in built.anchored['Ada Lovelace'] and built.anchored['Ada Lovelace'][OA + 'A1'] >= 1
    r = rows_of(built, 'Ada Lovelace')['Mixed Record Paper']                                 # kept on per-work evidence
    assert r['identity'] == 'advisee_coauthor' and r['authorship']['author_id'] == OA + 'A77'


def test_R_PAP_08_generational_suffixes():
    assert names.nosuffix(['john', 'w', 'fisher', 'iii']) == ['john', 'w', 'fisher']
    assert names.Name(['John Fisher']).match('John W. Fisher III') and names.Name(['Lionel P. Robert Jr.']).match('Lionel Robert')
    assert names.nosuffix(['ii', 'jr']) == ['ii', 'jr']                                       # too short to carry a suffix


def test_R_PAP_09_the_schools_own_institutes():
    assert not papers.names_other_inst('Robotics Institute, School of Computer Science', 'cmu')
    assert not papers.names_other_inst('Neuroscience Institute', 'cmu')
    assert papers.names_other_inst('Neuroscience Institute', 'princeton')                      # only CMU's own units
    assert papers.names_other_inst('Allen Institute for AI', 'cmu')


def test_R_PAP_10_page1_tie_outranks_openalex(built):
    w = work('W20', 'Tied By Page One', 2020, [au('Ada Lovelace', 'A1', school=False, raw=['Google Research'])])
    a = w['authorships'][0]
    built.tied[w['id']] = dict(how='byline', quotes=['Ada Lovelace', 'Princeton University'], url='https://arxiv.org/abs/x', pdf_sha256=SHA)
    via, page1 = papers.school_basis(built, 'Ada Lovelace', w, a, 'reviewed_openalex_author_id', None)
    assert via[0].startswith('page 1 (byline)') and page1['url'] == 'https://arxiv.org/abs/x'
    del built.tied[w['id']]
    assert papers.school_basis(built, 'Ada Lovelace', w, a, 'reviewed_openalex_author_id', None)[0] == []


def test_R_PAP_11_advisee_at_the_school(built):
    r = rows_of(built, 'Ada Lovelace')['The Advisee Route']
    assert r['authorship']['school_via'] == ['advisee at the school on the byline: Alan Turing']
    w = work('W21', 'Elsewhere', 2020, [au('Ada Lovelace', 'A1', school=False, raw=['Google Research']), au('Alan Turing', 'A9')])
    assert papers.school_basis(built, 'Ada Lovelace', w, w['authorships'][0], 'reviewed_openalex_author_id', None)[0] == []   # PI elsewhere


def test_R_PAP_12_unaffiliated_byline_with_an_advisee(built):
    w = work('W22', 'An arXiv Record', 2020, [au('Ada Lovelace', 'A1', school=False), au('Alan Turing', 'A9', school=False)])
    built.from_pw.add(('Ada Lovelace', w['id']))
    via, _ = papers.school_basis(built, 'Ada Lovelace', w, w['authorships'][0], 'reviewed_openalex_author_id', None)
    assert via == ['advisee on an unaffiliated byline: Alan Turing']
    w['authorships'][1] = au('A. Turing', 'A9', school=False)                                  # not by full name
    assert papers.school_basis(built, 'Ada Lovelace', w, w['authorships'][0], 'reviewed_openalex_author_id', None)[0] == []


def test_R_PAP_14_namesake_pis():
    pis = [dict(pi='Philip Wong', names=['H.-S. Philip Wong', 'Philip Wong']), dict(pi='Simon Wong', names=['S. Simon Wong', 'Simon Wong'])]
    row = lambda pi, raw, aid: dict(pi=pi, oa=OA + 'W1', authorship=dict(raw_name=raw, position='first', author_id=aid))
    rv = {'Philip Wong': {OA + 'AP'}, 'Simon Wong': set()}
    n = collections.Counter()
    kept = papers.drop_namesakes([row('Philip Wong', 'H.-S. Wong', OA + 'AP'), row('Simon Wong', 'H.-S. Wong', OA + 'AP')], pis, rv, n)
    assert [r['pi'] for r in kept] == ['Philip Wong']                                       # the reviewed id decides
    kept = papers.drop_namesakes([row('Philip Wong', 'Simon Wong', OA + 'AX'), row('Simon Wong', 'Simon Wong', OA + 'AX')], pis, rv, n)
    assert [r['pi'] for r in kept] == ['Simon Wong']                                        # the given names spelled out
    kept = papers.drop_namesakes([row('Philip Wong', 'S. Wong', OA + 'AX'), row('Simon Wong', 'S. Wong', OA + 'AX')], pis, rv, n)
    assert kept == [] and n['namesake_claims_dropped'] == 2                                 # initials only: neither


def test_R_PAP_16_one_record_per_paper_and_lab(built):
    lead = rows_of(built, 'Ada Lovelace')['Learning to Compute']
    assert lead['oa'] == OA + 'W1' and lead['work'] == 'cw1' and lead['doi'] == '10.1/w1'   # the published edition leads
    assert [e['oa'] for e in lead['editions']] == [OA + 'W2']
    assert sum(r['title'] == 'Learning to Compute' for r in built.rows) == 1
    rows = [dict(pi='X', oa='a', work=None, doi='10.48550/arxiv.1', title='T', year=2019, byline=['A'], byline_school=[]),
            dict(pi='X', oa='b', work=None, doi='10.1/j', title='T', year=2020, byline=['A B'], byline_school=['A B'])]
    merged = papers.merge_editions(rows, collections.Counter())
    assert len(merged) == 1 and merged[0]['oa'] == 'b' and merged[0]['editions'][0]['oa'] == 'a' and len(merged[0]['_bylines']) == 2


def test_R_PAP_17_not_paper_types(built):
    assert {'dataset', 'paratext', 'peer-review', 'erratum', 'supplementary-materials', 'grant', 'standard', 'retraction',
            'reference-entry', 'libguides', 'other'} == common.NOT_PAPERS
    assert all(h[1]['id'] != OA + 'W4' for h in built.hits) and 'Some Dataset' not in rows_of(built, 'Ada Lovelace')


# ---- students -----------------------------------------------------------------------------------------------------

def test_R_STU_01_student_sources(built):
    ada, grace = built.stu['Ada Lovelace'], built.stu['Grace Hopper']
    assert ada['p_alan']['relations'][0]['type'] == 'phd_advising'                         # an advising context naming the PI
    r = grace['ext:princeton:rosa-researched']                                               # researched, with quote and hash
    assert r['relations'][0]['type'] == 'researched_advising' and r['relations'][0]['sources'][0]['sha256'] == SHA
    assert 'few-students-evidence.json' in students.RESEARCHED_FILES


def test_R_STU_02_program_and_reader_only(built):
    assert 'p_bob' not in built.stu['Ada Lovelace']
    x = next(x for x in built.weak_dropped if x['student'] == 'p_bob')
    assert x['why'] == ['reader_or_program_heading'] and built.n['students_dropped_program_or_reader_only'] == 1
    assert 'p_wz1' in built.stu['Ada Lovelace']                                               # unlinked, but a real adviser


def test_R_STU_03_adviser_names(tmp_path):
    ctx = common.Ctx(SCHOOL, here=tmp_path)
    ctx.census = [dict(name='Hari Balakrishnan', is_pi=True), dict(name='Hamsa Balakrishnan', is_pi=True, aliases=['H. Balakrishnan'])]
    ctx.ov, ctx.yearly, ctx.Pid, ctx.units, ctx.periods = {}, {}, {}, {}, []
    census.pi_records(ctx); census.index_pis(ctx)
    assert students.adviser_named(ctx, 'Hari Balakrishnan', 'Balakrishnan, Hari')
    assert not students.adviser_named(ctx, 'Hamsa Balakrishnan', 'Balakrishnan, Hari')        # the alias is no full-name form
    assert not students.adviser_named(ctx, 'Hari Balakrishnan', 'H. Balakrishnan')            # initials shared by two PIs: no one
    assert not students.adviser_named(ctx, 'Hamsa Balakrishnan', 'H. Balakrishnan')


def test_R_STU_04_reviewed_corrections(built):
    ada = built.stu['Ada Lovelace']
    assert 'p_carl' not in ada and built.n['student_corrections_drop'] == 1
    m = ada['p_mm1']
    assert m['name'] == 'Mary Major' and 'Mary Minor' in m['aliases'] and 'p_mm2' in m['merged'] and 'p_mm2' not in ada


# ---- student-paper links ------------------------------------------------------------------------------------------

def links_of(ctx, title):
    r = next(r for r in ctx.rows if r['title'] == title)
    return {x['student']: x for x in ctx.sp if x['oa'] == r['oa']}


def test_R_LNK_01_link_bases(built):
    w1 = links_of(built, 'Learning to Compute')
    assert w1['p_linus']['basis'] == 'collection_person_link'
    assert w1['p_alan']['basis'] == 'byline_name_with_school_affiliation' and w1['p_alan']['byline'] == 'Alan Turing'
    assert 'p_wz1' not in w1 and 'p_bob' not in w1


def test_R_LNK_03_within_lab_byline_matching(built):
    x = links_of(built, 'Learning to Compute')['p_bruno']                                   # 'Bruno Schmitt' for 'Bruno Schmitt Antunes'
    assert x['basis'] == 'within_lab_byline_match' and x['byline'] == 'Bruno Schmitt'


def test_R_LNK_05_links_carry_their_evidence(built):
    for x in built.sp:
        assert x['relation_source'] and x['relation_source']['sha256'] == SHA and x['relation_source']['quote']
        if x['basis'] != 'collection_person_link':
            assert x['byline'] and x['oa']


# ---- determinism (2026-10-31): a context naming several advisers -----------------------------------------------
SHARED_URL = 'https://example.edu/theses/sam-shared'
SHARED = dict(id='p_sam', name='Sam Shared', roles=['phd'], contexts=[dict(
    type='phd_advising', advisors=['Ada Lovelace', 'Grace Hopper', 'Dan Klein'], years=[2020], role='phd',
    sources=[dict(url=SHARED_URL, sha256='', quote='')])])   # a bare-URL source: the collection gave no quote or hash


def write_shared_advising(root):
    """A student whose one advising context names three PIs, with re-captured evidence (R-STU-08): a quote naming Ada, one
    naming Dan, and a student-only one (Grace's lab has no quote of its own)."""
    H = root / 'hierarchy'
    coll = json.loads(gzip.decompress((H / SCHOOL / 'collection.json.gz').read_bytes()))
    coll['people'].insert(0, SHARED)  # first: the labs' order is then the order the build meets them here
    (H / SCHOOL / 'collection.json.gz').write_bytes(gzip.compress(json.dumps(coll).encode()))
    rec = lambda pi, names_pi, q, h: dict(url=SHARED_URL, person='p_sam', pi=pi, names_pi=names_pi, sha256=h * 64, quote=q,
                                          capture_url=SHARED_URL, observed='2026-10-29', method='live')
    (H / SCHOOL / 'relation-evidence.json').write_text(json.dumps(dict(records=[
        rec('Ada Lovelace', True, 'Sam Shared, PhD 2020. Advisor: Ada Lovelace', 'b'),
        rec('Dan Klein', True, 'Sam Shared, PhD 2020, Klein group', 'c'),
        rec(None, False, 'Sam Shared, PhD 2020', 'd')])))


def test_R_STU_08_each_lab_gets_its_own_recaptured_source(tmp_path):
    write_school(tmp_path)
    write_shared_advising(tmp_path)
    ctx = run_stages(tmp_path, upto='students')
    src = {pi: ctx.stu[pi]['p_sam']['relations'][0]['sources'][0] for pi in ('Ada Lovelace', 'Grace Hopper', 'Dan Klein')}
    assert src['Ada Lovelace']['names_pi'] is True and 'Ada Lovelace' in src['Ada Lovelace']['quote']
    assert src['Dan Klein']['names_pi'] is True and 'Klein' in src['Dan Klein']['quote']
    assert src['Grace Hopper']['names_pi'] is False and src['Grace Hopper']['quote'] == 'Sam Shared, PhD 2020'
    assert len({id(s) for s in src.values()}) == 3                                       # three dicts, none shared
    assert ctx.n['relation_evidence_recaptured_names_pi'] == 2 and ctx.n['relation_evidence_recaptured_student_only'] == 1
    assert next(p for p in ctx.people if p['id'] == 'p_sam')['contexts'][0]['sources'][0]['quote'] == ''   # the input is untouched
