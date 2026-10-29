"""Fetch URLs (argv after --names) via pcap and print snippets around the given names. Usage: pm_fetch.py name1,name2 url..."""
import sys
sys.path.insert(0, '/n/fs/resemble/cs-atlas/work/hierarchy/period-tools')
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
