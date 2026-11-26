import oa_identity_candidates as O

AUTHORS = {'A1': dict(n=30, years=[2016, 2025], raw={'Taisook Han': 30}, orcids={}, venues={'PLDI': 3}),
           'A2': dict(n=12, years=[2016, 2025], raw={'Sue Bok Moon': 12}, orcids={'0000-0001-0000-0001': 1}, venues={'IMC': 2})}
PIS = [dict(name='Taisook Han', aliases=[], orcid=[], years_listed=[2016, 2025]),
       dict(name='Sue Bok Moon', aliases=[], orcid=['https://orcid.org/0000-0001-0000-0001'], years_listed=[2016, 2025])]


def test_stock_binds_a_unique_name_match():
    auto, amb, un = O.propose(PIS, AUTHORS)
    assert set(auto) == {'Taisook Han', 'Sue Bok Moon'} and not amb


def test_propose_mode_needs_an_identifier():
    auto, amb, un = O.propose(PIS, AUTHORS, name_only='propose')
    assert set(auto) == {'Sue Bok Moon'}                       # the author id carries the PI's ORCID
    assert amb['Taisook Han'][0]['held_name_only'] and amb['Taisook Han'][0]['id'] == 'A1'
