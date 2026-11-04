"""Refresh the local OpenAlex snapshot (ROADMAP #24; docs/OPENALEX-SNAPSHOT.md section 14).

A newer snapshot date on the public bucket is streamed and filtered (oa_snapshot.py, the same 16 tasks and merge) into a NEW dated store
OA_SNAPSHOT/<date>/. The store `current` points at is never rewritten. A compare job writes <new>/refresh-compare.json (works per school,
old vs new). `current` moves only with `promote` (the --promote flag of `submit`/`auto`), and only when the compare report is clean.

  oa_snapshot_refresh.py plan   [--date D]                 what a refresh would do (one manifest request, nothing written)
  oa_snapshot_refresh.py submit [--date D] [--promote] [--dry-run]   filter array -> merge (--no-promote) -> compare [-> promote]
  oa_snapshot_refresh.py auto   [--promote]                submit when the bucket has a newer date than `current`, else say so (the monthly job)
  oa_snapshot_refresh.py compare --date D                  per-school work counts, current vs <D>, written next to the new store
  oa_snapshot_refresh.py promote --date D [--force]        point `current` at <D> (needs the compare report; refuses a school that lost > 5%)
Also: `atlas pipeline snapshot-refresh ...`. Extensions (`ext-<key>.sqlite` beside the current store) are folded in by the charters: the new
filter reads every charter in schools/*.toml, so an extension school must have its charter on main first (`plan` blocks otherwise).
"""
import argparse, json, os, sqlite3, subprocess, sys, time
from pathlib import Path

import atlas_paths as P  # noqa: E402
import oa_snapshot as S  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
MAX_LOSS = 0.05   # a school whose work count falls by more than this blocks the promotion


def current_date(root=None):
    return S.snapshot_date(root)


def extensions(root=None, date=None):
    """School keys that have an extension store beside the current main store."""
    root = Path(root or P.OA_SNAPSHOT)
    d = date or current_date(root)
    return sorted(p.name[len('ext-'):-len('.manifest.json')] for p in (root / d).glob('ext-*.manifest.json')) if d else []


def latest(manifest=None):
    """The newest snapshot date on the bucket (the works manifest's date)."""
    return (manifest or S.manifest)('works')[0]


def plan(date=None, root=None, manifest=None, charters=None):
    root = Path(root or P.OA_SNAPSHOT)
    cur = current_date(root)
    new = date or latest(manifest)
    if charters is None:
        import school_config as SC
        charters = SC.keys()
    ext = extensions(root, cur)
    unchartered = [k for k in ext if k not in charters]
    if cur and new <= cur:
        status = 'up-to-date'
    elif (root / new / 'openalex.sqlite').exists():
        status = 'exists'            # never in place: a store of that date is already there
    elif unchartered:
        status = 'blocked'
    else:
        status = 'refresh'
    return dict(current=cur, latest=new, status=status, new_store=str(root / new), schools=list(charters), extensions=ext,
                extensions_without_charter=unchartered, filter_tasks=16)


def _store_counts(db, ids):
    q = ','.join('?' * len(ids))
    return db.execute(f'SELECT COUNT(DISTINCT work_id) FROM work_inst WHERE inst IN ({q})', list(ids)).fetchone()[0]


def _open(path):
    return sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=60)


def compare(new, root=None, sweep_ids=None, schools=None):
    """Works per school in the current store (plus its ext-*.sqlite) and in <new>; written to <new>/refresh-compare.json."""
    root = Path(root or P.OA_SNAPSHOT)
    cur = current_date(root)
    if sweep_ids is None:
        import school_config as SC
        schools = schools or SC.keys()
        sweep_ids = lambda k: SC.sweep_ids(k)  # noqa: E731
    old_dbs = [_open(root / cur / 'openalex.sqlite')] + [_open(p) for p in sorted((root / cur).glob('ext-*.sqlite'))]
    new_db = _open(root / new / 'openalex.sqlite')
    rows = []
    for k in schools:
        ids = list(sweep_ids(k))
        # a work held by the main store and an extension counts once: union of ids over the old files
        q = ','.join('?' * len(ids))
        seen = set()
        for db in old_dbs:
            seen |= {r[0] for r in db.execute(f'SELECT work_id FROM work_inst WHERE inst IN ({q})', ids)}
        o, n = len(seen), _store_counts(new_db, ids)
        rows.append(dict(school=k, old=o, new=n, ratio=round(n / o, 4) if o else None, loss=bool(o and n < o * (1 - MAX_LOSS))))
    rep = dict(current=cur, new=new, made_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), schools=rows,
               ok=not any(r['loss'] for r in rows))
    (root / new / 'refresh-compare.json').write_text(json.dumps(rep, indent=1))
    return rep


