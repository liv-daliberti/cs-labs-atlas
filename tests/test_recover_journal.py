"""ftp_common.recover_journal: a hot <db>-journal left by a killed writer is rolled back by a read-write open, so a read-only open then works."""
import shutil
import sqlite3

import ftp_common as F


def test_hot_journal_is_recovered(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    db = src / 'catalog.sqlite'
    c = sqlite3.connect(db, isolation_level=None)
    c.execute('create table t(a)')
    c.execute('insert into t values (1)')
    c.execute('PRAGMA cache_size=1')
    c.execute('begin')
    c.executemany('insert into t values (?)', [('x' * 200,) for _ in range(5000)])   # spills dirty pages: the journal and the db file now differ from the commit
    dead = tmp_path / 'dead'
    dead.mkdir()
    for suf in ('', '-journal'):
        shutil.copy(str(db) + suf, str(dead / ('catalog.sqlite' + suf)))   # what a killed writer leaves behind
    c.execute('rollback')
    c.close()
    ro = sqlite3.connect(f"file:{dead / 'catalog.sqlite'}?mode=ro", uri=True)
    try:
        ro.execute('select count(*) from t').fetchone()
        pass
    except sqlite3.OperationalError:
        pass
    ro.close()
    F.recover_journal(dead / 'catalog.sqlite')
    ro = sqlite3.connect(f"file:{dead / 'catalog.sqlite'}?mode=ro", uri=True)
    assert ro.execute('select count(*) from t').fetchone()[0] == 1
