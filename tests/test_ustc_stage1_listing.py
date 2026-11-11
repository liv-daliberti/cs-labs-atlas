from tools import listing_formats as F


def test_webplus_faculty_page_requires_every_pager_page():
    html = '''<li class="col_title"><h2>教授</h2></li>
    <a class="sub-link" href="/trjs/list.htm">特任教授</a>
    <div id="wp_news_w6"><ul class="news_list list2">
      <li class="news n1"><div class="news_title"><a href="/profiles/chen.htm">陈恩红</a></div>
      <div class="news_tel">cheneh@ustc.edu.cn</div></li>
      <li class="news n2"><div class="news_title"><a href="/profiles/an.htm">安 虹</a></div></li>
    </ul></div>
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
