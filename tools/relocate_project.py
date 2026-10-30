"""Move the project into one root (/n/fs/resemble/homogenizing-science, 2026-10-30): the cutover tool. Dry run by default.

The mapping is atlas_paths' two layouts (every slot in atlas_paths._LEGACY -> where the project layout puts it) plus
docs/relocation/map-extra.tsv for what atlas_paths does not name (the world atlas's own files, the stores one school at
a time, the site history, the links that the move leaves dangling). After the move, the cutover itself is one line in
tools/atlas_paths.py (LAYOUT_DEFAULT = 'project') and a regenerated paths.sh.

usage: relocate_project.py                         print the plan: every entry, the order, conflicts, leftovers, the
                                                   preflight (busy processes, held .loop.lock files)
       relocate_project.py --rewrite-refs [--refs-in FILE ...]
                                                   also: the absolute references in the code repository's tracked text
                                                   files (and FILEs) that the move rewrites, and the unmapped ones
       relocate_project.py --apply [--compat-links] make the moves (and with --rewrite-refs, the rewrites); refuses on any
                                                   conflict, while a process of this user on this host has a cwd or an
                                                   open file under a source, or while any store's .loop.lock is held
       relocate_project.py --remove-compat [--record FILE]
                                                   remove exactly the temporary links --compat-links recorded

Rules: moves are os.rename within one filesystem (st_dev of the source and of the destination's parent must match);
children that go elsewhere move out before their parent; nothing is moved into its own subtree; nothing is copied or
deleted; no permanent links (--compat-links makes temporary ones, recorded for --remove-compat). Every move, directory
creation and link is appended to <MIGRATIONS>/relocate-<date>.jsonl. Only known paths are stat'ed or listed (depth 1);
nothing walks the shared filesystem.
"""
import argparse
import datetime
import errno
import fcntl
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import atlas_paths as P  # noqa: E402

EXTRAS = HERE.parent / 'docs' / 'relocation' / 'map-extra.tsv'
KINDS = ('rename', 'split', 'pool', 'keep', 'alias', 'stale-link', 'skip')
REF = re.compile(r'/n/fs/resemble(?:/[A-Za-z0-9._+@=,\-]+)+')
REWRITE_EXCLUDE = ('tools/atlas_paths.py', 'tools/relocate_project.py', 'tests/test_relocate_project.py',
                   'tests/test_atlas_paths.py', 'docs/relocation/map-extra.tsv')  # they hold the old paths on purpose
MAX_TEXT = 5 * 1024 * 1024


def inside(a, b):
    """a is b or below it (strings, no trailing slash)."""
    return a == b or a.startswith(b.rstrip('/') + '/')


def depth(p):
    return p.rstrip('/').count('/')


def entry(old, new, kind, note, source):
    if kind not in KINDS:
        raise ValueError(f'unknown kind {kind!r} for {old}')
    return dict(old=os.path.normpath(old), new=os.path.normpath(new) if new else None, kind=kind, note=note, source=source)


def slot_entries(legacy, project):
    """atlas_paths slots: legacy location -> project location."""
    out = []
    for name, old in legacy.items():
        new = str(project[name])
        kind = 'keep' if os.path.normpath(old) == os.path.normpath(new) else 'rename'
        if kind == 'rename' and inside(new, old):
            kind = 'split'  # would move into its own subtree: its items are mapped one by one instead
        out.append(entry(old, new, kind, f'atlas_paths slot {name}', f'slot:{name}'))
    return out


def load_extras(path, root):
    out = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) < 3:
            raise ValueError(f'{path}:{n}: expected old<TAB>new<TAB>kind[<TAB>note]')
        old, new, kind = parts[:3]
        note = parts[3] if len(parts) > 3 else ''
        new = None if new == '-' else (new if new.startswith('/') else str(Path(root) / new))
        out.append(entry(old, new, kind, note, f'extra:{n}'))
    return out


def _exists(p):
    return os.path.lexists(p)


def _dev(p):
    """st_dev of p, or of its nearest existing ancestor (a destination does not exist yet)."""
    q = Path(p)
    while not q.exists():
        q = q.parent
    return os.stat(str(q)).st_dev


def _listdir(p):
    try:
        return sorted(os.listdir(p))
    except OSError:
        return []


