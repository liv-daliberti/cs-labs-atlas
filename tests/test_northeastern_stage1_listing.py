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


def test_khoury_profile_name_and_position():
    html = '''<div class="single-people__header-content"><h1 class="single-people__header-title">Luowen Qian</h1>
      <p class="single-people__header-subtitle">(he/him)</p><p class="single-people__header-description">Assistant Professor</p></div>'''
    fmt, rows = F.parse(html)
    assert fmt == 'northeastern_khoury_profile'
    assert rows == [dict(name_listed='Luowen Qian', titles=['Assistant Professor'], homepage=None, division=None, profile=None)]
    assert F.parse('<h1 class="single-people__header-title">No Title</h1>')[1] == []


def test_netsi_cards_faculty_only():
    def card(slug, name, pos):
        return (f'<a href="/people/{slug}" class="link-block-11 w-inline-block"><div class="pub-list-title filtered pub width">{name}</div>'
                f'<div class="pub-list-title filtered pub width h w-condition-invisible w-dyn-bind-empty"></div>'
                f'<div fs-cmsfilter-field="position" class="pub-list-journal filtered width">{pos}</div></a>')
    html = card('dima-krioukov', 'Dima Krioukov', 'Professor') + card('x-student', 'A Student', 'PhD Student') + card('adm', 'B Admin', 'Admin Staff')
    fmt, rows = F.parse(html)
    assert fmt == 'northeastern_netsi_cards'
    assert rows == [dict(name_listed='Dima Krioukov', titles=['Professor'], homepage=None, division=None, profile='/people/dima-krioukov')]
