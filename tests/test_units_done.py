"""R5/R6 (Georgia Tech friction 18/19): `units` writes units-done.json with shell years; the review refuses a stale unit capture set."""
import json

import atlas_paths as P
import cs_related_school as C


def _charter(monkeypatch, units):
    monkeypatch.setattr(C.S, 'get', lambda key: {'affiliated_units': units})


def test_units_current_needs_every_charter_unit_and_listing(tmp_path, monkeypatch):
    f = tmp_path / 'units-done.json'
    monkeypatch.setattr(C.P, 'data', lambda name, key, **k: f)
    _charter(monkeypatch, [{'code': 'A', 'listings': ['a.edu/p']}, {'code': 'B', 'listings': ['b.edu/p', 'b.edu/q']}])
    assert C.units_current('k') is False    # no marker
    f.write_text(json.dumps({'units': {'A': {'listings': ['a.edu/p'], 'captures': 3, 'shell_years': []}}}))
    assert C.units_current('k') is False    # unit B was added after the last run
    f.write_text(json.dumps({'units': {'A': {'listings': ['a.edu/p'], 'captures': 3, 'shell_years': ['2022']}, 'B': {'listings': ['b.edu/q', 'b.edu/p'], 'captures': 1, 'shell_years': []}}}))
    assert C.units_current('k') is True


def test_review_refuses_without_a_current_marker(monkeypatch):
    import pytest
    monkeypatch.setattr(C, 'units_current', lambda key: False)
    with pytest.raises(SystemExit) as e:
        C.review('k')
    assert 'units-done.json' in str(e.value)


def test_the_marker_name_is_registered():
    assert P.data('units-done.json', 'gatech').name == 'units-done.json'


def test_the_units_step_is_checked_by_the_marker():
    import stage_gate as G
    st = next(x for x in G.STEPS['2'] if x['name'] == 'units')
    assert st['check'][1:2] == ['units-check'] and st['check_py'] == 'project'
