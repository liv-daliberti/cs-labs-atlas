"""PKU WICT (team nav 2016-18, m-list cards 2019-) and SIST (ltjs cards) listing formats; fixtures are trimmed saved captures."""
from tools import listing_formats as LF

TEAM = ('<ul><li class="leftchild"><a href=content_86.htm>肖建国_ 教授</a></li>'
        '<li class="leftchild"><a href=content_258.htm>孙&nbsp;俊_ 教授</a></li>'
        '<li class="leftchild"><a href=content_3283.htm><SPAN>连宙辉</SPAN>_ 副教授</a></li>'
        '<li class="leftchild"><a href=content_111.htm>陈&nbsp; 峰_ 高级工程师</a></li><li class="leftchild"><a href="x.htm">无职称</a></li></ul>')
CARDS = ('<ul class="m-list"><li><div class="m-tt"><a href="1222602.htm" target="_blank">陈峰 </a><em>高级工程师</em><p>图形</p></div>'
         '<div class="m-cont"><a href="chen_feng@pku.edu.cn">chen_feng@pku.edu.cn</a></div></li>'
         '<li><div class="m-tt"><a href="1222604.htm">陈文拯</a><em>助理教授</em></div></li></ul>'
         '<div class="onethink pagination pagination-right"><div><span class="current">1</span><a class="num" href="index1.htm">2</a><a class="next" href="index1.htm">>></a></div></div>')
SIST = ('<div class="ltjs_nr"><a href="../info/1362/2268.htm" target="_blank" title="陈宝权"><div class="ltjs_text"><h3>陈宝权</h3><dl>'
        '<dd><b>职称：</b>教授</dd><dd><b>研究领域：</b>图形</dd><dd><b>电子邮件：</b>baoquan@pku.edu.cn</dd></dl></div></a></div>'
        '<div class="ltjs_nr"><a href="../info/1362/2249.htm"><div class="ltjs_text"><h3>陈婧</h3><dl><dd><b>职称：</b>研究员</dd></dl></div></a></div>')


def test_wict_team_nav():
    assert [(e['name_listed'], e['titles'], e['profile']) for e in LF.pku_wict_team_nav(TEAM)] == [
        ('肖建国', ['教授'], 'content_86.htm'), ('孙俊', ['教授'], 'content_258.htm'), ('连宙辉', ['副教授'], 'content_3283.htm'), ('陈峰', ['高级工程师'], 'content_111.htm')]


def test_wict_cards_and_pager():
    es = LF.pku_wict_cards(CARDS)
    assert [(e['name_listed'], e['titles']) for e in es] == [('陈峰', ['高级工程师']), ('陈文拯', ['助理教授'])]
    assert LF.is_paged(CARDS)
    assert LF.page_links(CARDS, 'http://www.icst.pku.edu.cn/xztd/xztd_01/index.htm') == {
        1: 'http://www.icst.pku.edu.cn/xztd/xztd_01/index1.htm'}


def test_sist_cards_keep_no_contact_lines():
    es = LF.pku_sist_cards(SIST)
    assert [(e['name_listed'], e['titles'], e['profile']) for e in es] == [('陈宝权', ['教授'], '../info/1362/2268.htm'), ('陈婧', ['研究员'], '../info/1362/2249.htm')]
