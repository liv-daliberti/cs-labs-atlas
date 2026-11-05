"""ROADMAP #51: a trickled re-pull of 2016-2024 OpenAlex works for all 9 schools (owner 2026-11-05: backlog, never delay a release).

The key has no updated-since filter, so a re-pull is a full pull of each (school, year) under the sweep's own filter, ~5,000 credits for
81 chunks. This driver spends at most DAILY_CAP credits per UTC day on it (the shared key is 10k a day; the other agents keep the rest), one
(school, year) chunk at a time, 2024 back to 2016, and resubmits itself with --begin at the next UTC day until all chunks are done.
It reuses tools/oa_refresh_works.py (fetch + merge, same page layout, backups of every replaced row, datasets skipped, ids no longer
credited stay) and tools/oa_api.py (the only client: key redacted everywhere, ledger line per request, hard cap and floor).

  plan   [--json]                       the chunk list with credit estimates and the days to finish (reads sweep metadata only)
  run    [--cap N] [--floor N] ...      the daily loop (what tools/oa_repull_trickle.slurm runs)
  run --dry-run SCHOOL YEAR             fetch one chunk into scratch (credits, capped) and print the merge report; no store is written
  status                                rewrite STATUS.md from progress.jsonl

Store-write rules: no store is written while a `cs-release` job of this user is queued or running (checked before each chunk and again
immediately before the merge writes; a deferral resubmits the job behind that release with --dependency=afterany). The refresh used no
store lock, so the one lock here (an flock in the state dir) only keeps two trickle jobs from running together.
Every (school, year) chunk has its own fetch tag `repull<year>`; fetch is resumable by cursor, so a chunk cut by the cap resumes next day.
State: <SCRATCH>/oa-repull-trickle/{progress.jsonl, STATUS.md, .lock}; stages and backups: <SCRATCH>/oa-refresh-repull<year>/.
Tests: tests/test_oa_repull_trickle.py.
"""
import argparse
import datetime as dt
import fcntl
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import atlas_paths as P  # noqa: E402
import oa_api  # noqa: E402
import oa_refresh_works as R  # noqa: E402

SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech']
YEARS = list(range(2024, 2015, -1))
DAILY_CAP = 2000          # credits per UTC day for this job
FLOOR = 3000              # stop for the day when the shared key has fewer credits left than this (the other agents' headroom)
LOOKUPS = 3000            # singleton lookups per chunk (merged-id redirects: 0 credits)
KIND = 'repull'           # ledger kind prefix: daily use is summed from raw/openalex_budget.jsonl by this prefix
RELEASE_JOB = 'cs-release'
SQUEUE_GAP = 60           # seconds between squeue calls
STATE_DIR = P.SCRATCH / 'oa-repull-trickle'
SLURM = Path(__file__).resolve().parent / 'oa_repull_trickle.slurm'
ADDWORKS = Path(__file__).resolve().parents[1] / 'fulltext-push' / 'repull-addworks.slurm'


class Deferred(RuntimeError):
    """A release build is queued or running: no store is written now."""

    def __init__(self, jobs):
        super().__init__(f'release job(s) {jobs}')
        self.jobs = jobs


# ------------------------------------------------------------------ pure helpers
def tag(year):
    return f'repull{year}'


def plan_chunks(schools=SCHOOLS, years=YEARS):
    """(school, year) in order: years newest first; within a year the school order rotates by one per year, so no school is always last."""
    out = []
    for i, y in enumerate(sorted(years, reverse=True)):
        k = i % len(schools)
        out += [(s, y) for s in schools[k:] + schools[:k]]
    return out


def read_progress(path):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass   # a torn last line never blocks the run
    return out


def done_chunks(events):
    return {(e['school'], int(e['year'])) for e in events if e.get('event') == 'chunk_done'}


def pending_chunks(chunks, events):
    d = done_chunks(events)
    return [c for c in chunks if c not in d]


def credits_today(ledger, today, prefix=KIND):
    """Credits this job's requests were charged on UTC day `today` ('YYYY-MM-DD'), from the shared ledger."""
    n = 0
    p = Path(ledger)
    if not p.exists():
        return 0
    with p.open() as f:
        for line in f:
            if today not in line or prefix not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if str(r.get('at', '')).startswith(today) and str(r.get('kind', '')).startswith(prefix):
                c = r.get('credits')
                n += int(c) if str(c).isdigit() else 0
    return n


