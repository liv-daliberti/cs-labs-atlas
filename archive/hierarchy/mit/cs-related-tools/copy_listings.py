"""Copy department faculty listings into the MIT CS-related review store (hierarchy/mit/cs-related-captures.sqlite),
bytes and sha256 unchanged, copied_from naming the source store:
  (a) MIT Course Catalog department pages (live + yearly Wayback id_ captures 2016-2026) stored by the leftover
      2026-10-22 session in hierarchy/cs-related-captures-mit.sqlite;
  (b) EECS faculty listings (faculty-advisors 2016-2021, role/faculty 2021-2026) from listings/mit/captures.sqlite.
usage: copy_listings.py
"""
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import mpcap  # noqa: E402

H = mpcap.HERE
A = f'{H}/hierarchy/cs-related-captures-mit.sqlite'
L = f'{H}/listings/mit/captures.sqlite'
n = 0
s = sqlite3.connect(f'file:{A}?mode=ro', uri=True)
rows = s.execute("select id, url, content_type from captures where status=200 and error is null and url like '%catalog.mit.edu%/schools/%/%/' "
                 "and url not like '%cdx%'").fetchall()
for i, u, ct in rows:
    mpcap.copy(A, u, 'select fetched_at, sha256, content from captures where id=?', (i,), 'hierarchy/cs-related-captures-mit.sqlite', ctype=ct or 'text/html'); n += 1
s = sqlite3.connect(f'file:{L}?mode=ro', uri=True)
for (cu,) in s.execute("select capture_url from captures where http_status=200 and raw_zlib is not null and department='EECS' "
                       "and (capture_url like '%faculty-advisors%' or capture_url like '%role/faculty%')").fetchall():
    mpcap.copy(L, cu, 'select fetched_at, sha256, raw_zlib from captures where capture_url=?', (cu,), 'listings/mit/captures.sqlite'); n += 1
print('copied', n)
