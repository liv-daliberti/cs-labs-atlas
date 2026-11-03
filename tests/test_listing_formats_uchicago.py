"""UChicago listing formats (CS Drupal table, CS/Statistics people list, CS WordPress cards, TTIC media and table)."""
import listing_formats as L

CS_TABLE = '''<table><tbody><tr class="odd views-row-first"><td >
  Aaron  Elmore </td><td > Assistant Professor, <br />
 Department of Computer Science<br /><br />Research Interests: Databases </td><td >Office: Ryerson<br /><a href="mailto:a@cs.uchicago.edu">a@cs.uchicago.edu</a>
 <p><a href="http://people.cs.uchicago.edu/~aelmore/">Personal website</a></p></td><td></td></tr>
 <tr class="even"><td > Ian Foster </td><td > Arthur Holly Compton Distinguished Service Professor<br />Department of Computer Science</td><td></td><td></td></tr></tbody></table>'''
CS_LI = '''<li class="mix datascience faculty tenure-track-faculty "><div class="people_img"><h5>Aaron  Elmore</h5></div><div class="people_content">
<h3><a href="https://www.cs.uchicago.edu/people/profile/aaron-elmore"> Aaron Elmore </a><small> Assistant Professor <br />Department of Computer Science </small></h3></div></li>
<li class="mix staff "><h3><a href="https://x/people/profile/s">Some Staff</a><small>Staff</small></h3></li>'''
STAT_LI = '''<li class="mix faculty"><a href="https://stat.uchicago.edu/people/profile/chao-gao/"><div class="people_content"><h3><span>Chao Gao</span><b> Assistant Professor </b></h3></div></a></li>
<li class="mix phd-students"><a href="https://stat.uchicago.edu/people/profile/x/"><h3><span>A Student</span><b>PhD Student, First Year</b></h3></a></li>'''
CARD = '''<div class="card card--person"><div class="card__content"><h3 class="card__title">Aaron Elmore</h3>
<div class="card__position">Associate Professor, Department of Computer Science</div></div><a class="card__url" href="https://cs.uchicago.edu/people/aaron-elmore/" target="_self"></a></div>'''
TTIC_MEDIA = '''<div class="media-body"><h2 class="media-heading"><a href="blum">Avrim Blum</a></h2><h3>Professor and Chief Academic Officer</h3><p>PhD - MIT</p>
<p><a href="blum">Bio</a> | <a href="http://www.ttic.edu/blum">Home Page</a></p></div>'''
TTIC_TABLE = '''<tr><td><img/></td><td><strong>Mohit Bansal</strong>, Research Assistant Professor<br />PhD - UC Berkeley<br /><a href="bansal.php">Bio</a> | <a href="http://www.ttic.edu/bansal">Home Page</a><br />Research Interests: NLP</td></tr>'''


def test_uc_cs_table():
    fmt, es = L.parse(CS_TABLE)
    assert fmt == 'uc_cs_table' and [e['name_listed'] for e in es] == ['Aaron Elmore', 'Ian Foster']
    assert es[0]['titles'] == ['Assistant Professor', 'Department of Computer Science'] and es[0]['homepage'] == 'http://people.cs.uchicago.edu/~aelmore/'
    assert 'mailto' not in str(es) and 'Research Interests' not in str(es)


def test_uc_people_li_keeps_only_faculty_groups():
    fmt, es = L.parse(CS_LI)
    assert fmt == 'uc_people_li' and [e['name_listed'] for e in es] == ['Aaron Elmore'] and es[0]['titles'] == ['Assistant Professor', 'Department of Computer Science']
    assert es[0]['profile'].endswith('aaron-elmore')
    fmt, es = L.parse(STAT_LI)
    assert [e['name_listed'] for e in es] == ['Chao Gao'] and es[0]['titles'] == ['Assistant Professor']


def test_uc_card_ttic_media_and_ttic_table():
    assert L.parse(CARD)[1][0] == dict(name_listed='Aaron Elmore', titles=['Associate Professor, Department of Computer Science'], homepage=None, division=None,
                                       profile='https://cs.uchicago.edu/people/aaron-elmore/')
    fmt, es = L.parse(TTIC_MEDIA)
    assert fmt == 'ttic_media' and es[0]['name_listed'] == 'Avrim Blum' and es[0]['titles'] == ['Professor and Chief Academic Officer'] and es[0]['homepage'] == 'http://www.ttic.edu/blum'
    fmt, es = L.parse(TTIC_TABLE)
    assert fmt == 'ttic_table' and es[0]['name_listed'] == 'Mohit Bansal' and es[0]['titles'] == ['Research Assistant Professor'] and es[0]['homepage'] == 'http://www.ttic.edu/bansal'
