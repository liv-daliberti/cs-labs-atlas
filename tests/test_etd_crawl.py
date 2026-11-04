"""Dissertation item-page crawl for the adviser field (fulltext-push/etd_crawl.py), on fixture pages shaped like Georgia Tech's DSpace 7 render
and UChicago's InvenioRDM record page: parsers, dissertation filter, login pages, robots, resumable queue, advisor-to-PI evidence rows."""
import json
import types

import pytest

import etd_crawl as E
import oai_repo as O

GT = """<html><head><title>Study of Things</title>
<meta name="citation_title" content="Study of Things"><meta name="citation_author" content="Chang, Tina R.">
<meta name="citation_publication_date" content="2019-08"></head><body>
<h2 class="simple-view-element-header">Author(s)</h2><div class="simple-view-element-body"><span class="dont-break-out"> Chang, Tina R. </span></div>
<h2 class="simple-view-element-header">Advisor(s)</h2><div class="simple-view-element-body"><a href="/entities/person/x">Maple, Terry L.</a>
<a href="/entities/person/y">Other, Person</a></div>
<h2 class="simple-view-element-header">Date</h2><div class="simple-view-element-body"><span>2019-08</span></div>
<h2 class="simple-view-element-header">Resource Subtype</h2><div class="simple-view-element-body"><span>%s</span></div>
<h2 class="simple-view-element-header">Associated Organization(s)</h2><div class="simple-view-element-body"><span>School of Computer Science</span></div>
</body></html>"""
GT_LOGIN = '<html><head><title>DSpace Repository :: Login</title></head><body>login</body></html>'
UC = """<html><head><meta name="citation_title" content="Flow-directed Closure Conversion"><meta name="citation_author" content="Zhong, Byron"></head><body>
<p>Published December 2024</p><p>Version v1 Thesis Open Flow-directed</p>
<h3 class="creatibutors-header ui small header">Advisor:</h3><ul class="creatibutors"><li><a><span class="creatibutor-name">Reppy, John</span></a></li></ul>
<h3 class="creatibutors-header ui small header">Committee members:</h3><ul class="creatibutors"><li><span class="creatibutor-name">Chugh, Ravi</span></li></ul>
<dl><dt>Department(s)</dt><dd> Computer Science </dd></dl></body></html>"""
PIS = [dict(pi='Terry Maple', names=['Terry Maple']), dict(pi='John Reppy', names=['John H. Reppy']), dict(pi='Tina Chang', names=['Tina Chang'])]


def test_dspace7_parser():
    p = E.parse_dspace7(GT % 'Dissertation')
    assert p['author'] == 'Chang, Tina R.' and p['advisors'] == ['Maple, Terry L.', 'Other, Person'] and p['year'] == 2019
    assert p['dissertation'] and p['department'] == 'School of Computer Science' and 'Advisor(s) Maple, Terry L.; Other, Person' in p['quote']
    assert not E.parse_dspace7(GT % 'Technical Report')['dissertation']
    assert E.parse_dspace7(GT_LOGIN) is None


def test_invenio_parser():
    p = E.parse_invenio(UC)
    assert p['advisors'] == ['Reppy, John'] and p['year'] == 2024 and p['department'] == 'Computer Science' and p['author'] == 'Zhong, Byron'
    assert 'Chugh' not in p['quote']


def test_natural_and_roles():
    assert E.natural('Maple, Terry L.') == 'Terry L. Maple' and E.natural('Terry Maple') == 'Terry Maple'
    assert E.role_of('Dissertation') == 'phd' and E.role_of('Thesis') == 'other'


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(E, 'db_path', lambda school: tmp_path / f'{school}.sqlite')
    return tmp_path


def put(c, url, html, dissertation, status='done'):
    p = E.parse_dspace7(html)
    c.execute('INSERT INTO queue (url, seq, status) VALUES (?,?,?)', (url, 0, status))
    c.execute('INSERT INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?)', (url, 'abc', 'now', int(dissertation), p['title'], p['author'], p['degree'], p['year'],
                                                                 p['department'], json.dumps(p['advisors']), p['quote']))


def test_evidence_matches_advisor_to_pi_by_full_name(store):
    c = E.connect('s')
    put(c, 'https://h/entities/publication/1', GT % 'Dissertation', True)
    put(c, 'https://h/entities/publication/2', GT % 'Technical Report', False)
    c.commit()
    rows, counts = E.build_evidence('s', PIS)
    assert [r['pi'] for r in rows] == ['Terry Maple']
    s = rows[0]['students'][0]
    assert s['name'] == 'Tina R. Chang' and s['role'] == 'phd' and s['years'] == [2019, 2019] and s['sha256'] == 'abc'
    assert 'Advisor(s) Maple' in s['quote'] and counts['rows'] == 1 and counts['dissertations'] == 1
    rows, counts = E.build_evidence('s', PIS, window=(2020, 2026))
    assert rows == [] and counts['outside_window'] == 1


