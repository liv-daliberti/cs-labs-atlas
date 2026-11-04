"""Abstracts and topics of the universe's works from the OpenAlex bulk snapshot (S3, no API).

The local filtered snapshot (external/openalex-snapshot/current) kept neither abstract_inverted_index nor topics (docs/OPENALEX-SNAPSHOT.md
section 2, "Not kept"), so this adds them by one more streamed pass over the works partitions: a line is parsed only when its work id is one of
the universe's (EMB/universe.sqlite oa_ids), which rejects almost every line on its first bytes. Nothing but the kept rows is stored.
Same shape as tools/oa_snapshot.py (it supplies the manifest, the balanced split and the streaming reader): one array task takes its share of
the parts, writes a job-local part file, copies it to SCRATCH in one sequential write; `merge` attaches the parts into EMB/oa_fields.sqlite.

  oa_fields.py filter <task> <of>     one array task
  oa_fields.py merge [--of N]         parts -> EMB/oa_fields.sqlite, then the parts are removed
  oa_fields.py status
Table works(id PK 'W123', title, year, type, language, updated_date, abstract (plain text, word order), primary_topic json, topics json,
keywords json, snapshot_date). Topic rows are compact: {id, name, score, subfield, field, domain}.
"""
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path

import ecommon as C
import oa_snapshot as S

ID = re.compile(rb'"id":"https://openalex\.org/(W[0-9]+)"')
SCHEMA = '''create table if not exists works (id text primary key, title text, year int, type text, language text, updated_date text,
 abstract text, primary_topic text, topics text, keywords text, snapshot_date text);
create table if not exists parts (url text primary key, records int, kept int)'''


def abstract_text(inv):
    """Plain text of an OpenAlex abstract_inverted_index (word -> positions), in word order; None when empty."""
    if not inv:
        return None
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return ' '.join(w for _, w in pos) or None


def topic(t):
    if not t:
        return None
    return dict(id=(t.get('id') or '').rsplit('/', 1)[-1], name=t.get('display_name'), score=t.get('score'),
                subfield=(t.get('subfield') or {}).get('display_name'), field=(t.get('field') or {}).get('display_name'),
                domain=(t.get('domain') or {}).get('display_name'))


def project(w, date):
    return (w['id'].rsplit('/', 1)[-1], w.get('title'), w.get('publication_year'), w.get('type'), w.get('language'), w.get('updated_date'),
            abstract_text(w.get('abstract_inverted_index')), json.dumps(topic(w.get('primary_topic'))),
            json.dumps([topic(t) for t in w.get('topics') or []]), json.dumps([k.get('display_name') for k in w.get('keywords') or []]), date)


def wanted():
    db = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True)
    out = {r[0] for r in db.execute('select oa from oa_ids')}
    db.close()
    return out


def filter_lines(lines, want, date):
    """(records seen, kept rows) from an iterable of JSONL lines."""
    n, rows = 0, []
    for line in lines:
        n += 1
        m = ID.search(line[:200])
        if m and m.group(1).decode() in want:
            rows.append(project(json.loads(line), date))
    return n, rows


def scratch(date):
    return C.P.SCRATCH / f'oa-fields-{date}'


def cmd_filter(task, of):
    date, parts = S.manifest('works')
    want = wanted()
    mine = S.share([('works', u, b, r) for u, b, r in parts], task, of)
    tmp = Path(os.environ.get('TMPDIR') or '/tmp') / f'oa-fields-{date}-{task:02d}.sqlite'
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(str(tmp))
    db.executescript(SCHEMA)
    t0, done = time.time(), 0
    for _, url, size, _ in mine:
        for attempt in range(4):
            try:
                n, rows = filter_lines(S.stream_lines(url), want, date)
                break
            except Exception as e:  # network or gzip error: the part restarts, nothing of it was written
                C.log(part_retry=url, attempt=attempt, error=str(e)[:120]); time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f'part failed after retries: {url}')
        db.executemany('insert or replace into works values (?,?,?,?,?,?,?,?,?,?,?)', rows)
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
        nparts = db.execute('select count(*) from parts').fetchone()[0]
        if nparts != len(parts):
            raise SystemExit(f'parts table holds {nparts}, manifest {len(parts)}')
        db.commit(); db.close()
    C.atomic_write(C.OA_FIELDS, write)
    db = sqlite3.connect(f'file:{C.OA_FIELDS}?mode=ro', uri=True)
    got = dict(works=db.execute('select count(*) from works').fetchone()[0],
               with_abstract=db.execute('select count(*) from works where abstract is not null').fetchone()[0],
               with_topic=db.execute("select count(*) from works where primary_topic != 'null'").fetchone()[0])
    db.close()
    shutil.rmtree(out)
    C.log(merged=str(C.OA_FIELDS), snapshot_date=date, wanted=len(wanted()), **got)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['filter']:
        cmd_filter(int(a[1]), int(a[2]))
    elif a[:1] == ['merge']:
        cmd_merge(int(a[a.index('--of') + 1]) if '--of' in a else None)
    elif a[:1] == ['status']:
        C.log(oa_fields=str(C.OA_FIELDS), exists=C.OA_FIELDS.exists())
    else:
        raise SystemExit(__doc__)
