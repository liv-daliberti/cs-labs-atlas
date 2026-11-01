"""Scratch housekeeping (ROADMAP item 13, 2026-10-31): throw-away files live outside the code tree and are cleaned on a schedule.

Where scratch goes
  <SCRATCH> (atlas_paths.SCRATCH, <ROOT>/scratch)   trial builds (PI_HIERARCHY_OUT), pre-rebuild snapshots, diff reports,
                                                    handoff patches. One directory per use: scratch/<who>-<what>/.
  /tmp/$USER-<jobid>                                 node-local job work; every Slurm script removes its own on exit.
  worktrees/<name>/.equiv/                           the equivalence reports of a branch; old ones are cleaned here.
Never in the tree: nothing under hierarchy/ or tools/ is scratch, except what this tool lists below.

What `clean` removes, once the entry is older than --days (default 14; its own mtime, depth 1 only, nothing walked to decide):
  1. every entry directly under <SCRATCH>, unless it holds a file named KEEP;
  2. pkg-before-* in <SCRATCH> (the rebuild's pre-build snapshots) and in hierarchy/logs/ (where they used to go), except the
     newest --keep (default 2);
  3. every entry directly under worktrees/*/.equiv/, unless the name starts with 'keep-'.
Entries are removed whole; nothing else is touched. Dry run unless --apply. rebuild.sh runs `clean --apply` as its last stage.

usage: scratch.py path <name>                    create and print <SCRATCH>/<name> (for scripts: D=$(scratch.py path mytrial))
       scratch.py list [--days N]                what exists and what clean would remove
       scratch.py clean [--days N] [--keep K] [--apply]
"""
import argparse, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

DAY = 86400


def size_note(p):
    return 'dir' if p.is_dir() and not p.is_symlink() else 'file'


def worktree_equiv():
    try:
        out = subprocess.run(['git', '-C', str(P.CODE), 'worktree', 'list', '--porcelain'], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [Path(l.split(' ', 1)[1]) / '.equiv' for l in out.splitlines() if l.startswith('worktree ')]


def candidates(days, keep, now=None, scratch=None, logs=None, equivs=None):
    """[(path, why)] the entries clean would remove."""
    now = time.time() if now is None else now
    cut = now - days * DAY
    scratch = Path(P.SCRATCH if scratch is None else scratch)
    logs = Path(P.data('logs') if logs is None else logs)
    equivs = worktree_equiv() if equivs is None else equivs
    out = []
    if scratch.is_dir():
        for e in sorted(scratch.iterdir()):
            if e.stat().st_mtime < cut and not (e / 'KEEP').exists() and not e.name.startswith('pkg-before-'):
                out.append((e, 'scratch'))
    snaps = sorted((e for d in (scratch, logs) if d.is_dir() for e in d.glob('pkg-before-*')), key=lambda e: e.stat().st_mtime)
    if snaps:
        for e in snaps[:max(len(snaps) - keep, 0)]:
            if e.stat().st_mtime < cut:
                out.append((e, 'rebuild snapshot'))
    for d in equivs:
        if d.is_dir():
            for e in sorted(d.iterdir()):
                if e.stat().st_mtime < cut and not e.name.startswith('keep-'):
                    out.append((e, 'equivalence report'))
    return out


def remove(p):
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    else:
        p.unlink()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('path').add_argument('name')
    for c in ('list', 'clean'):
        s = sub.add_parser(c); s.add_argument('--days', type=float, default=14); s.add_argument('--keep', type=int, default=2)
    sub.choices['clean'].add_argument('--apply', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'path':
        if '/' in a.name or a.name in ('', '.', '..'):
            raise SystemExit('name: one directory name, no slashes')
        d = Path(P.SCRATCH) / a.name
        d.mkdir(parents=True, exist_ok=True)
        print(d)
        return 0
    cands = candidates(a.days, a.keep)
    if a.cmd == 'list':
        root = Path(P.SCRATCH)
        print(f'scratch {root}: ' + (', '.join(sorted(e.name for e in root.iterdir())) if root.is_dir() else '(not created)'))
    verb = 'removing' if getattr(a, 'apply', False) else 'would remove'
    for p, why in cands:
        print(f'{verb} {p} ({why}, {size_note(p)}, {(time.time() - p.stat().st_mtime) / DAY:.0f} days old)')
        if getattr(a, 'apply', False):
            remove(p)
    print(f'{len(cands)} entries older than {a.days:g} days' + ('' if getattr(a, 'apply', False) or a.cmd == 'list' else ' (dry run; --apply removes)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
