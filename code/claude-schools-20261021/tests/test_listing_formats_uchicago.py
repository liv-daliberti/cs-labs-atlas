"""UChicago listing formats (CS Drupal table, CS/Statistics people list, CS WordPress cards, TTIC media and table)."""
import importlib.util
from pathlib import Path

import listing_formats as L


def tools_listing_rows():
    """tools/listing_rows.py by path: another test puts archive/.../listing_rows.py first on sys.path."""
    spec = importlib.util.spec_from_file_location('tools_listing_rows', Path(L.__file__).with_name('listing_rows.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

CS_TABLE = '''<table><tbody><tr class="odd views-row-first"><td >
  Aaron  Elmore </td><td > Assistant Professor, <br />
 Department of Computer Science<br /><br />Research Interests: Databases </td><td >Office: Ryerson<br /><a href="mailto:[email removed]">[email removed]</a>
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


GALTON = '''<tr valign="top"><td><a name="amit"></a><a href="/faculty/amit.shtml" title="Yali Amit" target="_self"><strong>Yali Amit</strong></a><br>
<span class="text"><script language=JavaScript>var contact = "[email removed]"</script><br>Office: Eckhart 103 <br>Professor and Chair</span></td><td>&nbsp;</td></tr>
<tr><td><a href="/faculty/a.shtml"><strong>Mihai
 Anitescu</strong></a><br><span class="text"><br>Office: Eckhart 2 <br>Professor</span></td></tr>'''


def test_galton_cells_drops_email_and_office():
    fmt, es = L.parse(GALTON)
    assert fmt == 'galton_cells' and [(e['name_listed'], e['titles']) for e in es] == [('Yali Amit', ['Professor and Chair']), ('Mihai Anitescu', ['Professor'])]


def test_galton_cells_strong_around_the_link():
    h = '<td><strong><a name="c"></a><a href="/faculty/c.shtml">Linda Brant Collins</a></strong><br>\n<span class="text"><script>x</script><br>Office: E 1<br>Associate Professor</span></td>'
    assert L.parse(h)[1][0]['name_listed'] == 'Linda Brant Collins' and L.parse(h)[1][0]['titles'] == ['Associate Professor']


def test_uchicago_rank_words():
    R = tools_listing_rows()
    assert R.rank_of(['Assistant Instructional Professor of Computer Science']) == 'teaching'
    assert R.rank_of(['Adjoint Professor']) == 'adjunct' and R.rank_of(['Resident Adjoint Professor']) == 'adjunct'
    assert R.rank_of(['Neubauer Professor of Computer Science']) == 'ladder' and R.rank_of(['Professor Emeritus']) == 'emeritus'


def test_charter_rank_words_join_the_shared_patterns():
    R = tools_listing_rows()
    assert R.rank_of(['Professor of Basket Weaving']) == 'ladder'
    assert R.rank_of(['Professor of Basket Weaving'], {'teaching': r'basket weaving'}) == 'teaching'
    assert R.rank_of(['Assistant Professor'], {'teaching': r'basket weaving'}) == 'ladder'


PAGED = '<div class="pager"><a href="?page=1">2</a></div><li><a href="/p/a">Ann Lee</a> Professor</li>' * 6


def test_a_paged_capture_is_flagged_and_plan_fetch_rejects_it(monkeypatch):
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'listings' / 'scripts'))  # route-ok: tracked code, not data
    import plan_fetch as PF
    import listing_formats as LF
    assert LF.is_paged(PAGED) and not LF.is_paged('<ul><li>Ann Lee Professor</li></ul>')
    monkeypatch.setattr(LF, 'parse', lambda h, f=None: ('x', [{'name': str(i)} for i in range(9)]))
    monkeypatch.setattr(PF.wb, 'body', lambda raw: raw)

    class Con:
        def __init__(self, h): self.h = h
        def execute(self, q, a): return type('C', (), {'fetchone': lambda me: (self.h.encode(),)})()
    ok, why = PF.charter_usable(Con(PAGED), 'u', {})
    assert not ok and 'paged directory' in why
    assert PF.charter_usable(Con(PAGED), 'u', {'prefix': True})[0]
    assert PF.charter_usable(Con('<ul></ul>'), 'u', {})[0]


def test_partial_ok_slot_keeps_the_first_page_of_a_paged_list(monkeypatch):
    import plan_fetch as PF
    import listing_formats as LF
    monkeypatch.setattr(LF, 'parse', lambda h, f=None: ('x', [{'name': str(i)} for i in range(9)]))
    monkeypatch.setattr(PF.wb, 'body', lambda raw: raw)

    class Con:
        def execute(self, q, a): return type('C', (), {'fetchone': lambda me: (PAGED.encode(),)})()
    assert PF.charter_usable(Con(), 'u', {'partial_ok': True})[0]
    assert not PF.charter_usable(Con(), 'u', {})[0]


def test_plan_fetch_partial_ok_helper_detects_paged_list():
    import plan_fetch as PF
    assert PF.listing_formats_is_paged(PAGED) and not PF.listing_formats_is_paged('<ul><li>Ann Lee Professor</li></ul>')
