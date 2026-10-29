"""Local-reuse harvest, passes 3-4 (2026-10-29): build the inventory, propose copies, and import the ones that pass the
collector's own identity check.

plan     inventory.sqlite
           pdfs       every PDF the find pass listed (identify.py rows): path, source folder, bytes, sha256, pages, DOIs
                      and arXiv id on page 1 / in the metadata, first-page title, the catalogs already holding the same
                      sha256 (in_store), the match candidates, and (after import) the work it now serves
           proposals  (school, work) <- a file, from two origins:
                        disk           identify.py matches (rule doi / title / doi+title)
                        cross_catalog  a PDF another school's catalog already accepted (status downloaded) for a work
                                       with the same DOI (or one of the paper's edition DOIs), or the same normalized
                                       title (>= 20 characters) and a year within 1
import   per (school, work) still without a copy, proposals in order (doi+title, doi, title; cross-catalog before disk):
           1. the file passes the collector's checks, unchanged: collect_princeton_fulltext.validate_pdf (pdfinfo page
              count, written to a scratch copy) and check_identity(work row, file) against the catalog's own title and
              DOI. Only a positive identity is accepted (title_in_first_three_pages, doi_in_first_three_pages,
              title_in_first_page_layout); provider_link_only_review_pending - which the collector accepts for a
              provider link - is NOT accepted for a local file.
           2. the object goes to data/fulltext/<school>/objects/<sha256>.pdf: a hard link to the source when the
              filesystem allows it (no second copy of the bytes; the source is neither moved nor changed), else a copy
              whose sha256 is verified before it is renamed into place. An existing object of that name is kept.
           3. under the catalog's .collector.lock (taken non-blocking and polled every 10 s, as Princeton's import path
              does, so no collector pass is running and none has the work queued), the rows the collector writes for a
              downloaded copy (save_result): an attempts row (status downloaded, detail JSON with final_url,
              sha256, content_type, metadata_source, format, plus the source path, origin, rule and match evidence),
              an assets row (kind pdf), and the works row's status / file_path / sha256 / byte_count / pages /
              download_url / downloaded_at / identity_check - only when the work is still without a copy. The
              download_url is file://<source path>. One receipt per run: receipts 'local_reuse:<stamp>'.
           Evidence (every accepted row) -> data/fulltext/<school>/discovery/claude-<school>-local-reuse/evidence/
usage: reuse_import.py plan | rematch | import [--dry]   (plan rebuilds the tables; rematch only adds proposals)
"""
import fcntl, gzip, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, '/n/fs/resemble/homogenizing-science/scripts')
import ftp_common as F
from lr_common import SCHOOLS, load_missing, load_stores

INV = HERE / 'inventory.sqlite'
LOCAL = ('downloaded', 'fulltext_xml')
GOOD = {'title_in_first_three_pages', 'doi_in_first_three_pages', 'title_in_first_page_layout'}
RULE_ORDER = {'doi+title': 0, 'doi': 1, 'cross_doi': 0, 'cross_title': 1, 'title': 2, 'title_found': 3}


def now():
    return datetime.now(timezone.utc).isoformat()


