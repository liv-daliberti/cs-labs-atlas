"""Wayback fetch: for each URL, list captures via CDX (2010-2026) and fetch one id_ capture (the earliest after
--after YYYY if given, else the latest), printing snippets around the given names.
Usage: pm_wb.py [--first] name1,name2 url..."""
import sys
sys.path.insert(0, '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/period-tools')
import pcap
args = sys.argv[1:]
first = False
if args[0] == '--first':
    first = True; args = args[1:]
names = [n for n in args[0].split(',') if n]


def wb(u):
    rows = pcap.mpcap.cdx(u, '2010', '2026', collapse='timestamp:6')
    if not rows:
        return None
    ts = (rows[0] if first else rows[-1])[0]
    return f'https://web.archive.org/web/{ts}id_/{rows[0][1]}'


for u in args[1:]:
    try:
        cu = u if u.startswith('https://web.archive.org/') else wb(u)
        if not cu:
            print('NO CAPTURES', u); continue
        r = pcap.fetch(cu)
    except Exception as e:
        print('ERR', u, repr(e)[:200]); continue
    print('##', cu, r.get('status'), r.get('error'), len(r.get('text') or ''))
    for n in names:
        for s in pcap.around(cu, n, 250, 350)[:3]:
            print('   [', n, ']', s)
