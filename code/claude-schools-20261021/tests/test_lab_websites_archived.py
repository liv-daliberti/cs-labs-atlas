"""Malformed saved archive metadata must not prevent valid source replay."""
import sqlite3
import zlib

import lab_websites as W


def test_missing_archive_url_is_skipped_without_creating_a_link(tmp_path, monkeypatch):
    import labpage_audit as L
    monkeypatch.setattr(L, 'SCHOOLS', {'u': {'domain': r'school\.edu'}})
    path = tmp_path / 'captures.sqlite'
    body = b'<h1>Ada Example</h1><a href="https://homes.school.edu/ada/">Website</a>'
    with sqlite3.connect(path) as con:
        con.execute('create table captures(capture_url text, wayback_timestamp text, http_status integer, sha256 text, raw_zlib blob)')
        con.executemany('insert into captures values (?,?,?,?,?)', [
            (None, '20260102', 200, 'a' * 64, zlib.compress(body)),
            ('', '20260101', 200, 'b' * 64, zlib.compress(body))])
    monkeypatch.setattr(W.P, 'data', lambda name, school=None, **kw: path)
    row = dict(pi='Ada Example', coverage='website', url='https://homes.school.edu/ada/', checks=[])
    assert W.archived_official_links('u', {'labs': [row]})['labs'][0].get('official_link_status') != 'recorded'
    with sqlite3.connect(path) as con:
        con.execute('insert into captures values (?,?,?,?,?)', (
            'https://web.archive.org/web/20251201000000id_/https://www.school.edu/ada/',
            '20251201000000', 200, 'c' * 64, zlib.compress(body)))
    out = W.archived_official_links('u', {'labs': [row]})['labs'][0]
    assert out['official_link_status'] == 'recorded'
    assert out['official_link_evidence'][0]['source_sha256'] == 'c' * 64
