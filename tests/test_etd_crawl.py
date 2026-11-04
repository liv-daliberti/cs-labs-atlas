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


def test_sitemap_truncated_response_is_asked_again_never_parsed(monkeypatch):
    idx = b'<?xml version="1.0"?><sitemapindex><sitemap><loc>https://h/s0.xml</loc></sitemap></sitemapindex>'
    cut = b'<urlset><url><loc>https://h/entities/publication/1</loc></url><url><loc>https://h/entities/pub'
    full = (b'<urlset><url><loc>https://h/entities/publication/1</loc></url><url><loc>https://h/entities/person/2</loc></url></urlset>')
    sess = Sess([Resp(idx), Resp(cut), Resp(full)])
    cl = O.Client(10, session=sess, sleep=lambda s: None, clock=lambda: 0.0)
    assert E.sitemap_urls(cl, 'https://h/sitemap_index.xml', '/entities/publication/') == ['https://h/entities/publication/1']
    # the same cut twice = the server ends the file there: the complete entries before it are used
    cut2 = b'<urlset><url><loc>https://h/entities/publication/1</loc></url><url><loc>https://h/entities/pub'
    got = E.sitemap_urls(O.Client(10, session=Sess([Resp(cut2)] * 4), sleep=lambda s: None, clock=lambda: 0.0), 'https://h/s.xml', '/entities/publication/')
    assert got == ['https://h/entities/publication/1']


def test_transient_5xx_waits_and_resumes_instead_of_stopping(store, monkeypatch):
    monkeypatch.setattr(E, 'cfg', lambda school: dict(host='h', delay=10, parser='dspace7'))
    c = E.connect('s')
    c.execute('INSERT INTO queue (url, seq) VALUES (?,?)', ('https://h/entities/publication/1', 0))
    c.commit()
    sleeps = []
    sess = Sess([Resp(b'', 502)] * 6 + [Resp(GT.replace('%s', 'Dissertation').encode())])
    cl = O.Client(10, session=sess, sleep=sleeps.append, clock=lambda: 0.0)
    out = []
    E.crawl('s', out=out.append, client=cl)
    assert E.stats('s')['dissertations'] == 1 and any('transient' in o for o in out) and 1800 in sleeps and 60 in sleeps


def test_add_urls_queues_without_duplicates_and_front(store, monkeypatch):
    monkeypatch.setattr(E, 'cfg', lambda school: dict(host='h'))
    assert E.add_urls('s', ['https://h/a', 'https://h/b', 'https://other/c']) == 2
    assert E.add_urls('s', ['https://h/a', 'https://h/p'], front=True) == 1
    order = [r[0] for r in E.connect('s').execute('SELECT url FROM queue ORDER BY seq')]
    assert order == ['https://h/p', 'https://h/a', 'https://h/b']


FULL = """<html><body><table class="detailtable"><tr><td>dc.contributor.advisor</td><td>Cathcart, J. M.</td><td></td></tr>
<tr><td>dc.contributor.author</td><td>Prussing, Keith F.</td><td></td></tr><tr><td>dc.date.issued</td><td>2015-05-19</td><td></td></tr>
<tr><td>dc.title</td><td>An investigation of surface shape effects</td><td></td></tr><tr><td>dc.type</td><td>Dissertation</td><td></td></tr>
<tr><td>dc.description.degree</td><td>Ph.D.</td><td></td></tr><tr><td>dc.contributor.department</td><td>Physics</td><td></td></tr>
<tr><td>dc.contributor.committeeMember</td><td>Zangwill, Andrew</td><td></td></tr></table></body></html>"""
PLAIN = """<html><head><meta name="DC.contributor" content="Cathcart, J. M."><meta name="DC.creator" content="Prussing, Keith F.">
<meta name="DC.date" content="December 2015"><meta name="DC.title" content="An investigation of surface shape effects"><meta name="DC.type" content="Dissertation">
<meta name="DC.description" content="Ph.D."><meta name="DC.contributor" content="Physics"><meta name="DC.contributor" content="Zangwill, Andrew"></head><body></body></html>"""
OLD = """<html><head><meta name="DC.creator" content="Chang, Tina R."><meta name="DC.title" content="Social behavior"><meta name="DC.type" content="Thesis">
<meta name="DC.description" content="M.S."><meta name="DC.contributor" content="Psychology"><meta name="DC.description" content="Terry Maple"></head></html>"""


