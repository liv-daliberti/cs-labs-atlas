"""repath_evidence: old evidence prefixes map to the store, and only when the mapped file exists."""
import sqlite3
import sys
from pathlib import Path

FTP = Path(__file__).resolve().parents[1] / 'fulltext-push'
if str(FTP) not in sys.path:
    sys.path.append(str(FTP))
import ftp_common as F  # noqa: E402
import repath_evidence as R  # noqa: E402

OLD = '/n/fs/similarity/homogenizing-science/data/fulltext/cmu/'


def test_mapped_covers_every_old_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(F, 'FT', tmp_path)
    for p in R.old_prefixes('cmu'):
        assert R.mapped('cmu', p + 'discovery/x.json') == f'{tmp_path}/cmu/discovery/x.json'
    assert R.mapped('cmu', '/elsewhere/x.json') is None and R.mapped('cmu', None) is None


def test_apply_repoints_only_existing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(F, 'FT', tmp_path)
    store = tmp_path / 'cmu'
    (store / 'discovery').mkdir(parents=True)
    (store / 'discovery' / 'here.json').write_text('{}')
    db = sqlite3.connect(str(store / 'catalog.sqlite'))
    for t in ('candidates', 'assets', 'works'):
        db.execute(f'CREATE TABLE {t} (metadata_source TEXT)')
        db.executemany(f'INSERT INTO {t} VALUES (?)', [(OLD + 'discovery/here.json',), (OLD + 'discovery/gone.json',), ('/other',)])
    db.execute('CREATE TABLE attempts (id INTEGER PRIMARY KEY, detail TEXT)')
    db.execute('CREATE TABLE work_lab_sources (work_id TEXT, evidence_path TEXT)')  # Princeton-only evidence table
    db.executemany('INSERT INTO work_lab_sources VALUES (?,?)', [('a', OLD + 'discovery/here.json'), ('b', OLD + 'discovery/gone.json')])
    db.commit(); db.close()
    R.apply('cmu')
    db = sqlite3.connect(str(store / 'catalog.sqlite'))
    for t in ('candidates', 'assets', 'works'):
        assert [r[0] for r in db.execute(f'SELECT metadata_source FROM {t} ORDER BY rowid')] == [
            str(store / 'discovery' / 'here.json'), OLD + 'discovery/gone.json', '/other']
    assert [r[0] for r in db.execute('SELECT evidence_path FROM work_lab_sources ORDER BY rowid')] == [
        str(store / 'discovery' / 'here.json'), OLD + 'discovery/gone.json']
    assert (store / CL_NAME()).exists()


def CL_NAME():
    import catalog_lock
    return catalog_lock.NAME
