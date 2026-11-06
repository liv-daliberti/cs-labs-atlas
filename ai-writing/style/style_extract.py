"""Step 1: style features per paper -> RUN/features_{abstract,allai,fulltext}.parquet (resumable: chunks in RUN/parts, a finished chunk is skipped).

usage: style_extract.py {abstract|allai|fulltext} [--procs N] [--limit N]
abstract  the original abstracts (title excluded: the abstract text only)    allai  the all-AI rewritten abstracts (same papers, filter-kept)
fulltext  the stored body of the usable full texts (today's extraction; first 60 pages, Introduction to References)
"""
import argparse
import multiprocessing as mp
import sqlite3
import zlib

import pandas as pd

import style_common as S
import style_features as F

CHUNK = 2000


def rows(source, lo, hi):
    if source == 'abstract':
        db = sqlite3.connect(f'file:{S.ABS_DB}?mode=ro', uri=True, timeout=600)
        r = db.execute('select paper_id, abstract from abstracts order by paper_id limit ? offset ?', (hi - lo, lo)).fetchall()
    elif source == 'allai':
        db = sqlite3.connect(f'file:{S.ALLAI_DB}?mode=ro', uri=True, timeout=600)
        r = db.execute('select paper_id, abstract from abstracts order by paper_id limit ? offset ?', (hi - lo, lo)).fetchall()
    else:
        db = sqlite3.connect(f'file:{S.FT_DB}?mode=ro', uri=True, timeout=600)
        r = [(p, zlib.decompress(b).decode('utf-8', 'ignore')) for p, b in
             db.execute('select paper_id, body from fulltext where usable = 1 order by paper_id limit ? offset ?', (hi - lo, lo)) if b]
    db.close()
    return r


def count(source):
    path, tab = {'abstract': (S.ABS_DB, 'abstracts'), 'allai': (S.ALLAI_DB, 'abstracts'), 'fulltext': (S.FT_DB, 'fulltext where usable = 1')}[source]
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=600)
    n = db.execute(f'select count(*) from {tab}').fetchone()[0]
    db.close()
    return n


def work(args):
    source, lo, hi, out = args
    if out.exists():
        return out
    kob = S.kobak_words()
    recs = []
    for pid, txt in rows(source, lo, hi):
        f = F.features(txt, kob)
        f['paper_id'] = pid
        recs.append(f)
    df = pd.DataFrame(recs)
    tmp = out.with_name('tmp_' + out.name)
    df.to_parquet(tmp)
    tmp.rename(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', choices=['abstract', 'allai', 'fulltext'])
    ap.add_argument('--procs', type=int, default=8)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    parts = S.RUN / 'parts' / a.source
    parts.mkdir(parents=True, exist_ok=True)
    n = min(count(a.source), a.limit) if a.limit else count(a.source)
    chunks = [(a.source, lo, min(lo + CHUNK, n), parts / f'p{lo:07d}.parquet') for lo in range(0, n, CHUNK)]
    S.C.log(source=a.source, papers=n, chunks=len(chunks), done=sum(c[3].exists() for c in chunks))
    with mp.get_context('fork').Pool(a.procs) as pool:
        for i, _ in enumerate(pool.imap_unordered(work, chunks)):
            if i % 10 == 0:
                S.C.log(finished=i + 1, of=len(chunks))
    df = pd.concat([pd.read_parquet(c[3]) for c in chunks], ignore_index=True)
    df.to_parquet(S.RUN / f'features_{a.source}.parquet')
    S.C.log(done=a.source, rows=len(df))


if __name__ == '__main__':
    main()
