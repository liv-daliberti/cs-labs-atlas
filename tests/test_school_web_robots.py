"""school_web.robots_decision: allowed-for-us, allowed-for-AI-agents-by-name, and the crawl delay that binds this project."""
import school_web as W
import pytest

ROBOTS_NAMED_DELAY = """User-agent: PerplexityBot
User-agent: ClaudeBot
User-agent: CCBot
Crawl-delay: 10

User-agent: *
Disallow: /core/
"""


def test_a_crawl_delay_in_a_group_naming_claudebot_binds_us():
    ours, ai, delay = W.robots_decision(200, ROBOTS_NAMED_DELAY, '/people/')
    assert ours and ai and delay == 10.0


def test_star_group_delay_and_floor():
    assert W.robots_decision(200, 'User-agent: *\nCrawl-delay: 20\n', '/')[2] == 20.0
    assert W.robots_decision(200, 'User-agent: *\nDisallow:\n', '/')[2] == 2.0
    assert W.robots_decision(404, '', '/')[2] == 2.0


def test_ai_agent_disallow_is_detected_by_name():
    ours, ai, _ = W.robots_decision(200, 'User-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nDisallow:\n', '/x')
    assert ours and not ai


def test_html_instead_of_robots_is_unresolved_permission():
    assert W.robots_decision(200, '<html><title>Access denied</title></html>', '/faculty')[:2] == (False, False)


@pytest.mark.parametrize('status', [204, 301, 302, 307, 308, 401, 403, 429, 500, -1])
def test_refused_or_unavailable_robots_never_authorizes_fetch(status):
    assert W.robots_decision(status, '', '/faculty')[:2] == (False, False)


def test_cached_plain_refusal_blocks_other_urls_on_same_host(tmp_path, monkeypatch):
    monkeypatch.setattr(W.wb, 'db_path', W.wb.db_path)
    monkeypatch.setattr(W, '_blocked', set())
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    c = W.con('fixture')
    c.execute('insert into live (url,status) values (?,?)', ('https://example.edu/old', 403))
    c.commit()
    c.close()
    c = W.con('fixture')
    monkeypatch.setattr(W, 'robots_ok', lambda *args: pytest.fail('cached refusal must stop before any request'))
    assert W.live(c, 'https://example.edu/new') is None
    c.close()


