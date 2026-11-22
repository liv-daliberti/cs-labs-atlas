"""UW onboarding 2026-11-22: archived HCDE directory eras, profile-page faculty evidence, and official links from the school's own stored pages."""
import sqlite3
import zlib

import cs_related_school as C
import lab_websites as W
import listing_formats as F

HCDE_2016 = """<table><tbody><tr><td> <h3><img alt="Cecilia Aragon" class="imgLeft" src="a.jpg" /><a id="A" name="A"></a><strong><a href="/aragon">Cecilia Aragon</a></strong></h3> <p>Associate Professor<br /><strong><a href="http://faculty.washington.edu/aragon">Website</a> | <a href="mailto:x@uw.edu">Email</a></strong></p></td></tr>
<tr><td> <h3><a id="K" name="K"></a><a href="/kientz"><img alt="Julie Kientz" class="imgLeft" src="k.jpg" /><strong>Julie Kientz</strong></a></h3> <div> <p>Associate Professor<br /><strong><a href="http://x">Website</a></strong></p></div></td></tr>
<tr><td> <h3><a href="/ribes"><img alt="" class="imgLeft" src="r.jpg" /></a><a id="R" name="R"></a><a href="/ribes">David Ribes</a></h3> <p>Associate Professor<br /><a href="http://www.davidribes.com"><strong>Website</strong></a></p></td></tr></tbody></table>
<h3 class="uw-sidebar-heading"><a href="/people">People</a></h3><ul><li>x</li></ul>"""


def test_hcde_archived_h3_table_reads_every_cell_layout():
    es = F.uw_hcde_any(HCDE_2016)
    assert [(e['name_listed'], e['titles']) for e in es] == [('Cecilia Aragon', ['Associate Professor']), ('Julie Kientz', ['Associate Professor']),
                                                             ('David Ribes', ['Associate Professor'])]
    assert es[0]['homepage'] == '/aragon'


def test_profile_page_rank_followed_by_a_heading_is_evidence_only_on_a_single_person_page():
    pages = [('LING', 'u', 'sha', '20261122', 'Home People Gina-Anne Levow (she/her) Professor Contact Information levow@uw.edu')]
    assert C.faculty_evidence(pages, ['Gina-Anne Levow']) == []          # a directory: 'Professor Contact Information' could be the next entry
    ev = C.faculty_evidence(pages, ['Gina-Anne Levow'], single_person=True)
    assert ev and ev[0]['ladder'] and ev[0]['quote'] == 'Gina-Anne Levow (she/her) Professor'


def _row(url, checks):
    return {'pi': 'Ada Example', 'coverage': 'website', 'url': url, 'checks': checks}


def test_profile_link_through_meta_refresh_stub_is_an_official_link(monkeypatch):
    import labpage_audit as L
    monkeypatch.setattr(L, 'SCHOOLS', {'u': {'domain': r'school\.edu'}})
    r = _row('https://wp.school.edu/lab/', [
        {'source': 'school_profile', 'url': 'https://people.school.edu/ada/', 'at': '2026-11-22', 'result': 'ok', 'sha256': 'c' * 64},
        {'source': 'school_profile_link', 'url': 'https://depts.school.edu/lab/', 'at': '2026-11-22', 'result': 'listed', 'anchor': 'Ada Lab', 'on': 'https://people.school.edu/ada/'},
        {'source': 'meta_refresh_target', 'url': 'https://wp.school.edu/lab/', 'at': '2026-11-22', 'result': 'ok', 'on': 'https://depts.school.edu/lab/'}])
    out = W.archived_official_links('u', {'labs': [r]})['labs'][0]
    ev = out['official_link_evidence'][0]
    assert out['official_link_status'] == 'recorded' and ev['source'] == 'school_profile_link' and ev['via'] == 'meta_refresh'
    assert W.official_check(ev, out['url'])


