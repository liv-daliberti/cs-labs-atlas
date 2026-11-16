"""wayback_rotate: one unheld loop at a time, turns by Wayback-only queue size, re-hold on every end, a clean stop re-holds the holder."""
import json
import sqlite3
from types import SimpleNamespace

import pytest
import wayback_rotate as W


class Env:
    """A fake project: stores with loop-state, a clock, a throttle file and recording cancel/submit."""

    def __init__(self, tmp_path, queues):
        self.t = 1_800_000_000.0
        self.tmp = tmp_path
        self.queues = dict(queues)
        self.live_jobs = set()
        self.cancelled, self.submitted, self.log = [], [], []
        self.th = {}
        self.foreign_reason = None
        c = W.Ctx.__new__(W.Ctx)
        c.now = lambda: self.t
        c.logs, c.raw, c.stores = tmp_path / 'logs', tmp_path / 'raw', tmp_path / 'stores'
        for d in (c.logs, c.raw, c.stores):
            d.mkdir()
        c.state_path, c.out_path = c.logs / 'state.json', c.logs / 'rot.jsonl'
        c.stop = {'flag': None}
        c.free_gb = lambda: 500
        c.live = lambda: set(self.live_jobs)
        c.foreign = lambda: self.foreign_reason
        c.throttle = lambda: self.th
        c.queue = lambda s: self.queues[s]
        c.stats = lambda school, since_id, start, end: dict(attempts=5, wayback_successes=2, paused_429=1, throttle_429=1)
        c.cancel = lambda jobs: self.cancelled.append(sorted(jobs)) or self.live_jobs.difference_update(jobs)
        c.submit = self.submit
        c.log = lambda **kw: self.log.append(kw)
        self.c = c
        self.n = 100
        for s in queues:
            self.add_loop(s, hold=True)

    def add_loop(self, school, hold):
        d = self.c.stores / school
        d.mkdir(exist_ok=True)
        (d / 'catalog.sqlite').write_text('')
        (d / '.copy-quality-warm.json').write_text('{}')
        self.n += 1
        self.start(school, hold, str(self.n))

    def start(self, school, hold, job):
        (self.c.stores / school / 'loop-state.json').write_text(json.dumps(dict(slurm_job=job, wayback_hold=hold)))
        self.live_jobs.add(job)

    def submit(self, school, hold):
        self.n += 1
        self.submitted.append((school, hold, str(self.n)))
        self.new = (school, hold, str(self.n))
        return str(self.n)

    def run_started(self):
        """The submitted loops start: loop-state rewritten with the env they were submitted with."""
        for school, hold, job in self.submitted:
            self.start(school, hold, job)
        self.submitted.clear()

    def tick(self, adv=60, **kw):
        self.t += adv
        st = self.c.load()
        msg = W.tick(self.c, st, **kw)
        self.c.save(st)
        return msg, st

    def unheld(self):
        return W.unheld(self.c, self.live_jobs)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(W, 'TURN_S', 600)
    monkeypatch.setattr(W, 'MIN_QUEUE', 10)
    return Env(tmp_path, dict(gatech=900, mit=300, epfl=50, tiny=3))


def test_first_grant_is_the_largest_queue_and_only_that_school(env):
    msg, st = env.tick()
    assert msg == 'granted gatech' and st['holder'] == 'gatech'
    assert env.submitted == [('gatech', False, env.submitted[0][2])]
    assert env.cancelled == [['101']]                       # its held job was cancelled first
    env.run_started()
    assert env.unheld() == {'gatech'}
    assert 'tiny' not in [s for _, s in W.eligible(env.c, st, env.live_jobs)]   # under MIN_QUEUE: not eligible


def test_turn_counts_active_time_and_hands_over_with_rehold(env):
    env.tick(); env.run_started()
    env.tick()                                              # confirms the loop is running unheld
    for _ in range(8):                                      # 9 min active
        msg, st = env.tick()
        assert st['holder'] == 'gatech'
    env.th = dict(until=env.t + 10_000)                     # a 429 cooldown: the clock stops and no handover happens
    for _ in range(30):
        msg, st = env.tick()
    assert st['holder'] == 'gatech' and 'cooling' in msg
    env.th = {}
    env.submitted.clear(); env.cancelled.clear()
    for _ in range(3):
        msg, st = env.tick()
        if st['holder'] is None:
            break
    assert st['holder'] is None and st['settling']
    assert env.cancelled                                    # gatech's unheld job cancelled
    assert env.submitted[0][:2] == ('gatech', True)         # re-held in the same tick
    rec = json.loads(env.c.out_path.read_text().splitlines()[-1])
    assert rec['school'] == 'gatech' and rec['attempts'] == 5 and rec['wayback_successes'] == 2 and rec['throttle_429'] == 1 and rec['reason'] == 'turn over'
    assert env.unheld() == set()                            # nobody unheld during the handover
    env.run_started()
    msg, st = env.tick()
    assert msg == 'granted mit' and st['holder'] == 'mit'   # next in queue order
    env.run_started()
    assert env.unheld() == {'mit'}


def test_second_grant_waits_for_the_old_unheld_job_to_end(env):
    env.tick(); env.run_started(); env.tick()
    env.t += 700
    st = env.c.load(); st['turn']['active_s'] = 601; env.c.save(st)
    env.tick()
    st = env.c.load()
    st['settling']['jobs'] = ['9999']                        # still in squeue
    env.live_jobs.add('9999'); env.c.save(st)
    msg, _ = env.tick()
    assert 'waiting' in msg and env.c.load()['holder'] is None


