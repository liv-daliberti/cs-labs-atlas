"""Tsinghua listing formats (CS list, School of Software names, IIIS cards, Automation cards): real markup of the captured pages."""
import listing_formats as L


DPI_ARCHIVE = '''<div class="home home3"><div class="dl"><h6>导航类别</h6></div><div class="dr">
<div class="third" id="光电工程研究所"><h5>光电工程研究所</h5><ul>
<li><a href="/jgf-dpi.html"><img title="金国藩"></a><h6>金国藩</h6><p>中国工程院院士</p></li>
<li><a href="/lifengli.html"><img title="李立峰"></a><h6>李立峰</h6><p>教授</p></li>
<li><a href="/liyan.html"><img title="李岩"></a><h6>李 岩</h6><p>教授</p></li>
<li><a href="/yanghd.html"><img title="杨怀栋"></a><h6>杨怀栋</h6><p>副研究员</p></li>
</ul></div><div class="third" id="系机关"><h5>系机关</h5><ul>
<li><a href="/staff.html"><img title="曾海明"></a><h6>曾海明</h6><p>科研办公室</p></li>
</ul></div></div></div>'''


def test_dpi_archive_keeps_each_cards_written_role_and_institute():
    fmt, rows = L.parse(DPI_ARCHIVE, 'tsinghua_dpi_archive')
    assert fmt == 'tsinghua_dpi_archive'
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [
        ('金国藩', ['中国工程院院士'], '光电工程研究所'),
        ('李立峰', ['教授'], '光电工程研究所'),
        ('李岩', ['教授'], '光电工程研究所'),
        ('杨怀栋', ['副研究员'], '光电工程研究所'),
        ('曾海明', ['科研办公室'], '系机关'),
    ]
    assert rows[1]['profile'] == '/lifengli.html'
    assert rows[2]['quote_name'] == '李 岩'
    assert '导航类别' not in str(rows)


def test_dpi_archive_staff_title_does_not_become_faculty():
    from listing_rows import rank_of
    rows = L.parse(DPI_ARCHIVE, 'tsinghua_dpi_archive')[1]
    local_ranks = {'ladder': '教授'}
    assert rank_of(rows[-1]['titles'], local_ranks) == 'other'
    assert rank_of(rows[1]['titles'], local_ranks) == 'ladder'


def test_dpi_archive_requires_a_name_role_and_real_profile_link():
    malformed = '''<li><a href="javascript:;"><img title="王甲"></a><h6>王甲</h6><p>教授</p></li>
    <li><a href="/x.html"><img title="李乙"></a><p>教授</p></li>
    <li><a href="/y.html"><h6>张丙</h6></a></li>
    <li><a href="/z.html"></a><h6>周丁</h6><p>private@example.org</p></li>'''
    page = '<div class="home3"><div class="dr"><div class="third" id="所"><h5>所</h5><ul>' + malformed + '</ul></div></div></div>'
    assert L.parse(page, 'tsinghua_dpi_archive')[1] == []


def test_dpi_archive_quote_uses_its_own_title_without_adjacent_contact_text():
    from listing_rows import quote_of
    from bs4 import BeautifulSoup
    page = DPI_ARCHIVE.replace('<p>副研究员</p>', '<p>副研究员</p><p>private@example.org</p>')
    rows = L.parse(page, 'tsinghua_dpi_archive')[1]
    flat = ' '.join(BeautifulSoup(page, 'html.parser').get_text(' ', strip=True).split())
    assert quote_of(flat, rows[2]) == '李 岩 教授'
    assert rows[3]['titles'] == ['副研究员']
    assert 'private@example.org' not in str(rows)

