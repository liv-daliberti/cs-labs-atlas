import json

import oa_identity_school as O


def test_wanted_applies_reviewed_decisions_when_the_stage2_review_is_absent(tmp_path, monkeypatch, capsys):
    (tmp_path / 'openalex-identity-review.json').write_text(json.dumps({'decisions': {'A B': {'openalex': ['A1'], 'why': 'w'}}}))
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': [{'name': 'A B'}]}))
    monkeypatch.setattr(O.P, 'data', lambda name, key=None: tmp_path / name)
    out = O.wanted('x')
    assert out['A B']['openalex'] == ['https://openalex.org/A1'] and out['A B']['basis'] == 'reviewed'
    assert 'stage-2 candidates pending' in capsys.readouterr().err
