import sqlite3
import zlib

import cs_related_school as CR


def test_js_rendered_listing_is_a_unit_page(monkeypatch):
    c = sqlite3.connect(':memory:')
    c.execute('create table captures (capture_url, page_url, department, wayback_timestamp, http_status, sha256, text)')
    c.execute('create table live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    c.execute('create table js_render (url text, fetched_at text, status text, raw_http int, raw_sha256 text, raw_zlib blob, dom_sha256 text, dom_zlib blob, '
              'resources text, tool text, browser text, driver text, wait_css text, note text, primary key (url, fetched_at))')
    shell = b'<html><body><div id="root"></div><noscript>You need to enable JavaScript</noscript></body></html>'
    c.execute('insert into live values (?,?,?,?,?,?,?)', ('https://id.example.org/people/Faculty', '2026-11-24T10:00:00', 200, 'shellsha', 'text/html', zlib.compress(shell), ''))
    dom = '<html><body><div id="root"><div>Andrea Bianchi Associate Professor andrea@x.org</div><div>Ho-jun Ji Adjunct Professor</div></div></body></html>'.encode()
    c.execute('insert into js_render values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', ('https://id.example.org/people/Faculty', '2026-11-24T12:00:00', 'ok', 200, 'r', zlib.compress(shell), 'domsha',
                                                                              zlib.compress(dom), '[]', 't', 'b', 'd', '', ''))
    c.execute('insert into js_render values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', ('https://id.example.org/people/Faculty', '2026-11-24T11:00:00', 'challenge', 200, 'r', zlib.compress(shell), 'bad',
                                                                              zlib.compress(b'<p>challenge</p>'), '[]', 't', 'b', 'd', '', ''))
    monkeypatch.setattr(CR.S, 'get', lambda key: {'affiliated_units': [dict(code='ID', listings=['id.example.org/people/Faculty'])]})
    monkeypatch.setattr(CR.W, 'con', lambda key: c)
    pages = CR.unit_pages('k')
    assert [(p[0], p[1], p[2]) for p in pages] == [('ID', 'https://id.example.org/people/Faculty', 'domsha')]   # the shell and the failed render are not pages
    assert 'Andrea Bianchi Associate Professor' in pages[0][4]
    ev = CR.faculty_evidence([pages[0]], ['Andrea Bianchi'], '', single_person=False)
    assert ev and ev[0]['ladder']
    assert not [e for e in CR.faculty_evidence([pages[0]], ['Ho-jun Ji'], CR.not_ladder_titles('k') or 'Adjunct', single_person=False) if e['ladder']]
