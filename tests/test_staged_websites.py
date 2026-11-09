"""Staged-school website sweep: name and role parsing, member links, and the register gate."""
import person_websites as PW
import staged_websites as S


def test_looks_like_name():
    assert S.looks_like_name('Ada Lovelace') == 'Ada Lovelace'
    assert S.looks_like_name('Dr. Ada M. Lovelace') == 'Ada M. Lovelace'
    assert S.looks_like_name('José Álvarez-Smith') is None or S.looks_like_name('Jose Alvarez-Smith')
    assert S.looks_like_name('Publications') is None
    assert S.looks_like_name('Machine Learning Group') is None
    assert S.looks_like_name('Read more') is None
    assert S.looks_like_name('王小明') == '王小明'


def test_member_links_carry_their_heading_and_adjacent_name():
    html = (b'<h3>PhD Students</h3><ul><li><a href="http://ada.example.org/">Ada Lovelace</a></li>'
            b'<li>Bo Peep <a href="/~bo">homepage</a></li></ul><h3>Teaching</h3><p><a href="/t">Intro</a></p>')
    p = S.parse(html, 'https://lab.example.edu/people/')
    byurl = {x['url']: x for x in p.links}
    assert byurl['http://ada.example.org/']['heading'] == 'PhD Students'
    assert byurl['https://lab.example.edu/~bo']['block_name'] == 'Bo Peep'
    assert byurl['https://lab.example.edu/t']['heading'] == 'Teaching'


def test_row_fetch_states():
    ff = dict(kind='official_page', url='https://cs.example.edu/p', sha256='a' * 64)
    g = dict(status=200, at='2026-11-08T00:00:00', sha256='b' * 64, final_url='https://x.example.org/', note=None)
    r = S.row('Ada', 'pi', 'Ada', 'pi_home', 'https://x.example.org/', ff, g, (True, None))
    assert r['fetched'] and r['sha256'] == 'b' * 64 and r['names_person'] is True
    r = S.row('Ada', 'pi', 'Ada', 'pi_profile', 'https://scholar.google.com/citations?user=1', ff, profile_type='third_party')
    assert not r['fetched'] and 'not fetchable' in r['fetch_reason']
    g = dict(status=None, at=None, sha256=None, final_url=None, note='host refused automated access (HTTP 403); queue for Wayback only')
    r = S.row('Ada', 'pi', 'Ada', 'pi_home', 'https://y.example.org/', ff, g)
    assert not r['fetched'] and r['wayback_queue'] and PW.gate({'rows': [r]}) == []


def test_reg_domain_and_canon():
    assert S.reg_domain('www.cs.ox.ac.uk') == 'ox.ac.uk'
    assert S.reg_domain('www.comp.nus.edu.sg') == 'nus.edu.sg'
    assert S.canon('HTTPS://A.org#x') == 'https://a.org/'