CS = '''<div class="people01-nr"><dl><dt><h4>计算机软件研究所</h4></dt><dd class="clear"><h3>正高</h3><ul class="clear">
<li><div class="pic"><a href="../info/1111/3490.htm" title="冯建华"><img src="x.jpg" /></a></div><div class="text">
<h2><a href="../info/1111/3490.htm" title="冯建华">冯建华</a></h2><p>教授</p><p>62789150</p><p>fengjh@tsinghua.edu.cn</p></div></li>
<li><div class="text"><h2><a href="../info/1111/3489.htm" title="冯铃">冯铃</a></h2><p>教授</p><p>010-62773581</p></div></li></ul></dd></dl></div>'''
SW = '''<div class="group-title">院士</div> <div class="group-people"><div class="name-container"><a href="../faculty/sunjiaguang.htm" title="孙家广" class="up-link name">孙家广</a></div></div>
<div class="group-title">软件系统与工程研究所</div> <div class="group-people"><div class="name-container"><a href="../faculty/guming.htm" class="up-link name">顾明</a></div></div>'''
IIIS = '''<ul class="ls16 flex"><li data-aos="fade-up"><a href="rydw/qzjs/yaoqizhi.htm" title="姚期智" class="a"><div class="top flexjs"><div class="txt"><h4>姚期智</h4><p>院长，教授</p></div></div>
<div class="bottom"><h4 class="l2 h4s2">算法，密码学</h4></div></a></li></ul>'''
AU = '''<ul class="list13 flex"><li data-aos="fade-up"><a href="../../../info/1077/3123.htm" class="a"><div class="con"><h3><big>周东华</big></h3></div></a></li></ul>'''


def test_cs_list_rows_titles_and_division_without_contact_lines():
    fmt, rows = L.parse(CS)
    assert fmt == 'tsinghua_cs_list'
    assert [r['name_listed'] for r in rows] == ['冯建华', '冯铃']
    assert rows[0]['titles'] == ['教授'] and rows[0]['division'] == '计算机软件研究所'
    assert 'fengjh' not in str(rows) and '62789150' not in str(rows)


def test_sw_names_keep_the_band_as_division():
    fmt, rows = L.parse(SW)
    assert fmt == 'tsinghua_sw_names'
    assert [(r['name_listed'], r['division']) for r in rows] == [('孙家广', '院士'), ('顾明', '软件系统与工程研究所')]


def test_iiis_card_title_is_the_txt_line_not_the_interests():
    fmt, rows = L.parse(IIIS)
    assert fmt == 'tsinghua_iiis_cards' and rows[0]['titles'] == ['院长，教授'] and len(rows) == 1


def test_au_card_name_only():
    fmt, rows = L.parse(AU)
    assert fmt == 'tsinghua_au_cards' and rows[0]['name_listed'] == '周东华' and rows[0]['titles'] == []

AU22 = '<div class="research-name">控制与决策研究所</div><div class="teacher-list"><a href="../../../info/1077/1622.htm"><div class="item">黄德先</div></a><a href="javascript:;"><div class="item">吉吟东</div></a></div>'
AIR = '<div class="yjtd_tit"><h1>Professor</h1></div><div class="yjtd_nr"><ul><li><a href="../info/1046/1188.htm" title="Ya-Qin Zhang"><div class="yjtd_nwz"><h2>Ya-Qin Zhang</h2><h3>Founding Dean/Chair Professor</h3><p>Chair Professor</p></div></a></li></ul></div>'


def test_au_2022_template_keeps_institute_and_drops_javascript_links():
    fmt, rows = L.parse(AU22)
    assert fmt == 'tsinghua_au_cards' and [r['name_listed'] for r in rows] == ['黄德先', '吉吟东']
    assert rows[0]['division'] == '控制与决策研究所' and rows[1]['profile'] is None


def test_air_cards_band_name_and_title():
    fmt, rows = L.parse(AIR)
    assert fmt == 'tsinghua_air_cards' and rows[0]['name_listed'] == 'Ya-Qin Zhang' and rows[0]['titles'] == ['Founding Dean/Chair Professor'] and rows[0]['division'] == 'Professor'