def test_smartech_parser_full_and_plain_captures():
    f = E.parse_smartech(FULL, dict(handle='1853/54321'))
    assert f['advisors'] == ['Cathcart, J. M.'] and f['dissertation'] and f['year'] == 2015 and f['department'] == 'Physics' and f['handle'] == '1853/54321'
    p = E.parse_smartech(PLAIN)
    assert p['advisors'] == ['Cathcart, J. M.'] and p['dissertation'] and p['department'] == 'Physics' and p['year'] == 2015
    assert 'before DC.creator' in p['quote']
    o = E.parse_smartech(OLD)   # advisor only in a second DC.description: not read as an advisor
    assert o['advisors'] == [] and not o['dissertation']
    assert E.parse_smartech('<html><title>Login</title></html>') is None


def test_cdx_rows_prefer_full_and_newest():
    import types as T
    data = [['original', 'timestamp'], ['https://smartech.gatech.edu/handle/1853/9', '20190101000000'], ['https://smartech.gatech.edu/handle/1853/9', '20200101000000'],
            ['https://smartech.gatech.edu/handle/1853/9?show=full', '20180101000000'], ['https://smartech.gatech.edu/handle/1853/3', '20210101000000']]
    client = T.SimpleNamespace(get=lambda url, params=None, tolerate=(): T.SimpleNamespace(json=lambda: data))
    rows = E.cdx_rows(client, dict(cdx_url='x', cdx_original_rx='.*'))
    assert rows == [('9', 'full', '20180101000000', 'https://smartech.gatech.edu/handle/1853/9?show=full'),
                    ('3', 'plain', '20210101000000', 'https://smartech.gatech.edu/handle/1853/3')]
    more = data + [['https://smartech.gatech.edu/handle/1853/50?show=full', '20190101000000'], ['https://smartech.gatech.edu/handle/1853/70', '20190101000000']]
    client2 = T.SimpleNamespace(get=lambda url, params=None, tolerate=(): T.SimpleNamespace(json=lambda: more))
    assert [r[0] for r in E.cdx_rows(client2, dict(cdx_url='x', cdx_original_rx='.*'))] == ['50', '9', '70', '3']   # full first, high handles first


def test_wayback_rows_dedupe_against_live_and_use_replay_urls(store, monkeypatch):
    c = E.connect('s')
    put(c, 'https://h/entities/publication/1', GT % 'Dissertation', True)   # Chang / 'Study of Things' / advisor Maple, live
    c.commit()
    w = E.connect('s@wayback')
    for url, title, author in (('https://web.archive.org/web/20200101000000id_/https://smartech.gatech.edu/handle/1853/1', 'Study of Things', 'Chang, Tina R.'),
                               ('https://web.archive.org/web/20200101000000id_/https://smartech.gatech.edu/handle/1853/2', 'Another One Entirely', 'Chang, Tina R.')):
        w.execute('INSERT INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?)', (url, 'sha', 'now', 1, title, author, 'Dissertation Ph.D.', 2018, 'CS', json.dumps(['Maple, Terry L.']), 'q'))
    w.commit()
    rows, counts = E.build_evidence('s', PIS)
    urls = [x['url'] for r in rows for x in r['students']]
    assert counts['duplicate_of_earlier_source'] == 1 and len(urls) == 2
    assert 'https://web.archive.org/web/20200101000000/https://smartech.gatech.edu/handle/1853/2' in urls


def test_offline_and_non_html_bodies_do_not_stop_the_crawl(store, monkeypatch):
    monkeypatch.setattr(E, 'cfg', lambda school: dict(host='h', delay=10, parser='dspace7'))
    c = E.connect('s')
    for i in range(3):
        c.execute('INSERT INTO queue (url, seq) VALUES (?,?)', (f'https://h/entities/publication/{i}', i))
    c.commit()
    off = b'<html><head><title>Internet Archive: Temporarily Offline</title></head></html>'
    sess = Sess([Resp(off), Resp(b'%PDF-1.4 binary'), Resp(GT.replace('%s', 'Dissertation').encode()), Resp(GT.replace('%s', 'Dissertation').encode())])
    sleeps = []
    cl = O.Client(10, session=sess, sleep=sleeps.append, clock=lambda: 0.0)
    E.crawl('s', out=lambda *_: None, client=cl)
    st = dict(c.execute('SELECT url, status FROM queue').fetchall())
    assert st['https://h/entities/publication/0'] == 'nonhtml' or 1800 in sleeps
    assert 1800 in sleeps and E.stats('s')['pages'] >= 1 and 'pending' not in st.values()


def test_real_smartech_full_capture_fixture(tmp_path):
    from pathlib import Path
    fx = Path(__file__).parent / 'fixtures' / 'smartech_54321_full.html'
    p = E.parse_smartech(fx.read_bytes(), dict(handle='1853/54321'))
    assert p['dissertation'] and p['advisors'] == ['Cathcart, J. M.'] and p['year'] == 2015 and p['department'] == 'Physics'
