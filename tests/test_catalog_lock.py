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
