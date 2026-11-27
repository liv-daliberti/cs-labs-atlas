"""Cross-process reuse of public captures; callers retain their access-policy checks."""
import contextlib
import datetime
import email.utils
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import parse_qsl, urlsplit
import zlib
import requests


def public_request(url, options=None, session=None):
    options = options or {}
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return False
    if any(options.get(k) for k in ('params', 'headers', 'store_url')):
        return False
    private = re.compile(r'key|token|auth|password|signature|credential|session|^sig$|^x-amz-', re.I)
    if any(private.search(k) for k, _ in parse_qsl(parsed.query)):
        return False
    if session is not None:
        if getattr(session, 'auth', None) or getattr(session, 'params', None):
            return False
        prepared = session.prepare_request(requests.Request('GET', url))
        if any(k.lower() in ('authorization', 'cookie') for k in prepared.headers):
            return False
    return True


class CaptureCache:
    def __init__(self, directory, clock=time.time):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS objects (sha TEXT PRIMARY KEY, body BLOB NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS requests (key TEXT PRIMARY KEY, metadata TEXT NOT NULL, sha TEXT, expires REAL NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.directory / 'captures.sqlite', timeout=120)

    @contextlib.contextmanager
    def locked(self, key):
        # Permanent lock inodes: deleting a lock file can let two processes hold different locks.
        with (self.directory / (key + '.lock')).open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def get(self, key):
        with self.connect() as db:
            row = db.execute('SELECT metadata,sha,expires FROM requests WHERE key=?', (key,)).fetchone()
            if not row or row[2] <= self.clock():
                return None
            value = json.loads(row[0])
            body = db.execute('SELECT body FROM objects WHERE sha=?', (row[1],)).fetchone() if row[1] else None
        raw = zlib.decompress(body[0]) if body else b''
        if row[1] and (not body or hashlib.sha256(raw).hexdigest() != row[1]):
            raise ValueError('Shared capture checksum mismatch; preserve and inspect the cache')
        return dict(value, content=raw, cached=True, shared_cache=True)

    def put(self, key, result, url):
        value = {k: result.get(k) for k in ('url', 'final_url', 'capture_url', 'status', 'http_status',
                 'sha256', 'content_type', 'error', 'fetched_at', 'retry_after', 'copied_from')}
        body = result.get('content') or b''
        status = result.get('http_status') or result.get('status')
        expires, digest = 0, None
        if result.get('status') == 200 and not result.get('error') and result.get('fetched_at') and len(body) <= 20_000_000:
            digest = hashlib.sha256(body).hexdigest()
            if result.get('sha256') and digest != result['sha256']:
                raise ValueError('Capture bytes differ from their recorded checksum')
            observed = datetime.datetime.fromisoformat(result['fetched_at'].replace('Z', '+00:00'))
            expires = observed.timestamp() + 86400
            if re.search(r'/web/\d{8,14}(?:id_)?/', url):
                expires = self.clock() + 3650 * 86400
        elif status in (403, 429):
            body = b''
            delay = 86400 if status == 403 else 300
            retry = result.get('retry_after')
            if retry:
                try:
                    delay = max(delay, float(retry))
                except ValueError:
                    try:
                        delay = max(delay, email.utils.parsedate_to_datetime(retry).timestamp() - self.clock())
                    except (TypeError, ValueError):
                        pass
            expires = self.clock() + delay
        else:
            return
        value['sha256'] = digest
        with self.connect() as db:
            if digest:
                db.execute('INSERT OR IGNORE INTO objects VALUES (?,?)', (digest, zlib.compress(body)))
            db.execute('INSERT OR REPLACE INTO requests VALUES (?,?,?,?)', (key, json.dumps(value), digest, expires))

    def fetch(self, url, load, *, force=False, context='public-default'):
        key = hashlib.sha256(json.dumps([url, context]).encode()).hexdigest()
        with self.locked(key):
            hit = None if force else self.get(key)
            if hit is not None:
                return hit
            result = load()
            self.put(key, result, url)
            return result


def fetch_capture(cache, toolkit, school, url, loader, options):
    """Called only AFTER the charter/AI-agent/denial checks in labpage_audit.Kit."""
    if not public_request(url, options, toolkit._sess):
        return loader()

    def load():
        result = loader()
        if result.get('status') == 200 and not result.get('error'):
            stored = toolkit.cached(school, url)
            if stored and stored.get('sha256') == result.get('sha256'):
                result = dict(result, fetched_at=stored['fetched_at'], copied_from=toolkit.write_db(school))
        return result

    result = cache.fetch(url, load, force=options.get('force', False), context=toolkit.UA)
    if result.get('shared_cache') and result.get('status') == 200:
        with toolkit.connect(school) as db:
            rid, _ = toolkit._insert(db, result['url'], result['final_url'], result['capture_url'], 200,
                result['content'], result['content_type'], None, fetched_at=result['fetched_at'],
                copied_from=result.get('copied_from') or str(cache.directory), sha=result['sha256'])
        result['id'] = rid
    return result
