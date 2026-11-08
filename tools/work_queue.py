"""One shared work queue for every session (Claude agents and Codex), 2026-11-07: a claim names a task, its scope and its holder, so a second session sees the duplicate BEFORE it starts.

  atlas task add   --title T --school S --kind K [--scope PATH ...] [--id ID] [--note N]     put a task on the queue (status open)
  atlas task list  [--status S] [--school S] [--kind K] [--mine] [--all] [--json]             open and live-claimed work; --all adds done/dropped
  atlas task claim ID [--branch B] [--ttl SECONDS] [--running] [--allow-overlap REASON]       take it; REFUSED (exit 3) with the holder when a live claim overlaps
  atlas task heartbeat ID [--running] [--branch B] [--commit C] [--job JOBID ...] [--note N]  keep the claim alive (default ttl 1800 s, like leases)
  atlas task done  ID --commit C [--note N]      atlas task block ID --note WHY      atlas task release ID [--note N]     (release: back to open)
  atlas task drop  ID --note WHY                 atlas task show ID                  atlas task import FILE.json   (add tasks whose id is absent)
  atlas task land-lock acquire|release|status|check [--ttl S] [--force]                        one session lands on main at a time

State is <ROOT>/leases/queue.jsonl (one task per line, rewritten atomically) under flock on <ROOT>/leases/.queue.lock. The land lock is an ordinary lease named `land-lock`
(tools/agent_lease.py), so `atlas lease status` shows it too.

A claim is LIVE while status is claimed|running and heartbeat + ttl is in the future; a stale claim no longer blocks and the next claimant takes the task over (the old
holder is kept in its history). Two tasks CONFLICT when (live claim, other session) they share a scope key (equal, or one is a path prefix of the other, or an fnmatch
glob matches), have the same normalised title, or have the same school AND kind. Session id: --session, else $ATLAS_SESSION, else $CLAUDE_SESSION_ID; with none of
them a command that changes state stops (a per-call pid would make every claim look foreign).
"""
import argparse, contextlib, datetime, fcntl, fnmatch, json, os, re, sys
from pathlib import Path

import agent_lease as AL  # noqa: E402
import atlas_paths as P  # noqa: E402

TTL = 1800
KINDS = ('collect', 'build', 'review', 'land', 'release', 'analysis')
STATUSES = ('open', 'claimed', 'running', 'done', 'blocked', 'dropped')
LIVE_STATUSES = ('claimed', 'running')
LAND = 'land-lock'
LAND_TTL = 3600
now, stamp, parse = AL.now, AL.stamp, AL.parse


def root_dir(root=None):
    return Path(root or P.LEASES)


def qpath(root=None):
    return root_dir(root) / 'queue.jsonl'


@contextlib.contextmanager
def locked(root=None):
    d = root_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / '.queue.lock', 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def load(root=None):
    p = qpath(root)
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def save(tasks, root=None):
    p = qpath(root)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(''.join(json.dumps(t, sort_keys=True) + '\n' for t in tasks))
    os.replace(tmp, p)


def session_id(given=None):
    s = given or os.environ.get('ATLAS_SESSION') or os.environ.get('CLAUDE_SESSION_ID')
    if not s:
        raise SystemExit('no session id: pass --session or set ATLAS_SESSION (a per-call pid would make every claim look foreign)')
    return s


def live(t, at=None):
    return t['status'] in LIVE_STATUSES and bool(t.get('heartbeat')) and parse(t['heartbeat']) + datetime.timedelta(seconds=t.get('ttl', TTL)) > (at or now())


def state(t):
    """status, or 'stale' for a claimed/running task whose heartbeat ran out."""
    return 'stale' if t['status'] in LIVE_STATUSES and not live(t) else t['status']


def norm_title(s):
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def norm_key(k):
    return os.path.normpath(k.strip()).strip('/') if k.strip() else ''


def keys_overlap(a, b):
    a, b = norm_key(a), norm_key(b)
    if not a or not b:
        return False
    if a == b or a.startswith(b + '/') or b.startswith(a + '/'):
        return True
    return fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a)


