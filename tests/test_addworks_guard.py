"""addworks_guard: backup + sha256 before, id-subset proof after."""
import json
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def guard(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'fulltext-push'))
    import addworks_guard as G
    store = tmp_path / 'st'
    store.mkdir()
    db = sqlite3.connect(store / 'catalog.sqlite')
    db.execute('create table works(id primary key, status)')
    db.executemany('insert into works values (?,?)', [('a', 'queued'), ('b', 'downloaded')])
    db.commit(); db.close()
    monkeypatch.setattr(G.F, 'FT', tmp_path)
    (tmp_path / 'x').mkdir(exist_ok=True)
    monkeypatch.setenv('GUARD_DIR', str(tmp_path / 'g'))
    monkeypatch.setattr(G.F, 'backup_catalog', lambda s, r, keep=3: _backup(s))
    return G, tmp_path


def _backup(store):
    import shutil
    d = Path(store) / 'backups'
    d.mkdir(exist_ok=True)
    shutil.copy(Path(store) / 'catalog.sqlite', d / 'b.sqlite')
    return d / 'b.sqlite'


def test_adding_rows_passes_and_removal_fails(guard, capsys):
    G, tmp = guard
    (tmp / 'st').rename(tmp / 'school')
    G.before('school')
    rec = json.loads((Path(tmp) / 'g' / 'school.before.json').read_text())
    assert rec['works_before'] == 2 and len(rec['backup_sha256']) == 64
    db = sqlite3.connect(tmp / 'school' / 'catalog.sqlite')
    db.execute("insert into works values ('c','queued')"); db.commit(); db.close()
    assert G.after('school') == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out['added'] == 1 and out['removed'] == 0 and out['backup_unchanged']
    db = sqlite3.connect(tmp / 'school' / 'catalog.sqlite')
    db.execute("delete from works where id='a'"); db.commit(); db.close()
    assert G.after('school') == 1
