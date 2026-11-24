"""tools/lab_coverage.py: counts, sources and reasons per lab."""
import importlib.util
from pathlib import Path


def tool():
    spec = importlib.util.spec_from_file_location('lab_coverage_t', Path(__file__).resolve().parents[1] / 'tools' / 'lab_coverage.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_reasons_derived_from_the_census_row_and_open_otherwise():
    L = tool()
    p = {'pi': 'A', 'title': 'Professor Emeritus'}
    cen = {'title_as_listed': 'Professor Emeritus of X', 'years_listed': [2016, 2026], 'ranks_by_year': {'2016': ['emeritus'], '2026': ['emeritus']}, 'rank': 'emeritus'}
    assert L.derived_reason('students', p, cen, {})[0] == 'emeritus_throughout'
    assert L.derived_reason('papers', p, {'years_listed': [2026], 'ranks_by_year': {'2026': ['ladder']}, 'title_as_listed': 'Assistant Professor'}, {})[0] == 'new_hire_2025_or_later'
    assert L.derived_reason('papers', p, {'years_listed': [2016, 2026], 'ranks_by_year': {'2016': ['ladder']}}, {'no_identity': True, 'why_no_identity': 'searched'})[0] == 'no_identity'
    assert L.derived_reason('students', p, {'years_listed': [2016, 2026], 'ranks_by_year': {'2016': ['ladder']}, 'rank': 'ladder'}, {}) is None


def test_student_sources_are_counted_by_kind():
    L = tool()
    rels = [{'relations': [{'sources': [{'url': 'https://x/ttic.edu/students/', 'quote': 'Advisor: Y'}]}]},
            {'relations': [{'section': 'PhD roster + co-authored lab paper (r)', 'sources': [{'url': 'u', 'quote': 'q'}]}]},
            {'relations': [{'sources': [{'url': 'https://lab/people', 'quote': 'PhD students Z'}]}]}]
    assert L.student_sources(rels) == {'adviser list': 1, 'roster+co-author': 1, 'lab page': 1}


def test_R_STU_34_coverage_counts_student_roles_only(monkeypatch):
    """R-STU-34 / D-0046 (owner 2026-11-23): a postdoc or staff member stays a lab member but is not a student (Berkeley Chayes: her only member was a postdoc)."""
    L = tool()
    pis = [{'pi': 'Jennifer Chayes', 'departments': ['EECS'], 'counts': {'students': 1, 'labPapers': 26}},
           {'pi': 'B', 'departments': ['CS'], 'counts': {'students': 3, 'labPapers': 5}}]
    src = [{'url': 'https://lab/people', 'sha256': 'a' * 64, 'quote': 'q'}]
    stu = {'Jennifer Chayes': [{'name': 'S L', 'roles': ['postdoc'], 'relations': [{'type': 'researched_membership', 'role': 'postdoc', 'sources': src}]}],
           'B': [{'name': 'P', 'roles': ['phd'], 'relations': [{'sources': src}]},
                 {'name': 'V', 'roles': ['visiting'], 'relations': [{'sources': src}]},
                 {'name': 'T', 'roles': ['staff'], 'relations': [{'sources': src}]}]}
    files = {'pis.json': pis, 'students.json': stu}
    monkeypatch.setattr(L, 'read', lambda p, default=None: files.get(Path(str(p)).name, default))
    monkeypatch.setattr(L.CO, 'section', lambda key: {})
    rows = {r['pi']: r for r in L.lab_rows('x')}
    assert (rows['Jennifer Chayes']['students'], rows['Jennifer Chayes']['members']) == (0, 1)
    assert rows['Jennifer Chayes']['reasons']['students']['code'] == 'open'
    assert (rows['B']['students'], rows['B']['members']) == (2, 3)


def test_R_STU_34_build_counts_use_the_student_role_rule():
    """R-STU-34: pihier.build counts.students with links.student_role_ok; a postdoc-only or staff-only member is no student, a visiting student is."""
    ok = tool().student_role_ok   # lab_coverage imports pihier.links.student_role_ok
    src = [{'url': 'u', 'sha256': 'a' * 64, 'quote': 'q'}]
    assert not ok({'name': 'S L', 'roles': ['postdoc'], 'relations': [{'role': 'postdoc', 'sources': src}]})
    assert not ok({'name': 'T', 'roles': ['staff'], 'relations': [{'sources': src}]})
    assert ok({'name': 'V', 'roles': ['visiting'], 'relations': [{'role': 'visiting', 'sources': src}]})
    assert ok({'name': 'P', 'roles': ['phd'], 'relations': [{'sources': src}]})
    body = (Path(__file__).resolve().parents[1] / 'tools' / 'pihier' / 'build.py').read_text()
    assert 'students=sum(1 for s in stu[p[\'pi\']].values() if links.student_role_ok(s)), members=len(stu[p[\'pi\']])' in body
