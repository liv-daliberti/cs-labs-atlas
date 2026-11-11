from tools import listing_formats as F


def test_webplus_faculty_page_requires_every_pager_page():
    html = '''<li class="col_title"><h2>教授</h2></li>
    <a class="sub-link" href="/trjs/list.htm">特任教授</a>
    <div class="col_news_list listcon"><div id="wp_news_w6"><ul class="news_list list2">
      <li class="news n1"><div class="news_title"><a href="/profiles/chen.htm">陈恩红</a></div>
      <div class="news_tel">cheneh@ustc.edu.cn</div></li>
      <li class="news n2"><div class="news_title"><a href="/profiles/an.htm">安 虹</a></div></li>
    </ul></div></div>
    <ul class="wp_paging"><li class="page_nav"><a href="/js_23235/list3.htm">尾页</a></li>
    <li><em class="curr_page">1</em>/<em class="all_pages">3</em></li></ul>'''
    fmt, rows = F.parse(html)
    assert fmt == 'ustc_cs_cards'
    assert [(r['name_listed'], r['titles'], r['profile']) for r in rows] == [
        ('陈恩红', ['教授'], '/profiles/chen.htm'),
        ('安 虹', ['教授'], '/profiles/an.htm'),
    ]
    assert F.is_paged(html)
    assert F.page_links(html, 'https://cs.ustc.edu.cn/js_23235/list.htm') == {
        1: 'https://cs.ustc.edu.cn/js_23235/list2.htm',
        2: 'https://cs.ustc.edu.cn/js_23235/list3.htm',
    }


def test_legacy_profile_sidebar_uses_rank_rosters_and_ignores_biography():
    html = '''<a class="gk">教授</a><table><tr><td>
      <a href="../../bdjs/201006/t20100614_22053.html">陈恩红</a>
    </td></tr></table>
    <a class="gk">副教授</a><table><tr><td>
      <a href="../../fjs/201006/t20100614_22054.html">董兰芳</a>
    </td></tr></table>
    <a class="gk">博士后</a><table><tr><td>
      <a href="../../bsh/201007/t20100701_23943.html">博士后名单</a>
    </td></tr></table>
    <div class="wp_articlecontent"><h1>陈国良</h1><p>个人简介</p></div>'''
    rows = F.parse(html, 'ustc_cs_legacy_sidebar')[1]
    assert [(r['name_listed'], r['titles']) for r in rows] == [
        ('陈恩红', ['教授']), ('董兰芳', ['副教授'])]
