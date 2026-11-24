import census_build as C


def test_title_of_home_unit():
    f = lambda t: C.home_professor_of(t)[1]
    assert f('Bessie Darling Massey Professor of Biomedical Engineering') == 'Biomedical Engineering'
    assert f('John C. Malone Assistant Professor of Civil and Systems Engineering') == 'Civil and Systems Engineering'
    assert f('Professor of Chemical and Biomolecular Engineering and Kent Gordon Croft Investment Management Faculty Scholar') == 'Chemical and Biomolecular Engineering'
    assert f('Adjunct Lecturer in Mathematics') is None


def test_semicolon_affiliate_title_and_practice():
    f = lambda t: C.home_professor_of(t)[1]
    assert f('Assistant Professor of Statistics; Affiliate in Computer Science') == 'Statistics'
    assert f('Timothy E. Wirth Professor of Practice in Learning Technologies; Affiliate in Computer Science') is None
    assert f('Gordon McKay Professor of the Practice of Computer Science') is None
    assert f('Professor of Statistics, Emeritus; Affiliate in Computer Science') is None


def test_home_professor_still_works():
    m, unit = C.home_professor('Professor of Medicine, Medical School')
    assert m and unit == 'Medical School'
    assert C.home_professor('Professor, Bradley Department of Electrical and Computer Engineering; professor by courtesy, Department of Computer Science')[1]
