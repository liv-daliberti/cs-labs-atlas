"""school_hosts: a use = none charter host on the never-contact list (dblp.org, orcid.org, the Wayback Machine) is recorded without any request."""
import json
import school_hosts as H


def test_dblp_use_none_is_not_contacted(monkeypatch, tmp_path):
    calls = []
    cfg = {'hosts': [{'host': 'dblp.org', 'use': 'none', 'purpose': 'local dump only'},
                     {'host': 'example.edu', 'use': 'none', 'purpose': 'x'}]}
    monkeypatch.setattr(H.S, 'get', lambda key: cfg)
    monkeypatch.setattr(H.W, 'con', lambda key: type('C', (), {'execute': lambda self, *a, **k: type('R', (), {'fetchone': lambda s: None})()})())
    monkeypatch.setattr(H.W, 'robots_row', lambda c, host, refresh=False: (calls.append(host) or (200, 'User-agent: *\nDisallow:\n')))
    out = tmp_path / 'hosts.json'
    monkeypatch.setattr(H.P, 'data_w', lambda name, key: out)
    assert H.main('x') is True
    assert calls == ['example.edu']
    rows = json.loads(out.read_text())['hosts']
    assert rows[0]['robots'] == 'not_fetched' and rows[0]['consistent'] is True