def conflicts(task, tasks, session, at=None):
    """-> [(other task, reason)] for live claims of OTHER sessions that overlap `task`."""
    out = []
    for o in tasks:
        if o['id'] == task['id'] or not live(o, at) or o.get('session') == session:
            continue
        hit = next((f'scope {a!r} overlaps {b!r}' for a in task.get('scope', []) for b in o.get('scope', []) if keys_overlap(a, b)), None)
        if not hit and norm_title(task['title']) == norm_title(o['title']):
            hit = 'same title'
        if not hit and task.get('school') and task['school'] == o.get('school') and task['kind'] == o['kind']:
            hit = f"same school and kind ({task['school']}/{task['kind']})"
        if hit:
            out.append((o, hit))
    return out


def find(tasks, tid):
    for t in tasks:
        if t['id'] == tid:
            return t
    raise SystemExit(f'no task {tid!r} (atlas task list --all)')


def note_history(t, event, session, text=''):
    t.setdefault('history', []).append(dict(at=stamp(), by=session, event=event, note=text))


def new_id(tasks):
    n = max([int(m.group(1)) for t in tasks if (m := re.fullmatch(r'T(\d+)', t['id']))] or [0]) + 1
    return f'T{n:03d}'


def make(tasks, title, school='', kind='build', scope=(), tid=None, note='', by='', **extra):
    if kind not in KINDS:
        raise SystemExit(f'kind must be one of {", ".join(KINDS)}')
    if tid and any(t['id'] == tid for t in tasks):
        raise SystemExit(f'task {tid} exists')
    t = dict(id=tid or new_id(tasks), title=title, school=school or '', kind=kind, scope=[norm_key(s) for s in scope if norm_key(s)], status='open', session='', claimed_at='',
             heartbeat='', ttl=TTL, branch='', commit='', note=note, jobs=[], created_at=stamp(), created_by=by, history=[])
    t.update(extra)
    return t


def add(title, school='', kind='build', scope=(), tid=None, note='', by='', root=None):
    with locked(root):
        tasks = load(root)
        t = make(tasks, title, school, kind, scope, tid, note, by)
        dup = [o for o in tasks if o['status'] not in ('done', 'dropped') and (norm_title(o['title']) == norm_title(title))]
        if dup:
            return False, dup[0]
        save(tasks + [t], root)
        return True, t


def claim(tid, session, branch='', ttl=TTL, running=False, allow_overlap='', root=None):
    """-> (ok, task, conflicts). A held live claim by another session, or an overlap, refuses."""
    with locked(root):
        tasks = load(root)
        t = find(tasks, tid)
        if t['status'] in ('done', 'dropped'):
            return False, t, [(t, f"task is {t['status']}")]
        if live(t) and t['session'] != session:
            return False, t, [(t, 'already claimed')]
        cs = conflicts(t, tasks, session)
        if cs and not allow_overlap:
            return False, t, cs
        if state(t) == 'stale':
            note_history(t, 'expired', t['session'], f"heartbeat {t['heartbeat']}")
        t.update(status='running' if running else 'claimed', session=session, claimed_at=t['claimed_at'] if live(t) else stamp(), heartbeat=stamp(), ttl=ttl,
                 branch=branch or t.get('branch', ''))
        note_history(t, 'claim', session, (f'allow-overlap: {allow_overlap}; ' + '; '.join(f"{o['id']} {r}" for o, r in cs)) if cs else '')
        save(tasks, root)
        return True, t, []


def _mine(t, session, force=False):
    if t.get('session') and t['session'] != session and live(t) and not force:
        raise SystemExit(f"{t['id']} is held by {t['session']} (branch {t.get('branch') or '-'}), not {session}")


def update(tid, session, status=None, branch=None, commit=None, jobs=(), note=None, running=False, event='update', root=None, require_commit=False, force=False):
    with locked(root):
        tasks = load(root)
        t = find(tasks, tid)
        _mine(t, session, force)
        if t['status'] in ('open',) and event == 'heartbeat':
            raise SystemExit(f'{tid} is not claimed: atlas task claim {tid} first')
        if require_commit and not commit:
            raise SystemExit('done needs --commit (the commit that carries the result, or the word none with a note)')
        if status:
            t['status'] = status
        if running and t['status'] == 'claimed':
            t['status'] = 'running'
        if event == 'heartbeat' and not live(t) and t.get('session') and t['session'] != session:
            raise SystemExit('claim lost')
        if event == 'heartbeat' or status in (None, 'claimed', 'running'):
            t['heartbeat'] = stamp()
            t['session'] = session
        if status == 'open':
            t.update(session='', claimed_at='', heartbeat='')
        for k, v in (('branch', branch), ('commit', commit), ('note', note)):
            if v is not None:
                t[k] = v
        t['jobs'] = sorted(set(t.get('jobs', [])) | set(jobs))
        note_history(t, event, session, note or '')
        save(tasks, root)
        return t


