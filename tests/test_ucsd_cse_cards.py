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


JACOBS = '''<table id="faclist"><tr><td><strong>Faculty Name</strong></td></tr>
<tr><td><p style="font-weight:bold; padding-bottom:5px;"><a href="findprofile.sfe?department=cse&fmp_recid=7">Belongie, Serge J.</a></p>
<span class="profiledept"><p><em>Adjt Professor</em>,
 CSE</p><p><em>Faculty-Affiliate</em>,
 Calit2</p></span></td><td>Vision research. 858-555-0100</td></tr>
<tr><td><p style="font-weight:bold"><a href="findprofile.sfe?recid=9">Baden, Scott B.</a></p><span class="profiledept"><p><em>Professor</em>, CSE</p></span></td></tr></table>'''

INFO = '''<div class="faculty__info__col"><a href="https://example.org/a"><img alt="x"/></a><a href="https://example.org/a"><h2>Ann Bee</h2></a>Associate Teaching Professor<br />ab@example.org<br />(858) 555-0100<br />CSE 1</div>'''


def test_jacobs_search_rows_keep_each_printed_appointment():
    _, rows = F.parse(JACOBS, 'ucsd_jacobs_findprofile')
    assert [(r['name_listed'], r['titles']) for r in rows] == [
        ('Belongie, Serge J.', ['Adjt Professor , CSE', 'Faculty-Affiliate , Calit2']), ('Baden, Scott B.', ['Professor , CSE'])]


def test_info_cols_keep_title_but_not_contact_lines():
    _, rows = F.parse(INFO, 'ucsd_cse_info_cols')
    assert [(r['name_listed'], r['titles']) for r in rows] == [('Ann Bee', ['Associate Teaching Professor'])]
