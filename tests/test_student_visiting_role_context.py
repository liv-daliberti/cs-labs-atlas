"""A visitor's own position outranks a broad heading; foreign degrees do not."""
import pytest

from pihier.links import student_role_ok


def visitor(name, quote, role='visiting', **extra):
    return dict(name=name, roles=[role], relations=[dict(role=role, sources=[dict(quote=quote)])], **extra)


@pytest.mark.parametrize('role', ['visiting', 'visitor'])
def test_own_experience_title_beats_scholar_heading(role):
    assert student_role_ok(visitor('Kahyun Lee', 'Visiting Scholars Kahyun Lee Purdue Experience Visiting PhD Student, 3/2026-8/2026 Education Background Ph.D. Student Hallym University', role))


def test_current_host_scholar_position_beats_foreign_undergraduate_and_student_heading():
    quote = ('Visiting Students Carlos Alexis Ortiz Gonzalez Carlos Ortiz is an undergraduate student '
             'at the Universidad Tecnológica de Panamá (UTP). He is currently a visiting scholar at Purdue University. '
             'Johnny Rhe Johnny Rhe is a Ph.D. student at Sungkyunkwan University. '
             'He is currently a visiting researcher at Purdue University.')
    assert not student_role_ok(visitor('Carlos Alexis Ortiz Gonzalez', quote))
    assert not student_role_ok(visitor('Johnny Rhe', quote))


def test_next_person_title_does_not_override_this_person():
    assert student_role_ok(visitor('Ann Lee', 'Visiting Students Ann Lee Bob Gray Visiting Scholar'))
    assert not student_role_ok(visitor('Ann Lee', 'Visiting Scholars Ann Lee Bob Gray University Experience Visiting PhD Student'))
    assert student_role_ok(visitor('Ann Lee', 'Visiting Students Ann Lee Ann Lee is studying at ETH. Bob Gray is a scholar. He is currently a visiting scholar at Purdue.'))


def test_foreign_degree_alone_does_not_override_own_host_position():
    assert not student_role_ok(visitor('Ann Lee', 'Visiting Scholars Ann Lee Ph.D. Student, ETH Zurich'))
    assert not student_role_ok(visitor('Ann Lee', 'Visiting Students Ann Lee Visiting Researcher, Purdue. PhD Student, ETH Zurich'))


def test_independent_student_phase_remains_a_student():
    s = visitor('Ann Lee', 'Visiting Scholars Ann Lee Visiting Scholar')
    s['roles'].append('phd')
    assert student_role_ok(s)