def build_plan(legacy, project, extras, root):
    """The ordered plan: dict(entries=[...], conflicts=[...], leftovers={split: [...]})."""
    root = os.path.normpath(str(root))
    by_old = {}
    for e in slot_entries(legacy, project):
        by_old[e['old']] = e
    for e in extras:
        if e['old'] in by_old:
            e['note'] = (e['note'] + '; ' if e['note'] else '') + f"overrides {by_old[e['old']]['source']}"
        by_old[e['old']] = e
    entries = list(by_old.values())
    containers = [e for e in entries if e['kind'] in ('rename', 'split', 'pool')]
    conflicts = []
    for e in entries:
        parents = [p for p in containers if p is not e and p['old'] != e['old'] and inside(e['old'], p['old'])]
        if not parents:
            continue
        p = max(parents, key=lambda q: len(q['old']))
        e['parent'] = p['old']
        if p['kind'] == 'rename' and e['kind'] == 'rename':
            carried = p['new'] + e['old'][len(p['old']):]
            if e['new'] == carried:
                e['kind'] = 'with-parent'
                e['note'] = (e['note'] + '; ' if e['note'] else '') + f"moves with {p['old']}"
            else:
                e['note'] = (e['note'] + '; ' if e['note'] else '') + f"moves out before its parent {p['old']}"
        movers = [q for q in parents if q['kind'] == 'rename']
        if e['kind'] != 'rename' and movers:  # whatever stays in place travels with its nearest moving ancestor
            q = max(movers, key=lambda q: len(q['old']))
            e['travels_to'] = q['new'] + e['old'][len(q['old']):]
    renames = sorted([e for e in entries if e['kind'] == 'rename'], key=lambda e: (-depth(e['old']), e['old']))
    # directories the moves need: split/pool targets and the destinations' missing ancestors
    produced = {e['new']: i for i, e in enumerate(renames)}
    mkdirs = set()
    for e in entries:
        if e['kind'] in ('split', 'pool') and e['new'] and e['new'] != root and not _exists(e['new']):
            if not inside(e['new'], e['old']) or e['old'] == root:
                mkdirs.add(e['new'])
    for i, e in enumerate(renames):
        a = Path(e['new']).parent
        while inside(str(a), root) and str(a) != root:
            s = str(a)
            if s in produced:
                if produced[s] > i:
                    conflicts.append(f"{e['old']}: destination parent {s} is created by a later move")
                break
            if not _exists(s):
                mkdirs.add(s)
            a = a.parent
    mk = [dict(old=None, new=d, kind='mkdir', note='new directory', source='derived') for d in sorted(mkdirs, key=depth)]
    news = {}
    for e in renames:
        old, new = e['old'], e['new']
        if new in news:
            conflicts.append(f'{old}: same destination as {news[new]} ({new})')
        news[new] = old
        if not _exists(old):
            conflicts.append(f'{old}: source missing')
            continue
        if os.path.islink(old):
            conflicts.append(f'{old}: source is a symlink (move its target instead)')
        if inside(new, old):
            conflicts.append(f'{old}: destination {new} is inside the source')
        if _exists(new):
            conflicts.append(f'{old}: destination exists: {new}')
        for o in renames:
            if o is not e and inside(new, o['old']):
                conflicts.append(f"{old}: destination {new} is inside another source {o['old']}")
        try:
            if _dev(old) != _dev(new):
                conflicts.append(f'{old}: cross-device move to {new} (not a rename)')
        except OSError as x:
            conflicts.append(f'{old}: cannot stat ({x})')
    for e in entries:
        if e['kind'] == 'stale-link' and _exists(e['old']) and not os.path.islink(e['old']):
            conflicts.append(f"{e['old']}: listed as a stale link but is not a symlink")
    leftovers = {}
    olds = [e['old'] for e in entries]
    for e in entries:
        if e['kind'] != 'split' or not os.path.isdir(e['old']) or os.path.islink(e['old']):
            continue
        left = []
        for name in _listdir(e['old']):
            p = os.path.join(e['old'], name)
            if p in olds:
                continue
            if any(inside(o, p) for o in olds):
                left.append(name + '/ (partly mapped)')
            elif inside(e['new'] or '', p):
                continue  # the split's own target (the project root's new directories)
            else:
                left.append(name + ('@' if os.path.islink(p) else '/' if os.path.isdir(p) else ''))
        leftovers[e['old']] = left
    rest = [e for e in entries if e['kind'] != 'rename']
    order = {'with-parent': 0, 'split': 1, 'pool': 2, 'stale-link': 3, 'alias': 4, 'keep': 5, 'skip': 6}
    rest.sort(key=lambda e: (order[e['kind']], e['old']))
    return dict(entries=mk + renames + rest, conflicts=conflicts, leftovers=leftovers, root=root)


