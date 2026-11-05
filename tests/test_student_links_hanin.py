"""R-STU-20, R-LNK-06 and R-LNK-07 (2026-11-05, owner: Boris Hanin's lab deep dive). The fixtures are the shapes found in Hanin's
lab (hanin.princeton.edu, ORFE): a prose list of PhD students with postdocs after it, his students on his bylines, and the cases
the guards must refuse."""
import collections, gzip, json, sqlite3

import atlas_paths as P
from pihier import corroborated as CO
from pihier import links
from pihier.common import Ctx

PAGE = ('<html><body><h2>Research Group</h2><p>I am fortunate to supervise several excellent PhD students: <a>Boris Shigida</a> (joint with '
        'Matias Cattaneo), <a>Alex Negron</a>, <a>Tianze Jiang</a>, <a>Shaunak Bhandarkar</a> (joint with Jonathan Pillow). I am excited to be '
        'working with several phenomenal postdocs: <a>Gage DeZoort</a>, <a>Paolo Baglioni</a></p><h3>First Placement of Former Members</h3>'
        '<p>Samy Jelassi (Postdoc at Harvard)</p><h3>Papers</h3><p>The Score Hamiltonian, with P. Halmos</p></body></html>')
SHA = 'a' * 64
TEXT = ' '.join(__import__('re').sub(r'<[^>]+>', ' ', PAGE).split())


def q(start, name):
    """The audit's quote: from the heading (or the name itself) through the name."""
    i = TEXT.index(start)
    return TEXT[i:TEXT.index(name, i) + len(name)]


def test_R_STU_20_cue_role_reads_the_prose_list():
    shigida = q('Research Group', 'Boris Shigida')
    assert CO.cue_role(TEXT, shigida, 'Boris Shigida') == 'phd'
    assert CO.cue_role(TEXT, q('Research Group', 'Tianze Jiang'), 'Tianze Jiang') == 'phd'
    assert CO.cue_role(TEXT, q('Shaunak Bhandarkar', 'Shaunak Bhandarkar'), 'Shaunak Bhandarkar') == 'phd'   # the quote starts at the name
    assert CO.cue_role(TEXT, q('Research Group', 'Gage DeZoort'), 'Gage DeZoort') is None                     # 'postdocs' is the nearer cue
    assert CO.cue_role(TEXT, q('Research Group', 'Paolo Baglioni'), 'Paolo Baglioni') is None
    assert CO.cue_role(TEXT, 'a quote the page does not hold', 'Nobody') is None


def test_R_STU_20_full_name_on_never_initials_and_guarded():
    nt = ['tianze', 'jiang']
    assert CO.full_name_on(nt, 'Jiang, Tianze', ['Tianze Jiang']) and CO.full_name_on(nt, 'Tianze Jiang', ['Tianze Jiang'])
    assert not CO.full_name_on(nt, 'T. Jiang', ['Tianze Jiang'])             # initials never corroborate
    assert not CO.full_name_on(nt, 'Kaiqi Jiang', ['Tianze Jiang'])
    assert not CO.full_name_on(nt, 'Tianyu Jiang', ['Tianze Jiang'])


def _school(tmp_path, rows):
    P.data_w('labpage-additions.json', 'x', root=tmp_path).write_text(json.dumps(dict(students=rows)))
    db = sqlite3.connect(str(P.data_w('labpage-audit-captures.sqlite', 'x', root=tmp_path)))
    db.execute('create table captures (id integer primary key, url text, sha256 text, content blob, fetched_at text)')
    db.execute('insert into captures (url, sha256, content, fetched_at) values (?, ?, ?, ?)', ('https://h.example', SHA, gzip.compress(PAGE.encode()), '2026-10-30T18:05:40+00:00'))
    db.commit(); db.close()
    return CO.open_capture_dbs('x', tmp_path)


def row(name, start='Research Group', **kw):
    return dict(name=name, role=None, years=None, url='https://h.example', sha256=SHA, quote=q(start, name), pi='Boris Hanin', **dict(dict(alumni=False), **kw))


def paper(work, year, byline):
    return dict(pi='Boris Hanin', work=work, year=year, byline=byline, _bylines=[(byline, byline)])


