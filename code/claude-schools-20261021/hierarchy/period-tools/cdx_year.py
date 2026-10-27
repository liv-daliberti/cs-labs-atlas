"""CDX prefix queries for one year, cached in listings/<school>/captures.sqlite (wb.cdx; polite shared throttle).
usage: cdx_year.py <school> <year> <prefix> [<prefix> ...] [--grep REGEX]"""
import collections, os, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'listings/scripts'))
import wb
a = sys.argv[1:]; school, year = a[0], a[1]
g = re.compile(a[a.index('--grep') + 1], re.I) if '--grep' in a else None
pre = [x for i, x in enumerate(a[2:], 2) if not x.startswith('--') and a[i - 1] != '--grep']
con = wb.db(school)
for p in pre:
    rows = wb.cdx({"url": p, "matchType": "prefix", "from": year, "to": year, "output": "json",
                   "fl": "urlkey,timestamp,original,statuscode,digest", "filter": "statuscode:200", "collapse": "urlkey", "limit": "20000"}, con) or []
    print('==', p, len(rows), flush=True)
    for r in rows:
        if not g or g.search(r['original']):
            print('  ', r['timestamp'], r['original'][:140])
