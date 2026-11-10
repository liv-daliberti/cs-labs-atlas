from listing_formats import parse
from listing_rows import rank_of


def test_hkust_bilingual_names_roles_and_profiles_without_contact_cells():
    html = '''<table><tr><th>Name</th><th>Rank</th></tr>
    <tr class="search"><td class="name"><a href="profile/zxf">Xiaofang ZHOU<br>周曉方</a></td>
    <td>Named Professor of Engineering<br>&nbsp;Chair Professor and Head</td>
    <td><a href="javascript:msend('zxf')">private-contact</a></td><td>55551234</td></tr>
    <tr class="search"><td class="name"><a href="profile/other">Robin EXAMPLE</a></td>
    <td>Visiting Professor</td><td>another-contact</td></tr></table>'''
    _, rows = parse(html, 'hkust_faculty_table')
    assert len(rows) == 2
    assert rows[0]['name_listed'] == 'Xiaofang ZHOU 周曉方'
    assert rows[0]['titles'] == ['Named Professor of Engineering', 'Chair Professor and Head']
    assert rows[0]['profile'] == 'profile/zxf'
    assert rows[0]['homepage'] is None
    assert rank_of(rows[0]['titles']) == 'ladder'
    assert rank_of(rows[1]['titles']) == 'visiting'
    assert 'private-contact' not in str(rows)
    assert '55551234' not in str(rows)


def test_hkust_ignores_unlinked_and_incomplete_table_rows():
    html = '<tr class="search"><td class="name">No link</td><td>Professor</td></tr>'
    assert parse(html, 'hkust_faculty_table')[1] == []


CARDS = '''<a class="card news-card people-card search" href="profile/dyyeung"><div class="content"><p class="people-name">Dit-Yan YEUNG</p>
<p class="people-info1">Professor and Head</p></div></a><a class="card news-card people-card search" href="profile/dyyeung"><p class="people-name">Dit-Yan YEUNG</p></a>'''
POSITION = '''<table class="ruler fancy"><tbody><tr><td>
<a href="/~gchan/">CHAN, Shueng-Han Gary</a></td><td class="nowrap">陳雙幸</td><td>x</td><td>6990</td><td>3543</td><td>Professor</td><td>NE</td></tr></tbody></table>'''


def test_hkust_card_era_listing_parses_once_per_person():
    _, rows = parse(CARDS, 'hkust_faculty_any')
    assert [r['name_listed'] for r in rows] == ['Dit-Yan YEUNG'] and rows[0]['titles'] == ['Professor and Head']


def test_hkust_position_table_era_listing_parses_name_title():
    _, rows = parse(POSITION, 'hkust_faculty_any')
    assert rows[0]['name_listed'] == 'CHAN, Shueng-Han Gary 陳雙幸' and rows[0]['titles'] == ['Professor']


def test_listing_pi_years_account_ids_agree_across_url_eras():
    import listing_pi_years as L
    assert L.account('https://cse.hkust.edu.hk/admin/people/faculty/profile/gchan') == 'gchan'
    assert L.account('profile/gchan') == 'gchan'
    assert L.account('/~gchan/') == 'gchan'
    assert L.account('https://cse.hkust.edu.hk/faculty/horner/') == 'horner'
    assert L.account('https://cse.hkust.edu.hk/admin/people/faculty/') is None


def test_labpage_audit_has_the_shared_wayback_throttle():
    import labpage_audit as A
    assert A._host_throttle() is not None and hasattr(A._host_throttle(), 'cooldown_left')


def test_same_account_personal_link_on_the_profile_host():
    import labpage_audit as A
    prof = 'https://cse.hkust.edu.hk/admin/people/faculty/profile/wilfred'
    assert A.same_account_personal_link('https://cse.hkust.edu.hk/faculty/wilfred/', 'Personal Webpage', prof)
    assert A.same_account_personal_link('https://cse.hkust.edu.hk/~wilfred/', 'Personal Webpage', prof)
    assert not A.same_account_personal_link('https://cse.hkust.edu.hk/~other/', 'Personal Webpage', prof)
    assert not A.same_account_personal_link('https://cse.hkust.edu.hk/faculty/wilfred/', 'Publications list', prof)


