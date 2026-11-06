"""A heading that names PhD students and postdocs does not decide the role: the entry's own words do (UChicago round 2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import labpage_students_school as L  # noqa: E402

HEAD = ['Alumni (PhDs and Postdocs)']


def test_entry_says_phd_or_postdoc():
    assert L.mixed_heading_role('phd', HEAD, '(PhD, 2025) Next stop : assistant professor')[1] == 'phd'
    assert L.mixed_heading_role('phd', HEAD, '(postdoc, 2025) Next stop : postdoc at Czech Technical University')[1] == 'postdoc'


def test_entry_saying_neither_stays_member_and_other_headings_are_untouched():
    assert L.mixed_heading_role('phd', HEAD, 'Next stop : scientist')[1] == 'member'
    assert L.mixed_heading_role('phd', ['PhD students'], '(2025)') == ('phd', 'phd')


def test_generic_students_heading_gives_the_student_role():
    assert L.generic_student_role(None, ['Students']) == 'student'
    assert L.generic_student_role(None, ['Group', 'Current Students']) == 'student'
    assert L.generic_student_role(None, ['Advising']) == 'student'
    assert L.generic_student_role(None, ['Members']) is None
    assert L.generic_student_role(None, ['Students in the news']) is None
    assert L.generic_student_role('phd', ['Students']) == 'phd'
