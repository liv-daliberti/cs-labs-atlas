"""Stable atlas ids (tools/atlas_ids.py, docs/IDS.md): stability, reordered input, redirects, and the cross-school persons
the owner named on 2026-10-29 (Griffiths Berkeley -> Princeton, Jason Lee Princeton -> Berkeley; Dimakis, Mung Chiang and
Yuxin Chen each have one atlas school). Identifiers below are the real ones from the 2026-10-29 packages."""
import gzip, json, sqlite3, zlib
import pytest

import atlas_ids as A

GRIFFITHS_ORCID = '0000-0002-5138-7255'
GRIFFITHS_DBLP = 'https://dblp.org/pid/34/4472'
LEE_ORCID = '0000-0001-5290-1861'


def pi(name, **k):
    return dict(pi=name, names=k.pop('names', [name]), personIds=k.pop('personIds', []), orcid=k.pop('orcid', []), dblp=k.pop('dblp', []),
                reviewedOpenAlex=k.pop('oa', []), mixedOpenAlex=[], periods=k.pop('periods', []), listings=k.pop('listings', []), **k)


def stu(person, name, urls=(), **k):
    return dict(person=person, name=name, roles=['phd'], relations=[dict(type='academic_advising', years=[2019],
                                                                           sources=[dict(url=u, sha256='0' * 64, quote=name) for u in urls])], **k)


def paper(pi_, oa, doi=None, work=None, editions=(), title='t'):
    return dict(pi=pi_, oa=oa, doi=doi, work=work, title=title, year=2020, editions=list(editions))


def fixture():
    return {
        'berkeley': dict(
            pis=[pi('Thomas Griffiths', orcid=[GRIFFITHS_ORCID], dblp=[GRIFFITHS_DBLP]),
                 pi('Jason Lee', orcid=[LEE_ORCID], dblp=['https://dblp.org/pid/43/3813'], oa=['https://openalex.org/A5059740024']),
                 pi('Alex Dimakis', orcid=['0000-0002-4244-7033'], dblp=['https://dblp.org/pid/19/5000']),
                 pi('Michael Jordan', personIds=['berkeley_fac_mij'])],
            students={'Michael Jordan': [stu('berkeley_person_cj', 'Chi Jin', ['https://example.org/mij'])],
                      'Alex Dimakis': [stu('ext:berkeley:yuxin-chen', 'Yuxin Chen', ['https://example.org/dimakis-group'])]},
            papers=[paper('Thomas Griffiths', 'https://openalex.org/W1', doi='10.1/abc'),
                    paper('Michael Jordan', 'https://openalex.org/W5', editions=[dict(oa='https://openalex.org/W6', doi='10.48550/arxiv.1703.00887v2')])],
            links=[dict(pi='Michael Jordan', student='berkeley_person_cj', name='Chi Jin', oa='https://openalex.org/W5', byline='Chi Jin')],
            sweep=[dict(id='https://openalex.org/W5', authorships=[dict(raw_author_name='Chi Jin', author=dict(id='https://openalex.org/A5100595437'))])]),
        'princeton': dict(
            pis=[pi('Tom Griffiths', personIds=['leader_97645be09649f505'], orcid=[GRIFFITHS_ORCID], dblp=[GRIFFITHS_DBLP],
                    oa=['https://openalex.org/A5077079119']),
                 pi('Jason D. Lee', names=['Jason D. Lee', 'Jason Lee'], personIds=['member_lee'], orcid=[LEE_ORCID]),
                 pi('Mung Chiang', personIds=['member_chiang'], orcid=['0000-0002-8920-651X'], oa=['https://openalex.org/A5110782105']),
                 pi('Yuxin Chen', personIds=['member_yuxin'], dblp=['https://dblp.org/pid/11/5123']),
                 pi('Chi Jin', personIds=['member_chijin'], oa=['https://openalex.org/A5100595437'])],
            students={'Tom Griffiths': [stu('ext:princeton:yuxin-chen', 'Yuxin Chen', ['https://example.org/cocosci'])]},
            papers=[paper('Tom Griffiths', 'https://openalex.org/W2', doi='10.1/ABC'),           # the same DOI as Berkeley's W1
                    paper('Mung Chiang', 'https://openalex.org/W3', editions=[dict(oa='https://openalex.org/W4')]),
                    paper('Mung Chiang', 'https://openalex.org/W4', doi='10.5281/zenodo.2'),     # kept apart by the builder
                    paper('Chi Jin', 'https://dblp.org/rec/https://dblp.org/rec/conf/icml/X17', work='doi:10.48550/arxiv.1703.00887')],
            links=[], sweep=[]),
    }


