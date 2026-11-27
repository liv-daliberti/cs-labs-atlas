"""Reproduce 25 lab enrichments from individually reviewed primary sources."""
import collections
import hashlib
import json
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup
import atlas_paths as P
import schema_check
from pihier.links import student_role_ok
from pihier.names import clean_person_name

SESSION = 'codex-gatech25i-students-20261127'
BATCH = 'gatech-students25i-1127'
OUT = Path(__file__).resolve().parent
WT = OUT.parents[1]
RUN = P.school_part('gatech', 'work') / 'students25i-1127'
manifest = json.loads((RUN / 'sources.json').read_text())
sources = {s['sha256']: s for s in manifest.values()}
entries = json.loads((OUT / 'reviewed-entries.json').read_text())
texts = {}


def text(s):
    if s['sha256'] not in texts:
        body = Path(s['body_path']).read_bytes()
        assert s['status'] == 200 and hashlib.sha256(body).hexdigest() == s['sha256']
        if body.startswith(b'%PDF'):
            t = subprocess.check_output(['pdftotext', s['body_path'], '-'], stderr=subprocess.DEVNULL).decode()
        else:
            soup = BeautifulSoup(body, 'html.parser')
            for node in soup(['script', 'style', 'noscript']):
                node.decompose()
            t = soup.get_text(' ', strip=True)
        texts[s['sha256']] = ' '.join(t.split())
    return texts[s['sha256']]


# Rows were individually reviewed against original primary bytes; preserve roles and relationship types.
new = entries
for row in new:
    assert row['name'] in row['quote']
    assert row['quote'] in text(sources[row['sha256']])
    assert row['relationship'] in {'advising', 'membership'}
    assert 2016 <= min(row['years']) <= max(row['years']) <= 2026
    for source in row['additional_sources']:
        assert source['quote'] in text(sources[source['sha256']])

pairs = {(r['pi'], clean_person_name(r['name'])) for r in new}
selected = {r['pi'] for r in new}
counts = collections.Counter(pi for pi, name in pairs)
assert len(selected) == 25 and len(pairs) == len(new) == 84 and min(counts.values()) >= 1
canonical = json.loads(P.data('pis.json', 'gatech').read_text())
native = json.loads(P.data('students.json', 'gatech').read_text())
by_pi = {p['pi']: p for p in canonical}
bp = OUT / 'baseline.json'
if not bp.exists():
    baseline = dict(zero_student_labs=sum(p['counts']['students'] == 0 for p in canonical),
                    one_student_labs=sum(p['counts']['students'] == 1 for p in canonical),
                    student_memberships=sum(p['counts']['students'] for p in canonical),
                    selected={pi: by_pi[pi]['counts'] for pi in sorted(selected)},
                    existing_students={pi: [s for s in native.get(pi, []) if student_role_ok(s)] for pi in selected})
    assert sum(baseline['selected'][pi]['students'] == 0 for pi in selected) == 1
    assert sum(baseline['selected'][pi]['students'] == 1 for pi in selected) == 24
    bp.write_text(json.dumps(baseline, indent=2) + '\n')
baseline = json.loads(bp.read_text())
assert baseline['zero_student_labs'] == 52 and baseline['one_student_labs'] == 57
assert all(len(v) in (0, 1) for v in baseline['existing_students'].values())
assert all(baseline['selected'][pi]['students'] + counts[pi] >= 2 for pi in selected)
path = P.reviewed_path('few-students-evidence.json', 'gatech', code=WT)
records = json.loads(path.read_text())
records = [g for g in records if not any(s.get('batch') == BATCH for s in g['students'])]
for pi in sorted(selected):
    records.append(dict(pi=pi, students=[{k: v for k, v in r.items() if k != 'pi'} for r in new if r['pi'] == pi],
                        note='25 labs enriched: one empty lab gains four verified GT PhD students and 24 one-student labs gain distinct additional students.'))
errors = schema_check.validate(records, json.loads((WT / 'schemas/few-students-evidence.schema.json').read_text()))
assert not errors, errors
path.write_text(json.dumps(records, indent=1, ensure_ascii=False) + '\n')
(OUT / 'additions.json').write_text(json.dumps(new, indent=2, ensure_ascii=False) + '\n')
used = {r['sha256'] for r in new} | {s['sha256'] for r in new for s in r['additional_sources']}
(OUT / 'sources.json').write_text(json.dumps([s for s in sources.values() if s['sha256'] in used], indent=2) + '\n')
projection = dict(new_relationships=len(pairs), new_episodes=len(new), labs_enriched=len(selected), new_zero_labs_covered=1, one_student_labs_enriched=24,
                  projected_zero_labs=baseline['zero_student_labs'] - 1, projected_one_labs=baseline['one_student_labs'] - 24,
                  projected_memberships=baseline['student_memberships'] + len(pairs), counts=dict(sorted(counts.items())))
(OUT / 'projection.json').write_text(json.dumps(projection, indent=2) + '\n')
print(json.dumps(projection, indent=2))
