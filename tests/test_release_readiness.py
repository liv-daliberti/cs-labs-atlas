"""tools/release_readiness.py (the freeze check) and accuracy/g9_round.py (the pi2 redraw): the pure parts, on fixtures."""
from pathlib import Path

import pytest

import importlib.util

import release_readiness as R

ACC = Path(__file__).resolve().parent.parent / 'accuracy'


def load(name, monkeypatch):
    """accuracy/<name>.py by path (the directory is not on the test path; sibling imports need it first)."""
    monkeypatch.syspath_prepend(str(ACC))
    spec = importlib.util.spec_from_file_location(name, ACC / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def row(**k):
    gates = {str(i): dict(rc=0, gate='pass', open=0) for i in range(11)}
    gates.update(k.pop('gates', {}))
    r = dict(school='x', included=3, held=0, ids=True, gates=gates, compare=dict(rc=0, flags=0), g9=dict(state='fresh'), validate=dict(violations=0))
    r.update(k)
    return r


def test_a_clean_row_has_no_problem():
    assert R.problems(row()) == []


def test_each_failing_check_is_named():
    p = R.problems(row(ids=False, compare=dict(rc=1, flags=4), g9=dict(state='stale'), validate=dict(violations=2), gates={'2': dict(rc=1, gate='fail', open=3)}))
    assert p == ['ids', 'gates 2', 'removals 4', 'g9 stale', 'validate 2']


def test_a_failing_per_pi_gate_holds_pis_not_the_school():
    assert R.problems(row(gates={'5': dict(rc=1, gate='fail', open=7)})) == []


def test_a_school_without_an_included_pi_is_skipped():
    assert R.problems(dict(school='y', skip='no included PI')) == []


def test_markdown_lists_ready_and_skipped_schools():
    r = row()
    r['problems'] = []
    r['stale_build'] = dict(stale=False)
    r['built_at'] = '2026-11-19T01:02:03Z'
    r['compare'] = dict(rc=0, flags=0, corrected=5)
    doc = dict(at='t', published='2026-11-07', code='abc', secs=1, rows=[r, dict(school='z', skip='no included PI')],
               freshness=dict(newest_build='n', regression={}, evidence_check={}), shared_validate={})
    md = R.render_md(doc)
    assert 'READY' in md and 'z' in md.split('No included PI')[1]


def test_batches_are_at_most_25_rows(monkeypatch):
    G = load('g9_round', monkeypatch)
    assert G.chunks(65) == [(0, 25), (25, 25), (50, 15)]
    assert G.chunks(0) == []
    assert all(n <= G.MAX_BATCH for _, n in G.chunks(200))


def test_pi2_draw_refuses_without_a_fresh_seed(monkeypatch):
    S = load('sample', monkeypatch)
    monkeypatch.delenv('ACCURACY_REDRAW_SEED', raising=False)
    with pytest.raises(SystemExit) as e:
        S.draw_round('pi2', ['nowhere'])
    assert 'no fixed seed' in str(e.value)


def test_used_seed_is_refused(monkeypatch):
    G = load('g9_round', monkeypatch)
    assert 20261118 in G.used_seeds()