def test_skips_when_archive_paused_recently_used_or_foreign(env):
    env.th = dict(until=env.t + 5000)
    assert 'cooling' in env.tick()[0]
    env.th = dict(last_hi=env.t + 59)
    assert 'used within' in env.tick()[0]
    env.th = {}
    env.foreign_reason = 'live task claim T9 names wayback'
    assert env.tick()[0].startswith('skipped: live task claim')
    assert env.submitted == [] and env.c.load()['holder'] is None


def test_stray_unheld_loop_blocks_grants(env):
    env.start('mit', False, '555')
    msg, _ = env.tick()
    assert 'unmanaged unheld loop mit' in msg and env.submitted == []


def test_adopt_makes_an_existing_unheld_loop_the_first_turn(env):
    env.start('gatech', False, '777')
    msg, st = env.tick(adopt='gatech')
    assert st['holder'] == 'gatech' and st['turn']['adopted'] and env.submitted == [] and env.cancelled == []
    msg, st = env.tick(adopt='gatech')
    assert st['turn']['started_at'] and st['holder'] == 'gatech'


def test_foreign_fetcher_mid_turn_yields_the_holder(env):
    env.tick(); env.run_started(); env.tick()
    env.foreign_reason = 'running job 5 wayback-capture'
    env.submitted.clear()
    msg, st = env.tick()
    assert msg == 'yielded' and st['holder'] is None and env.submitted[0][:2] == ('gatech', True)
    assert 'yielded' in json.loads(env.c.out_path.read_text().splitlines()[-1])['reason']


def test_round_robin_and_renewal_when_alone(env):
    env.queues = dict(gatech=900, mit=300, epfl=50, tiny=3)
    st = env.c.load()
    order = []
    for _ in range(3):
        n, s = W.pick(env.c, st, env.live_jobs)
        order.append(s); st['served'].append(s)
    assert order == ['gatech', 'mit', 'epfl']
    assert W.pick(env.c, st, env.live_jobs)[1] == 'gatech' and st['round'] == 2 and st['served'] == []   # new round, largest first


def test_never_two_unheld_loops_across_a_whole_rotation(env):
    seen = []
    for i in range(80):
        env.tick(adv=60)
        env.run_started()
        seen.append(len(env.unheld()))
    assert max(seen) <= 1 and 1 in seen
    served = [json.loads(x)['school'] for x in env.c.out_path.read_text().splitlines()]
    assert served[:3] == ['gatech', 'mit', 'epfl']


def test_clean_stop_reholds_the_holder(env):
    env.tick(); env.run_started(); env.tick()
    env.submitted.clear(); env.cancelled.clear()
    st = env.c.load()
    W.stop_clean(env.c, st)
    assert env.submitted[0][:2] == ('gatech', True) and env.cancelled
    st = env.c.load()
    assert st['holder'] is None and json.loads(env.c.out_path.read_text().splitlines()[-1])['reason'] == 'rotator stopped'


def test_marker_and_disk_floor_do_nothing(env):
    (env.c.raw / 'downloads_stopped_by_disk_guard').write_text('x')
    assert 'disk guard' in env.tick()[0] and env.submitted == []
    (env.c.raw / 'downloads_stopped_by_disk_guard').unlink()
    env.c.free_gb = lambda: 50
    assert 'floor' in env.tick()[0] and env.submitted == []


def test_failed_submit_is_retried_next_tick(env):
    calls = []
    env.c.submit = lambda s, h: calls.append((s, h)) or (None if len(calls) == 1 else '900')
    env.tick()
    assert env.c.load()['pending'] == [dict(school='gatech', hold=False)]
    env.tick()
    assert env.c.load()['pending'] == [] and len(calls) == 2


def test_queue_sql_counts_archive_only_works_waiting_on_the_archive(tmp_path):
    db = sqlite3.connect(tmp_path / 'c.sqlite')
    db.executescript("""CREATE TABLE works (id TEXT PRIMARY KEY, status TEXT); CREATE TABLE candidates (work_id TEXT, url TEXT);
      CREATE TABLE attempts (id INTEGER PRIMARY KEY, work_id TEXT, detail TEXT);""")
    rows = [('a', 'needs_access_review', ['https://web.archive.org/web/1/x'], 'source_paused: HTTP 429'),    # counts
            ('b', 'queued', ['https://web.archive.org/web/1/y'], None),                                      # counts: never tried
            ('c', 'needs_access_review', ['https://web.archive.org/web/1/z'], '404 not found'),             # a real failure: not waiting
            ('d', 'needs_access_review', ['https://web.archive.org/web/1/q', 'https://example.org/q.pdf'], 'source_paused: HTTP 429'),  # has another host
            ('e', 'downloaded', ['https://web.archive.org/web/1/w'], None)]
    for w, st, urls, det in rows:
        db.execute('INSERT INTO works VALUES (?, ?)', (w, st))
        for u in urls:
            db.execute('INSERT INTO candidates VALUES (?, ?)', (w, u))
        if det:
            db.execute('INSERT INTO attempts (work_id, detail) VALUES (?, ?)', (w, det))
    assert db.execute(W.QUEUE_SQL).fetchone()[0] == 2


def test_submit_passes_the_hold_in_the_environment(tmp_path, monkeypatch):
    import loop_starter as L
    monkeypatch.setenv('CS_ATLAS_TOOLS', '/snap/tools')
    seen = []

    def run(cmd, **kw):
        seen.append(kw['env'])
        return SimpleNamespace(returncode=0, stdout='Submitted batch job 9', stderr='')
    assert L.submit('mit', '', run, str(tmp_path), extra_env={'WAYBACK_HOLD': '0'}) == '9'
    assert all(e['WAYBACK_HOLD'] == '0' and 'CS_ATLAS_TOOLS' not in e for e in seen)
