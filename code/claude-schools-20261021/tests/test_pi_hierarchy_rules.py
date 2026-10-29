"""Today's (2026-10-29) rules in tools/pi_hierarchy.py, on the real cases that motivated them."""
import collections

import pytest

import pi_hierarchy as h


# ---- the given-name guard on student byline links ------------------------------------------------------------------

@pytest.mark.parametrize('student, byline', [
    ('Wei-Ning Chen', 'Wei-Chen Chen'),        # the case that started the guard: three letters apart
    ('Yu-Han Chen', 'Yu-Hsin Chen'),
    # East Asian family names: a given name that is a prefix of another is a different common name
    ('Xinyu Li', 'Xin Li'),
    ('Xin Li', 'Xinyu Li'),
    ('Xiaoyuan Liu', 'Xiao Liu'),
    ('Ruihan Zhao', 'Rui Zhao'),
    ('Seung Hyun Lee', 'Seunghak Lee'),
])
def test_given_conflict_different_people(student, byline):
    assert h.given_conflict([student], byline)


@pytest.mark.parametrize('student, byline', [
    ('Avinash Boppana', 'Avi Boppana'),        # 3+ letter prefix, not an East Asian family name
    ('Avi Boppana', 'Avinash Boppana'),
    ('Abigail See', 'Abi See'),
    ('Abi See', 'Abigail See'),
    ('Johann Paratte', 'Johan Paratte'),       # one-letter spelling variant of a 4+ letter name
    ('Kiryong Ha', 'Kirong Ha'),               # ... allowed under an East Asian family name too
    ('Kirong Ha', 'Kiryong Ha'),
    ('Xiang Lisa Li', 'Lisa Li'),              # a middle name used as the preferred given name
    ('Hong-Xing Yu', 'Hongxing Yu'),           # hyphen/space variants
    ('Dylan M. Paiton', 'Paiton Dylan'),       # family name first
    ('Wei-Ning Chen', 'W. Chen'),              # an initial is never a conflict
])
def test_given_conflict_allowed(student, byline):
    assert not h.given_conflict([student], byline)


def test_given_conflict_strict_is_the_literal_guard():
    # the owner's literal guard would remove prefix and spelling variants; the build only counts those (kept_prefix_or_spelling_variant)
    assert h.given_conflict(['Avinash Boppana'], 'Avi Boppana', strict=True)
    assert h.given_conflict(['Johann Paratte'], 'Johan Paratte', strict=True)
    assert not h.given_conflict(['Xiang Lisa Li'], 'Lisa Li', strict=True)


def test_given_conflict_recurring_one_letter_variant():
    # Yuxin Chen's roster says 'Gene Li', his papers say 'Gen Li': allowed on 3+ of the lab's papers, not on 2
    lab = {'Yuxin Chen': {'gene li'}}
    three = collections.Counter({('Yuxin Chen', 'gen li'): 3})
    two = collections.Counter({('Yuxin Chen', 'gen li'): 2})
    assert not h.given_conflict(['Gene Li'], 'Gen Li', pi='Yuxin Chen', recur=three, lab_names=lab)
    assert h.given_conflict(['Gene Li'], 'Gen Li', pi='Yuxin Chen', recur=two, lab_names=lab)
    # never when another student of the lab is spelled that way
    assert h.given_conflict(['Gene Li'], 'Gen Li', pi='Yuxin Chen', recur=three, lab_names={'Yuxin Chen': {'gene li', 'gen li'}})
    # and never without the lab context
    assert h.given_conflict(['Gene Li'], 'Gen Li')


def test_east_asian_family_list_holds_the_cases():
    for fam in ('li', 'liu', 'zhao', 'lee', 'chen', 'ha'):
        assert fam in h.EAST_ASIAN_FAMILY


# ---- initials on the PI's byline -----------------------------------------------------------------------------------

def test_all_initials():
    assert h.all_initials(['Md Tauhidul Islam'], 'M.T. Islam')
    assert h.all_initials(['Md Tauhidul Islam'], 'M. T. Islam')
    assert not h.all_initials(['Yuxin Chen'], 'Y. L. Chen')        # two initials for a one-given-name PI
    assert not h.all_initials(['Mengdi Wang'], 'M. Wang')          # one initial proves nothing
    assert not h.all_initials(['Md Tauhidul Islam'], 'M.K. Islam')  # wrong second initial
    assert not h.all_initials(['Md Tauhidul Islam'], 'Md Tauhidul Islam')  # not initials at all


# ---- the transition-year rule for unaffiliated bylines ------------------------------------------------------------

def test_transition_side_griffiths(fixture_json):
    # Thomas Griffiths: Berkeley listings 2016-2018, the last captured 2018-04-05; he moved to Princeton in July 2018
    p = fixture_json('griffiths-berkeley.json')
    by_year = {l['year']: l for l in p['listings']}
    assert [l['year'] for l in p['listings']] == [2016, 2017, 2018]
    assert by_year[2018]['url'].startswith('https://web.archive.org/web/20180405')
    assert h.transition_side(p, by_year[2018], '2018-03-23') == 'inside'
    assert h.transition_side(p, by_year[2018], '2018-04-05') == 'inside'   # the capture day itself
    assert h.transition_side(p, by_year[2018], '2018-04-25') == 'outside'
    assert h.transition_side(p, by_year[2018], '2018-09-03') == 'outside'
    assert h.transition_side(p, by_year[2018], '2018') == 'outside'        # a bare year may fall after the capture
    assert h.transition_side(p, by_year[2017], '2017-11-01') == 'inside'   # no transition year
    assert h.transition_side(p, by_year[2016], '2016-01-02') == 'inside'   # the window's first year is no arrival


