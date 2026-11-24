"""Merge reviewed appointment periods (hierarchy/period-tools/proposals/<school>.json) into hierarchy/census-overrides.json.

Only the (school, PI) keys named in the proposals are touched, and within them only the `periods` list: a proposal
replaces the period with the same id (existing override_period_* id) or adds override_period_<school>_<slug>.
The file is re-read immediately before writing; other schools/PIs/keys are left exactly as found.
usage: merge_overrides.py <school> [--file proposals/<name>.json] [--dry]
"""
import json, os, re, sys, unicodedata, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]
OV = HERE / 'hierarchy/census-overrides.json'


def slug(n):
    s = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')


def main(school, dry=False, fname=None):
    props = json.load(open(HERE / 'hierarchy/period-tools' / (fname or f'proposals/{school}.json')))
    todo = []
    for e in props:
        if e.get('verdict') != 'period':
            continue
        p = dict(e['period'])
        eid = e.get('existing_period_id')
        pid = eid if eid and eid.startswith('override_period_') else f'override_period_{school}_{slug(e["pi"])}'
        for x in p.get('evidence') or []:
            assert x.get('url') and x.get('sha256') and (x.get('quote') or x.get('absent')), (e['pi'], x)
        per = dict(id=pid, start=p.get('start'), end=p.get('end'), asof=p.get('asof'),
                   datePrecision=p.get('datePrecision'), evidence=p['evidence'],
                   note=p.get('note'), reviewed='appointment_period_review_20261026')
        if p.get('endPrecision'):
            per['endPrecision'] = p['endPrecision']
        assert per['start'], (e['pi'], 'null start')
        todo.append((e['pi'], per))
    d = json.load(open(OV))  # re-read right before writing
    S = d.setdefault(school, {})
    for pi, per in todo:
        o = S.setdefault(pi, {})
        old = o.get('periods') or []
        ps = [q for q in old if q.get('id') != per['id']]
        o['periods'] = ps + [per]
        print(('replace ' if len(ps) < len(old) else 'add     ') + f'{pi}: {per["id"]} {per["start"]}..{per["end"]} asof={per["asof"]}')
    if dry:
        return
    fd, tmp = tempfile.mkstemp(dir=OV.parent, prefix='.census-overrides.', suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, OV)
    print('wrote', len(todo), 'periods for', school)


if __name__ == '__main__':
    main(sys.argv[1], '--dry' in sys.argv, sys.argv[sys.argv.index('--file') + 1] if '--file' in sys.argv else None)
