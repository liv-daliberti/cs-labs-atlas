"""PKU websites audit 2026-11-25: labelled homepage links on official unit profiles (classes a, c) and their access outcome handling."""
from profile_homepage_links import profile_homepage_links

BASE = 'https://sai.pku.edu.cn/info/1362/2264.htm'


def urls(html, base=BASE):
    return [c['url'] for c in profile_homepage_links(html, base)]


def test_label_then_plain_text_url_in_the_next_paragraph():   # ai.pku 周嘉欢
    html = '<p>电子邮件：x@pku.edu.cn</p><p>个人主页：</p><p>https://zhoujiahuan1991.github.io/ </p>'
    assert urls(html, 'https://www.ai.pku.edu.cn/info/1312/2839.htm') == ['https://zhoujiahuan1991.github.io']


def test_label_then_anchor_on_another_host():   # sai 王奕森, 方聪
    html = '<p>个人主页：<a href="https://yisenwang.github.io/">https://yisenwang.github.io/</a></p>'
    assert urls(html) == ['https://yisenwang.github.io']


def test_scheme_relative_and_bare_host_links():   # cs 詹乃军: 个人主页：//lcs.ios.ac.cn/~znj/
    assert urls('<div>个人主页：//lcs.ios.ac.cn/~znj/</div>', 'https://cs.pku.edu.cn/info/1086/2961.htm') == ['https://lcs.ios.ac.cn/~znj']
    html = '<p>个人主页：<a href="lcs.ios.ac.cn/~znj/">主页</a></p>'
    assert urls(html, 'https://cs.pku.edu.cn/info/1086/2961.htm') == ['http://lcs.ios.ac.cn/~znj']


def test_college_hosted_personal_page_is_a_link_too():   # ai.pku 谢广明 -> www2.coe.pku.edu.cn
    html = '<p>个人主页：http://www2.coe.pku.edu.cn/subpaget.asp?id=58</p>'
    assert urls(html) == ['http://www2.coe.pku.edu.cn/subpaget.asp?id=58']


def test_next_field_label_ends_the_address_and_identity_hosts_are_skipped():
    html = '<p>个人主页：https://shaofengjiang.cn招生须知：https://x.example</p><p>个人主页：https://scholar.google.com/citations?user=1</p>'
    assert urls(html) == ['https://shaofengjiang.cn']


def test_a_profile_without_the_label_yields_nothing():   # the generic unit profile is not a homepage (class c)
    assert urls('<p>研究领域：计算机视觉</p><a href="https://orcid.org/0000">ORCID</a>') == []


def test_han_name_on_a_han_page_verifies_gbk_and_utf8():   # 彭宇新 (utf-8 page with only 'pengyuxin' in Latin), 谢广明 (GBK college site)
    from person_fetch import names_person
    ok, q = names_person('<title>北京大学多媒体信息处理研究室：彭宇新</title>'.encode(), '彭宇新')
    assert ok and '彭宇新' in q
    ok, q = names_person('<h1>基本信息 谢广明 教授</h1>'.encode('gb18030'), '谢广明')
    assert ok
    assert not names_person('<p>其他人</p>'.encode(), '彭宇新')[0]


def test_pku_unit_profile_pages_are_profile_cards_not_websites():   # class (c): 姜少峰's CFCS faculty card was recorded as his lab site
    import labpage_audit as LA
    import lab_websites as LW
    LA.set_profile_pages('pku')
    try:
        for u in ('https://cfcs.pku.edu.cn/english/people/faculty/shaofengjiang/index.htm', 'https://cs.pku.edu.cn/info/1069/1630.htm',
                  'https://idm.pku.edu.cn/en/info/1009/1017.htm', 'https://cfcs.pku.edu.cn/english/'):
            assert 'selected_url_is_profile_card' in LW.selection_gaps(u), u
        for u in ('https://cfcs.pku.edu.cn/yuqkong/', 'http://www2.coe.pku.edu.cn/subpaget.asp?id=58', 'https://yisenwang.github.io/'):
            assert 'selected_url_is_profile_card' not in LW.selection_gaps(u), u
    finally:
        LA.PROFILE_PAGES[:] = []


def test_an_unreadable_linked_host_is_an_access_outcome_not_no_web_presence():   # class (b): 李胜 (graphics.pku), 袁晓如 (vis.pku)
    import lab_websites as LW
    row = dict(pi='李胜', coverage='reason', reason_code='host_access_blocked', reason='reviewed: the profile prints the address; two live attempts failed',
               checks=[dict(source='reviewed_absence_source', url='https://cs.pku.edu.cn/info/1071/3089.htm', at='2026-11-25T12:00:00+00:00', result='reviewed_host_access_blocked')])
    assert LW.gate(dict(school='', labs=[row]), ['李胜']) == []
    assert 'host_access_blocked' in LW.ABSENCE_REASONS
