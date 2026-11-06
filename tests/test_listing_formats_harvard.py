"""Harvard SEAS people directory (Drupal 10) and its `?page=%2C<n>` pager (excerpts of a real page)."""
import listing_formats as F

SEAS = """<h2 class="node-title teaching-area-dark person__detailed-name">
<a href="/person/david-alvarez-melis"><span class="person__name person__name--person-directory">David Alvarez-Melis</span></a></h2>
<div class="person-directory__primary-title"><div class="person__primary-title person__primary-title--person-directory field field-name-field-person-primary-title">
<div class="field-items"><div class="field-item">Assistant Professor of Computer Science</div></div></div></div>
<h2 class="node-title person__detailed-name"><a href="/person/joanna-aizenberg"><span class="person__name person__name--person-directory">Joanna Aizenberg</span></a></h2>
<div class="person__primary-title"><div class="field-items"><div class="field-item">Professor of Materials Science &amp; Chemistry</div></div></div>
<nav class="pager"><a href="?page=%2C1">2</a><a href="?page=%2C4">last</a></nav>"""


def test_seas_directory():
    name, rows = F.parse(SEAS)
    assert name == 'seas_directory' and [r['name_listed'] for r in rows] == ['David Alvarez-Melis', 'Joanna Aizenberg']
    assert rows[0]['titles'] == ['Assistant Professor of Computer Science']
    assert rows[1]['titles'] == ['Professor of Materials Science & Chemistry']


def test_seas_pager():
    assert F.is_paged(SEAS)
    assert sorted(F.page_links(SEAS, 'https://seas.harvard.edu/faculty')) == [1, 2, 3, 4]
    assert F.page_links(SEAS, 'https://seas.harvard.edu/faculty')[3] == 'https://seas.harvard.edu/faculty?page=%2C3'
