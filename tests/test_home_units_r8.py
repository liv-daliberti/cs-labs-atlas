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
