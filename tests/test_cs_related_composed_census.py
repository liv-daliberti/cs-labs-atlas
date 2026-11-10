"""Stage-2 candidates tool on the composed-school census layouts (ZJU: a bare list, no sweep, no dblp-affiliated file)."""
import json

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


def test_stage_gate_pis_of_accepts_a_bare_list_census(tmp_path, monkeypatch):
    import stage_gate as G
    files = {'census-faculty.json': [{'name': 'A', 'is_pi': True}, {'name': 'B', 'is_pi': False}], 'census-additions.json': [{'name': 'C', 'is_pi': True}]}
    for n, v in files.items():
        (tmp_path / n).write_text(json.dumps(v))
    monkeypatch.setattr(G.P, 'data', lambda name, key=None, *a, **k: tmp_path / name)
    assert [x['name'] for x in G.pis_of('zju')] == ['A', 'C']
