"""The data-layout move (ROADMAP item 10, phase B): from today's flat hierarchy/<school>/ to the split layout
(raw/ reviewed/ derived/ work/ reports/), docs/DATA-LAYOUT.md. Dry run by default; the owner approves the move and the
coordinator applies it at a quiet point.

The plan is atlas_paths.DATA_FILES (every entry's 'flat' path -> its 'split' path, for every school with a charter and for
the shared files) plus three rules for what the table does not name: hierarchy/<school>/tmp/ -> <school>/work/tmp/, the
schools' STAGE-*.md and REQUESTS-FOR-BUILDER.md -> <school>/reports/, the shared *-AUDIT.md / *-CHECK.md / *-REGRESSION.md
/ SCHOOL-PROFILES.md -> hierarchy/reports/. Tracked files move with `git mv` (the commit then carries the renames and the
.gitignore whitelist update the plan lists); the rest with os.rename on one filesystem. Nothing is copied or deleted.

usage: relocate_data.py [--json FILE]      the plan (dry run): each move (tracked or not), conflicts, missing sources, the readiness
                                           (code that still joins old paths, the .gitignore lines to translate) and the preflight
                                           (this user's processes with a cwd or an open file under a source, sqlite journals beside a
                                           source, the user's Slurm jobs that run in the project, the stores' held .loop.lock files)
       relocate_data.py --apply --approved-by WHO [--no-commit]
                                           make the moves. Refuses on any conflict, readiness blocker, busy process, sqlite journal,
                                           held loop lock or project job (listed). Tracked files move by `git mv` and, with the
                                           .gitignore translation, DATA_LAYOUT_DEFAULT = 'split' and the regenerated paths.sh, are ONE
                                           commit (--no-commit leaves them staged); the rest by os.rename on one filesystem. Every
                                           action is appended to <MIGRATIONS>/relocate-data-<date>.jsonl.
       relocate_data.py --verify [--record FILE]
                                           after an apply: every moved file is at its split path and no flat path is left; the data
                                           layout is split.
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
CODE_ROOT = HERE.parent   # the checkout this tool belongs to: its code is what the readiness check reads
sys.path.insert(0, str(HERE))
import atlas_paths as P  # noqa: E402
import relocate_project as R  # noqa: E402  (busy_processes, store_locks, record, _dev)
import school_config  # noqa: E402

DIRECT_JOIN = re.compile(r"(P\.)?(HIERARCHY|CENSUS|LISTINGS|PERIODS|CAPTURES)\s*/|'hierarchy'\s*/|/ 'hierarchy'|"
                         r"f'(\{[A-Z_.]+\}/)?(hierarchy|census|listings|periods)/|[\"']hierarchy/|"
                         r"\bH\s*=\s*(P\.HIERARCHY\s*/|HERE\s*/|.*/\s*'hierarchy')|(?<![\w.])H\s*/\s*(\w+\s*/\s*)?'|CS_ATLAS_(HIERARCHY|CENSUS|LISTINGS|PERIODS|CAPTURES)\b")
# a line that says why it is not a data path (tracked code that stays in hierarchy/, a label, a release's own layout) is skipped
SKIP_LINE = re.compile(r"route-ok|REL_HIERARCHY|labpage-tools-|gap-tools-")


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
        for n in sorted(R._listdir(str(H))):
            if fnmatch.fnmatch(n, 'STAGE-*.md') or n == 'REQUESTS-FOR-BUILDER.md':
                out.append((n, s, H / n, H / 'reports' / n))
    return out


CODE_DIR_LINE = re.compile(r'^!hierarchy/(gap|labpage)-tools-')   # tracked code that stays in hierarchy/


def gitignore_translate(line):
    """The .gitignore whitelist line for the split layout, or None when no DATA_FILES entry covers it."""
    body = line[1:]
    if CODE_DIR_LINE.match(line):
        return line
    for name, kind, flat, split in P.DATA_FILES:
        fp, sp = flat.replace('{school}', '*'), split.replace('{school}', '*')
        if body == fp:
            return '!' + sp
        if '{school}' in flat:   # a pattern naming one school (hierarchy/stanford/x.json) is the entry's pattern for that school
            m = re.fullmatch(re.escape(flat).replace(re.escape('{school}'), '(?P<s>[a-z0-9_-]+)'), body)
            if m:
                return '!' + split.replace('{school}', m.group('s'))
        if body.startswith(fp + '/'):   # a directory entry (hierarchy/nicknames/*.csv)
            return '!' + sp + body[len(fp):]
    return None


def gitignore_plan(lines):
    plan_, unmapped = [], []
    for ln in lines:
        new = gitignore_translate(ln)
        (plan_ if new else unmapped).append((ln, new) if new else ln)
    return plan_, unmapped


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
        k = sum(1 for ln in lines if not ln.lstrip().startswith('#') and DIRECT_JOIN.search(ln) and not SKIP_LINE.search(ln))
        if k:
            joins[f] = k
    gi = [ln for ln in (Path(root) / '.gitignore').read_text().splitlines() if ln.startswith(('!hierarchy/', '!census/', '!periods/', '!listings/'))]
    plan_, unmapped = gitignore_plan(gi)
    return dict(direct_joins=joins, gitignore_lines=gi, gitignore_plan=plan_, gitignore_unmapped=unmapped)


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
                readiness=readiness(CODE_ROOT), preflight=pre)


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
          f"(blocker until routed through atlas_paths.data); .gitignore lines to translate: {len(r['gitignore_plan'])}, "
          f"unmapped: {len(r['gitignore_unmapped'])}")
    for x in r['gitignore_unmapped']:
        print(f'  UNMAPPED .gitignore line: {x}')
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
    """The lines an apply would append to <MIGRATIONS>/relocate-data-<date>.jsonl (relocate_project.record format), first three."""
    rec = Path(P.MIGRATIONS) / f'relocate-data-{datetime.date.today().isoformat()}.jsonl'
    ex = [dict(kind='start', approved_by='<owner>', moves=len(pl['moves']))] + \
         [dict(kind='git-mv' if m['tracked'] else 'rename', old=m['old'], new=m['new']) for m in pl['moves'][:2]]
    return str(rec), ex


LAYOUT_LINE = re.compile(r"^DATA_LAYOUT_DEFAULT = '(flat|split)'", re.M)


def preflight_blockers(pl, projects=None):
    """[(why, detail)] that stop an apply: conflicts, readiness, busy processes, sqlite journals, held loop locks, project jobs."""
    out = [('conflict', f"{c['why']}: {c['old']}") for c in pl['conflicts']]
    r = pl['readiness']
    out += [('readiness', f'{n} direct path joins in {f}') for f, n in sorted(r['direct_joins'].items())]
    out += [('readiness', f'.gitignore line without a mapping: {x}') for x in r['gitignore_unmapped']]
    p = pl['preflight']
    out += [('busy process', f'pid {x[0]} {x[1]} {x[2]}') for x in p['busy']]
    out += [('sqlite journal', x) for x in p['journals']]
    out += [('held loop lock', k) for k in p['loop_locks']]
    out += [('project job', x) for x in p['jobs']]
    return out


def project_jobs(root=None):
    """The user's Slurm jobs that run in the project (their working directory is under the project root): they may read or write
    hierarchy/ or stores/ while the files move. Unrelated jobs of the user are ignored."""
    root = str(Path(root or P.ROOT))
    try:
        out = subprocess.run(['squeue', '-u', os.environ.get('USER', ''), '-h', '-o', '%i|%j|%T|%Z'], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ['squeue unavailable']
    jobs_ = []
    for ln in out.splitlines():
        jid, name, state, wd = (ln.split('|') + ['', '', '', ''])[:4]
        if wd.startswith(root):
            jobs_.append(f'{jid} {name} {state} ({wd})')
    return jobs_


def flip_layout(code_root, to='split'):
    f = Path(code_root) / 'tools' / 'atlas_paths.py'
    t = f.read_text()
    if not LAYOUT_LINE.search(t):
        raise SystemExit(f'no DATA_LAYOUT_DEFAULT line in {f}')
    f.write_text(LAYOUT_LINE.sub(f"DATA_LAYOUT_DEFAULT = '{to}'", t, count=1))


def translate_gitignore(code_root, plan_):
    f = Path(code_root) / '.gitignore'
    lines = f.read_text().split('\n')
    m = dict(plan_)
    f.write_text('\n'.join(m.get(ln, ln) if ln in m and m[ln] != ln else ln for ln in lines))
    return sum(1 for a, b in plan_ if a != b)


def regenerate_paths_sh(code_root):
    code_root = Path(code_root)
    out = subprocess.run([sys.executable, str(code_root / 'tools' / 'atlas_paths.py'), '--sh'], capture_output=True, text=True, check=True,
                         env=dict(os.environ, CS_ATLAS_DATA_LAYOUT='split')).stdout
    (code_root / 'paths.sh').write_text(out)


def settle_journals(pl):
    """Open each sqlite file that has a journal or WAL beside it for writing once (a hot journal is rolled back, a WAL checkpointed) and
    report which journals are still there. Only for files no process holds (the plan's preflight says); a stale journal left by a
    killed writer (hierarchy/epfl/labpage-recover.sqlite-journal, 2026-10-22) is settled this way, not deleted."""
    import sqlite3
    left = []
    for j in pl['preflight']['journals']:
        db = j.rsplit('-', 1)[0]
        c = sqlite3.connect(db, timeout=30)
        c.execute('pragma quick_check').fetchall()
        c.execute('pragma wal_checkpoint(truncate)').fetchall()
        c.close()
        if os.path.exists(j) and os.path.getsize(j) > 0:
            left.append(j)
    return left


def apply(pl, approved_by, record, commit=True, code_root=None, regen=regenerate_paths_sh):
    """Make the moves of a plan that has no blocker. Returns the number of moves."""
    blockers = preflight_blockers(pl)
    if blockers:
        for why, detail in blockers:
            print(f'BLOCKED ({why}): {detail}')
        raise SystemExit(f'refused: {len(blockers)} blockers (above)')
    if not approved_by:
        raise SystemExit('refused: --approved-by is required')
    root, code_root = Path(pl['root']), Path(code_root or pl['root'])
    R.record(record, kind='start', approved_by=approved_by, moves=len(pl['moves']), root=str(root))
    for m in pl['moves']:   # the plan lists every entry once; a destination's parents are made on the way
        Path(m['new']).parent.mkdir(parents=True, exist_ok=True)
        if m['tracked']:
            subprocess.run(['git', '-C', str(root), 'mv', m['old'], m['new']], check=True)
        else:
            os.rename(m['old'], m['new'])
        R.record(record, kind='git-mv' if m['tracked'] else 'rename', old=m['old'], new=m['new'], dir=m['dir'], name=m['name'], school=m['school'])
        for suffix in ('-journal', '-wal', '-shm'):   # a sqlite file's companions travel with it (the preflight refuses a live journal first)
            if m['old'].endswith('.sqlite') and os.path.exists(m['old'] + suffix):
                os.rename(m['old'] + suffix, m['new'] + suffix)
                R.record(record, kind='rename', old=m['old'] + suffix, new=m['new'] + suffix, dir=False, name=m['name'] + suffix, school=m['school'])
    n_gi = translate_gitignore(code_root, pl['readiness']['gitignore_plan'])
    flip_layout(code_root)
    regen(code_root)
    R.record(record, kind='layout', gitignore_lines=n_gi, data_layout='split')
    if commit:
        files = ['.gitignore', 'tools/atlas_paths.py', 'paths.sh']
        subprocess.run(['git', '-C', str(code_root), 'add', '--'] + files, check=True)
        subprocess.run(['git', '-C', str(code_root), 'commit', '-q', '-m', f"Data layout: raw/reviewed/derived/work split ({len(pl['moves'])} moves, tracked files by git mv), "
                        f"DATA_LAYOUT_DEFAULT = 'split', .gitignore whitelist translated\n\nApproved by {approved_by}. Record: {record}.\n\n"
                        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"], check=True, env=dict(os.environ, ATLAS_ALLOW_MAIN='1'))   # the one sanctioned direct commit to main
    R.record(record, kind='done', commit=bool(commit))
    return len(pl['moves'])


def verify(record, code_root=None):
    """After an apply: [problem] (empty when all is well): every moved file is at its split path, no flat path is left, layout is split."""
    problems = []
    moves = []
    for ln in Path(record).read_text().splitlines():
        x = json.loads(ln)
        if x.get('kind') in ('git-mv', 'rename'):
            moves.append(x)
    if not moves:
        problems.append(f'no moves in {record}')
    for x in moves:
        if not os.path.lexists(x['new']):
            problems.append(f"missing at the split path: {x['new']}")
        if os.path.lexists(x['old']):
            problems.append(f"a flat path is left: {x['old']}")
    if code_root:
        t = (Path(code_root) / 'tools' / 'atlas_paths.py').read_text()
        mm = LAYOUT_LINE.search(t)
        if not mm or mm.group(1) != 'split':
            problems.append("DATA_LAYOUT_DEFAULT is not 'split'")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', help='also write the plan as JSON')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--approved-by')
    ap.add_argument('--no-commit', action='store_true', help='with --apply: leave the moves and the three edited files staged, uncommitted')
    ap.add_argument('--settle-journals', action='store_true', help='open each sqlite file that has a journal or WAL once for writing, then re-plan')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--record', help='--verify: the migration record (default: the newest relocate-data-*.jsonl)')
    a = ap.parse_args()
    if a.verify:
        rec = a.record or sorted(str(p) for p in Path(P.MIGRATIONS).glob('relocate-data-*.jsonl'))[-1]
        probs = verify(rec, CODE_ROOT)
        for x in probs:
            print('PROBLEM', x)
        print(f'verify {rec}: {len(probs)} problems')
        return 1 if probs else 0
    pl = plan()
    if a.settle_journals:
        print('journals left after settling:', settle_journals(pl))
        pl = plan()
    pl['preflight']['jobs'] = project_jobs()
    show(pl)
    rec, ex = record_preview(pl)
    print(f'record an apply would write: {rec}')
    for x in ex:
        print('  ' + json.dumps(x))
    if a.json:
        Path(a.json).write_text(json.dumps(pl, indent=1, default=str))
    if a.apply:
        n = apply(pl, a.approved_by, rec, commit=not a.no_commit)
        print(f'applied {n} moves; record {rec}. Next: relocate_data.py --verify')
        return 0
    print('== dry run: nothing was moved or written')
    return 1 if pl['conflicts'] else 0


if __name__ == '__main__':
    sys.exit(main())
