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
