"""Per-PI release (D-0001, tools/pi_release.py): who is included, the filtered package, the monotone check, the subset-bound accuracy sample."""
import gzip
import json

import pytest

import pi_release as PR
import pi_states as PS
import stage_gate as SG


def write_pkg(d, pis, with_ids=True):
    d.mkdir(parents=True, exist_ok=True)
    rows = [dict(pi=p, **(dict(atlasId=f'atl:p:{p}', labId=f'atl:l:x:{p}') if with_ids else {})) for p in pis]
    (d / 'pis.json').write_text(json.dumps(rows))
    (d / 'students.json').write_text(json.dumps({p: [dict(person=f'ext:{p}-s', atlasId=f'atl:p:{p}s')] for p in pis}))
    with gzip.open(d / 'lab_papers.jsonl.gz', 'wt') as f:
        for p in pis:
            f.write(json.dumps(dict(pi=p, oa=f'W{p}', atlasWorkId=f'atl:w:{p}', authorship={}, work=None)) + '\n')
    with gzip.open(d / 'student_papers.jsonl.gz', 'wt') as f:
        for p in pis:
            f.write(json.dumps(dict(pi=p, student=f'ext:{p}-s', oa=f'W{p}', studentAtlasId=f'atl:p:{p}s', atlasWorkId=f'atl:w:{p}')) + '\n')
    (d / 'copies.json').write_text(json.dumps(dict(summary={'n': 1}, papers={f'W{p}': {'status': 'downloaded'} for p in pis})))


@pytest.fixture
def world(tmp_path, monkeypatch):
    new, rel = tmp_path / 'new', tmp_path / 'rel'
    monkeypatch.setattr(PR, 'package_dir', lambda key, base=None: new if base is None else base / 'hierarchy' / key)  # route-ok
    write_pkg(new, ['A', 'B', 'C'])
    write_pkg(rel / 'hierarchy' / 'x', ['A', 'B'])  # route-ok
    states = lambda open_: dict(open_pis=sorted(open_), school_items={'6': ['acceptance']},
                                pis={p: {s: dict(state='open' if p in open_ else 'done', reasons=[f'r-{p}']) for s in PS.ALL} for p in 'ABC'})
    return new, rel, states


def test_open_pi_is_held_with_its_reason_and_done_pis_are_included(world):
    _, rel, states = world
    pl = PR.plan('x', states({'C'}), published=rel)
    assert pl['included'] == ['A', 'B'] and list(pl['held']) == ['C'] and pl['partial'] and pl['held']['C'][0].startswith('stage census: r-C')
    st = PR.scope_statement(pl)
    assert (st['status'], st['pis_total'], st['pis_included'], st['pis_held']) == ('partial', 3, 2, 1) and st['held'][0]['pi'] == 'C'
    assert pl['school_items'] == {'6': ['acceptance']}       # reported, holds nobody
    assert 'C: stage census' in PR.render_notes([st])


def test_published_pi_that_is_open_now_is_carried_not_dropped(world):
    _, rel, states = world
    pl = PR.plan('x', states({'A', 'C'}), published=rel)
    assert pl['included'] == ['A', 'B'] and pl['carried'] == ['A'] and list(pl['held']) == ['C']


def test_nothing_held_is_complete(world):
    _, rel, states = world
    pl = PR.plan('x', states(set()), published=rel)
    assert not pl['partial'] and PR.scope_statement(pl)['status'] == 'complete'


def test_filter_keeps_only_included_rows_and_copies(world):
    _, _, _ = world
    assert [p['pi'] for p in PR.filtered_rows_and_json('x', 'pis.json', ['A'])] == ['A']
    assert list(PR.filtered_rows_and_json('x', 'students.json', ['A', 'C'])) == ['A', 'C']
    assert {r['pi'] for r in PR.filtered_rows_and_json('x', 'student_papers.jsonl.gz', ['B'])} == {'B'}
    assert list(PR.filtered_rows_and_json('x', 'copies.json', ['B'])['papers']) == ['WB']
    assert PR.filtered_bytes('x', 'lab_papers.jsonl.gz', ['A']) == PR.filtered_bytes('x', 'lab_papers.jsonl.gz', ['A'])   # deterministic
    h = PR.package_hashes('x', ['A', 'B'])
    assert set(h) == set(PR.PACKAGE) and h != PR.package_hashes('x', ['A'])