def test_archived_listing_card_and_archived_profile_supply_official_links(monkeypatch, tmp_path):
    import labpage_audit as L
    monkeypatch.setattr(L, 'SCHOOLS', {'u': {'domain': r'school\.edu'}})
    lst, prof = tmp_path / 'listings.sqlite', tmp_path / 'school.sqlite'
    for path, cu, body in ((lst, 'https://web.archive.org/web/20180101000000id_/https://www.school.edu/people/faculty',
                            b"<div class='card'><h3>Ada Example</h3><a href='https://homes.school.edu/~ada/'>Homepage</a></div><div class='card'><h3>Bo Other</h3></div>"),
                           (prof, 'https://web.archive.org/web/20200101000000id_/https://www.school.edu/people/faculty/bo/',
                            b'<h1>Bo Other</h1><p>Professor</p><a href="http://homes.school.edu/~bo/">Personal website</a>')):
        con = sqlite3.connect(path)
        con.execute('create table captures(capture_url text, wayback_timestamp text, http_status integer, sha256 text, raw_zlib blob)')
        con.execute('insert into captures values (?,?,?,?,?)', (cu, cu.split('/web/')[1][:14], 200, 'd' * 64, zlib.compress(body)))
        con.commit()
    paths = {'listings-captures.sqlite': lst, 'school-captures.sqlite': prof}
    monkeypatch.setattr(W.P, 'data', lambda name, school=None, **k: paths[name])
    doc = {'labs': [_row('https://homes.school.edu/~ada/', []), dict(_row('https://homes.school.edu/~bo/', []), pi='Bo Other'),
                    dict(_row('https://homes.school.edu/~cy/', []), pi='Cy Nobody')]}
    a, b, c = W.archived_official_links('u', doc)['labs']
    assert a['official_link_evidence'][0]['source'] == 'department_listing_link' and a['official_link_evidence'][0]['source_sha256'] == 'd' * 64
    assert b['official_link_evidence'][0]['source'] == 'school_profile_link' and b['listed_on'] == 'https://www.school.edu/people/faculty/bo/'
    assert c.get('official_link_status') != 'recorded'


def test_contact_block_between_name_and_title_is_skipped_on_a_directory_card():
    flat = ('Space Systems Morgansen, Kristi (206) 616-5950 morgansn@uw.edu AER 234 Aeronautics & Astronautics Professor Electrical & Computer '
            'Engineering Adjunct Professor Mesbahi, Mehran (206) 543-7238 mesbahi@uw.edu GUG 311 Aeronautics & Astronautics Professor')
    ev = C.faculty_evidence([('AA', 'u', 'sha', '20261122', flat)], ['Kristi A. Morgansen'])
    assert ev and ev[0]['ladder'] and ev[0]['quote'].endswith('AER 234 Aeronautics & Astronautics Professor')
    # a phone that ENDS an entry still stops the reading: the next person's title is never this one's
    assert C.faculty_evidence([('X', 'u', 's', '2026', 'Lauro Ojeda Assistant Research Scientist (734) 555-1212 Chinedum Okwudire Associate Professor')],
                              ['Lauro Ojeda']) == []


def test_role_phrase_after_the_rank_is_not_the_next_persons_name():
    flat = ('John Gennari, PhD Professor Graduate Program Director Primary BHI gennari@uw.edu Website Interests: Ontologies. '
            'Dr Chao Li Professor Benedikt Loewe Professor')
    ev = C.faculty_evidence([('BIME', 'u', 'sha', '20241102', flat)], ['John H. Gennari'])
    assert ev and ev[0]['ladder'] and ev[0]['quote'] == 'John Gennari, PhD Professor'
    assert C.faculty_evidence([('X', 'u', 's', '2026', flat)], ['Chao Li']) == []


def test_affiliate_titles_are_not_ladder_only_where_the_charter_says_so():
    flat = ('Hoifung Poon, PhD Assistant Professor Affiliate BHI hoifung@microsoft.com Wanda Pratt, PhD, FACMI Professor Adjunct BHI '
            'Kim Example Affiliate Assistant Professor ')
    uw = C.not_ladder_titles('uwashington')
    ev = lambda n, t: [e['ladder'] for e in C.faculty_evidence([('BIME', 'u', 's', '2026', flat)], [n], t)]
    assert ev('Hoifung Poon', uw) == [False] and ev('Kim Example', uw) == [False] and ev('Wanda Pratt', uw) == [False]
    # without the charter setting (Georgia Tech: 'Affiliate Assistant Professor' is a ladder cross-listing) the rank stands
    assert ev('Kim Example', '') == [True] and ev('Hoifung Poon', '') == [True]


