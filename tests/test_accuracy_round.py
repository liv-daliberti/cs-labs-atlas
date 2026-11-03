"""accuracy round r2 (owner 2026-11-02): 50 uniform rows per school and sample, a new seed, its own files; the 2026-10-29
draw (LEGACY) and its verdict files are unchanged."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

ACC = Path(__file__).resolve().parents[1] / 'accuracy'


def load(name):
    spec = importlib.util.spec_from_file_location('acc_' + name, ACC / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(autouse=True)
def accuracy_on_path(monkeypatch):
    monkeypatch.syspath_prepend(str(ACC))     # record.py imports sample (the scripts run from their own directory)


S = load('sample')


def test_round_config():
    r2 = S.ROUNDS['r2']
    assert r2['seed'] not in (S.SEED, None) and r2['seed'] == 20261102
    assert (r2['uniform'], r2['stratum'], r2['cov']) == (50, 5, 50) and r2['cands'] >= 100
    assert r2['schools'] == ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan']
    assert S.LEGACY['uniform'] == 25 and S.LEGACY['cov'] == 15 and S.LEGACY['cands'] == 40 and S.LEGACY['seed'] == 20261029


def test_round_files_are_separate(monkeypatch):
    R = load('record')
    monkeypatch.delenv('ACCURACY_ROUND', raising=False)
    assert R.files('mit') == (ACC / 'sample.json', ACC / 'verdicts.jsonl')           # the history stays where it was
    assert R.files('michigan') == (ACC / 'sample-michigan.json', ACC / 'verdicts-michigan.jsonl')
    monkeypatch.setenv('ACCURACY_ROUND', 'r2')
    assert R.files('mit') == (ACC / 'round-r2' / 'sample-mit.json', ACC / 'round-r2' / 'verdicts-mit.jsonl')
    assert R.files('michigan')[1].parent == ACC / 'round-r2'


def test_round_draw_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(S, 'ACC_DIR', tmp_path / 'accuracy')
    (tmp_path / 'accuracy').mkdir()
    monkeypatch.setitem(S.ROUNDS['r2'], 'schools', ['mit'])
    d = tmp_path / 'accuracy' / 'round-r2'
    d.mkdir()
    (d / 'sample-mit.json').write_text('{}')
    with pytest.raises(SystemExit):
        S.draw_round('r2')
    assert (d / 'sample-mit.json').read_text() == '{}'


@pytest.mark.nfs
def test_round_draw_sizes_and_history(tmp_path):
    out = S.main(['mit'], tmp_path / 'a.json', '2026-11-02', S.ROUNDS['r2'])
    m = out['schools']['mit']
    assert out['seed'] == 20261102 and out['sizes']['uniform'] == 50
    assert sum(x['stratum'] == 'uniform' for x in m['lab_precision']) == 50
    assert sum(x['stratum'] == 'uniform' for x in m['student_precision']) == 50
    assert len(m['lab_coverage']) == 50 and len(m['student_coverage_order']) == min(200, m['n_student_candidates'])
    assert {x['stratum'] for x in m['lab_precision']} >= {'uniform', 'advisee_unaffiliated'}
    legacy = S.main(['mit'], tmp_path / 'b.json')
    assert legacy['seed'] == 20261029 and 'sizes' not in legacy
    assert sum(x['stratum'] == 'uniform' for x in legacy['schools']['mit']['lab_precision']) == 25
    assert json.loads(Path(S.OUT).read_text())['seed'] == 20261029 and os.path.exists(ACC / 'verdicts.jsonl')
