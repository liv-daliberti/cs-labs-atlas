import faculty_periods as F


def test_following_cv_position_does_not_backdate_appointment(monkeypatch):
    monkeypatch.setitem(F.SCHOOL, 'test', r'University of Oxford')
    text = ('2024– Associate Professor, Department of Computer Science, University of Oxford '
            '2009–2024 DAMTP, University of Cambridge: PhD, Trinity College (2009–2013).')
    rows = F.candidates(text, 'test')
    assert [(start, end) for start, end, _, _ in rows] == [('2024', None)]


def test_reverse_order_dates_still_work_without_preceding_range(monkeypatch):
    monkeypatch.setitem(F.SCHOOL, 'test', r'University of Oxford')
    rows = F.candidates('Associate Professor, University of Oxford (2012–2018).', 'test')
    assert [(start, end) for start, end, _, _ in rows] == [('2012', '2018')]


def test_distinct_reverse_order_appointment_is_not_suppressed(monkeypatch):
    monkeypatch.setitem(F.SCHOOL, 'test', r'University of Oxford')
    text = ('2024– Professor, University of Oxford. Earlier appointment: '
            'Associate Professor, University of Oxford (2012–2018).')
    assert {(start, end) for start, end, _, _ in F.candidates(text, 'test')} == {
        ('2024', None), ('2012', '2018')}