def test_transition_side_arrival_year():
    p = {'listings': [{'year': 2019, 'url': 'https://web.archive.org/web/20190915000000id_/x'}, {'year': 2020, 'url': 'u'}]}
    lst = p['listings'][0]
    assert h.transition_side(p, lst, '2019-10-01') == 'inside'
    assert h.transition_side(p, lst, '2019-03-01') == 'outside'
    assert h.transition_side(p, {'year': 2019, 'url': 'no capture date'}, '2019-10-01') == 'outside'


# ---- translated editions and chapter runs ---------------------------------------------------------------------------

@pytest.mark.parametrize('title, foreign', [
    ('Algorithmen - Eine Einführung', True),
    ('9. Médianes et statistiques d’ordre', True),
    ('Introduction to Algorithms', False),
    ('Die stacking for 3D chips', False),     # 'die' is German, but 'for' is English
    ('Algorithmen', False),                   # one word says nothing
])
def test_foreign_title(title, foreign):
    assert h.foreign_title(title) is foreign


def _chapters(k, pi='Charles Leiserson', venue='Algorithmen - Eine Einführung', year=2010, title='Kapitel'):
    return [dict(pi=pi, type='book-chapter', venue=venue, year=year, title=f'{title} {i}', oa=f'W{i}') for i in range(k)]


def test_fold_books_chapter_run_without_book_record():
    rows = _chapters(5, venue='Introduction to Algorithms', title='Chapter')
    kept, folded, translated = h.fold_books(rows, 'mit')
    assert len(kept) == 1 and folded == 4 and translated == 0
    assert kept[0]['chapters_folded'] == 5


def test_fold_books_chapter_run_into_book_record():
    rows = _chapters(5, venue='Introduction to Algorithms', title='Chapter') + \
        [dict(pi='Charles Leiserson', type='book', venue='Introduction to Algorithms', year=2010, title='Introduction to Algorithms', oa='WB')]
    kept, folded, translated = h.fold_books(rows, 'mit')
    assert [r['oa'] for r in kept] == ['WB'] and folded == 5


def test_fold_books_needs_five_chapters_of_one_pi_venue_year():
    rows = _chapters(4, venue='Introduction to Algorithms', title='Chapter') + _chapters(1, venue='Introduction to Algorithms', year=2011, title='Chapter')
    kept, folded, _ = h.fold_books(rows, 'mit')
    assert len(kept) == 5 and folded == 0


def test_fold_books_translations_dropped_outside_epfl_only():
    rows = [dict(pi='X', type='book-chapter', venue='V', year=2012, title='9. Médianes et statistiques d’ordre', oa='W1'),
            dict(pi='X', type='book', venue='V2', year=2012, title='Algorithmen - Eine Einführung', oa='W2'),
            dict(pi='X', type='article', venue='J', year=2012, title='Algorithmen und Datenstrukturen für die Praxis', oa='W3')]
    kept, _, translated = h.fold_books([dict(r) for r in rows], 'mit')
    assert [r['oa'] for r in kept] == ['W3'] and translated == 2   # articles are never translated editions
    kept, _, translated = h.fold_books([dict(r) for r in rows], 'epfl')
    assert len(kept) == 3 and translated is None                    # French- and German-speaking school


# ---- stale listings after an evidenced move ------------------------------------------------------------------------

def test_listings_after_move_mung_chiang(fixture_json):
    # Mung Chiang left Princeton in 2017 (faculty_end_moved); Princeton ECE kept him on its list 2019-2026
    x = fixture_json('mung-chiang-princeton.json')
    listings = {l['year']: l for l in x['listings']}
    after = h.listings_after_move(listings, x['collection_periods'], [])
    assert sorted(after) == x['expected_after_move'] == list(range(2019, 2027))
    assert 2016 not in after and 2017 not in after


def test_listings_after_move_kept_by_a_later_period(fixture_json):
    x = fixture_json('mung-chiang-princeton.json')
    listings = {l['year']: l for l in x['listings']}
    after = h.listings_after_move(listings, x['collection_periods'], [dict(start='2021', end=None)])
    assert sorted(after) == [2019, 2020]


def test_listings_after_move_needs_move_evidence(fixture_json):
    x = fixture_json('mung-chiang-princeton.json')
    listings = {l['year']: l for l in x['listings']}
    periods = [dict(p, evidence=[e for e in p['evidence'] if e['kind'] != 'faculty_end_moved']) for p in x['collection_periods']]
    assert h.listings_after_move(listings, periods, []) == {}


# ---- small helpers the rules lean on --------------------------------------------------------------------------------

def test_full_pair_and_gwords():
    assert h.full_pair('John W. Fisher III') == ('john', 'fisher')
    assert h.full_pair('J. Fisher') is None
    assert h.gwords('Wei-Ning Chen') == ['weining', 'chen']
    assert h.gwords('Chen, Wei-Ning') == ['weining', 'chen']


def test_one_edit():
    assert h.one_edit('johann', 'johan') and h.one_edit('gene', 'gen') and h.one_edit('siddarth', 'siddharth')
    assert not h.one_edit('weining', 'weichen')
