"""A small OpenAlex API client that never shows the key, and logs every request to the shared budget ledger.

Why: on 2026-11-04 a traceback printed the API key (a `requests` exception carries the full URL, query string included, and Python
prints the chained cause too). Everything here goes through `Client.get`, which
  - sends the key only as the `api_key` parameter and never puts it in a message, a log line or an exception text (`redact`);
  - re-raises transport errors as `OAError` from None, so no chained traceback holds the URL;
  - installs a `sys.excepthook` that redacts whatever else reaches the top level (`install_excepthook`);
  - appends one line per request to the ledger raw/openalex_budget.jsonl (fulltext-push/oa_refresh.py's format: at, kind, status, credits,
    remaining) and stops when the run's own credit cap or the shared floor is reached.
The key comes from ~/.config/cs-atlas/openalex.env (or OPENALEX_API_KEY in the environment). Tests: tests/test_oa_api.py.
"""
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

import atlas_paths as P  # noqa: E402

KEY_FILE = Path.home() / '.config' / 'cs-atlas' / 'openalex.env'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
LEDGER = P.FT_RAW / 'openalex_budget.jsonl'
API = 'https://api.openalex.org'


class OAError(RuntimeError):
    pass


class Spent(OAError):
    """The run's credit cap or the shared floor was reached; nothing more is asked."""


def load_key():
    k = os.environ.get('OPENALEX_API_KEY')
    if not k and KEY_FILE.exists():
        for line in KEY_FILE.read_text().splitlines():
            m = re.match(r'\s*(?:export\s+)?OPENALEX_API_KEY=(.*)$', line)
            if m and not line.lstrip().startswith('#'):
                k = m.group(1).strip().strip('"').strip("'")
    return k or ''


def redact(text, key=None):
    """`text` with the key, any api_key=... parameter and the owner's mailto parameter masked."""
    text = str(text)
    key = key or load_key()
    if key:
        text = text.replace(key, '***')
    return re.sub(r'((?:api_key|mailto)=)[^&\s\'")]+', r'\1***', text)


def install_excepthook(key=None):
    def hook(etype, value, tb):
        sys.stderr.write(redact(''.join(traceback.format_exception(etype, value, tb)), key))
    sys.excepthook = hook


class Client:
    def __init__(self, cap, kind='api', floor=None, key=None, ledger=LEDGER):
        import requests
        self.key = key if key is not None else load_key()
        if not self.key:
            raise OAError('no OpenAlex key (OPENALEX_API_KEY or ~/.config/cs-atlas/openalex.env)')
        install_excepthook(self.key)
        self.s = requests.Session()
        self.s.headers['User-Agent'] = UA
        self.cap, self.kind, self.floor, self.ledger = cap, kind, floor, Path(ledger)
        self.used, self.requests, self.remaining = 0, 0, None
        self.pause = 0.6

    def _log(self, kind, status, credits, remaining):
        with self.ledger.open('a') as f:
            f.write(json.dumps(dict(at=time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime()), kind=kind, status=status,
                                    credits=None if credits is None else str(credits), remaining=remaining)) + '\n')

    def get(self, path, params=None, kind=None, tries=5):
        """GET api.openalex.org/<path> -> (json, response headers). One credit is charged per list request; `Spent` before a request that would pass the cap."""
        import requests
        kind = f'{self.kind}:{kind}' if kind else self.kind
        last = None
        for attempt in range(tries):
            if self.used >= self.cap:
                raise Spent(f'run cap of {self.cap} credits reached')
            time.sleep(self.pause)
            try:
                r = self.s.get(f'{API}/{path.lstrip("/")}', params=dict(params or {}, api_key=self.key), timeout=(15, 120), allow_redirects=False)
            except requests.RequestException as e:
                last = type(e).__name__
                time.sleep(5 * (attempt + 1))
                continue
            rem = r.headers.get('X-RateLimit-Remaining')
            cr = r.headers.get('X-RateLimit-Credits-Used')
            self.requests += 1
            self.used += int(cr) if (cr or '').isdigit() else 1
            self.remaining = int(rem) if (rem or '').isdigit() else self.remaining
            self._log(kind, r.status_code, cr, rem)
            if r.status_code == 429 and 'Plan upgrade required' in r.text[:300]:
                raise OAError(f'{path}: {redact(r.text[:200], self.key)}')   # from_updated_date, from_created_date and updated/created sorts need a paid plan
            if r.status_code == 429:
                # a burst limit has no remaining-credits header; only a header that says 0 means the day is spent
                if rem == '0':
                    raise Spent('HTTP 429 (daily credits spent)')
                last = 'HTTP 429 (rate limited)'
                time.sleep(10 * (attempt + 1))
                continue
            if self.floor is not None and self.remaining is not None and self.remaining < self.floor:
                raise Spent(f'shared floor reached ({self.remaining} left)')
            if r.status_code in (301, 302, 303, 307, 308):
                return dict(redirect=r.headers.get('Location') or ''), r.headers
            if r.status_code == 200:
                try:
                    return r.json(), r.headers
                except ValueError:
                    last = 'truncated body'
            elif r.status_code == 404:
                return None, r.headers
            else:
                last = f'HTTP {r.status_code}'
            time.sleep(5 * (attempt + 1))
        raise OAError(f'{path}: failed after {tries} tries ({last})')
