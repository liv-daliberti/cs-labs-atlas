"""A courtesy row's title that carries a professor rank in the person's own unit (VT CS listing, 2026-11-18)."""
import census_build as C


def unit(t):
    return C.home_professor(t)[1]


def test_vt_two_clause_title_gives_the_home_unit():
    assert unit('Professor, Bradley Department of Electrical and Computer Engineering; professor by courtesy, Department of Computer Science') \
        == 'Bradley Department of Electrical and Computer Engineering'
    assert unit('Associate professor, Department of Philosophy; associate professor by courtesy, Department of Computer Science') == 'Department of Philosophy'
    assert unit('Assistant Professor, Department of Aerospace and Ocean Engineering; assistant professor by courtesy, Department of Computer Science') \
        == 'Department of Aerospace and Ocean Engineering'


def test_named_professorship_takes_the_head_clause_unit():
    t = ('Fred D. Durham Professor of Engineering; head, Kevin T. Crofton Department of Aerospace and Ocean Engineering; '
         'and professor by courtesy, Department of Computer Science')
    assert unit(t) == 'Kevin T. Crofton Department of Aerospace and Ocean Engineering'


def test_single_clause_titles_keep_the_old_behaviour():
    assert unit('Professor of Medicine, Medical School') == 'Medical School'
    assert unit('Professor, Department of Statistics') == 'Department of Statistics'


def test_no_home_rank_no_unit():
    assert unit('Senior research associate, Virginia Tech Transportation Institute; affiliate faculty, Department of Computer Science') is None
    assert unit('Professor courtesy, Department of Computer Science') is None
    assert unit('Professor Emeritus, Department of Physics; professor by courtesy, Department of Computer Science') is None
    assert unit('Courtesy professor') is None
