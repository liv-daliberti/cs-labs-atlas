"""tools/link_check.py: the polite landing-page check, against a local server."""
import http.server
import sys
import threading
from functools import partial
from pathlib import Path

import pytest

CODE = Path(__file__).resolve().parents[1]
if str(CODE / 'tools') not in sys.path:
    sys.path.insert(0, str(CODE / 'tools'))
import link_check as L  # noqa: E402

PAGE = '<html><head><title>x</title><meta name="citation_title" content="Efficient Estimation of Word Representations in Vector Space"><meta name="citation_author" content="Mikolov, Tomas"><meta name="citation_author" content="Chen, Kai"></head></html>'
OTHER = '<html><head><meta name="citation_title" content="A Completely Different Paper About Graph Coloring Algorithms"><meta name="citation_author" content="Someone, Else"></head></html>'
NOAUTH = '<html><head><meta name="dc.title" content="Efficient Estimation of Word Representations in Vector Space"></head></html>'
WRONGAUTH = PAGE.replace('Mikolov, Tomas', 'Zhang, Wei')
CHALLENGE = '<html><head><title>Just a moment...</title></head><body>cf-chl-bypass</body></html>'
ROBOTS = 'User-agent: ClaudeBot\nDisallow: /private/\n\nUser-agent: *\nDisallow:\n'


@pytest.fixture
def server(tmp_path):
    root = tmp_path / 'www'
    (root / 'private').mkdir(parents=True)
    for name, body in {'match.html': PAGE, 'other.html': OTHER, 'noauth.html': NOAUTH, 'wrongauth.html': WRONGAUTH, 'challenge.html': CHALLENGE,
                       'private/p.html': PAGE, 'robots.txt': ROBOTS}.items():
        (root / name).write_text(body)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{srv.server_address[1]}'
    srv.shutdown()


def row(url):
    return dict(key='k', url=url, url_kind='landing', title='Efficient Estimation of Word Representations in Vector Space', doi='', first_author_family='mikolov', host='x', school='s')


def test_verdicts(server):
    c = L.Checker(gap=0.0)
    assert c.check(row(server + '/match.html'))['verdict'] == 'match'
    r = c.check(row(server + '/other.html'))
    assert r['verdict'] == 'mismatch' and 'Graph Coloring' in r['title_seen']
    assert c.check(row(server + '/noauth.html'))['verdict'] == 'match'  # no author listed: the title decides
    r = c.check(row(server + '/wrongauth.html'))
    assert r['verdict'] == 'unreachable' and r['reason'] == 'first_author_not_among_authors_seen'


def test_robots_rules_naming_claudebot_bind_us(server):
    r = L.Checker(gap=0.0).check(row(server + '/private/p.html'))
    assert r['verdict'] == 'unreachable' and r['reason'] == 'robots_disallow' and r['robots_ok'] is False


def test_a_challenge_page_is_not_read(server):
    r = L.Checker(gap=0.0).check(row(server + '/challenge.html'))
    assert r['verdict'] == 'unreachable' and r['reason'] == 'bot_challenge'


def test_the_never_used_hosts_are_not_asked():
    r = L.Checker(gap=0.0).check(row('https://deepblue.lib.umich.edu/handle/2027.42/1'))
    assert r['verdict'] == 'unreachable' and r['reason'] == 'never_used_host'
