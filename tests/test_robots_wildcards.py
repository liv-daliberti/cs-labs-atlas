"""RFC 9309 wildcards in robots.txt (2026-11-25): urllib.robotparser matched 'Disallow: /*.pdf' as a literal prefix, so Chicago Booth's
faculty-CV PDFs were fetched although the * group disallows them. school_web.wildcard_disallowed closes that."""
import school_web as W

BOOTH = """User-agent: booth-crawler
Disallow:
User-agent: *
Disallow: /admin/
Disallow: /*.pdf
Allow: /public/*.pdf
"""


def test_wildcard_pdf_rule_refuses_pdfs():
    assert W.robots_decision(200, BOOTH, 'https://www.chicagobooth.edu/-/media/faculty/cv.pdf')[0] is False


def test_wildcard_rule_leaves_other_pages():
    assert W.robots_decision(200, BOOTH, 'https://www.chicagobooth.edu/faculty/directory/w/amy-ward')[0] is True


def test_longer_allow_wins():
    assert not W.wildcard_disallowed(BOOTH, 'https://x.edu/public/report.pdf', [W.UA])


def test_end_anchor():
    body = 'User-agent: *\nDisallow: /*.php$\n'
    assert W.wildcard_disallowed(body, 'https://x.edu/a/index.php', [W.UA])
    assert not W.wildcard_disallowed(body, 'https://x.edu/a/index.php?x=1', [W.UA])


def test_named_group_replaces_star_group():
    body = 'User-agent: ClaudeBot\nDisallow: /*.pdf\n\nUser-agent: *\nDisallow:\n'
    assert W.wildcard_disallowed(body, 'https://x.edu/cv.pdf', ['ClaudeBot'])
    assert not W.wildcard_disallowed(body, 'https://x.edu/cv.pdf', [W.UA])
