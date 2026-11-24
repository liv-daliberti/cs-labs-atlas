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
import sys
import time
from pathlib import Path

BASE_COOLDOWN = 300.0
MAX_COOLDOWN = 3600.0
WAIT_MAX = 900.0       # a cooldown up to this long is waited out; longer pauses the host for the pass
WINDOW = 7200.0
# 2026-11-04: one request budget per host for ALL our clients (download loops, etd crawl). The interval here is the real limit: reserve() uses it
# instead of the caller's own delay, so a loop asking at 6 s and a crawl asking at 3 s still share 5 s slots (~12 a minute for web.archive.org,
# whose playback limit is about 15 a minute; four 429s in two hours on 2026-11-04 came from two clients each keeping its own clock).
# 2026-11-05: 8 s (7.5 a minute). At 5 s the clients still drew 429s in bursts of three or four (slots reserved before a 429 fired into the
# cooldown), and each burst 429 doubled the cooldown up to the 1-hour cap; see wait_slot() and BURST below. 2026-11-06: the first slot after a
# cooldown is a lone probe (PROBE_HOLD), see reserve().
SHARED_INTERVAL = {'web.archive.org': 15.0, 'archive.org': 15.0, 'arxiv.org': 15.0}   # 2026-11-06 slow lane (owner): 4 a minute; 8 s still drew 429s
# Direct arXiv PDF requests share its 15-second crawl-delay clock.
BASE_BY_HOST = {'web.archive.org': 900.0, 'archive.org': 900.0}     # first cooldown after a 429: 15 min for the archive (others BASE_COOLDOWN)
BURST = 60.0           # a 429 within this many seconds of the previous one (or inside a running cooldown) is the same event: no doubling
LOW_GAP_SLOTS = 3      # a low-priority client (the SMARTech crawl: evidence) takes at most one slot in 3 while a loop was served in the last LOW_WINDOW s
LOW_WINDOW = 60.0
PROBE_HOLD = 120.0     # after a cooldown ends, one client probes; every other slot waits this long for the probe's 429 (owner 2026-11-06: one request per cooldown)


def state_path():
    """The one shared clock file. CS_ATLAS_THROTTLE_STATE overrides it (a scratch tree or overlay must point at main's file so no copy of the clock forks:
    an overlay's own raw/host-throttle.json hid a running cooldown on 2026-11-06)."""
    if os.environ.get('CS_ATLAS_THROTTLE_STATE'):
        return Path(os.environ['CS_ATLAS_THROTTLE_STATE'])
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
        if not s['n429'] and s.get('until', 0) < now and s.get('next', 0) < now and now - s.get('last_hi', -1e12) > LOW_WINDOW:
            del state[h]


def reserve(host, delay, now=None, path=None, low=False):
    """Seconds this process must wait before asking `host`: the slot after every slot already handed out (any process). A host in SHARED_INTERVAL
    uses that interval whatever `delay` the caller passes. low=True (evidence crawls): the slot is also at least LOW_GAP_SLOTS intervals after the
    previous low slot while a normal client reserved a slot within LOW_WINDOW seconds, so the download loops keep 2 of every 3 slots."""
    now = time.time() if now is None else now
    delay = SHARED_INTERVAL.get(host, delay)
    with _Locked(path or state_path()) as st:
        _prune(st, now)
        s = st.setdefault(host, {})
        slot = max(now, s.get('next', 0.0))
        until = s.get('until', 0.0)
        if until > 0 and slot >= until:
            # 2026-11-06: the first slot after a cooldown is a probe. Three loops fired within 45 s of a cooldown ending (14:55 local) and the
            # archive refused all three, restarting the 1-hour cooldown. Every later slot waits PROBE_HOLD s after the probe, so a 429 on the
            # probe (record_429 moves `until`) reaches the others before they ask.
            if s.get('probed_for', 0.0) < until:
                s['probed_for'], s['probe_at'] = until, slot
            else:
                slot = max(slot, s.get('probe_at', 0.0) + PROBE_HOLD)
        if low:
            if now - s.get('last_hi', -1e12) < LOW_WINDOW:
                slot = max(slot, s.get('last_low', -1e12) + LOW_GAP_SLOTS * delay)
            s['last_low'] = slot
        else:
            s['last_hi'] = now
        s['next'] = slot + delay
        return slot - now