def test_slot_with_a_format_is_usable_when_english_title_lines_and_latin_names_cannot_see_the_listing(monkeypatch):
    """Tsinghua captures (Chinese names and titles) were all 'unusable' (0 English title lines, no Latin PI-name match) until a slot's own format counted."""
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'listings' / 'scripts'))  # route-ok: tracked code, not data
    import types
    import plan_fetch as PF
    html = CS.replace('</ul>', ''.join(f'<li><div class="text"><h2><a href="../info/1111/{i}.htm">甲{i}</a></h2><p>教授</p></div></li>' for i in range(6)) + '</ul>')
    monkeypatch.setattr(PF.wb, 'body', lambda raw: raw)
    monkeypatch.setitem(PF._CFG, 'x', types.SimpleNamespace(CHARTER=True))
    monkeypatch.setattr(PF, 'usable', lambda blocks, status, pis, school: (False, 'no listing in the capture'))

    class Con:
        def execute(self, q, a):
            return type('C', (), {'fetchone': lambda me: (html.encode(),)})()
    assert PF.slot_usable(Con(), 'u', {'format': 'tsinghua_cs_list'}, [], 200, [], 'x') == (True, None)
    assert not PF.slot_usable(Con(), 'u', {}, [], 200, [], 'x')[0]
    assert not PF.slot_usable(Con(), 'u', {'format': 'tsinghua_cs_list'}, [], 404, [], 'x')[0]


CSOLD = '''<div class="box_detail"><h1 style="text-align: center;"><span>计算机科学与技术系在职教师名录</span></h1><p>（2019年12月更新，按拼音顺序）</p><h1><span>计算机软件研究所</span></h1><ul class=" list-paddingleft-2"><li><p>正高：&nbsp;<a href="/publish/cs/4616/2010/a.html">蔡懿慈</a>， <a href="/publish/cs/4616/2011/b.html">冯 铃</a></p></li><li><p>副高： <a href="/publish/cs/4616/2011/c.html">陈 渝</a></p></li></ul></div>'''
IIISM = '''<h4 class="color_danger">教授系列</h4><div class="row"><div class="media"><div class="media-body"><strong><a href="http://iiis.tsinghua.edu.cn/zh/yao/" target="_blank">姚期智</a></strong><br> 院长，教授 <br> 算法分析，量子计算 <br></div></div></div>'''


def test_cs_old_list_bands_names_and_institute():
    fmt, rows = L.parse(CSOLD)
    assert fmt == 'tsinghua_cs_old_list'
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('蔡懿慈', ['正高'], '计算机软件研究所'), ('冯铃', ['正高'], '计算机软件研究所'), ('陈渝', ['副高'], '计算机软件研究所')]


def test_iiis_media_title_is_the_line_after_the_name():
    fmt, rows = L.parse(IIISM)
    assert fmt == 'tsinghua_iiis_media' and rows == [dict(name_listed='姚期智', titles=['院长，教授'], profile='http://iiis.tsinghua.edu.cn/zh/yao/', homepage=None, division='教授系列')]


SWOLD = '''<div id="s2_right_con"><p>&nbsp;</p><p style="TEXT-ALIGN: center">教师名录</p><p><strong>院士</strong></p><p><a href="/publish/soft/3641/2010/a.html" a="">孙家广</a></p><hr/>
<p><strong>杰青</strong></p><p><a href="/publish/soft/3641/2010/b.html">向东</a>&nbsp;&nbsp;&nbsp;<a href="/publish/soft/3641/2010/c.html">雍俊海</a><strong>&nbsp;&nbsp;&nbsp;</strong></p><hr/>
<p><strong>特聘教授</strong></p><p>Philip.S.Yu </p><hr/><p><strong>讲师/助理研究员/助理教授</strong></p><p><a href="/publish/soft/3641/2011/d.html">宋韶旭</a>&nbsp;&nbsp;&nbsp; 万海&nbsp;&nbsp;<a href="/publish/soft/3641/2013/e.html">刘克彬</a></p></div>'''


