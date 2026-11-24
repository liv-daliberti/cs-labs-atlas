"""Reviewed group memberships preserve degree roles without inventing PI advising."""
from collections import Counter, defaultdict
import copy
import json
from types import SimpleNamespace

import pytest

from pihier import students


def run_rows(tmp_path, monkeypatch, rows):
    (tmp_path / 'roster-evidence.json').write_text(json.dumps([dict(pi='Professor Example', students=rows)]))
    monkeypatch.setattr(students.P, 'data', lambda fn, school=None, root=None: tmp_path / fn)
    monkeypatch.setattr(students, 'accepted_additions', lambda *args: [])
    ctx = SimpleNamespace(here=tmp_path, school='test', pis=[dict(pi='Professor Example')], ge={}, n=Counter())
    native = defaultdict(dict)
    students.researched(ctx, native, {})
    return list(native['Professor Example'].values())


def source_row(name, role, **extra):
    return dict(name=name, role=role, years=[2020, 2021], url='https://example.edu/group', sha256='a' * 64,
                quote=f'Group Members: {name} ({role})', **extra)


@pytest.mark.parametrize('role', ['phd', 'masters', 'undergraduate', 'student'])
def test_explicit_typed_group_membership_is_not_advising(tmp_path, monkeypatch, role):
    row = source_row('Jane Researcher', role, relationship='membership')
    native, = run_rows(tmp_path, monkeypatch, [row])
    assert native['roles'] == [role]
    relation, = native['relations']
    assert relation == dict(type='researched_membership', role=role, years=[2020, 2021],
                            sources=[dict(url=row['url'], sha256=row['sha256'], quote=row['quote'])])


def test_explicit_advising_and_membership_episodes_union_without_role_loss(tmp_path, monkeypatch):
    rows = [source_row('Jane Researcher', 'phd', relationship='advising'),
            source_row('Jane Researcher', 'masters', relationship='membership')]
    native, = run_rows(tmp_path, monkeypatch, rows)
    assert native['roles'] == ['phd', 'masters']
    assert [r['type'] for r in native['relations']] == ['researched_advising', 'researched_membership']


def test_composite_relationship_retains_separate_literal_source_fragments(tmp_path, monkeypatch):
    extra = dict(url='https://example.edu/cv', capture_url='https://web.archive.org/web/20200101id_/https://example.edu/cv',
                 sha256='b' * 64, quote='Jane Researcher, PhD 2020')
    degree = dict(url='https://example.edu/degree', sha256='c' * 64, quote='Johns Hopkins University')
    row = source_row('Jane Researcher', 'phd', relationship='advising', host_quote='Advisor: Professor Example',
                     corroborating_sources=[extra, degree, extra])
    unchanged = copy.deepcopy(row)
    native, = run_rows(tmp_path, monkeypatch, [row])
    relation, = native['relations']
    assert relation['type'] == 'researched_advising'
    assert relation['sources'] == [dict(url=row['url'], sha256=row['sha256'], quote=row['quote']),
                                   dict(url=row['url'], sha256=row['sha256'], quote=row['host_quote']),
                                   dict(url=extra['capture_url'], sha256=extra['sha256'], quote=extra['quote']), degree]
    assert row == unchanged


@pytest.mark.parametrize('extra', [None, {}, [None], [dict(url='file:///tmp/source', sha256='a' * 64, quote='Degree')],
                                  [dict(url='https://example.edu', sha256='not-a-hash', quote='Degree')],
                                  [dict(url='https://example.edu', sha256='a' * 64, quote=' ')]])
def test_invalid_composite_source_stops_relationship_admission(tmp_path, monkeypatch, extra):
    with pytest.raises(ValueError, match='invalid reviewed corroborating source'):
        run_rows(tmp_path, monkeypatch, [source_row('Jane Researcher', 'phd', corroborating_sources=extra)])


@pytest.mark.parametrize('bad', [None, '', 'member', 'researched_membership', 'Advising', False, 1, [], {}])
def test_invalid_present_selector_stops_native_admission(tmp_path, monkeypatch, bad):
    with pytest.raises(ValueError, match='invalid reviewed relationship'):
        run_rows(tmp_path, monkeypatch, [source_row('Jane Researcher', 'phd', relationship=bad)])


@pytest.mark.parametrize('role', ['visiting', 'visitor', 'postdoc', 'member', 'staff'])
def test_advising_cannot_override_nonstudent_or_visiting_guards(tmp_path, monkeypatch, role):
    with pytest.raises(ValueError, match='invalid reviewed relationship'):
        run_rows(tmp_path, monkeypatch, [source_row('Jane Researcher', role, relationship='advising')])


def test_advising_cannot_override_withheld_degree_role(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='invalid reviewed relationship'):
        run_rows(tmp_path, monkeypatch, [source_row('Jane Researcher', None, role_basis='withheld_mixed_heading',
                                                   relationship='advising')])


def test_omitted_selector_preserves_complete_legacy_objects(tmp_path, monkeypatch):
    rows = [source_row('Jane Doctoral', 'phd'), source_row('Jane Doctoral', 'masters'),
            source_row('Pat Visitor', 'visiting'), source_row('Alex Postdoc', 'postdoc'),
            source_row('Robin Member', None, role_basis='withheld_mixed_heading')]
    unchanged = copy.deepcopy(rows)
    records = run_rows(tmp_path, monkeypatch, rows)
    assert rows == unchanged
    expected_roles = [['phd', 'masters'], ['visiting'], ['postdoc'], ['member']]
    expected_types = [['researched_advising', 'researched_advising'], ['researched_membership'],
                      ['researched_membership'], ['researched_membership']]
    assert [r['roles'] for r in records] == expected_roles
    assert [[x['type'] for x in r['relations']] for r in records] == expected_types
    for record in records:
        assert set(record) == {'person', 'name', 'roles', 'relations'}
        for relation in record['relations']:
            row = next(r for r in rows if r['name'] == record['name'] and r['role'] == relation['role'])
            expected = dict(type=students.researched_relation_type(row['role'], row['role'] is None),
                            role=row['role'], years=[2020, 2021], sources=[dict(url=row['url'],
                            sha256=row['sha256'], quote=row['quote'])])
            if row['role'] is None:
                expected['role_withheld'] = True
            assert relation == expected


@pytest.mark.parametrize('kind', ['few-students-evidence', 'gap-evidence'])
def test_source_schema_accepts_only_explicit_relationship_enum(kind):
    from pathlib import Path
    import schema_check

    schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas' / f'{kind}.schema.json').read_text())
    for selector in ['membership', 'advising']:
        group = dict(pi='Professor Example', students=[source_row('Jane Researcher', 'phd', relationship=selector)])
        if kind == 'gap-evidence':
            group['status'] = 'pi'
        assert schema_check.validate([group], schema) == []
    for selector in [None, '', 'researched_membership', False, []]:
        group['students'][0]['relationship'] = selector
        assert any('relationship' in path for path, _ in schema_check.validate([group], schema))
