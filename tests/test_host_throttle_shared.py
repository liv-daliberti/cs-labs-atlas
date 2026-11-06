"""One request budget for web.archive.org across every client (host_throttle.SHARED_INTERVAL, 2026-11-04): slots are 8 s apart (2026-11-05; 5 s before) across processes whatever
delay each asks for, a low-priority client (the evidence crawl) yields to the loops, and a 429 recorded by one client cools the host for all."""
import json
import os
import subprocess
import sys
from pathlib import Path

import host_throttle as HT

FTP = Path(__file__).resolve().parents[1] / 'fulltext-push'
CHILD = ("import json,sys; import host_throttle as HT; "
         "print(json.dumps([HT.reserve('web.archive.org', float(sys.argv[2]), now=1000.0, path=sys.argv[1], low=sys.argv[3]=='1') for _ in range(6)]))")


def run_child(state, delay, low):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(FTP), os.environ.get('PYTHONPATH', '')])))
    return subprocess.Popen([sys.executable, '-c', CHILD, str(state), str(delay), '1' if low else '0'], stdout=subprocess.PIPE, text=True, env=env)


def test_slots_are_shared_across_processes_whatever_delay_each_asks(tmp_path):
    state = tmp_path / 'ht.json'
    ps = [run_child(state, 6.0, False), run_child(state, 3.0, False)]   # a loop at 6 s and a crawl asking for 3 s
    waits = sorted(w for p in ps for w in json.loads(p.communicate()[0]))
    assert len(waits) == 12 and waits[0] == 0.0
    assert all(b - a >= 8.0 - 1e-9 for a, b in zip(waits, waits[1:])) and waits[-1] == 88.0   # 12 slots, 8 s apart, no overlap


def test_low_priority_yields_to_the_loops(tmp_path):
    path = tmp_path / 'ht.json'
    HT.reserve('web.archive.org', 6.0, now=1000.0, path=path)                     # a loop was served just now
    lows = [HT.reserve('web.archive.org', 3.0, now=1000.0, path=path, low=True) for _ in range(3)]
    assert [round(b - a) for a, b in zip(lows, lows[1:])] == [24, 24]             # one slot in three
    for _ in range(3):
        HT.reserve('web.archive.org', 6.0, now=1000.0, path=path)
    # with no loop in the last minute the crawl gets every slot
    p2 = tmp_path / 'ht2.json'
    quiet = [HT.reserve('web.archive.org', 3.0, now=1000.0, path=p2, low=True) for _ in range(3)]
    assert [round(b - a) for a, b in zip(quiet, quiet[1:])] == [8, 8]


def test_other_hosts_keep_the_callers_delay_and_a_429_cools_for_everyone(tmp_path):
    path = tmp_path / 'ht.json'
    assert HT.reserve('dspace.mit.edu', 15.0, now=0.0, path=path) == 0.0 and HT.reserve('dspace.mit.edu', 15.0, now=0.0, path=path) == 15.0
    cool = HT.record_429('web.archive.org', now=100.0, path=path)
    assert cool == 300.0 and HT.cooldown_left('web.archive.org', now=150.0, path=path) == 250.0
    assert HT.reserve('web.archive.org', 3.0, now=150.0, path=path) >= 250.0      # a client that did not see the 429 still waits it out


def test_client_uses_the_shared_clock_and_records_a_429(tmp_path, monkeypatch):
    import oai_repo as O

    monkeypatch.setattr(HT, 'state_path', lambda: tmp_path / 'ht.json')
    slept = []

    class R:
        def __init__(self, code):
            self.status_code, self.headers, self.content = code, {}, b'ok'

    class S:
        headers = {}
        calls = 0

        def get(self, url, params=None, timeout=None):
            S.calls += 1
            return R(429 if S.calls == 1 else 200)

    cl = O.Client(3.0, session=S(), sleep=slept.append, low_priority=True)
    assert cl.get('https://web.archive.org/web/1/x').status_code == 200
    assert S.calls == 2 and any(w >= 299 for w in slept)       # the 429 started a 300 s cooldown that this client then waited out
    assert HT.cooldown_left('web.archive.org') >= 0


def test_wayback_client_takes_its_slot_from_the_shared_clock(monkeypatch):
    """listings/scripts/wb.py (every Wayback fetch of the school tools) asks host_throttle for its slot and records a 429 there, not on a stamp file of its own."""
    import wb
    calls = []
    monkeypatch.setattr(HT, 'reserve', lambda host, delay, **k: calls.append((host, delay)) or 0.0)
    monkeypatch.setattr(HT, 'cooldown_left', lambda host, **k: 0.0)
    wb._throttle()
    assert calls == [('web.archive.org', wb.MIN_GAP)]


def test_a_429_burst_counts_once(tmp_path):
    """Slots reserved before a 429 fire into the cooldown and draw more 429s seconds later: those are the same event and must not double the
    cooldown (2026-11-05: three or four 429s 5 s apart had escalated the shared cooldown to the 1-hour cap)."""
    path = tmp_path / 'ht.json'
    first = HT.record_429('web.archive.org', now=1000.0, path=path)
    again = [HT.record_429('web.archive.org', now=1000.0 + 5 * i, path=path) for i in (1, 2, 3)]
    assert first == 300.0 and all(a <= 300.0 for a in again)
    assert HT.cooldown_left('web.archive.org', now=1100.0, path=path) == 200.0
    later = HT.record_429('web.archive.org', now=1000.0 + 1800, path=path)   # a new event after the cooldown: doubles once
    assert later == 600.0


def test_wait_slot_rechecks_the_cooldown_after_the_slot(tmp_path):
    """A client that reserved its slot before another client's 429 must not fire into the cooldown: wait_slot waits it out and reserves again."""
    path = tmp_path / 'ht.json'
    slept = []
    def sleep(s):
        slept.append(s)
        if len(slept) == 1:            # while this client waits for its slot, another client records a 429
            HT.record_429('web.archive.org', path=path)
    HT.reserve('web.archive.org', 8.0, path=path)          # someone holds the current slot, so this client waits
    waited = HT.wait_slot('web.archive.org', 8.0, sleep=sleep, path=path)
    assert any(s >= 290 for s in slept) and waited >= 290   # waited out the cooldown instead of requesting into it


def test_wait_slot_raises_on_a_long_cooldown(tmp_path):
    path = tmp_path / 'ht.json'
    st = {'web.archive.org': {'until': __import__('time').time() + 3600, 'next': 0, 'n429': []}}
    path.write_text(__import__('json').dumps(st))
    try:
        HT.wait_slot('web.archive.org', 8.0, sleep=lambda s: None, path=path, max_cooldown=900)
    except RuntimeError as e:
        assert 'cooling down' in str(e)
    else:
        raise AssertionError('expected RuntimeError')
