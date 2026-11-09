"""Polite, resumable, threaded live fetcher for the staged-school website sweep (tools/staged_websites.py).

One sqlite cache per school in the scratch directory (tables pages, robots, blocked); nothing is written to the school's own
capture stores. Rules (the brief 'Access rules'): robots.txt honoured for our own UA and, by name, ClaudeBot / anthropic-ai /
Claude-Web (a host that disallows them is never used); a generic User-Agent; per-host pacing of max(3 s, Crawl-delay); a bot
challenge, 401/403/429 marks the host blocked for the run and is never worked around (those URLs are queued for Wayback, not
fetched); redirects are followed by hand (<= 4 hops), each hop checked against its own host's robots.txt.
"""
import hashlib
import json
import sqlite3
import sys
import threading
import time
import urllib.parse
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I leaves the script's directory off sys.path
import school_web as W  # noqa: E402

MAX_BYTES = 2_000_000


class Fetcher:
    def __init__(self, db_path, min_delay=3.0, deadline=None):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.db_path, check_same_thread=False, timeout=60)
        self.con.executescript(
            'create table if not exists pages (url text primary key, final_url text, status int, sha256 text, fetched_at text, '
            'content_type text, body blob, chain text, note text);'
            'create table if not exists robots (host text primary key, fetched_at text, status int, body text);'
            'create table if not exists blocked (host text primary key, at text, why text);')
        self.db_lock = threading.RLock()
        self.host_locks, self.last = {}, {}
        self.glock = threading.Lock()
        self.min_delay = min_delay
        self.deadline = deadline
        self.blocked = {h for (h,) in self.con.execute('select host from blocked')}

    def _hl(self, host):
        with self.glock:
            return self.host_locks.setdefault(host, threading.Lock())

    def _robots(self, host, scheme='https'):
        with self._hl('robots:' + host):
            with self.db_lock:
                row = self.con.execute('select status, body from robots where host=?', (host,)).fetchone()
            if row is None:
                import requests
                try:
                    r = requests.get(f'{scheme}://{host}/robots.txt', headers={'User-Agent': W.UA}, timeout=30, allow_redirects=True)
                    row = (r.status_code, r.text if r.status_code == 200 else '')
                except Exception as e:  # noqa: BLE001
                    row = (-1, repr(e)[:200])
                with self.db_lock:
                    self.con.execute('insert or replace into robots values (?,?,?,?)',
                                     (host, time.strftime('%Y-%m-%dT%H:%M:%S'), row[0], row[1]))
                    self.con.commit()
            return row

    def allowed(self, url):
        """(allowed, delay, reason)"""
        sp = urllib.parse.urlsplit(url)
        if sp.hostname in self.blocked:
            return False, 0, 'host blocked this run (challenge or access refusal)'
        st, body = self._robots(sp.netloc, sp.scheme or 'https')
        ours, ai, delay = W.robots_decision(st, body, url)
        if not ours:
            return False, delay, f'robots.txt disallows (status {st})'
        if not ai:
            return False, delay, 'robots.txt names an AI agent (ClaudeBot/anthropic-ai/Claude-Web) as disallowed'
        return True, delay, None

    def block(self, host, why):
        self.blocked.add(host)
        with self.db_lock:
            self.con.execute('insert or replace into blocked values (?,?,?)', (host, time.strftime('%Y-%m-%dT%H:%M:%S'), why[:300]))
            self.con.commit()

    def cached(self, url):
        with self.db_lock:
            return self.con.execute('select url, final_url, status, sha256, fetched_at, content_type, body, chain, note from pages where url=?',
                                    (url,)).fetchone()

    def get(self, url):
        """dict(url, final_url, status, sha256, at, body, chain, note); status None when not fetched (note says why)."""
        row = self.cached(url)
        if row:
            return self._d(row)
        if self.deadline and time.time() > self.deadline:
            return dict(url=url, final_url=None, status=None, sha256=None, at=None, content_type=None, body=b'', chain=[],
                        note='deadline: left queued')
        import requests
        cur, chain, status, body, ct, note, loc = url, [], None, b'', None, None, None
        for hop in range(5):
            ok, delay, why = self.allowed(cur)
            if not ok:
                note = f'not fetched: {why}' + (f' (at {cur})' if cur != url else '')
                status = None
                break
            host = urllib.parse.urlsplit(cur).hostname
            with self._hl(host):
                w = self.last.get(host, 0) + max(delay, self.min_delay) - time.time()
                if w > 0:
                    time.sleep(w)
                try:
                    r = requests.get(cur, headers={'User-Agent': W.UA}, timeout=45, allow_redirects=False, stream=True)
                    body = r.raw.read(MAX_BYTES + 1, decode_content=True)
                    status, ct = r.status_code, (r.headers.get('Content-Type') or '').split(';')[0].strip().lower()
                    loc = r.headers.get('Location')
                    r.close()
                except Exception as e:  # noqa: BLE001
                    status, body, ct, loc, note = -1, b'', None, None, repr(e)[:200]
                self.last[host] = time.time()
            if status in (401, 403, 429):
                self.block(host, f'HTTP {status} at {cur}')
                note = f'host refused automated access (HTTP {status}); queue for Wayback only'
                break
            if status in (301, 302, 303, 307, 308) and loc:
                chain.append(dict(url=cur, status=status))
                cur = urllib.parse.urljoin(cur, loc)
                continue
            if status == 200 and W.CHALLENGE.search(body[:20000].decode('utf-8', 'replace')):
                self.block(host, f'challenge at {cur}')
                status, note = 999, 'bot challenge; host not used again, queue for Wayback only'
            break
        else:
            note = 'too many redirects'
        if len(body) > MAX_BYTES:
            body, note = body[:MAX_BYTES], 'truncated at 2 MB'
        sha = hashlib.sha256(body).hexdigest() if body and status == 200 else None
        at = time.strftime('%Y-%m-%dT%H:%M:%S')
        with self.db_lock:
            self.con.execute('insert or replace into pages values (?,?,?,?,?,?,?,?,?)',
                             (url, cur, status, sha, at, ct, zlib.compress(body, 6) if status == 200 else b'', json.dumps(chain), note))
            self.con.commit()
        return self._d(self.cached(url))

    @staticmethod
    def _d(row):
        url, final, status, sha, at, ct, body, chain, note = row
        return dict(url=url, final_url=final, status=status, sha256=sha, at=at, content_type=ct,
                    body=zlib.decompress(body) if body else b'', chain=json.loads(chain or '[]'), note=note)
