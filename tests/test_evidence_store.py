"""Evidence store phase 1: the reviewed files go into per-school SQLite stores and come back identical (docs/EVIDENCE-STORE.md)."""
import json
import sqlite3
from contextlib import closing

import pytest

import evidence_store as E


def put(path, doc, **kw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(E.dumps(doc, dict(indent=1, ascii=False, compact=False, sort=False, newline=True, **kw)))


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(E.S, 'keys', lambda: ['aa', 'bb'])
    r = tmp_path / 'code'
    h = r / 'hierarchy'
    put(h / 'aa' / 'reviewed' / 'census-additions.json', [{'name': 'Ann Lee', 'rank': 'Professor', 'sources': ['https://x.edu/p'], 'is_pi': True}, {'name': 'Zoë Ng', 'rank': 'Lecturer'}])
    put(h / 'aa' / 'reviewed' / 'census-overrides-school.json', {'Ann Lee': {'aliases': ['A. Lee'], 'dblp': '1/2'}, 'Bo Ray': {'no_identity': True, 'why_no_identity': 'two people'}})
    put(h / 'aa' / 'reviewed' / 'cs-related-review.json', {'school': 'aa', 'counts': {'x': 1}, 'decisions': [
        {'name': 'C D', 'decision': 'excluded_unresolved', 'reason': 'no source covers 2019', 'reason_code': 'no_source_covers_window', 'sources_tried': ['u1']},
        {'name': 'E F', 'decision': 'accepted', 'source': 'https://x.edu/f', 'reviewed_by': 'rv'}]})
    put(h / 'aa' / 'reviewed' / 'labpage-additions.json', {'school': 'aa', 'students': [{'name': 's1', 'pi': 'Ann Lee'}], 'papers': [{'title': 't', 'pi': 'Ann Lee'}]})
    put(h / 'aa' / 'reviewed' / 'host-alias-rule.json', {'school': 'aa', 'rule': 'text', 'sets': [['a', 'b']]})
    put(h / 'bb' / 'reviewed' / 'census-additions.json', [])
    put(h / 'bb' / 'reviewed' / 'student-decisions.json', {'Kim': {'decision': 'drop'}})
    (h / 'aa' / 'reviewed' / 'hand.json').write_text('{\n "school": "aa",\n "records": [{"name": "H", "x": [1, 2]}]\n}\n')   # hand-formatted
    (h / 'aa' / 'reviewed' / 'dup.json').write_text('{"a": 1, "a": 2}')
    (h / 'aa' / 'reviewed' / 'broken.json').write_text('{"a": ')
    put(h / 'reviewed' / 'census-overrides.json', {'_note': 'n', 'aa': {'Ann Lee': {'aliases': ['x']}}, 'bb': {'Kim': {'is_pi': False}}})
    put(h / 'reviewed' / 'student-corrections.json', [{'school': 'bb', 'pi': 'P', 'student': 's', 'action': 'drop'}, {'school': 'aa', 'pi': 'Q', 'student': 't', 'action': 'rename'}])
    put(h / 'reviewed' / 'cs-venues.json', [{'name': 'V', 'works': 3}])
    put(h / 'reviewed' / 'status-packages.json', {'version': 1, 'packages': {'p': {'n': 1}}})
    return r


def stores(tmp_path, schools):
    return [E.store_path(s, tmp_path / 'st') for s in list(schools) + [E.SHARED]]


def test_round_trip_every_file(root, tmp_path):
    rep = E.import_all(['aa', 'bb'], dest=tmp_path / 'st', root=root, log=lambda *_: None)
    E.export_files(stores(tmp_path, ['aa', 'bb']), tmp_path / 'out')
    res = E.compare(root, tmp_path / 'out', ['aa', 'bb'])
    assert res['diff'] == [] and res['missing'] == [] and res['canonical'] == []
    assert {u['file'] for u in rep['unrepresentable']} == {'dup.json', 'broken.json'}   # kept verbatim, named in the report


def test_hand_formatting_survives_until_the_rows_change(root, tmp_path):
    E.import_all(['aa', 'bb'], dest=tmp_path / 'st', root=root, log=lambda *_: None)
    lay = E.load_layers(stores(tmp_path, ['aa']))
    assert lay['hand.json']['style'] is None and E.render(lay['hand.json']) == (root / 'hierarchy/aa/reviewed/hand.json').read_text()
    lay['hand.json']['rows'][0][4]['name'] = 'changed'
    assert E.render(lay['hand.json']) != lay['hand.json']['layout'] and json.loads(E.render(lay['hand.json']))['records'][0]['name'] == 'changed'


def test_claim_columns(root, tmp_path):
    E.import_all(['aa', 'bb'], dest=tmp_path / 'st', root=root, log=lambda *_: None)
    with closing(sqlite3.connect(E.store_path('aa', tmp_path / 'st'))) as con:
        kinds = dict(con.execute("SELECT person_key, claim_kind FROM evidence WHERE school='aa'"))
        assert kinds['C D'] == 'excluded_unresolved' and kinds['E F'] == 'cs_related' and kinds['Bo Ray'] == 'hold'
        v = json.loads(con.execute("SELECT value FROM evidence WHERE person_key='C D'").fetchone()[0])
        assert v['reason_code'] == 'no_source_covers_window' and v['sources_tried'] == ['u1']
        assert con.execute("SELECT source_url, reviewed_by FROM evidence WHERE person_key='E F'").fetchone() == ('https://x.edu/f', 'rv')
        # a shared file is split over the school stores
        assert con.execute("SELECT COUNT(*) FROM evidence WHERE layer_id=(SELECT layer_id FROM layer WHERE name='student-corrections.json')").fetchone()[0] == 1
    with closing(sqlite3.connect(E.store_path(E.SHARED, tmp_path / 'st'))) as con:
        assert con.execute("SELECT COUNT(*) FROM evidence WHERE school='_shared'").fetchone()[0] == 2   # cs-venues row + the packages map


def test_partial_import_does_not_claim_the_shared_files(root, tmp_path):
    res = E.verify(['aa'], root)
    assert res['diff'] == [] and res['missing'] == []


def test_overlay_source_files_are_the_exported_ones(root, tmp_path, monkeypatch):
    E.import_all(['aa', 'bb'], dest=tmp_path / 'st', root=root, log=lambda *_: None)
    out = tmp_path / 'ov'
    import overlay_root as O
    monkeypatch.setattr(O, 'build', lambda school, out, worktree=None, main=None, private=False: (
        [(out / 'hierarchy' / school / 'reviewed').mkdir(parents=True), (out / 'hierarchy' / 'reviewed').mkdir(parents=True)], 0)[1])
    n = E.overlay('aa', out, tmp_path / 'st', root=root)
    assert n and (out / 'hierarchy/aa/reviewed/census-additions.json').read_bytes() == (root / 'hierarchy/aa/reviewed/census-additions.json').read_bytes()
    assert (out / 'hierarchy/reviewed/census-overrides.json').read_bytes() == (root / 'hierarchy/reviewed/census-overrides.json').read_bytes()


def test_schema_file_matches_the_tables(tmp_path):
    con = sqlite3.connect(':memory:')
    E.create(con)
    cols = {r[1] for r in con.execute('PRAGMA table_info(evidence)')}
    schema = json.loads((E.SQL.parent / 'evidence-row.schema.json').read_text())
    assert set(schema['required']) - {'layer'} <= cols
    assert 'excluded_unresolved' in schema['properties']['claim_kind']['enum']