def _until(host, path=None):
    try:
        return float((json.loads(Path(path or state_path()).read_text()).get(host) or {}).get('until', 0.0))
    except (OSError, ValueError):
        return 0.0


def wait_slot(host, delay, low=False, sleep=time.sleep, path=None, max_cooldown=WAIT_MAX):
    """Wait for this process's next request slot of `host`, then re-check the shared cooldown: a 429 recorded by another client while this one
    waited starts (or extends) a cooldown that the slot does not know about, so wait that out and reserve again rather than firing into it.
    Only a cooldown that ends later than the one already waited out sends it round again. Raises RuntimeError when a cooldown longer than
    `max_cooldown` is running (the caller pauses the host, as before). -> seconds waited."""
    waited, seen = 0.0, 0.0
    while True:
        until, left = _until(host, path), cooldown_left(host, path=path)
        if left > max_cooldown:
            raise RuntimeError(f'{host} cooling down for {left:.0f}s')
        if left > 0 and until > seen:
            sleep(left + 1.0)
            waited += left + 1.0
        seen = max(seen, until)
        w = reserve(host, delay, path=path, low=low)
        sleep(w)
        waited += w
        if _until(host, path) <= seen:      # no new 429 while this client waited for its slot
            return waited


def cooldown_left(host, now=None, path=None):
    now = time.time() if now is None else now
    try:
        s = json.loads(Path(path or state_path()).read_text()).get(host) or {}
    except (OSError, ValueError):
        return 0.0
    return max(0.0, s.get('until', 0.0) - now)


def _log_429(host, now, path, burst):
    """2026-11-06: one JSON line per 429 beside the state file (host-throttle-429.jsonl), naming the client (Slurm job, job name, pid,
    command), so a cooldown that stops every client can be attributed. Never raises."""
    try:
        state = Path(path or state_path())
        rec = {'at': now, 'host': host, 'burst': burst, 'job': os.environ.get('SLURM_JOB_ID'), 'array': os.environ.get('SLURM_ARRAY_JOB_ID'),
               'task': os.environ.get('SLURM_ARRAY_TASK_ID'), 'job_name': os.environ.get('SLURM_JOB_NAME'), 'pid': os.getpid(),
               'cmd': ' '.join(sys.argv[:3])[:200]}
        with open(state.with_name(state.stem + '-429.jsonl'), 'a') as f:
            f.write(json.dumps(rec) + '\n')
    except OSError:
        pass


def record_429(host, now=None, path=None):
    """A 429 from `host`: start (or extend) its cooldown, and log who drew it. -> cooldown seconds."""
    now = time.time() if now is None else now
    with _Locked(path or state_path()) as st:
        _prune(st, now)
        s = st.setdefault(host, {})
        prev = s.get('n429', [])
        if prev and (now - prev[-1] < BURST or now < s.get('until', 0.0)):   # same burst: slots reserved before the first 429 fired into it
            s['next'] = max(s.get('next', 0.0), s.get('until', 0.0))
            _log_429(host, now, path, True)
            return max(0.0, s.get('until', 0.0) - now)
        n = len(prev)
        cool = min(BASE_BY_HOST.get(host, BASE_COOLDOWN) * 2 ** n, MAX_COOLDOWN)
        s['n429'] = s.get('n429', []) + [now]
        s['until'] = max(s.get('until', 0.0), now + cool)
        s['next'] = max(s.get('next', 0.0), s['until'])
        _log_429(host, now, path, False)
        return cool
