"""R-STU-22: a student's own page names the PI as adviser (tools/own_page_students.py `statements`)."""
import re

import own_page_students as O

SCHOOL = re.compile(r'georgia\s+inst\w*\.?\s+of\s+tech\w*|georgia\s+tech(?:nology)?\b', re.I)
C = dict(pi='Magnus B Egerstedt', pi_names=['Magnus B Egerstedt', 'Magnus Egerstedt'], pi_family_unique=True, name='Jane Doe', key='jane doe')


def st(text, c=C):
    return O.statements(c, text, SCHOOL)


def test_R_STU_22_current_student_advised_by_the_pi_at_the_school():
    r = st('Jane Doe\nI am a third-year PhD student in ECE at Georgia Tech, advised by Prof. Magnus Egerstedt. (c) 2026')
    assert len(r) == 1 and r[0]['role'] == 'phd' and r[0]['years'] == [O.CAPTURE_YEAR] * 2 and r[0]['years_basis'] == 'capture_date'


def test_R_STU_22_cv_line_with_stated_years():
    r = st('Jane Doe\nPhD, Georgia Institute of Technology, 2017-2022. Advisor: Magnus Egerstedt')
    assert r and r[0]['years'] == [2017, 2022] and r[0]['years_basis'] == 'stated'


def test_R_STU_22_other_school_nearest_the_cue_is_no_statement():
    assert not st('Jane Doe\nPhD student at MIT, advised by Magnus Egerstedt. Previously at Georgia Tech. 2026')


def test_R_STU_22_postdoc_and_collaborator_are_no_statement():
    assert not st('Jane Doe\nPostdoc at Georgia Tech, in collaboration with Magnus Egerstedt, advised by X. 2026')


def test_R_STU_22_page_that_does_not_name_the_candidate_is_no_statement():
    assert not st('John Roe\nPhD student at Georgia Tech, advised by Magnus Egerstedt. 2026')


def test_R_STU_22_stale_undated_page_gets_no_capture_year():
    assert all(x['years_basis'] == 'undated_alumnus' for x in st('Jane Doe\nPhD student at Georgia Tech, advisor: Magnus Egerstedt. Last updated 2014'))


def test_R_STU_22_bare_family_name_needs_a_title_and_a_unique_family():
    c = dict(C, pi_family_unique=False)
    assert not st('Jane Doe\nPhD student at Georgia Tech, advised by Prof. Egerstedt. 2026', c)
    assert st('Jane Doe\nPhD student at Georgia Tech, advised by Prof. Egerstedt. 2026')


def test_R_STU_22_institution_after_the_cue_sentence_does_not_decide():
    c = dict(C, name='Yu Huang', key='yu huang', pi='Westley Weimer', pi_names=['Westley Weimer'])
    r = st('Yu Huang\nI received my PhD in Computer Science at Georgia Tech in 2021. My advisor was Prof. Westley Weimer. I received my MS at University of Virginia in 2016.', c)
    assert r and r[0]['years'] == [2021] and 'Georgia Tech' in r[0]['quote']


def test_R_STU_22_the_school_in_the_line_above_counts_for_an_advisor_line():
    r = st('Jane Doe\nEducation\nGeorgia Institute of Technology, PhD in Robotics, 2018-2023\nAdvisor: Magnus Egerstedt')
    assert r and r[0]['years'] == [2018, 2023]


def test_R_STU_22_alumnus_without_a_year_is_listed_apart_and_a_year_next_to_the_school_dates_it():
    r = st('Jane Doe\nI received my PhD from Georgia Tech, advised by Prof. Magnus Egerstedt.')
    assert r and r[0]['years'] is None and r[0]['years_basis'] == 'undated_alumnus'
    r = st("Jane Doe\nI'm a final-year PhD at Georgia Tech, advised by Magnus Egerstedt. (c) 2026")
    assert r and r[0]['years_basis'] == 'capture_date'


def test_R_STU_22_a_collaborator_after_the_adviser_is_no_adviser():
    c = dict(C, pi='Devi Parikh', pi_names=['Devi Parikh'])
    assert not st('Jane Doe\nI received a Master\'s degree from Georgia Tech in 2021, where I was advised by Dhruv Batra, and worked closely with Devi Parikh.', c)
    assert st('Jane Doe\nI received a Master\'s degree from Georgia Tech in 2021, where I was advised by Dhruv Batra and Devi Parikh.', c)


