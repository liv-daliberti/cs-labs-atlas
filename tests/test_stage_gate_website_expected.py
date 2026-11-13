"""stage_gate.website_expected: the register is keyed by package names (census aliases count) and review-excluded PIs are not expected."""
import stage_gate as G


def test_alias_and_review_exclusion(monkeypatch):
    census = [{'name': 'Dan Klein', 'aliases': ['Daniel Klein'], 'is_pi': True}, {'name': 'Brian Harvey', 'is_pi': True},
              {'name': 'Ann Lee', 'is_pi': True}]
    monkeypatch.setattr(G, 'pis_of', lambda key: census)
    monkeypatch.setattr(G, 'read', lambda p, d=None: {'excluded': [{'pi': 'Brian Harvey', 'why': 'not a PI'}]})
    doc = {'labs': [{'pi': 'Daniel Klein'}, {'pi': 'Ann Lee'}]}
    assert G.website_expected('x', doc) == ['Daniel Klein', 'Ann Lee']
    assert G.website_expected('x', {'labs': []}) == ['Dan Klein', 'Ann Lee']


def test_pi_census_addition_already_in_dated_census_is_counted_once(monkeypatch):
    census = {'faculty': [{'name': 'Fahiem Bacchus', 'is_pi': True, 'pi_basis': {'kind': 'ladder_faculty'}}]}
    additions = [{'name': 'Fahiem Bacchus', 'is_pi': True, 'pi_basis': {'kind': 'ladder_faculty'}},
                 {'name': 'New Faculty', 'is_pi': True}]
    monkeypatch.setattr(G.P, 'data', lambda name, key: name)
    monkeypatch.setattr(G, 'read', lambda name, default=None: census if name == 'census-faculty.json' else additions)
    assert [p['name'] for p in G.pis_of('toronto')] == ['Fahiem Bacchus', 'New Faculty']
