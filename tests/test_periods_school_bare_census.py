"""periods_school reads a bare-list census and a school without rows.json (hand-composed released schools)."""
import json
import periods_school as PS  # noqa: E402
import atlas_paths as P  # noqa: E402


def test_bare_list_census_and_missing_rows(tmp_path, monkeypatch):
    (tmp_path / 'census-faculty.json').write_text(json.dumps([{'name': 'A B', 'is_pi': True}]))
    monkeypatch.setattr(P, 'data', lambda name, school=None, root=None, layout=None: tmp_path / name)
    assert PS.census_faculty('x') == [{'name': 'A B', 'is_pi': True}]
    assert PS.rows_of('x') == []
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': [{'name': 'C D'}]}))
    assert PS.census_faculty('x') == [{'name': 'C D'}]
    (tmp_path / 'rows.json').write_text('[{"name": "C D"}]')
    assert PS.rows_of('x') == [{'name': 'C D'}]
