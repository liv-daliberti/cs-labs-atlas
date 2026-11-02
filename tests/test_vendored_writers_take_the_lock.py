"""The Princeton package importers and the Infoscience / DSpace resolvers write the catalog only under the catalog write lock,
with a locked backup first for a bulk write (ROADMAP #20, docs/STORES.md)."""
import fcntl
import os
import sys
from pathlib import Path

import pytest

CODE = Path(__file__).resolve().parents[1]
for d in (CODE / 'fulltext-push', CODE / 'vendor' / 'princeton_tools'):
    if str(d) not in sys.path:
        sys.path.append(str(d))
import catalog_lock as CL  # noqa: E402
import import_all_when_free as IA  # noqa: E402


def test_the_package_import_runs_under_the_catalog_lock(tmp_path, monkeypatch):
    stub = tmp_path / 'stubs'
    stub.mkdir()
    probe = tmp_path / 'probe.txt'
    (stub / 'stubmod.py').write_text(
        'import fcntl, os\n'
        'def import_catalog():\n'
        f"    fd = os.open({str(tmp_path / '.catalog-write.lock')!r}, os.O_RDWR)\n"
        '    try:\n'
        '        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); held = False\n'
        '    except BlockingIOError:\n'
        '        held = True\n'
        f"    open({str(probe)!r}, 'w').write(str(held))\n")
    monkeypatch.setenv('PYTHONPATH', str(stub))
    monkeypatch.setattr(IA, 'FULLTEXT', tmp_path)
    monkeypatch.setattr(IA, 'DISC', tmp_path / 'discovery')
    IA.run('stubmod', 'pkg')
    assert probe.read_text() == 'True'  # the importer's own lock fd was held while import_catalog ran
    fd = os.open(str(tmp_path / '.catalog-write.lock'), os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # and it is released afterwards
    os.close(fd)


def test_a_busy_catalog_is_a_retry_not_an_error(tmp_path, monkeypatch):
    stub = tmp_path / 'stubs'
    stub.mkdir()
    (stub / 'stubmod.py').write_text('def import_catalog():\n    pass\n')
    monkeypatch.setenv('PYTHONPATH', str(stub))
    monkeypatch.setattr(IA, 'FULLTEXT', tmp_path)
    monkeypatch.setattr(IA, 'DISC', tmp_path / 'discovery')
    monkeypatch.setattr(CL, 'catalog_lock', CL.catalog_lock)
    with CL.catalog_lock(tmp_path):
        # the child waits on the held lock; a short timeout turns that into CatalogBusy, which run() maps to a retry
        import subprocess
        real = subprocess.run

        def quick(cmd, **kw):
            cmd = list(cmd)
            cmd[-1] = cmd[-1].replace('CL.catalog_lock(', 'CL.catalog_lock(timeout=1, store=')
            return real(cmd, **kw)
        monkeypatch.setattr(subprocess, 'run', quick)
        with pytest.raises(BlockingIOError):
            IA.run('stubmod', 'pkg')


@pytest.mark.parametrize('rel', ['vendor/epfl_tools/epfl_infoscience_rest.py', 'vendor/mit_tools/mit_dspace_rest.py'])
def test_resolvers_lock_every_candidate_write_and_back_up_a_bulk_one(rel):
    src = (CODE / rel).read_text()
    assert 'with CL.catalog_lock(OUT):' in src
    assert src.index('with CL.catalog_lock(OUT):') < src.index("INSERT OR IGNORE INTO candidates")
    assert 'if len(rows) > 1000:' in src and 'CL.backup_catalog(OUT,' in src
    assert src.index('CL.backup_catalog(OUT,') < src.index("sqlite3.connect(str(OUT / 'catalog.sqlite')")


def test_the_one_package_importer_locks_and_backs_up_once():
    src = (CODE / 'vendor/princeton_tools/import_when_free.py').read_text()
    assert "CL.backup_catalog(FULLTEXT, 'before-import')" in src and 'import_locked(name)' in src
    assert 'with CL.catalog_lock(FULLTEXT):' in src