def write(root, fx, reverse=False):
    for s, d in fx.items():
        D = root / s; D.mkdir(parents=True, exist_ok=True)
        rv = (lambda x: list(reversed(x))) if reverse else list
        (D / 'pis.json').write_text(json.dumps(rv(d['pis'])))
        (D / 'students.json').write_text(json.dumps({k: rv(v) for k, v in (reversed(list(d['students'].items())) if reverse else d['students'].items())}))
        for name, rows in (('lab_papers', d['papers']), ('student_papers', d['links'])):
            with gzip.open(D / f'{name}.jsonl.gz', 'wt') as f:
                for r in rv(rows):
                    f.write(json.dumps(r) + '\n')
        db = sqlite3.connect(str(D / 'openalex-sweep.sqlite'))
        db.execute('create table if not exists pages (year int, page int, cursor text, next_cursor text, n int, count int, fetched_at text, body blob, primary key (year, page))')
        db.execute('delete from pages')
        db.execute('insert into pages (year, page, body) values (2020, 1, ?)', (zlib.compress(json.dumps(d['sweep']).encode()),))
        db.commit(); db.close()


def ids(root, reg, today='2026-10-29'):
    db = A.open_registry(reg, seed=False)
    res = A.run(['berkeley', 'princeton'], root, db, today=today)
    db.close()
    rd = lambda s, f: json.loads((root / s / f).read_text())
    out = {}
    for s in ('berkeley', 'princeton'):
        for p in rd(s, 'pis.json'):
            out[('pi', s, p['pi'])] = (p['atlasId'], p['labId'])
        for k, v in rd(s, 'students.json').items():
            for r in v:
                out[('stu', s, k, r['person'])] = r['atlasId']
        for r in (json.loads(l) for l in gzip.open(root / s / 'lab_papers.jsonl.gz', 'rt')):
            out[('w', s, r['pi'], r['oa'])] = r['atlasWorkId']
    return out, res


def test_ids_are_prefixed_and_stable(tmp_path):
    write(tmp_path / 'a', fixture())
    one, _ = ids(tmp_path / 'a', tmp_path / 'r1.sqlite')
    two, _ = ids(tmp_path / 'a', tmp_path / 'r1.sqlite')          # rebuild with the registry
    assert one == two
    write(tmp_path / 'b', fixture())
    fresh, _ = ids(tmp_path / 'b', tmp_path / 'r2.sqlite')          # rebuild from an empty registry
    assert fresh == one
    assert all(v[0].startswith('atl:p:') and v[1].startswith('atl:l:') for k, v in one.items() if k[0] == 'pi')
    assert one[('pi', 'princeton', 'Tom Griffiths')][1] == 'atl:l:princeton:tom-griffiths'
    assert all(v.startswith('atl:w:') for k, v in one.items() if k[0] == 'w')


def test_reordered_input_gives_identical_ids(tmp_path):
    write(tmp_path / 'a', fixture()); write(tmp_path / 'b', fixture(), reverse=True)
    one, _ = ids(tmp_path / 'a', tmp_path / 'r1.sqlite')
    rev, _ = ids(tmp_path / 'b', tmp_path / 'r2.sqlite')
    assert one == rev


def test_cross_school_persons(tmp_path):
    write(tmp_path / 'a', fixture())
    out, res = ids(tmp_path / 'a', tmp_path / 'r.sqlite')
    # Griffiths, Berkeley -> Princeton: one person (ORCID, DBLP), two appointments, two labs
    assert out[('pi', 'berkeley', 'Thomas Griffiths')][0] == out[('pi', 'princeton', 'Tom Griffiths')][0]
    assert out[('pi', 'berkeley', 'Thomas Griffiths')][1] != out[('pi', 'princeton', 'Tom Griffiths')][1]
    # Jason Lee, Princeton -> Berkeley: one person by ORCID
    assert out[('pi', 'berkeley', 'Jason Lee')][0] == out[('pi', 'princeton', 'Jason D. Lee')][0]
    p = json.loads((tmp_path / 'a/princeton/pis.json').read_text())
    g = next(x for x in p if x['pi'] == 'Tom Griffiths')
    assert sorted(a['school'] for a in g['appointments']) == ['berkeley', 'princeton']
    # Dimakis (UT Austin is not an atlas school), Mung Chiang (Purdue), Yuxin Chen (Penn): one appointment each
    for s, n in (('berkeley', 'Alex Dimakis'), ('princeton', 'Mung Chiang'), ('princeton', 'Yuxin Chen')):
        x = next(x for x in json.loads((tmp_path / f'a/{s}/pis.json').read_text()) if x['pi'] == n)
        assert len(x['appointments']) == 1
    # a student who became faculty: Chi Jin (Jordan's student at Berkeley, PI at Princeton) by the byline author id that
    # is the Princeton PI's reviewed OpenAlex id
    assert out[('stu', 'berkeley', 'Michael Jordan', 'berkeley_person_cj')] == out[('pi', 'princeton', 'Chi Jin')][0]
    names = {c['name'] for c in res['cross']}
    assert {'Tom Griffiths', 'Jason D. Lee', 'Chi Jin'} <= names or {'Thomas Griffiths', 'Jason Lee', 'Chi Jin'} & names


