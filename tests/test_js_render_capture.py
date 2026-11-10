"""tools/js_render_capture.py: rules 1-4 on a mocked driver and a static fixture; no browser, no network."""
import sqlite3

import pytest

import js_render_capture as J
import school_web as W

STATIC = '<html><body><ul id="app"></ul><script>/*renders later*/</script></body></html>'
RENDERED = '<html><body><ul id="app"><li>陈宏伟</li><li>陈明华</li></ul></body></html>'


class Driver:
    capabilities = {'browserName': 'firefox', 'browserVersion': '140.0', 'moz:geckodriverVersion': '0.37.1'}

    def __init__(self, dom=RENDERED, res=('https://x.example/api/people.json',)):
        self.dom, self.res, self.got, self.quit_called = dom, res, [], False

    def get(self, url): self.got.append(url)
    @property
    def page_source(self): return self.dom

    def execute_script(self, js, *a):
        if 'readyState' in js: return 'complete'
        if 'querySelector' in js: return True
        return list(self.res)

    def quit(self): self.quit_called = True


@pytest.fixture
def con(monkeypatch):
    c = sqlite3.connect(':memory:')
    c.execute('create table if not exists blocked (host text primary key, at text, why text)')
    monkeypatch.setattr(W, '_blocked', set())
    monkeypatch.setattr(W, 'robots_ok', lambda c_, u: (True, 0))
    return c


def run(con, urls, driver, **k):
    sleeps = []
    out = J.render('t', urls, driver_factory=lambda: driver, raw_fetch=lambda u: (200, STATIC.encode()), con=con, sleep=sleeps.append, **k)
    return out, sleeps


def test_rendered_dom_and_raw_html_are_both_stored_with_verified_hashes(con):
    d = Driver()
    out, _ = run(con, ['https://x.example/people'], d)
    assert out[0]['status'] == 'ok' and out[0]['raw_sha256'] != out[0]['dom_sha256']
    dom, raw, meta = J.stored(con, 'https://x.example/people')
    assert '陈宏伟' in dom and '陈宏伟' not in raw and 'renders later' in raw
    assert meta['resources'] == ['https://x.example/api/people.json'] and meta['browser'] == 'firefox 140.0' and meta['driver'] == 'geckodriver 0.37.1'
    assert d.quit_called


def test_robots_are_checked_before_navigation(con, monkeypatch):
    monkeypatch.setattr(W, 'robots_ok', lambda c_, u: (False, 0))
    d = Driver()
    out, _ = run(con, ['https://x.example/people'], d)
    assert out[0]['status'] == 'robots_disallowed' and d.got == []


def test_a_challenge_page_is_not_stored_and_blocks_the_host(con):
    d = Driver(dom='<html><title>Just a moment...</title><body>checking your browser</body></html>')
    out, _ = run(con, ['https://x.example/a', 'https://x.example/b'], d)
    assert [o['status'] for o in out] == ['challenge', 'host_blocked']
    assert J.stored(con, 'https://x.example/a') is None and d.got == ['https://x.example/a']


def test_login_wall_is_not_stored(con):
    d = Driver(dom='<html><form><input type="password"></form></html>')
    out, _ = run(con, ['https://x.example/a'], d)
    assert out[0]['status'] == 'login' and J.stored(con, 'https://x.example/a') is None


def test_polite_gap_and_page_cap(con):
    d = Driver()
    out, sleeps = run(con, ['https://x.example/a', 'https://x.example/b', 'https://x.example/c'], d, cap=2, gap=3.0)
    assert [o['status'] for o in out] == ['ok', 'ok', 'capped'] and len(d.got) == 2
    assert any(s >= 2.0 for s in sleeps)   # the 3 s gap between two navigations (less the elapsed time)


def test_wait_css_is_honoured(con):
    d = Driver()
    out, _ = run(con, ['https://x.example/a'], d, wait_css='#app li')
    assert out[0]['status'] == 'ok'


def test_http_origin_reads_robots_at_the_urls_own_origin(monkeypatch):
    """--http-origin: robots comes from http://host/robots.txt (404 = no file = allowed), stored apart from the HTTPS row; the default still reads HTTPS."""
    c = sqlite3.connect(':memory:')
    c.execute('create table robots (host text primary key, fetched_at text, status int, body text)')
    asked = []

    class R:
        status_code, text, headers = 404, '', {}

    def fake_get(url, **k):
        asked.append(url)
        if url.startswith('https://'):
            raise ConnectionError('https refuses connections')
        return R()
    monkeypatch.setattr('requests.get', fake_get)
    ok, _ = W.robots_ok(c, 'http://www.cst.zju.edu.cn/szdw/list.htm', same_origin=True)
    assert ok and asked == ['http://www.cst.zju.edu.cn/robots.txt']
    assert c.execute('select status from robots where host=?', ('http://www.cst.zju.edu.cn',)).fetchone() == (404,)
    ok_default, _ = W.robots_ok(c, 'http://www.cst.zju.edu.cn/szdw/list.htm')   # the default stays HTTPS: unreachable means no
    assert not ok_default and asked[-1] == 'https://www.cst.zju.edu.cn/robots.txt'


def test_render_passes_http_origin_to_the_robots_check(con, monkeypatch):
    seen = []
    monkeypatch.setattr(W, 'robots_ok', lambda c_, u, same_origin=False: (seen.append(same_origin) or (False, 0)))
    out = J.render('t', ['http://www.cad.zju.edu.cn/innovationteam'], con=con, http_origin=True, driver_factory=lambda: None)
    assert seen == [True] and out[0]['status'] == 'robots_disallowed'
