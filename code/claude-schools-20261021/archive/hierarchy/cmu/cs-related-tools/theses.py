"""CMU thesis records (hierarchy/thesis-tools/records.py over hierarchy/cmu/thesis-captures.sqlite), without the quote
closures, as JSON; and per-candidate advised theses (adviser name matched with pi_hierarchy.Name over the candidate's
names plus people.py aliases). usage: theses.py <out_dir>  -> <out_dir>/theses.json, <out_dir>/advised.json"""
import collections, json, sys
from pathlib import Path
W = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(W / 'hierarchy/thesis-tools')); sys.path.insert(0, str(W / 'tools')); sys.path.insert(0, str(W / 'hierarchy/cs-related-tools'))
import records  # noqa: E402
from pi_hierarchy import Name, toks  # noqa: E402
from people import P  # noqa: E402
out = Path(sys.argv[1])
T = [{k: v for k, v in r.items() if k != 'q'} for r in records.load('cmu')]
json.dump(T, open(out / 'theses.json', 'w'))
C = json.load(open(W / 'hierarchy/cmu/cs-related-candidates.json'))
al = {i: a + [n] for n, d, ids, a in P for i in ids}
bysur = collections.defaultdict(list)
for r in T:
    for a in r['advisers']:
        t = toks(a)
        if t:
            bysur[t[-1]].append((a, r))
res = {}
for i, c in enumerate(C):
    aid = c['author'].split('/')[-1]
    nm = Name(c['names'] + [c['name']] + al.get(aid, []))
    hits, seen = [], set()
    for s in {f[1] for f in nm.forms}:
        for a, r in bysur.get(s, []):
            if (r['url'], a) not in seen and nm.match(a):
                seen.add((r['url'], a))
                hits.append(dict(adv=a, n_adv=len(r['advisers']), advisers=r['advisers'], student=r['student'], year=r['year'], role=r['role'],
                                 dept=r['dept'], url=r['url'], src=r['source'], adviser_values=r.get('adviser_values'), title=r['title'][:160]))
    res[aid] = dict(i=i, name=c['name'], hits=sorted(hits, key=lambda h: (h['role'] != 'phd', h['year'])))
json.dump(res, open(out / 'advised.json', 'w'), ensure_ascii=False)
print(len(T), sum(1 for v in res.values() if any(h['role'] == 'phd' for h in v['hits'])))
