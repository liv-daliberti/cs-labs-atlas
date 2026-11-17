"""schools/<key>.toml (tools/school_config.py): every charter is valid, the released list is atlas_paths.SCHOOL_IDS, and
the released charters say what the builder's own tables say (until pi_hierarchy.py reads the charters itself)."""
import re

import atlas_paths as P
import school_config as S


def test_charters_pass_their_checks():
    assert [p for k in S.keys() for p in S.check(k)] == []


def test_released_is_school_ids():
    assert S.released() == P.SCHOOL_IDS
    assert P.SCHOOL_IDS[:6] == ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']


def test_onboarding_school_is_not_released():
    for k in S.onboarding():
        assert k not in P.SCHOOL_IDS


def test_released_charters_match_the_builder():
    import pi_hierarchy as PH
    for k in S.released():
        assert S.inst(k) == PH.INST[k]
        assert S.aff(k) == PH.AFF[k]
        if S.dblp_sweep(k):
            assert S.dblp_sweep(k) == PH.DBLP.get(k)


def test_michigan_affiliation():
    rx = S.aff_rx('michigan')
    assert rx.search('Dept. of EECS, University of Michigan, Ann Arbor')
    assert not rx.search('University of Michigan-Dearborn')
    assert not rx.search('Michigan State University, East Lansing')
    assert 'I27837315' in S.inst_ids('michigan') and 'I4210130704' not in S.sweep_ids('michigan')


def test_template_names_every_section():
    t = (P.SCHOOL_CONFIGS / 'TEMPLATE.toml').read_text()
    for sec in ('[ids]', '[web]', '[affiliation]', '[dblp]', '[[departments]]', '[thesis]', '[store]', '[[hosts]]'):
        assert sec in t
    assert re.search(r'^status = "onboarding"', t, re.M)


def test_affiliated_unit_slots_are_read_like_department_slots_but_stay_affiliated():
    cfg = dict(departments=[dict(code='A', coverage='full', listings=[dict(slot='a', url='x', kind='main')])],
               affiliated_units=[dict(code='U', name='Unit', slots=[dict(slot='u', url='y', kind='main', format='f')]),
                                 dict(code='V', name='No slots', listings=[])])
    units = S.listing_units(cfg)
    assert [(u['code'], u['coverage']) for u in units] == [('A', 'full'), ('U', 'affiliated')]
    assert units[1]['listings'][0]['slot'] == 'u'
    assert [d['code'] for d in cfg['departments']] == ['A']   # stage 1 (stage_gate.g1) reads only [[departments]]


def test_zju_cst_and_cadcg_are_affiliated_units():
    cfg = S.get('zju')
    assert {d['code'] for d in cfg['departments']} == {'CS_MAIN'}
    slots = {s['dept']: s for s in S.listing_slots('zju')}
    assert {'CST', 'CADCG', 'CS_MAIN'} <= {s['dept'] for s in S.listing_slots('zju')}
    assert {u['code'] for u in cfg['affiliated_units'] if u.get('slots')} == {'CST', 'CADCG'} and slots
