import listing_formats as LF
from listing_rows import given_first, quote_of, rank_of


def test_campus_faculty_preserves_multiunit_source_identity_and_written_roles():
    html = '''<h3>Computer Science</h3><ul class="faculty-list">
      <li><a href="https://directory.illinois.edu/search?netID=example%40illinois.edu">Example, Jane Q</a>, <span class="notes">Professor</span></li>
      <li><a href="/search?netID=staff">Staff, Example</a>, <span class="notes">Program Coordinator</span></li>
      <li><a href="/search?netID=no-title">Title, Missing</a></li></ul>
      <h3>Electrical Engineering</h3><ul class="faculty-list">
      <li><a href="/search?netID=example%40illinois.edu">Example, Jane Q</a>, <span class="notes">Affiliate Professor</span></li></ul>'''
    _, rows = LF.parse(html, 'illinois_campus_faculty')
    assert len(rows) == 3
    assert [r['source_key'] for r in rows] == ['example', 'staff', 'example']
    assert rows[0]['division'] == 'Computer Science'
    assert rows[2]['division'] == 'Electrical Engineering'
    assert given_first(rows[0]['name_listed']) == 'Jane Q Example'
    assert rank_of(rows[1]['titles']) == 'other'
    assert quote_of('Example, Jane Q Professor Staff, Example Program Coordinator', rows[0]) == 'Example, Jane Q [...] Professor'
    assert quote_of('Example, Jane Q Professor Staff, Example Program Coordinator', rows[1]) == 'Staff, Example [...] Program Coordinator'
