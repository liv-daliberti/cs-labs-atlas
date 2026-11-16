"""A resumable school step must not reuse stale build, copy or ledger outputs."""
import pytest

import stage_gate as G
import stale_stages as ST


@pytest.mark.parametrize('name,output', [('build', 'pis.json'), ('copies', 'copies.json'), ('ledger', 'unavailable-summary.json')])
def test_onboarding_resume_uses_rebuild_dependency_registry(tmp_path, monkeypatch, name, output):
    path = tmp_path / output
    path.write_text('{}')
    monkeypatch.setattr(G.P, 'data', lambda *a: path)
    seen = []
    monkeypatch.setattr(ST, 'check', lambda stage, key: seen.append((stage, key)) or (True, 'newer input'))
    step = dict(name=name, kind='slurm', done=[output])
    assert G.step_done('u', step) is False
    assert seen == [(name, 'u')]
    monkeypatch.setattr(ST, 'check', lambda *a: (False, 'fresh'))
    assert G.step_done('u', step) is True


def test_unrelated_steps_keep_existing_completion_check(tmp_path, monkeypatch):
    path = tmp_path / 'census.json'
    path.write_text('{}')
    monkeypatch.setattr(G.P, 'data', lambda *a: path)
    monkeypatch.setattr(ST, 'check', lambda *a: pytest.fail('unrelated step must not use the build check'))
    assert G.step_done('u', dict(name='census', done=['census-faculty.json'])) is True
