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
    (tmp_path / 'roster-evidence.json').write_text(json.dumps([dict(pi='Example PI', students=rows)]))
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