def shared_remaining_today(ledger, today):
    """The key's remaining credits per the newest ledger line of `today` (any agent's), or None when nobody has used it today."""
    p = Path(ledger)
    if not p.exists():
        return None
    rem = None
    with p.open() as f:
        for line in f:
            if today not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if str(r.get('at', '')).startswith(today) and str(r.get('remaining', '')).isdigit():
                rem = int(r['remaining'])
    return rem


def day_allowance(cap, used, remaining, floor):
    """Credits the run may still spend today: the daily cap minus today's use, and never below the shared floor. 0 = stop for the day."""
    room = cap - used
    if remaining is not None:
        room = min(room, remaining - floor)
    return max(0, room)


def next_utc_day_begin(now=None, minute=10):
    """sbatch --begin string for 00:<minute> UTC of the next UTC day, in the cluster's local time (sbatch reads --begin as local time)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    nxt = (now + dt.timedelta(days=1)).replace(hour=0, minute=minute, second=0, microsecond=0)
    return nxt.astimezone().strftime('%Y-%m-%dT%H:%M:%S')


def utc_today(now=None):
    return (now or dt.datetime.now(dt.timezone.utc)).strftime('%Y-%m-%d')


def estimate_credits(papers, n_pi_ids):
    """A chunk's credits: one count, one request per 200 papers, the PI queries (25 ids each, about a third of the papers again)."""
    return 1 + math.ceil(papers / R.PAGE) + math.ceil(n_pi_ids / 25) + math.ceil(0.35 * papers / R.PAGE)


def days_to_finish(estimates, cap=DAILY_CAP):
    return math.ceil(sum(estimates) / cap) if estimates else 0


# ------------------------------------------------------------------ release guard
_last_squeue = [0.0]


def release_jobs(run=None, clock=time.monotonic, sleep=time.sleep):
    """Job ids of this user's queued or running `cs-release` jobs. squeue is at least SQUEUE_GAP s after the last call; a failing squeue
    counts as 'a release may be running' (never write on an unknown)."""
    wait = SQUEUE_GAP - (clock() - _last_squeue[0])
    if _last_squeue[0] and wait > 0:
        sleep(wait)
    _last_squeue[0] = clock()
    run = run or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=60))
    try:
        r = run(['squeue', '-u', os.environ.get('USER', ''), '-n', RELEASE_JOB, '-h', '-o', '%i'])
    except Exception as e:  # noqa: BLE001
        raise Deferred([f'squeue-failed:{type(e).__name__}'])
    if r.returncode != 0:
        raise Deferred([f'squeue-rc{r.returncode}'])
    return [x for x in r.stdout.split() if x]


def guard_no_release(run=None, **kw):
    jobs = release_jobs(run, **kw)
    if jobs:
        raise Deferred(jobs)


# ------------------------------------------------------------------ submitting
def sbatch_argv(script, *, begin=None, after=None, export=None, extra=(), singleton=False):
    argv = ['sbatch']
    if begin:
        argv.append(f'--begin={begin}')
    deps = (['afterany:' + ':'.join(str(a) for a in after)] if after else []) + (['singleton'] if singleton else [])
    if deps:
        argv.append('--dependency=' + ','.join(deps))
    argv += ['--exclude=node302', *extra]
    if export:
        argv.append('--export=ALL,' + ','.join(f'{k}={v}' for k, v in export.items()))
    argv.append(str(script))
    return argv


def submit(argv, cwd, run=None, retries=6):
    """sbatch --test-only first; a plan that preempts a running job ('Preempts:') is never submitted: push --begin two hours and test again."""
    run = run or (lambda cmd, cwd: subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120))
    argv = list(argv)
    for k in range(retries):
        t = run([argv[0], '--test-only', *argv[1:]], cwd)
        out = (t.stdout or '') + (t.stderr or '')
        if t.returncode == 0 and 'Preempts:' not in out:
            r = run(argv, cwd)
            if r.returncode != 0:
                raise RuntimeError(f'sbatch failed: {oa_api.redact(r.stderr.strip()[:200])}')
            return r.stdout.strip().split()[-1]
        later = (dt.datetime.now() + dt.timedelta(hours=2 * (k + 1))).strftime('%Y-%m-%dT%H:%M:%S')
        argv = [a for a in argv if not a.startswith('--begin=')]
        argv.insert(1, f'--begin={later}')
    raise RuntimeError('sbatch: no submittable plan (Preempts: or errors)')