def plan():
    missing = load_missing()
    works, shas = load_stores()
    db = sqlite3.connect(str(INV))
    db.executescript('''
      DROP TABLE IF EXISTS pdfs; DROP TABLE IF EXISTS proposals;
      CREATE TABLE pdfs (path TEXT PRIMARY KEY, source_folder TEXT, bytes INTEGER, sha256 TEXT, pages INTEGER, error TEXT,
                         dois TEXT, arxiv TEXT, title_found TEXT, in_store TEXT, match_candidates TEXT,
                         matched_school TEXT, matched_work TEXT, imported INTEGER DEFAULT 0, import_note TEXT);
      CREATE INDEX IF NOT EXISTS pdfs_sha ON pdfs(sha256);
      CREATE TABLE proposals (school TEXT, work_id TEXT, paper_key TEXT, origin TEXT, rule TEXT, src_path TEXT, sha256 TEXT,
                              detail TEXT, outcome TEXT, PRIMARY KEY (school, work_id, src_path));
      CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
    ''')
    n = Counter()
    for f in sorted((HERE / 'ident').glob('shard-*.jsonl.gz')):
        try:
            lines = gzip.open(f, 'rt').read().splitlines()
        except EOFError:
            lines = []
            with gzip.open(f, 'rt') as g:
                try:
                    for l in g:
                        lines.append(l)
                except EOFError:
                    pass
        for l in lines:
            try:
                r = json.loads(l)
            except ValueError:
                continue
            ins = sorted(shas.get(r.get('sha256'), ()))
            db.execute('INSERT OR REPLACE INTO pdfs (path, source_folder, bytes, sha256, pages, error, dois, arxiv, title_found, in_store, match_candidates) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (r['path'], r.get('source_list'), r.get('bytes'), r.get('sha256'), r.get('pages'), r.get('error'), json.dumps(r.get('dois') or []),
                        r.get('arxiv'), r.get('title_found'), json.dumps(ins), json.dumps(r.get('matches') or [])))
            n['pdfs'] += 1
            for m in r.get('matches') or []:
                db.execute('INSERT OR IGNORE INTO proposals VALUES (?,?,?,?,?,?,?,?,NULL)',
                           (m['school'], m['work_id'], m['key'], 'disk', m['rule'], r['path'], r['sha256'], json.dumps(m)))
                n['disk_proposals'] += 1
    by_doi, by_title = defaultdict(list), defaultdict(list)
    for w in works:
        if w['doi']:
            by_doi[w['doi']].append(w)
        k = F.nt(w['title'])
        if len(k) >= 20:
            by_title[k].append(w)
    for r in missing:
        if not r['work_id']:
            continue
        seen = set()
        for d in [r.get('doi')] + (r.get('editions') or []):
            for w in by_doi.get(F.ndoi(d), []) if d else []:
                if w['school'] != r['school'] and w['sha256'] not in seen:
                    seen.add(w['sha256'])
                    db.execute('INSERT OR IGNORE INTO proposals VALUES (?,?,?,?,?,?,?,?,NULL)',
                               (r['school'], r['work_id'], r['key'], 'cross_catalog', 'cross_doi', str(F.FT / w['school'] / w['file_path']), w['sha256'],
                                json.dumps(dict(src_school=w['school'], src_work=w['work_id'], doi=F.ndoi(d)))))
                    n['cross_doi'] += 1
        k = F.nt(r.get('title'))
        for w in by_title.get(k, []) if len(k) >= 20 else []:
            if w['school'] != r['school'] and w['sha256'] not in seen and (not r.get('year') or not w.get('year') or abs(int(w['year']) - int(r['year'])) <= 1):
                seen.add(w['sha256'])
                db.execute('INSERT OR IGNORE INTO proposals VALUES (?,?,?,?,?,?,?,?,NULL)',
                           (r['school'], r['work_id'], r['key'], 'cross_catalog', 'cross_title', str(F.FT / w['school'] / w['file_path']), w['sha256'],
                            json.dumps(dict(src_school=w['school'], src_work=w['work_id'], year=w.get('year')))))
                n['cross_title'] += 1
    n['works_with_proposal'] = db.execute('SELECT COUNT(*) FROM (SELECT DISTINCT school, work_id FROM proposals)').fetchone()[0]
    db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', ('plan', json.dumps(dict(at=now(), **n))))
    db.commit()
    print(json.dumps(dict(n)), flush=True)


def catalog_rows(school, ids):
    db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    db.row_factory = sqlite3.Row
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        for r in db.execute(f'SELECT id, title, doi, year, status FROM works WHERE id IN ({",".join("?" * len(part))})', part):
            out[r['id']] = dict(r)
        time.sleep(0.05)
    db.close()
    return out


