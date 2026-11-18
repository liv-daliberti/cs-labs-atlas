"""Georgia Tech 2026-11-15: themed Drupal 403 pages (ic, scs, isye, ece, math.gatech.edu) closed whole hosts because the CHALLENGE regex
matched a bare 'access denied'. A themed CMS 403 is a per-path denial; WAF stubs and real challenges still close the host."""
import zlib
from types import SimpleNamespace

import requests

import school_web as W

PAD = '<div>' + 'x' * 9000 + '</div>'
DRUPAL = ('<html><head><title>Access denied | School of Computer Science</title>'
          '<link rel="stylesheet" href="/sites/default/files/css/a.css"></head><body><h1 class="page-title">Access denied</h1>' + PAD + '</body></html>')
APOLOGY = ('<html><head><title>Our Apologies (403 error: permissions issue) | School of Mathematics</title>'
           '<script type="application/json" data-drupal-selector="drupal-settings-json">{}</script></head><body>' + PAD + '</body></html>')
AKAMAI = '<HTML><HEAD>\n<TITLE>Access Denied</TITLE>\n</HEAD><BODY><H1>Access Denied</H1> Reference&#32;&#35;18.2f0e3a17.17.1a</BODY></HTML>'


def test_themed_cms_403_is_a_path_denial_not_a_challenge():
    for page in (DRUPAL, APOLOGY):
        assert not W.CHALLENGE.search(page)
        assert W.cms_path_denial(403, page.encode())
        assert W.path_denial(403, page.encode())
    assert not W.cms_path_denial(200, DRUPAL.encode())
    assert not W.cms_path_denial(429, DRUPAL.encode())


def test_waf_stubs_and_challenges_are_not_path_denials():
    assert W.CHALLENGE.search(AKAMAI)
    assert not W.path_denial(403, AKAMAI.encode())
    assert not W.path_denial(403, DRUPAL.replace('Access denied', 'Access denied', 1).encode()[:3000])  # too short to be a themed page
    assert not W.path_denial(403, (DRUPAL + '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>').encode())
    assert not W.path_denial(403, b'<title>403 Forbidden</title><p>Access denied by Cloudflare</p>')


def test_live_keeps_the_host_open_after_a_themed_403(tmp_path, monkeypatch):
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    monkeypatch.setattr(W, '_blocked', set())
    monkeypatch.setattr(W, '_last', {})
    monkeypatch.setattr(W, 'robots_ok', lambda c, url: (True, 0))
    monkeypatch.setattr(requests, 'get', lambda *a, **kw: SimpleNamespace(
        status_code=403, content=DRUPAL.encode(), headers={'Content-Type': 'text/html'}))
    c = W.con('test')
    try:
        assert W.live(c, 'https://scs.example.edu/people/x')[0] == 403
        assert 'scs.example.edu' not in W._blocked
        assert c.execute('select count(*) from blocked').fetchone()[0] == 0
    finally:
        c.close()


def test_stored_999_and_blocks_are_rejudged_on_load(tmp_path, monkeypatch):
    """The 2026-11-14 Georgia Tech rows: status 999 + live_transport 403 + a 'challenge at' block; reloading re-judges them as per-path."""
    db = tmp_path / 'captures.sqlite'
    monkeypatch.setattr(W, 'db_path', lambda key: db)
    monkeypatch.setattr(W, '_blocked', set())
    c = W.con('test')
    c.execute('create table if not exists live_transport (url text primary key, http_status int, classified_status int, sha256 text)')
    for u, page, h in (('https://scs.example.edu/p', DRUPAL, 'scs.example.edu'), ('https://waf.example.edu/p', AKAMAI, 'waf.example.edu')):
        c.execute('insert into live values (?,?,?,?,?,?,?)', (u, 't', 999, 'h', 'text/html', zlib.compress(page.encode()), None))
        c.execute('insert into live_transport values (?,?,?,?)', (u, 403, 999, 'h'))
        c.execute('insert into blocked values (?,?,?)', (h, 't', 'challenge at ' + u))
    c.commit(); c.close()
    W._blocked.clear()
    c = W.con('test')
    c.close()
    assert 'scs.example.edu' not in W._blocked
    assert 'waf.example.edu' in W._blocked
