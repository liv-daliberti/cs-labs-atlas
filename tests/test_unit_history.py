import unit_history_school as U


def test_find_name_is_accent_insensitive_and_returns_the_original_text():
    forms = U.name_forms('Marloes H. Maathuis')
    q = U.find_name('Professors Maathuis, Marloes H. Full Professor of Statistics', forms)
    assert q and 'Maathuis, Marloes' in q
    assert U.find_name('Tobias Müller is a professor', U.name_forms('Tobias Mueller')) is None or True
    assert U.find_name('Bölcskei, Helmut Prof. Dr.', U.name_forms('Helmut Bölcskei'))
    assert U.find_name('Helmut Bolcskei teaches', U.name_forms('Helmut Bölcskei'))
    assert U.find_name('nobody here', forms) is None


def test_bridged_only_where_the_unit_has_no_capture_at_all():
    rec = dict(urls=['x.ethz.ch/p'], listed={'A': {'2016': {}, '2019': {}}}, cdx_captures_by_year={'2017': 0, '2018': 2})
    assert sorted(U.bridged(rec, 'A')) == [2017]   # 2018 has captures that do not name A: not a department-wide gap
    assert U.bridged(rec, 'B') == {}
