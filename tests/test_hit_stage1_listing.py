from tools import listing_formats


def test_hit_2018_teacher_rows_keep_source_category_without_inventing_rank():
    html = '''<a href="/nav" title="所有教师名录">所有教师名录</a>
    <div id="wp_news_w6"><table class="wp_article_list_table">
      <tr><td><a href="/profile/1" title="王玲">王玲</a></td><td>2018-03-12</td></tr>
      <tr><td><a href="/profile/2" title="刘绍辉">刘绍辉</a></td><td>2017-12-05</td></tr>
    </table></div>'''
    rows = listing_formats.hit_teacher_list(html)
    assert [(r['name_listed'], r['titles'], r['profile']) for r in rows] == [
        ('王玲', ['教师'], '/profile/1'),
        ('刘绍辉', ['教师'], '/profile/2'),
    ]
