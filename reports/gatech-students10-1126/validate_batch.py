"""Check captured evidence and its exact survival in a native hierarchy build."""
import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

import atlas_paths as P
from bs4 import BeautifulSoup
from pihier.links import student_role_ok

ap = argparse.ArgumentParser()
ap.add_argument('--package', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--report', type=Path, action='append', help='Repeat to validate multiple recovery batches together.')
args = ap.parse_args()
reports = args.report or [Path(__file__).resolve().parent]
rows = [r for report in reports for r in json.loads((report / 'additions.json').read_text())]
sources = [s for report in reports for s in json.loads((report / 'sources.json').read_text())]
by_hash = {}
for s in sources:
    body = Path(s['body_path']).read_bytes()
    assert hashlib.sha256(body).hexdigest() == s['sha256']
    if body.startswith(b'%PDF'):
        visible = ' '.join(subprocess.check_output(['pdftotext', '-layout', s['body_path'], '-']).decode().split())
        by_hash[s['sha256']] = ('', visible)
        continue
    soup = BeautifulSoup(body, 'html.parser')
    for el in soup(['script', 'style', 'noscript']):
        el.decompose()
    by_hash[s['sha256']] = (body.decode(), ' '.join(soup.get_text(' ', strip=True).split()))
for row in rows:
    raw, visible = by_hash[row['sha256']]
    assert row['name'] in row['quote']
    assert row['quote'] in raw or row['quote'] in visible
    if row.get('host_quote'):
        assert row['host_quote'] in raw or row['host_quote'] in visible
    assert row['relationship'] in ('membership', 'advising')
    assert row['years'] and 2016 <= min(row['years']) <= max(row['years']) <= 2026
    for s in row.get('corroborating_sources', []):
        raw, visible = by_hash[s['sha256']]
        assert s['quote'] in raw or s['quote'] in visible

pis = json.loads((args.package / 'pis.json').read_text())
students = json.loads((args.package / 'students.json').read_text())
pairs = {(r['pi'], r['name']) for r in rows}
counts = Counter(pi for pi, name in pairs)
checks = []
for row in rows:
    matches = [s for s in students.get(row['pi'], []) if s['name'] == row['name']]
    assert len(matches) == 1, (row['pi'], row['name'], 'native identity')
    student, = matches
    assert student_role_ok(student), (row['pi'], row['name'], 'student role')
    assert row['role'] in student['roles']
    expected = 'researched_' + row['relationship']
    assert any(r['type'] == expected and r.get('role') == row['role'] and r.get('years') == row['years']
               and any(s.get('sha256') == row['sha256'] and s.get('quote') == row['quote']
                       for s in r.get('sources', [])) for r in student['relations']), row
    checks.append(dict(pi=row['pi'], name=row['name'], native_person=student['person'], result='pass'))
existing = {pi: entries for report in reports for pi, entries in json.loads((report / 'baseline.json').read_text()).get('existing_students', {}).items()}
expected_counts = {pi: len({name for p, name in pairs if p == pi} | {s['name'] for s in existing.get(pi, [])}) for pi in counts}
for pi, count in expected_counts.items():
    actual = next(p for p in pis if p['pi'] == pi)['counts']['students']
    assert actual == count, (pi, count, actual)
# Count every native role, independent of cached PI counters.
for pi in pis:
    assert pi['counts']['students'] == sum(student_role_ok(s) for s in students.get(pi['pi'], []))
before = json.loads(P.data('pis.json', 'gatech').read_text())
old = {p['pi']: p['counts'] for p in before}
changed_other = [dict(pi=p['pi'], before=old.get(p['pi']), after=p['counts']) for p in pis
                 if p['pi'] not in counts and old.get(p['pi']) != p['counts']]
result = dict(source_hashes_verified=len(by_hash), relationships_verified=len(pairs), episodes_verified=len(checks), labs_verified=len(counts),
              zero_student_labs=sum(p['counts']['students'] == 0 for p in pis),
              one_student_labs=sum(p['counts']['students'] == 1 for p in pis),
              student_memberships=sum(p['counts']['students'] for p in pis),
              selected_new_counts=dict(counts), selected_counts=expected_counts, other_lab_count_changes=changed_other, checks=checks)
args.out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'other_lab_count_changes')}, indent=2))
print('Other lab count changes:', len(changed_other))