def test_stage5_dblp_ids_fold_into_hand_additions_without_replacing_their_own():
    from pihier.census import fold_dblp_ids
    ids = {'Yejin Choi': dict(pid='https://dblp.org/pid/89/579-1', basis='homepage_url', url='u', sha256='s', quote='q', orcid=['0000-0001']),
           'Own Id': dict(pid='https://dblp.org/pid/x', basis='school_affiliation')}
    a, b, c = fold_dblp_ids([dict(name='Yejin Choi', dblp=[]), dict(name='Own Id', dblp=['https://dblp.org/pid/mine']), dict(name='Nobody', dblp=[])], ids)
    assert a['dblp'] == ['https://dblp.org/pid/89/579-1'] and a['dblp_basis'] == 'homepage_url' and a['orcid'] == ['0000-0001']
    assert a['dblp_evidence'] == dict(url='u', sha256='s', quote='q')
    assert b['dblp'] == ['https://dblp.org/pid/mine'] and 'dblp_basis' not in b
    assert c == dict(name='Nobody', dblp=[])


def test_arriving_professor_is_not_yet_a_dated_appointment():
    import listing_rows as LR
    assert LR.rank_of(['Associate Professor (Arriving January 2027)']) == 'other'
    assert LR.rank_of(['Assistant Professor, joining in fall 2026']) == 'other'
    assert LR.rank_of(['Associate Professor']) == 'ladder'


def test_official_link_variants_compare_equal_but_hosts_and_paths_never_merge():
    n = W.normalized_link
    assert n('http://vsdesign.org//index.shtml') == n('https://vsdesign.org/')
    assert n('http://www2.ee.washington.edu:80/people/faculty/otis_brian/') == n('http://www2.ee.washington.edu/people/faculty/otis_brian')
    assert n('http://www.ee.washington.edu/people/faculty/x/') != n('http://www2.ee.washington.edu/people/faculty/x/')
    assert n('https://a.edu/~ann/') != n('https://a.edu/~bob/') and n('https://a.edu:8080/') != n('https://a.edu/')
    chk = dict(source='school_profile_link', url='http://vsdesign.org//index.shtml', on='https://ischool.uw.edu/people/faculty/profile/dhendry')
    assert W.official_check(chk, 'https://vsdesign.org/')


def test_surname_first_card_without_middle_initial_supplies_the_listing_link():
    html = (b"<table><tr><td><strong><a href='/people/faculty/otis_brian/'>Otis, Brian</a></strong></td></tr>"
            b"<tr><td><strong><a href='/people/faculty/other/'>Other, Brian</a></strong></td></tr></table>")
    base = 'http://www2.ee.washington.edu:80/people/faculty/'
    hit = W.listing_link_context(html, base, W.normalized_link('http://www2.ee.washington.edu/people/faculty/otis_brian/'), 'Brian P. Otis')
    assert hit and hit[1] == 'Otis, Brian'
    assert W.listing_link_context(html, base, W.normalized_link('http://www2.ee.washington.edu/people/faculty/other/'), 'Brian P. Otis') is None


def test_shared_group_site_is_verified_by_its_own_people_page_when_an_official_profile_links_it(monkeypatch, tmp_path):
    db = tmp_path / 'caps.sqlite'
    con = sqlite3.connect(db)
    con.execute('create table captures(sha256 text, content blob)')
    con.execute('insert into captures values (?,?)', ('a' * 64, zlib.compress(b'<h1>Systems Lab</h1><p>We build systems.</p>')))
    con.execute('insert into captures values (?,?)', ('b' * 64, zlib.compress(b'<p>Top row: Dan Ports, Tom Anderson, Hank Levy</p>')))
    con.commit()
    monkeypatch.setattr(W, 'capture_stores', lambda s: [db])
    monkeypatch.setattr(W, 'wayback_captures', lambda s: {})
    monkeypatch.setattr(W, 'website_review', lambda s, near=None: {})
    monkeypatch.setattr(W.P, 'data', lambda name, school=None, **k: tmp_path / name)
    prof = 'https://www.school.edu/people/faculty/tom-anderson/'
    row = dict(pi='Tom Anderson', url='https://syslab.school.edu/', coverage='website', sha256='a' * 64, official_link_status='recorded',
               checks=[dict(source='school_profile_link', url='https://syslab.school.edu/', on=prof, result='listed'),
                       dict(source='people_link', url='https://syslab.school.edu/people/', on='https://syslab.school.edu/', result='ok', sha256='b' * 64)])
    other = dict(row, pi='Hank Levy', checks=[c for c in row['checks'] if c['source'] == 'people_link'])   # no official link: never via the people page
    doc = W.verify_websites('u', {'labs': [row, other]})
    a, b = doc['labs']
    assert a['verified'] and a['verified_via']['sha256'] == 'b' * 64 and a['url'] == 'https://syslab.school.edu/'
    assert not b.get('verified')
