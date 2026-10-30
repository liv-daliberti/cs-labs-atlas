"""Evidence helpers for the CS-related review: copy a stored capture from an earlier sweep's store into
hierarchy/cmu/cs-related-captures.sqlite (bytes and sha256 unchanged, copied_from set), then cut exact quotes from the
stored text."""
import json, re, sqlite3
from pathlib import Path
import csrcap

HERE = Path(csrcap.HERE)
THESIS_DB = HERE / 'hierarchy/cmu/thesis-captures.sqlite'
LIST_DB = HERE / 'listings/cmu/captures.sqlite'


def copy_thesis(url):
    """A KiltHub (figshare API) or SCS tech-report capture from hierarchy/cmu/thesis-captures.sqlite."""
    s = sqlite3.connect(f'file:{THESIS_DB}?mode=ro', uri=True)
    ct = (s.execute('select content_type from captures where url=? and status=200 order by id desc limit 1', (url,)).fetchone() or [None])[0]
    s.close()
    return csrcap.copy(str(THESIS_DB), url, 'select fetched_at, sha256, content from captures where url=? and status=200 order by id desc limit 1',
                       (url,), 'hierarchy/cmu/thesis-captures.sqlite', ctype=ct or ('application/json' if 'figshare' in url else 'text/html'))


def copy_listing(capture_url):
    """A Wayback capture from listings/cmu/captures.sqlite (raw_zlib)."""
    s = sqlite3.connect(f'file:{LIST_DB}?mode=ro', uri=True)
    ct = (s.execute('select content_type from captures where capture_url=?', (capture_url,)).fetchone() or [None])[0]
    s.close()
    return csrcap.copy(str(LIST_DB), capture_url, 'select fetched_at, sha256, raw_zlib from captures where capture_url=?', (capture_url,),
                       'listings/cmu/captures.sqlite', ctype=ct or 'text/html')


def text_of(url):
    h = csrcap.cached(url)
    return h['text'] if h else ''


def sha_of(url):
    h = csrcap.cached(url)
    return h['sha256'] if h else None


def find(url, pattern, before=0, after=0, flags=0):
    """Exact substring of the stored text around the first regex match (None when absent)."""
    t = text_of(url)
    m = re.search(pattern, t, flags)
    if not m:
        return None
    return t[max(0, m.start() - before):m.end() + after].strip()


def kilthub_basis(url, student, adviser_field):
    """pi_basis from a KiltHub thesis record: the quote is the record's own Advisor(s) field."""
    copy_thesis(url)
    t = text_of(url)
    adv = json.dumps(adviser_field)[1:-1]  # JSON-escaped as stored ("\n" stays the two characters \ and n)
    q = f'"name": "Advisor(s)", "value": "{adv}"'
    qs = f'"full_name": "{json.dumps(student)[1:-1]}"'
    assert q in t, (url, q)
    return dict(url=url, sha256=sha_of(url), quote=q, quote_student=qs if qs in t else None)