def test_sw_old_list_bands_links_and_plain_names():
    fmt, rows = L.parse(SWOLD)
    assert fmt == 'tsinghua_sw_old_list'
    got = [(r['name_listed'], r['titles'][0], bool(r['profile'])) for r in rows]
    assert got == [('孙家广', '院士', True), ('向东', '杰青', True), ('雍俊海', '杰青', True), ('Philip.S.Yu', '特聘教授', False),
                   ('宋韶旭', '讲师/助理研究员/助理教授', True), ('刘克彬', '讲师/助理研究员/助理教授', True), ('万海', '讲师/助理研究员/助理教授', False)]


EER = '''<ul class="ul-listb3"><li id="yjs_1"><div class="con"><div class="type">信息光电子研究所</div><div class="txt"><div class="line" id="zc_1_1"><div class="l" id="showdatatitle1">高 级：</div>
<div class="t"><ul id="showdatainfo1"><a href="http://web.ee.tsinghua.edu.cn/chenhongwei/zh_CN/index.htm" target="_blank">陈宏伟</a><a href="http://web.ee.tsinghua.edu.cn/luoyi/zh_CN/index.htm">罗毅</a></ul></div></div>
<div class="line" id="zc_1_2"><div class="l">副高级：</div><div class="t"><ul id="showdatainfo2"><a href="http://web.ee.tsinghua.edu.cn/x/zh_CN/index.htm">甲乙</a></ul></div></div></div></div></li></ul>'''


def test_ee_rendered_institute_band_and_names():
    fmt, rows = L.parse(EER)
    assert fmt == 'tsinghua_ee_rendered'
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('陈宏伟', ['高级'], '信息光电子研究所'), ('罗毅', ['高级'], '信息光电子研究所'), ('甲乙', ['副高级'], '信息光电子研究所')]


EEE = '''<ul><li id="yjs_1"> <div class="con"> <div class="type">信息光电子研究所</div></div></li></ul><script>
function topage_1_1(keyword, yjly, szm) { var qh_itemid = "showdatainfo1"; var qh_data = [{"showTitle":"陈宏伟","fields":{"szm":"C"},"url":{"asString":"http://web.ee.tsinghua.edu.cn/chenhongwei/zh_CN/index.htm"}},{"showTitle":"罗毅","fields":{},"url":{"asString":"http://web.ee.tsinghua.edu.cn/luoyi/zh_CN/index.htm"}}]; x }
function topage_1_2(keyword, yjly, szm) { var qh_itemid = "showdatainfo2"; var qh_data = [{"showTitle":"熊兵","fields":{},"url":{"asString":"http://web.ee.tsinghua.edu.cn/xiongbing/zh_CN/index.htm"}}]; x }</script>'''


def test_ee_embedded_json_bands_and_institute():
    fmt, rows = L.parse(EEE)
    assert fmt == 'tsinghua_ee_embedded'
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('陈宏伟', ['高级'], '信息光电子研究所'), ('罗毅', ['高级'], '信息光电子研究所'), ('熊兵', ['副高级'], '信息光电子研究所')]


EET = '''<html><body><div>首页 &gt; 人员情况 &gt; 在职教师 图片列表 信息光电子研究所 教 授： 陈宏伟 陈明华 副教授： 鲍捷 讲 师： 甘霖 通信研究所 教 授： 陈巍</div><div>版权所有 清华大学电子工程系</div></body></html>'''
AUOLD = '''<div class="box_detail"><p><span>系统集成研究所</span></p><p>教 授 / 研究员</p><table uetable="null"><tbody><tr><td><a href="/publish/au/1714/a.html"><img src="x.jpg"/></a></td></tr>
<tr><td><div><a href="/publish/au/1714/a.html">吴 澄</a></div><div>教授</div></td><td><div><a href="/publish/au/1714/b.html">柴跃廷</a></div><div>研究员</div></td></tr></tbody></table></div>'''
INSCB = '''<p><strong>教授：</strong></p><p><a href="../info/1157/1.htm">段海新</a> &nbsp; <a href="../info/1157/2.htm">王继龙</a></p><p><strong>副教授：</strong></p><p><a href="../info/1157/3.htm">王会</a> &nbsp; 李宗鹏</p>'''


