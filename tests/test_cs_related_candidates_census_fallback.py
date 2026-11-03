"""cs_related_candidates reads census PIs when a school has no pis.json yet (a school being onboarded, stage 2)."""
import json

import atlas_paths as P
import cs_related_candidates as C
import stage_gate


def test_school_pis_falls_back_to_the_census(tmp_path, monkeypatch):
    monkeypatch.setattr(P, 'data', lambda name, school=None, **k: tmp_path / name)
    monkeypatch.setattr(stage_gate, 'pis_of', lambda s: [{'name': 'Ann Lee', 'aliases': ['A. Lee']}])
    assert C.school_pis('newu') == [{'pi': 'Ann Lee', 'names': ['Ann Lee', 'A. Lee']}]
    (tmp_path / 'pis.json').write_text(json.dumps([{'pi': 'Bo Wu'}]))
    assert C.school_pis('newu') == [{'pi': 'Bo Wu'}]
