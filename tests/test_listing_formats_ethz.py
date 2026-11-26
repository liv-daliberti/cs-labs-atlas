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


def test_itet_any_reads_h2_blocks_and_comma_table_rows():
    table = '<table><tr><td>Benini, Luca, Prof. Dr.</td><td>ETZ J 84</td></tr><tr><td>Bona, Gian-Luca, Prof. Dr.</td></tr><tr><td>Doe, Jane, Dr.</td></tr></table>'
    rows = parse(table, 'eth_itet_any')[1]
    assert [(r['name_listed'], r['titles']) for r in rows] == [('Luca Benini', ['Prof. Dr.']), ('Gian-Luca Bona', ['Prof. Dr.'])]
    h2 = '<div class="text-image"><h2><b>Prof. Luca Benini</b></h2></div>'
    assert parse(h2, 'eth_itet_any')[1][0]['name_listed'] == 'Luca Benini'


def test_infk_bold_keeps_cards_whose_details_link_is_not_person_detail():
    html = ('<p><b>Florian Tram\u00e8r<br> </b>Assistant Professor</p><p><a href="/utils/search.MjU5NzMw.html">More details</a></p>'
            '<p><b>Karl Bringmann<br> </b> Full Professor</p><p><a href="https://ethz.ch/en/the-eth-zurich/organisation/who-is-who/infk/details.x.html">More details</a></p>')
    rows = parse(html, 'eth_infk_bold')[1]
    assert [r['name_listed'] for r in rows] == ['Florian Tram\u00e8r', 'Karl Bringmann']


def test_infk_bold_drops_soft_zero_width_spaces_in_names():
    html = '<p><b>Mennatallah El-​Assady<br> </b> Assistant Professor</p><p><a href="https://ai.ethz.ch/x.html">More details</a></p>'
    assert parse(html, 'eth_infk_bold')[1][0]['name_listed'] == 'Mennatallah El-Assady'


def test_infk_bold_quotes_the_printed_name_when_it_holds_zero_width_spaces():
    from listing_rows import quote_of
    html = '<p><b>Mennatallah El-​Assady<br> </b> Assistant Professor</p><p><a href="https://ai.ethz.ch/x.html">More details</a></p>'
    e = parse(html, 'eth_infk_bold')[1][0]
    assert e['name_listed'] == 'Mennatallah El-Assady' and e['quote_name'] == 'Mennatallah El-​Assady'
    flat = 'Mennatallah El-​Assady Assistant Professor More details'
    assert quote_of(flat, e) == 'Mennatallah El-​Assady Assistant Professor'


def test_infk_bold_keeps_an_external_more_details_link_as_the_homepage():
    html = ('<p><b>Jules Jacobs<br> </b> Assistant Professor</p><p><a href="https://julesjacobs.com/">More details</a></p>'
            '<p><b>Karl Bringmann<br> </b> Full Professor</p><p><a href="https://ethz.ch/en/the-eth-zurich/organisation/who-is-who/infk/details.x.html">More details</a></p>')
    rows = parse(html, 'eth_infk_bold')[1]
    assert rows[0]['homepage'] == 'https://julesjacobs.com/' and rows[1]['homepage'] is None
