"""Accepted CS-related decisions without a census row become census-additions rows (VT, 2026-11-18)."""
import json

import census_additions_from_review as A


def ev(q='A B Professor', unit='ECE'):
    return dict(unit=unit, url='https://x.edu/ab', sha256='a' * 64, observed='20261110', quote=q, ladder=True)


def test_missing_adds_only_accepted_ladder_people_not_in_census(tmp_path, monkeypatch):
    census = [dict(name='Thomas Hou', aliases=[], is_pi=False)]
    review = dict(decisions=[
        dict(name='A B', aliases=['Ab'], decision='accepted', faculty_evidence=[ev()], cs_basis=dict(dblp=['https://dblp.org/pid/1/2'], dblp_window=9), years_listed=[2026]),
        dict(name='Walid Saad', aliases=[], decision='accepted', faculty_evidence=[ev()], cs_basis={}),
        dict(name='Y. Thomas Hou 0001', aliases=['Thomas Hou'], decision='accepted', faculty_evidence=[ev()], cs_basis={}),
        dict(name='C D', aliases=[], decision='research_or_other_rank', faculty_evidence=[ev()]),
        dict(name='E F', aliases=[], decision='accepted', faculty_evidence=[dict(ev(), ladder=False)]),
    ])
    (tmp_path / 'census-faculty.json').write_text(json.dumps(dict(faculty=census + [dict(name='Walid Saad 0001', aliases=['Walid Saad'])])))
    (tmp_path / 'cs-related-review.json').write_text(json.dumps(review))
    monkeypatch.setattr(A.P, 'data', lambda name, key=None, *a, **k: tmp_path / name)
    out = A.missing('vt', '20261118')
    assert [e['name'] for e in out] == ['A B']
    e = out[0]
    assert e['is_pi'] and e['collection_person_id'] == 'vt_fac_a-b' and e['dblp'] == ['https://dblp.org/pid/1/2']
    assert e['pi_basis']['kind'] == 'ladder_faculty' and e['sources'][0]['kind'] == 'unit_listing:ECE'