# ---- land lock ----------------------------------------------------------------------------------------------------------------------------------------

def land_check(session=None, root=None):
    """-> (state, lease): 'ours' | 'free' | 'held' (live, someone else's)."""
    cur = AL.read(LAND, root_dir(root))
    if not AL.live(cur):
        return 'free', cur
    return ('ours' if session and cur['session'] == session else 'held'), cur


# ---- CLI ----------------------------------------------------------------------------------------------------------------------------------------------

def fmt(t):
    holder = f"{t['session']} [{t.get('branch') or '-'}] hb {age(t['heartbeat'])}" if t.get('session') else '-'
    return f"{t['id']:5} {state(t):8} {t['kind']:8} {t.get('school') or '-':12} {t['title'][:58]:58}  {holder}"


def age(s):
    if not s:
        return '-'
    d = int((now() - parse(s)).total_seconds())
    return f'{d // 60} min ago' if d < 7200 else f'{d // 3600} h ago'


def show(t):
    print(f"{t['id']}  {t['title']}\n  status {state(t)}   kind {t['kind']}   school {t.get('school') or '-'}\n  scope  {', '.join(t['scope']) or '-'}")
    print(f"  holder {t.get('session') or '-'}   branch {t.get('branch') or '-'}   claimed {t.get('claimed_at') or '-'}   heartbeat {t.get('heartbeat') or '-'} (ttl {t.get('ttl')} s)")
    print(f"  commit {t.get('commit') or '-'}   jobs {', '.join(t.get('jobs', [])) or '-'}\n  note   {t.get('note') or '-'}")
    for h in t.get('history', [])[-6:]:
        print(f"    {h['at']} {h['by']} {h['event']} {h.get('note') or ''}")