def test_ee_text_archived_template():
    fmt, rows = L.parse(EET)
    assert fmt == 'tsinghua_ee_text'
    assert [(r['name_listed'], r['titles'][0], r['division']) for r in rows] == [('陈宏伟', '教授', '信息光电子研究所'), ('陈明华', '教授', '信息光电子研究所'), ('鲍捷', '副教授', '信息光电子研究所'), ('甘霖', '讲师', '信息光电子研究所'), ('陈巍', '教授', '通信研究所')]


def test_au_old_list_names_and_titles_from_text_cells():
    fmt, rows = L.parse(AUOLD)
    assert fmt == 'tsinghua_au_old_list'
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('吴澄', ['教授'], '系统集成研究所'), ('柴跃廷', ['研究员'], '系统集成研究所')]


def test_insc_bands_links_and_plain_names():
    rows = L.tsinghua_insc_bands(INSCB)
    assert [(r['name_listed'], r['titles'][0], bool(r['profile'])) for r in rows] == [('段海新', '教授', True), ('王继龙', '教授', True), ('王会', '副教授', True), ('李宗鹏', '副教授', False)]


def test_ee_any_tries_embedded_then_rendered_then_text():
    assert [r['name_listed'] for r in L.tsinghua_ee_any(EEE)] == ['陈宏伟', '罗毅', '熊兵']
    assert [r['name_listed'] for r in L.tsinghua_ee_any(EER)] == ['陈宏伟', '罗毅', '甲乙']
    assert [r['name_listed'] for r in L.tsinghua_ee_any(EET)][:2] == ['陈宏伟', '陈明华']


ME_EN = '<h2 class="sz_tit">Professor</h2><ul><li class="ss"><a href="../../info/1283/1913.htm" target="_blank" title="Zhipeng Cai"><div class="con"><p class="bt">Zhipeng Cai</p></div></a></li></ul><h2 class="sz_tit">Assistant Professor</h2><ul><li class="ss"><a href="../../info/1/2.htm" title="Ann Lee"><p class="bt">Ann Lee</p></a></li></ul>'
ME_ZH = '<a word="中级" href="../info/1092/1531.htm" target="_blank" title="卢文秀">卢文秀</a> <a word="中级" href="../info/1098/1584.htm" title="赵　彤">赵　彤</a>'
MATH = '<div class="post fwBold">副教授</div><dl class="deptList gp-flex"><dd><a href="../../info/1376/3001.htm">陈大广</a></dd><dd><a href="https://ymsc.tsinghua.edu.cn/info/1032/5361.htm">刁晗生</a></dd></dl><div class="post">教 授</div><dl><dd><a href="x.htm">张三</a></dd></dl>'
BME = '<div class="ny-right"><div class="position"><div><h2> 教研系列（按姓氏音序横向排列）</h2></div></div><ul><li><a href="../../info/1118/1598.htm" title="丁长海"><div class="info"><p>丁长海</p></div></a></li></ul></div>'


def test_me_en_bands_are_the_ranks():
    rows = L.tsinghua_me_en(ME_EN)
    assert [(r['name_listed'], r['titles']) for r in rows] == [('Zhipeng Cai', ['Professor']), ('Ann Lee', ['Assistant Professor'])]


def test_me_zh_is_names_only_the_word_attribute_is_not_a_rank():
    rows = L.tsinghua_me_zh(ME_ZH)
    assert [(r['name_listed'], r['titles']) for r in rows] == [('卢文秀', []), ('赵彤', [])]


def test_math_bands_join_split_cjk_and_follow_the_post_div():
    rows = L.tsinghua_math_bands(MATH)
    assert [(r['name_listed'], r['titles']) for r in rows] == [('陈大广', ['副教授']), ('刁晗生', ['副教授']), ('张三', ['教授'])]


def test_bme_series_is_not_a_rank():
    rows = L.tsinghua_bme_cards(BME)
    assert [(r['name_listed'], r['titles']) for r in rows] == [('丁长海', ['教研系列'])]


