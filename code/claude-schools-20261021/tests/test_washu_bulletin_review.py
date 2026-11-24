"""Dated catalog evidence stays separate from accepted appointment listings."""
import pytest

import washu_bulletin_review as B


def test_real_cse_faculty_section_crosses_pages_without_losing_last_rows(fixture_json):
    fixture = fixture_json('washu-bulletin-2016-cse.json')
    quote = B.faculty_section(fixture['pages'])
    assert quote.startswith('Faculty Chair Roch Guérin')
    assert 'Shantanu Chakrabartty' in quote
    assert 'Assistant Professors Yasutaka Furukawa' in quote
    assert 'Research Faculty Sharlee Climer' in quote
    assert 'Lecturers Ruth Miller' in quote
    assert quote.endswith('Intellectual property, information systems')
    assert 'Degree Requirements' not in quote
    assert 'admissions@' not in quote
    assert B.printed_date(fixture['pages']) == '2016-10-04'


def test_printed_date_does_not_use_academic_edition_year():
    assert B.printed_date(['Bulletin 2021-22\nEngineering (11/16/22)']) == '2022-11-16'


@pytest.mark.parametrize('pages', [[], ['Faculty\nUnbounded Person'], ['\nFaculty\nPerson']])
def test_incomplete_section_is_refused(pages):
    with pytest.raises(ValueError):
        B.faculty_section(pages)


def test_conflicting_document_dates_are_refused():
    with pytest.raises(ValueError):
        B.printed_date(['Engineering (10/04/16)', 'Engineering (10/05/16)'])