def test_name_alone_never_joins(tmp_path):
    write(tmp_path / 'a', fixture())
    out, _ = ids(tmp_path / 'a', tmp_path / 'r.sqlite')
    ychen = {out[('stu', 'berkeley', 'Alex Dimakis', 'ext:berkeley:yuxin-chen')], out[('stu', 'princeton', 'Tom Griffiths', 'ext:princeton:yuxin-chen')],
             out[('pi', 'princeton', 'Yuxin Chen')][0]}
    assert len(ychen) == 3


def test_identifier_join_refused_when_family_names_differ(tmp_path):
    fx = fixture()
    fx['princeton']['pis'].append(pi('Someone Else', personIds=['member_x'], orcid=[LEE_ORCID]))  # a wrong ORCID on another person
    write(tmp_path / 'a', fx)
    out, res = ids(tmp_path / 'a', tmp_path / 'r.sqlite')
    assert out[('pi', 'princeton', 'Someone Else')][0] != out[('pi', 'princeton', 'Jason D. Lee')][0]
    assert res['report']['conflicts_refused'] >= 1


def test_works_join_by_doi_and_editions_but_not_inside_one_lab(tmp_path):
    write(tmp_path / 'a', fixture())
    out, _ = ids(tmp_path / 'a', tmp_path / 'r.sqlite')
    # one paper at two schools (same DOI, case-insensitive): one work id
    assert out[('w', 'berkeley', 'Thomas Griffiths', 'https://openalex.org/W1')] == out[('w', 'princeton', 'Tom Griffiths', 'https://openalex.org/W2')]
    # a preprint edition (arXiv DOI with version) joins the DBLP-recovered row of the same arXiv id
    assert out[('w', 'berkeley', 'Michael Jordan', 'https://openalex.org/W5')] == \
        out[('w', 'princeton', 'Chi Jin', 'https://dblp.org/rec/https://dblp.org/rec/conf/icml/X17')]
    # two rows one lab kept apart (W4 is an edition of W3 and its own row): two works
    assert out[('w', 'princeton', 'Mung Chiang', 'https://openalex.org/W3')] != out[('w', 'princeton', 'Mung Chiang', 'https://openalex.org/W4')]


def test_merge_is_a_redirect_never_a_reuse(tmp_path):
    fx = fixture()
    fx['princeton']['pis'][0] = pi('Tom Griffiths', personIds=['leader_97645be09649f505'])  # no shared identifier yet
    write(tmp_path / 'a', fx)
    one, _ = ids(tmp_path / 'a', tmp_path / 'r.sqlite', today='2026-10-29')
    b, p = one[('pi', 'berkeley', 'Thomas Griffiths')][0], one[('pi', 'princeton', 'Tom Griffiths')][0]
    assert b != p
    write(tmp_path / 'a', fixture())                                 # the ORCID and DBLP id are added at Princeton
    two, _ = ids(tmp_path / 'a', tmp_path / 'r.sqlite', today='2026-10-30')
    merged = two[('pi', 'berkeley', 'Thomas Griffiths')][0]
    assert merged == two[('pi', 'princeton', 'Tom Griffiths')][0] and merged in (b, p)
    old = p if merged == b else b
    db = sqlite3.connect(str(tmp_path / 'r.sqlite'))
    assert db.execute('select status, redirect_to from ids where id=?', (old,)).fetchone() == ('redirect', merged)
    assert A.resolve(db, old) == merged
    lines = (tmp_path / 'a/ids/redirects.tsv').read_text().splitlines()
    assert f'{old}\t{merged}\tperson' in lines
    # the lab ids do not change: each lab is keyed by its school and the person
    assert two[('pi', 'princeton', 'Tom Griffiths')][1] == 'atl:l:princeton:tom-griffiths'


def test_normalizers():
    assert A.norm_dblp_key('https://dblp.org/rec/https://dblp.org/rec/conf/aistats/NgLKL022') == 'conf/aistats/NgLKL022'
    assert A.norm_dblp_pid('https://dblp.org/pid/34/4472') == '34/4472'
    assert A.arxiv_of(A.norm_doi('https://doi.org/10.48550/arXiv.2311.09994v2')) == '2311.09994'
    assert A.norm_orcid('https://orcid.org/0000-0003-0064-780x') == '0000-0003-0064-780X'
    assert A.compatible('Tom Griffiths', 'Thomas L. Griffiths', A.__dict__.get('nick') or (lambda a, b: {a, b} == {'tom', 'thomas'}))
    assert not A.compatible('Y. Chen', 'Yuxin Chen')
