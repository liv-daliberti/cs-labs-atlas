"""Before/after of one school's package: lab_papers, outside_appointment, and per-target lab-paper/outside counts.
usage: delta.py <school> <before-dir>"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]
s, bd = sys.argv[1], Path(sys.argv[2])
rb, ra = json.load(open(bd / f'{s}-report.json')), json.load(open(HERE / f'hierarchy/{s}/report.json'))
for k in ('lab_papers', 'outside_appointment', 'lab_papers_by_period', 'lab_papers_by_listing', 'pis_with_lab_papers', 'dblp_recovered_outside_appointment', 'labpage_recovered_outside_appointment'):
    print(f'{k:40s} {rb["counts"].get(k)} -> {ra["counts"].get(k)}')
print('builtAt', rb['builtAt'], '->', ra['builtAt'])
PB = {p['pi']: p for p in json.load(open(bd / f'{s}-pis.json'))}
PA = {p['pi']: p for p in json.load(open(HERE / f'hierarchy/{s}/pis.json'))}
T = json.load(open(HERE / 'hierarchy/period-targets-20261026.json')).get(s, [])
out = lambda p: sum(v for k, v in (p.get('funnel') or {}).items() if k.startswith('outside_appointment_'))
for t in T:
    b, a = PB.get(t['pi']), PA.get(t['pi'])
    if not a: print('  missing', t['pi']); continue
    print(f"  {t['pi'][:30]:30s} lab {b['counts']['labPapers']:4d} -> {a['counts']['labPapers']:4d}   outside {out(b):4d} -> {out(a):4d}  left:{sorted(int(k[-4:]) for k in a['funnel'] if k.startswith('outside_appointment_'))}")
