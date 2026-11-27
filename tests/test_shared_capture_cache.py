import concurrent.futures
import datetime
import hashlib
import sqlite3
import threading
import time

import pytest
import requests

from shared_capture_cache import CaptureCache, public_request, fetch_capture


def capture(body=b'original evidence', fetched=1000):
    return dict(url='https://example.edu/profile', final_url='https://example.edu/profile', capture_url=None,
                status=200, error=None, content=body, sha256=hashlib.sha256(body).hexdigest(),
                fetched_at=datetime.datetime.fromtimestamp(fetched, datetime.timezone.utc).isoformat())


def test_concurrent_requests_share_one_loader_and_preserve_observation(tmp_path):
    cache = CaptureCache(tmp_path, clock=lambda: 1001)
    calls = []
    barrier = threading.Barrier(2)
    def load():
        calls.append(1)
        time.sleep(.03)
        return capture()
    def worker():
        barrier.wait()
        return cache.fetch('https://example.edu/profile', load)
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: worker(), range(2)))
    assert len(calls) == 1
    assert all(r['content'] == b'original evidence' and r['fetched_at'] == capture()['fetched_at'] for r in results)


def test_expiry_force_and_refusal_cooldowns(tmp_path):
    now = [1001]
    cache = CaptureCache(tmp_path, clock=lambda: now[0])
    calls = []
    def load():
        calls.append(1)
        return capture(fetched=now[0])
    cache.fetch('https://x.edu/', load)
    cache.fetch('https://x.edu/', load, force=True)
    now[0] += 86401
    cache.fetch('https://x.edu/', load)
    assert len(calls) == 3
    denied = lambda: dict(url='https://denied.edu/', status=429, error='HTTP 429', retry_after='900', content=b'')
    cache.fetch('https://denied.edu/', denied)
    now[0] += 400
    assert cache.fetch('https://denied.edu/', lambda: pytest.fail('cooldown bypassed'))['status'] == 429


def test_corrupt_bytes_do_not_trigger_an_unlogged_refetch(tmp_path):
    cache = CaptureCache(tmp_path, clock=lambda: 1001)
    cache.fetch('https://x.edu/', capture)
    with sqlite3.connect(tmp_path / 'captures.sqlite') as db:
        db.execute('DELETE FROM objects')
    with pytest.raises(ValueError, match='checksum'):
        cache.fetch('https://x.edu/', lambda: pytest.fail('corruption hidden'))


def test_authenticated_or_variant_requests_never_enter_public_cache():
    assert public_request('https://example.edu/a')
    for url in ('https://user:secret@example.edu/a', 'https://example.edu/a?api_key=private', 'file:///tmp/a'):
        assert not public_request(url)
    assert not public_request('https://example.edu/a', {'headers': {'Accept-Language': 'zh'}})
    session = requests.Session()
    session.cookies.set('session', 'private')
    assert not public_request('https://example.edu/a', session=session)
    other = requests.Session()
    other.cookies.set('session', 'private', domain='other.example.edu')
    assert public_request('https://example.edu/a', session=other)


def test_cross_school_import_preserves_exact_capture_time_and_source(tmp_path):
    from types import SimpleNamespace
    import contextlib
    saved = []
    toolkit = SimpleNamespace(_sess=requests.Session(), UA='public-agent',
        cached=lambda *_: capture(), write_db=lambda _: 'original-capture.sqlite',
        connect=lambda _: contextlib.nullcontext('db'))
    def insert(db, *args, **kwargs):
        saved.append((args, kwargs))
        return 42, args[4]
    toolkit._insert = insert
    cache = CaptureCache(tmp_path, clock=lambda: 1001)
    first = fetch_capture(cache, toolkit, 'first', 'https://example.edu/profile', capture, {})
    second = fetch_capture(cache, toolkit, 'second', 'https://example.edu/profile', lambda: pytest.fail('duplicate request'), {})
    assert first['content'] == second['content']
    assert second['id'] == 42
    assert saved[0][1]['fetched_at'] == capture()['fetched_at']
    assert saved[0][1]['copied_from'] == 'original-capture.sqlite'
