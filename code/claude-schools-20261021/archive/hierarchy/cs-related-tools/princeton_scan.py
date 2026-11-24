"""Department-list scan: every person on the stored non-CS Princeton faculty lists whose matching OpenAlex authors (author
index, Princeton-affiliated works 2016-2026) have >=5 works in CS venues, and who is not already a PI (pis.json).
-> <out>/princeton-scan.json
usage: princeton_scan.py <out_dir>
"""
import collections, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'hierarchy/cs-related-tools'))
import helpers  # noqa: E402
from helpers import Name, toks  # noqa: E402

out = Path(sys.argv[1])
E = json.load(open(out / 'princeton-listing-entries.json'))
pis = json.load(open(HERE / 'hierarchy/princeton/pis.json'))
pi_nm = [(p['pi'], Name(p['names'])) for p in pis]
pi_ids = {a for p in pis for a in (p.get('oaAuthorIds') or []) + (p.get('reviewedOpenAlex') or [])}
people = collections.defaultdict(lambda: dict(depts=collections.Counter(), titles=collections.Counter(), years=set()))
for e in E:
    k = ' '.join(toks(e['name']))
    p = people[k]; p['name'] = e['name']; p['depts'][e['dept']] += 1; p['titles'][e['title']] += 1; p['years'].add(e['year'])
res = []
for k, p in people.items():
    ms = helpers.oa_matches('princeton', [p['name']])
    cs = sum(m['cs'] for m in ms)
    if cs < 5:
        continue
    pi = next((x for x, n in pi_nm if n.match(p['name'])), None)
    res.append(dict(name=p['name'], depts=dict(p['depts']), titles=[t for t, _ in p['titles'].most_common(3)], years=sorted(p['years']), cs=cs,
                    existing_pi=pi, ids_in_pis=[m['id'] for m in ms if m['id'] in pi_ids],
                    oa=[dict(id=m['id'], n=m['n'], cs=m['cs'], raw=m['raw'], venues=m['venues'], orcid=m['orcid']) for m in ms if m['cs'] or m['n'] > 5]))
res.sort(key=lambda r: -r['cs'])
json.dump(res, open(out / 'princeton-scan.json', 'w'), indent=1, ensure_ascii=False)
print(len(res), sum(1 for r in res if not r['existing_pi']))
