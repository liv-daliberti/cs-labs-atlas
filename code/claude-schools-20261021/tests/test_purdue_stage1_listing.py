import listing_formats as F


def test_purdue_cs_faculty_cards_keep_names_roles_and_profiles():
    html = '''<div class="people-item" data-position="Teaching Professor of Computer Science">
      <p class="people-name"><a href="https://www.cs.purdue.edu/people/faculty/gba.html">George B. Adams, III</a></p>
      <p class="people-title">Teaching Professor</p><p class="people-campus">West Lafayette, Indianapolis</p>
      </div><div class="people-item" data-position="Professor (Courtesy: Electrical and Computer Engineering)">
      <p class="people-name"><a href="/people/faculty/example.html">Example Faculty</a></p>
      <p class="people-title">Professor (Courtesy: Electrical and Computer Engineering)</p></div>'''
    fmt, rows = F.parse(html, 'purdue_cs_people')
    assert fmt == 'purdue_cs_people'
    assert [(r['name_listed'], r['titles'][0], r['profile']) for r in rows] == [
        ('George B. Adams, III', 'Teaching Professor', 'https://www.cs.purdue.edu/people/faculty/gba.html'),
        ('Example Faculty', 'Professor (Courtesy: Electrical and Computer Engineering)', '/people/faculty/example.html'),
    ]


def test_purdue_2016_faculty_table_keeps_rank_and_bio():
    html = '''<div class="main-content"><h3>Tenured, Tenure-Track, and Research Faculty</h3>
      <table class="directory"><tr><th>Name</th><th>Title</th></tr>
      <tr><td>Daniel Aliaga</td><td>Associate Professor</td><td>49-46010</td>
      <td><a href="https://www.cs.purdue.edu/people/faculty/aliaga/">Bio</a></td></tr>
      </table></div>'''
    rows = F.parse(html, 'purdue_cs_people')[1]
    assert rows == [dict(name_listed='Daniel Aliaga', titles=['Associate Professor'],
                         homepage=None, division=None,
                         profile='https://www.cs.purdue.edu/people/faculty/aliaga/')]
