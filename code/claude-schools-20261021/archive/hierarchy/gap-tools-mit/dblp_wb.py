"""Fetch the newest Wayback id_ capture of DBLP person pages (dblp.org HTML is bot-walled live) and summarize.
usage: dblp_wb.py PID [PID...]"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import re, sys
sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-mit'))
import capstore
for p in sys.argv[1:]:
    u = 'https://dblp.org/pid/' + p + '.html'
    caps = capstore.wayback_cdx('dblp.org/pid/' + p + '.html', limit=100)
    r = None
    for ts, orig in reversed(caps):
        r = capstore.wayback_fetch(u, ts)
        if r.get('status') == 200 and b'not a bot' not in (r.get('content') or b'')[:3000]:
            break
    if not r or r.get('status') != 200:
        print(p, 'NO CAPTURE'); continue
    t = capstore.page_text(r['content'])
    print('##', p, r['capture_url'], r['sha256'][:16], len(t))
    print('   head:', t[:300])
    for rx in [r'orcid\.org/[0-9X-]{19}', r'(Massachusetts Institute of Technology|MIT)[^.]{0,80}', r'Affiliation[^.]{0,120}']:
        m = re.search(rx, t); print('   ', rx[:20], '->', m.group(0)[:150] if m else None)
    yrs = re.findall(r'\b(20[12]\d)\b', t)
    print('    years>=2016:', sorted({y for y in yrs if y >= '2016'}))
