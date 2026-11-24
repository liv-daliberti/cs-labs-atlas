"""A later repository co-adviser must survive the wrong-adviser exclusion."""
from pihier.students import relation_names_other_adviser


def relation(quote):
    return {'sources': [{'quote': quote}]}


def test_repository_coadvisers_are_not_dropped():
    row = relation('Creators Zhang, Jiawei | Advisor: Li, Bo; Zhang, Ce | Published 2026 | Dissertation')
    assert not relation_names_other_adviser(row, ['Bo Li'])
    assert not relation_names_other_adviser(row, ['Ce Zhang'])
    assert relation_names_other_adviser(row, ['Sanjay Krishnan'])


def test_later_metadata_is_not_advising():
    row = relation('Creators Student, Alex | Advisor: Li, Bo | Published 2026 | Title Zhang methods')
    assert relation_names_other_adviser(row, ['Ce Zhang'])
    row = relation('Creators Student, Alex | Advisor: Li, Bo; Committee members: Zhang, Ce | Dissertation')
    assert relation_names_other_adviser(row, ['Ce Zhang'])


def test_plain_roster_keeps_existing_wrong_adviser_guard():
    row = relation('Kritkorn Karntikoon - Adviser(s): Bernard Chazelle; Examiner: Matt Weinberg')
    assert not relation_names_other_adviser(row, ['Bernard Chazelle'])
    assert relation_names_other_adviser(row, ['Matt Weinberg'])
    assert relation_names_other_adviser(row, ['Mark Braverman'])


def test_each_source_must_exclude_the_pi_before_dropping():
    row = {'sources': [
        {'quote': 'Creators Student, Alex | Advisor: Li, Bo | Dissertation'},
        {'quote': 'Creators Student, Alex | Advisor: Li, Bo; Zhang, Ce | Dissertation'},
    ]}
    assert not relation_names_other_adviser(row, ['Ce Zhang'])
