"""Optional metadata fetching cannot hold back an admitted paper's catalog row."""
import sys

import add_works as A


def test_no_fetch_uses_known_paper_identifiers(monkeypatch, tmp_path):
    row = dict(work='w1', oa='https://openalex.org/W1', title='A paper already admitted to its school',
               doi='10.1234/fixture', year=2021, pis=['Fixture PI'], byline_school=['Fixture PI'])
    monkeypatch.setattr(sys, 'argv', ['add_works.py', 'hit', '--no-fetch'])
    monkeypatch.setattr(A.F, 'lab_papers', lambda *a: {'w1': row})
    monkeypatch.setattr(A.F, 'catalog_state', lambda *a, **k: {})
    monkeypatch.setattr(A.F, 'match_work', lambda *a: None)
    monkeypatch.setattr(A.F, 'is_local', lambda *a: False)
    monkeypatch.setattr(A.F, 'oa_bodies', lambda *a: {})
    monkeypatch.setattr(A.F, 'fetch_oa_bodies', lambda *a: (_ for _ in ()).throw(AssertionError('network fetch')))
    monkeypatch.setattr(A.F, 'arxiv_of', lambda *a: None)
    monkeypatch.setattr(A.F, 'FT', tmp_path)
    monkeypatch.setattr(A.F.P, 'FT_LOGS', tmp_path)
    monkeypatch.setattr(A, 'ensure_graph_receipt', lambda *a: False)
    writes = []

    class DB:
        def close(self):
            pass

    monkeypatch.setattr(A.F, 'connect_rw', lambda *a: DB())
    monkeypatch.setattr(A.F, 'write_batches', lambda db, sql, rows: writes.append((sql, rows)) or len(rows))
    A.main()
    work = writes[0][1][0]
    assert work[:4] == ('w1', row['title'], row['doi'], row['year'])
    assert work[-1] == 'queued'
