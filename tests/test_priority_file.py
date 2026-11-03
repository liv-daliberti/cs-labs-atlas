"""priority_file.py picks only the queued link-only papers; lab_first_loop orders them first (2026-11-03)."""
import gzip
import importlib.util
import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
FTP = CODE / 'fulltext-push'


def load(name):
    """This worktree's module by path (another test may have cached a copy from elsewhere)."""
    if str(FTP) not in sys.path:
        sys.path.insert(0, str(FTP))   # the modules import each other by bare name
    spec = importlib.util.spec_from_file_location('wt_' + name, FTP / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PF = load('priority_file')


def release(tmp_path):
    rel = tmp_path / 'rel'
    (rel / 'reader').mkdir(parents=True)
    (rel / 'hierarchy' / 's').mkdir(parents=True)  # route-ok: release layout
    reader = [
        dict(key='a', decision='link', stored_copy=False, link_basis='openalex_location'),
        dict(key='b', decision='link', stored_copy=False, link_basis='arxiv_id_doi'),
        dict(key='c', decision='link', stored_copy=False, link_basis='landing_page_metadata'),
        dict(key='d', decision='link', stored_copy=True, link_basis='confirmed_copy'),
        dict(key='e', decision='host', stored_copy=True, link_basis=None),
        dict(key='f', decision='link', stored_copy=False, link_basis='openalex_location'),
        dict(key='g', decision='link', stored_copy=False, link_basis='openalex_location'),
    ]
    ledger = [dict(key=k, work_id='w_' + k, reason_code=c) for k, c in
              [('a', 'found_awaiting_download'), ('b', 'pending_retry'), ('c', 'open_copy_robots_disallowed'),
               ('d', 'found_awaiting_download'), ('f', 'paywall_only')]]
    for name, rows in (('reader/s.jsonl.gz', reader), ('hierarchy/s/unavailable.jsonl.gz', ledger)):  # route-ok: release layout
        with gzip.open(rel / name, 'wt') as f:
            f.write(''.join(json.dumps(r) + '\n' for r in rows))
    return rel


def test_only_queued_link_only_papers_are_listed(tmp_path):
    rel = release(tmp_path)
    assert [e[0] for e in PF.queued_entries('s', rel)] == ['w_a', 'w_b']   # blocked, hosted, confirmed_copy and no-ledger rows are out
    m = PF.measure('s', rel)
    assert (m['total'], m['queued'], m['blocked'], m['no_ledger']) == (5, 2, 2, 1)
    assert m['code:open_copy_robots_disallowed'] == 1


def test_write_and_read_roundtrip(tmp_path):
    rel = release(tmp_path)
    p, n = PF.write('s', rel, tmp_path / 'out')
    assert n == 2 and p.name == 's-priority-work-ids.tsv'
    assert PF.read_ids(p) == ['w_a', 'w_b']


def test_loop_puts_priority_groups_first(monkeypatch):
    L = load('lab_first_loop')
    rows = {'k1': dict(work='w1', year=2020), 'k2': dict(work='w2', year=2024), 'k3': dict(work='w3', year=2025)}
    cs = dict(status={'w1': 'queued', 'w2': 'queued', 'w3': 'queued'}, alias={})

    class DB:
        def close(self):
            pass
    monkeypatch.setattr(L.F, 'lab_papers', lambda s: rows)
    monkeypatch.setattr(L.F, 'catalog_state', lambda s, with_urls=False: cs)
    monkeypatch.setattr(L.F, 'works_rows', lambda db, cols: [])
    monkeypatch.setattr(L.F, 'is_local', lambda s, r, c: False)
    monkeypatch.setattr(L.F, 'match_work', lambda s, r, c: r['work'])
    monkeypatch.setattr(L.sqlite3, 'connect', lambda *a, **k: DB())
    assert L.lab_work_ids('s', 2023) == ['w2', 'w3', 'w1']
    assert L.lab_work_ids('s', 2023, {'w1'}) == (['w1'], ['w2', 'w3'])
    assert L.lab_work_ids('s', 2023, set()) == ([], ['w2', 'w3', 'w1'])   # a blocked/absent id never changes the pass