def sha_file(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def place(src, dst, sha):
    """The object at data/fulltext/<school>/objects/<sha>.pdf: kept if present, else a hard link, else a verified copy."""
    if dst.exists():
        return 'existing_object'
    try:
        os.link(src, dst)
        return 'hard_link'
    except OSError:
        pass
    tmp = dst.with_name('.' + sha + '.local-reuse.part')
    shutil.copyfile(src, tmp)
    if sha_file(tmp) != sha:
        tmp.unlink()
        raise ValueError('copy checksum mismatch')
    tmp.replace(dst)
    return 'copy'


def check(school, row, src, sha):
    import collect_princeton_fulltext as base
    with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR', '/tmp')) as d:
        p = Path(d) / 'f.pdf'
        data = Path(src).read_bytes()
        if base.sha(data) != sha:
            raise ValueError('source changed since the inventory (sha256 differs)')
        pages = base.validate_pdf(data, p)
        ident = base.check_identity(row, p)
    if ident not in GOOD:
        raise ValueError('identity not positive: ' + ident)
    return pages, ident, len(data)


def write_school(school, accepted, stamp, dry):
    if not accepted:
        return 0
    ev_dir = F.FT / school / 'discovery' / f'claude-{school}-local-reuse' / 'evidence'
    ev = ev_dir / f'local_reuse-{stamp}.json'
    if not dry:
        ev_dir.mkdir(parents=True, exist_ok=True)
        ev.write_text(json.dumps(dict(rule=__doc__, created_at=now(), rows=accepted), indent=0))
    if dry:
        return len(accepted)
    out = F.FT / school
    deadline = time.time() + 20 * 3600
    with (out / '.collector.lock').open('a') as lock:
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); break
            except BlockingIOError:
                if time.time() > deadline:
                    raise
                time.sleep(10)
        db = sqlite3.connect(str(out / 'catalog.sqlite'), timeout=300)
        n = 0
        for i in range(0, len(accepted), 200):
            for a in accepted[i:i + 200]:
                st = db.execute('SELECT status FROM works WHERE id=?', (a['work_id'],)).fetchone()
                if not st or st[0] in LOCAL:
                    a['outcome'] = 'work already has a copy'; continue
                url = 'file://' + a['src_path']
                detail = dict(final_url=url, sha256=a['sha256'], content_type='application/pdf', license_as_listed=None, version_as_listed=None,
                              metadata_source=str(ev), format='pdf', local_reuse=dict(origin=a['origin'], rule=a['rule'], source_path=a['src_path'],
                                                                                       placed=a['placed'], match=a['detail']))
                db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)', (a['work_id'], url, now(), 'downloaded', json.dumps(detail, sort_keys=True)))
                db.execute('INSERT OR REPLACE INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                           (a['work_id'], 'pdf', url, a['file_path'], a['sha256'], a['bytes'], None, None, str(ev), now(), a['identity']))
                db.execute("UPDATE works SET status='downloaded',file_path=?,sha256=?,byte_count=?,pages=?,download_url=?,downloaded_at=?,identity_check=? WHERE id=? AND status NOT IN ('downloaded','fulltext_xml')",
                           (a['file_path'], a['sha256'], a['bytes'], a['pages'], url, now(), a['identity'], a['work_id']))
                a['outcome'] = 'imported'; n += 1
            db.commit()
        db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)', (f'local_reuse:{stamp}', json.dumps(dict(evidence=str(ev), imported=n, at=now(), tool=str(Path(__file__))))))
        db.commit(); db.close()
    return n


def do_import(dry=False):
    inv = sqlite3.connect(str(INV), timeout=60)
    props = defaultdict(list)
    for row in inv.execute('SELECT school, work_id, paper_key, origin, rule, src_path, sha256, detail FROM proposals WHERE outcome IS NULL'):
        props[(row[0], row[1])].append(dict(zip(('school', 'work_id', 'key', 'origin', 'rule', 'src_path', 'sha256', 'detail'), row)))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    n = Counter()
    pending = {}
    for school in SCHOOLS:
        ws = [w for s, w in props if s == school]
        rows = catalog_rows(school, ws)
        accepted = []
        for w in ws:
            row = rows.get(w)
            if not row or row['status'] in LOCAL:
                n[school + ':already_local_or_gone'] += 1; continue
            ok = None
            for p in sorted(props[(school, w)], key=lambda p: (RULE_ORDER.get(p['rule'], 9), p['origin'] != 'cross_catalog')):
                try:
                    pages, ident, size = check(school, row, p['src_path'], p['sha256'])
                    fp = f'objects/{p["sha256"]}.pdf'
                    p['placed'] = 'dry' if dry else place(p['src_path'], F.FT / school / fp, p['sha256'])
                    ok = dict(p, pages=pages, identity=ident, bytes=size, file_path=fp, detail=json.loads(p['detail']))
                    break
                except Exception as e:
                    p['outcome'] = 'rejected: ' + str(e)[:150]
                    n[school + ':rejected:' + re.sub(r'\d+', 'N', str(e)[:40])] += 1
                    if not dry:
                        inv.execute('UPDATE proposals SET outcome=? WHERE school=? AND work_id=? AND src_path=?', (p['outcome'], school, w, p['src_path']))
            if ok:
                accepted.append(ok); n[f'{school}:accepted:{ok["origin"]}'] += 1
        inv.commit()
        pending[school] = accepted
        print(json.dumps(dict(school=school, works_with_proposal=len(ws), accepted=len(accepted))), flush=True)
    # write each school as soon as its lock is free (one thread per school, so one busy catalog does not hold the rest)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(len(SCHOOLS)) as pool:
        futs = {s: pool.submit(write_school, s, pending[s], stamp, dry) for s in SCHOOLS}
        for s, fu in futs.items():
            try:
                n[s + ':imported'] = fu.result()
            except Exception as e:
                n[s + ':write_failed'] = str(e)[:200]
                print(json.dumps(dict(school=s, write_failed=str(e)[:200])), flush=True)
    for school in SCHOOLS:
        got = n.get(school + ':imported', 0)
        if not dry:
            for a in pending[school]:
                out = a.get('outcome', 'not written')
                inv.execute('UPDATE proposals SET outcome=? WHERE school=? AND work_id=? AND src_path=?', (out if out != 'imported' else f'imported {stamp}', school, a['work_id'], a['src_path']))
                if out == 'imported' and a['origin'] == 'disk':
                    cur = inv.execute('SELECT matched_work FROM pdfs WHERE path=?', (a['src_path'],)).fetchone()
                    lst = json.loads(cur[0]) if cur and cur[0] else []
                    lst.append(dict(school=school, work_id=a['work_id'], identity=a['identity'], placed=a['placed'], run=stamp))
                    inv.execute('UPDATE pdfs SET matched_school=?, matched_work=?, imported=1, import_note=? WHERE path=?',
                                (','.join(sorted({x['school'] for x in lst})), json.dumps(lst), f'{a["identity"]}; {a["placed"]}; {stamp}', a['src_path']))
            inv.commit()
        print(json.dumps(dict(school=school, imported=got)), flush=True)
    inv.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (f'import:{stamp}', json.dumps(dict(at=now(), dry=dry, **n))))
    inv.commit()
    print(json.dumps(dict(n), indent=1), flush=True)