# ------------------------------------------------------------------ progress and status
class State:
    def __init__(self, root=STATE_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.progress = self.root / 'progress.jsonl'

    def log(self, event, **kw):
        rec = dict(at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), event=event, job=os.environ.get('SLURM_JOB_ID'), **kw)
        with self.progress.open('a') as f:
            f.write(oa_api.redact(json.dumps(rec, default=str)) + '\n')

    def events(self):
        return read_progress(self.progress)

    def write_status(self, chunks, ledger=oa_api.LEDGER):
        ev = self.events()
        done = {(e['school'], int(e['year'])): e for e in ev if e.get('event') == 'chunk_done'}
        today = utc_today()
        per_day = {}
        for e in ev:
            if e.get('event') == 'chunk_done':
                per_day[e['at'][:10]] = per_day.get(e['at'][:10], 0) + (e.get('credits_chunk') or 0)
        tot = lambda k: sum((e.get(k) or 0) for e in done.values())  # noqa: E731
        last = [e for e in ev if e.get('event') in ('chunk_done', 'chunk_partial', 'deferred', 'day_end', 'stalled', 'dry_run', 'all_done')][-8:]
        L = ['# OpenAlex 2016-2024 trickled re-pull (ROADMAP #51)', '',
             f'Updated {dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}. Chunks done: **{len(done)} / {len(chunks)}**. '
             f'Credits today (UTC {today}): {credits_today(ledger, today)} of {DAILY_CAP}.', '',
             f'Totals so far: new works {tot("new")}, merged ids {tot("merged_ids")}, PI-credited new works {tot("new_pi_credited")}, '
             f'pi-works new rows {tot("pi_new")}, credits {tot("credits_chunk")}.', '',
             '| year | ' + ' | '.join(SCHOOLS) + ' |', '|---|' + '---|' * len(SCHOOLS)]
        for y in YEARS:
            L.append(f'| {y} | ' + ' | '.join(('done' if (s, y) in done else '.') for s in SCHOOLS) + ' |')
        L += ['', '| school | chunks | works before | works after | new | merged ids | PI-credited new |', '|---|---|---|---|---|---|---|']
        for s in SCHOOLS:
            d = [e for (sc, _), e in done.items() if sc == s]
            L.append(f'| {s} | {len(d)} | {sum(e.get("ours_before") or 0 for e in d)} | {sum(e.get("ours_after") or 0 for e in d)} | '
                     f'{sum(e.get("new") or 0 for e in d)} | {sum(e.get("merged_ids") or 0 for e in d)} | {sum(e.get("new_pi_credited") or 0 for e in d)} |')
        L += ['', 'Credits by UTC day (chunks completed that day): ' + (', '.join(f'{d} {c}' for d, c in sorted(per_day.items())) or 'none yet'), '',
              'Recent events:'] + [f'- {e["at"]} {e["event"]} ' + ' '.join(f'{k}={v}' for k, v in e.items() if k in ('school', 'year', 'reason', 'jobs', 'next', 'credits_today', 'new', 'remaining')) for e in last]
        (self.root / 'STATUS.md').write_text('\n'.join(L) + '\n')


# ------------------------------------------------------------------ one chunk
def chunk_stage_has_stale_backup(school, year):
    """A backup file with this chunk's sweep rows but no `refreshes` row in the sweep = a run that died before its single sweep commit:
    nothing was written, so the stale backup is removed and the chunk retried. A refreshes row with no chunk_done = a half-applied merge:
    refuse (the operator checks the backup)."""
    bk = R.stage_dir(tag(year)) / f'backup-{school}.sqlite'
    if not bk.exists():
        return False
    sc = sqlite3.connect(f'file:{P.data_w("openalex-sweep.sqlite", school)}?mode=ro', uri=True, timeout=120)
    try:
        has = sc.execute("select count(*) from sqlite_master where name='refreshes'").fetchone()[0] and \
            sc.execute('select count(*) from refreshes where tag=?', (tag(year),)).fetchone()[0]
    finally:
        sc.close()
    if has:
        raise RuntimeError(f'{school} {year}: merge was applied to the sweep but the chunk is not recorded; check {bk} before any retry')
    bk.unlink()
    return True


