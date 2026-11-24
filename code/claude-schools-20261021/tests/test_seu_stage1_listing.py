import listing_formats as F


def test_seu_department_table_excludes_staff_and_keeps_rank_unknown():
    html = '''<title>教师按系别</title><div class="wp_articlecontent">
      <table><tr><td><a href="/cs">陈教授</a></td></tr></table>
      <table><tr><td><a href="/ce">王老师</a></td></tr></table>
      <table><tr><td><a href="/img">李老师</a></td></tr></table>
      <table><tr><td><a href="/admin">学院机关职员</a></td></tr></table>
      <table><tr><td><a href="/center">计算中心职员</a></td></tr></table>
      </div>'''
    rows = F.seu_department_faculty(html)
    assert [r['name_listed'] for r in rows] == ['陈教授', '王老师', '李老师']
    assert all(r['titles'] == ['教师'] for r in rows)


def test_seu_2024_desktop_and_mobile_copies_are_not_double_counted():
    table = '<table><tr><td><a href="/pi">张明</a></td></tr></table>'
    html = '<div class="desktop-view">' + table + '</div><div class="mobile-view">' + table + '</div>'
    assert len(F.seu_department_faculty(html)) == 1
