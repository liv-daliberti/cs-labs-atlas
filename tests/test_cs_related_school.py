import cs_related_school as C


def test_faculty_title_does_not_cross_named_doctor_entry():
    pages = [('DPMMS', 'source', 'sha', '20250101',
              'Imre Leader Dr Kaisey Mandel Dr Stuart Martin Professor of Mathematics '
              'Chao Li Professor of Mathematics')]
    assert C.faculty_evidence(pages, ['Imre Leader']) == []
    assert C.faculty_evidence(pages, ['Chao Li'])[0]['ladder']
