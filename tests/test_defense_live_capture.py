"""The bounded recapture cannot expand its URL scope or retry a refused host."""
import hashlib
import sqlite3
import zlib

import pytest
import defense_live_capture as D


def manifest(urls):
    return {'school': 'gatech', 'host': D.HOST, 'max_pages': len(urls), 'urls': urls}


@pytest.mark.parametrize('url', ['http://hg.gatech.edu/node/1', 'https://hg.gatech.edu/node/1?next=/admin',
                                 'https://other.edu/node/1', 'https://hg.gatech.edu/node/add/'])
def test_exact_manifest_scope(url):
    with pytest.raises(ValueError):
        D.manifest_urls(manifest([url]), 1)


def fixture_cache(tmp_path, monkeypatch):
    db = tmp_path / 'captures.sqlite'
    c = sqlite3.connect(db)
    c.execute('create table live(url text,fetched_at text,status int,sha256 text,content_type text,raw_zlib blob)')
    monkeypatch.setattr(D.W, 'con', lambda school: c)
    monkeypatch.setattr(D.W, '_blocked', set())
    monkeypatch.setattr(D.W, 'robots_row', lambda *args: (200, 'User-agent: *\nDisallow: /node/add/\n'))
    monkeypatch.setattr(D.time, 'sleep', lambda _: None)
    return c


def test_refusal_stops_before_next_url_and_retains_raw_bytes(tmp_path, monkeypatch):
    c = fixture_cache(tmp_path, monkeypatch)
    urls = [f'https://hg.gatech.edu/node/{i}' for i in [1, 2, 3]]
    raw = b'<!doctype html><html><h1>PhD Defense</h1>Advisor: Dr. A</html>'
    calls = []

    def live(conn, url):
        calls.append(url)
        status, body = (200, raw) if len(calls) == 1 else (403, b'Forbidden')
        sha = hashlib.sha256(body).hexdigest()
        conn.execute('insert into live values(?,?,?,?,?,?)', (url, '2026-11-07', status, sha, 'text/html', zlib.compress(body)))
        return status, sha, []

    monkeypatch.setattr(D.W, 'live', live)
    result = D.capture(manifest(urls), tmp_path / 'out', tmp_path / 'host.lock', 3)
    assert calls == urls[:2]
    assert result['remaining'] == 1
    assert 'host refusal' in result['stop']
    assert (tmp_path / 'out/sources' / f'{hashlib.sha256(raw).hexdigest()}.html').read_bytes() == raw


def test_cached_refusal_prevents_even_robots_request(tmp_path, monkeypatch):
    fixture_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(D.W, '_blocked', {D.HOST})
    monkeypatch.setattr(D.W, 'robots_row', lambda *args: pytest.fail('refused host must not be retried'))
    result = D.capture(manifest(['https://hg.gatech.edu/node/1']), tmp_path / 'out', tmp_path / 'host.lock', 1)
    assert result['pages'] == []
    assert 'prior cached refusal' in result['stop']
