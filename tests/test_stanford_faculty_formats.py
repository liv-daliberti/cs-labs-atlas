from tools import listing_formats as L
from tools.listing_rows import quote_of


def test_legacy_cs_keeps_unlinked_names_and_categories_without_contacts():
    html = '''<h3>Regular Faculty</h3><table>
      <tr><th>Name</th><th>Phone</th><th>Office</th><th>email</th></tr>
      <tr><td><a href="https://example.edu/alex">Alex Aiken</a></td><td>555</td><td>Gates 1</td><td>secret</td></tr>
      <tr><td>Jeannette Bohg</td><td>666</td><td>Gates 2</td><td>private</td></tr></table>
      <h3>Courtesy Faculty</h3><table><tr><td>Jane Faculty</td><td></td><td></td><td></td></tr></table>
      <h3>Administrative Staff</h3><table><tr><td>Jane Staff</td><td></td><td></td><td></td></tr></table>'''
    rows = L.stanford_cs_legacy(html)
    assert [r['name_listed'] for r in rows] == ['Alex Aiken', 'Jeannette Bohg', 'Jane Faculty']
    assert [r['division'] for r in rows] == ['Regular Faculty', 'Regular Faculty', 'Courtesy Faculty']
    assert all(r['titles'] == [] for r in rows)
    assert rows[1]['homepage'] is None
    assert not any(value in str(rows) for value in ['555', '666', 'secret', 'private', 'Gates'])


def test_cs_card_eras_preserve_titles_and_absolute_profiles():
    old = '''<li><div class="views-field-title"><a href="/people/maneesh"><h3>Maneesh Agrawala</h3></a></div>
      <div class="views-field-su-person-short-title"><div class="field-content">Forest Baskett Professor</div></div></li>'''
    new = '''<div class="su-card__contents"><h3><a href="/people/mike">Mike Carbin Carbin</a></h3>
      <div class="su-person-short-title">Visiting Associate Professor</div></div>'''
    first = L.stanford_cs_cards(old)[0]
    second = L.stanford_cs_cards(new)[0]
    assert first['profile'] == 'https://www.cs.stanford.edu/people/maneesh'
    assert first['titles'] == ['Forest Baskett Professor']
    assert second['name_listed'] == 'Mike Carbin Carbin'
    assert second['titles'] == ['Visiting Associate Professor']


def test_ee_directory_excludes_embedded_administrators_and_remains_paged():
    html = '''<h3 class="description"><a href="https://example.edu/a">Amin Arbabian</a><small>Associate Professor</small></h3>
      <h3 class="description">Marie Hamel<small>Administrator</small></h3>
      <h3 class="orglist__display-name"><a href="https://example.edu/b">Sara Achour</a><small>Assistant Professor</small></h3>
      <ul class="pager js-pager__items"><li><a href="?page=1">2</a></li></ul>'''
    rows = L.stanford_ee_cards(html)
    assert [r['name_listed'] for r in rows] == ['Amin Arbabian', 'Sara Achour']
    assert L.is_paged(html)


def test_bulletin_rank_sections_and_emeriti_are_literal_source_quotes():
    html = '''<div id="facultytextcontainer">
      <p><em>Chair:</em> Department Administrator</p>
      <p><em>Emeriti: (Professors)</em> John Cioffi*, Hector Garcia-Molina (deceased November 25, 2019);
      (<em>Associate Professors</em>) John T. Gill III; (Professors, Research) Antony Fraser-Smith* (<em>*Recalled to active duty</em>)</p>
      <p><em>Professors:</em> Stephen P. Boyd, Dan Boneh</p>
      <p><em>Visiting Associate Professor</em>: Youngcheol Chae</p></div>'''
    rows = L.stanford_ee_bulletin(html)
    assert [r['name_listed'] for r in rows] == ['John Cioffi', 'Hector Garcia-Molina', 'John T. Gill III',
                                             'Antony Fraser-Smith', 'Stephen P. Boyd', 'Dan Boneh', 'Youngcheol Chae']
    assert rows[2]['titles'] == ['Emeriti: (Professors)', 'Associate Professors']
    assert rows[3]['titles'] == ['Emeriti: (Professors)', 'Professors, Research']
    assert all(quote_of('', row, html) for row in rows)
    assert L.stanford_ee_bulletin('<div id="facultytextcontainer"><p>Faculty page loading</p></div>') == []