def default_plan(extras_path=EXTRAS):
    env = {'CS_ATLAS_LAYOUT': 'project'}
    if os.environ.get('CS_ATLAS_ROOT'):
        env['CS_ATLAS_ROOT'] = os.environ['CS_ATLAS_ROOT']
    project = P._resolve(env)
    return build_plan(P._LEGACY, project, load_extras(extras_path, project['ROOT']), project['ROOT']), project


# ---------------------------------------------------------------- preflight


def busy_processes(sources, proc='/proc', uid=None, self_pid=None):
    """[(pid, what, path)] for this user's processes whose cwd or an open file is under a source."""
    uid = os.getuid() if uid is None else uid
    self_pid = os.getpid() if self_pid is None else self_pid
    srcs = set()
    for s in sources:
        srcs.add(os.path.normpath(s))
        try:
            srcs.add(os.path.realpath(s))
        except OSError:
            pass
    hits = []
    for pid in _listdir(proc):
        if not pid.isdigit() or int(pid) == self_pid:
            continue
        d = os.path.join(proc, pid)
        try:
            if os.stat(d).st_uid != uid:
                continue
        except OSError:
            continue
        links = [('cwd', os.path.join(d, 'cwd'))] + [('fd', os.path.join(d, 'fd', f)) for f in _listdir(os.path.join(d, 'fd'))]
        for what, link in links:
            try:
                target = os.readlink(link)
            except OSError:
                continue
            if any(inside(target, s) for s in srcs):
                hits.append((int(pid), what, target))
    return hits


def lock_held(path):
    """True when another process holds the flock on path (the download loops hold their store's .loop.lock). A shared
    lock attempt conflicts with the loops' exclusive one and changes nothing; it is released at once. Any other error is
    reported as held: the move must not go ahead unverified."""
    fd = os.open(path, os.O_RDONLY)
    try:
        for mode in (fcntl.LOCK_EX, fcntl.LOCK_SH):  # LOCK_EX on a read-only fd fails with EBADF on NFS: then LOCK_SH
            try:
                fcntl.flock(fd, mode | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
                return False
            except OSError as x:
                if x.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES):
                    return True
                if x.errno != errno.EBADF:
                    return True
        return True
    finally:
        os.close(fd)


def store_locks(store_dirs):
    """{lock file: held?} for every <store>/.loop.lock under the given store directories (depth 1)."""
    out, seen = {}, set()
    for d in store_dirs:
        cands = [d] + [os.path.join(d, n) for n in _listdir(d)]
        for c in cands:
            f = os.path.join(c, '.loop.lock')
            if not os.path.isfile(f):
                continue
            r = os.path.realpath(f)
            if r in seen:
                continue
            seen.add(r)
            try:
                out[f] = lock_held(f)
            except OSError:
                out[f] = True
    return out


# ---------------------------------------------------------------- references


def rewrite_map(entries, root=None):
    """[(old, new or None)] longest first: None means a known path that stays (keep, and a pool: it stays where it
    is). A dissolved directory maps to its new directory, except the project root itself and a directory dissolved into
    the root (what was under them is ambiguous: such references are listed as unmapped)."""
    m = [(e['old'], e['new']) for e in entries
         if e['kind'] in ('rename', 'with-parent', 'stale-link', 'alias') and e['new'] and e['old']]
    m += [(e['old'], e['new']) for e in entries
          if e['kind'] == 'split' and e['new'] and root not in (e['old'], e['new'])]
    m += [(e['old'], None) for e in entries if e['kind'] in ('keep', 'pool', 'skip')]
    return sorted(m, key=lambda t: -len(t[0]))


def rewrite_text(text, rmap):
    """(new text, [(ref, replacement)], [unmapped refs])."""
    done, unmapped = [], []

    def sub(m):
        ref = m.group(0).rstrip('.,')
        tail = m.group(0)[len(ref):]
        for old, new in rmap:
            if inside(ref, old):
                if new is None:
                    return m.group(0)
                rep = new + ref[len(old):]
                done.append((ref, rep))
                return rep + tail
        if depth(ref) >= 4:
            unmapped.append(ref)
        return m.group(0)
    return REF.sub(sub, text), done, unmapped


