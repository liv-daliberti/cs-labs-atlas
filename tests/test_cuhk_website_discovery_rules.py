"""CUHK 2026-11-25 websites audit (15 of 50 failed): card-scoped personal-website links, unreadable hosts are access outcomes, excluded-campus pages."""
import types

import labpage_audit as L
import lab_websites as W

CARD = b"""<html><body>
<div class="people-wrap"><div class="people"><div class="people-info-wrap">
<div class="people-website"><a href="https://www.ee.cuhk.edu.hk/~hsli/">Personal Website</a></div></div>
<div class="people-name"><div class="people-name-wrap">LI Hongsheng</div></div></div></div>
<div class="people-wrap"><div class="people"><div class="people-website"><a href="/en/people/other/">Personal Website</a></div>
<div class="people-name"><div class="people-name-wrap">WONG Someone Else</div></div></div></div>
</body></html>"""


def fake_kit():
    def match_one(text, name):
        return sorted(text.lower().replace(',', ' ').split()) == sorted(name.lower().split())
    return types.SimpleNamespace(names=types.SimpleNamespace(match_one=match_one))


def test_card_link_is_taken_only_from_the_pis_own_card():
    got = L.card_website_links(fake_kit(), dict(content=CARD), 'https://www.erg.cuhk.edu.hk/erg/FacultyMembers', ['Hongsheng Li', 'LI Hongsheng'])
    assert got == [('https://www.ee.cuhk.edu.hk/~hsli/', 'Personal Website')]
    assert L.card_website_links(fake_kit(), dict(content=CARD), 'https://x.hk/', ['Nobody Else']) == []


def test_relative_card_links_resolve_against_the_listing():
    got = L.card_website_links(fake_kit(), dict(content=CARD), 'https://www.erg.cuhk.edu.hk/erg/FacultyMembers', ['Someone Else Wong'])
    assert got == [('https://www.erg.cuhk.edu.hk/en/people/other/', 'Personal Website')]


def lab_page(results, reason_code='no_web_presence_found'):
    checks = [dict(source='candidate_site', url='http://www.ee.cuhk.edu.hk/~x/', at='2026-11-25T00:00:00+00:00', result=r) for r in results]
    return dict(pi='X Y', audited_at='2026-11-25', lab_page=dict(status='none_found', reason_code=reason_code, reason='r', checks=checks))


def test_unreadable_host_is_an_access_outcome_not_no_web_presence():
    for result in ('robots_unknown', 'unreachable'):
        e = W.entry(lab_page([result], 'host_access_blocked'))
        assert e['coverage'] == 'reason' and e['reason_type'] == 'access_blocked'


def test_none_reason_names_an_unreadable_candidate_host():
    checks = [dict(source='candidate_site', url='u', result='robots_unknown')]
    code, why = L.none_reason(dict(pi='X Y', title='Professor'), None, checks)
    assert code == 'host_access_blocked' and 'not proof' in why
    code, _ = L.none_reason(dict(pi='X Y', title='Professor'), None, [dict(source='dblp_person_url', url='u', result='no_homepage_url')])
    assert code == 'no_web_presence_found'


def test_excluded_campus_page_is_not_this_schools_site(monkeypatch):
    import school_config
    cfg = dict(affiliation=dict(regex=r'\bthe\s+chinese\s+university\s+of\s+hong\s+kong\b(?!\s*[,(-]?\s*shenzhen\b)', excluded_regex=r'chinese\s+university\s+of\s+hong\s+kong\s*[,(-]?\s*shenzhen'))
    monkeypatch.setattr(school_config, 'get', lambda key: cfg)
    assert L.excluded_campus_only('cuhk', 'School of Data Science, The Chinese University of Hong Kong (Shenzhen); City University of Hong Kong')
    assert not L.excluded_campus_only('cuhk', 'Department of IE, The Chinese University of Hong Kong; also CUHK (Shenzhen)')
    assert not L.excluded_campus_only('cuhk', 'City University of Hong Kong only')


def test_own_host_tilde_page_with_the_address_as_anchor_text_is_a_personal_link():
    assert L.own_host_personal_link('https://www.math.cuhk.edu.hk/~btjin/', 'https://www.math.cuhk.edu.hk/~btjin/', 'www.math.cuhk.edu.hk', ['jin'])
    assert not L.own_host_personal_link('https://www.math.cuhk.edu.hk/people/other/', 'https://www.math.cuhk.edu.hk/people/other/', 'www.math.cuhk.edu.hk', ['jin'])
    assert not L.own_host_personal_link('https://www.math.cuhk.edu.hk/~abc/', 'https://www.math.cuhk.edu.hk/~abc/', 'www.math.cuhk.edu.hk', ['jin'])