class Resp:
    def __init__(self, content, status=200):
        self.content, self.status_code, self.headers = content, status, {}


class Sess:
    headers = {}

    def __init__(self, pages):
        self.pages, self.asked = pages, []

    def get(self, url, params=None, timeout=None):
        self.asked.append(url)
        if url.endswith('robots.txt'):
            return types.SimpleNamespace(status_code=200, text='User-agent: *\nDisallow: /browse\nCrawl-delay: 15\n')
        return self.pages.pop(0)


def test_crawl_is_resumable_polite_and_skips_robots_disallowed(store, monkeypatch):
    conf = dict(host='h', delay=10, enumerate='sitemap', parser='dspace7')
    monkeypatch.setattr(E, 'cfg', lambda school: conf)
    c = E.connect('s')
    for i, u in enumerate(['https://h/entities/publication/1', 'https://h/browse/x', 'https://h/entities/publication/2', 'https://h/entities/publication/3']):
        c.execute('INSERT INTO queue (url, seq) VALUES (?,?)', (u, i))
    c.commit()
    sess = Sess([Resp(GT.replace('%s', 'Dissertation').encode()), Resp(b'', 404), Resp(GT_LOGIN.encode())])
    sleeps = []
    cl = O.Client(10, session=sess, sleep=sleeps.append, clock=lambda: 0.0)
    out = []
    E.crawl('s', out=out.append, client=cl)
    st = dict(c.execute('SELECT url, status FROM queue').fetchall())
    assert st['https://h/browse/x'] == 'robots' and st['https://h/entities/publication/2'] == 'gone' and st['https://h/entities/publication/3'] == 'login'
    assert cl.delay == 15 and not any('browse' in u for u in sess.asked)   # the declared Crawl-delay wins
    assert E.stats('s')['dissertations'] == 1


def test_login_views_in_a_row_stop_the_crawl(store, monkeypatch):
    monkeypatch.setattr(E, 'cfg', lambda school: dict(host='h', delay=10, parser='dspace7'))
    monkeypatch.setattr(E, 'LOGIN_STOP', 3)
    c = E.connect('s')
    for i in range(6):
        c.execute('INSERT INTO queue (url, seq) VALUES (?,?)', (f'https://h/entities/publication/{i}', i))
    c.commit()
    sess = Sess([Resp(GT_LOGIN.encode()) for _ in range(6)])
    out = []
    assert E.crawl('s', out=out.append, client=O.Client(10, session=sess, sleep=lambda s: None, clock=lambda: 0.0)) is None
    assert 'login views' in out[-1] and dict(c.execute('SELECT status, COUNT(*) FROM queue GROUP BY status').fetchall())['pending'] == 4


def test_oai_enumeration_keeps_doctoral_theses(store, monkeypatch, tmp_path):
    monkeypatch.setattr(O, 'db_path', lambda school: tmp_path / f'oai-{school}.sqlite')
    oc = O.connect('s')
    oc.execute("INSERT INTO records VALUES ('a','d',0,'[]','T','[]',2020,'[]',?,'[]','[]','info:eu-repo/semantics/doctoralThesis','[]')",
               (json.dumps(['https://k/records/aaa']),))
    oc.execute("INSERT INTO records VALUES ('b','d',0,'[]','T','[]',2020,'[]',?,'[]','[]','info:eu-repo/semantics/article','[]')",
               (json.dumps(['https://k/records/bbb']),))
    oc.commit()
    assert E.enumerate_queue('s', dict(enumerate='oai', oai_type_rx='doctoralThesis'), out=lambda *_: None) == 1
    assert [r[0] for r in E.connect('s').execute('SELECT url FROM queue')] == ['https://k/records/aaa']


def test_charters():
    from pathlib import Path
    import school_config as SC
    SC.DIR, SC._cache = Path(__file__).resolve().parents[1] / 'schools', {}
    for k, parser in (('gatech', 'dspace7'), ('uchicago', 'invenio')):
        c = SC.field(SC.get(k), 'etd_crawl')
        assert c['parser'] == parser and c['delay'] >= 10 and c['host'] in c.get('sitemap', c['host'] + '/')
    assert 'michigan' not in [k for k in SC.keys() if SC.field(SC.get(k), 'etd_crawl')]
