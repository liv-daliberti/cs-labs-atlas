"""Rotating single Wayback fetcher for the download loops (owner decision 2026-11-16; supersedes the permanent gatech exception of 2026-11-14).

Every loop runs with WAYBACK_HOLD=1 (collector_quality.wayback_held: web.archive.org / archive.org are not asked) except ONE school, the holder of the
turn, whose loop runs with WAYBACK_HOLD=0. The turn lasts TURN_S seconds of ACTIVE time (time while web.archive.org is cooling down after a 429 does not
count), then goes to the next school. A holder is changed the only way the env of a loop can be changed: scancel its job (a deliberate stop, no
resubmit) and submit it again through loop_starter.submit with WAYBACK_HOLD in its environment; loop_job.sh carries that environment through the loop's
own 59-minute self-resubmits. Nothing else changes: the 8 s / 15 s slot, the 429 cooldowns of raw/host-throttle.json, robots.txt and the charters are the
collector's and the throttle's, not ours.

One tick every INTERVAL_S (>= 60 s), one `squeue` per tick:
  - disk guard marker or free space under MIN_FREE_GB: do nothing (the guard stops the loops; a restart would be refused anyway);
  - an unheld loop that is not ours (stray), or a live foreign Wayback fetcher (a live task claim or lease naming wayback, a running job named like
    one): the holder is re-held and no turn is granted until it is gone ("skip the turn");
  - the holder's turn is over (ACTIVE time, or its Wayback-only queue is empty): its stats are appended to logs/wayback-rotation.jsonl, it is re-held
    (scancel + held resubmit); the NEXT tick, once its unheld jobs are gone from squeue, the next school is granted (never two unheld at once);
  - no holder: not while web.archive.org is cooling down or was used by someone else within QUIET_S; the next school is the one with the largest
    Wayback-only queue among those not yet served in this round (a round ends when every eligible school had a turn), eligible = a live loop, a warm
    copy-quality cache and at least MIN_QUEUE works that wait for Wayback (all candidates on archive hosts, last attempt source_paused or none).
Kill switch: `scancel <wayback-rotator job>` (SIGTERM) re-holds the holder before the script exits and does NOT resubmit. If the job is killed hard
(node loss, SIGKILL), the holder stays unheld until `wayback_rotate.py rehold` (or the resubmitted rotator, which reads logs/wayback-rotation-state.json).
usage: wayback_rotate.py run [--adopt SCHOOL] | once | plan | status | rehold     env WAYBACK_ROTATE_TURN_S (3600), _INTERVAL_S (60), _MIN_QUEUE (5)
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402
import loop_starter as L  # noqa: E402

HOST = 'web.archive.org'
TURN_S = int(os.environ.get('WAYBACK_ROTATE_TURN_S', '3600'))
INTERVAL_S = max(60, int(os.environ.get('WAYBACK_ROTATE_INTERVAL_S', '60')))
MIN_QUEUE = int(os.environ.get('WAYBACK_ROTATE_MIN_QUEUE', '5'))
MIN_FREE_GB = int(os.environ.get('WAYBACK_ROTATE_MIN_FREE_GB', '100'))
QUIET_S = 150            # nobody else may have used web.archive.org this recently when a turn is granted (PROBE_HOLD is 120 s)
CONFIRM_S = 1800         # a granted loop must be running unheld within 30 min or the grant is withdrawn
QUEUE_CACHE_S = 600
CHECK_FAILED = 'foreign-fetcher check failed'
FOREIGN_JOB_WORDS = tuple(os.environ.get('WAYBACK_ROTATE_FOREIGN_JOBS', 'wayback listing-capture').split())
ROTATOR_JOB = 'wayback-rotator'
OWN_TITLE = 'Rotating single Wayback fetcher'
ARCHIVE = "(c.url LIKE '%://web.archive.org/%' OR c.url LIKE '%://archive.org/%' OR c.url LIKE '%.archive.org/%')"
QUEUE_SQL = f"""SELECT COUNT(*) FROM (SELECT c.work_id w FROM candidates c JOIN works x ON x.id = c.work_id
  WHERE x.status NOT IN ('downloaded', 'fulltext_xml') GROUP BY c.work_id HAVING SUM(CASE WHEN {ARCHIVE} THEN 0 ELSE 1 END) = 0) ao
  LEFT JOIN attempts a ON a.work_id = ao.w AND a.id = (SELECT MAX(id) FROM attempts b WHERE b.work_id = ao.w)
  WHERE a.id IS NULL OR a.detail LIKE 'source_paused%'"""


def iso(t):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))


class Ctx:
    """Every outside effect behind one attribute, so tests replace them."""

    def __init__(self):
        self.now = time.time
        self.logs = Path(F.P.FT_LOGS)
        self.raw = Path(F.P.FT_RAW)
        self.stores = Path(F.FT)
        self.state_path = self.logs / 'wayback-rotation-state.json'
        self.out_path = self.logs / 'wayback-rotation.jsonl'
        self.run = subprocess.run
        self.stop = {'flag': None}
        self.free_gb = lambda: shutil.disk_usage(str(F.P.ROOT)).free // 2**30
        self.live = self._live
        self.foreign = self._foreign
        self.throttle = self._throttle
        self.queue = self._queue
        self.stats = self._stats
        self.cancel = self._cancel
        self.submit = self._submit
        self.log = lambda **kw: print(json.dumps(dict(at=F.now(), **kw)), flush=True)

    # ---- effects ----
    def _live(self):
        return L.live_jobs(self.run)

    def _cancel(self, jobs):
        if jobs:
            self.run(['scancel'] + sorted(jobs), capture_output=True, text=True, timeout=120)

    def _submit(self, school, hold):
        return L.submit(school, os.environ.get('LOOP_STARTER_CHANNELS', ''), self.run, extra_env={'WAYBACK_HOLD': '1' if hold else '0', 'LOOP_LOCK_WAIT_S': '600'})

    def _throttle(self):
        try:
            return json.loads(Path(F.P.FT_RAW, 'host-throttle.json').read_text()).get(HOST) or {}
        except (OSError, ValueError):
            return None   # unreadable or mid-write: treated as paused

    def _foreign(self):
        """Why another Wayback fetcher may be live (a reason string), else None. Live task claims and leases naming wayback; running jobs named like one."""
        t = self.now()
        try:
            for line in Path(F.P.LEASES, 'queue.jsonl').read_text().splitlines():
                d = json.loads(line) if line.strip() else {}
                if d.get('status') in ('claimed', 'running') and OWN_TITLE not in d.get('title', '') and 'wayback' in (d.get('title', '') + ' ' + ' '.join(d.get('scope') or [])).lower():
                    hb = time.mktime(time.strptime(d['heartbeat'], '%Y-%m-%dT%H:%M:%SZ')) - time.timezone
                    if hb + d.get('ttl', 1800) > t:
                        return f"live task claim {d['id']} names wayback ({d.get('session')})"
            for p in Path(F.P.LEASES).glob('*wayback*.json'):
                d = json.loads(p.read_text())
                if time.mktime(time.strptime(d['renewed_at'], '%Y-%m-%dT%H:%M:%SZ')) - time.timezone + d.get('ttl', 1800) > t:
                    return f'live lease {p.name}'
            r = self.run(['squeue', '-h', '-u', os.environ.get('USER', ''), '-t', 'RUNNING', '-o', '%i %j'], capture_output=True, text=True, timeout=60)
            for row in r.stdout.splitlines():
                if row.split(' ', 1)[-1].strip() != ROTATOR_JOB and any(w in row.lower() for w in FOREIGN_JOB_WORDS):   # not ourselves
                    return f'running job {row}'
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
            return f'{CHECK_FAILED} ({e}); not granting'
        return None

    def _queue(self, school):
        import sqlite3
        db = sqlite3.connect(f'file:{self.stores / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=60)
        try:
            return db.execute(QUEUE_SQL).fetchone()[0]
        finally:
            db.close()

    def _stats(self, school, since_id, start, end):
        import sqlite3
        out = dict(attempts=None, wayback_successes=None, paused_429=None, throttle_429=0)
        try:
            db = sqlite3.connect(f'file:{self.stores / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=60)
            rows = db.execute("SELECT status, detail FROM attempts WHERE id > ? AND observed_at <= ? AND (url LIKE '%://web.archive.org/%' OR url LIKE '%://archive.org/%' OR url LIKE '%.archive.org/%')",
                              (since_id or 0, iso(end + 1)[:-1])).fetchall()
            db.close()
            out.update(attempts=len(rows), wayback_successes=sum(1 for s, _ in rows if s in F.LOCAL), paused_429=sum(1 for _, d in rows if '429' in (d or '')))
        except Exception as e:   # the record must still be written
            out['stats_error'] = str(e)[:120]
        try:
            p = self.raw / 'host-throttle-429.jsonl'
            with open(p, 'rb') as f:
                f.seek(max(0, p.stat().st_size - 400_000))
                tail = f.read().decode('utf-8', 'replace').splitlines()
            for line in tail:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get('host') == HOST and start <= d.get('at', 0) <= end and f'/stores/{school}' in (d.get('cmd') or '') and not d.get('burst'):
                    out['throttle_429'] += 1
        except OSError:
            pass
        return out

    # ---- state ----
    def load(self):
        try:
            return json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            return dict(holder=None, turn=None, served=[], round=1, settling=None, pending=[], queues={}, last_tick=None)

    def save(self, st):
        tmp = self.state_path.with_name(f'.{self.state_path.name}.{os.getpid()}')
        tmp.write_text(json.dumps(st, indent=1))
        os.replace(tmp, self.state_path)

    def record(self, **kw):
        with open(self.out_path, 'a') as f:
            f.write(json.dumps(kw) + '\n')


def jread(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def loop_jobs(c, school, live):
    """Live job ids of the school's loop: the one in loop-state.json and the self-resubmission the sentinel recorded (it may still be pending)."""
    ids = {str(jread(c.stores / school / 'loop-state.json').get('slurm_job') or '')}
    try:
        ids.add((c.logs / f'.resubmitted-school-collector.slurm-{school}-none').read_text().strip())
    except OSError:
        pass
    return {i for i in ids if i and i in live}


