"""stage_gate stage 0: charter check, host gate file, and the OpenAlex snapshot (main store or extension) holding the school."""
import json
import sqlite3

import oa_snapshot as O
import stage_gate as G


def store(path, rows):
    db = sqlite3.connect(path)
    db.executescript(O.SCHEMA)
    db.executemany('insert into work_inst values (?,?)', rows)
    db.commit(); db.close()


def test_snapshot_count_reads_the_main_store_and_extensions(tmp_path, monkeypatch):
    d = tmp_path / '2026-10-14'; d.mkdir()
    store(d / 'openalex.sqlite', [('W1', 'I1')])
    (tmp_path / 'current').symlink_to('2026-10-14')
    monkeypatch.setattr(O, '_conns', {})
    monkeypatch.setattr(G.S, 'inst', lambda k: 'I9')
    assert G.snapshot_count('newu', tmp_path) == 0
    store(d / 'ext-newu.sqlite', [('W2', 'I9'), ('W3', 'I9')])
    monkeypatch.setattr(O, '_conns', {})
    assert G.snapshot_count('newu', tmp_path) == 2
    assert G.snapshot_count('newu', tmp_path / 'nowhere') is None


def test_g0_lists_what_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(G.S, 'check', lambda k: ['newu: missing ids.ror'])
    monkeypatch.setattr(G.S, 'get', lambda k: {'hosts': [{'host': 'a.edu'}, {'host': 'b.edu'}]})
    monkeypatch.setattr(G.S, 'inst', lambda k: 'I9')
    monkeypatch.setattr(G, 'snapshot_count', lambda k, root=None: 0)
    hosts = tmp_path / 'hosts.json'
    monkeypatch.setattr(G.P, 'data', lambda name, key=None: hosts)
    bad, _ = G.g0('newu')
    assert any('missing ids.ror' in b for b in bad) and any('hosts.json missing' in b for b in bad) and any('snapshot: no works' in b for b in bad)
    hosts.write_text(json.dumps(dict(gate=False, hosts=[dict(host='a.edu', consistent=False, problems=['probe returned http 310'])])))
    bad, c = G.g0('newu')
    assert any('b.edu is in the charter but not in hosts.json' in b for b in bad) and any('a.edu: probe returned http 310' in b for b in bad)
    monkeypatch.setattr(G.S, 'check', lambda k: [])
    monkeypatch.setattr(G, 'snapshot_count', lambda k, root=None: 5)
    hosts.write_text(json.dumps(dict(gate=True, hosts=[dict(host='a.edu', consistent=True, problems=[]), dict(host='b.edu', consistent=True, problems=[])])))
    assert G.g0('newu') == ([], dict(hosts=2, snapshot_works=5))
