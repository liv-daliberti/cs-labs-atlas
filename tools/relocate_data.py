"""The data-layout move (ROADMAP item 10, phase B): from today's flat hierarchy/<school>/ to the split layout
(raw/ reviewed/ derived/ work/ reports/), docs/DATA-LAYOUT.md. Dry run by default; the owner approves the move and the
coordinator applies it at a quiet point.

The plan is atlas_paths.DATA_FILES (every entry's 'flat' path -> its 'split' path, for every school with a charter and for
the shared files) plus three rules for what the table does not name: hierarchy/<school>/tmp/ -> <school>/work/tmp/, the
schools' STAGE-*.md and REQUESTS-FOR-BUILDER.md -> <school>/reports/, the shared *-AUDIT.md / *-CHECK.md / *-REGRESSION.md
/ SCHOOL-PROFILES.md -> hierarchy/reports/. Tracked files move with `git mv` (the commit then carries the renames and the
.gitignore whitelist update the plan lists); the rest with os.rename on one filesystem. Nothing is copied or deleted.

usage: relocate_data.py [--json FILE]      the plan: each move (tracked or not), conflicts, missing sources, the readiness
                                           (code that still joins old paths, the .gitignore lines to update), the preflight
                                           (this user's processes with a cwd or an open file under a source, sqlite journals
                                           beside a source, the project's Slurm jobs, the stores' held .loop.lock files) and
                                           the MIGRATIONS record an apply would write.
THIS TOOL IS A DRY RUN ONLY (2026-10-31): it has no apply mode. The owner reviews the plan first; a later change adds the
apply, modelled on relocate_project.py --apply (refuse on any conflict, readiness blocker or dirty preflight).
Only known paths are stat'ed (and hierarchy/<school>/ listed at depth 1); nothing walks the shared filesystem.
"""
import argparse
import datetime
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
import relocate_project as R  # noqa: E402  (busy_processes, store_locks, record, _dev)
import school_config  # noqa: E402

DIRECT_JOIN = re.compile(r"(P\.)?(HIERARCHY|CENSUS|LISTINGS|PERIODS|CAPTURES)\s*/|'hierarchy'\s*/|/ 'hierarchy'|"
                         r"f'(\{[A-Z_.]+\}/)?(hierarchy|census|listings|periods)/|[\"']hierarchy/")


def tracked(root):
    out = subprocess.run(['git', '-C', str(root), 'ls-files'], capture_output=True, text=True).stdout.split()
    return set(out)


def entries(root, schools):
    """[(name, school, old, new)] for every move the layout implies (old may not exist)."""
    out = []
    for name, kind, flat, split in P.DATA_FILES:
        for s in (schools if '{school}' in flat else [None]):
            old, new = P.data(name, s, root=root, layout='flat'), P.data(name, s, root=root, layout='split')
            if old != new:
                out.append((name, s, old, new))
    for s in schools:
        H = Path(root) / 'hierarchy' / s
        out.append(('tmp/', s, H / 'tmp', H / 'work' / 'tmp'))
        for n in sorted(R._listdir(str(H))):
            if fnmatch.fnmatch(n, 'STAGE-*.md') or n == 'REQUESTS-FOR-BUILDER.md':
                out.append((n, s, H / n, H / 'reports' / n))
    return out


def readiness(root):
    """Code that still names data files by path (they must ask atlas_paths.data first), and the .gitignore lines to update."""
    files = subprocess.run(['git', '-C', str(root), 'ls-files', 'tools/*.py', 'listings/scripts/*.py', 'hierarchy/*.sh',
                            'hierarchy/*.slurm', 'fulltext-push/*.py', 'fulltext-push/**/*.py', 'accuracy/*.py'],
                           capture_output=True, text=True).stdout.split()
    skip = ('tools/atlas_paths.py', 'tools/relocate_project.py', 'tools/relocate_data.py', 'tools/route_paths.py', 'tools/vendor_sync.py')
    joins = {}
    for f in files:
        if f in skip or f.startswith('tools/pihier/'):
            continue
        try:
            lines = (Path(root) / f).read_text(errors='replace').splitlines()
        except OSError:
            continue
        k = sum(1 for ln in lines if not ln.lstrip().startswith('#') and DIRECT_JOIN.search(ln))
        if k:
            joins[f] = k
    gi = [ln for ln in (Path(root) / '.gitignore').read_text().splitlines() if ln.startswith('!hierarchy/') or ln.startswith('!census/') or ln.startswith('!periods/')]
    return dict(direct_joins=joins, gitignore_lines=gi)


