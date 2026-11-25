"""stage_gate.website_expected: the register is keyed by package names (census aliases count) and review-excluded PIs are not expected."""
import stage_gate as G


def test_alias_and_review_exclusion(monkeypatch):
    census = [{'name': 'Dan Klein', 'aliases': ['Daniel Klein'], 'is_pi': True}, {'name': 'Brian Harvey', 'is_pi': True},
              {'name': 'Ann Lee', 'is_pi': True}]
    monkeypatch.setattr(G, 'pis_of', lambda key: census)
    monkeypatch.setattr(G.CO, 'section', lambda key: {})
    monkeypatch.setattr(G, 'read', lambda p, d=None: {'excluded': [{'pi': 'Brian Harvey', 'why': 'not a PI'}]})
    doc = {'labs': [{'pi': 'Daniel Klein'}, {'pi': 'Ann Lee'}]}
    assert G.website_expected('x', doc) == ['Daniel Klein', 'Ann Lee']
    assert G.website_expected('x', {'labs': []}) == ['Dan Klein', 'Ann Lee']


def test_pi_census_addition_already_in_dated_census_is_counted_once(monkeypatch):
    source = {'kind': 'ladder_faculty', 'sha256': 'abc', 'quote': 'Brendan Frey Professor'}
    census = {'faculty': [{'name': 'Fahiem Bacchus', 'is_pi': True, 'pi_basis': {'kind': 'ladder_faculty'}},
                          {'name': 'Brendan Frey', 'is_pi': True, 'pi_basis': source}]}
    accent_source = {'kind': 'ladder_faculty', 'sha256': 'def', 'quote': 'Michael Gruninger Professor'}
    census['faculty'].append({'name': 'Michael Gruninger', 'is_pi': True, 'pi_basis': accent_source})
    additions = [{'name': 'Fahiem Bacchus', 'is_pi': True, 'pi_basis': {'kind': 'ladder_faculty'}},
                 {'name': 'Brendan J. Frey', 'is_pi': True, 'pi_basis': source},
                 {'name': 'Michael Grüninger', 'is_pi': True, 'pi_basis': accent_source},
                 {'name': 'New Faculty', 'is_pi': True}]
    monkeypatch.setattr(G.P, 'data', lambda name, key: name)
    monkeypatch.setattr(G, 'read', lambda name, default=None: census if name == 'census-faculty.json' else additions)
    monkeypatch.setattr(G.CO, 'section', lambda *a, **k: {})
    assert [p['name'] for p in G.pis_of('toronto')] == ['Fahiem Bacchus', 'Brendan Frey', 'Michael Gruninger', 'New Faculty']


def test_bilingual_addition_with_the_census_dblp_pid_is_the_census_person(monkeypatch):
    # WHU 2026-11-24: the addition 'Kehua Su' carries the census person 苏科华's DBLP PID; the build merges them into one
    # pis.json record, so the stage-3 gate must not ask for a second home or website.
    census = {'faculty': [{'name': '苏科华', 'is_pi': True, 'dblp': ['https://dblp.org/pid/78/8499'],
                           'pi_basis': {'kind': 'ladder_faculty', 'sha256': 'a', 'quote': '苏科华 教授'}}]}
    additions = [{'name': 'Kehua Su', 'is_pi': True, 'dblp': ['https://dblp.org/pid/78/8499'],
                  'pi_basis': {'kind': 'ladder_faculty', 'sha256': 'b', 'quote': '计算机学院 教授'}},
                 {'name': 'Xin Li', 'is_pi': True, 'dblp': ['https://dblp.org/pid/1/2'],
                  'pi_basis': {'kind': 'ladder_faculty', 'sha256': 'c', 'quote': 'Xin Li Professor'}}]
    monkeypatch.setattr(G.P, 'data', lambda name, key: name)
    monkeypatch.setattr(G, 'read', lambda name, default=None: census if name == 'census-faculty.json' else
                        additions if name == 'census-additions.json' else default)
    monkeypatch.setattr(G.CO, 'section', lambda *a, **k: {})
    assert [p['name'] for p in G.pis_of('whu')] == ['苏科华', 'Xin Li']


def test_source_reviewed_override_alias_uses_existing_package_register(monkeypatch):
    monkeypatch.setattr(G, 'pis_of', lambda key: [
        {'name': 'Peng (Ryan) Huang', 'aliases': [], 'is_pi': True},
        {'name': 'Chien-Ming Huang', 'aliases': [], 'is_pi': True},
    ])
    monkeypatch.setattr(G, 'read', lambda *args: {})
    monkeypatch.setattr(G.CO, 'section', lambda key: {
        'Peng (Ryan) Huang': {'aliases': ['Ryan (Peng) Huang']},
    })
    assert G.website_expected('jhu', {'labs': [{'pi': 'Ryan (Peng) Huang'}]}) == [
        'Ryan (Peng) Huang', 'Chien-Ming Huang',
    ]
