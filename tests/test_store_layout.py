"""A store's layout before a collector runs (fulltext-push/store_layout.py), and the status page's alarm for attempts
without downloads (fulltext-push/collectors_status.py); 2026-10-31, Michigan's missing sources/."""
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FTP = Path(__file__).resolve().parents[1] / 'fulltext-push'
if str(FTP) not in sys.path:
    sys.path.append(str(FTP))
import store_layout as SL  # noqa: E402


def test_missing_directories_are_created(tmp_path):
    (tmp_path / 'catalog.sqlite').write_bytes(b'')
    made = SL.ensure(tmp_path)
    assert {'sources/', 'staged/', 'objects/', 'by_lab/', 'summary.json'} <= set(made)
    assert SL.ensure(tmp_path) == []


def test_refuses_without_a_catalog_or_when_asked_not_to_create(tmp_path):
    with pytest.raises(SL.StoreLayoutError):
        SL.ensure(tmp_path)
    (tmp_path / 'catalog.sqlite').write_bytes(b'')
    with pytest.raises(SL.StoreLayoutError):
        SL.ensure(tmp_path, create=False)


def test_status_page_alarms_on_attempts_without_downloads(tmp_path, monkeypatch):
    import collectors_status as CS
    import ftp_common as F
    st = tmp_path / 'stores' / 'michigan'
    st.mkdir(parents=True)
    db = sqlite3.connect(str(st / 'catalog.sqlite'))
    db.execute('CREATE TABLE attempts (id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT, status TEXT, detail TEXT)')
    now = datetime.now(timezone.utc).isoformat()
    db.executemany('INSERT INTO attempts(work_id, url, observed_at, status, detail) VALUES (?,?,?,?,?)',
                   [(f'w{i}', 'u', now, 'worker_error', "[Errno 2] No such file or directory: 'sources/x-robots.txt'") for i in range(5)])
    db.commit(); db.close()
    monkeypatch.setattr(F, 'FT', tmp_path / 'stores')
    monkeypatch.setattr(F, 'SCHOOLS', tmp_path)
    r = CS.school_status('michigan')
    assert r['attempts_24h'] == 5 and r['downloads_24h'] == 0
    assert 'no download in 24 h' in r['alarm'] and 'No such file' in r['alarm']