def refuse(t, cs):
    print(f"claim {t['id']} REFUSED: a live claim overlaps. See `atlas task show <id>`; do not start this work, pick another task, or ask the holder:", file=sys.stderr)
    for o, why in cs:
        print(f"  {o['id']} {o['title']!r}: {why}; held by {o.get('session')} on branch {o.get('branch') or '-'} (heartbeat {age(o.get('heartbeat'))}, ttl {o.get('ttl')} s)", file=sys.stderr)
    print("  (--allow-overlap 'reason' overrides and is recorded; use it only when you know the scopes are disjoint)", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, prog='atlas task')
    ap.add_argument('cmd', choices=['add', 'list', 'claim', 'heartbeat', 'done', 'block', 'release', 'drop', 'show', 'import', 'land-lock'])
    ap.add_argument('arg', nargs='?', help='task id | import file | land-lock action')
    ap.add_argument('--session'); ap.add_argument('--root'); ap.add_argument('--title'); ap.add_argument('--school', default='')
    ap.add_argument('--kind'); ap.add_argument('--scope', action='append', default=[]); ap.add_argument('--id'); ap.add_argument('--note')
    ap.add_argument('--branch'); ap.add_argument('--commit'); ap.add_argument('--job', action='append', default=[]); ap.add_argument('--ttl', type=int)
    ap.add_argument('--running', action='store_true'); ap.add_argument('--allow-overlap', default=''); ap.add_argument('--force', action='store_true')
    ap.add_argument('--status'); ap.add_argument('--mine', action='store_true'); ap.add_argument('--all', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'list':
        me = session_id(a.session) if a.mine else None
        rows = [t for t in load(a.root) if (a.all or t['status'] not in ('done', 'dropped')) and (not a.status or a.status in (state(t), t['status']))
                and (not a.school or t.get('school') == a.school) and (not a.kind or t['kind'] == a.kind) and (not me or t.get('session') == me)]
        if a.json:
            print(json.dumps(rows, indent=1))
        else:
            for t in sorted(rows, key=lambda t: (state(t) in ('done', 'dropped'), t['id'])):
                print(fmt(t))
            print(f'{len(rows)} task(s); claim first: atlas task claim <id> --branch <b>', file=sys.stderr)
        return 0
    if a.cmd == 'show':
        show(find(load(a.root), a.arg))
        return 0
    if a.cmd == 'land-lock':
        s = session_id(a.session) if a.arg in ('acquire', 'release') else (a.session or os.environ.get('ATLAS_SESSION') or os.environ.get('CLAUDE_SESSION_ID'))
        if a.arg == 'acquire':
            ok, l = AL.acquire(LAND, s, a.ttl or LAND_TTL, a.note or '', root_dir(a.root), a.force)
            print(f'land-lock acquire: ok ({s}); release it after the fast-forward' if ok else f"land-lock acquire: REFUSED, {l['session']} is landing ({l.get('note') or ''}), renewed {l['renewed_at']}", file=sys.stderr if not ok else sys.stdout)
            return 0 if ok else 3
        if a.arg == 'release':
            ok, l = AL.release(LAND, s, root_dir(a.root), a.force)
            print('land-lock release: ok' if ok else f"land-lock release: REFUSED, held by {l['session']}", file=sys.stderr if not ok else sys.stdout)
            return 0 if ok else 3
        if a.arg in ('check', 'status', None):
            st, l = land_check(s, a.root)
            print(f"land-lock: {st}" + (f" ({l['session']}, renewed {l['renewed_at']}, ttl {l['ttl']} s)" if st != 'free' and l else ''))
            return 0 if st in ('free', 'ours') else 3
        raise SystemExit('land-lock acquire|release|status|check')
    if a.cmd == 'import':
        n = 0
        with locked(a.root):
            tasks = load(a.root)
            for d in json.loads(Path(a.arg).read_text()):
                if any(t['id'] == d['id'] for t in tasks):
                    continue
                t = make(tasks, d['title'], d.get('school', ''), d.get('kind', 'build'), d.get('scope', []), d['id'], d.get('note', ''), by='import',
                         branch=d.get('branch', ''), jobs=d.get('jobs', []))
                if d.get('claimed_by'):   # seeded claim: the observation time is the heartbeat; the long ttl is the seed's, the holder renews it
                    t.update(status='claimed', session=d['claimed_by'], claimed_at=stamp(), heartbeat=stamp(), ttl=d.get('ttl', 4 * 3600))
                if d.get('status') in ('done', 'blocked', 'dropped'):
                    t['status'] = d['status']
                note_history(t, 'import', 'import', d.get('source', ''))
                tasks.append(t); n += 1
            save(tasks, a.root)
        print(f'imported {n} task(s)')
        return 0
    s = session_id(a.session)
    if a.cmd == 'add':
        if not a.title:
            raise SystemExit('--title is needed')
        ok, t = add(a.title, a.school, a.kind or 'build', a.scope, a.id, a.note or '', s, a.root)
        if not ok:
            print(f"add REFUSED: {t['id']} has the same title ({state(t)}, {t.get('session') or 'unclaimed'}, branch {t.get('branch') or '-'})", file=sys.stderr)
            return 3
        print(f"added {t['id']}: {t['title']}")
        return 0
    if not a.arg:
        raise SystemExit('a task id is needed')
    if a.cmd == 'claim':
        ok, t, cs = claim(a.arg, s, a.branch or '', a.ttl or TTL, a.running, a.allow_overlap, a.root)
        if not ok:
            refuse(t, cs)
            return 3
        print(f"claimed {t['id']} as {s} (ttl {t['ttl']} s): heartbeat at least every {t['ttl'] // 2} s; done with --commit")
        return 0
    if a.cmd == 'heartbeat':
        t = update(a.arg, s, branch=a.branch, commit=a.commit, jobs=a.job, note=a.note, running=a.running, event='heartbeat', root=a.root)
        print(f"heartbeat {t['id']} ok ({state(t)})")
        return 0
    spec = dict(done=('done', True), block=('blocked', False), release=('open', False), drop=('dropped', False))[a.cmd]
    if a.cmd in ('block', 'drop') and not a.note:
        raise SystemExit(f'{a.cmd} needs --note (the reason)')
    t = update(a.arg, s, status=spec[0], branch=a.branch, commit=a.commit, jobs=a.job, note=a.note, event=a.cmd, root=a.root, require_commit=spec[1], force=a.force)
    print(f"{a.cmd} {t['id']}: ok ({t['status']})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
