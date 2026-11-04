"""cs_related_candidates reads census PIs when a school has no pis.json yet (a school being onboarded, stage 2)."""
import json

import atlas_paths as P
import cs_related_candidates as C


def test_school_pis_for_an_onboarding_school_are_the_census_pis_never_the_built_pis_json(tmp_path, monkeypatch):
    monkeypatch.setattr(P, 'data', lambda name, school=None, **k: tmp_path / name)
    monkeypatch.setattr(C.CO if hasattr(C, 'CO') else __import__('census_overrides'), 'onboarding', lambda k: k == 'newu')
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': [{'name': 'Ann Lee', 'aliases': ['A. Lee'], 'is_pi': True}, {'name': 'Bo', 'is_pi': False}]}))
    (tmp_path / 'pis.json').write_text(json.dumps([{'pi': 'Added Person'}]))   # the previous review's additions live here: not read
    assert C.school_pis('newu') == [{'pi': 'Ann Lee', 'names': ['Ann Lee', 'A. Lee']}]
    assert C.school_pis('released') == [{'pi': 'Added Person'}]


def test_school_test_gates_a_related_lineage_child(monkeypatch):
    import re
    monkeypatch.setattr(C.S, 'inst_ids', lambda k: ['I1'])
    monkeypatch.setattr(C.S, 'sweep_ids', lambda k: ['I1', 'I7'])
    monkeypatch.setattr(C.S, 'aff_rx', lambda k: re.compile('University of Chicago', re.I))
    ok = C.school_test('u')
    O = 'https://openalex.org/'
    arg = {'id': O + 'I7', 'lineage': [O + 'I7', O + 'I1']}
    assert not ok({'institutions': [arg], 'raw_affiliation_strings': ['Argonne National Laboratory']})
    assert ok({'institutions': [arg], 'raw_affiliation_strings': ['University of Chicago and Argonne']})
    assert ok({'institutions': [{'id': O + 'I1', 'lineage': [O + 'I1']}, arg], 'raw_affiliation_strings': ['x']})
