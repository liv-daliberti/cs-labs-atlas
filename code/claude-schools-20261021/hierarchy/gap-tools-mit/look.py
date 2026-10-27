"""Fetch URLs (round-robin across hosts, cached in gap-captures.sqlite) and print text windows around a regex.
usage: look.py [--grep RX] [--chars N] [--wb] [--force] URL...
  --wb : if the live fetch is not 200 (or matches a login wall), fall back to the newest Wayback id_ capture."""
import argparse, json, re, sys
from collections import defaultdict, deque
from urllib.parse import urlsplit
sys.path.insert(0, '/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-mit')
import capstore

ap = argparse.ArgumentParser()
ap.add_argument('--grep'); ap.add_argument('--chars', type=int, default=1200); ap.add_argument('--wb', action='store_true')
ap.add_argument('--force', action='store_true'); ap.add_argument('--head', type=int, default=0); ap.add_argument('urls', nargs='+')
a = ap.parse_args()
WALL = re.compile(r'Access denied|You must log in|Log in to continue|Please log in|Sign in with', re.I)
byhost = defaultdict(deque)
for u in a.urls:
    byhost[urlsplit(u).netloc].append(u)
order = []
while any(byhost.values()):
    for h in list(byhost):
        if byhost[h]:
            order.append(byhost[h].popleft())
for u in order:
    r = capstore.fetch(u, force=a.force)
    t = capstore.page_text(r['content']) if r.get('content') else ''
    if a.wb and (r.get('status') != 200 or (WALL.search(t[:3000]) and len(t) < 6000)):
        caps = capstore.wayback_cdx(u, limit=200)
        if caps:
            ts = caps[-1][0]
            r = capstore.wayback_fetch(u, ts)
            t = capstore.page_text(r['content']) if r.get('content') else ''
    print(json.dumps({k: r.get(k) for k in ('url', 'final_url', 'capture_url', 'status', 'sha256', 'error', 'cached')}), 'len', len(t))
    if a.head:
        print(t[:a.head])
    if a.grep and t:
        n = 0
        for m in re.finditer(a.grep, t, flags=re.I):
            s = max(0, m.start() - a.chars // 2)
            print('  >>', t[s:m.end() + a.chars // 2]); n += 1
            if n >= 8: break
    print('=' * 60, flush=True)