def run_chunk(school, year, cl, lookup_cl, state, guard, apply=True, lookups=LOOKUPS):
    """fetch (scratch, credits) then merge (stores). Returns the progress record. `Spent` propagates (the chunk resumes next time)."""
    t0, c0 = time.time(), cl.used
    R.fetch(school, [year], cl, tag(year), pi=True)
    if apply:
        chunk_stage_has_stale_backup(school, year)
    rep = R.merge(school, [year], tag(year), apply=apply, cl=lookup_cl, lookups=lookups, guard=guard if apply else None)
    y = rep['years'].get(str(year))
    if y is None:
        raise RuntimeError(f'{school} {year}: fetch left no finished year to merge')
    return dict(school=school, year=year, tag=tag(year), ours_before=y['ours_before'], ours_after=y['ours_after'], papers_before=y['papers_before'],
                papers_after=y['papers_after'], api_all=y['api_all'], api_papers=y['api_papers'], new=y['new'], changed=y['changed'],
                dropped=y['dropped'], merged_ids=y['merged_ids'], not_returned=y['not_returned_reasons'], new_pi_credited=y['new_pi_credited'],
                pi_fetched=rep['pi']['fetched'], pi_new=rep['pi']['new'], pi_stale_replaced=rep['pi']['stale_ids_replaced'],
                credits_chunk=cl.used - c0, seconds=round(time.time() - t0), applied=bool(apply))


# ------------------------------------------------------------------ estimates
def sweep_papers(school, year):
    p = P.data_w('openalex-sweep.sqlite', school)
    try:
        c = sqlite3.connect(f'file:{p}?mode=ro', uri=True, timeout=60)
        r = c.execute('select max(count) from pages where year=?', (year,)).fetchone()
        c.close()
        return int(r[0] or 0)
    except sqlite3.Error:
        return 0


def plan_table(chunks, done=()):
    rows = []
    ids = {}
    for s, y in chunks:
        if s not in ids:
            try:
                ids[s] = len(R.pi_author_ids(s))
            except OSError:
                ids[s] = 0
        n = sweep_papers(s, y)
        rows.append(dict(school=s, year=y, stored=n, est_credits=estimate_credits(n, ids[s]), done=(s, y) in done))
    return rows


