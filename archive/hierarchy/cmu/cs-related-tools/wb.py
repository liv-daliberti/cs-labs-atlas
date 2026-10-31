"""Wayback captures without the CDX API (which is throttled from this host): GET https://web.archive.org/web/<ts>id_/<url>,
let the archive redirect to its nearest capture, store the bytes via csrcap (robots, politeness, bot checks), and set
the stored row's capture_url to the resolved 14-digit id_ URL, so quotes cite the exact capture.
usage: wb.py <ts> <url> [<url> ...]     (ts like 2016 or 20170601)"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'cs-related-tools'))
import csrcap  # noqa: E402

RX = re.compile(r'^https?://web\.archive\.org/web/(\d{14})id_/(.+)$')


def get(ts, url):
    req = f'https://web.archive.org/web/{ts}id_/{url}'
    r = csrcap.fetch(req)
    con = csrcap.connect()
    fin = con.execute('select final_url from captures where id=?', (r['id'],)).fetchone()[0] or ''
    m = RX.match(fin)
    if m and r.get('status') == 200 and not r.get('error'):
        con.execute('update captures set capture_url=? where id=?', (fin, r['id'])); con.commit()
        r['capture_url'] = fin
    con.close()
    return r


if __name__ == '__main__':
    ts = sys.argv[1]
    for u in sys.argv[2:]:
        try:
            r = get(ts, u)
            print(ts, u, r.get('status'), r.get('error'), r.get('capture_url'), len(r.get('text') or ''), flush=True)
        except Exception as e:
            print(ts, u, 'ERROR', repr(e)[:200], flush=True)
