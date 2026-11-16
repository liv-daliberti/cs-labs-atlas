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
