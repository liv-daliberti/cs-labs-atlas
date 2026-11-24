"""Stage-2 candidates tool on the composed-school census layouts (ZJU: a bare list, no sweep, no dblp-affiliated file)."""
import json
import hashlib

import pytest

import cs_related_school as C


def test_census_rows_accepts_list_dict_and_missing():
    rows = [{'name': 'A B', 'sources': []}]
    assert C.census_rows(rows) == rows
    assert C.census_rows({'faculty': rows}) == rows
    assert C.census_rows(None) == []
    assert C.census_rows([{'no_name': 1}, 'x']) == []


def test_candidates_runs_on_a_bare_list_census(tmp_path, monkeypatch):
    census = tmp_path / 'census.json'
    census.write_text(json.dumps([{'name': 'Kui Ren', 'departments': ['ICSR'], 'sources': [{'kind': 'preserved_named_official_ICSR_faculty'}]}]))
    out = tmp_path / 'out.json'
    monkeypatch.setattr(C.P, 'data', lambda name, key=None, *a, **k: census if name == 'census-faculty.json' else tmp_path / name)
    monkeypatch.setattr(C.P, 'data_w', lambda name, key=None, *a, **k: out)
    monkeypatch.setattr(C.S, 'get', lambda key: {'departments': [{'code': 'ICSR', 'coverage': 'full'}]})
    C.candidates('zju')
    assert json.loads(out.read_text()) == []


def test_source_checked_ladder_profile_enters_candidate_review_without_dblp(tmp_path, monkeypatch):
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': [
        {'name': 'Ada Example', 'is_pi': True, 'sources': []},
        {'name': 'Nora Courtesy', 'is_pi': False, 'sources': []},
    ]}))
    (tmp_path / 'cs-related-hand.json').write_text(json.dumps([
        {'name': 'Grace Hopper', 'unit': 'ECE', 'url': 'https://example.edu/grace', 'sha256': 'a' * 64, 'ladder': True},
        {'name': 'Alan Teaching', 'unit': 'ECE', 'url': 'https://example.edu/alan', 'sha256': 'b' * 64, 'ladder': False},
        {'name': 'Ada Example', 'unit': 'ECE', 'url': 'https://example.edu/ada', 'sha256': 'c' * 64, 'ladder': True},
        {'name': 'Nora Courtesy', 'unit': 'ECE', 'url': 'https://example.edu/nora', 'sha256': 'd' * 64, 'ladder': True},
    ]))
    monkeypatch.setattr(C.P, 'data', lambda name, key=None, *a, **k: tmp_path / name)
    monkeypatch.setattr(C.P, 'data_w', lambda name, key=None, *a, **k: tmp_path / name)
    monkeypatch.setattr(C.S, 'get', lambda key: {'departments': [{'code': 'CS', 'coverage': 'full'}]})
    C.candidates('sample')
    rows = json.loads((tmp_path / 'cs-related-candidates.json').read_text())
    assert [(r['name'], r['source']) for r in rows] == [
        ('Grace Hopper', 'official_profile_ladder'), ('Nora Courtesy', 'official_profile_ladder')]


def test_stage_gate_pis_of_accepts_a_bare_list_census(tmp_path, monkeypatch):
    import stage_gate as G
    files = {'census-faculty.json': [{'name': 'A', 'is_pi': True}, {'name': 'B', 'is_pi': False}], 'census-additions.json': [{'name': 'C', 'is_pi': True}]}
    for n, v in files.items():
        (tmp_path / n).write_text(json.dumps(v))
    monkeypatch.setattr(G.P, 'data', lambda name, key=None, *a, **k: tmp_path / name)
    assert [x['name'] for x in G.pis_of('zju')] == ['A', 'C']


def test_cs_related_candidates_school_pis_accepts_a_bare_list_census(tmp_path, monkeypatch):
    import cs_related_candidates as K
    (tmp_path / 'c.json').write_text(json.dumps([{'name': 'A B', 'is_pi': True}]))
    (tmp_path / 'a.json').write_text(json.dumps([{'name': 'C D', 'is_pi': True, 'aliases': ['Cd']}]))
    monkeypatch.setattr(K.P, 'data', lambda name, s=None, *a, **k: tmp_path / {'census-faculty.json': 'c.json', 'census-additions.json': 'a.json'}.get(name, 'none.json'))
    import census_overrides as CO
    monkeypatch.setattr(CO, 'onboarding', lambda s: True)
    assert [p['pi'] for p in K.school_pis('zju')] == ['A B', 'C D']


