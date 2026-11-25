import lab_websites as W

RR = {'reviewer': 'r', 'reviewed_on': '2026-11-25', 'why': 'accepted in the reviewed register'}


def doc(*labs):
    return {'school': 'x', 'labs': list(labs)}


def test_retained_row_survives_a_refresh():
    prev = doc({'pi': 'A', 'coverage': 'website', 'url': 'http://a/', 'retained_review': RR})
    cur = doc({'pi': 'A', 'coverage': 'pending', 'url': None})
    out = W.preserve_reviewed_entries(prev, cur)
    assert out['labs'][0]['coverage'] == 'website' and out['labs'][0]['preserved_review_on_refresh']


def test_retained_row_under_an_alias_moves_to_the_canonical_key():
    prev = doc({'pi': 'Pascale Fung', 'coverage': 'website', 'url': 'http://p/', 'retained_review': RR})
    cur = doc({'pi': 'Pascale FUNG', 'coverage': 'pending'})
    out = W.preserve_reviewed_entries(prev, cur, aliases={'Pascale FUNG': ['Pascale FUNG', 'Pascale Fung']})
    assert out['labs'][0]['pi'] == 'Pascale FUNG' and out['labs'][0]['alias_of'] == 'Pascale Fung' and out['labs'][0]['url'] == 'http://p/'


def test_row_without_a_complete_retained_review_is_refreshed():
    prev = doc({'pi': 'A', 'coverage': 'website', 'url': 'http://a/', 'retained_review': {'reviewer': 'r'}})
    cur = doc({'pi': 'A', 'coverage': 'pending'})
    assert W.preserve_reviewed_entries(prev, cur)['labs'][0]['coverage'] == 'pending'


def test_verification_never_rejects_a_retained_row(monkeypatch, tmp_path):
    RRR = {'reviewer': 'r', 'reviewed_on': '2026-11-25', 'why': 'accepted'}
    page_less = {'pi': 'Ann Lee', 'coverage': 'website', 'url': 'https://x.example/~al/', 'sha256': 'a' * 64, 'checks': [], 'retained_review': RRR}
    plain = {'pi': 'Bob Ray', 'coverage': 'website', 'url': 'https://x.example/~br/', 'sha256': 'b' * 64, 'checks': []}
    monkeypatch.setattr(W.P, 'data', lambda name, school=None, **k: tmp_path / name)
    monkeypatch.setattr(W, 'capture_stores', lambda school: [])
    monkeypatch.setattr(W, 'wayback_captures', lambda school: {})
    monkeypatch.setattr(W, 'website_review', lambda school, near=None: {})
    monkeypatch.setattr(W, 'school_domains', lambda school: [])
    out = W.verify_websites('x', {'school': 'x', 'labs': [dict(page_less), dict(plain)]})
    kept, other = out['labs']
    assert kept['coverage'] == 'website' and kept['url'] == 'https://x.example/~al/' and 'verified' not in kept
    assert other.get('verified') is False   # an unreviewed row is still checked (no stored capture)
