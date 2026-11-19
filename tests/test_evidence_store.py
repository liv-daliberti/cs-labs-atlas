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
    def fake_build(school, out, worktree=None, main=None, private=False):
        for d in (E.school_dir(school, out), E.shared_dir(out)):
            d.mkdir(parents=True)
        return out, 0
    monkeypatch.setattr(O, 'build', fake_build)
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


# ---------------------------------------------------------------- phase 2 (R3a): a store-sourced school


@pytest.fixture
def flagged_aa(root, tmp_path, monkeypatch):
    E.import_all(['aa', 'bb'], dest=tmp_path / 'st', root=root, log=lambda *_: None)
    monkeypatch.setattr(E, 'source_of', lambda s: 'store' if s == 'aa' else 'json')
    return tmp_path / 'st'


def test_charter_flag_defaults_to_json_and_michigan_is_store():
    import school_config as S
    assert S.evidence_source('oxford') == 'json'   # a school still on the JSON files
    assert S.evidence_source('princeton') == 'store' and S.evidence_shared('princeton') == 'store'
    assert S.evidence_source('michigan') == 'store'
    assert S.check('michigan') == []


def test_view_matches_then_a_direct_edit_is_refused(root, flagged_aa):
    assert E.check_view('aa', root, flagged_aa) == []
    f = root / 'hierarchy/aa/reviewed/census-additions.json'
    f.write_text(f.read_text().replace('Lecturer', 'Professor'))
    probs = E.check_view('aa', root, flagged_aa)
    assert len(probs) == 1 and 'census-additions.json' in probs[0] and 'evidence_store.py record' in probs[0]
    assert E.sync('aa', root, flagged_aa) == ['census-additions.json']   # the store wins: the view is regenerated
    assert E.check_view('aa', root, flagged_aa) == []


def test_unknown_reviewed_file_and_missing_file_are_reported(root, flagged_aa):
    (root / 'hierarchy/aa/reviewed/new-thing.json').write_text('[]\n')
    (root / 'hierarchy/aa/reviewed/hand.json').unlink()
    probs = ' '.join(E.check_view('aa', root, flagged_aa))
    assert 'new-thing.json' in probs and 'hand.json' in probs


def test_record_adds_to_a_list_and_a_map_and_supersedes(root, flagged_aa):
    e1 = E.record('aa', 'census-additions.json', {'name': 'New P', 'rank': 'Professor'}, source='https://x.edu/new', decided_by='w1', reviewed_by='r1', stores_dir=flagged_aa)
    e2 = E.record('aa', 'census-overrides-school.json', {'aliases': ['N. P']}, entry_key='New P', source='file:notes', decided_by='w1', stores_dir=flagged_aa)
    assert E.sync('aa', root, flagged_aa) == ['census-additions.json', 'census-overrides-school.json']
    adds = json.loads((root / 'hierarchy/aa/reviewed/census-additions.json').read_text())
    assert [x['name'] for x in adds] == ['Ann Lee', 'Zoë Ng', 'New P']
    assert json.loads((root / 'hierarchy/aa/reviewed/census-overrides-school.json').read_text())['New P'] == {'aliases': ['N. P']}
    e3 = E.record('aa', 'census-additions.json', {'name': 'New P', 'rank': 'Associate Professor'}, source='https://x.edu/new2', decided_by='w2', supersede=e1, stores_dir=flagged_aa)
    assert e3 == e1
    E.sync('aa', root, flagged_aa)
    assert json.loads((root / 'hierarchy/aa/reviewed/census-additions.json').read_text())[2]['rank'] == 'Associate Professor'
    assert E.check_view('aa', root, flagged_aa) == []
    with closing(sqlite3.connect(E.store_path('aa', flagged_aa))) as con:
        log = con.execute('SELECT evidence_id, action, decided_by, reviewed_by, source, old_record FROM write_log ORDER BY id').fetchall()
        row = con.execute('SELECT decided_by, reviewed_by, source_url, supersedes FROM evidence WHERE id = ?', (e1,)).fetchone()
    assert [x[:3] for x in log] == [(e1, 'add', 'w1'), (e2, 'add', 'w1'), (e1, 'supersede', 'w2')]
    assert log[2][5] == '{"name":"New P","rank":"Professor"}' and log[0][3] == 'r1'
    assert row[0] == 'w2' and row[3] == f'evidence:{e1}'


def test_record_refusals(root, flagged_aa):
    kw = dict(source='s', decided_by='w', stores_dir=flagged_aa)
    with pytest.raises(E.SourceOfTruth, match='not store-sourced'):
        E.record('bb', 'census-additions.json', {'name': 'x'}, **kw)
    with pytest.raises(E.SourceOfTruth, match='--source and --decided-by'):
        E.record('aa', 'census-additions.json', {'name': 'x'}, source='', decided_by='w', stores_dir=flagged_aa)
    with pytest.raises(E.SourceOfTruth, match='no layer'):
        E.record('aa', 'nope.json', {}, **kw)
    with pytest.raises(E.SourceOfTruth, match='entry-key'):
        E.record('aa', 'census-overrides-school.json', {'x': 1}, **kw)
    with pytest.raises(E.SourceOfTruth, match='exists'):
        E.record('aa', 'census-overrides-school.json', {'x': 1}, entry_key='Ann Lee', **kw)
    with pytest.raises(E.SourceOfTruth, match='no --entry-key'):
        E.record('aa', 'census-additions.json', {'x': 1}, entry_key='k', **kw)
    assert E.check_view('aa', root, flagged_aa) == []   # a refused write changed nothing


