import vt_year_proofs as V


def test_ladder_ranks():
    assert V.ladder('Associate Professor') and V.ladder('Professor of Electrical and Computer Engineering') and V.ladder('Assoc. Prof. of Statistics')
    assert not V.ladder('Research Associate Professor') and not V.ladder('Professor Emeritus') and not V.ladder('Professional Lecturer')


def test_proofs_need_a_spelled_given_name_and_ladder_rank():
    person = dict(name='A. Lynn Abbott', aliases=['Amos Lynn Abbott', 'Amos Abbott'])
    rows = [(2018, 'Abbott', 'Amos', 'Associate Professor', 'Abbott, Amos Associate Professor', 'u', 's'),
            (2018, 'Abbott', 'Jonathan', 'Associate Professor', 'x', 'u', 's'),
            (2019, 'Abbott', 'A.', 'Professor', 'x', 'u', 's'),
            (2021, 'Abbott', 'Amos', 'Research Associate Professor', 'x', 'u', 's')]
    assert list(V.proofs(person, rows)) == [2018]
