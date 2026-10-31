"""Princeton + EPFL CS-related scope review (owner decision 2026-10-22; DBLP-based candidate list): the polite fetcher of
hierarchy/missing-pi-tools/mpcap.py (robots.txt honoured, 2 s per host shared with the sister agents' stamp files,
dblp/escholarship/scholar refused, bot challenges stored and not retried), pointed at one store per school:
hierarchy/<school>/cs-related-captures.sqlite (same captures table as mpcap).

use(school)                       point mpcap at hierarchy/<school>/cs-related-captures.sqlite
fetch(url) / cached(url) / quote_ok(url, quote) / around(url, needle)    mpcap's, on that store
copy_from(src_db, url, kind)      copy one capture unchanged (fetched_at, sha256, bytes) from another store:
                                  kind 'mp' = mpcap-format store (captures.url/capture_url, content),
                                  'listing' = listings sweep store (capture_url, raw_zlib), 'thesis' = thesis store (url, content)
"""
import sqlite3, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'hierarchy/missing-pi-tools'))
import mpcap  # noqa: E402

SCHOOL = None


def use(school):
    global SCHOOL
    SCHOOL = school
    mpcap.DB = str(HERE / 'hierarchy' / school / 'cs-related-captures.sqlite')
    mpcap._robots.clear()
    mpcap.connect().close()
    return mpcap.DB


def fetch(url, refetch=False):
    assert SCHOOL
    return mpcap.fetch(url, refetch=refetch)


cached, quote_ok, around = mpcap.cached, mpcap.quote_ok, mpcap.around


def rel(p):
    p = str(p)
    return p[len(str(HERE)) + 1:] if p.startswith(str(HERE)) else p


def copy_from(src_db, url, kind='mp'):
    assert SCHOOL
    s = sqlite3.connect(f'file:{src_db}?mode=ro', uri=True)
    if kind == 'listing':
        ct = (s.execute('select content_type from captures where capture_url=?', (url,)).fetchone() or ['text/html'])[0]
        sql, args = 'select fetched_at, sha256, raw_zlib from captures where capture_url=?', (url,)
    elif kind == 'thesis':
        ct = (s.execute('select content_type from captures where url=? and status=200 order by id desc limit 1', (url,)).fetchone() or ['text/html'])[0]
        sql, args = 'select fetched_at, sha256, content from captures where url=? and status=200 and error is null order by id desc limit 1', (url,)
    else:
        ct = (s.execute('select content_type from captures where (url=? or capture_url=?) and status=200 order by id desc limit 1', (url, url)).fetchone() or ['text/html'])[0]
        sql, args = ('select fetched_at, sha256, content from captures where (url=? or capture_url=?) and status=200 and error is null '
                     'order by id desc limit 1'), (url, url)
    s.close()
    return mpcap.copy(src_db, url, sql, args, rel(src_db), ctype=ct or 'text/html')