def test_import_never_overwrites_a_store_sourced_store(root, flagged_aa, tmp_path):
    with pytest.raises(E.SourceOfTruth, match='erase'):
        E.import_all(['aa'], dest=flagged_aa, root=root, log=lambda *_: None)
    E.import_all(['bb'], dest=flagged_aa, root=root, log=lambda *_: None)   # a json-sourced school is still a fresh snapshot


def test_overlay_of_a_store_sourced_school_takes_only_its_own_files_from_the_store(root, flagged_aa, tmp_path, monkeypatch):
    import overlay_root as O
    monkeypatch.setattr(O, 'build', lambda school, out, **kw: [d.mkdir(parents=True, exist_ok=True) for d in (E.school_dir(school, out), E.shared_dir(out))])
    E.record('aa', 'census-additions.json', {'name': 'New P'}, source='s', decided_by='w', stores_dir=flagged_aa)
    n = E.overlay('aa', tmp_path / 'ov', flagged_aa, root)
    assert n > 0 and not list(E.shared_dir(tmp_path / 'ov').glob('*.json'))
    assert 'New P' in (E.school_dir('aa', tmp_path / 'ov') / 'census-additions.json').read_text()


def test_backup_verifies_prunes_and_restores(root, flagged_aa, tmp_path):
    bk = tmp_path / 'bk'
    for i in range(4):   # stamps are per second: make them distinct by hand
        d = bk / f'2026111{i}T000000Z'
        E.backup_one('aa', d, flagged_aa)
        (d / 'SHA256SUMS').write_text(f'{E.hashlib.sha256((d / "aa-evidence.sqlite").read_bytes()).hexdigest()}  aa-evidence.sqlite\n')
    assert len(E.backups_of('aa', bk)) == 4
    assert E.prune_backups('aa', 2, bk) == 2
    assert [s for s, _ in E.backups_of('aa', bk)] == ['20261112T000000Z', '20261113T000000Z'] and not (bk / '20261110T000000Z').exists()
    done = E.backup(['aa'], flagged_aa, bk, keep=3, log=lambda *_: None)
    assert len(E.backups_of('aa', bk)) == 3 and len(done['aa']) == 64
    newest = E.backups_of('aa', bk)[-1][1]
    # a decision recorded after the backup is lost by a restore unless forced; the live file is kept aside
    E.record('aa', 'census-additions.json', {'name': 'Later P'}, source='s', decided_by='w', stores_dir=flagged_aa)
    with pytest.raises(E.SourceOfTruth, match='loses 1'):
        E.restore('aa', newest, flagged_aa, log=lambda *_: None)
    E.restore('aa', newest, flagged_aa, force=True, log=lambda *_: None)
    assert list(E.store_path('aa', flagged_aa).parent.glob('evidence.sqlite.pre-restore-*'))
    assert 'Later P' not in json.dumps(E.rendered('aa', flagged_aa))
    newest.write_bytes(newest.read_bytes() + b'x')   # a corrupted backup is refused
    with pytest.raises(RuntimeError, match='sha256 differs'):
        E.restore('aa', newest, flagged_aa, force=True, log=lambda *_: None)


def test_backup_loop_skips_a_recent_backup(root, flagged_aa, tmp_path, monkeypatch):
    bk = tmp_path / 'bk'
    monkeypatch.setattr(E, 'flagged', lambda schools=None: ['aa'])
    out = []
    E.backup_loop(flagged_aa, bk, every_h=24, once=True, log=out.append)
    E.backup_loop(flagged_aa, bk, every_h=24, once=True, log=out.append)
    assert len(E.backups_of('aa', bk)) == 1 and 'backed_up' in out[0] and out[1:] == []


