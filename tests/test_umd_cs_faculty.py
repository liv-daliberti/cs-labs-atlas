import listing_formats as LF
import school_config as S
from listing_rows import listing_rank

CARDS = '''<div class="view-content"><h3>CS Faculty</h3><div class="row"><div class="media col-xs-12">
<div class="media-left"><a href="/people/abadi"><img alt="Photo of Daniel Abadi"/></a></div>
<div class="media-body"><h4 class="media-heading"><a href="/people/abadi">Daniel Abadi  </a></h4> Professor <br/>Darnell-Kanal Professor of Computer Science <br/><a href="/research-area/databases-and-big-data">Databases and Big Data</a>, <a href="/x">Systems</a></div>
</div><div class="media"><div class="media-body"><h4 class="media-heading"><a href="/people/lecturer1">Jane Lecturer </a></h4> Senior Lecturer <br/> </div></div></div>
<h3>Emeritus Faculty</h3><div class="media"><div class="media-body"><h4 class="media-heading"><a href="/people/emer1">Old Person </a></h4> Professor Emeritus <br/> </div></div>
<h3>Affiliate Faculty</h3><div class="media"><div class="media-body"><h4 class="media-heading"><a href="/people/aff1">Cross Listed </a></h4> Affiliate Professor <br/><a href="/r">Area</a></div></div>
<h3>Post Doctoral Scientists/Research Assistants</h3><div class="media"><div class="media-body"><h4 class="media-heading"><a href="/people/pd1">Post Doc </a></h4> Research Associate <br/> </div></div></div>'''

TABLE = '''<div class="view-content"><h3>CS Faculty</h3><table class="views-view-grid"><tbody><tr><td class="col-1">
<div class="views-field views-field-field-person-photo"><div class="field-content"><a href="/people/agrawala#profile-contact_info"><img src="x"/></a></div></div>
<div class="views-field views-field-field-person-last-name"><strong class="field-content"><a href="/people/agrawala">Ashok Agrawala  </a></strong></div>
<div class="views-field views-field-field-faculty-title"><div class="field-content">Professor</div></div>
<div class="views-field views-field-field-research-areas"><div class="field-content">Systems</div></div></td></tr></tbody></table>
<h3>Adjunct Faculty</h3><table><tr><td><strong class="field-content"><a href="/people/adj1">Adj Person</a></strong>
<div class="views-field views-field-field-faculty-title"><div class="field-content">Adjunct Associate Professor</div></div></td></tr></table></div>'''


def test_umd_cs_cards_keep_category_in_titles_and_division():
    fmt, rows = LF.parse(CARDS)
    assert fmt == 'umd_cs_faculty'
    assert [r['name_listed'] for r in rows] == ['Daniel Abadi', 'Jane Lecturer', 'Old Person', 'Cross Listed', 'Post Doc']
    assert rows[0]['titles'] == ['Professor', 'Darnell-Kanal Professor of Computer Science']
    assert rows[0]['division'] == 'CS Faculty' and rows[4]['division'].startswith('Post Doctoral')
    ranks = S.field(S.get('umd'), 'census.rank_words')
    assert listing_rank(rows[0]['titles'], [], 'main', ranks) == 'ladder'
    assert listing_rank(rows[1]['titles'], [], 'main', ranks) in ('teaching', 'lecturer')
    assert listing_rank(rows[2]['titles'], [], 'main', ranks) == 'emeritus'
    _, aff = LF.parse(CARDS, 'umd_cs_affiliates')
    assert [r['name_listed'] for r in aff] == ['Cross Listed']
    assert listing_rank(aff[0]['titles'], [], 'courtesy', ranks) == 'courtesy'
    _, main = LF.parse(CARDS, 'umd_cs_main')
    assert [r['name_listed'] for r in main] == ['Daniel Abadi', 'Jane Lecturer', 'Old Person']
    _, adj = LF.parse(TABLE, 'umd_cs_adjuncts')
    assert [r['name_listed'] for r in adj] == ['Adj Person']


def test_umd_cs_table_era():
    _, rows = LF.parse(TABLE, 'umd_cs_faculty')
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [
        ('Ashok Agrawala', ['Professor'], 'CS Faculty'), ('Adj Person', ['Adjunct Associate Professor'], 'Adjunct Faculty')]
    assert 'Systems' not in str(rows)


def test_wayback_original_for_relative_profile_resolution():
    import census_build as C
    assert C.wayback_original('https://web.archive.org/web/20160326141137id_/http://cs.umd.edu:80/people/faculty') == 'http://cs.umd.edu:80/people/faculty'
    assert C.wayback_original('https://www.cs.umd.edu/people/faculty') == 'https://www.cs.umd.edu/people/faculty'


def test_courtesy_home_must_name_a_unit_not_a_role():
    import home_departments_school as H
    known = {'Electrical and Computer Engineering', 'Computer Science'}
    norm = lambda u: u   # noqa: E731
    role = 'Lockheed Martin Chair in Systems Engineering, Director HyNET, Founding Director, ISR'
    assert not H.courtesy_home_ok(role, norm, known, True)
    assert H.courtesy_home_ok('Electrical and Computer Engineering', norm, known, True)
    assert H.courtesy_home_ok(role, norm, known, False)   # released schools are not re-judged
    assert not H.courtesy_home_ok(None, norm, known, True)


UMD_PROFILE = '''<div class="views-field views-field-field-profile-location"><strong class="views-label">Location: </strong><div class="field-content">IRB 5154</div></div>
<div class="views-field views-field-field-profile-website col-md-6"><strong class="views-label views-label-field-profile-website">Website: </strong>
<div class="field-content"><a href="http://www.cs.umd.edu/~amol/">http://www.cs.umd.edu/~amol/</a></div></div>
<div class="views-field views-field-field-profile-gscholar"><strong class="views-label">Google Scholar: </strong><div class="field-content"><a href="https://scholar.google.com/x">GS</a></div></div>'''


def test_profile_website_field_is_a_first_class_link_even_on_the_profiles_own_host():
    import labpage_audit as LA
    links = LA.profile_website_links(UMD_PROFILE, 'https://www.cs.umd.edu/people/amol')
    assert links == [('http://www.cs.umd.edu/~amol/', 'http://www.cs.umd.edu/~amol/')]
    rel = '<div class="views-field-field-profile-website"><strong>Website: </strong><a href="/~tomg">Tom</a></div>'
    assert LA.profile_website_links(rel, 'https://www.cs.umd.edu/people/tomg') == [('https://www.cs.umd.edu/~tomg', 'Tom')]


def test_class_pages_and_unlabelled_links_are_not_a_homepage():
    import labpage_audit as LA
    cls = '<div class="views-field-field-profile-website"><strong>Website: </strong><a href="http://www.cs.umd.edu/class">Class Web Pages</a></div>'
    assert LA.profile_website_links(cls, 'https://www.cs.umd.edu/people/vs') == []
    assert LA.profile_website_links('<p><a href="http://example.org/">Class Web Pages</a></p>', 'https://x.edu/') == []
    lab = '<dl><dt>Homepage</dt><dd><a href="http://www.cs.umd.edu/~vs/">vs</a></dd></dl>'   # label in a dt, link in the sibling dd
    assert LA.profile_website_links(lab, 'https://www.cs.umd.edu/people/vs') == [('http://www.cs.umd.edu/~vs/', 'vs')]
