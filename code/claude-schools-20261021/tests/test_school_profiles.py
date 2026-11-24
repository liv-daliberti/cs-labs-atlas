"""Newly released charters must work before a vendored site-builder refresh."""
import collections

import pytest

import school_profiles as SP


@pytest.mark.parametrize('school,code,expected', [
    ('harvard', 'CS', 'Computer Science (SEAS)'),
    ('jhu', 'CS', 'Department of Computer Science'),
    ('washu', 'CSE', 'Department of Computer Science and Engineering'),
])
def test_new_school_department_from_charter(school, code, expected):
    assert SP.dept(school, {'pi': 'Example PI', 'departments': [code]},
                   collections.defaultdict(dict)) == expected


def test_reviewed_home_beats_computing_directory_membership():
    homes = {'harvard': {'Example PI': {'home_department': 'Harvard Business School'}}}
    assert SP.dept('harvard', {'pi': 'Example PI', 'departments': ['CS']}, homes) == 'Harvard Business School'