def test_shared_slice_patch_is_byte_identical_and_touches_only_the_school(root, flagged_aa, monkeypatch):
    assert E.adopt_shared('aa', root, flagged_aa, log=lambda *_: None) == 2   # census-overrides (aa section: 1 person) + student-corrections (1 item)
    monkeypatch.setattr(E, 'shared_of', lambda s: 'store' if s == 'aa' else 'json')
    with pytest.raises(E.SourceOfTruth, match='already'):
        E.adopt_shared('aa', root, flagged_aa, log=lambda *_: None)
    assert E.check_view('aa', root, flagged_aa) == []
    before = {f.name: f.read_bytes() for f in E.shared_dir(root).glob('*.json')}
    assert E.sync_shared('aa', root, flagged_aa) == [] and {f.name: f.read_bytes() for f in E.shared_dir(root).glob('*.json')} == before
    # another school's rows in the shared files stay editable: no complaint
    sc = E.shared_dir(root) / 'student-corrections.json'
    sc.write_text(sc.read_text().replace('"drop"', '"keep"'))
    assert E.check_view('aa', root, flagged_aa) == []
    # a direct edit of aa's own slice is reported
    co = E.shared_dir(root) / 'census-overrides.json'
    co.write_text(co.read_text().replace('"x"', '"y"'))
    assert 'census-overrides.json' in ' '.join(E.check_view('aa', root, flagged_aa))
    assert E.sync_shared('aa', root, flagged_aa) == ['census-overrides.json'] and E.check_view('aa', root, flagged_aa) == []
    # recorded decisions land in aa's slice only, in place / after its last item
    E.record('aa', 'student-corrections.json', {'school': 'aa', 'pi': 'R', 'student': 'u', 'action': 'drop'}, shared=True, source='s', decided_by='w', stores_dir=flagged_aa)
    E.record('aa', 'census-overrides.json', {'aliases': ['N']}, shared=True, entry_key='aa', sub_key='New P', source='s', decided_by='w', stores_dir=flagged_aa)
    assert len(E.check_view('aa', root, flagged_aa)) == 2
    assert sorted(E.sync_shared('aa', root, flagged_aa)) == ['census-overrides.json', 'student-corrections.json']
    items = json.loads(sc.read_text())
    assert [(x['school'], x['student']) for x in items] == [('bb', 's'), ('aa', 't'), ('aa', 'u')] and items[0]['action'] == 'keep'   # bb's edit survives
    assert json.loads(co.read_text())['aa']['New P'] == {'aliases': ['N']} and json.loads(co.read_text())['bb'] == {'Kim': {'is_pi': False}}
    assert E.check_view('aa', root, flagged_aa) == []
    with pytest.raises(E.SourceOfTruth, match='not store-sourced'):
        E.record('bb', 'student-corrections.json', {'school': 'bb'}, shared=True, source='s', decided_by='w', stores_dir=flagged_aa)


def test_unmanaged_files_stay_outside_the_store_and_the_guard(root, tmp_path, monkeypatch):
    monkeypatch.setattr(E, 'source_of', lambda s: 'store' if s == 'aa' else 'json')
    monkeypatch.setattr(E.S, 'evidence_unmanaged', lambda s: ['hand.*', 'recall-*.json'] if s == 'aa' else [], raising=False)
    put(root / 'hierarchy/aa/reviewed/recall-check.json', {'rows': [{'name': 'x'}]})
    E.import_all(['aa', 'bb'], dest=tmp_path / 'st', root=root, log=lambda *_: None)
    assert 'recall-check.json' not in E.rendered('aa', tmp_path / 'st') and 'hand.json' not in E.rendered('aa', tmp_path / 'st')
    f = root / 'hierarchy/aa/reviewed/recall-check.json'
    f.write_text('[]\n')   # a tool regenerates it: no complaint
    assert E.check_view('aa', root, tmp_path / 'st') == []
    assert E.is_unmanaged('aa', 'recall-check.json') and not E.is_unmanaged('aa', 'census-additions.json')


def test_add_layer_then_record_sync_check_and_a_second_add_is_refused(root, flagged_aa):
    st = flagged_aa
    skel = {'school': 'aa', 'against_release': '2026-11-07'}
    E.add_layer('aa', 'release-corrections.json', key='classes', skeleton=skel, stores_dir=st, root=root)
    with pytest.raises(E.SourceOfTruth, match='already exists'):
        E.add_layer('aa', 'release-corrections.json', key='classes', skeleton=skel, stores_dir=st, root=root)
    assert E.sync('aa', root, st) == ['release-corrections.json']
    f = root / 'hierarchy' / 'aa' / 'reviewed' / 'release-corrections.json'
    assert json.loads(f.read_text()) == {'school': 'aa', 'against_release': '2026-11-07', 'classes': []}
    assert E.check_view('aa', root, st) == []
    cls = {'id': 'not_paper_rule', 'rule': 'R-PAP-17', 'rows': [{'pi': 'Ann Lee', 'oa': 'https://openalex.org/W1'}]}
    E.record('aa', 'release-corrections.json', cls, source='scratch/x.json', decided_by='t', stores_dir=st)
    assert E.sync('aa', root, st) == ['release-corrections.json']
    assert json.loads(f.read_text())['classes'] == [cls] and E.check_view('aa', root, st) == []
    f.write_text('{}\n')
    assert E.check_view('aa', root, st)      # a direct edit is refused
    E.sync('aa', root, st)
    E.add_layer('aa', 'roots.json', stores_dir=st, root=root)   # a root-list layer
    E.record('aa', 'roots.json', {'a': 1}, source='s', decided_by='t', stores_dir=st)
    E.sync('aa', root, st)
    assert json.loads((root / 'hierarchy' / 'aa' / 'reviewed' / 'roots.json').read_text()) == [{'a': 1}]
    with pytest.raises(E.SourceOfTruth, match='not store-sourced'):
        E.add_layer('bb', 'x.json', stores_dir=st, root=root)
