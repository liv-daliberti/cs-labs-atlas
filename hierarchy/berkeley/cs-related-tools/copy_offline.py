"""Copy the offline evidence (EECS listing captures, EECS dissertation pages, missing-PI review pages) into the store."""
import sqlite3, sys
sys.path.insert(0, '.')
import mpcap
H = mpcap.HERE
L = f'{H}/listings/berkeley/captures.sqlite'
T = f'{H}/hierarchy/berkeley/thesis-captures.sqlite'
M = f'{H}/hierarchy/missing-pi-captures.sqlite'
n = 0
s = sqlite3.connect(f'file:{L}?mode=ro', uri=True)
for (cu,) in s.execute('select capture_url from captures where http_status=200 and raw_zlib is not null').fetchall():
    mpcap.copy(L, cu, 'select fetched_at, sha256, raw_zlib from captures where capture_url=?', (cu,), 'listings/berkeley/captures.sqlite'); n += 1
s = sqlite3.connect(f'file:{T}?mode=ro', uri=True)
for (u,) in s.execute("select distinct url from captures where status=200 and url like '%Pubs/Dissertations/Years/%'").fetchall():
    mpcap.copy(T, u, 'select fetched_at, sha256, content from captures where url=? and status=200 order by id desc limit 1', (u,), 'hierarchy/berkeley/thesis-captures.sqlite'); n += 1
s = sqlite3.connect(f'file:{M}?mode=ro', uri=True)
for (i, u) in s.execute("select id, url from captures where id between 3 and 12 and status=200 and url not like '%robots.txt'").fetchall():
    mpcap.copy(M, u, 'select fetched_at, sha256, content from captures where id=?', (i,), 'hierarchy/missing-pi-captures.sqlite'); n += 1
print('copied', n)
