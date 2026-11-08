"""Native census/member regressions: exact Chinese names are identities, never an empty Latin key."""
from collections import Counter, defaultdict
import gzip
import json
from types import SimpleNamespace

import pytest

import census_build as CB
from pihier import census, students
from pihier.names import Name, placeholder_name, strict_name_one, toks
from pihier.periods import pi_listings


def faculty(name, profile):
    return dict(name=name, is_pi=True, profile_url=profile)


def test_distinct_literal_names_survive_native_census():
    rows = [faculty('孙家广', 'https://example.edu/sun'), faculty('顾明', 'https://example.edu/gu')]
    merged, nicknames = census.merge_census_rows(rows, {}, Counter())
    assert [[r['name'] for r in group] for group in merged.values()] == [['孙家广'], ['顾明']]
    assert not nicknames
    assert toks('孙家广') == ['孙家广']
    assert not placeholder_name('孙 家 广')
    assert strict_name_one('孙家广') != strict_name_one('顾明')


def test_same_written_name_needs_same_profile_or_explicit_identity():
    rows = [faculty('周强', 'https://example.edu/a'), faculty('周强', 'https://example.edu/b')]
    assert len(census.merge_census_rows(rows, {}, Counter())[0]) == 2
    assert len(census.merge_census_rows([rows[0], dict(rows[0])], {}, Counter())[0]) == 1
    rows[0]['dblp'] = rows[1]['dblp'] = ['https://dblp.org/pid/explicit']
    assert len(census.merge_census_rows(rows, {}, Counter())[0]) == 1


def test_duplicate_pi_labels_stop_before_lossy_indexing():
    ctx = SimpleNamespace(census=[faculty('周强', 'https://example.edu/a'), faculty('周强', 'https://example.edu/b')],
                          ov={}, yearly={}, Pid={}, units={}, periods=[], n=Counter())
    with pytest.raises(ValueError, match='reviewed unique display names'):
        census.pi_records(ctx)


def test_literal_name_match_is_exact_and_never_guesses_romanization():
    nm = Name(['孙家广'])
    assert nm.match('孙家广')
    assert not nm.match('顾明')
    assert not nm.match('Sun Jiaguang')
    assert Name(['孙家广', 'Jiaguang Sun']).match('Jiaguang Sun')


def test_chinese_faculty_listing_supplies_its_captured_year_only():
    x = dict(name='孙家广', sources=[dict(url='https://example.edu/sun', observed='20261108000000',
                                      sha256='a' * 64, quote='孙家广 教授')])
    assert set(pi_listings(x, {}, Counter())) == {2026}


def listing(name, profile):
    return dict(name=name, profile=profile, homepage=None, observed='20261108000000', year=2026,
                half='H2', dept='CS', rank='ladder', titles=['Professor'], dept_title=['Professor'],
                kind='main', slot='regular', capture_url='https://example.edu/faculty/',
                sha256='a' * 64, quote=f'{name} 教授')


def test_listing_census_retains_cjk_people_and_unique_ids(tmp_path, monkeypatch):
    def path(name, school=None):
        return tmp_path / (school or 'shared') / name

    def writable(name, school=None):
        p = path(name, school)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    monkeypatch.setattr(CB.P, 'data', path)
    monkeypatch.setattr(CB.P, 'data_w', writable)
    monkeypatch.setattr(CB.S, 'get', lambda key: dict(name='Example', window=[2016, 2026],
                                                  departments=[dict(code='CS', coverage='full')]))
    rows = [listing('孙家广', 'https://example.edu/sun'), listing('顾明', 'https://example.edu/gu')]
    writable('rows.json', 'test').write_text(json.dumps(rows))
    CB.main('test')
    with gzip.open(path('collection.json.gz', 'test'), 'rt') as fh:
        people = json.load(fh)['people']
    assert {p['name'] for p in people} == {'孙家广', '顾明'}
    assert len({p['id'] for p in people}) == 2
    faculty_rows = json.loads(path('census-faculty.json', 'test').read_text())['faculty']
    assert all(r['is_pi'] for r in faculty_rows)
    assert len(CB.merge_people([rows[0], dict(rows[0])])) == 1


def test_listing_same_name_distinct_profiles_do_not_merge():
    rows = [listing('周强', 'https://example.edu/a'), listing('周强', 'https://example.edu/b')]
    assert len(CB.merge_people(rows)) == 2
    for r in rows:
        r['homepage'] = 'https://example.edu/shared-lab'
    assert len(CB.merge_people(rows)) == 2


def member_context(tmp_path, monkeypatch, entries):
    path = tmp_path / 'few-students-evidence.json'
    path.write_text(json.dumps([dict(pi=pi, students=members) for pi, members in entries.items()]))
    monkeypatch.setattr(students.P, 'data', lambda fn, school=None, root=None: tmp_path / fn)
    monkeypatch.setattr(students, 'accepted_additions', lambda *args: [])
    return SimpleNamespace(here=tmp_path, school='test', pis=[dict(pi=pi) for pi in entries], ge={}, n=Counter())


def member(name, role='phd'):
    return dict(name=name, role=role, years=[2026], url='https://example.edu/members', sha256='a' * 64,
                quote=f'{name} {role}')


def test_native_researched_members_keep_distinct_names_and_lab_scoped_ids(tmp_path, monkeypatch):
    ctx = member_context(tmp_path, monkeypatch, {'孙家广': [member('张三'), member('李四')], '顾明': [member('张三')]})
    stu = defaultdict(dict)
    students.researched(ctx, stu, {})
    assert [len(stu[pi]) for pi in ('孙家广', '顾明')] == [2, 1]
    ids = [r['person'] for members in stu.values() for r in members.values()]
    assert len(set(ids)) == 3 and all(sid != 'ext:test:' for sid in ids)
    again = defaultdict(dict)
    students.researched(ctx, again, {})
    assert stu == again
    assert students.external_member_id('test', 'Sun', 'Jane Doe') == 'ext:test:jane-doe'


def test_exact_cjk_collection_identity_reused_only_when_unique(tmp_path, monkeypatch):
    ctx = member_context(tmp_path, monkeypatch, {'孙家广': [member('张三')]})
    people = [dict(id='known', name='张三')]
    stu = defaultdict(dict)
    students.researched(ctx, stu, students.people_by_family(people))
    assert set(stu['孙家广']) == {'known'}
    people.append(dict(id='namesake', name='张三'))
    stu = defaultdict(dict)
    students.researched(ctx, stu, students.people_by_family(people))
    assert all(sid.startswith('ext:test:') for sid in stu['孙家广'])


@pytest.mark.parametrize('role', ['postdoc', 'researcher', 'staff', 'engineer', 'assistant', 'visitor', 'visiting', 'faculty', 'member'])
def test_nonstudent_research_roles_are_memberships(tmp_path, monkeypatch, role):
    ctx = member_context(tmp_path, monkeypatch, {'孙家广': [member('张三', role)]})
    stu = defaultdict(dict)
    students.researched(ctx, stu, {})
    r = next(iter(stu['孙家广'].values()))
    assert r['roles'] == [role]
    assert r['relations'][0]['type'] == 'researched_membership'


def test_member_role_history_preserved(tmp_path, monkeypatch):
    ctx = member_context(tmp_path, monkeypatch, {'孙家广': [member('张三', 'phd'), member('张三', 'postdoc')]})
    stu = defaultdict(dict)
    students.researched(ctx, stu, {})
    r = next(iter(stu['孙家广'].values()))
    assert r['roles'] == ['phd', 'postdoc']
    assert [rel['type'] for rel in r['relations']] == ['researched_advising', 'researched_membership']
