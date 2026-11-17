"""queued_oa_fill: candidates for catalog works that are 'queued' with no candidate and no attempt, from the LOCAL OpenAlex snapshot
(no API credits). The lab-paper channels (oa_arxiv, openalex) plan only the lab papers (lab_channels.plan_for); the catalogs also hold
tens of thousands of other queued works (the oa-expand batches) that no channel ever looks at (measured 2026-11-16: CMU 43,692 queued
vs 6,393 planned lab papers).

Per work: the snapshot record by OpenAlex id (from the work id <school>_oa_W...) or by exact DOI, in one sequential pass over the
snapshot for all requested schools; then the standard rules: ftp_common.arxiv_of -> the arXiv bulk copy (ftp_common.bulk_rows),
ftp_common.oa_location_rows -> open locations. Identity stays with the collector's page-1 rule at download time.

Safety:
  * DRY by default: reads catalogs read-only and writes nothing except, with --json, the counts file.
  * --write is explicit, needs --backup-dir holding a backup file of every school named (catalog-backup-<school>-*.sqlite, at most
    12 h old, a readable catalog with a works table), and refuses a school whose <store>/.catalog-write.lock is held right now.
  * The only SQL it issues against a catalog is INSERT OR IGNORE INTO candidates (ftp_common.write_candidates: batches of 100
    under the catalog write lock); works, attempts, status and downloads are never touched. A rerun adds nothing (works that already
    have a candidate or an attempt are not planned).
usage: queued_oa_fill.py <school>[,<school>...] [--json FILE] [--write --backup-dir DIR]
       queued_oa_fill.py <schools> --plan-file PLAN.json.gz [--json COUNTS]      one read-only scan for all schools, rows saved
       queued_oa_fill.py <schools> --apply-plan PLAN.json.gz --write --backup-dir DIR [--lock-wait 2700]   per school, wait for the lock
"""
import argparse
import collections
import fcntl
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402

BACKUP_MAX_AGE = 12 * 3600
SOURCE = 'queued_oa'


def queued(school, path=None):
    """[(work id, doi)] of queued works with no candidate and no attempt (read-only)."""
    path = path or F.FT / school / 'catalog.sqlite'
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=120)
    try:
        rows = db.execute("SELECT id, doi FROM works WHERE status='queued'").fetchall()
        have = {r[0] for r in db.execute('SELECT DISTINCT work_id FROM candidates')}
        have |= {r[0] for r in db.execute('SELECT DISTINCT work_id FROM attempts')}
    finally:
        db.close()
    return [r for r in rows if r[0] not in have]


def wanted_keys(plan):
    """{OpenAlex id URL | doi URL (lower case): [(school, work)]} for the plan {school: [(id, doi)]}."""
    want = collections.defaultdict(list)
    for s, rows in plan.items():
        for i, d in rows:
            if '_oa_W' in i:
                want['https://openalex.org/' + i.split('_oa_')[-1]].append((s, i))
            if d:
                want['https://doi.org/' + F.ndoi(d)].append((s, i))
    return want


def snapshot_bodies(want):
    """{(school, work): snapshot record}: one sequential pass per store over (rowid, id, doi), bodies read only for the matches."""
    import oa_snapshot as OS
    bodies = {}
    for db, _d in [OS.conn()] + OS.exts():
        hits = []
        for rid, i, doi in db.execute('SELECT rowid, id, doi FROM works'):
            if i in want or (doi and doi.lower() in want):
                hits.append((rid, i, (doi or '').lower()))
        for rid, i, doi in hits:
            w = OS.unpack(db.execute('SELECT body FROM works WHERE rowid=?', (rid,)).fetchone()[0])
            for k in want.get(i, []) + want.get(doi, []):
                bodies.setdefault(k, w)
    return bodies


def pmc_open_data_rows(want):
    """{work: {pmcid digits}} -> PMC open-data candidate rows (ftp_common.pmc_rows: the bucket's PDF / JATS XML per PMCID, 1 s per listing;
    no OpenAlex credits). A PMCID outside the bucket gives no row."""
    import requests
    s = requests.Session()
    s.headers['User-Agent'] = F.UA
    memo, rows = {}, []
    for w, ids in want.items():
        rows += F.pmc_rows(w, ids, memo, s)
    return rows


