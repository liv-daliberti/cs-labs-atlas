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
