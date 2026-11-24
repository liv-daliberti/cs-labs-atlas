"""Copy captures unchanged from another mpcap-format store into period-captures.sqlite (as cscap.copy_mp does).
Usage: pm_copy.py <src store path relative to hierarchy/> url..."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import sqlite3, sys
sys.path.insert(0, str(P.HIERARCHY / 'period-tools'))
import pcap
H = f'{P.HIERARCHY}/'
src = H + sys.argv[1]
for url in sys.argv[2:]:
    s = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    ct = (s.execute('select content_type from captures where (url=? or capture_url=?) and status=200 order by id desc limit 1', (url, url)).fetchone() or ['text/html'])[0]
    s.close()
    r = pcap.mpcap.copy(src, url, 'select fetched_at, sha256, content from captures where (url=? or capture_url=?) and status=200 and error is null order by id desc limit 1',
                        (url, url), 'hierarchy/' + sys.argv[1], ctype=ct or 'text/html')
    print('copied', url, r['sha256'][:12], len(r['text']))