def build_rows(school, plan_rows, bodies, bulk=None, pmc_rows=None):
    """-> (candidate rows, Counter). bulk(want {work: arxiv id}) -> (rows, n_not_in_bulk); default ftp_common.bulk_rows.
    pmc_rows(want {work: {pmcid}}) -> rows for works whose open location is a PMC link and who have no other candidate (the 'pmc_only'
    works, 2026-11-17); None = counted only."""
    bulk = bulk or (lambda want: F.bulk_rows(want, 'openalex_arxiv_bulk'))
    n = collections.Counter(queued=len(plan_rows))
    doi_of = dict(plan_rows)
    arx, rows, pmc_want = {}, [], {}
    for (sc, i), w in bodies.items():
        if sc != school:
            continue
        n['in_snapshot'] += 1
        a = F.arxiv_of(dict(doi=doi_of.get(i)), w)
        r, pmc = F.oa_location_rows(i, w)
        if a:
            arx[i] = a
        rows += r
        n['loc_work'] += bool(r)
        n['pmc_only'] += bool(pmc and not r and not a)
        if pmc and not r and not a:
            pmc_want[i] = pmc
    arows, missing = bulk(arx) if arx else ([], 0)
    rows += arows
    n['arxiv_ids'] = len(arx)
    n['arxiv_rows'] = len(arows)
    n['arxiv_not_in_bulk'] = missing
    if pmc_rows and pmc_want:
        prows = pmc_rows(pmc_want)
        n['pmc_rows'] = len(prows)
        n['pmc_works'] = len({r['work_id'] for r in prows})
        rows += prows
    rows = list({(r['work_id'], r['url']): r for r in rows}.values())
    n['rows'] = len(rows)
    n['works_with_candidate'] = len({r['work_id'] for r in rows})
    return rows, n