# ------------------------------------------------------------------ the daily loop
def run_day(args, state=None, ledger=oa_api.LEDGER, resubmit=True):
    state = state or State()
    chunks = plan_chunks()
    lock = open(state.root / '.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('another trickle job holds the lock; exiting'); return 0
    today = utc_today()
    oa_api.install_excepthook()
    state.log('day_start', today=today, pending=len(pending_chunks(chunks, state.events())))
    why, jobs = 'cap', []
    n_new_by_school = {}
    try:
        guard_no_release()
        while True:
            todo = pending_chunks(chunks, state.events())
            if not todo:
                why = 'all_done'; break
            used = credits_today(ledger, today)
            allow = day_allowance(args.cap, used, shared_remaining_today(ledger, today), args.floor)
            if allow <= 0:
                why = 'cap'; break
            school, year = todo[0]
            guard_no_release()
            cl = oa_api.Client(cap=allow, kind=KIND, floor=args.floor)
            lcl = oa_api.Client(cap=50, kind=KIND, floor=args.floor)
            try:
                rec = run_chunk(school, year, cl, lcl, state, guard_no_release, apply=True)
            except oa_api.Spent as e:
                state.log('chunk_partial', school=school, year=year, reason=oa_api.redact(str(e)), credits_used=cl.used, credits_today=credits_today(ledger, today))
                why = 'cap'; break
            state.log('chunk_done', credits_today=credits_today(ledger, today), **rec)
            n_new_by_school[school] = n_new_by_school.get(school, 0) + rec['new'] + rec['new_pi_credited']
            state.write_status(chunks, ledger)
            if args.max_chunks and sum(1 for e in state.events() if e.get('event') == 'chunk_done' and e['at'][:10] == today) >= args.max_chunks:
                why = 'max_chunks'; break
    except Deferred as e:
        why, jobs = 'release', e.jobs
        state.log('deferred', reason='a release build is queued or running', jobs=jobs)
    except Exception as e:  # noqa: BLE001  (the key never reaches this text: redact; a stalled job is visible in STATUS and does not resubmit)
        state.log('stalled', reason=oa_api.redact(f'{type(e).__name__}: {e}')[:400])
        state.write_status(chunks, ledger)
        print(oa_api.redact(f'stalled: {type(e).__name__}: {e}'), file=sys.stderr)
        return 1
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
    left = len(pending_chunks(chunks, state.events()))
    nxt = None
    if resubmit and left:
        cwd = os.environ.get('CS_ATLAS_CODE', str(Path.cwd()))
        exp = {k: os.environ[k] for k in ('CS_ATLAS_SNAPSHOT_COMMIT', 'REPULL_ARGS') if os.environ.get(k)}
        if why == 'release':
            ids = [j for j in jobs if str(j).isdigit()]
            soon = None if ids else (dt.datetime.now() + dt.timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%S')
            nxt = submit(sbatch_argv(SLURM, after=ids or None, begin=soon, export=exp), cwd)
        else:
            nxt = submit(sbatch_argv(SLURM, begin=next_utc_day_begin(), export=exp), cwd)
    if n_new_by_school and resubmit:
        schools = '+'.join(sorted(n_new_by_school))
        try:
            guard_jobs = release_jobs()
        except Deferred as e:
            guard_jobs = [j for j in e.jobs if str(j).isdigit()]
        exp = {'SCHOOLS': schools, 'DAY': today}
        if os.environ.get('CS_ATLAS_SNAPSHOT_COMMIT'):
            exp['CS_ATLAS_SNAPSHOT_COMMIT'] = os.environ['CS_ATLAS_SNAPSHOT_COMMIT']
        aj = submit(sbatch_argv(ADDWORKS, after=guard_jobs or None, export=exp, singleton=True),
                    os.environ.get('CS_ATLAS_CODE', str(Path.cwd())))
        state.log('addworks_queued', schools=schools, addworks_job=aj)
    state.log('day_end' if left else 'all_done', reason=why, left=left, next=nxt, credits_today=credits_today(ledger, today))
    state.write_status(chunks, ledger)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan'); p.add_argument('--json', action='store_true')
    r = sub.add_parser('run')
    r.add_argument('--cap', type=int, default=DAILY_CAP); r.add_argument('--floor', type=int, default=FLOOR)
    r.add_argument('--max-chunks', type=int, default=0, help='stop after this many chunks today (0 = until the cap)')
    r.add_argument('--no-resubmit', action='store_true')
    r.add_argument('--dry-run', nargs=2, metavar=('SCHOOL', 'YEAR'), help='fetch one chunk to scratch, print the merge report, write no store')
    sub.add_parser('status')
    a = ap.parse_args(argv)
    st = State()
    chunks = plan_chunks()
    if a.cmd == 'plan':
        rows = plan_table(chunks, done_chunks(st.events()))
        left = [x['est_credits'] for x in rows if not x['done']]
        out = dict(chunks=len(rows), pending=len(left), est_credits=sum(left), daily_cap=DAILY_CAP, est_days=days_to_finish(left), rows=rows)
        if a.json:
            print(json.dumps(out))
        else:
            for x in rows:
                print(f'{x["year"]} {x["school"]:10} stored {x["stored"]:6} est {x["est_credits"]:4} {"done" if x["done"] else ""}')
            print(f'{out["pending"]} chunks, ~{out["est_credits"]} credits, ~{out["est_days"]} UTC days at {DAILY_CAP}/day')
        return 0
    if a.cmd == 'status':
        st.write_status(chunks); print(st.root / 'STATUS.md'); return 0
    if a.dry_run:
        school, year = a.dry_run[0], int(a.dry_run[1])
        today = utc_today()
        allow = day_allowance(a.cap, credits_today(oa_api.LEDGER, today), shared_remaining_today(oa_api.LEDGER, today), a.floor)
        oa_api.install_excepthook()
        cl = oa_api.Client(cap=min(allow, 300), kind=KIND, floor=a.floor)
        R.fetch(school, [year], cl, tag(year), pi=True)
        rep = R.merge(school, [year], tag(year), apply=False, cl=None, lookups=0)
        st.log('dry_run', school=school, year=year, credits_chunk=cl.used, report=rep)
        print(json.dumps(rep, indent=1))
        return 0
    return run_day(a, st, resubmit=not a.no_resubmit)


if __name__ == '__main__':
    sys.exit(main())
