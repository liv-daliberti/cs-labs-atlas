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
