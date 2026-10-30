"""Fetch URLs (argv after --names) via pcap and print snippets around the given names. Usage: pm_fetch.py name1,name2 url..."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import sys
sys.path.insert(0, str(P.HIERARCHY / 'period-tools'))
import pcap
names = [n for n in sys.argv[1].split(',') if n]
for u in sys.argv[2:]:
    try:
        r = pcap.fetch(u)
    except Exception as e:
        print('ERR', u, repr(e)[:200]); continue
    print('##', u, r.get('status'), r.get('error'), len(r.get('text') or ''))
    for n in names:
        for s in pcap.around(u, n, 250, 350)[:3]:
            print('   [', n, ']', s)
