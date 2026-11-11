"""Princeton directory evidence (2026-11-11): department graduate-directory rows enter the student build through department-directory-evidence.json."""
import collections
import json
from pathlib import Path

import atlas_paths as P
from pihier.students import RESEARCHED_FILES, researched


def test_directory_evidence_is_a_researched_source_and_a_registered_reviewed_file():
    assert 'department-directory-evidence.json' in RESEARCHED_FILES
    assert P.data('department-directory-evidence.json', 'princeton').name == 'department-directory-evidence.json'


def test_princeton_directory_rows_have_hash_quote_and_never_upgrade_the_role():
    rows = json.load(open(Path(__file__).resolve().parents[1] / 'hierarchy/princeton/reviewed/department-directory-evidence.json'))
    seen = collections.Counter()
    for o in rows:
        for s in o['students']:
            seen[(o['pi'], s['name'])] += 1
            assert s['sha256'] and s['quote'] and s['url'].startswith('https://www.cs.princeton.edu/people/grad')
            assert s.get('role') in (None, 'phd', 'masters')
            if s.get('role') is None:   # the current-student card does not state a degree: no role, no years
                assert s.get('years') is None and 'degree not stated' not in (s.get('role') or '')
    assert seen and max(seen.values()) == 1   # no student twice under one PI


def test_a_role_less_directory_row_is_a_plain_student_relation(tmp_path):
    f = P.data('department-directory-evidence.json', 'princeton', root=tmp_path)
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps([dict(pi='Pat Barber', students=[dict(name='Ann Lee', years=None, url='https://www.cs.princeton.edu/people/grad', sha256='ab' * 32, quote='Ann Lee Graduate Student Advisers Pat Barber')])]))
    ctx = type('C', (), dict(here=tmp_path, school='princeton', pis=[{'pi': 'Pat Barber'}], ge={}, n=collections.Counter()))()
    stu = collections.defaultdict(dict)
    researched(ctx, stu, {})
    r = next(iter(stu['Pat Barber'].values()))
    assert r['name'] == 'Ann Lee' and r['roles'] == ['student'] and r['relations'][0]['role'] is None and r['relations'][0]['years'] in (None, [])
