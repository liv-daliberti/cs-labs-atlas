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
