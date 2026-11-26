"""oa_identity_school.wanted(): the hand review is optional and so is the stage-2 cs-related review (its absence adds no share-test ids)."""
import json
import atlas_paths as P  # noqa: E402
import oa_identity_school as O  # noqa: E402


def setup(tmp_path, monkeypatch, review=None, cs=None):
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': [{'name': 'Ann Lee'}, {'name': 'Bo Chu'}]}))
    if review is not None:
        (tmp_path / 'openalex-identity-review.json').write_text(json.dumps({'decisions': review}))
    if cs is not None:
        (tmp_path / 'cs-related-review.json').write_text(json.dumps({'decisions': cs}))
    monkeypatch.setattr(P, 'data', lambda name, school=None, root=None, layout=None: tmp_path / name)
    monkeypatch.setattr(O.S, 'get', lambda k: {'name': 'Newu'})


def test_without_a_cs_related_review_only_the_hand_decisions_are_returned(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, review={'Ann Lee': dict(openalex=['A1'], why='hand')})
    got = O.wanted('x')
    assert list(got) == ['Ann Lee'] and got['Ann Lee']['basis'] == 'reviewed'


def test_an_accepted_share_test_person_is_added_when_the_review_exists(tmp_path, monkeypatch):
    cs = [dict(decision='accepted', name='Bo Chu', cs_basis=dict(openalex_share=dict(result='computing', ids=['A2'], authors=[dict(author='https://openalex.org/A2', basis='orcid')])))]
    setup(tmp_path, monkeypatch, review={'Ann Lee': dict(openalex=['A1'], why='hand')}, cs=cs)
    got = O.wanted('x')
    assert set(got) == {'Ann Lee', 'Bo Chu'} and got['Bo Chu']['basis'] == 'share_test'
