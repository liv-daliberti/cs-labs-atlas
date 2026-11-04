"""The second look at open PIs (Georgia Tech 2026-11-04)."""
import periods_school as PS


def test_home_hosts_match_unit_names_either_way(monkeypatch):
    monkeypatch.setattr(PS.S, 'get', lambda key: {'departments': [{'name': 'School of Interactive Computing', 'url': 'https://ic.gatech.edu/'}],
                                                   'affiliated_units': [{'name': 'George W. Woodruff School of Mechanical Engineering', 'url': 'https://me.gatech.edu/faculty', 'listings': ['me.gatech.edu/faculty']}]})
    assert PS.home_hosts('k', 'Interactive Computing') == ['ic.gatech.edu']
    assert PS.home_hosts('k', 'George W. Woodruff School of Mechanical Engineering') == ['me.gatech.edu']
    assert PS.home_hosts('k', 'Nowhere') == []


def test_open_pis_are_the_gates_no_period_items(monkeypatch):
    import stage_gate as SG
    monkeypatch.setattr(SG, 'g4', lambda key: (['Ann Lee: no period, listing years [2016, 2018]', 'Bo: PI basis x'], {}))
    assert PS.open_pis('k') == ['Ann Lee']


def test_a_year_proven_by_the_deep_look_is_not_a_gap_for_the_gate(monkeypatch):
    import stage_gate as SG
    monkeypatch.setattr(SG, 'read', lambda p, default=None: {'Ann': {'evidence': {'2018': {}, '2019': {}}}})
    assert SG.proven_years('k', 'Ann') == {2018, 2019} and SG.proven_years('k', 'Bo') == set()
