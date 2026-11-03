"""An onboarding school's reviewed census overrides live in its own file; the shared tracked file is never written for it."""
import json

import atlas_paths as P
import census_overrides as CO


def setup(tmp_path, monkeypatch, status):
    monkeypatch.setattr(P, 'data', lambda name, school=None, root=None, **k: tmp_path / ((school or '_') + '-' + name))
    monkeypatch.setattr(P, 'data_w', lambda name, school=None, **k: P.data(name, school))
    monkeypatch.setattr(CO.S, 'get', lambda k: {'status': status})
    shared = tmp_path / '_-census-overrides.json'
    shared.write_text(json.dumps({'u': {'Ann': {'why': 'shared'}}, 'mit': {'Bo': {}}}, indent=1))
    return shared


def test_onboarding_writes_its_own_file_and_reads_both(tmp_path, monkeypatch):
    shared = setup(tmp_path, monkeypatch, 'onboarding')
    before = shared.read_text()
    sec, save = CO.open_section('u')
    sec['Cy'] = {'periods': [1]}
    save()
    assert shared.read_text() == before                      # the tracked shared file is untouched
    assert json.loads((tmp_path / 'u-census-overrides-school.json').read_text()) == {'Cy': {'periods': [1]}}
    assert CO.section('u') == {'Ann': {'why': 'shared'}, 'Cy': {'periods': [1]}}
    (tmp_path / 'u-census-overrides-school.json').write_text(json.dumps({'Ann': {'periods': [2]}}))
    assert CO.section('u')['Ann'] == {'why': 'shared', 'periods': [2]}


def test_a_released_school_still_edits_the_shared_file(tmp_path, monkeypatch):
    shared = setup(tmp_path, monkeypatch, 'released')
    sec, save = CO.open_section('mit')
    sec['Di'] = {}
    save()
    ov = json.loads(shared.read_text())
    assert set(ov['mit']) == {'Bo', 'Di'} and 'u' in ov and not (tmp_path / 'mit-census-overrides-school.json').exists()


def test_oa_identity_review_file_is_optional(tmp_path, monkeypatch):
    import oa_identity_school as O
    monkeypatch.setattr(O.P, 'data', lambda name, school=None, **k: tmp_path / name)
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': []}))
    (tmp_path / 'cs-related-review.json').write_text(json.dumps({'decisions': []}))
    assert O.wanted('u') == {}
