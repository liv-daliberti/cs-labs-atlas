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
