import listing_formats as F


BASE = ('https://faculty.uestc.edu.cn/xylb.jsp?urltype=tsites.CollegeTeacherList'
        '&wbtreeid=1021&st=0&id=2031&lang=zh_CN')


def test_uestc_college_roster_is_paged_and_parses_only_titled_people():
    html = '''<div class="ex_img"><ul>
      <li><span><h2><a href="/alice">Alice</a></h2><p>教授</p></span></li>
      <li><span><h2><a href="/bob">Bob</a></h2><p></p></span></li>
      </ul></div><div class="totality">共175条 1/11
      <a href="?totalpage=11&PAGENUM=2&urltype=tsites.CollegeTeacherList&wbtreeid=1021&st=0&id=2031&lang=zh_CN">下页</a>
      <a href="?totalpage=11&PAGENUM=11&urltype=tsites.CollegeTeacherList&wbtreeid=1021&st=0&id=2031&lang=zh_CN">尾页</a></div>'''
    assert F.uestc_college_teachers(html) == [
        dict(name_listed='Alice', titles=['教授'], homepage=None,
             division=None, profile='/alice')]
    assert F.is_paged(html)
    pages = F.page_links(html, BASE)
    assert len(pages) == 10
    assert 'PAGENUM=2' in pages[1]
    assert 'PAGENUM=11' in pages[10]