def test_stage_two_does_not_merge_same_named_candidate_identities(tmp_path, monkeypatch):
    import stage_gate as G
    candidates = [
        {'name': 'Dong Li', 'source': 'dblp_affiliation', 'dblp': 'https://dblp.org/pid/1'},
        {'name': 'Dong Li', 'source': 'dblp_affiliation', 'dblp': 'https://dblp.org/pid/2'},
    ]
    (tmp_path / 'cs-related-candidates.json').write_text(json.dumps(candidates))
    (tmp_path / 'cs-related-review.json').write_text(json.dumps({'decisions': [
        {'name': 'Dong Li', 'decision': 'accepted', 'reason': 'one source identity reviewed'}]}))
    monkeypatch.setattr(G.P, 'data', lambda name, key=None, *a, **k: tmp_path / name)
    monkeypatch.setattr(G, 'sweep_gate', lambda key: [])
    bad, _ = G.g2('sample')
    assert any('2 candidate identities share a display name' in item for item in bad)


def test_stage_two_accepts_separate_terminal_reviews_for_each_source_id(tmp_path, monkeypatch):
    import stage_gate as G
    candidates = [
        {'name': 'Dong Li', 'source': 'dblp_affiliation', 'dblp': 'https://dblp.org/pid/1'},
        {'name': 'Dong Li', 'source': 'dblp_affiliation', 'dblp': 'https://dblp.org/pid/2'},
    ]
    (tmp_path / 'cs-related-candidates.json').write_text(json.dumps(candidates))
    (tmp_path / 'cs-related-review.json').write_text(json.dumps({'decisions': [
        {'name': 'Dong Li', 'source_id': c['dblp'], 'decision': 'not_faculty_listed',
         'reason': 'reviewed source identity', 'cs_basis': {'dblp': [c['dblp']]}}
        for c in candidates]}))
    monkeypatch.setattr(G.P, 'data', lambda name, key=None, *a, **k: tmp_path / name)
    monkeypatch.setattr(G, 'sweep_gate', lambda key: [])
    assert G.g2('sample')[0] == []


def test_reviewed_pid_exclusion_requires_saved_source_quote_and_hash(tmp_path, monkeypatch):
    body = b'<html><body>Lei Zhang was a Ph.D. student in Computer Science.</body></html>'
    (tmp_path / 'source.html').write_bytes(body)
    row = {'source': 'dblp_affiliation', 'source_id': 'https://dblp.org/pid/97/8704-158',
           'decision': 'exclude_nonfaculty_vt', 'evidence': {'raw_path': 'source.html',
           'raw_sha256': hashlib.sha256(body).hexdigest(), 'format': 'html',
           'quotes': ['Lei Zhang was a Ph.D. student in Computer Science.']}}
    path = tmp_path / 'decisions.json'
    path.write_text(json.dumps({'school': 'vt', 'records': [row]}))
    monkeypatch.setattr(C.P, 'ROOT', tmp_path)
    monkeypatch.setattr(C.P, 'data', lambda name, key=None, *a, **k: path)
    assert C.source_exclusions('vt') == {'https://dblp.org/pid/97/8704-158'}
    row['evidence']['quotes'] = ['Professor Lei Zhang']
    path.write_text(json.dumps({'school': 'vt', 'records': [row]}))
    with pytest.raises(AssertionError):
        C.source_exclusions('vt')


def test_michigan_pid_exclusion_binds_official_homepage_to_exact_dblp_record(tmp_path, monkeypatch):
    body = b'<h1>Yan Chen</h1><p>Assistant Professor at Virginia Tech; 2020 Michigan Ph.D.</p><a href="https://personal.example/">Homepage</a>'
    (tmp_path / 'source.html').write_bytes(body)
    row = {'source': 'dblp_affiliation', 'source_id': 'https://dblp.org/pid/88/2827-33',
           'name': 'Yan Chen', 'decision': 'exclude_nonfaculty_michigan',
           'source_id_basis': {'homepage': 'https://personal.example/'},
           'evidence': {'raw_path': 'source.html', 'raw_sha256': hashlib.sha256(body).hexdigest(),
                        'format': 'html', 'quotes': ['Assistant Professor at Virginia Tech']}}
    files = {'cs-related-source-exclusions.json': tmp_path / 'decisions.json',
             'dblp-affiliated.json': tmp_path / 'dblp.json'}
    files['cs-related-source-exclusions.json'].write_text(json.dumps({'school': 'michigan', 'records': [row]}))
    files['dblp-affiliated.json'].write_text(json.dumps({'persons': [{'pid': row['source_id'], 'names': ['Yan Chen 0033'],
                                                                     'urls': ['https://personal.example/']}]}))
    monkeypatch.setattr(C.P, 'ROOT', tmp_path)
    monkeypatch.setattr(C.P, 'data', lambda name, key=None, *a, **k: files[name])
    assert C.source_exclusions('michigan') == {row['source_id']}
    row['source_id_basis']['homepage'] = 'https://wrong.example/'
    files['cs-related-source-exclusions.json'].write_text(json.dumps({'school': 'michigan', 'records': [row]}))
    with pytest.raises(AssertionError):
        C.source_exclusions('michigan')
