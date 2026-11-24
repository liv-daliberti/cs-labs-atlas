"""ROADMAP #43: `periods_school.py deep --work-years` proves the years of a PI's identified works outside the listing years
(Georgia Tech 2026-11-05: Warnke, Yu and Mahmoudi are listed in one year only, so span_gaps sees no gap)."""
import importlib.util
import json
from pathlib import Path


def periods_school():
    spec = importlib.util.spec_from_file_location('by_path_periods_school', Path(__file__).resolve().parents[1] / 'tools' / 'periods_school.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_outside_work_years(tmp_path, monkeypatch):
    ps = periods_school()
    f = tmp_path / 'pis.json'
    f.write_text(json.dumps([dict(pi='A', funnel={'identity': 5, 'outside_appointment_2018': 2, 'outside_appointment_2017': 1, 'outside_appointment_2031': 1})]))
    monkeypatch.setattr(ps.P, 'data', lambda name, key=None, **k: f)
    monkeypatch.setattr(ps.S, 'get', lambda key: {'window': [2016, 2026]})
    assert ps.outside_work_years('x', 'A', dict(years_listed=[2017])) == {2018}
    assert ps.outside_work_years('x', 'missing', {}) == set()
