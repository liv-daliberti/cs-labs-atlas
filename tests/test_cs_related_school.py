import cs_related_school as C


def test_faculty_title_does_not_cross_named_doctor_entry():
    pages = [('DPMMS', 'source', 'sha', '20250101',
              'Imre Leader Dr Kaisey Mandel Dr Stuart Martin Professor of Mathematics '
              'Chao Li Professor of Mathematics')]
    assert C.faculty_evidence(pages, ['Imre Leader']) == []
    assert C.faculty_evidence(pages, ['Chao Li'])[0]['ladder']


def test_faculty_title_does_not_cross_next_professor_prefix():
    pages = [('DPMMS', 'source', 'sha', '20200809',
              'Dr Chao Li Professor Benedikt Loewe Miss Giulia Luoni')]
    assert C.faculty_evidence(pages, ['Chao Li']) == []


def test_explicit_professor_role_still_supplies_evidence():
    pages = [('DPMMS', 'source', 'sha', '20200809',
              'Po-Ling Loh Professor of Statistics')]
    assert C.faculty_evidence(pages, ['Po-Ling Loh'])[0]['quote'] == 'Po-Ling Loh Professor of Statistics'


def test_qualified_role_is_not_mistaken_for_a_next_person_prefix():
    pages = [('AE', 'source', 'sha', '20200809',
              'Karen M Feigh Associate Professor Knight-419 View Full Profile')]
    assert C.faculty_evidence(pages, ['Karen M. Feigh'])[0]['ladder']
