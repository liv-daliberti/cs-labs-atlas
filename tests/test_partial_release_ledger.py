import pytest

import school_config as S


def test_new_onboarding_without_package_does_not_break_released_ledger(monkeypatch, tmp_path):
    configs = {'existing': {}, 'partial': {'release': {'ledger_mode': 'offline', 'owner_quote': 'release what we have', 'reason': 'copy search incomplete'}}}
    monkeypatch.setattr(S, 'get', configs.__getitem__)
    monkeypatch.setattr(S, 'onboarding', lambda: ['started', 'ready'])
    monkeypatch.setattr(S.P, 'data', lambda name, key: tmp_path / key / name)
    (tmp_path / 'ready').mkdir()
    for name in ('copies.json', 'lab_papers.jsonl.gz'):
        (tmp_path / 'ready' / name).touch()
    assert S.ledger_groups(['existing', 'partial']) == (['existing', 'ready'], ['partial'])


def test_partial_copy_search_requires_documented_authorization(monkeypatch):
    monkeypatch.setattr(S, 'get', lambda _: {'release': {'ledger_mode': 'offline'}})
    with pytest.raises(ValueError, match='authorization'):
        S.ledger_groups(['partial'])


def test_selected_missing_package_is_not_silently_omitted(monkeypatch):
    monkeypatch.setattr(S, 'get', lambda _: {})
    monkeypatch.setattr(S, 'onboarding', lambda: ['selected'])
    assert S.ledger_groups(['selected']) == (['selected'], [])