def text_files(repo, extra=(), exclude=()):
    r = subprocess.run(['git', '-C', str(repo), 'ls-files', '-z'], stdout=subprocess.PIPE, check=True)
    names = [n.decode() for n in r.stdout.split(b'\0') if n]
    out = [(n, Path(repo) / n) for n in names
           if n not in REWRITE_EXCLUDE and not any(fnmatch.fnmatch(n, g) for g in exclude)]
    out += [(str(f), Path(f)) for f in extra]
    return out


def read_text(p):
    try:
        if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_TEXT:
            return None
        b = p.read_bytes()
    except OSError:
        return None
    if b'\0' in b[:8192]:
        return None
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        return None


def scan_refs(files, rmap, apply=False):
    per_file, unmapped = {}, {}
    for name, p in files:
        t = read_text(p)
        if t is None:
            continue
        new, done, un = rewrite_text(t, rmap)
        if done:
            per_file[name] = done
            if apply:
                p.write_text(new)
        for u in un:
            unmapped.setdefault(u, set()).add(name)
    return per_file, unmapped


def group_unmapped(unmapped):
    """{prefix (/n/fs/resemble/<a>/<b>): (count, [example files])}"""
    g = {}
    for ref, files in unmapped.items():
        key = '/'.join(ref.split('/')[:6])
        c, ex = g.get(key, (0, set()))
        g[key] = (c + len(files), ex | files)
    return {k: (c, sorted(ex)[:3]) for k, (c, ex) in sorted(g.items())}


# ---------------------------------------------------------------- apply


def record(path, **kw):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as f:
        f.write(json.dumps(dict(kw, at=datetime.datetime.now(datetime.timezone.utc).isoformat())) + '\n')


def apply_plan(plan, rec, compat=False):
    for e in plan['entries']:  # every move checked before anything changes
        if e['kind'] == 'rename' and _dev(e['old']) != _dev(e['new']):
            raise SystemExit(f"refused: {e['old']} -> {e['new']} crosses filesystems")
    for e in plan['entries']:
        if e['kind'] == 'mkdir' and not os.path.isdir(e['new']):
            os.makedirs(e['new'])
            record(rec, op='mkdir', new=e['new'])
    moved = []
    for e in plan['entries']:
        if e['kind'] != 'rename':
            continue
        if _dev(e['old']) != _dev(e['new']):
            raise SystemExit(f"refused: {e['old']} -> {e['new']} crosses filesystems")
        os.rename(e['old'], e['new'])
        record(rec, op='rename', old=e['old'], new=e['new'])
        moved.append(e)
    if compat:
        for e in sorted(moved, key=lambda e: depth(e['old'])):  # parents first: a child's link lands through its parent's
            if os.path.isdir(os.path.dirname(e['old'])) and not os.path.lexists(e['old']):
                os.symlink(e['new'], e['old'])
                record(rec, op='compat-link', link=e['old'], real=os.path.join(os.path.realpath(os.path.dirname(e['old'])),
                                                                               os.path.basename(e['old'])), target=e['new'])
            else:
                record(rec, op='compat-link-skipped', link=e['old'], target=e['new'])


def remove_compat(records):
    links = []
    for r in records:
        for line in Path(r).read_text().splitlines():
            x = json.loads(line)
            if x.get('op') == 'compat-link':
                links.append((r, x))
    removed = 0
    for r, x in sorted(links, key=lambda t: -depth(t[1]['real'])):  # children first
        p = x['real']
        if os.path.islink(p) and os.readlink(p) == x['target']:
            os.unlink(p)
            record(r, op='compat-link-removed', link=x['link'], real=p)
            removed += 1
        else:
            print(f'not removed (no longer the recorded link): {p}')
    return removed


# ---------------------------------------------------------------- report