def test_monotone_check_flags_a_removal_and_not_an_addition(world):
    _, rel, _ = world
    ok = PR.compare('x', ['A', 'B', 'C'], rel)
    assert ok['flags'] == 0 and ok['basis'] == 'atlas ids' and ok['kinds']['pi']['added'] == 1
    gone = PR.compare('x', ['A', 'C'], rel)                    # B was published
    assert gone['flags'] == 5 and gone['kinds']['pi']['n_removed'] == 1 and gone['kinds']['lab_paper']['n_removed'] == 1
    assert PR.compare('y', ['A'], rel) == dict(school='y', compared=False, flags=0)


def test_monotone_falls_back_to_legacy_keys_without_ids(world, tmp_path):
    new, rel, _ = world
    write_pkg(new, ['A', 'B', 'C'], with_ids=False)
    r = PR.compare('x', ['A', 'B'], rel)
    assert r['basis'].startswith('legacy') and r['flags'] == 0
    assert PR.compare('x', ['A'], rel)['flags'] > 0


def test_g9_binds_a_subset_summary_to_the_included_pis(world, monkeypatch):
    _, rel, states = world
    inc = ['A', 'B']
    sha = PR.plan('x', states({'C'}), published=rel)['included_sha']
    summ = {k: dict(p=0.99) for k, _ in SG.ACCURACY_BARS}
    summ['subset'] = dict(pis=inc, n_pis=2, included_sha=sha, files=PR.package_hashes('x', inc))
    monkeypatch.setattr(SG, 'read', lambda p, default=None: summ)
    monkeypatch.setattr(PR, 'plan', lambda key, **k: dict(included=inc, included_sha=sha))
    assert SG.g9('x')[0] == []
    summ['subset']['included_sha'] = 'stale'                    # a PI was added or lost since the draw
    assert any('included PIs changed' in b for b in SG.g9('x')[0])
    summ['subset']['included_sha'] = sha
    summ['subset']['files'] = dict(summ['subset']['files'], **{'pis.json': '0' * 64})   # their content changed since the draw
    assert any('content changed' in b for b in SG.g9('x')[0])


def test_sample_with_only_pis_draws_only_from_them(world, monkeypatch, tmp_path):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('accuracy_sample_pi', Path(__file__).resolve().parents[1] / 'accuracy' / 'sample.py')
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    new, _, _ = world
    monkeypatch.setattr(S.P, 'SchoolDir', lambda school: new)
    monkeypatch.setattr(S, 'dblp_persons', lambda wanted, school=None: {})
    out = S.main(['x'], tmp_path / 's.json', cfg=dict(S.ROUNDS['pi1']), only_pis=['A', 'B'])
    sc = out['schools']['x']
    assert sc['n_lab_papers'] == 2 and sc['n_student_papers'] == 2
    assert all(r['key'].split('|')[0] in ('A', 'B') for r in sc['lab_precision'] + sc['student_precision'])
    assert out['subset']['x']['pis'] == ['A', 'B'] and out['subset']['x']['files'] == PR.package_hashes('x', ['A', 'B'])
    full = S.main(['x'], tmp_path / 't.json', cfg=dict(S.ROUNDS['pi1']))
    assert 'subset' not in full and full['schools']['x']['n_lab_papers'] == 3     # without only_pis the draw is the school-wide one


