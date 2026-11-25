"""Kit.refresh_robots: ONE named host's /robots.txt is fetched with the toolkit's own robots code and stored as a newer robots row; the normal
decision (Kit._ai_allowed reads the newest row) then follows it. A refreshed 404 row allows, a refreshed Disallow row refuses (HKUST 2026-11-25)."""
import sqlite3
import zlib
from types import SimpleNamespace

import pytest

import labpage_audit as A


def _fixture(tmp_path, stale_status, answers):
    db = tmp_path / 's.sqlite'
    c = sqlite3.connect(db)
    c.execute('create table captures (id integer primary key autoincrement, url text, final_url text, capture_url text, fetched_at text, status int, sha256 text, '
              'content_type text, content blob, error text, copied_from text)')
    c.execute('insert into captures (url,capture_url,status,content,error,fetched_at) values (?,?,?,?,?,?)',
              ('https://h.github.io/robots.txt', None, stale_status, zlib.compress(b'<html>unavailable</html>'), None, '2026-11-10T00:00:00'))
    c.commit()
    c.close()

    def connect(school):
        return sqlite3.connect(db)

    def insert(con, url, final, capture_url, status, body, ctype, error):
        con.execute('insert into captures (url,final_url,capture_url,fetched_at,status,content,error) values (?,?,?,?,?,?,?)',
                    (url, final, capture_url, '2026-11-25T00:00:00', status, zlib.compress(body) if body is not None else None, error))
        con.commit()

    def get(url, **kw):
        status, body = answers
        return SimpleNamespace(status_code=status, content=body, url=url, headers={'content-type': 'text/plain'})

    lp = SimpleNamespace(DBS={'x': str(db)}, connect=connect, _insert=insert, _wait=lambda h: None, _sess=SimpleNamespace(get=get), TIMEOUT=(1, 1), _robots={}, _robots_unknown=set())
    return SimpleNamespace(store=str(db), school='x', lpcap=lp)


def test_refreshed_404_row_allows_where_the_stale_503_row_refused(tmp_path):
    kit = _fixture(tmp_path, 503, (404, b'not found'))
    assert A.Kit._ai_allowed(kit, 'https://h.github.io/') is False   # the stale row keeps refusing
    rec = A.Kit.refresh_robots(kit, 'h.github.io')
    assert rec['status'] == 404 and rec['host'] == 'h.github.io'
    assert A.Kit._ai_allowed(kit, 'https://h.github.io/') is True


def test_refreshed_disallow_row_refuses(tmp_path):
    kit = _fixture(tmp_path, 404, (200, b'User-agent: ClaudeBot\nDisallow: /\n'))
    assert A.Kit._ai_allowed(kit, 'https://h.github.io/') is True
    A.Kit.refresh_robots(kit, 'h.github.io')
    assert A.Kit._ai_allowed(kit, 'https://h.github.io/') is False


def test_refresh_needs_one_explicit_host(tmp_path):
    kit = _fixture(tmp_path, 503, (404, b''))
    for bad in ('', None, '*', 'a b', 'h.github.io/x', 'localhost'):
        with pytest.raises(ValueError):
            A.Kit.refresh_robots(kit, bad)
