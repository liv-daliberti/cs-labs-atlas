"""One lease per agent or session (ROADMAP #17, 2026-11-01): a second copy of an agent refuses to start while the first one's lease is live.

  agent_lease.py acquire <name> [--session ID] [--ttl SECONDS] [--note TEXT]    take the lease; exit 3 if another session holds a live one
  agent_lease.py renew   <name> [--session ID] [--note TEXT]                      on each report/step: extends it; exit 3 if it was lost
  agent_lease.py release <name> [--session ID]                                    at a clean stop (handoff)
  agent_lease.py status  [<name>]                                                 every lease: live | expired, holder, age
  agent_lease.py check   <name> [--session ID]                                    exit 0 when free, expired or ours; 3 when held by another

A lease is <ROOT>/leases/<name>.json {session, host, pid, started_at, renewed_at, ttl, note}. It is live while renewed_at + ttl is in the future
(default ttl 1800 s: an agent that works renews on every report, so a crashed or abandoned one is free again after at most half an hour; a restart
that is sure the old copy is gone can `release` it with --force). The session id is $CLAUDE_SESSION_ID, else <host>:<pid>. All changes happen under a
flock on <ROOT>/leases/.lock, so two copies starting together cannot both win.
"""
import argparse, contextlib, datetime, fcntl, json, os, socket, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

TTL = 1800


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(t=None):
    return (t or now()).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse(s):
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)


def session_id():
    return os.environ.get('CLAUDE_SESSION_ID') or f'{socket.gethostname()}:{os.getpid()}'


def path(name, root=None):
    if not name or '/' in name or name.startswith('.'):
        raise SystemExit(f'bad lease name {name!r}')
    return Path(root or P.LEASES) / f'{name}.json'


@contextlib.contextmanager
def locked(root=None):
    d = Path(root or P.LEASES)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / '.lock', 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def read(name, root=None):
    p = path(name, root)
    return json.loads(p.read_text()) if p.exists() else None


def live(lease, at=None):
    return bool(lease) and parse(lease['renewed_at']) + datetime.timedelta(seconds=lease.get('ttl', TTL)) > (at or now())


def acquire(name, session=None, ttl=TTL, note='', root=None, force=False):
    """-> (ok, lease or holder)."""
    session = session or session_id()
    with locked(root):
        cur = read(name, root)
        if live(cur) and cur['session'] != session and not force:
            return False, cur
        t = stamp()
        lease = dict(name=name, session=session, host=socket.gethostname(), pid=os.getpid(), started_at=cur['started_at'] if cur and cur['session'] == session else t,
                     renewed_at=t, ttl=ttl, note=note)
        tmp = path(name, root).with_suffix('.tmp')
        tmp.write_text(json.dumps(lease, indent=1))
        os.replace(tmp, path(name, root))
        return True, lease


def renew(name, session=None, note=None, root=None):
    session = session or session_id()
    with locked(root):
        cur = read(name, root)
        if cur and cur['session'] != session and live(cur):
            return False, cur
        if not cur or cur['session'] != session:   # expired and nobody took it: retake
            pass
        lease = dict(cur or dict(name=name, host=socket.gethostname(), pid=os.getpid(), started_at=stamp(), ttl=TTL, note=''), session=session, renewed_at=stamp())
        if note is not None:
            lease['note'] = note
        path(name, root).write_text(json.dumps(lease, indent=1))
        return True, lease


def release(name, session=None, root=None, force=False):
    session = session or session_id()
    with locked(root):
        cur = read(name, root)
        if not cur:
            return True, None
        if cur['session'] != session and live(cur) and not force:
            return False, cur
        path(name, root).unlink()
        return True, cur


def status(root=None):
    out = []
    d = Path(root or P.LEASES)
    for f in sorted(d.glob('*.json')) if d.is_dir() else []:
        l = json.loads(f.read_text())
        out.append(dict(l, live=live(l), age_s=int((now() - parse(l['renewed_at'])).total_seconds())))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['acquire', 'renew', 'release', 'status', 'check']); ap.add_argument('name', nargs='?')
    ap.add_argument('--session'); ap.add_argument('--ttl', type=int, default=TTL); ap.add_argument('--note'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--root')
    a = ap.parse_args(argv)
    if a.cmd == 'status':
        for l in status(a.root):
            if a.name and l['name'] != a.name:
                continue
            print(f"{l['name']:24} {'LIVE   ' if l['live'] else 'expired'} {l['session']:32} renewed {l['age_s']} s ago, ttl {l['ttl']} s  {l.get('note') or ''}")
        return 0
    if not a.name:
        raise SystemExit('a lease name is needed')
    if a.cmd == 'acquire':
        ok, l = acquire(a.name, a.session, a.ttl, a.note or '', a.root, a.force)
    elif a.cmd == 'renew':
        ok, l = renew(a.name, a.session, a.note, a.root)
    elif a.cmd == 'release':
        ok, l = release(a.name, a.session, a.root, a.force)
    else:
        cur = read(a.name, a.root)
        ok, l = not (live(cur) and cur['session'] != (a.session or session_id())), cur
    if ok:
        print(f'{a.cmd} {a.name}: ok')
        return 0
    print(f"{a.cmd} {a.name}: REFUSED, a live lease is held by {l['session']} on {l['host']} (renewed {l['renewed_at']}, ttl {l['ttl']} s): {l.get('note') or ''}", file=sys.stderr)
    return 3


if __name__ == '__main__':
    sys.exit(main())