def test_recorded_corrections_are_counted_not_flagged(world):
    """Q-0339: removals an owner rule explains sit in the school's release-corrections record; a student link follows its lab paper; the rest still flag."""
    _, rel, _ = world
    rec = dict(against_release=rel.name, decided='2026-11-18', classes=[dict(id='ctrn_excluded', rule='charter openalex_excluded (D3)', rows=[dict(pi='B', oa='WB', labId='atl:l:x:B', atlasWorkId='atl:w:B')])])
    gone = PR.compare('x', ['A', 'C'], rel, corrections=rec)           # B (a PI) is gone too: only its lab paper and student link are explained
    assert gone['corrected'] == {'lab_paper:ctrn_excluded': 1, 'student_paper:ctrn_excluded': 1}
    assert gone['kinds']['lab_paper']['n_removed'] == 0 and gone['kinds']['student_paper']['n_removed'] == 0
    assert gone['kinds']['pi']['n_removed'] == 1 and gone['flags'] == 3   # PI, lab, student stay flagged
    assert gone['corrections_record']['classes'] == {'ctrn_excluded': dict(rule='charter openalex_excluded (D3)', rows=1)}
    kept = PR.compare('x', ['A', 'B', 'C'], rel, corrections=rec)      # restored: nothing removed, the row is reported unused
    assert kept['flags'] == 0 and kept['corrected'] == {} and kept['corrections_unused'] == 1


def test_a_recorded_link_class_explains_a_dropped_link_not_the_paper(world):
    """A class with `links` (7c8fdedd postdoc guard) explains a removed student-paper link whose lab paper stays; a link not listed still flags."""
    new, rel, _ = world
    rows = [json.loads(l) for l in gzip.open(new / 'student_papers.jsonl.gz', 'rt')]
    with gzip.open(new / 'student_papers.jsonl.gz', 'wt') as f:    # the link of C is gone, its paper stays
        for r in rows:
            if r['pi'] != 'A':
                f.write(json.dumps(r) + '\n')
    rec = dict(against_release=rel.name, classes=[dict(id='postdoc_role_guard_7c8fdedd', rule='7c8fdedd', rows=[],
               links=[dict(pi='A', student='ext:A-s', oa='WA', labId='atl:l:x:A', studentAtlasId='atl:p:As', atlasWorkId='atl:w:A')])])
    ok = PR.compare('x', ['A', 'B', 'C'], rel, corrections=rec)
    assert ok['kinds']['student_paper']['n_removed'] == 0 and ok['corrected'] == {'student_paper:postdoc_role_guard_7c8fdedd': 1}
    assert PR.compare('x', ['A', 'B', 'C'], rel, corrections=dict(rec, classes=[]))['kinds']['student_paper']['n_removed'] == 1


def test_a_record_written_against_another_release_is_ignored(world, tmp_path, monkeypatch):
    _, rel, _ = world
    import atlas_paths as P
    f = tmp_path / 'rc.json'
    f.write_text(json.dumps(dict(against_release='2026-01-01', classes=[])))
    monkeypatch.setattr(P, 'data', lambda name, school=None, **kw: f)
    assert PR.load_corrections('x', rel) is None
    f.write_text(json.dumps(dict(against_release=rel.name, classes=[])))
    assert PR.load_corrections('x', rel)['against_release'] == rel.name


def test_a_renamed_open_pi_is_carried_by_atlas_id(world, monkeypatch):
    """A published PI that an alias merge renamed keeps its atlas id; if it is open now it is still carried (published rows never disappear)."""
    new, rel, states = world
    rows = json.loads((new / 'pis.json').read_text())
    for r in rows:
        if r['pi'] == 'B':
            r['pi'] = 'B2'; r['atlasId'] = 'atl:p:B'
    (new / 'pis.json').write_text(json.dumps(rows))
    st = states({'B2'}); st['pis']['B2'] = st['pis']['B']
    pl = PR.plan('x', res=st, published=rel)
    assert 'B2' in pl['carried'] and 'B2' in pl['included']


