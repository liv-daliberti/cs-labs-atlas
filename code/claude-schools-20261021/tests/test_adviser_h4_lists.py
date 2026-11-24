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


def test_h4_directory_linked_coadvisers_match_page_text(monkeypatch):
    """Two linked advisers: the tag strip must not leave 'Lee , Bo' where the page text reads 'Lee, Bo' (JHU 2026-11-24)."""
    html = '''<h4>Ada Student</h4><p>Email: <a href="mailto:[email removed]">[email removed]</a><br />
Advisors: <a href="https://x.edu/ann-lee/">Ann Lee</a>, <a href="https://x.edu/bo-chen/">Bo Chen</a><br />
Research Interests: Topic</p>'''
    flat = 'Ada Student Email: [email removed] Advisors: Ann Lee, Bo Chen Research Interests: Topic'
    c = sqlite3.connect(':memory:')
    c.execute('create table live(url text, fetched_at text, status int, sha256 text)')
    c.execute('insert into live values (?,?,?,?)', ('https://example.edu/phd/', '2026-11-07T12:00:00Z', 200, 'abc'))
    monkeypatch.setattr(L.W, 'con', lambda key: c)
    monkeypatch.setattr(L.S, 'get', lambda key: {'students': {'adviser_h4_lists': ['example.edu/phd/']}})
    monkeypatch.setattr(L.W, 'live_html', lambda c, u: html)
    monkeypatch.setattr(L.W, 'live', lambda c, u: (200, 'abc', [('text', flat)]))
    monkeypatch.setattr(L.W, 'cdx_rows', lambda *a, **kw: [])
    rows = L.adviser_h4_lists('school', [('Ann Lee', 'Ann Lee'), ('Bo Chen', 'Bo Chen')])
    assert [(r['student'], r['pi']) for r in rows] == [('Ada Student', 'Ann Lee'), ('Ada Student', 'Bo Chen')]
    assert all(r['host_quote'] == 'Advisors: Ann Lee, Bo Chen' for r in rows)


def test_historical_directory_div_fields_split_name_and_parenthetical_adviser():
    html = '''<div><h3><span>Anton </span><span>Belyy </span></h3>
    <div><span>Group(s): </span><span>Language &amp; Speech</span></div>
    <div><span>Adviser(s): </span><span>Benjamin Van Durme, Vladimir Braverman</span></div>
    <div><span>Research Interests: </span><span>NLP</span></div></div>
    <div><h3>Unassigned Student</h3><div>Research with Ann Lee</div></div>
    <div><h3>Other Student</h3><div>Adviser(s): Joann Lee</div></div>'''
    assert list(L.adviser_heading_entries(html)) == [
        ('Anton Belyy', 'Benjamin Van Durme, Vladimir Braverman',
         'Adviser(s): Benjamin Van Durme, Vladimir Braverman'),
        ('Other Student', 'Joann Lee', 'Adviser(s): Joann Lee'),
    ]


def test_directory_ignores_later_card_and_nonadviser_research_text():
    html = '''<h4>Unassigned Student</h4><p>Research with Ann Lee</p>
    <div><h4>Assigned Student</h4><p>Advisor: Ann Lee<br/>Research Interests: Vision</p></div>'''
    assert list(L.adviser_heading_entries(html)) == [
        ('Assigned Student', 'Ann Lee', 'Advisor: Ann Lee'),
    ]
