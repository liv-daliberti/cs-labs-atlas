"""Reference lists, open-access status, venue and author ids of the universe's works from the OpenAlex bulk snapshot (S3, no API).

The same streamed pass as ai-writing/embeddings/oa_fields.py (its manifest, share and reader), keeping other fields: the content-robust outcomes and
controls of the AI-dose study (reference lists for reference-based novelty, `open_access.oa_status`, the venue's source type, author ids and team size).

  oa_extra.py filter <task> <of>     one array task      oa_extra.py merge [--of N]     parts -> EMB/oa_extra.sqlite
Table works(id PK 'W123', year, type, oa_status, is_oa, source_type, source_name, n_authors, author_ids json, n_refs, refs zlib(comma-joined W numbers),
cited_by, snapshot_date).
"""
import json
import os
import shutil
import sqlite3
import sys
import time
import zlib

import dcommon  # noqa: F401  (puts ai-writing/embeddings on sys.path)
import ecommon as C
import oa_fields as F
import oa_snapshot as S

OUT = C.EMB / 'oa_extra.sqlite'
SCHEMA = '''create table if not exists works (id text primary key, year int, type text, oa_status text, is_oa int, source_type text, source_name text,
 n_authors int, author_ids text, n_refs int, refs blob, cited_by int, snapshot_date text);
create table if not exists parts (url text primary key, records int, kept int)'''


def wnum(u):
    return (u or '').rsplit('/', 1)[-1][1:]


def project(w, date):
    loc = w.get('primary_location') or {}
    src = loc.get('source') or {}
    oa = w.get('open_access') or {}
    auth = w.get('authorships') or []
    refs = [wnum(r) for r in w.get('referenced_works') or [] if wnum(r).isdigit()]
    return (w['id'].rsplit('/', 1)[-1], w.get('publication_year'), w.get('type'), oa.get('oa_status'), int(bool(oa.get('is_oa'))), src.get('type'),
            src.get('display_name'), len(auth), json.dumps([(a.get('author') or {}).get('id', '').rsplit('/', 1)[-1] for a in auth]), len(refs),
            zlib.compress(','.join(refs).encode()), w.get('cited_by_count'), date)


def scratch(date):
    return C.P.SCRATCH / f'oa-extra-{date}'


def cmd_filter(task, of):
    date, parts = S.manifest('works')
    want = F.wanted()
    mine = S.share([('works', u, b, r) for u, b, r in parts], task, of)
    tmp = C.local_tmp() / f'oa-extra-{date}-{task:02d}.sqlite'
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(str(tmp))
    db.executescript(SCHEMA)
    t0, done = time.time(), 0
    for _, url, size, _ in mine:
        for attempt in range(4):
            try:
                n, rows = 0, []
                for line in S.stream_lines(url):
                    n += 1
                    m = F.ID.search(line[:200])
                    if m and m.group(1).decode() in want:
                        rows.append(project(json.loads(line), date))
                break
            except Exception as e:
                C.log(part_retry=url, attempt=attempt, error=str(e)[:120]); time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f'part failed after retries: {url}')
        db.executemany('insert or replace into works values (?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
        db.execute('insert or replace into parts values (?,?,?)', (url, n, len(rows))); db.commit()
        done += 1
        C.log(task=task, parts_done=done, of=len(mine), records=n, kept=len(rows), seconds=int(time.time() - t0))
    db.close()
    out = scratch(date); out.mkdir(parents=True, exist_ok=True)
    dest = out / f'part-{task:02d}.sqlite'
    shutil.copyfile(tmp, str(dest) + '.part'); os.replace(str(dest) + '.part', dest)
    (out / f'part-{task:02d}.done').write_text(json.dumps(dict(bytes=dest.stat().st_size, sha256=S.sha(dest), parts=len(mine), of=of)))
    tmp.unlink(missing_ok=True)
    C.log(task=task, finished=str(dest))


def cmd_merge(of=None):
    date, parts = S.manifest('works')
    out = scratch(date)
    dones = sorted(out.glob('part-*.done'))
    if not dones or (of and len(dones) != of):
        raise SystemExit(f'expected {of} finished parts in {out}, found {len(dones)}')

    def write(t):
        db = sqlite3.connect(t)
        db.executescript(SCHEMA)
        for dn in dones:
            part = dn.with_suffix('.sqlite')
            if S.sha(part) != json.loads(dn.read_text())['sha256']:
                raise SystemExit(f'checksum differs: {part}')
            db.execute('attach ? as p', (str(part),))
            db.execute('insert or replace into works select * from p.works')
            db.execute('insert or replace into parts select * from p.parts')
            db.commit(); db.execute('detach p')
        if db.execute('select count(*) from parts').fetchone()[0] != len(parts):
            raise SystemExit('parts table differs from the manifest')
        db.commit(); db.close()
    C.atomic_write(OUT, write)
    db = sqlite3.connect(f'file:{OUT}?mode=ro', uri=True)
    got = dict(works=db.execute('select count(*) from works').fetchone()[0], with_refs=db.execute('select count(*) from works where n_refs > 0').fetchone()[0])
    db.close()
    shutil.rmtree(out)
    C.log(merged=str(OUT), snapshot_date=date, wanted=len(F.wanted()), **got)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['filter']:
        cmd_filter(int(a[1]), int(a[2]))
    elif a[:1] == ['merge']:
        cmd_merge(int(a[a.index('--of') + 1]) if '--of' in a else None)
    else:
        raise SystemExit(__doc__)
