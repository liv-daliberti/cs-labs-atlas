from listing_formats import parse
from listing_rows import rank_of


def test_infk_old_h4_era():
    html = '<h4>Gustavo Alonso</h4> <p>Professor</p><p><a href="http://www.inf.ethz.ch/personal/alonso/">Website</a></p><h4>Peter Arbenz</h4><p>Titular Professor</p>'
    rows = parse(html, 'eth_infk_h4')[1]
    assert [(r['name_listed'], r['titles']) for r in rows] == [('Gustavo Alonso', ['Professor']), ('Peter Arbenz', ['Titular Professor'])]


def test_infk_new_bold_era_and_emeriti():
    html = '<p><b>Valentina Boeva<br> </b>Associate&nbsp;Professor</p><p><a href="/people/person-detail.boeva.html">More details</a></p><p><b>Not A Person</b> Footer text</p>'
    rows = parse(html, 'eth_infk_bold')[1]
    assert rows == [dict(name_listed='Valentina Boeva', titles=['Associate Professor'], homepage=None, division=None, profile='/people/person-detail.boeva.html')]
    em = '<div is="vue:eth-tab-accordion-item" title="Peter Arbenz"><p>Faculty member from 1987 to 2018</p></div>'
    assert parse(em, 'eth_infk_emeriti')[1][0]['titles'] == ['Emeritus Faculty (Faculty member from 1987 to 2018)']
    assert rank_of(parse(em, 'eth_infk_emeriti')[1][0]['titles']) == 'emeritus'


def test_itet_prof_heading_needs_charter_rank_word():
    html = '<div class="text-image"><h2><b>Prof. Luca Benini</b></h2><p><a href="/the-department/people-a-z/person-detail.luca-benini.html">Contact details</a></p></div><h2>Footer</h2>'
    rows = parse(html, 'eth_itet_h2')[1]
    assert rows[0]['name_listed'] == 'Luca Benini' and rows[0]['titles'] == ['Prof.']
    assert rank_of(rows[0]['titles'], {'ladder': r'\bprof\b'}) == 'ladder'
