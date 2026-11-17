"""pi_states (process v4): stage 3-7 findings are attributed to the PI they name; school items stay school items; ratchet gaps never hold a PI."""
import pi_states as PS
import stage_gate as SG


def setup(monkeypatch, items_by_stage, pis=('A B', 'C D'), waived=None, ledger=None, excluded=None):
    monkeypatch.setattr(SG, 'pis_of', lambda key: [dict(name=n, aliases=[]) for n in pis])
    monkeypatch.setattr(SG, 'evaluate', lambda key, st: dict(items=list(items_by_stage.get(st, [])), waived_items=list((waived or {}).get(st, []))))
    monkeypatch.setattr(PS, '_ledger', lambda key: ledger or {})
    monkeypatch.setattr(PS, '_build_excluded', lambda key: excluded or {})
    monkeypatch.setattr(SG.CO, 'section', lambda key: {})
    import chain_audit
    monkeypatch.setattr(chain_audit, 'audit', lambda key: dict(checks={}))
    import downloads_ready as DR
    monkeypatch.setattr(DR, 'pi_status', lambda key: {n: dict(name=n, period='period', identity='dblp', reasons=[]) for n in pis})


def test_item_is_attributed_to_its_pi_only(monkeypatch):
    setup(monkeypatch, {'4': ['A B: no period, listing years []'], '3': ['lab-page audit: register missing']})
    r = PS.compute('x')
    assert r['pis']['A B']['4']['state'] == 'open' and r['pis']['C D']['4']['state'] == 'done'
    assert r['open_pis'] == ['A B'] and r['school_items']['3'] == ['lab-page audit: register missing']
    assert r['pis']['C D']['downloadable']          # C D is not held by A B's open item or the school item


def test_waived_item_is_an_exclusion_with_reason(monkeypatch):
    item = 'C D: no accepted home department'
    setup(monkeypatch, {'3': [item]}, waived={'3': [item]})
    r = PS.compute('x')
    assert r['pis']['C D']['3']['state'] == 'excluded_with_reason' and r['open_pis'] == []


def test_ratchet_gap_is_open_but_not_a_release_blocker_per_pi(monkeypatch):
    setup(monkeypatch, {}, ledger={'A B': dict(pi='A B', lab_state='gap', lab_cause='thin_lab_papers')})
    r = PS.compute('x')
    assert r['pis']['A B']['5']['state'] == 'open' and r['open_pis'] == [] and r['counts']['5']['open_ratchet_only'] == 1
    assert r['pis']['A B']['downloadable']          # a coverage gap never holds downloads


def test_census_finding_holds_that_pi_downloads(monkeypatch):
    setup(monkeypatch, {'2': ['A B: 2 candidate identities share a display name; resolve source IDs before admission', 'Z Z: no decision']})
    import downloads_ready as DR
    r = PS.compute('x')
    assert r['pis']['A B']['census']['state'] == 'open' and not r['pis']['A B']['downloadable'] and r['pis']['C D']['downloadable']
    assert r['school_items']['2'] == ['Z Z: no decision']     # not a PI: school item, holds nobody
    assert DR.census_holds  # the downloads rule reads the same attribution


def test_excluded_by_build_review(monkeypatch):
    setup(monkeypatch, {'4': ['A B: no period']}, excluded={'A B': 'not a PI in the window'})
    r = PS.compute('x')
    assert r['pis']['A B']['state'] == 'excluded_with_reason' and not r['pis']['A B']['downloadable'] and r['open_pis'] == []


def test_release_findings_need_every_pi_and_school_item(monkeypatch):
    setup(monkeypatch, {'6': ['lab-page students acceptance: not accepted'], '3': ['A B: PI basis without url/sha256/quote']})
    bad = PS.release_findings('x')
    assert any('PI A B is open' in b for b in bad) and any('school item' in b and 'acceptance' in b for b in bad)


def test_chain_audit_items_are_per_pi_and_follow_a_waiver_of_their_summary(monkeypatch):
    import chain_audit
    rows = {'links': dict(unexplained=[dict(key='A B | S | id', pi='A B'), dict(key='no-pi-row')])}
    monkeypatch.setattr(chain_audit, 'audit', lambda key: dict(checks=rows))
    setup(monkeypatch, {'7': ['links: 2 unexplained of 9']})
    monkeypatch.setattr(chain_audit, 'audit', lambda key: dict(checks=rows))
    r = PS.compute('x')
    assert r['pis']['A B']['7']['state'] == 'open' and r['pis']['C D']['7']['state'] == 'done' and r['school_items']['7'] == ['chain audit links: no-pi-row']
    setup(monkeypatch, {'7': ['links: 2 unexplained of 9']}, waived={'7': ['links: 2 unexplained of 9']})
    monkeypatch.setattr(chain_audit, 'audit', lambda key: dict(checks=rows))
    r = PS.compute('x')
    assert r['pis']['A B']['7']['state'] == 'excluded_with_reason' and r['open_pis'] == []


def test_gate10_judges_pis_of_onboarding_schools_only(monkeypatch):
    import school_config as S
    setup(monkeypatch, {'3': ['A B: PI basis without url/sha256/quote']})
    monkeypatch.setattr(S, 'get', lambda key: dict(status='released'))
    monkeypatch.setattr(SG, 'read', lambda p, default=None: {'counts': {'x': {}}})
    assert SG.g10('x')[0] == []
    monkeypatch.setattr(S, 'get', lambda key: dict(status='onboarding'))
    assert any('PI A B is open' in b for b in SG.g10('x')[0])
