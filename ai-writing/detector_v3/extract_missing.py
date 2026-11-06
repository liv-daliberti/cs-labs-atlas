"""Extract the stored copies that sections.sqlite lacks (data/missing_copies.jsonl.gz, from missing3.py) with the same splitter.

Uses ai-writing/sections/run_split.py (branch agent/fulltext-sections, read from SPLIT_CODE, default its worktree) for one paper:
fulltext_sections.split_file on the stored copy, passages(main) then passages(appendix). Output = one container per shard in the
sections.sqlite format (tables sections and passages; passage_tags stays empty: these papers have no earlier body to tag):
data/sections_extra/shard-<i>.sqlite. A copy that cannot be read keeps split_error and no text (nothing is scored for it).
usage: extract_missing.py --shard I --nshards N [-j 8]
"""
import argparse, gzip, hashlib, json, os, sqlite3, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import v3common as C

SPLIT_CODE = Path(os.environ.get('SPLIT_CODE', '/n/fs/resemble/homogenizing-science/worktrees/fulltext-sections/ai-writing'))
sys.path.insert(0, str(SPLIT_CODE / 'sections'))
import run_split as RS  # noqa: E402


def one(job):
    pid, school, path, kind = job
    rec = RS.one((pid, None, school, path, kind, None, None))
    return rec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--shard', type=int, required=True); ap.add_argument('--nshards', type=int, required=True)
    ap.add_argument('-j', type=int, default=8)
    a = ap.parse_args()
    t0 = time.time()
    rows = [json.loads(line) for line in gzip.open(C.DATA / 'missing_copies.jsonl.gz', 'rt')]
    rows = [r for i, r in enumerate(rows) if i % a.nshards == a.shard]
    out = C.DATA / 'sections_extra'; out.mkdir(parents=True, exist_ok=True)
    dst = out / f'shard-{a.shard}.sqlite'
    tmp = Path(f'/tmp/extra-{a.shard}-{time.time_ns()}.sqlite')
    db = sqlite3.connect(tmp)
    db.executescript('''create table sections (paper_id text primary key, key text, school text, path text, kind text, main blob, appendix blob, flags text, main_words int,
        appendix_words int, references_chars int, appendix_found int, appendix_position text, appendix_rule text, truncated int, copy_missing int, split_error text,
        n_main_passages int, n_appendix_passages int, n_main_identical int, n_old_passages int);
        create table passage_tags (src text, id text, pidx int, section text, words int);
        create table passages (paper_id text, i int, section text, text_hash text, words int);''')
    import zlib
    n = 0
    with ProcessPoolExecutor(a.j) as ex:
        for rec in ex.map(one, [(r['paper_id'], r['school'], r['path'], r['kind']) for r in rows], chunksize=4):
            f, err = rec['flags'], rec['err']
            main_t, app = (rec['main'], rec['appendix']) if not err else ('', '')
            pm = [] if err else [p for s, p in rec['new'] if s == 'main']
            pa = [] if err else [p for s, p in rec['new'] if s == 'appendix']
            db.execute('insert into sections values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
                rec['paper_id'], None, rec['school'], rec['path'], rec['kind'], zlib.compress(main_t.encode(), 6), zlib.compress(app.encode(), 6), json.dumps(f),
                len(main_t.split()), len(app.split()), rec['refs_chars'], int(bool(f.get('appendix_found'))), f.get('appendix_position'), f.get('appendix_rule'),
                int(bool(f.get('truncated'))), int(err == 'missing'), err if err != 'missing' else None, len(pm), len(pa), 0, 0))
            db.executemany('insert into passages values (?,?,?,?,?)', [(rec['paper_id'], i, s, hashlib.sha1(p.encode()).hexdigest()[:16], len(p.split()))
                                                                      for i, (s, p) in enumerate([('main', x) for x in pm] + [('appendix', x) for x in pa])])
            n += 1
            if n % 500 == 0:
                db.commit(); print(json.dumps(dict(shard=a.shard, done=n, of=len(rows), seconds=round(time.time() - t0))), flush=True)
    db.execute('create index pp on passages (paper_id)'); db.commit(); db.close()
    import shutil
    shutil.copy2(tmp, dst.with_suffix('.tmp')); dst.with_suffix('.tmp').rename(dst); tmp.unlink()
    print(json.dumps(dict(shard=a.shard, finished=n, seconds=round(time.time() - t0), out=str(dst))))


if __name__ == '__main__':
    main()
