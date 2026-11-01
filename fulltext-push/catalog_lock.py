"""One writer per catalog (ROADMAP item 11; 2026-10-31; docs/STORES.md).

Every write transaction on a store's catalog.sqlite holds <store>/.catalog-write.lock (an flock) from its first write to
its commit: the download collector (each saved result, the pass-start requeue), the channels' candidate writes
(ftp_common.write_batches / write_candidates), imports and the recovery tools (requeue_causes, revert_downloads,
review_access apply, quarantine_robots_ai apply, identity_review apply). The lock is short (one batch of at most 200
rows); a writer waits for it up to `timeout` seconds and then refuses (CatalogBusy), so no tool writes beside another.
The download loop's own <store>/.loop.lock (one loop per store) is separate and long-lived.
usage:  with catalog_lock(store_dir): ...writes...; db.commit()
        with catalog_lock_for(db): ...       (the store of an open sqlite3 connection)
"""
import fcntl, os, time
from contextlib import contextmanager
from pathlib import Path

NAME = '.catalog-write.lock'


class CatalogBusy(RuntimeError):
    pass


@contextmanager
def catalog_lock(store, timeout=1800, poll=0.5):
    p = Path(store) / NAME
    fd = os.open(str(p), os.O_RDWR | os.O_CREAT, 0o664)
    try:
        end = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > end:
                    raise CatalogBusy(f'{p} held by another writer for over {timeout} s')
                time.sleep(poll)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def store_of(db):
    """The directory of an open connection's main database file."""
    for _, name, path in db.execute('PRAGMA database_list').fetchall():
        if name == 'main' and path:
            return Path(path).parent
    raise ValueError('not a file database')


def catalog_lock_for(db, timeout=1800):
    return catalog_lock(store_of(db), timeout)


def backup_catalog(store, reason, keep=3):
    """A consistent snapshot of <store>/catalog.sqlite before a bulk write (2026-10-31; docs/STORES.md): sqlite's online
    backup API, taken while holding the catalog write lock, into <store>/backups/catalog.<reason>-<UTC date>.sqlite
    (written to a .part file and renamed, so a half-copy never looks like a backup). Then only the newest `keep`
    catalog.*.sqlite files stay. Call it before the tool's own locked writes (the lock is not re-entrant). Returns the path."""
    import sqlite3
    from datetime import datetime, timezone
    store = Path(store)
    bdir = store / 'backups'
    bdir.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    dest = bdir / f'catalog.{reason}-{now:%Y%m%d}.sqlite'
    if dest.exists():
        dest = bdir / f'catalog.{reason}-{now:%Y%m%d-%H%M%S}.sqlite'
    part = Path(str(dest) + '.part')
    with catalog_lock(store):
        src = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
        dst = sqlite3.connect(str(part))
        try:
            src.backup(dst)
        finally:
            dst.close(); src.close()
        os.replace(part, dest)
    old = sorted(bdir.glob('catalog.*.sqlite'), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[keep:]
    for p in old:
        p.unlink()
    return dest
