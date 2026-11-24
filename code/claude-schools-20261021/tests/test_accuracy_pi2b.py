"""Round pi2b (owner D-0026): redraws of schools whose pi2 draw was judged and superseded go to accuracy/round-pi2b/; the judged pi2 files are never touched,
the seed rule spans both rounds and stage-gate 9 reads the newest round's summary."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACC = ROOT / 'accuracy'


def load(name, base=ACC):
    spec = importlib.util.spec_from_file_location('pi2b_' + name, base / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(autouse=True)
def accuracy_on_path(monkeypatch):
    monkeypatch.syspath_prepend(str(ACC))
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))


def test_pi2b_round_is_separate_from_pi2():
    S = load('sample')
    assert S.ROUNDS['pi2b']['dir'] == 'round-pi2b' and S.ROUNDS['pi2']['dir'] == 'round-pi2'
    for k in ('uniform', 'stratum', 'cov', 'cands', 'subset'):
        assert S.ROUNDS['pi2b'][k] == S.ROUNDS['pi2'][k]
    assert S.ROUNDS['pi2b']['seed'] is None            # a fresh seed is always passed in


def test_g9_round_flag_selects_the_round_directory(monkeypatch, tmp_path):
    G = load('g9_round')
    (tmp_path / 'round-pi2').mkdir()
    monkeypatch.setattr(G, 'main_acc', lambda: tmp_path)
    plan = tmp_path / 'p'
    # `plan` reads packages only; run the argument handling for both rounds and check which round the module is set to
    for rnd in ('pi2', 'pi2b'):
        monkeypatch.setattr(G, 'cmd_plan', lambda a: 0)
        assert G.main(['plan', '--round', rnd]) == 0
        assert G.ROUND == rnd
    assert not (tmp_path / 'round-pi2b').exists() and not plan.exists()      # nothing is created by choosing a round
    assert G.S0.ROUNDS[G.ROUND]['dir'] == 'round-pi2b'


def test_drawn_reads_only_the_selected_round(monkeypatch, tmp_path):
    G = load('g9_round')
    monkeypatch.setattr(G, 'main_acc', lambda: tmp_path)
    for rd, school in (('round-pi2', 'aaa'), ('round-pi2b', 'bbb')):
        (tmp_path / rd).mkdir()
        (tmp_path / rd / f'sample-{school}.json').write_text(json.dumps({'seed': 1, 'schools': {school: {}}}))
    monkeypatch.setattr(G, 'ROUND', 'pi2')
    assert set(G.drawn()) == {'aaa'}
    monkeypatch.setattr(G, 'ROUND', 'pi2b')
    assert set(G.drawn()) == {'bbb'}


def test_seed_uniqueness_spans_both_rounds(monkeypatch, tmp_path):
    G = load('g9_round')
    monkeypatch.setattr(G, 'main_acc', lambda: tmp_path)
    for rd, seed in (('round-pi2', 111), ('round-pi2b', 222)):
        (tmp_path / rd).mkdir()
        (tmp_path / rd / 'sample-x.json').write_text(json.dumps({'seed': seed}))
    used = G.used_seeds()
    assert {111, 222} <= used


def test_stage_gate_reads_the_newest_round_summary(monkeypatch, tmp_path):
    SG = load('stage_gate', ROOT / 'tools')
    seen = []

    def fake_read(path):
        seen.append(Path(path))
        return None
    monkeypatch.setattr(SG, 'read', fake_read)
    monkeypatch.setattr(SG, 'ACCURACY_DIR', tmp_path)
    bad, _ = SG.g9('zzz')
    assert seen[0] == tmp_path / 'round-pi2c' / 'summary-zzz.json' and seen[1] == tmp_path / 'round-pi2b' / 'summary-zzz.json' and seen[2] == tmp_path / 'summary-zzz.json'
    assert bad and 'missing' in bad[0]
    # a pi2b summary shadows the shared slot
    seen.clear()
    monkeypatch.setattr(SG, 'read', lambda p: {'school': 'zzz'} if 'round-pi2b' in str(p) else {'school': 'old'})
    SG.g9('zzz')


def test_pi2c_is_a_third_separate_round_and_gate_prefers_it(monkeypatch, tmp_path):
    S = load('sample')
    assert S.ROUNDS['pi2c']['dir'] == 'round-pi2c'
    SG = load('stage_gate', ROOT / 'tools')
    seen = []
    monkeypatch.setattr(SG, 'ACCURACY_DIR', tmp_path)
    monkeypatch.setattr(SG, 'read', lambda p: seen.append(Path(p)) or None)
    SG.g9('zzz')
    assert [p.parent.name for p in seen[:2]] == ['round-pi2c', 'round-pi2b']
