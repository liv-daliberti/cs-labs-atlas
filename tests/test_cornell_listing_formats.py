import listing_formats as F


def test_cornell_cs_legacy_person_boxes():
    html = '''<div class="people-list"> <div class="person"><br /> <a href="http://x/albonesi/"><img alt="David Albonesi" src="a.jpg" /></a>
      <div class="info"> <h2><a href="http://x/albonesi/">David Albonesi</a></h2>
      <p>Professor<br /> ECE, CS Field Member<br /> Ph.D., Univ of Mass, Amherst, 1996<br /> <b>Research focus:</b> architecture</p> </div> </div>
      <div class="person"><div class="info"><h2>Yoav Artzi</h2><p>Assistant Professor<br />Ph.D., UW, 2013</p></div></div></div>'''
    fmt, rows = F.parse(html)
    assert fmt == 'cornell_cs_legacy'
    assert [(r['name_listed'], r['titles']) for r in rows] == [
        ('David Albonesi', ['Professor', 'ECE, CS Field Member']), ('Yoav Artzi', ['Assistant Professor'])]
    assert rows[0]['homepage'] == 'http://x/albonesi/'


def test_cornell_cis_directory_flat_and_nested_cards():
    flat = '''<div class="person-listing"> <h6 class="text-primary"><a href="https://a.example/">Jayadev Acharya</a></h6>
      <strong class="inline-field">Assistant Professor</strong> <span class="inline-field">; Electrical and Computer Engineering, CS Field Member</span>
      <span class="inline-field">; Ph.D., UCSD, 2014</span><p><strong>Research Focus: </strong> theory</p></div>'''
    nested = '''<div class="person-listing"> <h6 class="text-primary"><a href="https://b.example/">Mohamed Abdelfattah</a></h6>
      <div class="person-list"><div class="person-listing"><strong class="inline-field">Assistant Professor</strong>
      <span class="inline-field">; Electrical and Computer Engineering, Cornell Tech, CS Field Member</span></div></div></div>'''
    fmt, rows = F.parse(flat + nested)
    assert fmt == 'cornell_cis_directory'
    assert [(r['name_listed'], r['titles']) for r in rows] == [
        ('Jayadev Acharya', ['Assistant Professor; Electrical and Computer Engineering, CS Field Member']),
        ('Mohamed Abdelfattah', ['Assistant Professor; Electrical and Computer Engineering, Cornell Tech, CS Field Member'])]


def test_cornell_cis_index_cards_keep_titles_department_and_profile_type():
    html = '''<div class="directory-container directory-container--condensed"><div class="views-row"><div class="directory-card">
      <div class="card-content-group card-content-group-main"><div class="name"><span>John Hopcroft</span></div>
      <div class="position-titles"><div class="field__item">Professor Emeritus</div></div></div>
      <div class="card-content-group"><div class="card-content-group-subgroup"><div class="label">Contact</div><div class="email">jeh at cs dot cornell dot edu</div></div>
      <div class="card-content-group-subgroup"><div class="label">College/Department</div><div class="item-content">Computer Science</div></div>
      <div class="card-content-group-subgroup"><div class="label">Profile Type</div><div class="item-content">Faculty (Emeritus)</div></div></div></div></div></div>'''
    fmt, rows = F.parse(html)
    assert fmt == 'cornell_cis_index_cards'
    assert rows == [dict(name_listed='John Hopcroft', titles=['Professor Emeritus', 'Computer Science', 'Faculty (Emeritus)'], homepage=None, division=None, profile=None)]
