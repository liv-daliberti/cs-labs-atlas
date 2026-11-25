import json

import lab_websites as W
import official_profile_links as PL

BASE = 'https://cse.hkust.edu.hk/admin/people/faculty/profile/x'


def test_homepage_anchor_is_the_site_not_the_profile_or_a_unit_root():
    html = ('<a href="/faculty/x/">Personal Webpage</a> <a href="https://hkust.edu.hk/">Homepage</a> '
            '<a href="' + BASE + '">Homepage</a> <a href="https://scholar.google.com/x">Scholar Profile</a>')
    assert PL.homepage_anchors(html, BASE) == [('https://cse.hkust.edu.hk/faculty/x/', 'Personal Webpage')]


def test_listing_hit_stops_at_the_next_card():
    html = ('<div class="team-item"><span>Sen LI</span><a href="https://a.example/">Homepage</a></div>'
            '<div class="team-item"><span>Bo WU</span><a href="https://b.example/">Homepage</a></div>')
    href, blk = PL.listing_hit(html, ['Sen Li'])
    assert [u for u, _ in PL.homepage_anchors(blk, 'https://u.example/list')] == ['https://a.example/']


def test_json_node_listing_gives_the_nodes_own_reference_link():
    html = ('"nid":[{"value":1}],"title":[{"value":"Ling SHI"}],"field_reference_link":[{"uri":"https:\\/\\/s.example\\/","title":"Personal Homepage","options":[]}],"alias":"\\/eesling"'
            '"nid":[{"value":2}],"title":[{"value":"Bo WU"}],"field_reference_link":[{"uri":"https:\\/\\/b.example\\/","title":"Personal Homepage","options":[]}]')
    alias, links = PL.json_nodes(html, ['Ling Shi'])
    assert alias == '/eesling' and links == [('https://s.example/', 'Personal Homepage')]


def _doc(monkeypatch, tmp_path, row, captures):
    f = tmp_path / 'profile-links.json'
    f.write_text(json.dumps({'rows': [row]}))
    monkeypatch.setattr(W.P, 'data', lambda name, school=None, **k: f)
    monkeypatch.setattr(W, 'stored_captures', lambda school, urls: {u: v for u, v in captures.items() if u in urls})
    lab = {'pi': 'A', 'coverage': 'website', 'url': BASE, 'sha256': 'f' * 64, 'checks': [], 'official_link_status': 'not_recorded'}
    return W.apply_profile_links('x', {'labs': [lab]})['labs'][0]


PROF = dict(pi='A', profile_url=BASE, fetched_at='2026-11-25T05:00:00+00:00', status='ok', sha256='a' * 64)


def test_linked_site_with_a_capture_replaces_the_profile_url(monkeypatch, tmp_path):
    lab = _doc(monkeypatch, tmp_path, dict(PROF, link=dict(url='https://a.example/~x/', anchor='Personal Webpage')),
               {'https://a.example/~x/': ('b' * 64, 't', 'page')})
    assert lab['url'] == 'https://a.example/~x/' and lab['sha256'] == 'b' * 64 and lab['official_link_status'] == 'recorded'


def test_linked_site_without_a_capture_stays_pending_never_absent(monkeypatch, tmp_path):
    lab = _doc(monkeypatch, tmp_path, dict(PROF, link=dict(url='https://h.home.example/', anchor='Personal Homepage')), {})
    assert lab['coverage'] == 'pending' and lab['evidence_gaps'] == ['linked_site_not_captured'] and lab['linked_site'] == 'https://h.home.example/'


def test_profile_without_a_link_turns_an_unlinked_site_into_a_quoted_absence(monkeypatch, tmp_path):
    lab = _doc(monkeypatch, tmp_path, dict(PROF, link=None), {})
    assert lab['coverage'] == 'reason' and lab['reason_code'] == 'profile_only_no_homepage' and PROF['profile_url'] in lab['reason']


def test_icon_link_with_a_personal_web_address_label_counts():
    html = '<a href="http://x.github.io/" aria-label="Personal web address" title="Personal web address"><i class="icon"></i></a>'
    assert PL.homepage_anchors(html, BASE) == [('http://x.github.io/', 'Personal web address')]


