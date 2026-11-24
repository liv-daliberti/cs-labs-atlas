import pytest

from appointment_rosters import illinois_graybook, regular_professor


def page(campus='Urbana-Champaign Campus', rows=None):
    return ('August 22, 2016     Board of Trustees - University of Illinois    Page 1\n'
            f'September, 2016 - ({campus})\n'
            'Employee Name       Job Title          Tenure   Class\n'
            'KP - Engineering\n   434 - Computer Science\n' + (rows or
            'Example, Alice       ASST PROF           P        AA    1.00   1.00  $1.00  $2.00\n'
            '                     RESEARCH PROF                AA    0.00   0.00  $0.00  $0.00\n'))


def test_campus_boundaries_and_no_financial_fields():
    rows = illinois_graybook(page() + '\f' + page('Chicago Campus'))
    assert len(rows) == 2
    assert [x['name'] for x in rows] == ['Example, Alice'] * 2
    assert rows[0]['document_date'] == '2016-08-22'
    assert rows[0]['unit'] == '434 - Computer Science'
    assert rows[0]['title'] == 'ASST PROF'
    assert rows[0]['tenure'] == 'P'
    assert '$' not in str(rows)
    assert not any('salary' in k or 'fte' in k for row in rows for k in row)


def test_no_rank_borrowing_or_invented_continuations():
    with pytest.raises(ValueError, match='Orphan continuation'):
        illinois_graybook(page(rows='                     PROF      A        AA    1.00   1.00  $1.00  $2.00\n'))
    assert regular_professor('FOX FAMILY PROF')
    assert not regular_professor('FOX FAMILY PROF EMERITUS')
    assert not regular_professor('RES ASST PROF')
    assert not regular_professor('TCH ASSOC PROF')
    assert not regular_professor('ADJ PROF')
    assert not regular_professor('VST PROF')


def test_date_and_unit_required():
    with pytest.raises(ValueError, match='lacks date/campus'):
        illinois_graybook(page().replace('August 22, 2016', 'Undated'))
    with pytest.raises(ValueError, match='outside unit'):
        illinois_graybook(page().replace('   434 - Computer Science\n', ''))


def evidence():
    row = illinois_graybook(page())[0]
    proof = dict(format='illinois_graybook', page=row['page'], entry_name=row['name'],
                 title=row['title'], unit=row['unit'], college=row['college'],
                 date=row['document_date'], date_quote=row['date_quote'],
                 employee_class=row['employee_class'])
    return dict(name='Alice Example', quote=row['quote'], observed='20261123',
                ladder=True, dated_roster=proof)


def test_review_preserves_the_source_year_without_a_continuous_interval():
    from cs_related_school import dated_roster, dated_source_fields, faculty_observed
    entry = evidence()
    assert dated_roster(entry, illinois_graybook(page()))['date'] == '2016-08-22'
    assert faculty_observed(entry) == '20160822'
    assert dated_source_fields(entry)['retrieved_at'] == '20261123'
    assert 'historical_appointment' not in dated_source_fields(entry)


@pytest.mark.parametrize('field,value', [('unit', '699 - Computer Science'),
                                       ('entry_name', 'Example, Bob'),
                                       ('date', '2026-08-22'), ('title', 'PROF'),
                                       ('page', True)])
def test_review_cannot_borrow_another_campus_person_title_or_date(field, value):
    from cs_related_school import dated_roster
    entry = evidence()
    entry['dated_roster'][field] = value
    with pytest.raises(SystemExit, match='dated roster'):
        dated_roster(entry, illinois_graybook(page()))


def test_candidate_identity_and_retirement_require_separate_evidence():
    from cs_related_school import dated_roster
    entry = evidence()
    entry['name'] = 'Alfred Example'
    with pytest.raises(SystemExit, match='name conflicts'):
        dated_roster(entry, illinois_graybook(page()))
    entry = evidence()
    entry['observed'] = '20150822'
    with pytest.raises(SystemExit, match='observation window'):
        dated_roster(entry, illinois_graybook(page()))