def jobs():
    try:
        out = subprocess.run(['squeue', '-u', os.environ.get('USER', ''), '-h', '-o', '%i %j %T'], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ['squeue unavailable']
    return [ln for ln in out.splitlines() if ln.strip()]


def plan(root=None, schools=None):
    root = Path(root or P.CODE)
    schools = schools or school_config.keys()
    tr = tracked(root)
    moves, conflicts, missing = [], [], []
    for name, s, old, new in entries(root, schools):
        if not os.path.lexists(old):
            missing.append(dict(name=name, school=s, old=str(old)))
            continue
        rel = os.path.relpath(old, root)
        is_tracked = rel in tr or any(t.startswith(rel + '/') for t in tr) if os.path.isdir(old) else rel in tr
        m = dict(name=name, school=s, old=str(old), new=str(new), tracked=bool(is_tracked), dir=os.path.isdir(old))
        if os.path.lexists(new):
            conflicts.append(dict(m, why='destination exists'))
        elif R._dev(str(old)) != R._dev(str(Path(new).parent if Path(new).parent.exists() else root)):
            conflicts.append(dict(m, why='crosses filesystems'))
        moves.append(m)
    sources = [m['old'] for m in moves]
    journals = [m['old'] + j for m in moves for j in ('-journal', '-wal') if m['old'].endswith('.sqlite') and os.path.exists(m['old'] + j)]
    pre = dict(busy=R.busy_processes(sources), journals=journals, jobs=jobs(),
               loop_locks={k: v for k, v in R.store_locks([str(P.STORES)]).items() if v})
    return dict(root=str(root), schools=list(schools), moves=moves, conflicts=conflicts, missing=missing,
                readiness=readiness(root), preflight=pre)


def show(pl):
    mv = pl['moves']
    print(f"data-layout move: {len(mv)} moves ({sum(m['tracked'] for m in mv)} tracked, by git mv; "
          f"{sum(not m['tracked'] for m in mv)} by rename), {len(pl['missing'])} table entries with no file, "
          f"{len(pl['conflicts'])} conflicts")
    for m in mv:
        print(f"  {'git mv' if m['tracked'] else 'rename'}  {os.path.relpath(m['old'], pl['root'])} -> {os.path.relpath(m['new'], pl['root'])}")
    for c in pl['conflicts']:
        print(f"  CONFLICT {c['why']}: {c['old']} -> {c['new']}")
    r = pl['readiness']
    print(f"readiness: {sum(r['direct_joins'].values())} direct path joins in {len(r['direct_joins'])} files still name old paths "
          f"(blocker until routed through atlas_paths.data); .gitignore lines to update: {len(r['gitignore_lines'])}")
    for f, k in sorted(r['direct_joins'].items(), key=lambda x: -x[1]):
        print(f'  {k:4d} {f}')
    p = pl['preflight']
    print(f"preflight: {len(p['busy'])} busy processes, {len(p['journals'])} sqlite journals, {len(p['jobs'])} running/pending jobs, "
          f"{len(p['loop_locks'])} held loop locks")
    for x in p['busy'][:20]:
        print(f'  busy {x}')
    for x in p['journals'] + p['jobs']:
        print(f'  {x}')


def record_preview(pl):
    """The lines an apply would append to <MIGRATIONS>/data-layout-<date>.jsonl (relocate_project.record format), first three."""
    rec = Path(P.MIGRATIONS) / f'data-layout-{datetime.date.today().isoformat()}.jsonl'
    ex = [dict(kind='start', approved_by='<owner>', moves=len(pl['moves']))] + \
         [dict(kind='git-mv' if m['tracked'] else 'rename', old=m['old'], new=m['new']) for m in pl['moves'][:2]]
    return str(rec), ex


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', help='also write the plan as JSON')
    a = ap.parse_args()
    pl = plan()
    show(pl)
    rec, ex = record_preview(pl)
    print(f'record an apply would write: {rec}')
    for x in ex:
        print('  ' + json.dumps(x))
    if a.json:
        Path(a.json).write_text(json.dumps(pl, indent=1, default=str))
    print('== dry run: nothing was moved or written')
    return 1 if pl['conflicts'] else 0


if __name__ == '__main__':
    sys.exit(main())