def rematch():
    """After the lab-paper lists change (2026-10-29 regeneration): new proposals for the current missing set
    (lr_common.py snapshot again first) without re-reading any file and without touching earlier rows. From the inventory:
    a DOI / arXiv DOI found on page 1 or in the metadata equal to a missing paper's DOI or edition DOI (rule doi), or the
    first-page title equal to its normalized title (rule title_found); the import's identity check is the gate as before.
    Cross-catalog proposals are rebuilt from the fresh stores snapshot the same way as in plan()."""
    missing = load_missing()
    works, shas = load_stores()
    db = sqlite3.connect(str(INV))
    by_doi, by_title = defaultdict(list), defaultdict(list)
    for r in missing:
        if not r['work_id']:
            continue
        for d in [r.get('doi')] + (r.get('editions') or []):
            if d:
                by_doi[F.ndoi(d)].append(r)
        k = F.nt(r.get('title'))
        if len(k) >= 20:
            by_title[k].append(r)
    n = Counter()
    for path, sha, dois, arx, title in db.execute('SELECT path, sha256, dois, arxiv, title_found FROM pdfs WHERE error IS NULL').fetchall():
        hits = {}
        for d in json.loads(dois or '[]') + (['10.48550/arxiv.' + arx] if arx else []):
            for r in by_doi.get(F.ndoi(d), []):
                hits[(r['school'], r['work_id'])] = (r, 'doi')
        for r in by_title.get(F.nt(title), []) if len(F.nt(title)) >= 20 else []:
            hits.setdefault((r['school'], r['work_id']), (r, 'title_found'))
        for (s, w), (r, rule) in hits.items():
            n['disk_' + rule] += db.execute('INSERT OR IGNORE INTO proposals VALUES (?,?,?,?,?,?,?,?,NULL)',
                                            (s, w, r['key'], 'disk', rule, path, sha, json.dumps(dict(rule=rule, rematch=now())))).rowcount
    wd, wt = defaultdict(list), defaultdict(list)
    for w in works:
        if w['doi']:
            wd[w['doi']].append(w)
        k = F.nt(w['title'])
        if len(k) >= 20:
            wt[k].append(w)
    for r in missing:
        if not r['work_id']:
            continue
        for d in [r.get('doi')] + (r.get('editions') or []):
            for w in wd.get(F.ndoi(d), []) if d else []:
                if w['school'] != r['school']:
                    n['cross_doi'] += db.execute('INSERT OR IGNORE INTO proposals VALUES (?,?,?,?,?,?,?,?,NULL)',
                                                 (r['school'], r['work_id'], r['key'], 'cross_catalog', 'cross_doi', str(F.FT / w['school'] / w['file_path']), w['sha256'],
                                                  json.dumps(dict(src_school=w['school'], src_work=w['work_id'], doi=F.ndoi(d))))).rowcount
        k = F.nt(r.get('title'))
        for w in wt.get(k, []) if len(k) >= 20 else []:
            if w['school'] != r['school'] and (not r.get('year') or not w.get('year') or abs(int(w['year']) - int(r['year'])) <= 1):
                n['cross_title'] += db.execute('INSERT OR IGNORE INTO proposals VALUES (?,?,?,?,?,?,?,?,NULL)',
                                               (r['school'], r['work_id'], r['key'], 'cross_catalog', 'cross_title', str(F.FT / w['school'] / w['file_path']), w['sha256'],
                                                json.dumps(dict(src_school=w['school'], src_work=w['work_id'], year=w.get('year'))))).rowcount
    db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', ('rematch:' + now(), json.dumps(dict(n))))
    db.commit()
    print(json.dumps(dict(n)), flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'plan':
        plan()
    elif sys.argv[1] == 'rematch':
        rematch()
    else:
        do_import('--dry' in sys.argv)
