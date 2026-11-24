"""D-0027: a measure with an EMPTY population is not applicable (disclosed); never for a small sample."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACC = ROOT / 'accuracy'


def load(name, base=ACC):
    spec = importlib.util.spec_from_file_location('na_' + name, base / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(autouse=True)
def paths(monkeypatch):
    monkeypatch.syspath_prepend(str(ACC))
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))


def test_empty_populations_are_not_applicable():
    Sm = load('summarize')
    na = Sm.not_applicable(dict(n_lab_papers=59, n_student_papers=100, n_coverage_pool=0, n_student_candidates=0))
    assert set(na) == {'lab_coverage'} and na['lab_coverage']['population'] == 0 and na['lab_coverage']['not_applicable']
    na = Sm.not_applicable(dict(n_lab_papers=12, n_student_papers=0, n_coverage_pool=50, n_student_candidates=0))
    assert set(na) == {'student_precision_uniform'}


def test_a_small_but_nonempty_population_is_never_not_applicable():
    Sm = load('summarize')
    assert Sm.not_applicable(dict(n_lab_papers=3, n_student_papers=1, n_coverage_pool=1, n_student_candidates=0)) == {}


def _g9(monkeypatch, tmp_path, summary):
    SG = load('stage_gate', ROOT / 'tools')
    monkeypatch.setattr(SG, 'ACCURACY_DIR', tmp_path)
    monkeypatch.setattr(SG, 'read', lambda p: summary if 'round-pi2b' not in str(p) else None)
    return SG.g9('zzz')[0]


def test_gate_skips_only_a_zero_population_measure(monkeypatch, tmp_path):
    ok = dict(p=1.0, n=50)
    na = dict(p=None, n=0, population=0, not_applicable=True)
    bad = _g9(monkeypatch, tmp_path, dict(lab_precision_uniform=ok, student_precision_uniform=ok, lab_coverage=na))
    assert not any('lab_coverage' in b for b in bad)
    # an NA flag on a measure that has items (population or n nonzero) does not exempt it
    bad = _g9(monkeypatch, tmp_path, dict(lab_precision_uniform=ok, student_precision_uniform=ok, lab_coverage=dict(p=None, n=5, population=5, not_applicable=True)))
    assert any('lab_coverage' in b for b in bad)
    # a missing probability without the flag still fails
    bad = _g9(monkeypatch, tmp_path, dict(lab_precision_uniform=ok, student_precision_uniform=ok, lab_coverage=dict(p=None, n=0)))
    assert any('lab_coverage' in b for b in bad)
