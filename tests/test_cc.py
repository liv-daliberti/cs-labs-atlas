"""listings/scripts/cc.py: robots fail-closed, WARC parsing, storage in the Wayback captures schema; no network."""
import gzip
import hashlib
import json
import sqlite3
import zlib

import pytest

import cc

HTML = b'<html><body><h1>People</h1></body></html>'


def warc_record(body=HTML):
    http = b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + body
    w = b'WARC/1.0\r\nWARC-Type: response\r\nWARC-Target-URI: https://x.edu/p\r\n\r\n' + http
    return gzip.compress(w)


def fake(routes):
    calls = []

    def http(url, headers):
        calls.append((url, headers))
        for k, v in routes.items():
            if url.startswith(k):
                return v
        return 404, {}, b''
    http.calls = calls
    return http


@pytest.fixture(autouse=True)
def nosleep(monkeypatch):
    monkeypatch.setattr(cc.time, 'sleep', lambda s: None)
    cc._last[0] = 0.0


def test_gate_refuses_while_robots_disallows():
    h = fake({cc.INDEX + '/robots.txt': (200, {}, b'User-agent: *\nDisallow: /\n'), cc.DATA + '/robots.txt': (200, {}, b'User-agent: *\nDisallow: /\n')})
    with pytest.raises(cc.CCRefused):
        cc.cdx_rows('CC-MAIN-2019-10', 'x.edu/p', http=h)
    assert all('robots.txt' in u for u, _ in h.calls)  # nothing but robots was requested


def test_gate_opens_when_robots_allow_and_fetch_parses():
    h = fake({cc.INDEX + '/robots.txt': (200, {}, b'User-agent: *\nAllow: /\n'), cc.DATA + '/robots.txt': (404, {}, b''),
              cc.DATA + '/crawl-data/a.warc.gz': (206, {}, warc_record())})
    row = dict(timestamp='20190301000000', original='https://x.edu/p', filename='crawl-data/a.warc.gz', offset=10, length=99)
    st, body, _ = cc.fetch_record(row, http=h)
    assert st == 200 and body == HTML
    assert h.calls[-1][1]['Range'] == 'bytes=10-108' and '@' not in cc.UA


def test_backoff_on_503_then_gives_up():
    h = fake({'https://z/': (503, {'Retry-After': '7'}, b'')})
    with pytest.raises(cc.CCRefused):
        cc.polite_get('https://z/', http=h)
    assert len(h.calls) == cc.MAX_TRIES


def test_chunked_body():
    http = b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n0\r\n\r\n'
    rec = gzip.compress(b'WARC/1.0\r\nWARC-Type: response\r\n\r\n' + http)
    assert cc.parse_warc(rec)[3] == b'hello'


def test_store_schema_and_hash():
    con = sqlite3.connect(':memory:')
    con.execute('create table captures(capture_url text primary key, page_url text, department text, wayback_timestamp text, final_url text, '
                'http_status integer, fetched_at text, sha256 text, nbytes integer, content_type text, raw_zlib blob, blocks_json text, text text, note text)')
    row = dict(timestamp='20190301000000', original='https://x.edu/p', filename='crawl-data/a.warc.gz', offset=10, length=99, crawl='CC-MAIN-2019-13')
    sha = cc.store(con, row, 200, HTML, {'content-type': 'text/html'}, 'x.edu/p')
    r = con.execute('select capture_url, sha256, raw_zlib, note from captures').fetchone()
    assert sha == hashlib.sha256(HTML).hexdigest() == r[1] and zlib.decompress(r[2]) == HTML
    assert r[0] == 'commoncrawl:crawl-data/a.warc.gz:10:99'
    assert json.loads(r[3])['source'] == 'commoncrawl' and json.loads(r[3])['warc_offset'] == 10


def test_crawls_and_halves():
    info = [{'id': 'CC-MAIN-2019-13'}, {'id': 'CC-MAIN-2015-11'}, {'id': 'CC-MAIN-2017-04'}, {'id': 'CC-NEWS-2019'}]
    assert cc.crawls_for_years(info) == ['CC-MAIN-2017-04', 'CC-MAIN-2019-13']
    assert cc.fallback_halves([dict(timestamp='20190301000000'), dict(timestamp='20190901000000')]) == ['2019H1', '2019H2']


def test_ai_named_host_not_used():
    robots = b'User-agent: ClaudeBot\nDisallow: /\n'
    assert not cc.host_allowed(200, robots.decode(), 'https://x.edu/people/')
    assert cc.host_allowed(200, 'User-agent: *\nAllow: /\n', 'https://x.edu/people/')


def test_pick_crawls_one_per_half_nearest_middle():
    info = [{'id': 'CC-MAIN-2019-13'}, {'id': 'CC-MAIN-2019-04'}, {'id': 'CC-MAIN-2019-39'}, {'id': 'CC-MAIN-2015-11'}]
    got = cc.pick_crawls(info)
    assert got[(2019, 'H1')] == ['CC-MAIN-2019-13', 'CC-MAIN-2019-04'] and got[(2019, 'H2')] == ['CC-MAIN-2019-39']
    assert not any(y == 2015 for y, _ in got)


def test_cdx_cached_asks_once_and_stops_after_errors():
    con = sqlite3.connect(':memory:')
    cc.init_tables(con)
    line = json.dumps(dict(url='https://x.edu/p', timestamp='20190301000000', filename='f.warc.gz', offset='1', length='2', digest='D'))
    ok = {cc.INDEX + '/robots.txt': (200, {}, b'User-agent: *\nAllow: /\n'), cc.DATA + '/robots.txt': (404, {}, b''),
          cc.INDEX + '/CC-MAIN-2019-13-index': (200, {}, line.encode())}
    h = fake(ok)
    errs = {}
    assert cc.cdx_cached(con, 'CC-MAIN-2019-13', 'x.edu/p', errs, http=h)[0]['offset'] == 1
    n = len(h.calls)
    assert cc.cdx_cached(con, 'CC-MAIN-2019-13', 'x.edu/p', errs, http=h)[0]['crawl'] == 'CC-MAIN-2019-13' and len(h.calls) == n
    bad = fake({k: v for k, v in ok.items() if 'index?' not in k and '-index' not in k} | {cc.INDEX + '/CC-MAIN-2020-10-index': (500, {}, b'')})
    for _ in range(cc.MAX_CRAWL_ERRORS):
        with pytest.raises(cc.CCRefused):
            cc.cdx_cached(con, 'CC-MAIN-2020-10', 'x.edu/p', errs, http=bad)
    m = len(bad.calls)
    with pytest.raises(cc.CCRefused):
        cc.cdx_cached(con, 'CC-MAIN-2020-10', 'x.edu/p', errs, http=bad)
    assert len(bad.calls) == m  # skipped without a request


def test_target_robots_recorded_and_ai_optout_refused():
    con = sqlite3.connect(':memory:')
    cc.init_tables(con)
    h = fake({'https://x.edu/robots.txt': (200, {}, b'User-agent: ClaudeBot\nDisallow: /\n')})
    assert cc.host_ok(con, 'https://x.edu/people/', http=h) is False
    assert con.execute('select ai_allowed, length(robots_sha256) from cc_robots').fetchone() == (0, 64)
    n = len(h.calls)
    assert cc.host_ok(con, 'https://x.edu/people/', http=h) is False and len(h.calls) == n  # cached for a day