def show(plan, preflight=None):
    root = plan['root']

    def rel(p):
        return p if p is None or not inside(p, root) or p == root else '<ROOT>/' + p[len(root) + 1:]
    print(f'== relocation plan: root {root}')
    print('== 1. directories to create')
    for e in plan['entries']:
        if e['kind'] == 'mkdir':
            print(f"  mkdir   {rel(e['new'])}")
    print('== 2. moves, in order (os.rename)')
    n = 0
    for e in plan['entries']:
        if e['kind'] == 'rename':
            n += 1
            print(f"  {n:3d}. {e['old']}\n         -> {rel(e['new'])}   [{e['source']}{'; ' + e['note'] if e['note'] else ''}]")
    for title, kinds in (('3. carried along (no move of their own)', ('with-parent',)),
                         ('4. dissolved (split) / pools left in place', ('split', 'pool')),
                         ('5. stale links: remove after the move', ('stale-link',)),
                         ('6. aliases (rewrite only) / kept / skipped', ('alias', 'keep', 'skip'))):
        print(f'== {title}')
        for e in plan['entries']:
            if e['kind'] in kinds:
                extra = f" (travels to {rel(e['travels_to'])})" if e.get('travels_to') else ''
                print(f"  {e['kind']:10s} {e['old']} -> {rel(e['new'])}{extra}   {e['note']}")
    print('== 7. leftovers in dissolved directories (not mapped)')
    for k, v in plan['leftovers'].items():
        print(f"  {k}: {', '.join(v) if v else '(nothing)'}")
    print(f"== 8. conflicts: {len(plan['conflicts'])}")
    for c in plan['conflicts']:
        print('  CONFLICT', c)
    if preflight is not None:
        busy, locks = preflight
        print(f'== 9. preflight for --apply: {len(busy)} busy processes of this user on this host, '
              f'{sum(locks.values())} of {len(locks)} store .loop.lock files held')
        for pid, what, path in busy[:40]:
            print(f'  busy pid {pid} {what} {path}')
        for f, held in sorted(locks.items()):
            print(f"  lock {'HELD' if held else 'free'} {f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--compat-links', action='store_true', help='with --apply: temporary links at the old paths')
    ap.add_argument('--remove-compat', action='store_true')
    ap.add_argument('--record', action='append', default=[], help='--remove-compat: the jsonl record(s) to read')
    ap.add_argument('--rewrite-refs', action='store_true')
    ap.add_argument('--refs-in', action='append', default=[], help='also rewrite references in this file')
    ap.add_argument('--exclude', action='append', default=[],
                    help='glob of tracked files not to rewrite (e.g. the reviewed inputs, whose paths are provenance)')
    ap.add_argument('--repo', default=str(P.CODE), help='the code repository whose tracked files are scanned')
    ap.add_argument('--extras', default=str(EXTRAS))
    a = ap.parse_args()
    plan, project = default_plan(a.extras)
    rec = Path(project['MIGRATIONS']) / f'relocate-{datetime.date.today().isoformat()}.jsonl'
    if a.remove_compat:
        recs = a.record or sorted(str(p) for p in Path(project['MIGRATIONS']).glob('relocate-*.jsonl'))
        print(f'removed {remove_compat(recs)} compat links')
        return 0
    if a.compat_links and not a.apply:
        ap.error('--compat-links needs --apply')
    sources = [e['old'] for e in plan['entries'] if e['kind'] == 'rename']
    stores = [P._LEGACY['STORES'], P._LEGACY['STANFORD_STORE']]
    preflight = (busy_processes(sources), store_locks(stores))
    show(plan, preflight)
    if a.rewrite_refs:
        rmap = rewrite_map(plan['entries'], plan['root'])
        per_file, unmapped = scan_refs(text_files(a.repo, a.refs_in, a.exclude), rmap, apply=False)
        print(f'== 10. reference rewrites in {a.repo} (tracked text files; excluded: '
              f'{", ".join(REWRITE_EXCLUDE + tuple(a.exclude))})')
        for name, done in sorted(per_file.items()):
            print(f'  {len(done):4d}  {name}')
        print(f'  total {sum(len(d) for d in per_file.values())} references in {len(per_file)} files')
        print('== 11. unmapped references (no mapping entry): prefix, count, examples')
        for k, (c, ex) in group_unmapped(unmapped).items():
            print(f"  {c:4d}  {k}   e.g. {', '.join(ex)}")
    if not a.apply:
        print('== dry run: nothing was moved or written')
        return 1 if plan['conflicts'] else 0
    busy, locks = preflight
    if plan['conflicts'] or busy or any(locks.values()):
        print('refused: conflicts, busy processes or held .loop.lock files (above)')
        return 2
    apply_plan(plan, rec, compat=a.compat_links)
    if a.rewrite_refs:
        repo = a.repo if os.path.isdir(a.repo) else str(project['CODE'])  # the repository itself has moved
        scan_refs(text_files(repo, a.refs_in, a.exclude), rewrite_map(plan['entries'], plan['root']), apply=True)
    print(f'applied; record: {rec}. Next: LAYOUT_DEFAULT = "project" in tools/atlas_paths.py, regenerate paths.sh, '
          'git worktree repair, remove the stale links listed above.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
