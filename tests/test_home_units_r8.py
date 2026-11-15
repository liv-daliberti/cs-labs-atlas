"""R8 (Georgia Tech friction 23): a home department is never title text ('Starting Fall'26', 'KUKA Chair...', 'Joint with...')."""
import home_departments_school as H


def test_clean_unit_separates_joint_appointments_and_drops_non_units():
    assert H.clean_unit('Joint with the School of Math') == (None, 'School of Math')
    assert H.clean_unit('Joint w/School of Chemistry and Biochemistry') == (None, 'School of Chemistry and Biochemistry')
    assert H.clean_unit('Joint with the Daniel…') == (None, None)
    assert H.clean_unit("Starting Fall'26") == (None, None)
    assert H.clean_unit('KUKA Chair of Robotics, and Director of IRIM') == (None, None)
    assert H.clean_unit('KUKA Chair for Robotics, Executive…') == (None, None)
    assert H.clean_unit('School of Information') == ('School of Information', None)
    assert H.clean_unit('College of Architecture') == ('College of Architecture', None)
    assert H.clean_unit(None) == (None, None)


def test_the_gate_rejects_a_home_that_is_not_a_known_name(monkeypatch):
    import stage_gate as G
    import lab_websites
    monkeypatch.setattr(lab_websites, 'gate', lambda *a, **kw: [])  # this test isolates the home-department gate
    monkeypatch.setattr(G, 'known_homes', lambda key: {'Computer Science'})
    monkeypatch.setattr(G, 'pis_of', lambda key: [{'name': 'Ann', 'pi_basis': {'url': 'u', 'sha256': 's', 'quote': 'q'}}, {'name': 'Bo', 'pi_basis': {'url': 'u', 'sha256': 's', 'quote': 'q'}}])
    monkeypatch.setattr(G, 'read', lambda p, default=None: [dict(name='Ann', status='accepted', home_department='Computer Science'), dict(name='Bo', status='accepted', home_department="Starting Fall'26")])
    bad, _ = G.g3('k')
    assert any(b.startswith('Bo: home department') for b in bad) and not any(b.startswith('Ann') for b in bad)


def test_a_second_title_is_not_a_unit():
    assert H.clean_unit('Professor Emeritus') == (None, None)


def test_units_by_recency_puts_the_center_first_and_the_latest_academic_unit_last():
    import cs_related_school as C
    lad = [dict(unit='ML', observed='20261103'), dict(unit='AE', observed='20180101'), dict(unit='BME', observed='20250117'), dict(unit='AE', observed='20240101')]
    assert C.units_by_recency(lad, {'ML'}) == ['ML', 'AE', 'BME'] and C.units_by_recency(lad, set()) == ['AE', 'BME', 'ML']


def test_a_site_feedback_form_is_not_a_website_selection():
    import lab_websites as W
    assert 'selected_url_is_feedback_form' in W.selection_gaps('https://webdev.iac.gatech.edu/feedback?code=lmc')
    assert 'selected_url_is_feedback_form' in W.selection_gaps('https://example.edu/people/feedback/')
    assert 'selected_url_is_feedback_form' not in W.selection_gaps('https://www.cs.example.edu/~ann/')


def test_a_title_case_listing_heading_is_a_unit_name_but_a_host_token_is_not(tmp_path, monkeypatch):
    """UT Austin 2026-11-15: an addition coded by its listing heading ('Mathematics') is homed there; a lower-case host token ('jhu') is still a hold."""
    import json
    import atlas_paths as P
    import school_config as S
    rows = [dict(name=n, is_pi=True, departments=[d], pi_basis=dict(url='u', sha256='s', quote='q'), sources=[dict(kind=f'unit_listing:{d}')]) for n, d in (('Ann', 'Mathematics'), ('Bo', 'jhu'))]
    out = {}
    monkeypatch.setattr(S, 'get', lambda key: dict(departments=[], affiliated_units=[], census=dict(home_units={}, center_units=[])))
    monkeypatch.setattr(S, 'field', lambda cfg, path: cfg['census'].get(path.split('.')[-1]))
    files = {'census-faculty.json': json.dumps(dict(faculty=[])), 'census-additions.json': json.dumps(rows), 'rows.json': '[]'}
    monkeypatch.setattr(P, 'data', lambda name, key=None: type('F', (), {'read_text': lambda self: files[name], 'exists': lambda self: name in files})())
    monkeypatch.setattr(P, 'data_w', lambda name, key=None: type('F', (), {'write_text': lambda self, t: out.update(rows=json.loads(t))})())
    import census_overrides as CO
    monkeypatch.setattr(CO, 'section', lambda key: {})
    H.main('k')
    got = {r['name']: r for r in out['rows']}
    assert got['Ann']['status'] == 'accepted' and got['Ann']['home_department'] == 'Mathematics' and got['Bo']['status'] == 'hold'
