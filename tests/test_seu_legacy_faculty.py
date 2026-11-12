from tools.listing_formats import seu_department_faculty


def test_legacy_department_tables_exclude_offices_and_preserve_unlinked_names():
    html = '''<h2>计算机科学系</h2><table class="table-name"><tr>
      <td><a href="/PersonalPage/a/index.htm">陈汉武</a></td><td>耿新</td></tr></table>
      <h2>计算机工程系</h2><table class="table-name"><tr><td>曹玖新</td></tr></table>
      <h2>影像科学与技术系</h2><table class="table-name"><tr><td>陈阳</td></tr></table>
      <h2>学院机关</h2><table class="table-name"><tr><td>其他职工</td></tr></table>
      <h2>计算中心</h2><table class="table-name"><tr><td>中心职工</td></tr></table>'''
    rows = seu_department_faculty(html)
    assert [r['name_listed'] for r in rows] == ['陈汉武', '耿新', '曹玖新', '陈阳']
    assert rows[0]['profile'] == 'http://cse.seu.edu.cn/PersonalPage/a/index.htm'
    assert rows[1]['profile'] is None
    assert rows[-1]['division'] == '影像科学与技术系'


def test_current_department_table_keeps_names_with_no_href_and_printed_role_notes():
    html = '''<div class="wp_articlecontent"><h2>计算机科学系</h2><table><tr>
      <td><a textvalue="曹玲玲">曹玲玲</a></td><td>狄 凯(博士后)</td><td>王帅</td><td>王帅</td><td></td>
      </tr></table></div>'''
    rows = seu_department_faculty(html)
    assert [r['name_listed'] for r in rows] == ['曹玲玲', '狄 凯(博士后)', '王帅', '王帅']
    assert all(r['profile'] is None and r['titles'] == ['教师'] for r in rows)