def promote(new, root=None, force=False):
    root = Path(root or P.OA_SNAPSHOT)
    rep_path = root / new / 'refresh-compare.json'
    if not (root / new / 'openalex.sqlite').exists():
        raise SystemExit(f'no store for {new}')
    if not rep_path.exists():
        raise SystemExit(f'run compare first: {rep_path} is missing')
    rep = json.loads(rep_path.read_text())
    if not rep['ok'] and not force:
        bad = [r['school'] for r in rep['schools'] if r['loss']]
        raise SystemExit(f'not promoted: {bad} lost more than {MAX_LOSS:.0%} of their works against {rep["current"]} (read the report; --force to override)')
    cur = root / 'current'
    tmp = root / 'current.new'
    tmp.unlink(missing_ok=True)
    tmp.symlink_to(new)
    os.replace(tmp, cur)       # atomic: readers see the old or the new store, never none
    return rep


def submit(date, do_promote=False, dry_run=False, run=subprocess.run, root=None, manifest=None, charters=None):
    """The chain as sbatch calls through `atlas submit`: filter array -> merge (--no-promote) -> compare -> promote (only if asked)."""
    pl = plan(date, root, manifest, charters)
    if pl['status'] != 'refresh':
        return pl, []
    d = pl['latest']
    env = dict(os.environ, OA_DATE=d, OA_NO_PROMOTE='1')
    atlas = str(CODE / 'bin' / 'atlas')
    chain = [('filter', [atlas, 'submit', '--parsable', str(CODE / 'tools' / 'oa_snapshot.slurm')]),
             ('merge', [atlas, 'submit', '--parsable', '--dependency=afterok:{prev}', str(CODE / 'tools' / 'oa_snapshot_merge.slurm')]),
             ('compare', [atlas, 'submit', '--parsable', '--dependency=afterok:{prev}', str(CODE / 'tools' / 'oa_snapshot_refresh.slurm'), 'compare'])]
    if do_promote:
        chain.append(('promote', [atlas, 'submit', '--parsable', '--dependency=afterok:{prev}', str(CODE / 'tools' / 'oa_snapshot_refresh.slurm'), 'promote']))
    jobs, prev, shown = {}, None, []
    for name, argv in chain:
        argv = [a.replace('{prev}', prev or '') for a in argv]
        shown.append((name, argv))
        if dry_run:
            prev = f'<{name}>'
            continue
        r = run(argv, capture_output=True, text=True, env=dict(env, OA_REFRESH_DATE=d), cwd=str(CODE))
        if r.returncode:
            raise SystemExit(f'submit failed at {name}: {(r.stderr or r.stdout).strip()[:300]}')
        prev = r.stdout.strip().splitlines()[-1].split(';')[0]
        jobs[name] = prev
    return dict(pl, jobs=jobs), shown


def main(argv=None, run=subprocess.run, manifest=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['plan', 'submit', 'auto', 'compare', 'promote'])
    ap.add_argument('--date'); ap.add_argument('--promote', action='store_true'); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'plan':
        print(json.dumps(plan(a.date, manifest=manifest), indent=1))
    elif a.cmd in ('submit', 'auto'):
        if a.cmd == 'auto' and os.environ.get('OA_REFRESH_PROMOTE') == '1':
            a.promote = True
        pl, shown = submit(a.date, a.promote, a.dry_run, run=run, manifest=manifest)
        print(json.dumps({k: v for k, v in pl.items() if k != 'schools'}, indent=1))
        for name, cmd in shown:
            print(('would submit ' if a.dry_run else 'submitted ') + name + ': ' + ' '.join(cmd))
        if pl['status'] == 'blocked':
            return 1
    elif a.cmd == 'compare':
        rep = compare(a.date or os.environ['OA_REFRESH_DATE'])
        print(json.dumps(rep, indent=1))
        return 0 if rep['ok'] else 1
    else:
        rep = promote(a.date or os.environ['OA_REFRESH_DATE'], force=a.force)
        print(f'current -> {rep["new"]} (was {rep["current"]})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
