"""tools/discover_listings.py summarises CDX rows into half-years and gaps."""
import discover_listings as D
import hashlib
import json
import sqlite3
import zlib

import pytest


def rows(*ts):
    return [dict(timestamp=t, original='https://x.edu/people/') for t in ts]


def test_summarize_halves_and_gaps():
    s = D.summarize(rows('20160215000000', '20160915000000', '20170301000000'), 2016, 2017)
    assert s['halves'] == ['2016H1', '2016H2', '2017H1'] and s['missing'] == ['2017H2'] and s['captures'] == 3
    assert D.line('x.edu/people/', s) == 'x.edu/people/: 3 captures 20160215..20170301; 2016H1H2 2017H1'


def test_no_capture():
    s = D.summarize([], 2016, 2016)
    assert s['missing'] == ['2016H1', '2016H2'] and D.line('u', s) == 'u: no 200 capture'


def test_sample_picks_the_capture_nearest_mid_year_and_reports_format_and_paging(tmp_path, monkeypatch):
    rs = rows('20200110000000', '20200620000000', '20200912000000', '20240101000000')
    assert D.nearest(rs, 2020)['timestamp'] == '20200620000000' and D.nearest(rs, 2018) is None
    html = ('<div class="row profile-card__content variant-directory"><h4 class="card-block__title"><a href="/p/a">A B</a></h4><h6 class="card-block__subtitle">Professor</h6></div>'
            '<nav class="pager"><a href="?page=1">2</a></nav>')
    monkeypatch.setattr(D.W, 'capture', lambda c, ts, orig, url, key: ('cap' + ts, 200, 'sha', []))
    monkeypatch.setattr(D.W, 'raw_html', lambda c, cap: html)
    out = D.sample(None, 'k', 'x.edu/people/', rs, [2020, 2018], tmp_path)
    assert 'format gt_card, 1 entries, PAGED (1 more pages)' in out[0] and out[1] == '  2018: no capture'
    assert len(list(tmp_path.glob('*.html'))) == 1


def cache(tmp_path, url, body, status=200):
    path = tmp_path / 'captures.sqlite'
    c = sqlite3.connect(path)
    c.execute('create table cdx(query text, status integer, body text)')
    c.execute('create table captures(capture_url text, http_status integer, sha256 text, raw_zlib blob)')
    params = {'url': url, 'from': '2016', 'to': '2026', 'output': 'json',
              'fl': 'urlkey,timestamp,original,statuscode,digest,mimetype', 'limit': '30000',
              'filter': 'statuscode:200', 'collapse': 'timestamp:6'}
    query = 'https://web.archive.org/cdx/search/cdx?' + D.urlencode(params)
    c.execute('insert into cdx values(?,?,?)', (query, status, json.dumps(body)))
    c.commit()
    return path, c


def test_failed_cdx_is_not_a_successful_empty_inventory(monkeypatch):
    monkeypatch.setattr(D.W.wb, 'cdx', lambda *a: None)
    with pytest.raises(D.DiscoveryPending, match='availability remains unknown'):
        D.index_rows(None, 'x.edu', 2016, 2026)


def test_offline_missing_samples_stay_pending_without_cache_writes(tmp_path, monkeypatch):
    url = 'x.edu/people/'
    path, c = cache(tmp_path, url, [['timestamp', 'original'], ['20200620000000', 'https://' + url]])
    c.close()
    before = path.read_bytes()
    monkeypatch.setattr(D.W, 'db_path', lambda key: path)
    monkeypatch.setattr(D.W, 'con', lambda *a: pytest.fail('offline opened writer'))
    monkeypatch.setattr(D.W.wb, 'raw_get', lambda *a: pytest.fail('offline made network request'))
    report = tmp_path / 'report.json'
    rc = D.main(['k', url, '--offline', '--sample', '2018,2020', '--out', str(tmp_path / 'samples'), '--report', str(report)])
    result = json.loads(report.read_text())['urls'][url]
    assert rc == 3 and result['status'] == 'pending'
    assert result['samples'][0]['status'] == 'no_capture_in_successful_index'
    assert result['samples'][1]['status'] == 'pending'
    assert path.read_bytes() == before
    assert not list((tmp_path / 'samples').glob('*.html'))


def test_offline_saved_successful_sample_and_empty_index_are_distinct(tmp_path, monkeypatch):
    url = 'x.edu/people/'
    original = 'https://' + url
    path, c = cache(tmp_path, url, [['timestamp', 'original'], ['20200620000000', original]])
    body = b'<html><body>Archived faculty directory</body></html>'
    c.execute('insert into captures values(?,?,?,?)', ('https://web.archive.org/web/20200620000000id_/' + original,
              200, hashlib.sha256(body).hexdigest(), zlib.compress(body)))
    c.commit(); c.close()
    monkeypatch.setattr(D.W, 'db_path', lambda key: path)
    monkeypatch.setattr(D.W.wb, 'raw_get', lambda *a: pytest.fail('offline made network request'))
    report = tmp_path / 'report.json'
    assert D.main(['k', url, '--offline', '--sample', '2020', '--out', str(tmp_path / 'samples'), '--report', str(report)]) == 0
    result = json.loads(report.read_text())['urls'][url]
    assert result['status'] == 'discovered_unreviewed'
    assert result['samples'][0]['status'] == 'sampled_unreviewed'
    assert len(list((tmp_path / 'samples').glob('*.html'))) == 1


@pytest.mark.parametrize('status,body', [(429, 'Slow down'), (403, 'Denied'), (200, ''), (200, '<title>Just a moment...</title>')])
def test_failed_sample_does_not_complete_or_request_more_pages(tmp_path, monkeypatch, status, body):
    calls = []
    def fetch(c, ts, orig, url, key):
        calls.append(ts)
        return 'cap', status, 'sha', []
    monkeypatch.setattr(D.W, 'capture', fetch)
    monkeypatch.setattr(D.W, 'raw_html', lambda *a: body)
    monkeypatch.setattr(D, 'cached_capture', lambda *a: (_ for _ in ()).throw(D.DiscoveryPending('not cached')))
    receipts = []
    D.sample(None, 'k', 'x.edu/', rows('20200620000000', '20210620000000'), [2020, 2021], tmp_path, receipts=receipts)
    assert len(calls) == 1
    assert [r['status'] for r in receipts] == ['pending', 'pending']
    assert not list(tmp_path.glob('*.html'))


def test_cached_failure_and_corrupt_capture_do_not_become_success(tmp_path):
    path, c = cache(tmp_path, 'x.edu/', [], status=429)
    with pytest.raises(D.DiscoveryPending, match='No successful'):
        D.index_rows(c, 'x.edu/', 2016, 2026, offline=True)
    c.execute('insert into captures values(?,?,?,?)', ('https://web.archive.org/web/20200620000000id_/https://x.edu/people/',
              200, 'wrong-hash', zlib.compress(b'content')))
    with pytest.raises(D.DiscoveryPending, match='hash'):
        D.cached_capture(c, rows('20200620000000')[0])
    c.close()
