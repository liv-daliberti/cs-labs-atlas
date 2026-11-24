import listing_formats as F

PAGER = ('<span class="p_pages"><span class="p_no_d">1</span><span class="p_no"><a href="jyxl/11.htm">2</a></span>'
         '<span class="p_no"><a href="jyxl/10.htm">3</a></span><span class="p_dot">...</span>'
         '<span class="p_no"><a href="jyxl/1.htm">12</a></span></span>')


def test_pku_cards_and_namelist():
    cards = ('<ul class="list15 list15s flex"><li><a href="../../../info/1061/1602.htm"><div class="con"><h3><big>边凯归</big></h3>'
             '<p>职称：长聘副教授</p><p>研究所：数据科学与工程研究所</p></div></a></li></ul>')
    e = F.pku_cs_cards(cards)
    assert e[0]['name_listed'] == '边凯归' and e[0]['titles'] == ['长聘副教授'] and e[0]['division'] == '数据科学与工程研究所'
    old = ('<ul class="m-list9" id="teachernamelist"><li><div class="txt"><h4><a href="../info/1008/1090.htm">曹永知</a></h4>'
           '<p>教授</p><p>软件研究所</p></div></li></ul>')
    e = F.pku_cs_namelist(old)
    assert e[0]['name_listed'] == '曹永知' and e[0]['titles'] == ['教授']
    assert F.parse(old)[0] == 'pku_cs_namelist'


def test_webplus_reverse_numbered_pager():
    html = '<div>' + PAGER + '</div>'
    assert F.is_paged(html)
    pages = F.page_links(html, 'https://cs.pku.edu.cn/szdw1/jyxl.htm')
    assert pages[1].endswith('/szdw1/jyxl/11.htm') and pages[11].endswith('/szdw1/jyxl/1.htm') and len(pages) == 11


def test_uestc_scse_bands():
    html = ('<div class="list"><div class="listHead"><span>正高</span></div><div class="listBody">'
            '<a href="info/1082/7261.htm">陈端兵</a></div></div>')
    assert F.uestc_scse_bands(html) == [dict(name_listed='陈端兵', quote_name='陈端兵', titles=['正高'], profile='info/1082/7261.htm', homepage=None, division=None)]
