import json

import pytest

import chain_audit as A


def row(school, count):
    return {'school': school,
            'checks': {c: {'pass': count, 'total': count, 'n_unexplained': 0, 'explained': {}}
                       for c in A.CHECKS}}


def configure(monkeypatch, tmp_path, previous):
    path = tmp_path / 'chain-audit.json'
    path.write_text(json.dumps(dict(at='earlier', schools=previous)))
    monkeypatch.setattr(A, 'SCHOOLS', ['mit'])
    monkeypatch.setattr(A.CO, 'onboarding', lambda s: s in {'ntu', 'sjtu'})
    monkeypatch.setattr(A.P, 'hfile', lambda root, name: tmp_path / name)
    monkeypatch.setattr(A.P, 'hfile_w', lambda root, name: tmp_path / name)
    calls = []

    def audit(school):
        calls.append(school)
        return row(school, 205)

    monkeypatch.setattr(A, 'audit', audit)
    return path, calls


def test_explicit_onboarding_school_is_exported_and_other_rows_preserved(monkeypatch, tmp_path):
    existing = [row('mit', 232), row('sjtu', 200)]
    path, calls = configure(monkeypatch, tmp_path, existing)
    A.main(['ntu'])
    rows = {r['school']: r for r in json.loads(path.read_text())['schools']}
    assert calls == ['ntu']
    assert rows['ntu'] == row('ntu', 205)
    assert rows['mit'] == existing[0]
    assert rows['sjtu'] == existing[1]
    assert '| ntu |' in (tmp_path / 'CHAIN-AUDIT.md').read_text()


def test_unknown_explicit_school_fails_before_audit_or_output_write(monkeypatch, tmp_path):
    path, calls = configure(monkeypatch, tmp_path, [row('mit', 232)])
    before = path.read_bytes()
    with pytest.raises(SystemExit, match='unknown or unsupported school: typo'):
        A.main(['typo'])
    assert calls == []
    assert path.read_bytes() == before
    assert not (tmp_path / 'CHAIN-AUDIT.md').exists()


def test_default_audit_keeps_released_school_scope(monkeypatch, tmp_path):
    path, calls = configure(monkeypatch, tmp_path, [row('mit', 232), row('ntu', 180)])
    A.main([])
    assert calls == ['mit']
    assert [r['school'] for r in json.loads(path.read_text())['schools']] == ['mit']
