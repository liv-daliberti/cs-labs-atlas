"""Native source-reviewed faculty merges retain older relationship and recovery keys."""
import json

import pytest

import atlas_paths as P
from pihier.students import merged_alias_spellings, renamed_pis


def test_native_merge_routes_historical_student_and_publication_spelling(tmp_path, monkeypatch):
    path = tmp_path / 'aliases.json'
    path.write_text(json.dumps(dict(rows=[], native_pi_merges=[
        dict(canonical='Jiahai Yang', aliases=['杨家海（校内兼职）'])])))
    monkeypatch.setattr(P, 'data', lambda *a, **kw: path)
    pis = [dict(pi='Jiahai Yang'), dict(pi='Another PI', censusName='Old spelling')]
    assert renamed_pis(pis, 'tsinghua', tmp_path) == {
        'Old spelling': 'Another PI', '杨家海（校内兼职）': 'Jiahai Yang'}


def test_native_alias_cannot_redirect_an_existing_distinct_lab(tmp_path, monkeypatch):
    path = tmp_path / 'aliases.json'
    path.write_text(json.dumps(dict(rows=[], native_pi_merges=[dict(canonical='Ada', aliases=['Bea'])])))
    monkeypatch.setattr(P, 'data', lambda *a, **kw: path)
    with pytest.raises(ValueError, match='Conflicting'):
        merged_alias_spellings('school', [dict(pi='Ada'), dict(pi='Bea')], tmp_path)
    assert merged_alias_spellings('school', [dict(pi='Bea')], tmp_path) == {}
