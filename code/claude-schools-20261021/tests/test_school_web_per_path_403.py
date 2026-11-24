"""cs.toronto.edu (2026-11-10): one Apache directory-permission 403 on /~sam/ closed the whole host; that is a per-path denial.
Any other 403 (a WAF or bot refusal) still closes the host (tests/test_school_web_robots.py)."""
import school_web as W

APACHE = (b'<!DOCTYPE HTML><html><head>\n<title>403 Forbidden</title>\n</head><body>\n<h1>Forbidden</h1>\n'
          b"<p>You don't have permission to access this resource.</p>\n<hr>\n<address>Apache/2.4.66 (Ubuntu) Server at www.cs.toronto.edu Port 443</address></body></html>")


def test_apache_permission_403_is_a_per_path_denial():
    assert W.apache_path_denial(403, APACHE)
    assert W.apache_path_denial(403, APACHE.replace(b'this resource', b'/vis/ on this server'))


def test_other_refusals_are_not_per_path():
    assert not W.apache_path_denial(403, b'Forbidden')
    assert not W.apache_path_denial(403, b'<title>403 Forbidden</title><p>Access denied by Cloudflare</p>')
    assert not W.apache_path_denial(429, APACHE)
    assert not W.apache_path_denial(200, APACHE)


def test_school_hosts_ignores_a_rejudged_per_path_block(tmp_path, monkeypatch):
    """school_hosts must read the block through school_web's re-judged set, not the raw `blocked` table."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1] / 'tools' / 'school_hosts.py').read_text()
    assert 'host in W._blocked' in src
