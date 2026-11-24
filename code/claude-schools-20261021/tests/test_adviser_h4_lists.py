"""A department's PhD directory must bind each adviser only to their own entry."""
import sqlite3

import labpage_students_school as L


def test_h4_directory_coadvisers_entry_boundaries_and_capture_year(monkeypatch):
    html = '''<h4>Ada Student</h4><p>Advisor: Ann Lee and Bo Chen<br/>Topic</p>
    <h4>Other Student</h4><p>Advisor: Joann Lee<br/>Topic</p>
    <h4>Unassigned Student</h4><p>Research with Ann Lee<br/>Topic</p>'''
    flat = 'Ada Student Advisor: Ann Lee and Bo Chen Topic Other Student Advisor: Joann Lee Topic Unassigned Student Research with Ann Lee Topic'
    c = sqlite3.connect(':memory:')
    c.execute('create table live(url text, fetched_at text, status int, sha256 text)')
    c.execute('insert into live values (?,?,?,?)', ('https://example.edu/phd/', '2024-11-07T12:00:00Z', 200, 'abc'))
    monkeypatch.setattr(L.W, 'con', lambda key: c)
    monkeypatch.setattr(L.S, 'get', lambda key: {'students': {'adviser_h4_lists': ['example.edu/phd/']}})
    monkeypatch.setattr(L.W, 'live_html', lambda c, u: html)
    monkeypatch.setattr(L.W, 'live', lambda c, u: (200, 'abc', [('text', flat)]))
    monkeypatch.setattr(L.W, 'cdx_rows', lambda *a, **kw: [])
    rows = L.adviser_h4_lists('school', [('Ann Lee', 'Ann Lee'), ('Bo Chen', 'Bo Chen')])
    assert [(r['student'], r['pi']) for r in rows] == [('Ada Student', 'Ann Lee'), ('Ada Student', 'Bo Chen')]
    assert all(r['years'] == [2024, 2024] and r['sha256'] == 'abc' for r in rows)
    assert all(r['host_quote'] == 'Advisor: Ann Lee and Bo Chen' for r in rows)
