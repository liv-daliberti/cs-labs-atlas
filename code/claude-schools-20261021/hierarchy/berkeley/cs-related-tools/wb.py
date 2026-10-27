"""usage: wb.py PAGE_URL YEAR [MONTHFROM]: fetch the first 200 Wayback capture of PAGE_URL in YEAR (id_ form) into the store."""
import sys, mpcap
page, year = sys.argv[1], sys.argv[2]
frm = year + (sys.argv[3] if len(sys.argv) > 3 else '')
rows = mpcap.cdx(page, frm, year, collapse='timestamp:6')
if not rows:
    print('NO CAPTURE', page, year); sys.exit()
ts, orig, st = rows[0]
u = f'https://web.archive.org/web/{ts}id_/{orig}'
r = mpcap.fetch(u)
print(r.get('status'), len(r.get('text') or ''), r.get('error'), u, flush=True)
