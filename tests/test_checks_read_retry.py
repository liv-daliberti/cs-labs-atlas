"""checks.latest survives a writer's hot journal (2026-11-21): the 2026-11-19 ledger run died on 'attempt to write a readonly
database' when a download loop's channel was mid-commit on the checks store; the read is retried on a fresh connection."""
import sqlite3

import pytest

import checks as C


def store(tmp_path):
    p = tmp_path / 'x.sqlite'
    db = sqlite3.connect(p)
    db.execute(f'CREATE TABLE checks (id INTEGER PRIMARY KEY, {", ".join(c for c in C.COLS)})')
    db.execute(f'INSERT INTO checks ({", ".join(C.COLS)}) VALUES ({", ".join("?" * len(C.COLS))})',
               ['k1' if c == 'paper_key' else 'openalex' if c == 'channel' else '2026-11-21T00:00:00+00:00' if c == 'at' else None for c in C.COLS])
    db.commit(); db.close()
    return p


def test_retries_a_transient_readonly_error(tmp_path, monkeypatch):
    p = store(tmp_path)
    monkeypatch.setattr(C, 'READ_WAIT_S', 0)
    calls = {'n': 0}

    def flaky(db):
        calls['n'] += 1
        if calls['n'] < 3:
            raise sqlite3.OperationalError('attempt to write a readonly database')
        return db.execute('SELECT COUNT(*) FROM checks').fetchone()[0]
    assert C._read(p, flaky) == 1 and calls['n'] == 3
    assert list(C.latest('x', path=p)) == [('k1', 'openalex')]


def test_other_errors_and_exhaustion_raise(tmp_path, monkeypatch):
    p = store(tmp_path)
    monkeypatch.setattr(C, 'READ_WAIT_S', 0)
    with pytest.raises(sqlite3.OperationalError, match='no such table'):
        C._read(p, lambda d: d.execute('SELECT * FROM nope').fetchall())
    monkeypatch.setattr(C, 'READ_TRIES', 2)

    def always(db):
        raise sqlite3.OperationalError('database is locked')
    with pytest.raises(sqlite3.OperationalError, match='locked'):
        C._read(p, always)


def abandoned_journal(tmp_path):
    """A copy of a store taken mid-transaction: the database file already holds uncommitted pages and its hot journal sits
    beside it with no writer alive, as a channel killed mid-commit leaves it."""
    src = store(tmp_path)
    w = sqlite3.connect(src, isolation_level=None)
    w.execute('PRAGMA cache_size=1'); w.execute('BEGIN')
    for i in range(3000):
        w.execute('INSERT INTO checks (paper_key, channel) VALUES (?, ?)', (f'p{i}' * 20, 'openalex'))
    dst = tmp_path / 'y.sqlite'
    assert (tmp_path / 'x.sqlite-journal').exists()
    dst.write_bytes(src.read_bytes()); (tmp_path / 'y.sqlite-journal').write_bytes((tmp_path / 'x.sqlite-journal').read_bytes())
    w.execute('ROLLBACK'); w.close()
    return dst


def test_an_abandoned_journal_is_rolled_back(tmp_path, monkeypatch):
    p = abandoned_journal(tmp_path)
    monkeypatch.setattr(C, 'READ_WAIT_S', 0)
    with pytest.raises(sqlite3.OperationalError, match='readonly'):
        db = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
        db.execute('SELECT COUNT(*) FROM checks').fetchone()
    db.close()
    assert C._read(p, lambda d: d.execute('SELECT COUNT(*) FROM checks').fetchone()[0]) == 1   # the last committed state
    assert not (tmp_path / 'y.sqlite-journal').exists()
    assert list(C.latest('y', path=p)) == [('k1', 'openalex')]
