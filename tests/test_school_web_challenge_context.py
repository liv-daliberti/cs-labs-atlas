"""A citation about CAPTCHA is not an access gate; actual refusals remain blocks."""
from types import SimpleNamespace

import pytest
import requests

import school_web as W


@pytest.mark.parametrize('body', [
    '<title>Faculty publications</title><li>PhishDecloaker: Detecting CAPTCHA-cloaked Phishing Websites via Hybrid Vision-based Interactive Models (USENIX Security 2024).</li>',
    '<p>We study CAPTCHA security and privacy.</p>',
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
    'access denied',
    '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>',
])
def test_real_gates_still_match(body):
    assert W.CHALLENGE.search(body)


@pytest.mark.parametrize('status,body,classified,blocked', [
    (200, '<title>Faculty publications</title><p>Research on CAPTCHA-cloaked phishing.</p>', 200, False),
    (403, '<title>Faculty publications</title><p>Research on CAPTCHA-cloaked phishing.</p>', 403, True),
    (200, '<title>CAPTCHA verification</title>', 999, True),
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
