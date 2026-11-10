"""Tsinghua listing formats (CS list, School of Software names, IIIS cards, Automation cards): real markup of the captured pages."""
import listing_formats as L

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
