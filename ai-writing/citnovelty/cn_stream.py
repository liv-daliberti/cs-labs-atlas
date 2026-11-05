"""One streamed pass over the OpenAlex works snapshot (S3, no API credits) for the citation study.

  cn_stream.py prepare                  write the focal-set arrays (CSR of references -> focal papers) to SCRATCH once
  cn_stream.py filter <task> <of>       one array task: streams its share of the works parts
  cn_stream.py merge  [--of N]          parts -> DATA/citnovelty.sqlite (meta of referenced works) + counts.npz
  cn_stream.py status

For every work w of the snapshot (focal = a universe paper f with year >= 2008):
  * meta rows for every work that a focal paper references (or is a focal paper): year, source id/type/name, primary subfield and field;
  * citation counts of each focal paper by citing-year offset dy = year(w) - year(f) in 0..MAX_DY, split by whether the citing work also cites at least one of
    f's references (nj) or not (ni)   [exact, every citing work];
  * rc(f, dy): the number of SAMPLED works (id number % SAMPLE_MOD == 0) that cite at least one of f's references (including f itself). The disruption
    index needs nk = works citing a reference of f but not f: nk = SAMPLE_MOD * rc - nj  (a sampled estimate; the n_i, n_j terms are exact).
Same shape as dose/oa_extra.py (manifest, balanced split, streaming reader); the part files are copied to SCRATCH in one write each and removed by `merge`.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import time

import numpy as np

import cn_common as C
import oa_snapshot as S

ID = re.compile(rb'"id":\s?"https://openalex\.org/W([0-9]+)"')
YEAR = re.compile(rb'"publication_year":\s?([0-9]{4})')
WREF = re.compile(rb'/W([0-9]+)')
MIN_Y = 2016


def prep_dir(date):
    return C.SCRATCH / f'cn-stream-{date}'


def cmd_prepare(date):
    d = prep_dir(date); d.mkdir(parents=True, exist_ok=True)
    foc = C.focal_works()
    ids = np.array([int(i[1:]) for i, _, _ in foc], dtype=np.int64)
    years = np.array([y for _, y, _ in foc], dtype=np.int16)
    pairs_r, pairs_f = [], []
    for k, (_, _, refs) in enumerate(foc):
        r = np.unique(np.array(refs, dtype=np.int64)) if refs else np.zeros(0, np.int64)
        pairs_r.append(r); pairs_f.append(np.full(len(r), k, np.int32))
    refcat = np.concatenate(pairs_r); focat = np.concatenate(pairs_f)
    order = np.argsort(refcat, kind='stable')
    refcat, focat = refcat[order], focat[order]
    rids, start = np.unique(refcat, return_index=True)
    roff = np.append(start, len(refcat)).astype(np.int64)
    nref = np.array([len(r) for r in pairs_r], dtype=np.int32)
    roffs = np.zeros(len(foc) + 1, np.int64); roffs[1:] = np.cumsum(nref)
    allrefs = np.concatenate(pairs_r)
    np.savez(d / 'focal.npz', ids=ids, years=years, rids=rids, roff=roff, rfoc=focat, nref=nref, foff=roffs, frefs=allrefs)
    C.log(prepared=str(d / 'focal.npz'), focal=len(foc), refs=len(rids), pairs=len(refcat))


def load_focal(date):
    z = np.load(prep_dir(date) / 'focal.npz')
    return {k: z[k] for k in z.files}


def cmd_filter(task, of, date, parts):
    z = load_focal(date)
    ids, years, rids, roff, rfoc, foff, frefs = (z[k] for k in ('ids', 'years', 'rids', 'roff', 'rfoc', 'foff', 'frefs'))
    fidx = {int(n): k for k, n in enumerate(ids)}
    rset = set(rids.tolist()) | set(fidx)
    refsets = {}
    nf = len(ids)
    ni = np.zeros((nf, C.MAX_DY + 1), np.int32); nj = np.zeros_like(ni); rc = np.zeros_like(ni)
    mine = S.share([('works', u, b, r) for u, b, r in parts], task, of)
    out = prep_dir(date)
    dest = out / f'part-{task:03d}.sqlite'
    if (out / f'part-{task:03d}.done').exists():
        C.log(task=task, skip='done'); return
    tmp = C.local_tmp() / f'cn-stream-{date}-{task:03d}.sqlite'
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(str(tmp))
    db.execute('create table meta (id int primary key, year int, type text, source_id text, source_type text, source_name text, subfield int, field int, cited_by int)')
    t0, nlines, nmeta = time.time(), 0, 0
    for _, url, size, _ in mine:
        for attempt in range(4):
            try:
                rows = []
                ni_t = np.zeros_like(ni); nj_t = np.zeros_like(ni); rc_t = np.zeros_like(ni)
                n = 0
                for line in S.stream_lines(url):
                    n += 1
                    m = ID.search(line, 0, 120)
                    if not m:
                        continue
                    wid = int(m.group(1))
                    if wid in rset:
                        rows.append(meta_row(json.loads(line), wid)); 
                    ym = YEAR.search(line, 0, 4000) or YEAR.search(line)
                    if not ym:
                        continue
                    y = int(ym.group(1))
                    if y < MIN_Y:
                        continue
                    a = line.find(b'"referenced_works":[')
                    if a < 0:
                        continue
                    b = line.find(b']', a)
                    nums = [int(x) for x in WREF.findall(line, a, b)]
                    if not nums:
                        continue
                    ns = None
                    for r in nums:
                        f = fidx.get(r)
                        if f is None:
                            continue
                        dy = y - int(years[f])
                        if 0 <= dy <= C.MAX_DY:
                            if ns is None:
                                ns = set(nums)
                            rs = refsets.get(f)
                            if rs is None:
                                rs = refsets[f] = set(frefs[foff[f]:foff[f + 1]].tolist())
                            if rs & ns:
                                nj_t[f, dy] += 1
                            else:
                                ni_t[f, dy] += 1
                    if wid % C.SAMPLE_MOD == 0:
                        arr = np.array(nums, dtype=np.int64)
                        pos = np.searchsorted(rids, arr)
                        pos[pos >= len(rids)] = len(rids) - 1
                        ok = rids[pos] == arr
                        if ok.any():
                            ps = pos[ok]
                            fs = np.unique(np.concatenate([rfoc[roff[p]:roff[p + 1]] for p in ps]))
                            dys = y - years[fs].astype(np.int64)
                            sel = (dys >= 0) & (dys <= C.MAX_DY)
                            rc_t[fs[sel], dys[sel]] += 1
                # a focal paper citing itself would count nothing; fine
                break
            except Exception as e:
                C.log(part_retry=url, attempt=attempt, error=str(e)[:160]); time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f'part failed after retries: {url}')
        ni += ni_t; nj += nj_t; rc += rc_t
        db.executemany('insert or replace into meta values (?,?,?,?,?,?,?,?,?)', rows); db.commit()
        nlines += n; nmeta += len(rows)
        C.log(task=task, part=url.rsplit('/', 2)[-2][-10:], lines=n, meta=len(rows), seconds=int(time.time() - t0))
    db.close()
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / f'part-{task:03d}.npz', ni=ni, nj=nj, rc=rc)
    shutil.copyfile(tmp, str(dest) + '.part'); os.replace(str(dest) + '.part', dest)
    (out / f'part-{task:03d}.done').write_text(json.dumps(dict(bytes=dest.stat().st_size, lines=nlines, meta=nmeta, parts=len(mine), of=of)))
    tmp.unlink(missing_ok=True)
    C.log(task=task, finished=str(dest), lines=nlines, seconds=int(time.time() - t0))


def meta_row(w, wid):
    loc = w.get('primary_location') or {}
    src = loc.get('source') or {}
    t = w.get('primary_topic') or {}
    sub = ((t.get('subfield') or {}).get('id') or '').rsplit('/', 1)[-1]
    fld = ((t.get('field') or {}).get('id') or '').rsplit('/', 1)[-1]
    return (wid, w.get('publication_year'), w.get('type'), (src.get('id') or '').rsplit('/', 1)[-1] or None, src.get('type'), src.get('display_name'),
            int(sub) if sub.isdigit() else None, int(fld) if fld.isdigit() else None, w.get('cited_by_count'))


def cmd_merge(of, date):
    d = prep_dir(date)
    missing = [t for t in range(of) if not (d / f'part-{t:03d}.done').exists()]
    if missing:
        raise SystemExit(f'tasks not done: {missing}')
    z = load_focal(date)
    nf = len(z['ids'])
    tot = {k: np.zeros((nf, C.MAX_DY + 1), np.int64) for k in ('ni', 'nj', 'rc')}
    for t in range(of):
        p = np.load(d / f'part-{t:03d}.npz')
        for k in tot:
            tot[k] += p[k]
    C.DATA.mkdir(parents=True, exist_ok=True)
    out = C.DB
    tmp = str(out) + '.part'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.execute('create table meta (id int primary key, year int, type text, source_id text, source_type text, source_name text, subfield int, field int, cited_by int)')
    for t in range(of):
        db.execute(f"attach '{d / f'part-{t:03d}.sqlite'}' as p")
        db.execute('insert or replace into meta select * from p.meta')
        db.commit(); db.execute('detach p')
    db.execute('create table info (k text, v text)')
    db.executemany('insert into info values (?,?)', [('snapshot_date', date), ('sample_mod', str(C.SAMPLE_MOD)), ('tasks', str(of))])
    db.commit(); n = db.execute('select count(*) from meta').fetchone()[0]; db.close()
    os.replace(tmp, out)
    np.savez(C.DATA / 'counts.npz', ids=z['ids'], years=z['years'], nref=z['nref'], sample_mod=C.SAMPLE_MOD, **tot)
    C.log(merged=str(out), meta=n, focal=nf)
    shutil.rmtree(d, ignore_errors=True) if os.environ.get('CN_KEEP_PARTS') != '1' else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['prepare', 'filter', 'merge', 'status'])
    ap.add_argument('task', nargs='?', type=int)
    ap.add_argument('of', nargs='?', type=int, default=128)
    ap.add_argument('--of', dest='of2', type=int)
    a = ap.parse_args()
    date, parts = S.manifest('works')
    if a.cmd == 'prepare':
        cmd_prepare(date)
    elif a.cmd == 'filter':
        cmd_filter(a.task, a.of, date, parts)
    elif a.cmd == 'merge':
        cmd_merge(a.of2 or a.of, date)
    else:
        d = prep_dir(date)
        print(date, 'done tasks:', len(list(d.glob('part-*.done'))) if d.exists() else 0)


if __name__ == '__main__':
    main()
