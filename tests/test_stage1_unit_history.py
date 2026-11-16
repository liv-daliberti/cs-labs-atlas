import hashlib
import json
import sqlite3
import zlib

import pytest

from tools import stage_gate as G


@pytest.fixture
def history(tmp_path, monkeypatch):
    raw = '<html><meta charset="utf-8"><p>AIR于2020年创建。</p></html>'.encode()
    url = 'https://air.school.edu/history'
    quote = 'AIR于2020年创建。'
    sha = hashlib.sha256(raw).hexdigest()
    evidence = dict(url=url, sha256=sha, quote=quote, reviewed_by='owner',
                    reviewed_on='2026-11-16', owner_quote='Review AIR from its founding')
    department = dict(code='AIR', founded_year=2020, founded_evidence=evidence)
    cfg = dict(window=[2016, 2021], web=dict(domains=['school.edu']), departments=[department])
    (tmp_path / 'coverage.json').write_text(json.dumps({'AIR': {'2021': {'Faculty H1': 'ok'}}}))
    db = sqlite3.connect(tmp_path / 'school-captures.sqlite')
    db.execute('create table live (url text, status int, sha256 text, raw_zlib blob)')
    db.execute('insert into live values (?,200,?,?)', (url, sha, zlib.compress(raw)))
    db.commit()
    monkeypatch.setattr(G.S, 'get', lambda key: cfg)
    monkeypatch.setattr(G.P, 'data', lambda name, key: tmp_path / name)
    yield department, evidence, db
    db.close()


def test_R_SRC_01_captured_founding_bounds_only_unit_source_window(history):
    bad, counts = G.g1('u')
    assert bad == ['AIR 2020: never planned']
    assert counts['pre_founding_years_not_applicable'] == [f'AIR {y}' for y in range(2016, 2020)]
    assert counts['unit_founding_years'] == {'AIR': 2020}
    assert G.S.get('u')['window'] == [2016, 2021]


def test_unconfigured_unit_retains_full_window(history):
    department, _, _ = history
    department.pop('founded_year')
    bad, counts = G.g1('u')
    assert bad == [f'AIR {y}: never planned' for y in range(2016, 2021)]
    assert counts == dict(departments=1, reviewed_gap_years=0)


@pytest.mark.parametrize('change', [dict(sha256='0' * 64), dict(quote='Founded in 2020'),
                                   dict(reviewed_by='agent'), dict(reviewed_on='20261116'),
                                   dict(owner_quote=''), dict(owner_quote='  '), dict(owner_quote={'not': 'a quote'}),
                                   dict(url='https://evil.edu/history')])
def test_invalid_review_never_removes_required_years(history, change):
    _, evidence, _ = history
    evidence.update(change)
    bad, counts = G.g1('u')
    assert 'invalid founded_year evidence' in bad[0]
    assert bad[1:] == [f'AIR {y}: never planned' for y in range(2016, 2021)]
    assert 'unit_founding_years' not in counts


@pytest.mark.parametrize('year', [2019, True, '2020', 2022])
def test_wrong_year_cannot_limit_window(history, year):
    department, _, _ = history
    department['founded_year'] = year
    assert len(G.g1('u')[0]) == 6


@pytest.mark.parametrize('mutation', ['delete from live', 'update live set status=404',
                                    "update live set raw_zlib=X'00'",
                                    "update live set raw_zlib=X'789c030000000001'"])
def test_missing_or_corrupt_original_capture_fails_closed(history, mutation):
    _, _, db = history
    db.execute(mutation)
    db.commit()
    assert len(G.g1('u')[0]) == 6


def test_hidden_script_is_not_founding_proof(history):
    _, evidence, db = history
    raw = b'<html><script>Founded in 2020</script><p>History unavailable</p></html>'
    evidence.update(sha256=hashlib.sha256(raw).hexdigest(), quote='Founded in 2020')
    db.execute('update live set sha256=?,raw_zlib=?', (evidence['sha256'], zlib.compress(raw)))
    db.commit()
    assert len(G.g1('u')[0]) == 6
