import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'accuracy'))
import sample as S  # noqa: E402

URL = 'https://ecommons.cornell.edu/server/api/discover/search/objects?query=thesis.degree.level%3A%22Doctor+of+Philosophy%22&size=100'


def rel(url=URL, role='phd', typ='researched_advising'):
    return dict(type=typ, role=role, years=[2017, 2017], sources=[dict(url=url, quote='X [...] Y')])


def test_thesis_repository_phd_relation_counts_as_alumnus():
    assert S.alumni_relation(rel(), ['phd']) == 2017


def test_roster_page_or_non_phd_role_does_not():
    assert S.alumni_relation(rel(url='https://cs.example.edu/people/students'), ['phd']) is None
    assert S.alumni_relation(rel(role='ms'), ['ms']) is None
    assert S.alumni_relation(rel(typ='coauthor'), ['phd']) is None


def test_explicit_alumnus_role_still_works():
    assert S.alumni_relation(rel(url='https://cs.example.edu/alumni'), ['phd_alumnus']) == 2017
