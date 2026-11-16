"""fulltext-push/queued_oa_fill.py (2026-11-16): candidates for queued catalog works from the local snapshot's records.
Fixture catalog only: the tool adds candidate rows and nothing else, is idempotent, skips works with a candidate or attempt,
and refuses --write without a fresh backup or while the catalog write lock is held."""
import fcntl
import os
import sqlite3
import time

import pytest

import queued_oa_fill as Q
import ftp_common as F

DDL = """
CREATE TABLE works (id TEXT PRIMARY KEY, title TEXT, doi TEXT, year INTEGER, graph_json TEXT NOT NULL, oa_json TEXT, metadata_source TEXT,
  status TEXT NOT NULL DEFAULT 'queued', file_path TEXT, sha256 TEXT, byte_count INTEGER, pages INTEGER, download_url TEXT,
  downloaded_at TEXT, identity_check TEXT);
CREATE TABLE candidates (work_id TEXT, url TEXT, landing_url TEXT, license TEXT, version TEXT, metadata_source TEXT, PRIMARY KEY(work_id,url));
CREATE TABLE attempts (id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT, status TEXT, detail TEXT);
CREATE TABLE receipts (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT, name TEXT, record_json TEXT);
"""
WORKS = [  # id, doi, status
    ('t_oa_W1', '10.1000/a', 'queued'),       # open location in the fixture record
    ('t_x2', '10.1000/b', 'queued'),          # matched by DOI only, no open location
    ('t_x3', '10.1000/c', 'queued'),          # already has a candidate
    ('t_x4', '10.1000/d', 'queued'),          # already attempted
    ('t_x5', '10.1000/e', 'downloaded'),      # not queued
]
REC = {
    ('t', 't_oa_W1'): dict(locations=[dict(pdf_url='https://repo.example.edu/files/a.pdf', landing_page_url='https://repo.example.edu/a', is_oa=True,
                                           version='acceptedVersion', license='cc-by', source=dict(type='repository', display_name='Repo'))]),
    ('t', 't_x2'): dict(locations=[]),
}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(F, 'FT', tmp_path)
    monkeypatch.setattr(Q.F, 'FT', tmp_path)
    s = tmp_path / 't'
    s.mkdir()
    db = sqlite3.connect(s / 'catalog.sqlite')
    db.executescript(DDL)
    for i, d, st in WORKS:
        db.execute("INSERT INTO works (id, title, doi, graph_json, status) VALUES (?,?,?,?,?)", (i, 'T ' + i, d, '{}', st))
    db.execute("INSERT INTO candidates VALUES ('t_x3','https://x.example/c.pdf',NULL,NULL,NULL,'e')")
    db.execute("INSERT INTO attempts (work_id,url,status) VALUES ('t_x4','https://x.example/d.pdf','failed')")
    db.commit()
    db.close()
    return s


def snapshot(s):
    db = sqlite3.connect(s / 'catalog.sqlite')
    out = {t: db.execute(f'SELECT * FROM {t} ORDER BY 1,2').fetchall() for t in ('works', 'candidates', 'attempts')}
    db.close()
    return out


def backup(tmp, school='t', age=0):
    from datetime import datetime, timezone
    stamp = datetime.fromtimestamp(time.time() - age, timezone.utc).strftime('%Y%m%dT%H%M%S')
    b = tmp / f'catalog-backup-{school}-{stamp}Z.sqlite'
    db = sqlite3.connect(b)
    db.execute('CREATE TABLE works (id TEXT)')
    db.commit()
    db.close()
    os.utime(b, (1, 1))   # cp -p keeps the source's old mtime: the name's stamp decides
    return b


def test_plan_skips_candidates_attempts_and_non_queued(store):
    assert sorted(i for i, _ in Q.queued('t')) == ['t_oa_W1', 't_x2']


def test_wanted_keys_by_id_and_doi():
    want = Q.wanted_keys({'t': [('t_oa_W1', '10.1000/A'), ('t_x2', None)]})
    assert want['https://openalex.org/W1'] == [('t', 't_oa_W1')]
    assert want['https://doi.org/10.1000/a'] == [('t', 't_oa_W1')]
    assert 't_x2' not in str(want)


def test_dry_run_default_writes_nothing(store, tmp_path):
    before = snapshot(store)
    out = Q.run(['t'], plan={'t': Q.queued('t')}, bodies=REC, bulk=lambda w: ([], 0), log=False)
    assert out['t']['works_with_candidate'] == 1 and out['t']['rows'] == 1 and out['t']['written'] == 0
    assert snapshot(store) == before


def test_write_adds_only_candidate_rows_and_is_idempotent(store, tmp_path):
    backup(tmp_path)
    before = snapshot(store)
    kw = dict(write=True, backup_dir=tmp_path, bodies=REC, bulk=lambda w: ([], 0), log=False, ev_dir=tmp_path / 'ev')
    out = Q.run(['t'], **kw)
    assert out['t']['written'] == 1
    after = snapshot(store)
    assert after['works'] == before['works'] and after['attempts'] == before['attempts']   # status, downloads, everything else untouched
    new = [r for r in after['candidates'] if r not in before['candidates']]
    assert [(r[0], r[1]) for r in new] == [('t_oa_W1', 'https://repo.example.edu/files/a.pdf')]
    again = Q.run(['t'], **kw)                      # the work now has a candidate: not planned, nothing added
    assert again['t']['queued'] == 1 and again['t']['written'] == 0
    assert snapshot(store) == after


