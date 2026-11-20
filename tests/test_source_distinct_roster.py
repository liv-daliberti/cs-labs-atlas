"""Source-distinct homonyms remain separate until their identity is reviewed."""
from collections import Counter, defaultdict
import json
from types import SimpleNamespace

import pytest

from pihier import links, students


def load_rows(tmp_path, monkeypatch, keys):
    rows = [dict(name='Ziyu Chen', role='student', relationship='membership', years=[2026],
                 url='https://example.edu/team', sha256='a' * 64, quote='Ziyu Chen',
                 source_record_key=key) for key in keys]
    (tmp_path / 'group-source-evidence.json').write_text(json.dumps([dict(pi='Example PI', students=rows)]))
    monkeypatch.setattr(students.P, 'data', lambda fn, school=None, root=None: tmp_path / fn)
    monkeypatch.setattr(students, 'accepted_additions', lambda *args: [])
    ctx = SimpleNamespace(here=tmp_path, school='example', pis=[dict(pi='Example PI')],
                          ge={}, n=Counter(), initials_merges=[])
    native = defaultdict(dict)
    students.researched(ctx, native, {'chen': [dict(id='collection-person', name='Ziyu Chen')]})
    return ctx, native


def test_homonyms_do_not_borrow_collection_identity_or_merge(tmp_path, monkeypatch):
    ctx, native = load_rows(tmp_path, monkeypatch, ['doctoral-profile', 'masters-profile'])
    assert len(native['Example PI']) == 2
    assert 'collection-person' not in native['Example PI']
    assert students.merge_within_lab(ctx, native) == 0
    assert {s['sourceRecordKey'] for s in native['Example PI'].values()} == {'doctoral-profile', 'masters-profile'}


def test_repeated_same_source_unions_evidence(tmp_path, monkeypatch):
    ctx, native = load_rows(tmp_path, monkeypatch, ['doctoral-profile', 'doctoral-profile'])
    assert len(native['Example PI']) == 1
    assert len(next(iter(native['Example PI'].values()))['relations']) == 2
    assert students.merge_within_lab(ctx, native) == 0


@pytest.mark.parametrize('keys', [['doctoral-profile', 'masters-profile'], ['unresolved-profile']])
def test_unresolved_source_identity_never_borrows_name_only_authorship(tmp_path, monkeypatch, keys):
    ctx, native = load_rows(tmp_path, monkeypatch, keys)
    ctx.stu, ctx.pls = native, defaultdict(list)
    ctx.rows = [dict(pi='Example PI', work='work-1', oa='W1', year=2026,
                     byline=['Example PI', 'Ziyu Chen'], _bylines=[(['Example PI', 'Ziyu Chen'], ['Ziyu Chen'])])]
    links.link_students(ctx)
    assert ctx.sp == []


def test_source_identity_does_not_change_legacy_ids():
    assert students.external_member_id('example', 'PI', 'Jane Doe') == 'ext:example:jane-doe'
    assert not students.compatible_source_records({'sourceRecordKey': 'one'}, {})
    assert not students.compatible_source_records({'sourceRecordKey': 'one'}, {'sourceRecordKey': 'two'})


@pytest.mark.parametrize('key', ['', 0, [], False])
def test_invalid_source_key_refuses_identity(key):
    with pytest.raises(ValueError, match='source_record_key'):
        students.external_member_id('example', 'PI', 'Jane Doe', key)


def held_row(**changes):
    return dict(name='Unresolved Student', reason='Historical roster gives no membership dates.',
                url='https://example.edu/alumni', sha256='b' * 64,
                quote='Former members: Unresolved Student', **changes)


def test_held_roster_observations_remain_source_records_without_people_or_links(tmp_path, monkeypatch):
    row = held_row(source_record_id='one')
    (tmp_path / 'group-source-evidence.json').write_text(json.dumps([dict(pi='Example PI', students=[],
        unresolved_students=[row, row, held_row(source_record_id='two')])]))
    monkeypatch.setattr(students.P, 'data', lambda fn, school=None, root=None: tmp_path / fn)
    monkeypatch.setattr(students, 'accepted_additions', lambda *args: [])
    ctx = SimpleNamespace(here=tmp_path, school='example', pis=[dict(pi='Example PI'), dict(pi='Other PI')],
                          ge={}, n=Counter(), initials_merges=[])
    native = defaultdict(dict)
    students.researched(ctx, native, {'student': [dict(id='known-person', name='Unresolved Student')]})
    observations = ctx.pis[0]['unresolvedRosterObservations']
    assert len(observations) == 2
    assert all(row['status'] == 'unresolved' for row in observations)
    assert 'unresolvedRosterObservations' not in ctx.pis[1]
    assert not any(native.values())
    ctx.stu, ctx.pls = native, defaultdict(list)
    ctx.rows = [dict(pi='Example PI', work='work-1', oa='W1', year=2026,
                     byline=['Example PI', 'Unresolved Student'], _bylines=[(['Unresolved Student'], ['Unresolved Student'])])]
    links.link_students(ctx)
    assert ctx.sp == []
    assert not any(native.values())


@pytest.mark.parametrize('changes', [dict(reason=''), dict(quote=None), dict(sha256='bad'),
    dict(url='javascript:alert(1)'), dict(person='existing-person'), dict(years=[2026]),
    dict(relationship='advising'), dict(status='accepted')])
def test_held_source_cannot_smuggle_accepted_claims_or_missing_evidence(changes):
    row = held_row()
    row.update(changes)
    with pytest.raises(ValueError, match='unresolved roster'):
        students.unresolved_roster_observations(dict(unresolved_students=[row]))


def test_unresolved_field_is_optional_and_explicit():
    assert students.unresolved_roster_observations({}) == []
    assert students.unresolved_roster_observations(dict(unresolved_students=[])) == []
    with pytest.raises(ValueError, match='must be a list'):
        students.unresolved_roster_observations(dict(unresolved_students='names'))


def test_pi_schema_preserves_held_evidence_but_rejects_accepted_identity_fields():
    from pathlib import Path
    import schema_check

    document = json.loads((Path(__file__).parents[1] / 'schemas/pis.schema.json').read_text())
    schema = document['$defs']['pi']['properties']['unresolvedRosterObservations']
    rows = students.unresolved_roster_observations(dict(unresolved_students=[held_row()]))
    assert schema_check.validate(rows, schema) == []
    rows[0]['person'] = 'existing-person'
    assert schema_check.validate(rows, schema)
