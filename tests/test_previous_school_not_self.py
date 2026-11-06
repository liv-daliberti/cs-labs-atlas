"""labpage_students_school.previous_school_students never matches the school against itself (Michigan 2026-11-05: after Michigan's own package
existed, `extract` dropped 426 of its own lab-page students as 'students of the PI's previous school')."""
import json

import atlas_paths as P
import census_overrides as CO
import labpage_students_school as L
import school_config as S


def test_a_school_is_not_its_own_previous_school(tmp_path, monkeypatch):
    census = dict(faculty=[dict(name='Ada Lovelace', dblp=['https://dblp.org/pid/1'])])
    pis = [dict(pi='Ada Lovelace', dblp=['https://dblp.org/pid/1'], orcid=[])]
    studs = {'Ada Lovelace': [dict(name='Bob Babbage')]}
    files = {'census-faculty.json': census, 'pis.json': pis, 'students.json': studs}

    def data(name, school=None, *a, **k):
        f = tmp_path / f'{school}-{name}'
        if name in files and not f.exists():
            f.write_text(json.dumps(files[name]))
        return f
    monkeypatch.setattr(P, 'data', data)
    monkeypatch.setattr(CO, 'section', lambda key: {})
    monkeypatch.setattr(S, 'released', lambda: ['x'])
    assert 'Ada Lovelace' not in L.previous_school_students('x')       # x's own package is not a previous school
    assert L.previous_school_students('z')['Ada Lovelace'][0] == 'x'   # another school's is
