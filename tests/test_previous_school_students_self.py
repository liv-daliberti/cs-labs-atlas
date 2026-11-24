# R-STU-21
"""previous_school_students never reads the school's own package (UChicago, 2026-11-05): once a school is released its package is among
S.released(), and a rerun of `extract` after a build took every student the build already held for a 'previous school' student and
dropped it (56 accepted lab-page students vanished)."""
import json

import labpage_students_school as L  # noqa: E402


def test_R_STU_21_own_package_is_not_a_previous_school(tmp_path, monkeypatch):
    def put(name, obj):
        (tmp_path / name).write_text(json.dumps(obj))
        return tmp_path / name
    census = put('census.json', dict(faculty=[dict(name='Pat Roe', dblp='pid/1')]))
    pis = [dict(pi='Pat Roe', dblp=['pid/1'], orcid=[])]
    studs = {'Pat Roe': [dict(name='Sam Lee')]}
    files = {('census-faculty.json', 'own'): census, ('pis.json', 'own'): put('pis_own.json', pis), ('students.json', 'own'): put('st_own.json', studs),
             ('pis.json', 'other'): put('pis_other.json', pis), ('students.json', 'other'): put('st_other.json', studs)}
    monkeypatch.setattr(L.P, 'data', lambda n, s=None, **kw: files.get((n, s), tmp_path / 'missing.json'))
    monkeypatch.setattr(L.S, 'released', lambda: ['other', 'own'])
    monkeypatch.setattr(L.CO, 'section', lambda k: {})
    out = L.previous_school_students('own')
    assert out['Pat Roe'][0] == 'other'


def test_census_faculty_as_a_plain_list(tmp_path, monkeypatch):
    """CMU's census-faculty.json is a list, not {'faculty': [...]}: extract crashed in previous_school_students (2026-11-23, job 32522634)."""
    def put(name, obj):
        (tmp_path / name).write_text(json.dumps(obj))
        return tmp_path / name
    pis = [dict(pi='Pat Roe', dblp=['pid/1'], orcid=[])]
    studs = {'Pat Roe': [dict(name='Sam Lee')]}
    files = {('census-faculty.json', 'own'): put('census.json', [dict(name='Pat Roe', dblp='pid/1')]),
             ('pis.json', 'other'): put('pis_other.json', pis), ('students.json', 'other'): put('st_other.json', studs)}
    monkeypatch.setattr(L.P, 'data', lambda n, s=None, **kw: files.get((n, s), tmp_path / 'missing.json'))
    monkeypatch.setattr(L.S, 'released', lambda: ['other', 'own'])
    monkeypatch.setattr(L.CO, 'section', lambda k: {})
    assert L.previous_school_students('own')['Pat Roe'][0] == 'other'
