"""Capture store of the CS-related scope review (owner decision 2026-10-22): one SQLite store per school,
hierarchy/cs-related-captures-<school>.sqlite, same table and politeness as hierarchy/missing-pi-tools/mpcap.py (robots.txt
honoured, 2 s per host shared across processes, dblp/escholarship/scholar refused, bot challenges stored and not retried).

use(school)           point mpcap at the school's store (call once per process, before any fetch)
fetch(url)            mpcap.fetch: a live page or a Wayback id_ URL, stored; a stored 200 capture is reused
copy_listing(src, capture_url, copied_from)   copy one capture from a listings sweep store (capture_url, raw_zlib, sha256)
copy_thesis(src, url, copied_from)            copy one capture from a thesis store (url, content zlib, sha256)
text(url) / quote_ok(url, quote) / around(url, needle)   the stored capture's text view (tags removed, whitespace collapsed)
"""
import sqlite3, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'hierarchy/missing-pi-tools'))
import mpcap  # noqa: E402

SCHOOL = None


def use(school):
    global SCHOOL
    SCHOOL = school
    mpcap.DB = str(HERE / 'hierarchy' / f'cs-related-captures-{school}.sqlite')
    mpcap._robots.clear()
    mpcap.connect().close()
    return mpcap.DB


def fetch(url, refetch=False):
    assert SCHOOL, 'call use(school) first'
    return mpcap.fetch(url, refetch=refetch)


def cached(url):
    return mpcap.cached(url)


def text(url):
    h = mpcap.cached(url)
    return h['text'] if h else ''


def quote_ok(url, quote):
    return mpcap.quote_ok(url, quote)


def around(url, needle, before=80, after=200):
    return mpcap.around(url, needle, before, after)


def copy_listing(src_db, capture_url, copied_from):
    """A Wayback (or live) listing capture from a listings sweep store, copied unchanged (fetched_at, sha256, bytes)."""
    s = sqlite3.connect(f'file:{src_db}?mode=ro', uri=True)
    ct = (s.execute('select content_type from captures where capture_url=?', (capture_url,)).fetchone() or ['text/html'])[0]
    s.close()
    return mpcap.copy(src_db, capture_url, 'select fetched_at, sha256, raw_zlib from captures where capture_url=?', (capture_url,),
                      copied_from, ctype=ct or 'text/html')


def copy_thesis(src_db, url, copied_from):
    s = sqlite3.connect(f'file:{src_db}?mode=ro', uri=True)
    ct = (s.execute('select content_type from captures where url=? and status=200 order by id desc limit 1', (url,)).fetchone() or ['text/html'])[0]
    s.close()
    return mpcap.copy(src_db, url, 'select fetched_at, sha256, content from captures where url=? and status=200 and error is null order by id desc limit 1',
                      (url,), copied_from, ctype=ct or 'text/html')


def copy_mp(src_db, url, copied_from):
    """A capture from another mpcap-format store (hierarchy/missing-pi-captures.sqlite)."""
    s = sqlite3.connect(f'file:{src_db}?mode=ro', uri=True)
    ct = (s.execute('select content_type from captures where (url=? or capture_url=?) and status=200 order by id desc limit 1', (url, url)).fetchone() or ['text/html'])[0]
    s.close()
    return mpcap.copy(src_db, url, 'select fetched_at, sha256, content from captures where (url=? or capture_url=?) and status=200 and error is null order by id desc limit 1',
                      (url, url), copied_from, ctype=ct or 'text/html')
