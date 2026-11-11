import json
import sqlite3

import pytest
import school_hosts as H


def test_explicit_http_origin_uses_its_own_robots_and_delay(tmp_path, monkeypatch):
    host = 'www.cad.zju.edu.cn'
    probe = 'http://www.cad.zju.edu.cn/innovationteam'
    cfg = {'hosts': [dict(host=host, use='live', probe=probe,
                          http_origin=True, min_delay=3.2)]}
    c = sqlite3.connect(':memory:')
    c.execute('create table blocked(host text, why text)')
    calls = []
    monkeypatch.setattr(H.S, 'get', lambda key: cfg)
    monkeypatch.setattr(H.W, 'con', lambda key: c)
    monkeypatch.setattr(H.W, 'robots_row', lambda *a, **kw: (calls.append(('robots', kw['scheme'])) or (200, 'User-agent: *\nAllow: /')))
    monkeypatch.setattr(H.W, 'robots_decision', lambda *a: (True, True, 3.2))
    monkeypatch.setattr(H.W, 'live', lambda *a, **kw: (calls.append(('live', a[1], kw)) or (200, 'hash', [])))
    monkeypatch.setattr(H.P, 'data_w', lambda *a: tmp_path / 'hosts.json')
    assert H.main('zju')
    assert calls == [('robots', 'http'), ('live', probe, dict(refresh=False, same_origin=True, min_delay=3.2))]
    assert json.loads((tmp_path / 'hosts.json').read_text())['gate'] is True


def test_http_origin_rejects_wrong_scheme_before_network(monkeypatch):
    monkeypatch.setattr(H.S, 'get', lambda key: {'hosts': [dict(host='cad.zju.edu.cn', use='live',
                                                                probe='https://cad.zju.edu.cn/',
                                                                http_origin=True, min_delay=3.2)]})
    monkeypatch.setattr(H.W, 'con', lambda key: sqlite3.connect(':memory:'))
    with pytest.raises(ValueError, match='exact HTTP probe'):
        H.main('zju')
