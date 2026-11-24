"""warm_copy_cache: fills the per-store cache from a read-only catalog scan; a second run reads the cache, not the files."""
import sqlite3

import copy_quality as CQ
import warm_copy_cache as W

XML = '<article><body>' + ''.join(f'<p>{"word " * 60}{i}</p>' for i in range(3)) + '</body></article>'


def make_store(tmp_path):
    store = tmp_path / 'store'
    (store / 'objects').mkdir(parents=True)
    f = store / 'objects' / 'a.xml'
    f.write_text(XML)
    db = sqlite3.connect(store / 'catalog.sqlite')
    db.execute('create table works(id, title, doi, year, graph_json, metadata_source, status, file_path, sha256, byte_count, download_url, identity_check)')
    db.execute('create table assets(work_id, kind, path, sha256, bytes, identity_check, url, version, license)')
    db.execute("insert into works(id,title,status) values ('w1','T','fulltext_xml')")
    db.execute("insert into works(id,title,status) values ('w2','U','queued')")
    import hashlib
    db.execute("insert into assets values ('w1','xml','objects/a.xml',?,?,NULL,NULL,NULL,NULL)", (hashlib.sha256(XML.encode()).hexdigest(), len(XML.encode())))
    db.commit()
    db.close()
    return store


def test_warm_fills_cache_then_reuses_it(tmp_path, monkeypatch):
    monkeypatch.delenv('COPY_QUALITY_CACHE_DIR', raising=False)
    store = make_store(tmp_path)
    logs = []
    rec = W.warm('x', 2, store=store, log=lambda m, **k: logs.append(m))
    assert rec['works'] == 1 and rec['unconfirmed'] == 0 and (store / CQ.CACHE_NAME).exists() and (store / '.copy-quality-warm.json').exists()
    CQ._CACHE.clear()
    CQ._PERSIST.clear()
    monkeypatch.setattr(CQ, 'xml_quality', lambda d: (_ for _ in ()).throw(AssertionError('re-parsed')))
    assert W.warm('x', 2, store=store, log=lambda m, **k: None)['unconfirmed'] == 0


def test_runs_as_a_script_under_python_dash_I():
    """The Slurm job runs `python -I warm_copy_cache.py <school>`: no PYTHONPATH, so every import must resolve through the script's own sys.path edit."""
    import subprocess
    import sys
    from pathlib import Path
    script = Path(W.__file__)
    r = subprocess.run([sys.executable, '-I', str(script)], capture_output=True, text=True, cwd=script.parent)
    assert r.returncode == 0, r.stderr