def test_plain_refusal_persists_host_stop(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import requests
    monkeypatch.setattr(W.wb, 'db_path', W.wb.db_path)
    monkeypatch.setattr(W, '_blocked', set())
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    monkeypatch.setattr(W, 'robots_ok', lambda *args: (True, 0))
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(content=b'Forbidden', status_code=403, headers={'Content-Type': 'text/plain'}, history=[])
    monkeypatch.setattr(requests, 'get', get)
    c = W.con('fixture')
    assert W.live(c, 'https://refused.edu/one')[0] == 403
    assert W.live(c, 'https://refused.edu/two') is None
    assert len(calls) == 1
    assert c.execute('select host from blocked').fetchone()[0] == 'refused.edu'
    c.close()


@pytest.mark.parametrize('target', ['https://other.edu/private', '/private'])
def test_live_redirect_is_recorded_without_contacting_target(tmp_path, monkeypatch, target):
    import json
    import zlib
    from types import SimpleNamespace
    import requests
    monkeypatch.setattr(W.wb, 'db_path', W.wb.db_path)
    monkeypatch.setattr(W, '_blocked', set())
    monkeypatch.setattr(W, '_last', {})
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    monkeypatch.setattr(W, 'robots_ok', lambda *args: (True, 0))
    calls = []
    def get(url, **kwargs):
        assert kwargs['allow_redirects'] is False
        calls.append(url)
        return SimpleNamespace(content=b'', status_code=302, headers={'Location': target})
    monkeypatch.setattr(requests, 'get', get)
    c = W.con('fixture')
    assert W.live(c, 'https://start.edu/person')[0] == 302
    assert calls == ['https://start.edu/person']
    raw = c.execute('select raw_zlib from live').fetchone()[0]
    assert json.loads(zlib.decompress(raw))['location'] == target
    c.close()


def test_robots_redirect_does_not_contact_target_or_authorize_page(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import requests
    monkeypatch.setattr(W.wb, 'db_path', W.wb.db_path)
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    calls = []
    def get(url, **kwargs):
        assert kwargs['allow_redirects'] is False
        calls.append(url)
        return SimpleNamespace(status_code=302)
    monkeypatch.setattr(requests, 'get', get)
    c = W.con('fixture')
    assert W.robots_ok(c, 'https://start.edu/person')[0] is False
    assert calls == ['https://start.edu/robots.txt']
    c.close()


def test_same_origin_robots_file_redirect_preserves_named_agent_restrictions(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import requests
    monkeypatch.setattr(W.wb, 'db_path', W.wb.db_path)
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    calls = []
    def get(url, **kwargs):
        assert kwargs['allow_redirects'] is False
        calls.append(url)
        if url.endswith('/content/dam/robots.txt'):
            return SimpleNamespace(status_code=200, headers={}, text='User-agent: ClaudeBot\nDisallow: /\n')
        return SimpleNamespace(status_code=301, headers={'Location': '/content/dam/robots.txt'})
    monkeypatch.setattr(requests, 'get', get)
    c = W.con('fixture')
    assert W.robots_ok(c, 'https://start.edu/person')[0] is False
    assert calls == ['https://start.edu/robots.txt', 'https://start.edu/content/dam/robots.txt']
    assert c.execute('select target_url from robots_redirects').fetchone()[0] == calls[-1]
    c.close()


@pytest.mark.parametrize('target', ['https://other.edu/robots.txt', '/private/faculty', 'http://start.edu/robots.txt'])
def test_robots_redirect_never_fetches_other_origin_or_ordinary_content(tmp_path, monkeypatch, target):
    from types import SimpleNamespace
    import requests
    monkeypatch.setattr(W.wb, 'db_path', W.wb.db_path)
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=302, headers={'Location': target})
    monkeypatch.setattr(requests, 'get', get)
    c = W.con('fixture')
    assert W.robots_ok(c, 'https://start.edu/person')[0] is False
    assert calls == ['https://start.edu/robots.txt']
    c.close()


def test_robots_redirect_loop_stops_without_repeating_request(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import requests
    monkeypatch.setattr(W.wb, 'db_path', W.wb.db_path)
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=301, headers={'Location': '/robots.txt'})
    monkeypatch.setattr(requests, 'get', get)
    c = W.con('fixture')
    assert W.robots_ok(c, 'https://start.edu/person')[0] is False
    assert calls == ['https://start.edu/robots.txt']
    c.close()


def test_urls_on_host_lists_department_and_unit_slots():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('sh_by_path', Path(__file__).resolve().parents[1] / 'tools' / 'school_hosts.py')
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    cfg = {'departments': [{'listings': [{'url': 'https://old.edu/people/'}, {'url': 'https://new.edu/p'}]}],
           'affiliated_units': [{'listings': ['old.edu/people/faculty/', 'x.edu/y']}]}
    assert H.urls_on_host(cfg, 'old.edu') == ['https://old.edu/people/', 'old.edu/people/faculty/']


def _robots_get(chain):
    from types import SimpleNamespace
    def get(url, **kwargs):
        status, loc, text = chain[url]
        return SimpleNamespace(status_code=status, headers={'Location': loc} if loc else {}, text=text)
    return get


def test_robots_redirect_within_registered_domain_is_followed(tmp_path, monkeypatch):
    import requests
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    chain = {'https://cs.example.edu/robots.txt': (301, 'https://www.cs.example.edu/robots.txt', ''),
             'https://www.cs.example.edu/robots.txt': (200, None, 'User-agent: *\nDisallow: /private/\n')}
    monkeypatch.setattr(requests, 'get', _robots_get(chain))
    c = W.con('fixture')
    st, body = W.robots_row(c, 'cs.example.edu')
    assert st == 200 and 'private' in body
    assert c.execute('select final_url, status from robots_final').fetchone() == ('https://www.cs.example.edu/robots.txt', 200)
    assert c.execute('select count(*) from robots_redirects').fetchone()[0] == 1


def test_robots_redirect_to_another_domain_stays_unreadable(tmp_path, monkeypatch):
    import requests
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    chain = {'https://a.example.edu/robots.txt': (302, 'https://evil.example.com/robots.txt', '')}
    monkeypatch.setattr(requests, 'get', _robots_get(chain))
    st, body = W.robots_row(W.con('fixture'), 'a.example.edu')
    assert st == 302 and W.robots_decision(st, body, '/x')[:2] == (False, False)


def test_registered_domain():
    assert W.registered_domain('www.cs.stanford.edu') == 'stanford.edu'
    assert W.registered_domain('www.cs.ox.ac.uk') == 'ox.ac.uk'


def test_transient_robots_timeout_is_retried_and_recorded_unknown_not_disallowed(tmp_path, monkeypatch):
    import requests
    from types import SimpleNamespace
    monkeypatch.setattr(W, 'ROBOTS_RETRY_WAITS', (0, 0, 0))
    monkeypatch.setattr(W.wb, 'db_path', W.wb.db_path)
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'c.sqlite')
    calls = []

    def get(url, **kw):
        calls.append(url)
        if len(calls) < 3:
            raise requests.exceptions.Timeout('slow')
        return SimpleNamespace(status_code=200, text='User-agent: *\nDisallow:\n', headers={})
    monkeypatch.setattr(requests, 'get', get)
    c = W.con('fixture')
    st, body = W.robots_row(c, 'x.example.edu')
    assert st == 200 and len(calls) == 3 and W.robots_decision(st, body, '/p')[:2] == (True, True)
    # all attempts fail: status -1 (unknown), not cached, asked again next time
    calls.clear()
    monkeypatch.setattr(requests, 'get', lambda url, **kw: (_ for _ in ()).throw(requests.exceptions.Timeout('x')))
    st, _ = W.robots_row(c, 'y.example.edu')
    assert st == -1
    monkeypatch.setattr(requests, 'get', lambda url, **kw: SimpleNamespace(status_code=404, text='', headers={}))
    assert W.robots_row(c, 'y.example.edu')[0] == 404
    c.close()


def test_audit_ai_allowed_uses_own_scheme_and_ignores_error_and_redirect_rows(tmp_path):
    import sqlite3
    import zlib
    from types import SimpleNamespace
    import labpage_audit as A
    db = tmp_path / 's.sqlite'
    c = sqlite3.connect(db)
    c.execute('create table captures (id integer primary key, url text, capture_url text, status int, content blob, error text)')
    rows = [('https://h.edu/robots.txt', 200, zlib.compress(b'User-agent: *\nDisallow: /private/\n'), None),
            ('http://h.edu/robots.txt', 301, zlib.compress(b'moved'), None),
            ('https://h.edu/robots.txt', None, None, 'Timeout()')]
    for u, st, b, e in rows:
        c.execute('insert into captures (url,capture_url,status,content,error) values (?,?,?,?,?)', (u, None, st, b, e))
    c.commit()
    c.close()
    kit = SimpleNamespace(store=str(db), school='x', lpcap=SimpleNamespace(DBS={'x': str(db)}))
    assert A.Kit._ai_allowed(kit, 'https://h.edu/faculty') is True
    assert A.Kit._ai_allowed(kit, 'http://h.edu/faculty') is True
    assert A.Kit._ai_allowed(kit, 'https://h.edu/private/x') is False


SPA = '<!doctype html><html><head><title>Lab</title></head><body><div id="app"></div><script src="/app.js"></script></body></html>'


def test_long_spa_shell_mentioning_a_cdn_or_a_research_challenge_is_no_rules():
    body = SPA.replace('</body>', '<link href="https://cdnjs.cloudflare.com/x.css"><p>' + 'security challenges and Cloudflare, Akamai ' * 400 + '</p></body>')
    assert W.robots_decision(200, body, '/people/')[:2] == (True, True)


def test_html_spa_catch_all_robots_is_no_rules():
    # owner ruling 2026-11-12: a 200 HTML page with no robots lines is 'no rules'
    ours, ai, _ = W.robots_decision(200, SPA, '/people/')
    assert ours and ai


@pytest.mark.parametrize('body', ['<html><title>Request Error</title><body>The requested URL was rejected</body></html>',
                                  '<html><body>Please complete the CAPTCHA</body></html>',
                                  '<html><title>Just a moment...</title><body>cf_chl_opt cloudflare</body></html>',
                                  '<html><title>Sign in</title><form><input type="password"></form></html>',
                                  '<html><title>Anubis</title>checking</html>',
                                  '<html><body>User-agent: *\nDisallow: /</body></html>'])
def test_html_challenge_error_login_or_rules_robots_is_refused(body):
    assert W.robots_decision(200, body, '/faculty')[0] is False


def test_audit_ai_allowed_html_spa_allowed_challenge_5xx_403_refused(tmp_path):
    import sqlite3
    import zlib
    from types import SimpleNamespace
    import labpage_audit as A

    def allowed(status, body):
        db = tmp_path / f's{abs(hash((status, body)))}.sqlite'
        c = sqlite3.connect(db)
        c.execute('create table captures (id integer primary key, url text, capture_url text, status int, content blob, error text)')
        c.execute('insert into captures (url,capture_url,status,content,error) values (?,?,?,?,?)',
                  ('https://spa.edu/robots.txt', None, status, zlib.compress(body.encode()), None))
        c.commit(); c.close()
        kit = SimpleNamespace(store=str(db), school='x', lpcap=SimpleNamespace(DBS={'x': str(db)}))
        return A.Kit._ai_allowed(kit, 'https://spa.edu/people/')
    assert allowed(200, SPA) is True
    assert allowed(200, '<html><title>Request Error</title></html>') is False
    assert allowed(200, '<html>Cloudflare challenge</html>') is False
    assert allowed(403, '') is False
    assert allowed(503, SPA) is False
    assert allowed(302, '') is False


@pytest.mark.parametrize('toolkit', ['labpage-tools-princeton-mit', 'labpage-tools-epfl-berkeley'])
def test_lpcap_html_robots_helper_and_redirect_to_other_host(toolkit):
    import importlib.util
    import os
    import sys
    d = os.path.join(os.path.dirname(__file__), '..', 'hierarchy', toolkit)
    sys.path.insert(0, d)
    try:
        spec = importlib.util.spec_from_file_location('lpcap_' + toolkit.replace('-', '_'), os.path.join(d, 'lpcap.py'))
        L = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(L)
    finally:
        sys.path.remove(d)
    assert L.html_robots_is_no_rules(SPA)
    assert not L.html_robots_is_no_rules('<html>Access Denied</html>')
    assert L.robots_final_elsewhere('https://login.example.org/x', 'lab.edu')
    assert not L.robots_final_elsewhere('https://www.lab.edu/robots.txt', 'lab.edu')
