"""Reproduce 25 previously empty labs from dated university doctoral programs."""
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

SESSION = 'codex-gatech25-students-20261127'
BATCH = 'gatech-students25f-1127'
OUT = Path(__file__).resolve().parent
WT = OUT.parents[1]
RUN = P.school_part('gatech', 'work') / 'students25f-1127'
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


def supporting(s, quote):
    assert quote in text(s), (s['url'], quote)
    return dict(url=s['url'], sha256=s['sha256'], quote=quote)


new = []
for entry in entries:
    s = sources[entry['sha256']]
    assert entry['name'] in entry['quote'] and entry['quote'] in text(s)
    assert 2016 <= entry['year'] <= 2026
    degree = 'Doctor of Philosophy'
    assert degree in text(s)
    # The degree designation and ceremony year are separate source assertions.
    date_options = [f"{entry['year']} FALL COMMENCEMENT", f"{entry['year']} SPRING COMMENCEMENT",
                    f"{entry['year']} Fall Commencement", f"{entry['year']} Spring Commencement"]
    date_quote = next(q for q in date_options if q in text(s))
    row = dict(pi=entry['pi'], name=entry['name'], role='phd', relationship='advising',
               years=[entry['year'], entry['year']], years_basis='dated university doctoral candidate program; explicit named adviser',
               alumni=False, url=s['url'], sha256=s['sha256'], quote=entry['quote'], observed=s['observed'],
               reviewed=True, reviewed_by=SESSION, auto=False, rule='R-STU-01', batch=BATCH,
               source_pdf_page=entry['pdf_page'], source_text_extraction='pdftotext reading order',
               additional_sources=[supporting(s, degree), supporting(s, date_quote)],
               note='Historical doctoral-candidate observation in the ceremony year. No enrollment span, present enrollment, or degree completion inferred. Only explicitly named advisers receive a relationship; coadvisers are preserved independently.')
    if entry.get('corroboration_url'):
        ps = next(s for s in sources.values() if s['url'] == entry['corroboration_url'])
        row['additional_sources'].append(supporting(ps, entry['corroboration_cue']))
        row['note'] += ' ' + entry['note']
    if entry['pi'] == 'Spyros Reveliotis':
        ps = next(s for s in sources.values() if s['url'] == 'https://www2.isye.gatech.edu/~spyros/LP/')
        row['additional_sources'].append(supporting(ps, 'Spiridon (Spyros) Reveliotis'))
    if entry['name'] == 'Mustafa Mukadam':
        ps = next(s for s in sources.values() if s['url'] == 'https://par.nsf.gov/servlets/purl/10090225')
        t = text(ps)
        a = t.index('Mustafa Mukadam is currently')
        b = t.index('He received', a)
        q = t[a:b].strip()
        assert 'Byron Boots' in q
        row['additional_sources'].append(supporting(ps, q))
    new.append(row)

pairs = {(r['pi'], clean_person_name(r['name'])) for r in new}
selected = {r['pi'] for r in new}
counts = collections.Counter(pi for pi, name in pairs)
assert len(selected) == 25 and len(pairs) == len(new) == 90 and min(counts.values()) >= 2
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
    assert all(baseline['selected'][pi]['students'] == 0 for pi in selected)
    bp.write_text(json.dumps(baseline, indent=2) + '\n')
baseline = json.loads(bp.read_text())
assert baseline['zero_student_labs'] == 124 and baseline['one_student_labs'] == 60
assert all(not v for v in baseline['existing_students'].values())
path = P.reviewed_path('few-students-evidence.json', 'gatech', code=WT)
records = json.loads(path.read_text())
records = [g for g in records if not any(s.get('batch') == BATCH for s in g['students'])]
for pi in sorted(selected):
    records.append(dict(pi=pi, students=[{k: v for k, v in r.items() if k != 'pi'} for r in new if r['pi'] == pi],
                        note='25 empty labs recovered with two or more source-verified doctoral advisees each.'))
errors = schema_check.validate(records, json.loads((WT / 'schemas/few-students-evidence.schema.json').read_text()))
assert not errors, errors
path.write_text(json.dumps(records, indent=1, ensure_ascii=False) + '\n')
(OUT / 'additions.json').write_text(json.dumps(new, indent=2, ensure_ascii=False) + '\n')
used = {r['sha256'] for r in new} | {s['sha256'] for r in new for s in r['additional_sources']}
(OUT / 'sources.json').write_text(json.dumps([s for s in sources.values() if s['sha256'] in used], indent=2) + '\n')
projection = dict(new_relationships=len(pairs), new_episodes=len(new), labs_enriched=len(selected), new_zero_labs_covered=25,
                  projected_zero_labs=baseline['zero_student_labs'] - 25, projected_one_labs=baseline['one_student_labs'],
                  projected_memberships=baseline['student_memberships'] + len(pairs), counts=dict(sorted(counts.items())))
(OUT / 'projection.json').write_text(json.dumps(projection, indent=2) + '\n')
print(json.dumps(projection, indent=2))