def test_R_STU_20_corroborated_rows(tmp_path):
    dbs = _school(tmp_path, [row('Boris Shigida'), row('Alex Negron'), row('Tianze Jiang'), row('Shaunak Bhandarkar', 'Shaunak Bhandarkar'),
                             row('Gage DeZoort'), row('Paolo Baglioni'), row('Samy Jelassi', 'Samy Jelassi', alumni=True), row('Boris Shigida', note='lab-page audit; section: Recent Lab Alumni')])
    papers = {'Boris Hanin': [paper('w1', 2026, ['Shigida, Boris', 'Hanin, Boris', 'Gromov, Andrey']),
                              paper('w2', 2025, ['Hanin, Boris', 'Jiang, Tianze']),
                              paper('w3', 2026, ['Bhandarkar, Shaunak', 'Hanin, Boris']),
                              paper('w4', 2026, ['DeZoort, Gage', 'Hanin, Boris']),
                              paper('w5', 2025, ['Samy Jelassi', 'Boris Hanin']),
                              paper('w6', 2026, ['Hanin, Boris'] + [f'Author {i}' for i in range(20)] + ['Alex Negron'])]}   # hyper-authored
    n = collections.Counter()
    out = CO.corroborated_rows('x', papers, {'Boris Hanin': []}, dbs, tmp_path, n)
    got = {r['name']: (r['role'], r['years'], w) for r, w in out}
    assert sorted(got) == ['Boris Shigida', 'Shaunak Bhandarkar', 'Tianze Jiang']
    assert got['Tianze Jiang'] == ('phd', [2026], ['w2'])                         # capture-year dating (R-STU-14): 2025 is within three years of 2026
    assert 'Alex Negron' not in got and n['labpage_students_corroborated_skipped:no_byline'] >= 1   # a roster alone is never evidence; nor a hyper-authored paper
    assert 'Gage DeZoort' not in got and 'Paolo Baglioni' not in got                # postdocs, even on the byline (DeZoort is)
    assert n['labpage_students_corroborated_skipped:alumni_without_years'] == 2       # a capture year is not a membership year (flagged alumni, and an alumni section)
    # a student the lab already holds is left to the existing records
    out = CO.corroborated_rows('x', papers, {'Boris Hanin': ['Tianze Jiang']}, dbs, tmp_path, collections.Counter())
    assert 'Tianze Jiang' not in {r['name'] for r, _ in out}
    # an explicit postdoc role is never read as a student, whatever the page says
    P.data_w('labpage-additions.json', 'x', root=tmp_path).write_text(json.dumps(dict(students=[dict(row('Tianze Jiang'), role='postdoc')])))
    assert CO.corroborated_rows('x', papers, {'Boris Hanin': []}, dbs, tmp_path, collections.Counter()) == []


def link(stu_name, relations, byline_rows, extra=()):
    """The students of one lab linked to papers (rows: (work, year, byline list, school-affiliated list)); returns {work: (basis, byline)}."""
    ctx = Ctx('x')
    ctx.rows = [dict(pi='Lab', work=w, oa=w, year=y, byline=bl, _bylines=[(bl, sch)]) for w, y, bl, sch in byline_rows]
    ctx.stu = {'Lab': {'s1': dict(person='s1', name=stu_name, relations=relations)}}
    for i, (nm, rel) in enumerate(extra):
        ctx.stu['Lab'][f's{i + 2}'] = dict(person=f's{i + 2}', name=nm, relations=rel)
    ctx.pls = {sid: [] for sid in ctx.stu['Lab']}
    links.link_students(ctx)
    return {x['work']: (x['basis'], x['byline']) for x in ctx.sp if x['student'] == 's1'}, ctx


DSPACE = [dict(type='researched_advising', years=[2022, 2022], role='phd', sources=[dict(url='u', sha256='b' * 64,
           quote='<dim:field element="contributor" qualifier="advisor">Rinard, Martin</dim:field> <dim:field qualifier="author">Shen, Jiasi</dim:field>')])]
ROSTER = [dict(type='researched_advising', years=[2022, 2022], role='phd', sources=[dict(url='u', sha256='b' * 64, quote='Jiasi Shen, PhD student of Martin Rinard')])]