def test_a_recorded_student_class_and_pi_rename_explain_legacy_removals(world):
    """pi_renames maps a census-renamed PI onto its current spelling (pre-id keys); a `students` class explains a removed student and its links."""
    new, rel, _ = world
    write_pkg(new, ['A', 'B2', 'C'], with_ids=False)
    write_pkg(rel / 'hierarchy' / 'x', ['A', 'B'], with_ids=False)  # route-ok
    plain = PR.compare('x', ['A', 'B2', 'C'], rel, corrections=dict(against_release=rel.name, classes=[]))
    assert plain['kinds']['pi']['n_removed'] == 1
    rec = dict(against_release=rel.name, pi_renames={'B': 'B2'}, classes=[])
    assert PR.compare('x', ['A', 'B2', 'C'], rel, corrections=rec)['kinds']['pi']['n_removed'] == 0
    gone = PR.compare('x', ['A', 'C'], rel, corrections=dict(rec, classes=[dict(id='st', rule='r', rows=[], students=[dict(pi='B', student='ext:B-s')])]))
    assert gone['kinds']['student']['n_removed'] == 0 and gone['corrected'].get('student:st') == 1


def test_held_links_leave_the_package_unless_published_and_do_not_count_as_removals(world):
    """D-0017: a held link (student with no linked paper) is dropped from the filtered package; one the published release carried is never held (D-0001)."""
    new, rel, states = world
    # A and B already published S-students ('ext:A-s', 'ext:B-s'); add a new student 'ext:A-new' of A, flagged now
    st = json.loads((new / 'students.json').read_text())
    st['A'].append(dict(person='ext:A-new', atlasId='atl:p:Anew'))
    (new / 'students.json').write_text(json.dumps(st))
    res = dict(states(set()), held_links=dict(A=[dict(student='New', id='ext:A-new', diagnosis='x'), dict(student='Old', id='ext:A-s', diagnosis='x')]))
    pl = PR.plan('x', res, published=rel)
    assert pl['held_links'] == {'A': [dict(student='New', id='ext:A-new', diagnosis='x')]}     # the published student is carried, not held
    held = PR.held_set(pl)
    assert held == {('A', 'ext:A-new')}
    assert [x['person'] for x in PR.filtered_rows_and_json('x', 'students.json', pl['included'], held=held)['A']] == ['ext:A-s']
    assert len(PR.filtered_rows_and_json('x', 'students.json', pl['included'])['A']) == 2        # without `held` nothing is dropped
    sp = PR.filtered_rows_and_json('x', 'student_papers.jsonl.gz', pl['included'], held={('A', 'ext:A-s')})
    assert all(r['student'] != 'ext:A-s' for r in sp if r['pi'] == 'A')
    assert PR.compare('x', pl['included'], rel, corrections=dict(against_release=rel.name, classes=[]), held=held)['flags'] == 0
    st = PR.scope_statement(pl)
    assert st['held_links_n'] == 1 and st['held_links'][0]['id'] == 'ext:A-new' and '1 student links are held' in PR.render_notes([st])


def test_compare_follows_a_drifted_lab_id_by_pi_name(world):
    """A PI that lost an identity anchor gets a new person/lab id in the rebuild; the published rows are not removals, the drift is counted."""
    new, rel, _ = world
    pis = json.loads((new / 'pis.json').read_text())
    for p in pis:
        if p['pi'] == 'A':
            p['labId'], p['atlasId'] = 'atl:l:x:A-2', 'atl:p:A2'
    (new / 'pis.json').write_text(json.dumps(pis))
    rows = [json.loads(l) for l in gzip.open(new / 'lab_papers.jsonl.gz', 'rt')]
    st = json.loads((new / 'students.json').read_text())
    assert PR.compare('x', ['A', 'B', 'C'], rel, corrections=dict(against_release=rel.name, classes=[]))['id_drift'] == 1
    got = PR.compare('x', ['A', 'B', 'C'], rel, corrections=dict(against_release=rel.name, classes=[]))
    assert got['kinds']['pi']['n_removed'] == 0 and got['kinds']['lab']['n_removed'] == 0 and got['kinds']['lab_paper']['n_removed'] == 0
    assert rows and st