NAMES_HTML = """<html><body>
<div class="people-wrap"><div class="people-website"><a href="http://www.se.cuhk.edu.hk/people/Anthony.html">Personal Website</a></div><div class="people-name"><div class="people-name-wrap">SO Man Cho Anthony</div></div></div>
<div class="people-wrap"><div class="people-website"><a href="http://www.ie.cuhk.edu.hk/people/chandra.shtml">Personal Website</a></div><div class="people-name"><div class="people-name-wrap">NAIR Chandra M.</div></div></div>
<div class="people-wrap"><div class="people-website"><a href="https://www.bme.cuhk.edu.hk/yuan/">Personal Website</a></div><div class="people-name"><div class="people-name-wrap">YUAN Wu Scott</div></div></div>
<div class="people-wrap"><div class="people-website"><a href="https://x.hk/a/">Personal Website</a></div><div class="people-name"><div class="people-name-wrap">LI Wei Ming</div></div></div>
<div class="people-wrap"><div class="people-website"><a href="https://x.hk/b/">Personal Website</a></div><div class="people-name"><div class="people-name-wrap">LI Wei Hong</div></div></div>
</body></html>""".encode()


def kit_no_matcher():
    return types.SimpleNamespace(names=types.SimpleNamespace(match_one=lambda t, n: None))


def cl(name):
    return [h for h, _ in L.card_website_links(kit_no_matcher(), dict(content=NAMES_HTML), 'https://x.hk/', [name])]


def test_name_token_order_initials_hyphens_and_a_unique_nickname_card():
    assert cl('Anthony Man-Cho So') == ['http://www.se.cuhk.edu.hk/people/Anthony.html']
    assert cl('Chandra Nair') == ['http://www.ie.cuhk.edu.hk/people/chandra.shtml']
    assert cl('Wu Yuan') == ['https://www.bme.cuhk.edu.hk/yuan/']


def test_an_extra_token_card_is_refused_when_two_cards_could_be_the_pi():
    assert cl('Wei Li') == []


def test_www_prefix_is_not_a_different_site_but_other_subdomains_are():
    assert W.normalized_link('https://www.yanzhenyu.com/') == W.normalized_link('https://yanzhenyu.com')
    assert W.normalized_link('https://www1.se.cuhk.edu.hk/~a/') != W.normalized_link('https://se.cuhk.edu.hk/~a/')
    assert W.normalized_link('https://a.example.org/x') != W.normalized_link('https://b.example.org/x')


def test_js_stub_on_a_school_host_forwards_to_the_pis_current_site():
    page = dict(status=200, content=b"<html><body><script language='javascript'>document.location = 'http://jiaya.me/'</script></body></html>")
    assert L.meta_refresh_target(page, 'https://www.cse.cuhk.edu.hk/~leojia', r'cuhk\.edu\.hk$') == 'http://jiaya.me/'
    assert L.meta_refresh_target(page, 'https://elsewhere.org/~x', r'cuhk\.edu\.hk$') is None


def test_placeholder_pages_and_plural_profile_paths():
    assert L.PLACEHOLDER_RX.search('Benjamin W. Wah These pages are best viewed with some recent version of Netscape.')
    assert L.PLACEHOLDER_RX.search('Welcome <html> You are not using a frames-compatible browser')
    assert not L.PLACEHOLDER_RX.search('Research interests: machine learning and systems.')
    assert L.is_profile('https://www4.mae.cuhk.edu.hk/peoples/liu-yun-hui/', r'cuhk\.edu\.hk')
    assert L.is_profile('https://www.se.cuhk.edu.hk/people/academic-staff/prof-viet-anh-nguyen/', r'cuhk\.edu\.hk')
    assert not L.is_profile('https://www.cse.cuhk.edu.hk/~leojia', r'cuhk\.edu\.hk')


def test_charter_tie_policy_accepts_dblp_or_orcid_sites_and_names_waiver(monkeypatch):
    import school_config
    cfg = dict(labpages=dict(official_tie_sources=['dblp_person_url'], official_link_site_needs_no_name=True))
    monkeypatch.setattr(school_config, 'get', lambda key: cfg)
    W.set_tie_policy('cuhk')
    try:
        chk = dict(source='dblp_person_url', url='https://dblp.org/pid/1', at='2026-11-25', result='listed', urls=['https://www.yanzhenyu.com/'])
        assert W.official_check(chk, 'https://yanzhenyu.com')
        assert not W.official_check(dict(chk, urls=['https://other.org/']), 'https://yanzhenyu.com')
        assert not W.official_check(dict(chk, result='no_homepage_url'), 'https://yanzhenyu.com')
        assert W.NAME_WAIVER[0]
    finally:
        monkeypatch.undo()
        W.set_tie_policy('no-such-school')
    assert not W.NAME_WAIVER[0] and not W.TIE_SOURCES
