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
