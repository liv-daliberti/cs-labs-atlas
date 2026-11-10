import hashlib
import json

import pytest

import census_build as C


def test_explicit_source_backed_alias_merges_only_named_groups(tmp_path, monkeypatch):
    raw = b'<p>Danfeng (Daphne) Yao is a professor.</p>'
    (tmp_path / 'alias.html').write_bytes(raw)
    doc = {'school': 'vt', 'rows': [{'name_a': 'Danfeng Yao', 'name_b': 'Daphne Yao',
           'evidence': {'raw_path': 'alias.html', 'sha256': hashlib.sha256(raw).hexdigest(),
                        'quote': 'Danfeng (Daphne) Yao', 'additional_quote': 'is a professor'}}]}
    p = tmp_path / 'aliases.json'
    p.write_text(json.dumps(doc))
    monkeypatch.setattr(C.P, 'ROOT', tmp_path)
    monkeypatch.setattr(C.P, 'data', lambda name, key=None, *a, **k: p)
    pairs = C.reviewed_name_aliases('vt')
    rows = [{'name': 'Danfeng Yao', 'observed': '2022'},
            {'name': 'Daphne Yao', 'observed': '2025'},
            {'name': 'Danfeng Li', 'observed': '2025'}]
    groups = C.merge_people(rows, pairs)
    assert len(groups) == 2
    assert {'Danfeng Yao', 'Daphne Yao'} in [set(g['names']) for g in groups]
    doc['rows'][0]['evidence']['quote'] = 'another person'
    p.write_text(json.dumps(doc))
    with pytest.raises(AssertionError):
        C.reviewed_name_aliases('vt')
    doc['rows'][0]['evidence']['quote'] = 'Danfeng (Daphne) Yao'
    doc['rows'][0]['evidence']['additional_quote'] = 'another person'
    p.write_text(json.dumps(doc))
    with pytest.raises(AssertionError):
        C.reviewed_name_aliases('vt')
