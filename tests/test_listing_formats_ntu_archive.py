"""Archived CCDS directory cards moved appointments into description paragraphs."""
import listing_formats as L


def test_ntu_2024_2025_appointments_survive_description_layout():
    html = '''<div class="img-card--academic">
      <h3 class="img-card__title"><a href="/profiles/one">Assoc Prof Faculty One</a></h3>
      <p class="img-card__desc">Faculty One researches algorithms and teaches computing.</p>
      <p class="img-card__desc"><span class="label">Appointments:</span>
      Associate Professor, College of Computing &amp; Data Science<br>
      Courtesy Appointment, School of Physical &amp; Mathematical Sciences</p>
      <a class="email-label" href="mailto:private@example.edu">private@example.edu</a>
    </div>
    <div class="img-card--academic">
      <h3 class="img-card__title"><a href="/profiles/two">Prof Faculty Two</a></h3>
      <p class="img-card__interests"><span class="label">Appointments:</span>
      Professor, School of Computer Science and Engineering</p>
    </div>'''
    _, rows = L.parse(html, 'ntu_img_cards')
    assert rows[0]['name_listed'] == 'Faculty One'
    assert rows[0]['titles'] == [
        'Associate Professor, College of Computing & Data Science',
        'Courtesy Appointment, School of Physical & Mathematical Sciences',
    ]
    assert rows[1]['titles'] == ['Professor, School of Computer Science and Engineering']
    assert 'private@example.edu' not in str(rows)
    assert 'researches algorithms' not in str(rows)


def test_ntu_namesake_cards_quote_their_own_titles_without_contact_fields():
    from bs4 import BeautifulSoup
    from listing_rows import quote_of
    long_biography = 'Research in algorithms and data science. ' * 20
    html = f'''<div class="img-card--academic">
      <h3 class="img-card__title"><a href="/person/Li-Yi">Assoc Prof Li Yi</a></h3>
      <a href="mailto:first@example.edu">first@example.edu</a>
      <p class="img-card__desc">{long_biography}</p>
      <p class="img-card__desc"><span class="label">Appointments:</span>
        Associate Professor, College of Computing &amp; Data Science</p>
    </div>
    <div class="img-card--academic">
      <h3 class="img-card__title"><a href="/person/yili">Assoc Prof Li Yi</a></h3>
      <a href="mailto:second@example.edu">second@example.edu</a>
      <p class="img-card__desc">{long_biography}</p>
      <p class="img-card__desc"><span class="label">Appointments:</span>
        Associate Professor, School of Physical &amp; Mathematical Sciences</p>
    </div>'''
    _, rows = L.parse(html, 'ntu_img_cards')
    flat = ' '.join(BeautifulSoup(html, 'html.parser').get_text(' ', strip=True).split())
    quotes = [quote_of(flat, row, html) for row in rows]
    assert quotes[0] != quotes[1]
    for quote, row in zip(quotes, rows):
        assert all(part in flat for part in quote.split(' [...] '))
        assert row['name_listed'] in quote and all(title in quote for title in row['titles'])
        assert '@' not in quote and 'Research in algorithms' not in quote
    assert quote_of(flat, dict(rows[1], quote_parts=['Assoc Prof Li Yi', 'Invented appointment'])) is None
    assert quote_of(flat, dict(rows[1], quote_parts=['Assoc Prof Li Yi'])) is None


def test_ntu_legacy_photo_rows_keep_literal_ranks_and_parenthesized_names():
    from listing_rows import quote_of, rank_of
    html = """<table><tr><td><img src="photo.jpg"></td><td>
      <span class="parahead2"><a href="http://www.ntu.edu.sg/home/lana/">Svetlana (Lana) Obraztsova</a>
      (Asst Prof)<br>PhD University<br>Email: <a href="mailto:private@example.edu">private@example.edu</a></span>
      </td><td>Interests</td><td>Research</td></tr>
      <tr><td><img src="adj.jpg"></td><td>Ang Kai Keng (Adjunct Asst Prof)<br>
      <a href="mailto:private@example.edu">Email</a></td><td>Interests</td><td>Research</td></tr>
      <tr><td>Navigation</td><td>Example Person (Professor)</td><td>x</td><td>y</td></tr></table>"""
    _, rows = L.parse(html, 'ntu_moss_faculty')
    assert len(rows) == 2
    assert rows[0]['name_listed'] == 'Svetlana (Lana) Obraztsova'
    assert rows[0]['titles'] == ['Asst Prof']
    assert rows[0]['profile'] == 'http://www.ntu.edu.sg/home/lana/'
    assert rows[1]['profile'] is None
    assert rank_of(rows[0]['titles'], {'ladder': r'\b(?:Assoc|Asst)\s+Prof\b'}) == 'ladder'
    assert rank_of(rows[1]['titles'], {'ladder': r'\b(?:Assoc|Asst)\s+Prof\b'}) == 'adjunct'
    flat = ' '.join(__import__('bs4').BeautifulSoup(html, 'html.parser').get_text(' ', strip=True).split())
    for row in rows:
        assert quote_of(flat, row) == row['quote']
        assert '@' not in str(row) and 'PhD University' not in str(row)
