"""Pacing and HTTP 429 cooldowns shared by every download loop (2026-11-03).

The collector paces each host inside one process (3 s, 15 s for dspace.mit.edu) and, on an HTTP 429, paused the host for the
rest of the pass. Seven loops run side by side and Princeton, Stanford, CMU and MIT all hold dspace.mit.edu candidates, so the
host saw several 15 s clocks at once, and one 429 then burned every remaining dspace work of the pass as 'source_paused' (the
next pass's requeue asks again, and the first request of the next pass meets the 429 again: 2,114 attempts requeued on MIT
alone between 23:00 and 00:06 on 2026-11-03, no dspace copy since 2026-10-23).

State (raw/host-throttle.json, one flock): per host
  next     epoch time of the next free request slot (reserve() hands out slots `delay` apart across all processes)
  until    epoch time until which the host is cooling down after a 429
  n429     epochs of the 429s of the last 2 hours
A 429 starts a cooldown of 300 s, doubled for every earlier 429 in the last 2 hours (cap 3600 s). A cooldown up to WAIT_MAX is
waited out inside the host lock (the pass carries on afterwards); a longer one pauses the host as before ('source_paused', cleared
by the pass-start requeue). Nothing here asks a host more often than before, and robots.txt, crawl delays and paused hosts stand.
"""
import fcntl
import json
import os
import time
from pathlib import Path

BASE_COOLDOWN = 300.0
MAX_COOLDOWN = 3600.0
WAIT_MAX = 900.0       # a cooldown up to this long is waited out; longer pauses the host for the pass
WINDOW = 7200.0


def state_path():
    import atlas_paths as P
    return Path(P.FT_RAW) / 'host-throttle.json'


class _Locked:
    def __init__(self, path):
        self.path = Path(path)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(str(self.path) + '.lock', os.O_RDWR | os.O_CREAT, 0o664)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        try:
            self.state = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.state = {}
        return self.state

    def __exit__(self, *exc):
        if exc[0] is None:
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(self.state, indent=0))
            tmp.replace(self.path)
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)


def _prune(state, now):
    for h in list(state):
        s = state[h]
        s['n429'] = [t for t in s.get('n429', []) if now - t < WINDOW]
        if not s['n429'] and s.get('until', 0) < now and s.get('next', 0) < now:
            del state[h]


def reserve(host, delay, now=None, path=None):
    """Seconds this process must wait before asking `host`: the slot after every slot already handed out (any process)."""
    now = time.time() if now is None else now
    with _Locked(path or state_path()) as st:
        _prune(st, now)
        s = st.setdefault(host, {})
        slot = max(now, s.get('next', 0.0))
        s['next'] = slot + delay
        return slot - now


def cooldown_left(host, now=None, path=None):
    now = time.time() if now is None else now
    try:
        s = json.loads(Path(path or state_path()).read_text()).get(host) or {}
    except (OSError, ValueError):
        return 0.0
    return max(0.0, s.get('until', 0.0) - now)


def record_429(host, now=None, path=None):
    """A 429 from `host`: start (or extend) its cooldown. -> cooldown seconds."""
    now = time.time() if now is None else now
    with _Locked(path or state_path()) as st:
        _prune(st, now)
        s = st.setdefault(host, {})
        n = len(s.get('n429', []))
        cool = min(BASE_COOLDOWN * 2 ** n, MAX_COOLDOWN)
        s['n429'] = s.get('n429', []) + [now]
        s['until'] = max(s.get('until', 0.0), now + cool)
        s['next'] = max(s.get('next', 0.0), s['until'])
        return cool
