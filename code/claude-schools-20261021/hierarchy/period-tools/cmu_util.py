"""Helpers for the CMU appointment-period review (2026-10-26).
usage: cmu_util.py fetch <url> [needle ...]      polite fetch (stored in period-captures.sqlite) + contexts
       cmu_util.py show <url> [needle ...]       contexts from a stored capture
       cmu_util.py copy <url> [needle ...]       copy from cmu/cs-related-captures.sqlite or listings/cmu/captures.sqlite
       cmu_util.py wb <first|last|YYYY> <url> [needle ...]   Wayback: CDX then fetch the first/last/first-in-year id_ capture
       cmu_util.py cdx <url>                     list Wayback captures (one per month)
"""
import sqlite3, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pcap  # noqa: E402
pcap.mpcap._sess.headers['Accept-Encoding'] = 'gzip, deflate'
_fetch0 = pcap.fetch


def _fetch_retry(url, refetch=False):
    import time
    for i in range(3):
        r = _fetch0(url, refetch=refetch)
        if r.get('status') or 'ConnectionError' not in str(r.get('error')):
            return r
        time.sleep(30)
    return r


pcap.fetch = _fetch_retry
ROOT = HERE.parents[1]
CS = ROOT / 'hierarchy/cmu/cs-related-captures.sqlite'
LS = ROOT / 'listings/cmu/captures.sqlite'


def copy_any(url):
    if pcap.cached(url):
        return pcap.cached(url)
    try:
        return pcap.mpcap.copy(str(CS), url, 'select fetched_at, sha256, content from captures where (url=? or capture_url=?) '
                               'and status=200 and error is null order by id desc limit 1', (url, url),
                               str(CS.relative_to(ROOT)), ctype='text/html')
    except KeyError:
        pass
    return pcap.copy_listing('cmu', url)


def show(url, needles, before=200, after=300, n=6):
    t = pcap.text(url)
    print(f'[{len(t)} chars] {url}')
    for nd in needles:
        hs = pcap.around(url, nd, before, after)
        if not hs:
            print('  -- no hit:', nd)
        for h in hs[:n]:
            print('  >>', h.replace('\n', ' '))


def wb(which, url):
    rows = pcap.mpcap.cdx(url, '1996', '2026', collapse='timestamp:6')
    if not rows:
        return None
    if which == 'first':
        r = rows[0]
    elif which == 'last':
        r = rows[-1]
    else:
        c = [x for x in rows if x[0][:4] >= which]
        r = c[0] if c else rows[-1]
    return f'https://web.archive.org/web/{r[0]}id_/{r[1]}'


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'fetch':
        url, needles = sys.argv[2], sys.argv[3:]
        try:
            r = pcap.fetch(url)
        except Exception as e:
            print("ERR", repr(e)[:200]); sys.exit(0)
        print('status', r.get('status'), r.get('error'))
        show(url, needles)
    elif cmd == 'show':
        show(sys.argv[2], sys.argv[3:])
    elif cmd == 'copy':
        url = sys.argv[2]
        copy_any(url)
        show(url, sys.argv[3:])
    elif cmd == 'wb':
        cu = wb(sys.argv[2], sys.argv[3])
        if not cu:
            print('NO CAPTURES', sys.argv[3])
        else:
            r = pcap.fetch(cu)
            print('status', r.get('status'), r.get('error'))
            show(cu, sys.argv[4:])
    elif cmd == 'cdx':
        for r in pcap.mpcap.cdx(sys.argv[2], '1996', '2026', collapse='timestamp:6'):
            print(r)


def raw(url):
    import zlib
    con = pcap.mpcap.connect()
    row = con.execute('select content from captures where (url=? or capture_url=?) and status=200 and error is null order by id desc limit 1', (url, url)).fetchone()
    con.close()
    if not row:
        return b''
    b = zlib.decompress(row[0])
    if b[:2] == b'\x1f\x8b':
        import gzip
        b = gzip.decompress(b)
    return b


def links(url, pat):
    import re
    s = raw(url).decode('utf-8', 'replace')
    return sorted(set(re.findall(r'href="([^"]*' + pat + r'[^"]*)"', s)))


def scholar(name):
    """search scholars.cmu.edu for a name and return candidate profile links"""
    import urllib.parse
    u = 'https://scholars.cmu.edu/search?query=' + urllib.parse.quote(name)
    pcap.fetch(u)
    return [l for l in links(u, '') if __import__('re').match(r'^/?\d+-', l.lstrip('/').split('scholars.cmu.edu/')[-1])]


if __name__ == '__main__' and cmd == 'scholar':
    for n in sys.argv[2:]:
        print(n, scholar(n)[:8])
