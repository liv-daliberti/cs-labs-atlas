"""EPFL: copy the school/institute faculty-list captures of the listings sweep (listings/epfl/captures.sqlite) into
hierarchy/cs-related-captures-epfl.sqlite unchanged (fetched_at, sha256, bytes; copied_from set). Person pages are not copied."""
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import cscap

HERE = cscap.HERE
SRC = HERE / 'listings/epfl/captures.sqlite'
cscap.use('epfl')
s = sqlite3.connect(f'file:{SRC}?mode=ro', uri=True)
rows = s.execute("select capture_url, department, page_url from captures where http_status=200 and raw_zlib is not null "
                 "and department in ('STI','SB','SV','ENAC','CDM','IC') and page_url not like '%people.epfl.ch%' order by department, wayback_timestamp").fetchall()
n = 0
for cu, d, pu in rows:
    r = cscap.copy_listing(str(SRC), cu, 'listings/epfl/captures.sqlite')
    n += 1
print('copied', n)
