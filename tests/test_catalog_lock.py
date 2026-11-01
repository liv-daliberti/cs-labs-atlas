"""One writer per catalog (fulltext-push/catalog_lock.py; ROADMAP item 11): a second writer waits, then refuses."""
import sqlite3
import sys
import threading
from pathlib import Path

import pytest

FTP = Path(__file__).resolve().parents[1] / 'fulltext-push'
if str(FTP) not in sys.path:
    sys.path.append(str(FTP))
import catalog_lock as CL  # noqa: E402


def test_second_writer_refuses_while_the_lock_is_held(tmp_path):
    held, release = threading.Event(), threading.Event()

    def holder():
        with CL.catalog_lock(tmp_path):
            held.set(); release.wait(5)
    t = threading.Thread(target=holder); t.start(); held.wait(5)
    with pytest.raises(CL.CatalogBusy):
        with CL.catalog_lock(tmp_path, timeout=0.5, poll=0.1):
            pass
    release.set(); t.join()
    with CL.catalog_lock(tmp_path, timeout=1):  # free again
        pass


def test_write_batches_takes_the_lock(tmp_path):
    import ftp_common as F
    db = sqlite3.connect(str(tmp_path / 'catalog.sqlite'))
    db.execute('CREATE TABLE t (x INTEGER)')
    assert CL.store_of(db) == tmp_path
    assert F.write_batches(db, 'INSERT INTO t VALUES (?)', [(i,) for i in range(5)]) == 5
    assert (tmp_path / CL.NAME).exists()


def test_backup_catalog_snapshots_under_the_lock_and_keeps_three(tmp_path):
    db = sqlite3.connect(str(tmp_path / 'catalog.sqlite'))
    db.execute('CREATE TABLE t (x INTEGER)'); db.executemany('INSERT INTO t VALUES (?)', [(i,) for i in range(100)]); db.commit(); db.close()
    import os
    made = []
    for i in range(5):
        p = CL.backup_catalog(tmp_path, f'r{i}')
        os.utime(p, (1000 + i, 1000 + i)); made.append(p)
    left = sorted(q.name for q in (tmp_path / 'backups').glob('catalog.*'))
    assert left == sorted(p.name for p in made[2:])  # the newest three
    snap = sqlite3.connect(str(made[-1]))
    assert snap.execute('SELECT COUNT(*) FROM t').fetchone()[0] == 100
    assert not list((tmp_path / 'backups').glob('*.part'))
    with CL.catalog_lock(tmp_path, timeout=1):  # the lock was released
        pass
    held = threading.Event(), threading.Event()

    def holder():
        with CL.catalog_lock(tmp_path):
            held[0].set(); held[1].wait(5)
    t = threading.Thread(target=holder); t.start(); held[0].wait(5)
    import catalog_lock
    orig = catalog_lock.catalog_lock
    catalog_lock.catalog_lock = lambda s, timeout=1800, poll=0.5: orig(s, timeout=0.3, poll=0.1)
    try:
        with pytest.raises(CL.CatalogBusy):  # a snapshot waits for the writer like any other
            CL.backup_catalog(tmp_path, 'blocked')
    finally:
        catalog_lock.catalog_lock = orig; held[1].set(); t.join()
