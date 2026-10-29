"""Print a compact view of each period target: current periods, listings, census override periods."""
import json, sys
H = '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy'
school = sys.argv[1]
T = json.load(open(f'{H}/period-targets-20261026.json'))[school]
P = {p['pi']: p for p in json.load(open(f'{H}/{school}/pis.json'))}
O = json.load(open(f'{H}/census-overrides.json')).get(school)
for t in T:
    p = P.get(t['pi'])
    print('=' * 100); print(t['pi'], t['covered_years'], 'rej', t['years_with_rejected_papers'], 'null_start', t['null_start'])
    if not p:
        print('  NOT IN PIS'); continue
    print('  rank', p.get('rank'), '| title', p.get('title'), '| basis', json.dumps(p.get('piBasis'))[:200])
    for per in p['periods']:
        print('  PERIOD', per['id'], per.get('start'), per.get('end'), per.get('asof'), per.get('datePrecision'), per.get('note','')[:300])
        for e in per.get('evidence', []):
            print('     ev', e.get('kind'), e['url'][:120], '::', e.get('quote','')[:200])
    for l in p.get('listings', []):
        print('  LIST', l.get('year'), l.get('kind'), l['url'][:110], '::', l.get('quote','')[:100])