def test_write_refuses_without_backup(store, tmp_path):
    with pytest.raises(SystemExit, match='no catalog-backup'):
        Q.run(['t'], write=True, backup_dir=tmp_path, bodies=REC, log=False)
    with pytest.raises(SystemExit, match='no catalog-backup'):
        Q.run(['t'], write=True, backup_dir=None, bodies=REC, log=False)


def test_write_refuses_stale_or_broken_backup(store, tmp_path):
    backup(tmp_path, age=13 * 3600)
    with pytest.raises(SystemExit, match='older than'):
        Q.run(['t'], write=True, backup_dir=tmp_path, bodies=REC, log=False)
    for p in tmp_path.glob('catalog-backup-*'):
        p.unlink()
    (tmp_path / 'catalog-backup-t-1.sqlite').write_bytes(b'not a database' * 10)
    with pytest.raises(SystemExit, match='not a readable'):
        Q.run(['t'], write=True, backup_dir=tmp_path, bodies=REC, log=False)


def test_write_refuses_while_the_catalog_lock_is_held(store, tmp_path):
    backup(tmp_path)
    fd = os.open(str(store / '.catalog-write.lock'), os.O_RDWR | os.O_CREAT, 0o664)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        before = snapshot(store)
        with pytest.raises(SystemExit, match='write lock is held'):
            Q.run(['t'], write=True, backup_dir=tmp_path, bodies=REC, log=False, lock_wait=0)
        assert snapshot(store) == before
    finally:
        os.close(fd)


def test_cli_is_dry_by_default(monkeypatch):
    seen = {}
    monkeypatch.setattr(Q, 'run', lambda schools, **kw: seen.update(kw, schools=schools))
    Q.main(['a,b'])
    assert seen['write'] is False and seen['schools'] == ['a', 'b']
    Q.main(['a', '--write', '--backup-dir', '/x'])
    assert seen['write'] is True


def plan_file(store, tmp_path):
    f = tmp_path / 'plan.json.gz'
    Q.make_plan(['t'], f, plan={'t': Q.queued('t')}, bodies=REC, bulk=lambda w: ([], 0))
    return f


def test_plan_is_read_only_and_apply_writes_candidates_only(store, tmp_path):
    before = snapshot(store)
    f = plan_file(store, tmp_path)
    assert snapshot(store) == before                       # the plan touches no catalog
    backup(tmp_path)
    done, skipped = Q.apply_plan(f, ['t'], tmp_path, lock_wait=0, ev_dir=tmp_path / 'ev', log=False)
    assert done['t']['written'] == 1 and done['t']['integrity'] is True and skipped == []
    after = snapshot(store)
    assert after['works'] == before['works'] and after['attempts'] == before['attempts']
    assert [(r[0], r[1]) for r in after['candidates'] if r not in before['candidates']] == [('t_oa_W1', 'https://repo.example.edu/files/a.pdf')]
    again, _ = Q.apply_plan(f, ['t'], tmp_path, lock_wait=0, ev_dir=tmp_path / 'ev', log=False)   # the work has a candidate now
    assert again['t']['still_wanted'] == 0 and again['t']['written'] == 0
    assert snapshot(store) == after


def test_apply_needs_a_fresh_backup(store, tmp_path):
    f = plan_file(store, tmp_path)
    with pytest.raises(SystemExit, match='no catalog-backup'):
        Q.apply_plan(f, ['t'], tmp_path, log=False)


def test_apply_skips_a_locked_school_and_retries_it(store, tmp_path):
    f = plan_file(store, tmp_path)
    backup(tmp_path)
    before = snapshot(store)
    fd = os.open(str(store / '.catalog-write.lock'), os.O_RDWR | os.O_CREAT, 0o664)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        done, skipped = Q.apply_plan(f, ['t'], tmp_path, lock_wait=0, passes=2, ev_dir=tmp_path / 'ev', log=False)
        assert done == {} and skipped == ['t'] and snapshot(store) == before
    finally:
        os.close(fd)
    done, skipped = Q.apply_plan(f, ['t'], tmp_path, lock_wait=0, ev_dir=tmp_path / 'ev', log=False)
    assert done['t']['written'] == 1


def test_lock_wait_polls_until_the_lock_frees(store, tmp_path):
    import threading
    fd = os.open(str(store / '.catalog-write.lock'), os.O_RDWR | os.O_CREAT, 0o664)
    fcntl.flock(fd, fcntl.LOCK_EX)
    threading.Timer(0.6, lambda: os.close(fd)).start()   # closing releases the flock
    t0 = time.monotonic()
    Q.check_no_writer('t', wait=10, poll=0.1)
    assert 0.4 < time.monotonic() - t0 < 5


def test_apply_plan_needs_explicit_write(tmp_path):
    with pytest.raises(SystemExit, match='--write'):
        Q.main(['t', '--apply-plan', str(tmp_path / 'x.json.gz')])
