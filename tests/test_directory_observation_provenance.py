"""Every year of an observed advising interval retains its original proof."""
import hashlib
import json
import sqlite3
import zlib

import labpage_students_school as L
from pihier.students import researched_sources


def test_named_directory_keeps_later_original_and_native_source(monkeypatch):
    first = 'https://web.archive.org/web/20240102000000id_/https://example.edu/students'
    last = 'https://web.archive.org/web/20260203000000id_/https://example.edu/students'
    flat = 'Outgoing Ph.D. Students Bo Chen Advisor: Ann Lee'
    entries = [('Bo Chen', 'Ann Lee', first, 'a' * 64, '20240102000000', 'example.edu/students', flat),
               ('Bo Chen', 'Ann Lee', last, 'b' * 64, '20260203000000', 'example.edu/students', flat)]
    monkeypatch.setattr(L, 'adviser_directory_entries', lambda _: entries)
    row, = L.adviser_directory('fixture', [('Ann Lee', 'Ann Lee')])
    assert row['years'] == [2024, 2026]
    assert {p['url'] for p in row['directory_evidence']} == {first, last}
    assert {p['observed'] for p in row['directory_evidence']} == {'20240102', '20260203'}
    native = researched_sources(row)
    assert {p['sha256'] for p in native} == {'a' * 64, 'b' * 64}
    assert all('Bo Chen' in p['quote'] and 'Ann Lee' in p['quote'] for p in native)


def test_surname_directory_preserves_generic_degree_and_each_capture(monkeypatch, tmp_path):
    pis = tmp_path / 'pis.json'
    pis.write_text(json.dumps([dict(pi='Ann Lee', listings=[
        dict(kind='dept_listing:CSE', year=2024), dict(kind='dept_listing:CSE', year=2026)])]))
    output = tmp_path / 'surname.json'
    page = 'norfolk.example.edu/students'
    cfg = dict(students=dict(surname_adviser_lists=[dict(url=page, department='CSE', format='adviser_column_table')]))
    monkeypatch.setattr(L.S, 'get', lambda _: cfg)
    monkeypatch.setattr(L.W, 'con', lambda _: None)
    monkeypatch.setattr(L.P, 'data', lambda *_a, **_k: pis)
    monkeypatch.setattr(L.P, 'data_w', lambda *_a, **_k: output)
    captures = [dict(timestamp='20240102000000', original='https://' + page),
                dict(timestamp='20260203000000', original='https://' + page)]
    monkeypatch.setattr(L.W, 'cdx_rows', lambda *_a, **_k: captures)
    monkeypatch.setattr(L.W, 'capture', lambda _c, ts, *_a: (
        f'https://web.archive.org/web/{ts}id_/https://{page}', 200, ('a' if ts.startswith('2024') else 'b') * 64, []))
    markup = ('<h1>Full-time Graduate Students</h1><table><tr><th>Name</th><th>Advisor (* Temp)</th></tr>'
              '<tr><td>Chen, Bo</td><td>Lee</td></tr></table>')
    monkeypatch.setattr(L.W, 'raw_html', lambda *_a: markup)
    L.surname_advisers('fixture')
    row = json.loads(output.read_text())[0]['students'][0]
    assert row['role'] == 'graduate'
    assert row['years'] == [2024, 2026]
    assert len(row['directory_evidence']) == 2
    assert all(p['quote'] == 'Chen, Bo' and p['host_quote'] == 'Lee' for p in row['directory_evidence'])
    native = researched_sources(row)
    assert any(p['sha256'] == 'b' * 64 and p['quote'] == 'Chen, Bo' for p in native)
    assert any(p['sha256'] == 'b' * 64 and p['quote'] == 'Lee' for p in native)


def test_cached_live_directory_uses_actual_capture_date(monkeypatch):
    url = 'https://example.edu/students'
    markup = ('<div><span class="stafftemplate--name">Bo Chen</span>'
              '<span>Adviser: Ann Lee<br /></span></div>').encode()
    digest = hashlib.sha256(markup).hexdigest()
    db = sqlite3.connect(':memory:')
    db.execute('create table live(url text, raw_zlib blob, fetched_at text)')
    db.execute('insert into live values(?,?,?)', (url, zlib.compress(markup), '2024-01-02T03:04:05+00:00'))
    cfg = dict(students=dict(adviser_directories=[dict(url=url, live=True)]))
    monkeypatch.setattr(L.S, 'get', lambda _: cfg)
    monkeypatch.setattr(L.S, 'host_use', lambda *_a: 'live')
    monkeypatch.setattr(L.W, 'con', lambda _: db)
    monkeypatch.setattr(L.W, 'live', lambda *_a: (200, digest, [('p', 'Bo Chen Adviser: Ann Lee')]))
    monkeypatch.setattr(L.W, 'cdx_rows', lambda *_a, **_k: [])
    result, = L.adviser_directory_entries('fixture')
    assert result[0:2] == ('Bo Chen', 'Ann Lee')
    assert result[4] == '20240102030405'
    db.close()
