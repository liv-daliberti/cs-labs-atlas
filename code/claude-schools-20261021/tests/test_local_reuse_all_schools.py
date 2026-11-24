"""Cross-school reuse keeps identity, quality, backups and writer serialization."""
import fcntl
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def reuse(monkeypatch):
    root = Path(__file__).resolve().parents[1] / 'fulltext-push/local-reuse'
    monkeypatch.syspath_prepend(str(root))
    spec = importlib.util.spec_from_file_location('reuse_fixture', root / 'reuse_import.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_school_selection_all_and_explicit(reuse, tmp_path, monkeypatch):
    import lr_common as L
    monkeypatch.setattr(L.F, 'FT', tmp_path)
    monkeypatch.setattr(L.F.P, 'data', lambda name, school: tmp_path / school / name)
    for school in ('hit', 'michigan', 'uwashington'):
        p = tmp_path / school
        p.mkdir()
        (p / 'catalog.sqlite').touch()
    (tmp_path / 'hit/lab_papers.jsonl.gz').touch()
    assert L.selected_schools('all') == ('hit', 'michigan', 'uwashington')
    assert L.selected_schools('all', targets=True) == ('hit',)
    assert L.selected_schools('hit, michigan hit') == ('hit', 'michigan')
    assert L.selected_schools(None) == L.LEGACY_SCHOOLS
    with pytest.raises(ValueError):
        L.selected_schools('../other')


def test_source_scan_reads_paths_only_for_possible_missing_papers(reuse):
    import lr_common as L
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE works(id TEXT PRIMARY KEY,doi TEXT,title TEXT,year INT,status TEXT,sha256 TEXT,file_path TEXT)')
    db.executemany('INSERT INTO works VALUES (?,?,?,?,?,?,?)', [
        ('yes', '10.1234/missing', 'The Missing Paper Title', 2020, 'downloaded', 'sha1', 'objects/sha1.pdf'),
        ('irrelevant', '10.1234/other', 'A Different Paper Title', 2021, 'downloaded', 'sha2', 'objects/sha2.pdf'),
        ('queued', '10.1234/missing', 'The Missing Paper Title', 2020, 'queued', None, None),
    ])
    db.execute('CREATE INDEX works_slim ON works(id,status,doi,title,year,identity_check,byte_count,sha256)'.replace(
        ',identity_check,byte_count', ''))
    queries = []
    db.set_trace_callback(queries.append)
    rows = list(L.source_rows(db, ({'10.1234/missing'}, set())))
    assert len(rows) == 1 and rows[0][0] == 'yes' and rows[0][-2] == 'objects/sha1.pdf'
    path_reads = [q for q in queries if 'SELECT id,file_path' in q]
    assert len(path_reads) == 1 and 'irrelevant' not in path_reads[0]


def test_target_share_imports_only_the_remaining_deficit(reuse, tmp_path, monkeypatch):
    inv = tmp_path / 'inventory.sqlite'
    with sqlite3.connect(inv) as db:
        db.executescript('''
            CREATE TABLE proposals(school TEXT,work_id TEXT,paper_key TEXT,origin TEXT,rule TEXT,
              src_path TEXT,sha256 TEXT,detail TEXT,outcome TEXT);
            CREATE TABLE meta(k TEXT PRIMARY KEY,v TEXT);
        ''')
        db.executemany('INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,NULL)', [
            ('hit', w, w, 'cross_catalog', 'cross_doi', '/source/' + w, w, '{}') for w in ('w1', 'w2')])
    monkeypatch.setattr(reuse, 'INV', inv)
    monkeypatch.setattr(reuse, 'SCHOOLS', ('hit',))
    monkeypatch.setattr(reuse, 'load_missing', lambda: [dict(school='hit')] * 41)
    monkeypatch.setattr(reuse.F, 'lab_papers', lambda s: dict.fromkeys(range(100)))
    monkeypatch.setattr(reuse, 'catalog_rows', lambda s, ws: {w: dict(status='queued') for w in ws})
    monkeypatch.setattr(reuse, 'check', lambda *a: (2, 'title_in_first_three_pages', 100))
    monkeypatch.setattr(reuse, 'place', lambda *a: 'hard_link')
    written = []

    def write(school, accepted, stamp, dry):
        for a in accepted:
            a['outcome'] = 'imported'
            written.append(a['work_id'])
        return len(accepted)

    monkeypatch.setattr(reuse, 'write_school', write)
    reuse.do_import(target_share=0.6)
    assert written == ['w1']  # 59 of 100 already local; one more reaches 60%
    with sqlite3.connect(inv) as db:
        assert db.execute("SELECT outcome FROM proposals WHERE work_id='w2'").fetchone() == (None,)


def test_import_rejects_metadata_only_and_unconfirmed_identity(reuse, tmp_path, monkeypatch):
    import collect_princeton_fulltext as base
    import hashlib
    p = tmp_path / 'paper.pdf'
    p.write_bytes(b'fixture')
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    monkeypatch.setattr(base, 'validate_pdf', lambda data, dst: dst.write_bytes(data))
    monkeypatch.setattr(base, 'check_identity', lambda row, dst: 'title_in_first_three_pages')
    monkeypatch.setattr(reuse.F.CQ, 'file_quality', lambda *a: dict(ok=False, reason='pdf_no_substantive_text'))
    with pytest.raises(ValueError, match='copy_quality'):
        reuse.check('hit', {}, p, digest)
    monkeypatch.setattr(reuse.F.CQ, 'file_quality', lambda *a: dict(ok=True))
    monkeypatch.setattr(base, 'check_identity', lambda row, dst: 'provider_link_only_review_pending')
    with pytest.raises(ValueError, match='identity not positive'):
        reuse.check('hit', {}, p, digest)
    with pytest.raises(ValueError, match='source changed'):
        reuse.check('hit', {}, p, 'wrong-hash')


def test_write_is_backed_up_locked_and_idempotent(reuse, tmp_path, monkeypatch):
    store = tmp_path / 'hit'
    store.mkdir()
    monkeypatch.setattr(reuse.F, 'FT', tmp_path)
    db = sqlite3.connect(store / 'catalog.sqlite')
    db.executescript('''
        CREATE TABLE works(id TEXT PRIMARY KEY, status TEXT, file_path TEXT, sha256 TEXT,
          byte_count INTEGER, pages INTEGER, download_url TEXT, downloaded_at TEXT, identity_check TEXT);
        INSERT INTO works(id,status) VALUES('w1','queued');
        CREATE TABLE attempts(id INTEGER PRIMARY KEY, work_id TEXT,url TEXT,observed_at TEXT,status TEXT,detail TEXT);
        CREATE TABLE assets(work_id TEXT,kind TEXT,url TEXT,path TEXT,sha256 TEXT,bytes INTEGER,
          version TEXT,license TEXT,source TEXT,at TEXT,identity_check TEXT,PRIMARY KEY(work_id,kind));
        CREATE TABLE receipts(key TEXT PRIMARY KEY,value TEXT);
    ''')
    db.close()
    import catalog_lock as CL
    from contextlib import contextmanager
    original = CL.catalog_lock
    holds = []

    @contextmanager
    def checked_lock(where):
        with original(where):
            with (store / CL.NAME).open('a') as f:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            holds.append(True)
            yield

    monkeypatch.setattr(reuse.F, 'catalog_lock', checked_lock)
    row = dict(work_id='w1', src_path='/source/paper.pdf', sha256='a' * 64, bytes=123,
               pages=2, file_path='objects/paper.pdf', identity='title_in_first_three_pages',
               origin='cross_catalog', rule='cross_doi', placed='hard_link', detail={})
    assert reuse.write_school('hit', [row], 'run1', False) == 1
    backup = next((store / 'backups').glob('*.sqlite'))
    with sqlite3.connect(backup) as old:
        assert old.execute('SELECT status FROM works').fetchone() == ('queued',)
    assert holds
    assert reuse.write_school('hit', [dict(row)], 'run2', False) == 0
    with sqlite3.connect(store / 'catalog.sqlite') as now:
        assert now.execute('SELECT status FROM works').fetchone() == ('downloaded',)
        assert now.execute('SELECT COUNT(*) FROM attempts').fetchone() == (1,)
        detail = json.loads(now.execute('SELECT detail FROM attempts').fetchone()[0])
        assert detail['local_reuse']['rule'] == 'cross_doi'
