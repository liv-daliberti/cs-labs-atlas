import listing_formats as F


def _card(name, pos):
    return f'''<article class="people-directory"><div class="grid-item"><h3 class="person-name">
      <a href="https://www.khoury.northeastern.edu/people/{name.lower().replace(' ', '-')}/">{name}</a></h3>
      <div class="position-list"><span class="position">{pos}</span></div>
      <div class="contact-info"><div class="email"><a href="mailto:x@ccs.neu.edu">x@ccs.neu.edu</a></div></div></div></article>'''


def test_people_directory_keeps_faculty_rows_only_and_no_contacts():
    html = _card('Aanjhan Ranganathan', 'Assistant Professor') + _card('Jaideep Ramachandran', 'PhD Student') + _card('Pat Staff', 'Administrative Coordinator')
    fmt, rows = F.parse(html)
    assert fmt == 'northeastern_people_directory'
    assert rows == [dict(name_listed='Aanjhan Ranganathan', titles=['Assistant Professor'], homepage=None, division=None,
                         profile='https://www.khoury.northeastern.edu/people/aanjhan-ranganathan/')]


def test_ccs_headshots_name_title_profile():
    html = '''<div class="headshot"><a href="http://www.ccs.neu.edu/people/faculty/member/ahmed/"><div class="overview">
      <div class="image"><div class="details"><p class="position branded-strong">Assistant Professor</p><p class="more">Read Full Bio</p></div></div>
      <p class="name branded-alt">Amal Ahmed</p></div></a></div>'''
    fmt, rows = F.parse(html)
    assert fmt == 'northeastern_ccs_headshots'
    assert rows == [dict(name_listed='Amal Ahmed', titles=['Assistant Professor'], homepage=None, division=None,
                         profile='http://www.ccs.neu.edu/people/faculty/member/ahmed/')]