DPI = '<ul><li> <a href="/houbo/zh_CN/index.htm"><div class="pics"></div><div class="info"><h3>侯波</h3><div><p>职称：副教授</p><p>单位：导航技术工程中心</p></div></div></a></li><li><a href="/x/zh_CN/index.htm"><div class="info"><h3>杨 军</h3><div><p>职称：副研究员</p></div></div></a></li></ul>'


def test_dpi_rendered_cards_keep_title_and_unit():
    rows = L.tsinghua_dpi_rendered(DPI)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('侯波', ['副教授'], '导航技术工程中心'), ('杨军', ['副研究员'], None)]


# ---- older site eras (stage 1 gate, 2026-11-14): excerpts of archived pages, rows from the real markup ----
EEOLD = ('<div class="box_detail"><p><strong>信息光电子研究所</strong></p><p>院&nbsp;&nbsp; &nbsp;士： <a title="周炳琨" href="/x/1.html">周炳琨</a>&nbsp;&nbsp;</p>'
         '<p>教 授： &nbsp;<a title="陈明华" href="/x/2.html">陈明华</a>&nbsp;&nbsp;|&nbsp; <a href="/x/3.html">宁存政</a></p>'
         '<p>副教授： &nbsp;<a href="/x/4.html">陈宏伟</a>&nbsp;|&nbsp; <a href="/x/5.html">冯雪</a>&nbsp;|&nbsp; <a href="/x/6.html">尤&nbsp; 政</a></p></div>')


def test_banded_text_rosters_keep_band_division_and_join_spaced_names():
    rows = L.tsinghua_banded_text(EEOLD)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [
        ('周炳琨', ['院士'], '信息光电子研究所'), ('陈明华', ['教授'], '信息光电子研究所'), ('宁存政', ['教授'], '信息光电子研究所'),
        ('陈宏伟', ['副教授'], '信息光电子研究所'), ('冯雪', ['副教授'], '信息光电子研究所'), ('尤政', ['副教授'], '信息光电子研究所')]


MATHOLD = ('<div class="box_detail"><p>基础数学研究所</p><p>1999年更名并建立基础数学研究所。研究方向包括：数论与算术几何，量子代数。</p><p>本所在职教师30人， 其中教授16人。</p>'
           '<p>教授：<a href="/a">步尚全</a>（1995年清华学术新人奖、2003年新世纪优秀人才）、邓邦明、Masood、<a href="/b">肖杰</a>（1999年国家杰出青年基金）、姚家燕。</p>'
           '<p>副教授：陈大广、姚国武（2005年全国优秀博士论文)、张宇光。</p><p>讲师：艾颖华。</p></div>')


def test_banded_text_ignores_prose_and_strips_award_parentheses():
    rows = L.tsinghua_banded_text(MATHOLD)
    assert [(r['name_listed'], r['titles'][0]) for r in rows] == [
        ('步尚全', '教授'), ('邓邦明', '教授'), ('Masood', '教授'), ('肖杰', '教授'), ('姚家燕', '教授'),
        ('陈大广', '副教授'), ('姚国武', '副教授'), ('张宇光', '副教授'), ('艾颖华', '讲师')]


MEOLD = ('<div class="box_detail">摩擦学研究所<table><tr><td>正高级</td></tr><tr><td>长聘教授/首席研究员：</td><td>温诗铸</td><td>周&nbsp; 明</td></tr>'
         '<tr><td>高级工程师/工程师、实验师/编辑</td><td>秦 力</td></tr><tr><td>所长：</td><td>陈大广</td></tr></table></div>')


def test_banded_text_skips_engineer_and_director_bands():
    rows = L.tsinghua_banded_text(MEOLD)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('温诗铸', ['长聘教授/首席研究员'], '摩擦学研究所'), ('周明', ['长聘教授/首席研究员'], '摩擦学研究所')]
    assert rows[1]['quote_name'] == '周 明' and 'quote_name' not in rows[0]


