"""Georgia Tech 2026-11-04/05: a charter school has only the lab-page audit's capture store (labpage-audit-captures.sqlite). The
labpages channel crashed on the missing labpage-captures.sqlite and the ledger marked every paper incomplete_check."""
import sqlite3

import labpage_channel as lc


def test_audit_captures_are_the_fallback(tmp_path, monkeypatch):
    files = {'labpage-captures.sqlite': tmp_path / 'a.sqlite', 'labpage-audit-captures.sqlite': tmp_path / 'b.sqlite'}
    monkeypatch.setattr(lc.F.P, 'data', lambda name, school=None, **k: files[name])
    assert lc.captures_db('x') == files['labpage-audit-captures.sqlite']
    files['labpage-captures.sqlite'].write_bytes(b'')
    assert lc.captures_db('x') == files['labpage-captures.sqlite']


def test_iter_captures_reads_the_audit_store(tmp_path, monkeypatch):
    db = tmp_path / 'b.sqlite'
    c = sqlite3.connect(db)
    c.execute('create table captures (id integer primary key autoincrement, url text, final_url text, capture_url text, status int, content_type text, content blob)')
    c.execute("insert into captures(url, final_url, capture_url, status, content_type, content) values ('https://a.edu/x', null, null, 200, 'text/html', ?)", (b'<html>x</html>',))
    c.commit(); c.close()
    monkeypatch.setattr(lc.F.P, 'data', lambda name, school=None, **k: tmp_path / ('none.sqlite' if name == 'labpage-captures.sqlite' else 'b.sqlite'))
    assert [r[0] for r in lc.iter_captures('x')] == ['https://a.edu/x']
