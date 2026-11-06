"""R-STU-22: a student's own page names the PI as adviser (tools/own_page_students.py `statements`)."""
import re

import own_page_students as O

SCHOOL = re.compile(r'georgia\s+inst\w*\.?\s+of\s+tech\w*|georgia\s+tech(?:nology)?\b', re.I)
C = dict(pi='Magnus B Egerstedt', pi_names=['Magnus B Egerstedt', 'Magnus Egerstedt'], pi_family_unique=True, name='Jane Doe', key='jane doe')


def st(text, c=C):
    return O.statements(c, text, SCHOOL)


def test_current_student_advised_by_the_pi_at_the_school():
    r = st('Jane Doe\nI am a third-year PhD student in ECE at Georgia Tech, advised by Prof. Magnus Egerstedt. (c) 2026')
    assert len(r) == 1 and r[0]['role'] == 'phd' and r[0]['years'] == [O.CAPTURE_YEAR] * 2 and r[0]['years_basis'] == 'capture_date'


def test_cv_line_with_stated_years():
    r = st('Jane Doe\nPhD, Georgia Institute of Technology, 2017-2022. Advisor: Magnus Egerstedt')
    assert r and r[0]['years'] == [2017, 2022] and r[0]['years_basis'] == 'stated'


def test_other_school_nearest_the_cue_is_no_statement():
    assert not st('Jane Doe\nPhD student at MIT, advised by Magnus Egerstedt. Previously at Georgia Tech. 2026')


def test_postdoc_and_collaborator_are_no_statement():
    assert not st('Jane Doe\nPostdoc at Georgia Tech, in collaboration with Magnus Egerstedt, advised by X. 2026')


def test_page_that_does_not_name_the_candidate_is_no_statement():
    assert not st('John Roe\nPhD student at Georgia Tech, advised by Magnus Egerstedt. 2026')


def test_stale_undated_page_gets_no_capture_year():
    assert not st('Jane Doe\nPhD student at Georgia Tech, advisor: Magnus Egerstedt. Last updated 2014')


def test_bare_family_name_needs_a_title_and_a_unique_family():
    c = dict(C, pi_family_unique=False)
    assert not st('Jane Doe\nPhD student at Georgia Tech, advised by Prof. Egerstedt. 2026', c)
    assert st('Jane Doe\nPhD student at Georgia Tech, advised by Prof. Egerstedt. 2026')
