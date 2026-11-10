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


@pytest.fixture(autouse=True)
def marker(monkeypatch, tmp_path):
    (tmp_path / 'OWNER-APPROVED').write_text('test approval')
    monkeypatch.setattr(cc, 'approval_marker', lambda: str(tmp_path / 'OWNER-APPROVED'))
    monkeypatch.setattr(cc, 'cache_dir', lambda: str(tmp_path / 'cache'))
    cc.BYTES.update(n=0, requests=0)


def test_no_marker_means_no_request(monkeypatch, tmp_path):
    (tmp_path / 'OWNER-APPROVED').unlink()
    h = fake({})
    with pytest.raises(cc.CCRefused):
        cc.cdx_rows('CC-MAIN-2019-13', 'x.edu/p', http=h)
    with pytest.raises(cc.CCRefused):
        cc.fetch_record(dict(filename='a', offset=0, length=1), http=h)
    assert h.calls == []


def test_index_and_data_hosts_are_never_requested():
    h = fake({})
    for host in cc.FORBIDDEN_HOSTS:
        with pytest.raises(cc.CCRefused):
            cc.polite_get(f'https://{host}/robots.txt', http=h)
    with pytest.raises(cc.CCRefused):
        cc.polite_get('https://x.edu/robots.txt', http=h)  # only target robots may use external=True
    assert h.calls == []


def test_fetch_range_from_s3_and_parses():
    h = fake({cc.S3 + '/crawl-data/a.warc.gz': (206, {}, warc_record())})
    row = dict(timestamp='20190301000000', original='https://x.edu/p', filename='crawl-data/a.warc.gz', offset=10, length=99)
    st, body, _ = cc.fetch_record(row, http=h)
    assert st == 200 and body == HTML
    assert h.calls[-1][1]['Range'] == 'bytes=10-108' and '@' not in cc.UA and h.calls[-1][0].startswith('https://commoncrawl.s3.amazonaws.com/')
    assert cc.BYTES['requests'] == 1 and cc.BYTES['n'] == len(warc_record())


def test_surt():
    assert cc.surt('https://www.cs.Harvard.edu/People/') == 'edu,harvard,cs)/people/'
    assert cc.surt('http://x.edu/a?b=2&a=1') == 'edu,x)/a?a=1&b=2'


CL = ('edu,aaa)/ 20190101000000\tcdx-00000.gz\t0\t100\t1\n' 'edu,x)/a 20190101000000\tcdx-00000.gz\t100\t100\t2\n'
      'edu,x)/people 20190101000000\tcdx-00000.gz\t200\t150\t3\n' 'edu,x)/people/z 20190101000000\tcdx-00000.gz\t350\t100\t4\n'
      'edu,zzz)/ 20190101000000\tcdx-00001.gz\t0\t100\t5\n')


def test_cluster_blocks_binary_search(tmp_path):
    p = tmp_path / 'c.idx'
    p.write_text(CL)
    assert [b[3] for b in cc.cluster_blocks(str(p), 'edu,x)/people')] == [100, 200]  # previous block + the equal-key line
    assert [b[3] for b in cc.cluster_blocks(str(p), 'edu,x)/b')] == [100]
    assert [b[2:] for b in cc.cluster_blocks(str(p), 'edu,zzz)/')][-1] == ('cdx-00001.gz', 0, 100)
    assert cc.cluster_blocks(str(p), 'edu,0)/') == []


def test_cdx_rows_reads_cluster_once_then_only_the_block(tmp_path):
    crawl = 'CC-MAIN-2019-13'
    idx = cc.S3 + f'/cc-index/collections/{crawl}/indexes/'
    cdx = (gzip.compress(('edu,x)/people 20190401000000 ' + json.dumps(dict(url='https://x.edu/people', status='200', mime='text/html', digest='D', filename='crawl-data/a.warc.gz', offset='10', length='99')) + '\n'
                          'edu,x)/people 20190501000000 ' + json.dumps(dict(url='https://x.edu/people', status='404', mime='text/html', filename='f', offset='1', length='2')) + '\n').encode()))
    cl = f'edu,x)/people 20190101000000\tcdx-00000.gz\t0\t{len(cdx)}\t1\n'
    h = fake({idx + 'cluster.idx': (206, {'Content-Range': f'bytes 0-{len(cl) - 1}/{len(cl)}'}, cl.encode()), idx + 'cdx-00000.gz': (206, {}, cdx)})
    rows = cc.cdx_rows(crawl, 'https://x.edu/people', http=h)
    assert [(r['timestamp'], r['offset'], r['filename']) for r in rows] == [('20190401000000', 10, 'crawl-data/a.warc.gz')]
    assert all(u.startswith(cc.S3) for u, _ in h.calls) and h.calls[1][1]['Range'] == f'bytes=0-{len(cdx) - 1}'
    n = len(h.calls)
    cc.cdx_rows(crawl, 'https://x.edu/people', http=h)
    assert not any('cluster.idx' in u for u, _ in h.calls[n:])  # cluster.idx cached on disk, read once


def test_backoff_on_503_then_gives_up():
    h = fake({cc.S3 + '/z': (503, {'Retry-After': '7'}, b'')})
    with pytest.raises(cc.CCRefused):
        cc.polite_get(cc.S3 + '/z', http=h)
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


def test_cdx_cached_asks_once_and_stops_after_errors(tmp_path):
    con = sqlite3.connect(':memory:')
    cc.init_tables(con)
    crawl = 'CC-MAIN-2019-13'
    cl = 'edu,x)/p 20190101000000\tcdx-00000.gz\t0\t10\t1\n'
    blk = gzip.compress(('edu,x)/p 20190301000000 ' + json.dumps(dict(url='https://x.edu/p', status='200', mime='text/html', filename='f.warc.gz', offset='1', length='2', digest='D')) + '\n').encode())
    cl = f'edu,x)/p 20190101000000\tcdx-00000.gz\t0\t{len(blk)}\t1\n'
    idx = cc.S3 + f'/cc-index/collections/{crawl}/indexes/'
    h = fake({idx + 'cluster.idx': (206, {}, cl.encode()), idx + 'cdx-00000.gz': (206, {}, blk)})
    errs = {}
    assert cc.cdx_cached(con, crawl, 'x.edu/p', errs, http=h)[0]['offset'] == 1
    n = len(h.calls)
    assert cc.cdx_cached(con, crawl, 'x.edu/p', errs, http=h)[0]['crawl'] == crawl and len(h.calls) == n
    bad = fake({cc.S3 + '/cc-index/collections/CC-MAIN-2020-10/indexes/cluster.idx': (500, {}, b'')})
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
