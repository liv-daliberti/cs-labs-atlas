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
