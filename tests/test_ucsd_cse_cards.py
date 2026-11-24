import listing_formats as F

OLD = '''<h3>Full</h3><div class="grid"><div class="views-field"><span class="field-content">
<img alt="A B"/><a href="/index.php/people/faculty-profiles/ann-bee" title="p"><h4>Ann Bee <i class="fas"></i></h4></a></span></div>
</div><h3>Emeritus</h3><div><a href="/index.php/people/faculty-profiles/old-prof"><h4>Old Prof <i></i></h4></a></div>
<h3>Faculty Alumni</h3><div><a href="/index.php/people/faculty-profiles/gone-away"><h4>Gone Away</h4></a></div>'''
NEW = '''<h3>Department Leadership</h3><a href="/people/faculty-profiles/ann-bee"><p><strong>Ann Bee <i></i></strong></p></a><p>Department Chair</p>
<h3>Faculty</h3><a href="/people/faculty-profiles/ann-bee"><p><strong>Ann Bee <i></i></strong></p></a>
<h3>Affiliated</h3><a href="/people/faculty-profiles/cy-dee"><p><strong>Cy Dee</strong></p></a>
<h3>Alumni</h3><a href="/people/faculty-profiles/gone"><p><strong>Gone Person</strong></p></a>'''


def test_old_cards_use_section_headings_and_skip_alumni():
    name, rows = F.parse(OLD, 'ucsd_cse_cards')
    assert name == 'ucsd_cse_cards'
    assert [(r['name_listed'], r['titles']) for r in rows] == [('Ann Bee', ['Full']), ('Old Prof', ['Emeritus'])]
    assert rows[0]['quote_parts'] == ['Ann Bee', 'Full']


def test_new_cards_skip_leadership_repeat_and_alumni():
    _, rows = F.parse(NEW, 'ucsd_cse_cards')
    assert [(r['name_listed'], r['titles']) for r in rows] == [('Ann Bee', ['Faculty']), ('Cy Dee', ['Affiliated'])]
