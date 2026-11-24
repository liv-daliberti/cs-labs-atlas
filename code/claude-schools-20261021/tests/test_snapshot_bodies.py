"""ftp_common.oa_bodies reads the OpenAlex snapshot first and leaves the rest to the older stores (ROADMAP #24)."""
from pathlib import Path
import json
import sqlite3
import zlib

CODE = Path(__file__).resolve().parents[1]
import ftp_common as F  # noqa: E402
import oa_snapshot as OS  # noqa: E402


def test_snapshot_bodies_prefer_the_snapshot_and_skip_missing(monkeypatch):
    db = snapshot([dict(id='https://openalex.org/W1', locations=[dict(pdf_url='https://x/y.pdf')])])
    ext = snapshot([dict(id='https://openalex.org/W1', locations=[]), dict(id='https://openalex.org/W3')])
    monkeypatch.setattr(OS, 'conn', lambda *a, **k: (db, '2026-10-14'))
    monkeypatch.setattr(OS, 'exts', lambda *a, **k: [(ext, '2026-11-23')])
    got = F.snapshot_bodies(['https://openalex.org/W1', 'https://openalex.org/W2'])
    assert list(got) == ['https://openalex.org/W1'] and got['https://openalex.org/W1']['snapshot_date'] == '2026-10-14'
    assert got['https://openalex.org/W1']['locations']
    assert F.snapshot_bodies(['W3'])['W3']['snapshot_date'] == '2026-11-23'


def snapshot(rows):
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE works(id TEXT PRIMARY KEY,body BLOB)')
    db.executemany('INSERT INTO works VALUES (?,?)', [(r['id'], zlib.compress(json.dumps(r).encode())) for r in rows])
    return db


def test_snapshot_lookup_is_bounded_and_batched(monkeypatch):
    rows = [dict(id=f'https://openalex.org/W{i}') for i in range(601)]
    db = snapshot(rows)
    queries = []
    db.set_trace_callback(queries.append)
    monkeypatch.setattr(OS, 'conn', lambda *a, **k: (db, '2026-10-14'))
    monkeypatch.setattr(OS, 'exts', lambda *a, **k: [])
    got = F.snapshot_bodies([r['id'] for r in rows])
    assert len(got) == 601
    assert len(queries) == 4  # 200 ids per short read, instead of 601 separate reads


def test_no_snapshot_means_the_old_path(monkeypatch):
    def none(*a, **k):
        raise FileNotFoundError('no snapshot')
    monkeypatch.setattr(OS, 'conn', none)
    assert F.snapshot_bodies(['https://openalex.org/W1']) == {}


def test_oa_bodies_merges_snapshot_over_the_stores(monkeypatch, tmp_path):
    monkeypatch.setattr(F, 'snapshot_bodies', lambda ids: {i: {'id': i, 'src': 'snapshot'} for i in ids if i.endswith('W1')})
    monkeypatch.setattr(F, 'oa_store', lambda school: tmp_path / 'absent.sqlite')
    got = F.oa_bodies('epfl', ['https://openalex.org/W1', 'https://openalex.org/W2'])
    assert got['https://openalex.org/W1']['src'] == 'snapshot' and 'https://openalex.org/W2' not in got
