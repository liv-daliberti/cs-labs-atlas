"""Mixed contribution/affiliation symbols cannot hide or transfer a PI's numbered school."""
import re
from labpage_recover import page1_tie
from pihier.common import norm_title


def check(text):
    return page1_tie(text, [('james', 'evans')], re.compile('University of Chicago', re.I),
                     [norm_title('The Paradox of Collective Certainty in Science')])


def test_symbol_before_affiliation_number_resolves_own_school():
    text = ('The Paradox of Collective Certainty in Science Eamon Duede*1 and James Evans†2,3,4 '
            '1 Harvard University 2 University of Chicago 3 Santa Fe Institute 4 Knowledge Lab Abstract')
    how, quotes, variant = check(text)
    assert how == 'marker' and variant == 'markers_split'
    assert any('2 University of Chicago' in quote for quote in quotes)


def test_composite_marker_cannot_borrow_another_authors_school():
    text = ('The Paradox of Collective Certainty in Science Eamon Duede*2 and James Evans†1 '
            '1 Harvard University 2 University of Chicago Abstract')
    assert check(text)[0] is None


def test_affiliation_on_a_different_paper_is_not_accepted():
    text = 'Different Paper Eamon Duede*1 and James Evans†2 1 Harvard University 2 University of Chicago Abstract'
    assert check(text)[0] == 'title_not_on_page1'
