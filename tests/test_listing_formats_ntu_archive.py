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