def test_banded_text_unknown_label_is_not_a_rank_band():
    rows = L.tsinghua_banded_text('<div class="box_detail"><p>教授：甲乙丙</p><p>学术带头人：吴建平</p><p>副教授：王会</p></div>')
    assert [(r['name_listed'], r['titles'][0]) for r in rows] == [('甲乙丙', '教授'), ('王会', '副教授')]


def test_me_column_letter_bucket_links():
    rows = L.tsinghua_me_column('<div class="tea-text"><a word="C" href="../essay/89/461.html">蔡志鹏</a><a word="C" href="../essay/83/419.html">陈 恳</a></div>')
    assert [(r['name_listed'], r['titles']) for r in rows] == [('蔡志鹏', []), ('陈恳', [])]
    assert rows[1]['quote_name'] == '陈 恳'


BMEP = ('<div class="content width1000 clearfix"><div class="cont_item "><h2>教研系列</h2><div><table><tr><td class="title">神经工程</td><td><ul>'
        '<li><a href="Person?method=102&perId=55">高小榕 </a></li><li><a href="Person?method=102&perId=64"> 宋森 </a></li></ul></td></tr></table></div></div></div>')


def test_bme_person_table_series_title_and_area_division():
    rows = L.tsinghua_bme_person_table(BMEP)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('高小榕', ['教研系列'], '神经工程'), ('宋森', ['教研系列'], '神经工程')]


BMEM = ('<div class="content_li"><div class="title001"><h3> 神经工程</h3></div><div class="fl00"><ul><li><a href="../../../info/1356/3826.htm" target="_blank" title="高上凯">'
        '<h5><font>高上凯</font></h5></a></li></ul></div></div>')


def test_bme_med_area_cards():
    rows = L.tsinghua_bme_med_areas(BMEM)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('高上凯', ['教研系列'], '神经工程')]


IIISP = ('<div class="list_team"><ul><li><div class="item"><div class="info"><div class="name"><a href="/zh/yao/">姚期智</a></div><div class="area">院长，教授</div>'
         '<div class="area">算法</div></div></div></li></ul></div>')


def test_iiis_people_cards_keep_first_area_line_as_title():
    rows = L.tsinghua_iiis_people(IIISP)
    assert [(r['name_listed'], r['titles']) for r in rows] == [('姚期智', ['院长，教授'])]


AIRZ = ('<div class="yjtd_tit"><h1>教授、研究员</h1></div><div class="yjtd_nr"><ul><li><a href="../info/1046/1207.htm" title="张亚勤"><div class="yjtd_nwz">'
        '<h2><b>张亚勤</b>院长/讲席教授</h2><p>清华大学讲席教授</p></div></a></li></ul></div>')


def test_air_zh_cards_split_name_from_title():
    rows = L.tsinghua_air_zh_cards(AIRZ)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('张亚勤', ['院长/讲席教授'], '教授、研究员')]


AUA = ('<div class="list-line" id="C"><div class="word f-left">C</div><div class="n-list f-left"><a href="../../info/1088/1507.htm"><div class="item">柴跃廷</div></a>'
       '<a href="javascript:;"><div class="item">曹 丽</div></a></div></div>')


def test_au_alpha_names_only_javascript_links_have_no_profile():
    rows = L.tsinghua_au_alpha(AUA)
    assert [(r['name_listed'], r['titles'], r['profile']) for r in rows] == [('柴跃廷', [], '../../info/1088/1507.htm'), ('曹丽', [], None)]
    assert rows[1]['quote_name'] == '曹 丽'


def test_banded_text_zhenggao_fugao_bands_with_sort_remark():
    rows = L.tsinghua_banded_text('<div class="box_detail"><p>骨干教师</p><p><br/>正高（按姓氏拼音排序）：<br/>毕军、段海新<br/>副高（按姓氏拼音排序）：<br/>安长青、包丛笑</p></div>')
    assert [(r['name_listed'], r['titles'][0]) for r in rows] == [('毕军', '正高'), ('段海新', '正高'), ('安长青', '副高'), ('包丛笑', '副高')]
