"""Compact view of CMU period targets: pis.json periods/listings + target info. usage: cmu_show.py [name-substring ...]"""
import json, sys
H = '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy'
T = json.load(open(f'{H}/period-tools/cmu-targets-20261026.json'))
P = {p['pi']: p for p in json.load(open(f'{H}/cmu/pis.json'))}
subs = sys.argv[1:]
for t in T:
    if subs and not any(s.lower() in t['pi'].lower() for s in subs):
        continue
    p = P[t['pi']]
    print('=' * 100); print(t['pi'], t['departments'], 'cov', t['covered_years'], 'rej', t['rejected_by_year'])
    print('  rank', p.get('rank'), '| title', p.get('title'), '| depts', p.get('departments'), '| basis', json.dumps(p.get('piBasis'))[:300])
    for per in p['periods']:
        print('  PERIOD', per['id'], per.get('start'), per.get('end'), per.get('asof'), per.get('datePrecision'), (per.get('note') or '')[:400])
        for e in per.get('evidence', []):
            print('     ev', e.get('kind'), e['url'][:130], '::', e.get('quote', '')[:220])
    for l in p.get('listings', []):
        print('  LIST', l.get('year'), l.get('kind'), l['url'][:120], '::', l.get('quote', '')[:90])