def test_R_LNK_06_dissertation_year_is_the_end_of_the_work():
    papers = [('w17', 2017, ['Jiasi Shen', 'Martin Rinard'], []), ('w18', 2018, ['Jiasi Shen', 'Martin Rinard'], []),
              ('w15', 2015, ['Jiasi Shen', 'Martin Rinard'], []), ('wi', 2018, ['J. Shen', 'Martin Rinard'], []),
              ('wh', 2018, ['Jiasi Shen'] + [f'A{i}' for i in range(20)], [])]
    got, _ = link('Jiasi Shen', DSPACE, papers)
    assert set(got) >= {'w18', 'w17'} and 'w15' not in got                         # 2015 is seven years before the degree year
    assert 'wi' not in got or got['wi'][0] != 'full_name_on_lab_paper_byline'      # an initial byline never takes the longer window
    assert 'wh' not in got                                                         # nor a hyper-authored paper
    got, _ = link('Jiasi Shen', ROSTER, papers)                                    # a roster year is not a degree year: the old window
    assert 'w17' not in got and 'w18' not in got


def test_R_LNK_07_spelling_variant_within_lab():
    rel = [dict(type='researched_advising', years=[2021, 2021], role='phd', sources=[dict(url='u', sha256='b' * 64, quote='Aiden Curtis, PhD student')])]
    got, ctx = link('Aiden Curtis', rel, [('w1', 2021, ['Aidan Curtis', 'Leslie Kaelbling'], [])])
    assert got == {'w1': ('within_lab_byline_match', 'Aidan Curtis')} and ctx.n['link_within_lab_spelling_variant'] == 1
    # both spellings on one paper: two people
    got, _ = link('Aiden Curtis', rel, [('w1', 2021, ['Aidan Curtis', 'Aiden Curtis', 'Leslie Kaelbling'], [])])
    assert 'w1' in got and got['w1'][1] == 'Aiden Curtis'
    # a hyper-authored paper, and an East Asian family name ('Yue' / 'Yuan' are different people)
    got, _ = link('Aiden Curtis', rel, [('w2', 2021, ['Aidan Curtis'] + [f'A{i}' for i in range(20)], [])])
    assert got == {}
    rel2 = [dict(type='researched_advising', years=[2021, 2021], role='phd', sources=[dict(url='u', sha256='b' * 64, quote='Yuan Li, PhD student')])]
    got, _ = link('Yuan Li', rel2, [('w3', 2021, ['Yuen Li', 'Leslie Kaelbling'], [])])
    assert got == {}
    # a consonant for a consonant ('Kavin'/'Navin', 'Anna'/'Anja') and short names ('Yong'/'Yang') are different names
    rel4 = [dict(type='researched_advising', years=[2026, 2026], role='phd', sources=[dict(url='u', sha256='b' * 64, quote='Kavin Ravie, member')])]
    got, _ = link('Kavin Ravie', rel4, [('w7', 2026, ['Navin Ravie', 'Sebastian Scherer'], [])])
    assert got == {}
    got, _ = link('Connor Igoe', rel4, [('w8', 2026, ['Conor Igoe', 'Stephen Smith'], [])])
    assert got == {'w8': ('within_lab_byline_match', 'Conor Igoe')}
    # a lab student who owns the variant spelling is that author, not this one
    got, _ = link('Aiden Curtis', rel, [('w4', 2021, ['Aidan Curtis'], [])], extra=[('Aidan Curtis', rel)])
    assert 'w4' not in got
    # a family-name typo is never matched through the order swap (R-STU-13 queues it for review): 'Dor Mintzer' / 'Dor Minzer'
    rel3 = [dict(type='researched_advising', years=[2021, 2021], role='phd', sources=[dict(url='u', sha256='b' * 64, quote='Dor Mintzer, PhD student')])]
    got, _ = link('Dor Mintzer', rel3, [('w5', 2021, ['Dor Minzer', 'Mark Braverman'], [])])
    assert got == {}
    got, _ = link('Swarup Kumar Sahoo', rel3, [('w6', 2021, ['Swarun Kumar'], [])])
    assert got == {}