def schools(c):
    return sorted(p.name for p in c.stores.iterdir() if (p / 'loop-state.json').exists() and (p / 'catalog.sqlite').exists())


def unheld(c, live):
    return {s for s in schools(c) if jread(c.stores / s / 'loop-state.json').get('wayback_hold') is False and loop_jobs(c, s, live)}


def _max_attempt(c, school):
    import sqlite3
    try:
        db = sqlite3.connect(f'file:{c.stores / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=60)
        v = db.execute('SELECT MAX(id) FROM attempts').fetchone()[0] or 0
        db.close()
        return v
    except sqlite3.Error:
        return None


def queue_of(c, st, school, fresh=False):
    q = st['queues'].get(school)
    if q and not fresh and c.now() - q[1] < QUEUE_CACHE_S:
        return q[0]
    try:
        n = c.queue(school)
    except Exception as e:
        c.log(queue_failed=school, error=str(e)[:120])
        return None
    st['queues'][school] = [n, c.now()]
    return n


def eligible(c, st, live):
    """(queue, school) for every school a turn may go to, largest queue first."""
    out = []
    for s in schools(c):
        if c.stop['flag']:
            break
        if not loop_jobs(c, s, live) or not (c.stores / s / '.copy-quality-warm.json').exists():
            continue
        n = queue_of(c, st, s)
        if n is not None and n >= MIN_QUEUE:
            out.append((n, s))
    return sorted(out, key=lambda x: (-x[0], x[1]))


def pick(c, st, live, exclude=()):
    el = [x for x in eligible(c, st, live) if x[1] not in exclude]
    todo = [x for x in el if x[1] not in st['served']]
    if not todo and el:
        st['served'], st['round'] = [], st['round'] + 1
        todo = el
    return todo[0] if todo else None


def restart(c, st, school, hold, live):
    """scancel the school's loop jobs and submit it again with WAYBACK_HOLD=<hold>. A failed submit stays pending and is retried every tick."""
    jobs = loop_jobs(c, school, live)
    c.cancel(jobs)
    st['pending'] = [p for p in st['pending'] if p['school'] != school] + [dict(school=school, hold=hold)]
    c.log(restart=school, hold=hold, cancelled=sorted(jobs))
    return sorted(jobs)


def run_pending(c, st):
    keep = []
    for p in st['pending']:
        if (c.raw / L.MARKER).exists():
            keep.append(p)
            continue
        job = c.submit(p['school'], p['hold'])
        c.log(submitted=p['school'], hold=p['hold'], job=job)
        if not job:
            keep.append(p)
        elif not p['hold'] and st.get('turn') and st['turn']['school'] == p['school']:
            st['turn']['job'] = job
    st['pending'] = keep


def end_turn(c, st, reason, live, rehold=True):
    t = st['turn']
    now = c.now()
    if t:
        rec = dict(school=t['school'], start=iso(t['started_at'] or t['granted_at']), end=iso(now), active_s=int(t['active_s']), reason=reason, job=t.get('job'),
                   queue_at_start=t.get('queue_at_start'), confirmed=bool(t['started_at']))
        rec.update(c.stats(t['school'], t.get('max_attempt_id'), t['started_at'] or t['granted_at'], now))
        c.record(**rec)
        c.log(turn_ended=rec)
        st['served'] = sorted(set(st['served']) | {t['school']})
    if t and rehold:
        old = restart(c, st, t['school'], True, live)
        st['settling'] = dict(school=t['school'], jobs=old)
        st['holder'], st['turn'] = None, None
        run_pending(c, st)
        return
    st['holder'], st['turn'] = None, None


def grant(c, st, school, n, live):
    st['holder'] = school
    st['turn'] = dict(school=school, granted_at=c.now(), started_at=None, active_s=0.0, queue_at_start=n, max_attempt_id=None, job=None)
    restart(c, st, school, False, live)
    c.log(granted=school, wayback_only_queue=n, round=st['round'])


def tick(c, st, adopt=None):
    """One decision; returns a short string for the log. Mutates st (the caller saves it)."""
    now = c.now()
    last, st['last_tick'] = st.get('last_tick'), now
    live = c.live()
    if live is None:
        return 'squeue failed'
    if (c.raw / L.MARKER).exists() or c.free_gb() < MIN_FREE_GB:
        return 'disk guard marker or free space under the floor: nothing to do'
    run_pending(c, st)
    th = c.throttle()
    paused = th is None or th.get('until', 0) > now
    holder, turn = st['holder'], st['turn']
    others = unheld(c, live) - ({holder} if holder else set())
    if st['settling']:   # the previous holder's unheld jobs must be gone before the next grant
        if any(j in live for j in st['settling']['jobs']):
            return f"waiting for {st['settling']['school']}'s unheld jobs to end"
        st['settling'] = None
    if adopt and not st.get('adopt_done') and not holder and others == {adopt}:   # the owner's gatech exception (2026-11-14) becomes the first turn
        st['holder'], st['turn'] = adopt, dict(school=adopt, granted_at=now, started_at=now, active_s=0.0, max_attempt_id=_max_attempt(c, adopt), job=None,
                                               queue_at_start=queue_of(c, st, adopt, True), adopted=True)
        holder, turn, others, st['adopt_done'] = adopt, st['turn'], set(), True
        c.log(adopted=adopt)
    foreign = c.foreign()
    if holder:
        if foreign and foreign.startswith(CHECK_FAILED):
            foreign = None   # a failed check never costs the holder its loop; it only blocks a new grant
        if others or foreign:
            end_turn(c, st, f'yielded: {foreign or "unmanaged unheld loop " + ",".join(sorted(others))}', live)
            return 'yielded'
        if not loop_jobs(c, holder, live) and not any(p['school'] == holder for p in st['pending']):
            end_turn(c, st, 'holder loop is gone', live, rehold=False)
            return 'holder loop gone'
        if not turn['started_at']:
            ls = jread(c.stores / holder / 'loop-state.json')
            sj = str(ls.get('slurm_job'))
            if ls.get('wayback_hold') is False and sj in live and (not turn.get('job') or sj == str(turn['job'])):
                turn.update(started_at=now, max_attempt_id=_max_attempt(c, holder))
                c.log(turn_started=holder, job=ls.get('slurm_job'))
            elif now - turn['granted_at'] > CONFIRM_S:
                end_turn(c, st, 'never started unheld within 30 min', live)
                return 'grant withdrawn'
            return 'waiting for the holder loop to start'
        if not paused and last:
            turn['active_s'] += min(now - last, 2 * INTERVAL_S)
        done = None
        if turn['active_s'] >= TURN_S:
            done = 'turn over'
        elif now - turn.get('queue_checked', turn['started_at']) > 600:
            turn['queue_checked'] = now
            n = queue_of(c, st, holder, True)
            if n is not None and n < MIN_QUEUE:
                done = f'holder queue empty ({n})'
        if done and not paused:
            st['served'] = sorted(set(st['served']) | {holder})   # a round gives every school one turn before anyone gets a second
            nxt = pick(c, st, live)
            if nxt and nxt[1] == holder:   # nobody else waits: keep the loop, start a new record
                end_turn(c, st, done + ' (renewed: no other school waits)', live, rehold=False)
                st['holder'], st['turn'] = holder, dict(school=holder, granted_at=now, started_at=now, active_s=0.0, max_attempt_id=_max_attempt(c, holder), job=turn.get('job'), queue_at_start=nxt[0])
                return 'renewed'
            end_turn(c, st, done, live)
            return 'turn ended'
        return f"holder {holder}: {int(turn['active_s'])} s of {TURN_S}" + (' (archive cooling down)' if paused else '')
    if st['pending']:
        return 'restarts pending'
    if others:
        return f"unmanaged unheld loop {','.join(sorted(others))}: no turn granted"
    if foreign:
        return f'skipped: {foreign}'
    if paused:
        return 'skipped: web.archive.org is cooling down (host-throttle.json)'
    if now - th.get('last_hi', 0) < QUIET_S:
        return 'skipped: web.archive.org used within the last %d s by someone else' % QUIET_S
    nxt = pick(c, st, live)
    if not nxt:
        return 'no school has a Wayback-only queue'
    grant(c, st, nxt[1], nxt[0], live)
    run_pending(c, st)
    return f'granted {nxt[1]}'


def stop_clean(c, st):
    """Kill switch: re-hold the holder (scancel + held submit) before exiting."""
    live = c.live() or set()
    if st['holder']:
        end_turn(c, st, 'rotator stopped', live)
        run_pending(c, st)
    c.save(st)


def main(argv):
    cmd = argv[0] if argv else 'run'
    c = Ctx()
    st = c.load()
    adopt = argv[argv.index('--adopt') + 1] if '--adopt' in argv else os.environ.get('WAYBACK_ROTATE_ADOPT')
    if cmd == 'status':
        print(json.dumps(st, indent=1))
        return 0
    if cmd == 'plan':
        live = c.live() or set()
        print(json.dumps([dict(school=s, queue=n) for n, s in eligible(c, st, live)]))
        c.save(st)
        return 0
    if cmd == 'rehold':
        live = c.live() or set()
        for s in sorted(unheld(c, live) | ({st['holder']} if st['holder'] else set())):
            restart(c, st, s, True, live)
        st.update(holder=None, turn=None)
        run_pending(c, st)
        c.save(st)
        return 0
    if cmd == 'once':
        print(tick(c, st, adopt))
        c.save(st)
        return 0
    mine = os.environ.get('SLURM_JOB_ID', '')   # a second rotator would be a second turn-giver: refuse to run beside one
    r = c.run(['squeue', '-h', '-u', os.environ.get('USER', ''), '-n', ROTATOR_JOB, '-t', 'RUNNING', '-o', '%i'], capture_output=True, text=True, timeout=60)
    if mine and (set(r.stdout.split()) - {mine}):
        c.log(rotator='another wayback-rotator job is running; exiting', others=sorted(set(r.stdout.split()) - {mine}))
        return 0
    signal.signal(signal.SIGTERM, lambda *_: c.stop.update(flag='stop'))
    signal.signal(signal.SIGINT, lambda *_: c.stop.update(flag='stop'))
    signal.signal(signal.SIGUSR1, lambda *_: c.stop.update(flag='restart'))
    c.log(rotator='started', turn_s=TURN_S, interval_s=INTERVAL_S, holder=st['holder'], adopt=adopt)
    while not c.stop['flag']:
        try:
            msg = tick(c, st, adopt)
        except Exception as e:   # one bad tick must not end the rotation
            msg = f'tick failed: {e!r}'[:300]
        c.save(st)
        c.log(tick=msg, holder=st['holder'])
        end = time.monotonic() + INTERVAL_S
        while not c.stop['flag'] and time.monotonic() < end:
            time.sleep(min(5, max(0.1, end - time.monotonic())))
    if c.stop['flag'] == 'stop':
        stop_clean(c, st)
        c.log(rotator='stopped: holder re-held', holder=None)
    else:
        c.save(st)
        c.log(rotator='restarting: turn state kept', holder=st['holder'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