def test_R_STU_22_an_intern_is_no_student_and_the_role_is_the_nearest_cue():
    assert not st('Jane Doe\nI am a senior at Nanjing University, currently an intern at Georgia Tech, supervised by Prof. Magnus Egerstedt. 2026')
    r = st("Jane Doe\nI'm a PhD student at Stanford. Previously, I was an undergrad at Georgia Tech, advised by Magnus Egerstedt.")
    assert r and r[0]['role'] == 'undergraduate' and r[0]['years_basis'] == 'undated_alumnus'


def test_R_STU_22_a_range_must_sit_next_to_the_school_mention():
    r = st('Jane Doe\nHe obtained the PhD from Georgia Tech in 2018, advised by Prof. Magnus Egerstedt. From 2019 to 2021, he worked at Acme.')
    assert r and r[0]['years'] == [2018]


def test_R_STU_22_role_is_the_cue_before_the_adviser_and_a_start_year_dates_a_current_student():
    r = st('Jane Doe\nI received my PhD from Georgia Tech in 2017 where I was advised by Prof. Magnus Egerstedt. I also received a Masters in Math.')
    assert r and r[0]['role'] == 'phd' and r[0]['years'] == [2017]
    r = st("Jane Doe\nI'm a PhD student at Georgia Tech (since Autumn 2024) advised by Magnus Egerstedt . My research focus. (c) 2026")
    assert r and r[0]['years'] == [2024, O.CAPTURE_YEAR]


def test_R_STU_22_space_before_the_period_still_ends_the_sentence():
    r = st('Jane Doe\nI am currently a 4th-year PhD student at Georgia Tech and luckily advised by Prof. Magnus Egerstedt . I was at INSAIT in Fall 2024 as a visiting student. 2026')
    assert r and r[0]['role'] == 'phd' and r[0]['years_basis'] == 'capture_date'


def test_R_STU_22_degree_year_comes_from_the_sentence_with_the_school_not_from_a_job_or_other_degree():
    r = st('Jane Doe\nI have been at Amazon since May 2024. Before that, I obtained my PhD from Georgia Tech, advised by Prof. Magnus Egerstedt.')
    assert r and r[0]['years_basis'] == 'undated_alumnus'
    r = st('Jane Doe\nShe received the MS from Columbia in 2016. She obtained the Ph.D. from Georgia Institute of Technology, advised by Prof. Magnus Egerstedt.')
    assert r and r[0]['years_basis'] == 'undated_alumnus'


def test_R_STU_22_cv_line_with_month_years_is_a_stated_range_and_a_bare_degree_line_is_not_current():
    r = st('Jane Doe\nPh.D in Computer Science, Georgia Institute of Technology, Aug 2019 - May 2024 Advisors: Prof. Magnus Egerstedt')
    assert r and r[0]['years'] == [2019, 2024] and r[0]['years_basis'] == 'stated'
    r = st('Jane Doe\nPh.D in Computer Science, Georgia Institute of Technology. Advisor: Prof. Magnus Egerstedt. (c) 2026')
    assert r and r[0]['years_basis'] == 'undated_alumnus'


def test_R_STU_22_committee_member_after_the_adviser_is_no_adviser_and_phd_beats_ms_in_a_sentence():
    assert not st('Jane Doe\nPh.D. at Georgia Tech. Adviser: Polo Chau Committee: Magnus Egerstedt, X (2019)')
    r = st('Jane Doe\nPh.D. and M.S. in ECE at Georgia Institute of Technology, advised by Magnus Egerstedt')
    assert r and r[0]['role'] == 'phd'


def test_page_urls_skip_charter_closed_hosts(monkeypatch):
    monkeypatch.setitem(O.CLOSED, 'x', {'dr.ntu.edu.sg', 'personal.ntu.edu.sg'})
    p = dict(urls=['https://dr.ntu.edu.sg/entities/person/A-B', 'https://personal.ntu.edu.sg/~ab/', 'https://ab.github.io/', 'https://id.loc.gov/authorities/n1'])
    assert O.page_urls(p, 'x') == ['https://ab.github.io/']
    assert len(O.page_urls(p)) == 3 and 'https://id.loc.gov/authorities/n1' not in O.page_urls(p)
