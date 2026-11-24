"""An incomplete source overlay must never erase an established faculty census."""
import json

import pytest

import census_build as C


@pytest.mark.parametrize('source_content', [None, [], {}])
def test_missing_or_empty_listing_rows_preserve_existing_outputs(tmp_path, monkeypatch, source_content):
    rows = tmp_path / 'rows.json'
    census = tmp_path / 'census-faculty.json'
    prior = b'{"faculty": [{"name": "Established Faculty"}]}\n'
    census.write_bytes(prior)
    if source_content is not None:
        rows.write_text(json.dumps(source_content))
    monkeypatch.setattr(C.S, 'get', lambda key: {'window': [2016, 2026], 'departments': []})
    monkeypatch.setattr(C.P, 'data', lambda name, key: rows if name == 'rows.json' else tmp_path / name)
    monkeypatch.setattr(C.P, 'data_w', lambda *args, **kwargs: pytest.fail('No output may be opened before source validation'))
    with pytest.raises(SystemExit, match='existing census outputs were preserved'):
        C.main('example')
    assert census.read_bytes() == prior