def test_address_printed_as_text_after_the_label_counts():
    html = '<p>Links: Personal Webpage https://amir.example/ Research Area</p>'
    assert PL.homepage_anchors(html, BASE) == [('https://amir.example/', 'Personal Webpage')]


def test_portal_slugs_from_latin_names():
    assert PL.portal_slugs(['Hongbo Fu', 'Hongbo FU 傅紅波', 'Kam Tim Woo']) == ['hongbo-fu', 'kam-woo', 'kam-tim-woo']


def test_unit_pages_are_followed_and_office_sites_are_not_homepages():
    assert PL.UNIT_PAGE('https://www.math.hkust.edu.hk/people/faculty/profile/makxu/') and PL.UNIT_PAGE('https://ece.hkust.edu.hk/eeklau')
    assert not PL.UNIT_PAGE('https://eejzhang.people.ust.hk/') and not PL.UNIT_PAGE('https://cse.hkust.edu.hk/~x/') and not PL.UNIT_PAGE('https://x.github.io/')
    assert PL.homepage_anchors('<a href="http://hkustprovost.hkust.edu.hk/meet-provost">Personal web address</a>', BASE) == []


def test_url_variants_cover_the_hkust_host_families_and_cse_personal_forms():
    v = W.url_variants('https://cse.hkust.edu.hk/faculty/golin/')
    assert 'http://www.cse.ust.hk/~golin/' in v and 'https://cse.hkust.edu.hk/~golin/' in v
    assert 'http://meyklee.people.ust.hk/' not in v


def test_robots_rule_reads_an_ai_crawler_group_before_the_star_group():
    body = "User-agent: *\nAllow: /\n\nUser-agent: ClaudeBot\nDisallow: /\n"
    assert PL.robots_rule(body, 'https://x.example/page') == (False, 'ClaudeBot', 'Disallow: /')
    assert PL.robots_rule("User-agent: *\nDisallow: /private\n", 'https://x.example/a') == (True, '*', None)
    assert PL.robots_rule("User-agent: *\nDisallow: /private\n", 'https://x.example/private/a')[0] is False


def test_hyphenated_given_name_matches_its_unhyphenated_spelling_in_a_listing():
    # HKUST ECE lists 'Chi Ying TSUI' for the PI recorded as 'Chi-Ying Tsui'
    node = '"nid":[{"value":1}],"title":[{"value":"Chi Ying TSUI"}],"field_reference_link":[{"uri":"https:\\/\\/t.example\\/","title":"Personal Home Page","options":[]}],"alias":"\\/eetsui"'
    alias, links = PL.json_nodes(node, ['Chi-Ying Tsui'])
    assert alias == '/eetsui' and links == [('https://t.example/', 'Personal Home Page')]
    assert PL.name_regexes(['Chi-Ying Tsui'])[0].search('Chi Ying TSUI') and PL.name_regexes(['Chi-Ying Tsui'])[0].search('TSUI, ChiYing')


def test_row_evidence_names_the_url_its_capture_was_stored_under(monkeypatch, tmp_path):
    import json
    f = tmp_path / 'profile-links.json'
    f.write_text(json.dumps({'rows': [dict(pi='A', profile_url=BASE, fetched_at='2026-11-25T05:00:00+00:00', status='ok', sha256='a' * 64,
                                           link=dict(url='https://cse.hkust.edu.hk/faculty/x/', anchor='Personal Webpage'))]}))
    monkeypatch.setattr(W.P, 'data', lambda name, school=None, **k: f)
    caps = {'http://www.cse.ust.hk/~x/': ('1' * 64, 't', 'page'), 'http://www.cse.ust.hk/faculty/x/': ('2' * 64, 't', 'page')}
    monkeypatch.setattr(W, 'stored_captures', lambda school, urls: {u: v for u, v in caps.items() if u in urls})
    row = W.apply_profile_links('x', {'labs': [{'pi': 'A', 'coverage': 'pending', 'checks': []}]})['labs'][0]
    assert row['sha256'] == '2' * 64 and row['evidence']['captured_url'] == 'http://www.cse.ust.hk/faculty/x/'   # the exact address wins over its ~login twin


def test_url_variants_include_the_default_port_spelling():
    assert 'http://www.cse.ust.hk:80/faculty/golin/' in W.url_variants('https://cse.hkust.edu.hk/faculty/golin/')