def backup_time(p):
    """When the backup was taken: the UTC stamp in its name (catalog-backup-<school>-YYYYMMDDTHHMMSSZ.sqlite; `cp -p` keeps the source's old
    mtime), else the file's mtime."""
    import re
    from datetime import datetime, timezone
    m = re.search(r'-(\d{8}T\d{6})Z\.sqlite$', Path(p).name)
    if m:
        return datetime.strptime(m.group(1), '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc).timestamp()
    return Path(p).stat().st_mtime


def check_backup(school, backup_dir, now=None):
    """The newest catalog-backup-<school>-*.sqlite in backup_dir, or raise SystemExit: it must be fresh and a readable catalog."""
    now = now or time.time()
    files = sorted(Path(backup_dir).glob(f'catalog-backup-{school}-*.sqlite'), key=lambda p: (backup_time(p), p.name)) if backup_dir else []
    if not files:
        raise SystemExit(f'{school}: no catalog-backup-{school}-*.sqlite in {backup_dir}; refusing to write')
    b = files[-1]
    if now - backup_time(b) > BACKUP_MAX_AGE:
        raise SystemExit(f'{school}: newest backup {b} is older than {BACKUP_MAX_AGE // 3600} h; refusing to write')
    try:
        db = sqlite3.connect(f'file:{b}?mode=ro', uri=True)
        db.execute('SELECT 1 FROM works LIMIT 1').fetchone()
        db.close()
    except sqlite3.Error as e:
        raise SystemExit(f'{school}: backup {b} is not a readable catalog ({e}); refusing to write')
    return b


def check_no_writer(school, wait=0, poll=2):
    """Refuse while another process holds the catalog write lock (a loop or tool is writing right now). The collector's lock is short
    (one saved result), so with wait > 0 the probe is repeated every 2 s for up to `wait` seconds before refusing."""
    p = F.FT / school / '.catalog-write.lock'
    if not p.exists():
        return
    fd = os.open(str(p), os.O_RDWR)
    end = time.monotonic() + wait
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= end:
                    raise SystemExit(f'{school}: the catalog write lock is held right now (a loop write in progress); refusing to write')
                time.sleep(poll)
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def write_rows(school, rows, ev_dir=None):
    """INSERT OR IGNORE candidates only (ftp_common.write_candidates). -> rows added."""
    import lab_channels as L
    ev_dir = ev_dir or F.FT / school / 'discovery' / f'claude-{school}-queued-oa' / 'evidence'
    return L.write(school, rows, SOURCE, ev_dir=ev_dir)


def run(schools, write=False, backup_dir=None, json_out=None, ev_dir=None, plan=None, bodies=None, bulk=None, log=True, lock_wait=120):
    if write:
        for s in schools:
            check_backup(s, backup_dir)
    plan = plan if plan is not None else {s: queued(s) for s in schools}
    if bodies is None:
        bodies = snapshot_bodies(wanted_keys(plan))
    out = {}
    for s in schools:
        rows, n = build_rows(s, plan[s], bodies, bulk)
        added = 0
        if write and rows:
            check_no_writer(s, lock_wait)
            added = write_rows(s, rows, ev_dir)
        n['written'] = added
        out[s] = dict(n)
        print(json.dumps(dict(at=F.now(), school=s, step='queued_oa_fill', write=write, **n)), flush=True)
        if write and log:
            with open(F.P.FT_LOGS / 'channels.jsonl', 'a') as f:
                f.write(json.dumps(dict(at=F.now(), school=s, step='queued_oa_fill', missing_in_catalog=n['queued'], applies=n['in_snapshot'],
                                        rows=n['rows'], works=n['works_with_candidate'], candidates_added=added, results={})) + '\n')
        if json_out:
            Path(json_out).write_text(json.dumps(out, indent=1))
    return out


def make_plan(schools, plan_file, json_out=None, plan=None, bodies=None, bulk=None, pmc_rows=None):
    """The read-only half: one snapshot scan for all schools; saves {school: {counts, rows}} to plan_file (gzip JSON). No catalog lock is
    taken and nothing is written to a catalog."""
    import gzip
    plan = plan if plan is not None else {s: queued(s) for s in schools}
    if bodies is None:
        bodies = snapshot_bodies(wanted_keys(plan))
    saved, counts = {}, {}
    for s in schools:
        rows, n = build_rows(s, plan[s], bodies, bulk, pmc_rows)
        saved[s] = dict(counts=dict(n), rows=rows)
        counts[s] = dict(n)
        print(json.dumps(dict(at=F.now(), school=s, step='queued_oa_plan', **n)), flush=True)
    meta = dict(made_at=F.now(), schools=saved)
    tmp = Path(str(plan_file) + '.part')
    with gzip.open(tmp, 'wt') as f:
        json.dump(meta, f)
    os.replace(tmp, plan_file)
    if json_out:
        Path(json_out).write_text(json.dumps(counts, indent=1))
    return counts


def integrity_ok(school):
    db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    try:
        return db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    finally:
        db.close()


def apply_plan(plan_file, schools, backup_dir, lock_wait=2700, poll=15, passes=2, json_out=None, ev_dir=None, log=True, check=integrity_ok):
    """The write half: per school, in the given order, wait (polling every `poll` s, up to `lock_wait` s) for the catalog write lock to be
    free, then write the planned rows that are still wanted (the work is still queued with no candidate and no attempt), INSERT OR IGNORE
    candidates only, then integrity_check. A school whose lock never frees is skipped and retried in the next pass. A fresh backup named for
    each school is required before anything is written."""
    import gzip
    with gzip.open(plan_file, 'rt') as f:
        saved = json.load(f)['schools']
    for s in schools:
        check_backup(s, backup_dir)
    done, todo = {}, list(schools)
    for _pass in range(passes):
        skipped = []
        for s in todo:
            try:
                check_no_writer(s, lock_wait, poll)
            except SystemExit as e:
                print(json.dumps(dict(at=F.now(), school=s, step='queued_oa_apply', skipped=str(e))), flush=True)
                skipped.append(s)
                continue
            check_backup(s, backup_dir)
            still = {i for i, _ in queued(s)}
            rows = [r for r in saved.get(s, {}).get('rows', []) if r['work_id'] in still]
            added = write_rows(s, rows, ev_dir) if rows else 0
            done[s] = dict(planned=len(saved.get(s, {}).get('rows', [])), still_wanted=len(rows), written=added, integrity=bool(check(s)))
            print(json.dumps(dict(at=F.now(), school=s, step='queued_oa_apply', **done[s])), flush=True)
            if log:
                with open(F.P.FT_LOGS / 'channels.jsonl', 'a') as f:
                    f.write(json.dumps(dict(at=F.now(), school=s, step='queued_oa_fill', missing_in_catalog=saved.get(s, {}).get('counts', {}).get('queued', 0),
                                            applies=saved.get(s, {}).get('counts', {}).get('in_snapshot', 0), rows=len(rows),
                                            works=len({r['work_id'] for r in rows}), candidates_added=added, results={})) + '\n')
            if json_out:
                Path(json_out).write_text(json.dumps(dict(done=done, skipped=skipped), indent=1))
        todo = skipped
        if not todo:
            break
    if json_out:
        Path(json_out).write_text(json.dumps(dict(done=done, skipped=todo), indent=1))
    return done, todo


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('schools')
    ap.add_argument('--write', action='store_true', help='write candidate rows (default: dry, counts only)')
    ap.add_argument('--backup-dir', help='directory with catalog-backup-<school>-*.sqlite (required with --write)')
    ap.add_argument('--json', help='write the per-school counts here')
    ap.add_argument('--plan-file', help='read-only: scan once for all schools and save the candidate rows here (no catalog is touched)')
    ap.add_argument('--apply-plan', help='write the rows of this plan file school by school (needs --write and --backup-dir)')
    ap.add_argument('--lock-wait', type=int, default=2700, help='seconds to wait per school for the catalog write lock (apply-plan)')
    a = ap.parse_args(argv)
    if a.plan_file:
        make_plan(a.schools.split(','), a.plan_file, a.json, pmc_rows=pmc_open_data_rows)
        return
    if a.apply_plan:
        if not a.write:
            raise SystemExit('--apply-plan writes candidates: pass --write explicitly')
        apply_plan(a.apply_plan, a.schools.split(','), a.backup_dir, lock_wait=a.lock_wait, json_out=a.json)
        return
    run(a.schools.split(','), write=a.write, backup_dir=a.backup_dir, json_out=a.json)


if __name__ == '__main__':
    main()
