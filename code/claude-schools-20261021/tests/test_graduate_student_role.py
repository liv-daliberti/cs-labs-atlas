"""Generic graduate students count without choosing PhD or master's degree."""
from pihier.links import student_role_ok


def test_generic_graduate_students_count_from_record_or_relation_role():
    assert student_role_ok(dict(name='Jie Yang', roles=['graduate'], relations=[]))
    assert student_role_ok(dict(name='Jie Yang', roles=[], relations=[dict(role='graduate')]))


def test_graduate_cue_does_not_admit_explicit_nonstudent_roles():
    for role in ['postgraduate researcher', 'graduate researcher', 'graduate member', 'graduate research_staff', 'graduate professor', 'postdoc', 'staff', 'member']:
        assert not student_role_ok(dict(name='Example Person', roles=[role], relations=[]))
    assert not student_role_ok(dict(name='Example Person', roles=['visiting'], relations=[
        dict(sources=[dict(quote='Visiting scholar Example Person (2021) from Purdue University')])]))
