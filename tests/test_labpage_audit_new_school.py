"""labpage_audit knows a charter school without a hand-edited table (UChicago PROTOCOL-FRICTION 26)."""
import labpage_audit as L


def test_a_charter_school_gets_an_entry_and_own_names(monkeypatch):
    import school_config
    cfg = {'name': 'University of Chicago', 'web': {'domains': ['uchicago.edu', 'ttic.edu']}}
    monkeypatch.setattr(school_config, 'get', lambda k: cfg if k == 'newu' else (_ for _ in ()).throw(KeyError(k)))
    e = L.SCHOOLS['newu']
    assert e['family'] == 'michigan' and 'uchicago\\.edu' in e['domain'] and 'ttic\\.edu' in e['domain']
    assert {'NEWU', 'UC', 'CHICAGO'} <= L.own_names('newu', L.OWN_INST)
    assert L.own_names('mit', L.OWN_INST) == {'MIT'}
    assert 'University\\ of\\ Chicago' in L.school_names_rx('newu') and L.school_names_rx('mit').startswith('MIT')


def test_an_onboarding_school_summary_is_school_local(monkeypatch):
    import atlas_paths as P
    import school_config
    monkeypatch.setattr(school_config, 'get', lambda k: {'status': 'onboarding' if k == 'newu' else 'released'})
    assert L.onboarding('newu') and not L.onboarding('mit')
    # the school-local summary has its own data name; the shared one stays a different (tracked, release-written) file
    assert 'labpage-audit-summary-school.json' in str(P.data('labpage-audit-summary-school.json', 'newu'))
    assert P.data('labpage-audit-summary-school.json', 'newu') != P.data('labpage-audit-summary.json')


def test_a_stated_end_year_makes_the_entry_an_alumnus():
    f = L.entry_years_end_the_stay
    assert f([None, 2024], 'stated_in_entry') and f([2022, 2025], 'stated_in_entry') and f([None, 2026], 'stated_in_entry')
    assert not f([2022, 2026], 'stated_in_entry') and not f([2022, None], 'stated_in_entry') and not f(None, 'none')
    assert not f([None, 2020], 'section_year_heading')
