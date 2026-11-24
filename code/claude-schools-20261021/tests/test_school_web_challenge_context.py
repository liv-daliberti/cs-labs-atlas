"""A citation about CAPTCHA is not an access gate; actual refusals remain blocks."""
from types import SimpleNamespace

import pytest
import requests

import school_web as W


@pytest.mark.parametrize('body', [
    '<title>Faculty publications</title><li>PhishDecloaker: Detecting CAPTCHA-cloaked Phishing Websites via Hybrid Vision-based Interactive Models (USENIX Security 2024).</li>',
    '<p>We study CAPTCHA security and privacy.</p>',
    '<title>Access denied | School of Interactive Computing</title><link rel="stylesheet" href="/sites/default/files/css/a.css"><h1 class="page-title">Access denied</h1>',
    '<h1>Faculty homepage</h1><script src="/_Incapsula_Resource?SWJIYLWA=abc" async></script>',
    '<html><head><script src="/_Incapsula_Resource?SWJIYLWA=abc"></script></head><body><h1>Faculty homepage</h1><p>PhD students</p></body></html>',
    '<title>Group - Yang Gao</title><script>_W.recaptchaUrl = "https://www.google.com/recaptcha/api.js";</script><h2>Ph.D. Students</h2><p>Chuan Wen (2020-)</p>',
])
def test_research_mentions_are_not_challenges(body):
    assert not W.CHALLENGE.search(body)


@pytest.mark.parametrize('body', [
    '<title>CAPTCHA verification</title>',
    '<div class="g-recaptcha"></div>',
    '<div class="h-captcha"></div>',
    'Please complete the CAPTCHA to continue',
    '<title>Just a moment...</title>',
    'checking your browser',
    '<iframe src="/_Incapsula_Resource?incident_id=123"></iframe>',
    'Request unsuccessful. Incapsula incident ID: 123',
    '<HTML><HEAD>\n<TITLE>Access Denied</TITLE>\n</HEAD><BODY>\n<H1>Access Denied</H1>\nYou don\'t have permission. Reference&#32;&#35;18.2f0e3a17.1700000000.1a2b3c</BODY></HTML>',
    '<title>Access Denied</title></head><body>',
    'Sucuri WebSite Firewall - Access Denied',
    'Access denied | www.example.org used Cloudflare to restrict access',
    'https://errors.edgesuite.net/18.abc',
    '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>',
    '<script src="https://www.google.com/recaptcha/api.js"></script>',
    "<script async src='https://www.google.com/recaptcha/enterprise.js'></script>",
    '<script src=https://www.google.com/recaptcha/api.js></script>',
    '<script>_W.recaptchaUrl = "https://www.google.com/recaptcha/api.js";</script><div class="g-recaptcha"></div>',
    '<html>\r\n<head>\r\n<META NAME="robots" CONTENT="noindex,nofollow">\r\n<script src="/_Incapsula_Resource?SWJIYLWA=abc">\r\n</script>\r\n<body>\r\n</body></html>',
    '<html><head><script src="/_Incapsula_Resource?SWJIYLWA=abc"></script></head><body></body></html>',
])
def test_real_gates_still_match(body):
    assert W.CHALLENGE.search(body)


@pytest.mark.parametrize('status,body,classified,blocked', [
    (200, '<title>Faculty publications</title><p>Research on CAPTCHA-cloaked phishing.</p>', 200, False),
    (200, '<title>Group - Yang Gao</title><script>_W.recaptchaUrl = "https://www.google.com/recaptcha/api.js";</script><h2>Ph.D. Students</h2>', 200, False),
    (200, '<script src="https://www.google.com/recaptcha/api.js"></script>', 999, True),
    (403, '<title>Faculty publications</title><p>Research on CAPTCHA-cloaked phishing.</p>', 403, True),
    (200, '<title>CAPTCHA verification</title>', 999, True),
    (200, '<html><head><script src="/_Incapsula_Resource?SWJIYLWA=abc"></script></head><body></body></html>', 999, True),
])
def test_transport_status_is_preserved(tmp_path, monkeypatch, status, body, classified, blocked):
    monkeypatch.setattr(W, 'db_path', lambda key: tmp_path / 'captures.sqlite')
    monkeypatch.setattr(W, '_blocked', set())
    monkeypatch.setattr(W, '_last', {})
    monkeypatch.setattr(W, 'robots_ok', lambda c, url: (True, 0))
    monkeypatch.setattr(requests, 'get', lambda *a, **kw: SimpleNamespace(
        status_code=status, content=body.encode(), headers={'Content-Type': 'text/html'}))
    c = W.con('test')
    try:
        W.live(c, 'https://example.org/pi')
        assert c.execute('select status from live').fetchone()[0] == classified
        assert c.execute('select http_status, classified_status from live_transport').fetchone() == (status, classified)
        assert ('example.org' in W._blocked) == blocked
    finally:
        c.close()
