"""The not-yet-scored full texts, for incremental scoring with the final model (score_delta.slurm).

scored   every key in results/scores/papers-*.jsonl.gz (the full run's shards and earlier deltas)
store    ai-writing/fulltext.sqlite, read in short rowid chunks (read-only; fulltext.py may be writing)
-> data/delta-<tag>.sqlite texts(key, school, path, kind, chars, intro, body, flags): the texts no shard has scored,
   fresh contiguous rowids, so detector.py score's rowid sharding splits it evenly
usage: score_delta_prep.py TAG
"""
import glob, gzip, json, sqlite3, sys, time
import v2common as V

tag = sys.argv[1]
scored = set()
for f in glob.glob(str(V.RESULTS / 'scores' / 'papers-*.jsonl.gz')):
    for line in gzip.open(f, 'rt'):
        scored.add(json.loads(line)['key'])
src = sqlite3.connect(f'file:{V.FULLTEXT}?mode=ro', uri=True, timeout=1800)
hi = src.execute('select max(rowid) from texts').fetchone()[0] or 0
dst_path = V.HERE / 'data' / f'delta-{tag}.sqlite'
tmp = dst_path.with_suffix('.tmp')
tmp.unlink(missing_ok=True)
dst = sqlite3.connect(tmp)
dst.execute('create table texts (key text primary key, school text, path text, kind text, chars int, intro blob, body blob, flags text)')
n = 0; by_school = {}
for lo in range(0, hi + 1, 2000):
    keys = [k for (k,) in src.execute('select key from texts where rowid >= ? and rowid < ?', (lo, lo + 2000)) if k not in scored]
    for i in range(0, len(keys), 200):
        q = keys[i:i + 200]
        rows = src.execute(f'select key, school, path, kind, chars, intro, body, flags from texts where key in ({",".join("?" * len(q))})', q).fetchall()
        dst.executemany('insert into texts values (?,?,?,?,?,?,?,?)', rows)
        for r in rows:
            by_school[r[1]] = by_school.get(r[1], 0) + 1
        n += len(rows)
    dst.commit(); time.sleep(0.02)
dst.close(); src.close()
tmp.replace(dst_path)
print(json.dumps(dict(delta=str(dst_path), texts=n, by_school=by_school, already_scored=len(scored))))