def test_publication_list_names_are_not_students():
    import labpage_audit as A
    q = 'Xiaozhe Yao, Youhe Jiang, Binhang Yuan. “LLMFabric: Unifying Decentralized HPC Clusters for Heterogeneous LLM Serving.” In 20th USENIX Symposium, 2026.'
    assert A.publication_item('Selected Publications > 2026', q, q)
    assert A.publication_item(None, q, q)
    assert not A.publication_item('Current Group Members', 'PhD student (2022-present)', 'Tianyi Bai PhD 2026')
    assert not A.publication_item('Publications and students', 'PhD student', 'Ann Lee PhD 2024')


def test_long_comma_author_lists_are_bylines():
    import labpage_audit as A
    assert A.byline_item('Xiaozhe Yao, Youhe Jiang , Ilia Badanin, Qinghao Hu,')
    assert A.byline_item('Jiarui Zhang *, Yuchen Yang*, Ran Yan , Zhiyu Mei, Liyuan Zhang,')
    assert not A.byline_item('Luyu Cheng (PhD 2021-2026), Ann Lee')


def test_page1_tie_accepts_a_parenthesised_nickname_before_the_family_name():
    import re
    import pi_fulltext_affiliation as F
    aff = re.compile(r'hong\s+kong\s+university\s+of\s+science\s+and\s+technology', re.I)
    flat = 'Preprint Yiyang Fang1,5 Pei Fu2 Yi R. (May) Fung5 Mang Ye1 1 Wuhan University 5 The Hong Kong University of Science and Technology fangyiyang@whu.edu.cn Abstract'
    how, quotes = F.tie(flat, [('Yi', 'Fung')], aff)
    assert how == 'marker' and 'Fung5' in quotes[0] and 'Hong Kong University' in quotes[1]


def test_page1_quote_matches_a_bilingual_census_name():
    from pihier import papers
    assert papers.page1_quote_names_pi(['Yi R. FUNG 馮一人'], ['Yi R. (May) Fung5 ', '5 The Hong Kong University of Science and Technology'])
    assert papers.page1_quote_names_pi(['Jiasi SHEN 沈嘉思'], ['JIASI SHEN, The Hong Kong University of Science and Technology'])
    assert not papers.page1_quote_names_pi(['Yi R. FUNG 馮一人'], ['Wei Wang, The Hong Kong University'])


def test_official_homepage_fallback_selects_the_profile_linked_page_and_keeps_the_old_site(monkeypatch):
    import lab_websites as L
    chk = dict(source='school_profile_link', url='https://cse.hkust.edu.hk/~x/', on='https://cse.hkust.edu.hk/admin/people/faculty/profile/x', result='listed', at='2026-11-10T00:00:00+00:00')
    doc = dict(labs=[dict(pi='A B', coverage='website', url='https://lab.example/', sha256='a' * 64, kind='lab_site', found_via='prior', checks=[chk], official_link_status='not_recorded',
                          people_page='https://lab.example/people')])
    monkeypatch.setattr(L, 'stored_captures', lambda school, urls: {'https://cse.hkust.edu.hk/~x/': ('b' * 64, 'now', 'A B home')})
    r = L.official_homepage_fallback('hkust', doc)['labs'][0]
    assert r['url'] == 'https://cse.hkust.edu.hk/~x/' and r['official_link_status'] == 'recorded' and r['sha256'] == 'b' * 64
    assert r['website_note']['replaced_url'] == 'https://lab.example/' and r['website_note']['people_page'] == 'https://lab.example/people'
    assert any(L.official_check(c, r['url']) for c in r['checks'])


def test_prior_degree_phrases_are_not_roles():
    import labpage_audit as A
    role_of = lambda t: ('masters' if 'master' in t.lower() else 'undergraduate' if 'undergrad' in t.lower() or 'bachelor' in t.lower() else 'phd' if 'phd' in t.lower() else 'member', 0)
    assert A.entry_role("(Bachelor's from X University, Hong Kong PhD Fellowship)", 'Students > Current/Incoming PhD students', role_of)[0] != 'undergraduate'
    assert A.entry_role("Master's from Y University", 'Current PhD students', role_of)[0] != 'masters'
    assert A.entry_role('(Master student, 2023-2025)', 'Members', role_of)[0] == 'masters'
