from listing_formats import parse
from listing_rows import rank_of, quote_of


def card(name, title, url='/people/smith.html'):
    return f'<span class="vt-list-title vt-list-item-title"><a href="{url}">{name}<span class="sr-only">, bio</span></a></span><p class="vt-list-description vt-list-item-description">{title}</p><p>private-contact@example.edu</p>'


def test_vt_separates_appointment_sections_and_ignores_navigation():
    html = '<nav>' + card('Navigation Copy', 'Professor') + '</nav><main><h2>Teaching and research faculty</h2><h3>Find faculty by research area</h3>' + card('Alex Smith', 'Associate Professor') + '<h3>Courtesy faculty</h3>' + card('Robin Doe', 'Professor, Electrical Engineering; Professor by courtesy, Computer Science') + '</main>'
    main = parse(html, 'vt_main')[1]
    courtesy = parse(html, 'vt_courtesy')[1]
    assert main == [dict(name_listed='Alex Smith', titles=['Associate Professor'], homepage='/people/smith.html', division=None,
                         quote='Alex Smith , bio Associate Professor')]
    assert len(courtesy) == 1 and courtesy[0]['name_listed'] == 'Robin Doe'
    assert 'by courtesy' in courtesy[0]['titles'][0]
    assert 'contact' not in str(main + courtesy)
    assert parse(html, 'vt_adjunct')[1] == []


def test_vt_preserves_collegiate_and_incoming_rank_cues():
    html = '<main><h2>Teaching and research faculty</h2>' + card('Alex Smith', 'Collegiate Assistant Professor') + card('Robin Doe', 'Incoming Assistant Professor') + '</main>'
    rows = parse(html, 'vt_main')[1]
    words = {'teaching': r'\bcollegiate\s+(?:(?:assistant|associate)\s+)?professor\b'}
    assert rank_of(rows[0]['titles'], words) == 'teaching'
    assert rank_of(rows[1]['titles'], words) == 'other'


def test_vt_does_not_parse_a_navigation_only_or_unrecognized_page():
    assert parse('<nav>' + card('Alex Smith', 'Professor') + '</nav>', 'vt_main')[1] == []


def test_vt_retains_plain_adjunct_names_and_stops_at_unrelated_heading():
    html = '<main><h3>Adjunct faculty</h3><div class="vt-text"><p>Alex Smith</p></div><div class="vt-text"><p><a href="/robin">Robin Doe</a></p></div><h3>Emeritus faculty</h3><div class="vt-text"><p>Lee Example</p></div><h3>Contact us</h3><div class="vt-text"><p>Office contact</p></div></main>'
    rows = parse(html, 'vt_adjunct')[1]
    assert [r['name_listed'] for r in rows] == ['Alex Smith', 'Robin Doe']
    assert rows[0]['homepage'] is None and rows[0]['titles'] == ['Adjunct faculty']
    assert rows[1]['homepage'] == '/robin'
    assert [r['name_listed'] for r in parse(html, 'vt_emeritus')[1]] == ['Lee Example']


def test_card_quote_keeps_rank_despite_an_earlier_navigation_name():
    row = parse('<main><h2>Teaching and research faculty</h2>' + card('Alex Smith', 'Associate Professor') + '</main>', 'vt_main')[1][0]
    flat = 'Alex Smith navigation ' + 'other navigation entries ' * 40 + 'Alex Smith , bio Associate Professor'
    assert quote_of(flat, row) == 'Alex Smith , bio Associate Professor'
    assert quote_of(flat, {**row, 'quote': 'Alex Smith Professor of Invented Claims'}) is None
    assert quote_of(flat, {**row, 'quote': 'Alex Smith'}) is None
