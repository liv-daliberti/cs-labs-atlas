"""Read cached CDX discovery rows (listings/<school>/captures.sqlite, table cdx) offline.
usage: cdxview.py <school> <url-substring-of-query> [<url regex>]   -> per-URL year counts of 200 captures
"""
import collections, json, re, sqlite3, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]
school, qsub = sys.argv[1], sys.argv[2]
rx = re.compile(sys.argv[3], re.I) if len(sys.argv) > 3 else None
con = sqlite3.connect(f'file:{HERE}/listings/{school}/captures.sqlite?mode=ro', uri=True)
for q, st, body in con.execute('select query, status, body from cdx where query like ?', ('%' + qsub + '%',)):
    try:
        rows = json.loads(body or '[]')
    except ValueError:
        print('bad body', q[:150]); continue
    if not rows:
        print('== (empty)', q[:160]); continue
    h = rows[0]; R = [dict(zip(h, r)) for r in rows[1:]]
    by = collections.defaultdict(collections.Counter)
    for r in R:
        k = r.get('urlkey') or r.get('original')
        if rx and not rx.search(k):
            continue
        by[k][r['timestamp'][:4]] += 1
    print('==', q[:160], len(R))
    for k, c in sorted(by.items()):
        print('  %-90s %s' % (k[:90], ' '.join(f'{y[2:]}:{c[y]}' for y in sorted(c))))
