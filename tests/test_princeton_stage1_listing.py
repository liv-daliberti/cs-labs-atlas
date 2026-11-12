from tools.listing_formats import princeton_cs_faculty


def test_princeton_faculty_uses_person_card_title_not_navigation_or_degree():
    html = '''<a href="/people/faculty">Faculty</a>
    <div class="people people-facstaff"><div class="person clearfix">
      <div class="person-details"><h2 class="person-name">
        <a href="/people/profile/appel">Andrew Appel</a><small>(on leave)</small>
      </h2><div class="person-title">Eugene Higgins Professor</div>
      <div class="person-degree">Ph.D., Carnegie Mellon University</div></div>
    </div><div class="person clearfix"><h2 class="person-name">Jack Brassil</h2>
      <div class="person-title">Senior Research Scholar</div></div></div>'''
    assert princeton_cs_faculty(html) == [
        dict(name_listed='Andrew Appel', titles=['Eugene Higgins Professor'],
             homepage=None, division=None, profile='/people/profile/appel'),
        dict(name_listed='Jack Brassil', titles=['Senior Research Scholar'],
             homepage=None, division=None, profile=None),
    ]
