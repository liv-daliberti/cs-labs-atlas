"""Chinese-school website register: gate, name/role extraction, URL normalisation (no network)."""
import person_websites_cn as C


def test_gate_matches_reason_rule():
    ok = dict(person='王', role='pi', lab='王', kind='pi_home', url=None, reason='no personal website found')
    assert C.gate([ok]) == []
    assert C.gate([dict(ok, reason=None)])
    bad = dict(ok, url='https://x.example.cn/', found_from={}, fetched=False, fetch_reason='queued')
    assert C.gate([bad])


def test_norm_url_ignores_index_and_trailing_slash():
    assert C.norm_url('http://a.cn/~x/index.html') == C.norm_url('http://a.cn/~x/')
    assert C.norm_url('https://a.cn/x/main.htm') == C.norm_url('https://a.cn/x')


def test_person_text_and_roles_verbatim():
    assert C.is_person_text('张 伟') and C.is_person_text('Ada Lovelace') and not C.is_person_text('更多')
    html = ('<h3>博士研究生</h3><a href="/z">张三</a><h3>硕士研究生</h3><a href="http://l.example.cn/li">李四</a>'
            '<a href="/news">研究成果</a>').encode()
    got = [(t, r) for t, h, r in C.role_of_headings(html) if C.is_person_text(t)]
    assert got == [('张三', '博士研究生'), ('李四', '硕士研究生')]


def test_decode_falls_back_to_gb18030():
    assert C.decode('测试'.encode('gb18030')) == '测试'


def test_link_kind_filters_organisations():
    assert C.link_kind('Programming Languages Laboratory', 'http://pl.example.cn/', 'x') == 'group'
    assert C.link_kind('IFIP Working Group 2.1', 'http://w.example.org/', 'x') is None
    assert C.link_kind('个人主页', 'http://p.example.cn/~a', 'x') == 'pi_home'


def test_clean_members_drops_unrecognisable_roles_with_reason():
    mk = lambda role: dict(kind='member_home', lab='L', person='张三', url='http://x/', found_from={'url': 'http://p/'}, member_role_stated=role)
    keep, dropped = C.clean_members([mk('博士研究生'), mk('Past MS Students:'), mk('not stated on the page'), mk('研究生教学'), mk("master's degree")])
    assert len(keep) == 3 and len(dropped) == 2 and all(d['reason'] for d in dropped)


def test_person_text_needs_a_surname_and_no_nav_words():
    assert C.is_person_text('张三') and C.is_person_text('宛 斌')
    for nav in ('内部资源', '研究生', '查看更多', '尾页', '中心主任', '发表论文', '课程信息', '获奖信息', 'Minimal Mistakes', 'Google Scholar'):
        assert not C.is_person_text(nav), nav
