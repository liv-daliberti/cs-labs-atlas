"""Plan (and, after owner sign-off, apply) the school-layout move of 2026-11-26: each school's data physically under
<ROOT>/schools/<school>/ (docs/relocation/SCHOOL-LAYOUT-PLAN.md), plus the tidy-up of the project root.

usage: relocate_schools.py                  the dry-run plan for every released/onboarding school: directories to create, moves
                                            (source -> destination, in order), the one permanent link, what stays in git, leftovers,
                                            conflicts, the preflight (busy cwd/open files, held .loop.lock, live Slurm jobs), the
                                            project-root tidy-up, per-school completeness and totals
       relocate_schools.py --references     also: per-school paths hard-coded in tracked code, Slurm scripts, docs and tests
                                            (git grep over the index, never the filesystem) that bypass atlas_paths
       relocate_schools.py --school mit ... restrict the per-school sections to these schools
       relocate_schools.py --no-ai          leave ai-writing/data/embeddings/<model>/<school> out (its users hand-join paths)
       relocate_schools.py --apply [--compat-links]
                                            make the moves (refused on any conflict, busy process or held lock) -- NOT to be run
                                            before the cutover steps in the plan document

Rules (as relocate_project.py): moves are os.rename within one filesystem (st_dev of the source and of the destination's nearest
existing ancestor must match); nothing is copied or deleted; only known paths are stat'ed or listed (depth 1); `git ls-files` and
`git grep` read the index. Directories that hold git-tracked files are moved child by child and the tracked children stay in git.
The only permanent link is schools/<school>/reviewed -> <CODE>/hierarchy/<school>/reviewed (owner sign-off). Root tidy-up items that
delete anything (empty directories, caches, a stale lock) are listed as `remove (owner approval)` and never executed by this tool.
Every apply step is appended to <MIGRATIONS>/school-layout-<date>.jsonl.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

import atlas_paths as P
import relocate_project as R

PARTS_DIRS = ('derived', 'raw', 'work', 'reports', 'tmp')     # hierarchy/<s>/<part> -> schools/<s>/<part>
SLURM_OUT = re.compile(r'^slurm-.*\.out$')
SITE_LOOSE = ('site-interim-1120', 'site-publish-1115', 'site-visibility-1118')
EMPTY_DIRS = ('x', 'site-host-update-1115')
SQLITE_SIDE = ('', '-wal', '-shm', '-journal')


def school_keys(configs=None):
    """Every charter under <CODE>/schools/<key>.toml except TEMPLATE (released and onboarding): 40 today."""
    d = Path(configs or P.SCHOOL_CONFIGS)
    return sorted(f.stem for f in d.glob('*.toml') if f.stem != 'TEMPLATE')


def tracked_files(code, prefixes):
    """{path relative to code} tracked by git under the given prefixes (one `git ls-files`, the index only)."""
    r = subprocess.run(['git', '-C', str(code), 'ls-files', '-z', '--', *prefixes], stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, check=False)
    return {n.decode() for n in r.stdout.split(b'\0') if n}


def _mv(old, new, group, school, note='', kind='rename'):
    return dict(kind=kind, old=str(old) if old else None, new=str(new) if new else None, group=group, school=school, note=note)


def layout_of(cfg=None):
    """The directories the plan reads, from atlas_paths (tests pass a fake tree)."""
    c = dict(ROOT=P.ROOT, CODE=P.CODE, SCHOOLS_TREE=P.SCHOOLS_TREE, STORES=P.STORES, LISTINGS=P.LISTINGS, CAPTURES=P.CAPTURES,
             CENSUS=P.CENSUS, PERIODS=P.PERIODS, FT_CHECKS=P.FT_CHECKS, EMBEDDINGS=P.EMBEDDINGS, HIERARCHY=P.HIERARCHY,
             SLURM_LOGS=P.SLURM_LOGS, MIGRATIONS=P.MIGRATIONS)
    c.update(cfg or {})
    return {k: Path(v) for k, v in c.items()}


def plan_school(s, cfg, tracked, ai=True):
    """The entries for one school: moves (kind rename / git-mv), the permanent link, tracked files that stay, leftovers, absent sources."""
    H, T = cfg['HIERARCHY'] / s, cfg['SCHOOLS_TREE'] / s
    out = []
    code = cfg['CODE']

    def rel(p):
        return str(Path(p).relative_to(code)) if str(p).startswith(str(code) + os.sep) else '__outside__'

    def stays(prefix):
        return sorted(t for t in tracked if t.startswith(prefix + '/'))

    for part in PARTS_DIRS:   # derived raw work reports tmp
        src, dst = H / part, T / part
        if not R._exists(src):
            out.append(_mv(src, dst, part, s, 'absent today', 'absent'))
            continue
        if os.path.islink(src):
            out.append(_mv(src, dst, part, s, 'source is a symlink', 'conflict'))
            continue
        tr = stays(rel(src))
        if not tr:
            out.append(_mv(src, dst, part, s))
            continue
        top = {t[len(rel(src)) + 1:].split('/')[0] for t in tr}   # children that carry tracked files stay in git
        out.append(_mv(None, dst, part, s, f'{len(tr)} tracked file(s) in {rel(src)}: moved child by child', 'mkdir'))
        for name in R._listdir(src):
            if name not in top:
                out.append(_mv(src / name, dst / name, part, s))
        for t in tr:
            out.append(_mv(code / t, None, part, s, 'tracked: stays in git (owner: git rm --cached if it is a generated file)', 'stay-tracked'))
    if R._exists(H / 'reviewed'):   # the one permanent link; the tracked decision files stay
        out.append(_mv(T / 'reviewed', H / 'reviewed', 'reviewed', s, 'PERMANENT LINK (owner sign-off): decisions stay tracked at code/hierarchy/<s>/reviewed', 'link'))
    else:
        out.append(_mv(None, T / 'reviewed', 'reviewed', s, 'no hierarchy/<s>/reviewed today', 'absent'))
    man = H / 'inputs-manifest.sha256.json'
    if R._exists(man):
        out.append(_mv(man, T / 'derived' / man.name, 'derived', s, 'input_manifest.py writes it beside the data; its path is hand-joined'))
    # listings
    L = cfg['LISTINGS'] / s
    if R._exists(L):
        tr = stays(rel(L))
        if tr:
            out.append(_mv(None, T / 'listings', 'listings', s, f'{len(tr)} tracked file(s): child by child', 'mkdir'))
            top = {t[len(rel(L)) + 1:].split('/')[0] for t in tr}
            out += [_mv(L / n, T / 'listings' / n, 'listings', s) for n in R._listdir(L) if n not in top]
            out += [_mv(code / t, None, 'listings', s, 'tracked: stays in git', 'stay-tracked') for t in tr]
        else:
            out.append(_mv(L, T / 'listings', 'listings', s))
    else:
        out.append(_mv(L, T / 'listings', 'listings', s, 'absent today', 'absent'))
    # store (the loops hold <store>/.loop.lock)
    St = cfg['STORES'] / s
    out.append(_mv(St, T / 'store', 'store', s, 'a download loop may hold .loop.lock') if R._exists(St)
               else _mv(St, T / 'store', 'store', s, 'absent today', 'absent'))
    # checks: the ledger's sqlite and its journal files
    got = False
    for suf in SQLITE_SIDE:
        f = cfg['FT_CHECKS'] / f'{s}.sqlite{suf}'
        if R._exists(f):
            got = True
            out.append(_mv(f, T / 'checks' / f.name, 'checks', s, 'ledger sqlite' + (' (journal file)' if suf else '')))
    if not got:
        out.append(_mv(cfg['FT_CHECKS'] / f'{s}.sqlite', T / 'checks' / f'{s}.sqlite', 'checks', s, 'absent today', 'absent'))
    # captures/<s>.sqlite -> raw/school-captures.sqlite
    cap = cfg['CAPTURES'] / f'{s}.sqlite'
    twin = H / 'raw' / 'school-captures.sqlite'
    if R._exists(cap) and R._exists(twin):   # the pre-split copy: a 0-byte leftover is removed with approval, anything else is a conflict
        empty = os.path.getsize(cap) == 0
        out.append(_mv(cap, None if empty else T / 'raw' / 'school-captures.sqlite', 'captures', s,
                       'empty pre-split leftover (hierarchy/<s>/raw/school-captures.sqlite is the live copy)' if empty
                       else 'hierarchy/<s>/raw/school-captures.sqlite also exists: two non-empty copies of the school captures',
                       'remove-approval' if empty else 'conflict'))
        cap = None
    if cap is not None:
        out.append(_mv(cap, T / 'raw' / 'school-captures.sqlite', 'captures', s, 'data(school-captures.sqlite)') if R._exists(cap)
                   else _mv(cap, T / 'raw' / 'school-captures.sqlite', 'captures', s, 'absent today', 'absent'))
    # census/ and periods/: per-school files by prefix (none today)
    for grp, d in (('census', cfg['CENSUS']), ('periods', cfg['PERIODS'])):
        names = [n for n in R._listdir(d) if n.startswith(s + '-')]
        for n in names:
            kind_dir = 'reviewed' if grp == 'periods' or n.endswith('additions.json') else 'derived'
            out.append(_mv(d / n, T / kind_dir / n.replace(s + '-', '', 1), grp, s, f'{grp}/ per-school file'))
        if not names:
            out.append(_mv(d / (s + '-*'), None, grp, s, f'no {grp}/{s}-* files today', 'absent'))
    # per-school files inside shared hierarchy directories (reader, link-sweep) and the tracked listings-input
    for sub, name, dest, part in (('derived/reader', f'{s}.jsonl.gz', 'reader.jsonl.gz', 'derived'),
                                  ('derived/link-sweep', f'{s}.json', 'link-sweep.json', 'derived'),
                                  ('', f'sweep-{s}.log', 'sweep.log', 'work')):
        f = cfg['HIERARCHY'] / sub / name
        if R._exists(f):
            out.append(_mv(f, T / part / dest, 'shared-dir', s, f'per-school file of hierarchy/{sub or "."}'))
    li = cfg['HIERARCHY'] / 'reviewed' / f'listings-input-{s}.json'
    if R._exists(li):
        out.append(_mv(li, H / 'reviewed' / 'listings-input.json', 'reviewed', s, 'TRACKED: git mv into the reviewed directory (history kept); the link then exposes it', 'git-mv'))
    # ai: embeddings/<model>/<school>
    if ai:
        for model in R._listdir(cfg['EMBEDDINGS']):
            d = cfg['EMBEDDINGS'] / model
            if os.path.isdir(d) and s in R._listdir(d):
                out.append(_mv(d / s, T / 'ai' / 'embeddings' / model, 'ai', s, 'embeddings <model>/<school>'))
    # leftovers: anything else directly under hierarchy/<s>
    known = set(PARTS_DIRS) | {'reviewed', 'inputs-manifest.sha256.json'}
    for name in R._listdir(H):
        if name in known:
            continue
        r = rel(H / name)
        tracked_here = any(t == r or t.startswith(r + '/') for t in tracked)
        if tracked_here:
            out.append(_mv(code / r, None, 'leftover', s, 'tracked: stays in git', 'stay-tracked'))
        else:   # owner decision 4 (2026-11-26): untracked leftovers go to the school's work/
            out.append(_mv(H / name, T / 'work' / name, 'work', s, 'untracked leftover: into the school work/ (owner decision 4)'))
    return out


def plan_root(cfg):
    """The project-root tidy-up (owner 2026-11-26): stray Slurm outputs, loose site checkouts, empty directories, the rest."""
    root, out = cfg['ROOT'], []
    names = R._listdir(root)
    logs = cfg['SLURM_LOGS']
    for n in names:
        if SLURM_OUT.match(n) and os.path.isfile(root / n):
            out.append(_mv(root / n, logs / n, 'slurm-logs', None, 'stray Slurm output'))
    code = cfg['CODE']
    if code != root:   # the main checkout's root collects them too (git-ignored): jobs submitted from <CODE> without --output
        for n in R._listdir(code):
            if (SLURM_OUT.match(n) or re.match(r'^[a-z-]+-[0-9]+\.out$', n)) and os.path.isfile(code / n):
                out.append(_mv(code / n, logs / n, 'slurm-logs', None, 'stray Slurm output in the code root (git-ignored)'))
    stray = root / 'hierarchy' / 'logs'
    for n in R._listdir(stray):
        out.append(_mv(stray / n, logs / n, 'slurm-logs', None, 'job run with cwd=<ROOT> wrote hierarchy/logs/'))
    for n in SITE_LOOSE:
        if n in names:
            out.append(_mv(root / n, root / 'site-worktrees' / n, 'site', None, 'git worktree of site/: `git -C site worktree move`', 'git-worktree-move'))
    for n in EMPTY_DIRS:
        p = root / n
        if n in names and os.path.isdir(p):
            out.append(_mv(p, None, 'empty', None, f'{len(R._listdir(p))} entries: empty directory', 'remove-approval'))
    if 'hierarchy' in names:
        out.append(_mv(root / 'hierarchy', None, 'empty', None, 'becomes empty once logs/ is moved out', 'remove-approval'))
    if '.pytest_cache' in names:
        out.append(_mv(root / '.pytest_cache', None, 'cache', None, 'pytest run with cwd=<ROOT>; regenerable (proposal: pytest cache_dir under SCRATCH)', 'remove-approval'))
    if '.queue.lock' in names:
        out.append(_mv(root / '.queue.lock', None, 'cache', None, 'stale: tools/work_queue.py locks <ROOT>/leases/.queue.lock', 'remove-approval'))
    return out


def root_other(cfg):
    """[(entry, proposed home)] for each ROOT child that is not a documented atlas_paths slot."""
    slots = {Path(str(v)).relative_to(cfg['ROOT']).parts[0] for k, v in P._P.items()
             if str(v).startswith(str(cfg['ROOT']) + os.sep) and k not in ('ENV_PY', 'ENV_LIB')} | {'schools', 'stores'}
    proposal = {'worktrees': 'keep; add a WORKTREES slot (documented in CONTRIBUTING, used by tools/agent_worktree.sh)',
                'site-worktrees': 'keep; add a SITE_WORKTREES slot; the three loose site-* checkouts join it',
                'hierarchy': 'remove once empty (a job ran with cwd=<ROOT>); logs go to SLURM_LOGS',
                '.pytest_cache': 'remove; set pytest cache_dir under SCRATCH',
                '.queue.lock': 'remove (stale lock of an earlier work_queue.py)',
                'x': 'remove (empty)', 'site-host-update-1115': 'remove (empty)'}
    return [(n, proposal.get(n, 'owner decides')) for n in R._listdir(cfg['ROOT'])
            if not (n in slots or SLURM_OUT.match(n) or n in SITE_LOOSE)]


def worktree_facts(root):
    """{path: [porcelain lines]} from `git -C site worktree list --porcelain` (one call); empty when site/ is not a repository."""
    r = subprocess.run(['git', '-C', str(root / 'site'), 'worktree', 'list', '--porcelain'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    out, cur = {}, None
    for line in r.stdout.decode().splitlines():
        if line.startswith('worktree '):
            cur = line[9:]
            out[cur] = []
        elif cur and line:
            out[cur].append(line)
    return out


def check_plan(entries):
    """Conflicts: destination exists, cross-device, duplicate destinations, symlink sources."""
    conflicts, seen = [], {}
    moves = [e for e in entries if e['kind'] in ('rename', 'git-mv', 'git-worktree-move')]
    for e in entries:
        if e['kind'] == 'conflict':
            conflicts.append(f"{e['old']}: {e['note']}")
    for e in moves:
        old, new = e['old'], e['new']
        if new in seen:
            conflicts.append(f'{old}: same destination as {seen[new]} ({new})')
        seen[new] = old
        if R._exists(new):
            conflicts.append(f'{old}: destination exists: {new}')
        if os.path.islink(old) and e['kind'] == 'rename':
            conflicts.append(f'{old}: source is a symlink (move its target instead)')
        if e['kind'] == 'rename':
            try:
                if R._dev(old) != R._dev(new):
                    conflicts.append(f'{old}: cross-device move to {new} (not a rename)')
            except OSError as x:
                conflicts.append(f'{old}: cannot stat ({x})')
    for e in entries:
        if e['kind'] == 'link' and R._exists(e['old']):
            conflicts.append(f"{e['old']}: the permanent link would replace an existing path")
    return conflicts


def order(entries):
    """mkdirs (parents first), then renames, git worktree moves, git mv, the links."""
    mk = {e['new']: e for e in entries if e['kind'] == 'mkdir'}
    for e in entries:
        if e['kind'] in ('rename', 'git-worktree-move', 'link', 'git-mv') and e['new']:
            p = str(Path(e['new']).parent)
            while p not in ('/', '.') and not R._exists(p) and p not in mk:
                mk[p] = _mv(None, p, 'mkdir', None, 'new directory', 'mkdir')
                p = str(Path(p).parent)
    renamed = {e['new'] for e in entries if e['kind'] == 'rename'}
    mkdirs = sorted((m for m in mk.values() if m['new'] not in renamed), key=lambda e: R.depth(e['new']))
    rank = {'rename': 1, 'git-worktree-move': 2, 'git-mv': 3, 'link': 4}
    rest = sorted([e for e in entries if e['kind'] in rank], key=lambda e: (rank[e['kind']], R.depth(e['new'] or ''), e['group'], e['school'] or '', e['old'] or ''))
    return mkdirs + rest


def preflight(entries, cfg):
    sources = [e['old'] for e in entries if e['kind'] in ('rename', 'git-worktree-move') and e['old']]
    busy = R.busy_processes(sources)
    locks = R.store_locks([str(cfg['STORES'])])
    f = cfg['ROOT'] / '.queue.lock'
    if os.path.isfile(f):
        try:
            locks[str(f)] = R.lock_held(str(f))
        except OSError:
            locks[str(f)] = True
    return busy, locks


def squeue_jobs():
    """This user's queued/running jobs (one squeue call; a live job may hold paths on another node, which /proc cannot see)."""
    try:
        r = subprocess.run(['squeue', '-u', os.environ.get('USER', ''), '-h', '-o', '%i|%j|%T|%R'], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return [ln for ln in r.stdout.decode().splitlines() if ln]


def per_school_table(entries, schools):
    have = {s: {} for s in schools}
    for e in entries:
        if e['school'] in have and e['kind'] in ('rename', 'git-mv', 'link'):
            have[e['school']][e['group']] = have[e['school']].get(e['group'], 0) + 1
    return have


def show(entries, conflicts, schools, cfg, pre, jobs, wt, out=print):
    root = cfg['ROOT']

    def rel(p):
        p = str(p)
        return '<ROOT>/' + p[len(str(root)) + 1:] if p.startswith(str(root) + os.sep) else p
    ordered = order(entries)
    out(f'== school-layout plan: root {root}; {len(schools)} schools; nothing was moved or written')
    out('== 1. directories to create')
    n_mk = 0
    for e in ordered:
        if e['kind'] == 'mkdir':
            n_mk += 1
            out(f"  mkdir   {rel(e['new'])}")
    out('== 2. moves, in order (os.rename; git-mv and git-worktree-move are marked)')
    n = 0
    for e in ordered:
        if e['kind'] in ('rename', 'git-mv', 'git-worktree-move'):
            n += 1
            tag = '' if e['kind'] == 'rename' else f"[{e['kind']}] "
            who = '/' + e['school'] if e['school'] else ''
            out(f"  {n:4d}. {tag}{rel(e['old'])}\n         -> {rel(e['new'])}   [{e['group']}{who}{'; ' + e['note'] if e['note'] else ''}]")
    out('== 3. the one permanent link (OWNER SIGN-OFF): schools/<s>/reviewed -> code/hierarchy/<s>/reviewed')
    links = [e for e in ordered if e['kind'] == 'link']
    for e in links:
        out(f"  link    {rel(e['old'])} -> {e['new']}")
    out('== 4. tracked in git, stays where it is (not moved by this plan)')
    stay = [e for e in entries if e['kind'] == 'stay-tracked']
    for e in sorted(stay, key=lambda e: e['old']):
        out(f"  stay    {rel(e['old'])}   [{e['group']}/{e['school']}]")
    out('== 5. leftovers directly under hierarchy/<school> that no rule maps (untracked ones now move to schools/<s>/work/, section 2; owner decision 4)')
    left = [e for e in entries if e['kind'] == 'leftover']
    for e in left:
        out(f"  leftover {rel(e['old'])}   {e['note']}")
    out('== 6. project-root tidy-up: remove (owner approval) -- listed, never executed')
    rem = [e for e in entries if e['kind'] == 'remove-approval']
    for e in rem:
        out(f"  remove  {rel(e['old'])}   {e['note']}")
    out('== 7. other ROOT entries that are not documented atlas_paths slots')
    oth = root_other(cfg)
    for name, prop in oth:
        out(f'  {name:24s} {prop}')
    out('== 8. site worktrees (git facts from `git -C site worktree list --porcelain`)')
    for e in entries:
        if e['kind'] == 'git-worktree-move':
            what = 'registered worktree of site/' if e['old'] in wt else 'NOT a registered worktree: plain rename needed'
            out(f"  {e['old']}: {what} {' '.join(wt.get(e['old'], []))}")
    for path, facts in wt.items():
        if any('prunable' in f for f in facts):
            out(f'  prunable worktree record (path missing): {path}  -> `git -C site worktree prune` (owner approval)')
    out(f'== 9. conflicts: {len(conflicts)}')
    for c in conflicts:
        out(f'  CONFLICT {c}')
    busy, locks = pre
    out(f'== 10. preflight for --apply: {len(busy)} busy processes of this user on this host, {sum(locks.values())} of {len(locks)} lock files held')
    for pid, what, path in busy[:40]:
        out(f'  busy pid {pid} {what} {path}')
    for f, held in sorted(locks.items()):
        out(f"  lock {'HELD' if held else 'free'} {f}")
    if jobs is None:
        out('  squeue: unavailable (check by hand: a running job holds paths on its node)')
    else:
        out(f'  squeue: {len(jobs)} job(s) of this user queued or running (they read and write these paths; wait for them)')
        for j in jobs[:30]:
            out('    ' + j)
    out('== 11. per-school completeness (moves per group; - = no such source today)')
    have = per_school_table(entries, schools)
    groups = ['derived', 'raw', 'work', 'reports', 'tmp', 'listings', 'store', 'checks', 'captures', 'census', 'periods', 'ai', 'reviewed', 'shared-dir']
    out('  ' + 'school'.ljust(14) + ' '.join(g[:7].ljust(7) for g in groups) + ' leftover')
    for s in schools:
        nl = sum(1 for e in left if e['school'] == s)
        out('  ' + s.ljust(14) + ' '.join(str(have[s].get(g, '-')).ljust(7) for g in groups) + f' {nl}')
    out('  stays elsewhere, for every school: reviewed decisions and tracked reports (git, history, GitHub); the charter code/schools/<s>.toml;')
    out('  releases/<id>/ (immutable dated snapshots, never rewritten); export/ (the public clone of the releases); labs/ and school.json (organize_tree, already')
    out('  under schools/<s>/); site and world-atlas collections (shared builds, not school-owned); ai-scores (one sqlite/parquet for all schools).')
    n_move = sum(1 for e in entries if e['kind'] in ('rename', 'git-mv', 'git-worktree-move'))
    n_school = sum(1 for e in entries if e['kind'] in ('rename', 'git-mv') and e['school'])
    absent = sum(1 for e in entries if e['kind'] == 'absent')
    out(f"== totals: {n_move} moves ({n_school} per-school, {sum(1 for e in entries if e['group'] == 'slurm-logs')} slurm outputs, "
        f"{sum(1 for e in entries if e['kind'] == 'git-worktree-move')} site worktrees, {sum(1 for e in entries if e['kind'] == 'git-mv')} git mv), "
        f"{len(links)} permanent links, {n_mk} mkdirs, {len(stay)} tracked files stay, {len(left)} leftovers, {len(rem)} removals needing approval, "
        f"{len(oth)} undocumented root entries, {len(conflicts)} conflicts, {len(busy)} busy, {sum(locks.values())} locks held, {absent} absent sources")


REFERENCES = [   # (label, ERE)
    ('hierarchy/<school>/', r'hierarchy/(\{school\}|\{s\}|<school>|<s>|\$\{?[A-Za-z_]*[sS]chool[A-Za-z_]*\}?|\$\{?s\}?|\$1|%s)/'),
    ('listings/<school>/', r'listings/(\{school\}|\{s\}|<school>|<s>|\$\{?[A-Za-z_]*[sS]chool\}?|\$\{?s\}?|%s)\b'),
    ('stores/<school>', r'stores?/(\{school\}|\{s\}|<school>|<s>|\$\{?[A-Za-z_]*[sS]chool\}?|\$\{?s\}?)|STORES\s*/|STANFORD_STORE'),
    ('fulltext-push/checks', r'FT_CHECKS|fulltext-push/checks|CS_ATLAS_FT_CHECKS'),
    ('captures/<school>.sqlite', r'captures/(\{school\}|\{s\}|<school>|\$\{?s\}?)|CAPTURES\s*/'),
    ('embeddings / ai-scores', r'EMBEDDINGS\s*/|AI_SCORES\s*/|data/embeddings/|data/ai-scores/'),
    ('slot hand-join', r'\b(HIERARCHY|LISTINGS|CENSUS|PERIODS)\s*/\s*[A-Za-z_(\'"]'),
    ('absolute path', r'/n/fs/resemble/homogenizing-science/(code/)?(hierarchy|listings|stores|schools|census|periods|captures)/'),
]
SKIP_REF = ('tools/atlas_paths.py', 'tools/relocate_schools.py', 'tools/relocate_project.py', 'tools/relocate_data.py',
            'tests/test_relocate_schools.py', 'tests/test_atlas_paths_school_layout.py', 'tests/test_relocate_data.py', 'tests/test_relocate_project.py')


def kind_of(path):
    if path.startswith('docs/') or path.endswith('.md'):
        return 'docs'
    if path.startswith('tests/'):
        return 'tests'
    if path.endswith(('.slurm', '.sh', '.sbatch')):
        return 'slurm/shell'
    if path.startswith(('vendor/', 'archive/')):
        return 'vendor/archive'
    return 'code'


def references(repo):
    """{(kind, path): {label: n}}: docs, vendor/archive and non-script files by `git grep -nE` per pattern (the index only); live code (.py, .sh,
    .slurm: kinds code, slurm/shell, tests) by tools/route_school_paths.py, which ignores comments and docstrings and honours `route-ok`.
    Files of the second pass (fulltext-push/, ai-writing/, lab-page kits) are labelled 'second pass'."""
    import route_school_paths as RS
    res = {}
    for label, rx in REFERENCES:
        r = subprocess.run(['git', '-C', str(repo), 'grep', '-nIE', rx, '--', '.', ':!docs/relocation', ':!*.json', ':!*.jsonl', ':!*.tsv', ':!*.csv'],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        for line in r.stdout.decode(errors='replace').splitlines():
            path = line.split(':', 1)[0]
            if path in SKIP_REF or (path.endswith(RS.SUFFIXES) and not path.startswith(('vendor/', 'archive/', 'docs/'))):
                continue
            d = res.setdefault((kind_of(path), path), {})
            d[label] = d.get(label, 0) + 1
    for path in RS.tracked(repo):
        if path in SKIP_REF or path.startswith(('vendor/', 'archive/', 'docs/')) or path in RS.ALWAYS:
            continue
        f = Path(repo) / path
        hits = RS.scan_text(path, f.read_text(errors='replace')) if f.is_file() else []
        if hits:
            res[(kind_of(path), path)] = {'second pass' if path.startswith(RS.ALLOW_PREFIXES[len(RS.ALWAYS):]) else 'hand-joined': len(hits)}
    return res


def show_references(res, out=print):
    out('== 12. per-school paths in tracked files that bypass atlas_paths (git grep over the index; one hit = one matching line)')
    by_kind = {}
    for (k, p), d in res.items():
        by_kind.setdefault(k, []).append((p, d))
    for k in ('code', 'slurm/shell', 'tests', 'docs', 'vendor/archive'):
        files = sorted(by_kind.get(k, []), key=lambda t: (-sum(t[1].values()), t[0]))
        out(f'  -- {k}: {sum(sum(d.values()) for _, d in files)} hits in {len(files)} files')
        for p, d in files:
            out(f"    {sum(d.values()):4d}  {p}   " + ', '.join(f'{lab}:{n}' for lab, n in sorted(d.items())))
    out(f'  total {sum(sum(d.values()) for d in res.values())} hits in {len(res)} files')


def apply_plan(entries, cfg, rec, compat=False):
    ordered = order(entries)
    for e in ordered:
        if e['kind'] == 'mkdir' and not os.path.isdir(e['new']):
            os.makedirs(e['new'])
            R.record(rec, op='mkdir', new=e['new'])
    done = []
    for e in ordered:
        if e['kind'] == 'rename':
            if R._dev(e['old']) != R._dev(e['new']):
                raise SystemExit(f"refused: {e['old']} -> {e['new']} crosses filesystems")
            os.rename(e['old'], e['new'])
            R.record(rec, op='rename', old=e['old'], new=e['new'])
            done.append(e)
        elif e['kind'] == 'git-worktree-move':
            subprocess.run(['git', '-C', str(cfg['ROOT'] / 'site'), 'worktree', 'move', e['old'], e['new']], check=True)
            R.record(rec, op='git-worktree-move', old=e['old'], new=e['new'])
        elif e['kind'] == 'git-mv':
            subprocess.run(['git', '-C', str(cfg['CODE']), 'mv', os.path.relpath(e['old'], cfg['CODE']), os.path.relpath(e['new'], cfg['CODE'])], check=True)
            R.record(rec, op='git-mv', old=e['old'], new=e['new'])
        elif e['kind'] == 'link':
            os.symlink(e['new'], e['old'])
            R.record(rec, op='permanent-link', link=e['old'], target=e['new'])
    if compat:   # temporary links at the old paths, recorded for relocate_project.py --remove-compat
        for e in sorted(done, key=lambda e: R.depth(e['old'])):
            if os.path.isdir(os.path.dirname(e['old'])) and not os.path.lexists(e['old']):
                os.symlink(e['new'], e['old'])
                R.record(rec, op='compat-link', link=e['old'], real=os.path.join(os.path.realpath(os.path.dirname(e['old'])), os.path.basename(e['old'])), target=e['new'])


def build(cfg=None, schools=None, ai=True, tracked=None):
    cfg = layout_of(cfg)
    schools = schools or school_keys()
    if tracked is None:
        tracked = tracked_files(cfg['CODE'], ['hierarchy', 'listings', 'captures', 'census', 'periods'])
    entries = []
    for s in schools:
        entries += plan_school(s, cfg, tracked, ai)
    entries += plan_root(cfg)
    return cfg, schools, entries


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--school', action='append', default=[])
    ap.add_argument('--no-ai', action='store_true')
    ap.add_argument('--references', action='store_true')
    ap.add_argument('--index-of', metavar='REPO', help='read the tracked files and the references from this checkout\'s git index (a branch worktree) instead of the main checkout\'s')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--compat-links', action='store_true')
    a = ap.parse_args(argv)
    tracked = tracked_files(a.index_of, ['hierarchy', 'listings', 'captures', 'census', 'periods']) if a.index_of else None
    cfg, schools, entries = build(schools=a.school or None, ai=not a.no_ai, tracked=tracked)
    conflicts = check_plan(entries)
    pre = preflight(entries, cfg)
    show(entries, conflicts, schools, cfg, pre, squeue_jobs(), worktree_facts(cfg['ROOT']))
    if a.references:
        show_references(references(a.index_of or cfg['CODE']))
    if not a.apply:
        print('== dry run: nothing was moved or written')
        return 1 if conflicts else 0
    busy, locks = pre
    if conflicts or busy or any(locks.values()):
        print('refused: conflicts, busy processes or held lock files (above)')
        return 2
    rec = cfg['MIGRATIONS'] / f'school-layout-{datetime.date.today().isoformat()}.jsonl'
    apply_plan(entries, cfg, rec, compat=a.compat_links)
    print(f'applied; record: {rec}. Next: DATA_LAYOUT_DEFAULT = "school", regenerate paths.sh, re-measure the gates (SCHOOL-LAYOUT-PLAN.md).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
