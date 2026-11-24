"""Capture store of the appointment-period review (2026-10-26): hierarchy/period-captures.sqlite, same table, politeness
and off-limits list as hierarchy/missing-pi-tools/mpcap.py (robots.txt honoured, >=2 s per host shared across processes,
bot challenges stored and not retried, dblp/escholarship/scholar refused).

fetch(url)                      one polite GET (live page or Wayback id_ URL), stored; a stored 200 capture is reused
copy_listing(school, cap_url)   copy a capture unchanged from listings/<school>/captures.sqlite (sha256 re-checked)
text(url) / around(url, needle) / quote_ok(url, quote)
ev(url, quote, kind, observed, note=None)   an evidence item whose quote is verified against the stored capture
"""
import re, sqlite3, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'hierarchy/missing-pi-tools'))
import mpcap  # noqa: E402

mpcap.DB = str(HERE / 'hierarchy' / 'period-captures.sqlite')
mpcap.connect().close()


def fetch(url, refetch=False):
    return mpcap.fetch(url, refetch=refetch)


def cached(url):
    return mpcap.cached(url)


def text(url):
    h = mpcap.cached(url)
    return h['text'] if h else ''


def around(url, needle, before=120, after=220, flags=re.I):
    t = text(url)
    return [t[max(0, m.start() - before):m.end() + after] for m in re.finditer(needle if isinstance(needle, str) and needle.startswith('(?') else re.escape(needle), t, flags)]


def quote_ok(url, quote):
    return mpcap.quote_ok(url, quote)


def copy_listing(school, capture_url):
    src = str(HERE / 'listings' / school / 'captures.sqlite')
    s = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    row = s.execute('select content_type from captures where capture_url=?', (capture_url,)).fetchone()
    s.close()
    return mpcap.copy(src, capture_url, 'select fetched_at, sha256, raw_zlib from captures where capture_url=?', (capture_url,),
                      f'listings/{school}/captures.sqlite', ctype=(row or ['text/html'])[0] or 'text/html')


def ev(url, quote, kind, observed, note=None):
    h = mpcap.cached(url)
    if not h:
        raise KeyError(f'not captured: {url}')
    q = ' '.join(quote.split())
    if q not in h['text']:
        raise ValueError(f'quote not in capture text: {url} :: {q[:120]}')
    e = dict(url=url, sha256=h['sha256'], quote=q, observed=observed, kind=kind)
    if note:
        e['note'] = note
    return e
