from tools.listing_formats import whu_cs_rank_table


def test_whu_rank_table_keeps_printed_rank_and_profile_only():
    html = '''<a href="teacher.aspx">教师名录</a><table>
      <tr><th>姓名</th><th>性别</th><th>职称</th><th>研究方向</th></tr>
      <tr><td class="w1"><a href="teacherinfo.aspx?id=206">马于涛</a></td>
      <td class="w2">男</td><td class="w4">副教授</td><td class="w5">软件工程</td></tr>
      <tr><td class="w1"><a href="teacherinfo.aspx?id=17">黄华</a></td>
      <td class="w2">男</td><td class="w4">助教</td><td class="w5"></td></tr>
      <tr><td class="w1"><a href="news.aspx?id=1">通知</a></td><td class="w4">教授</td></tr>
      </table>'''
    assert whu_cs_rank_table(html) == [
        dict(name_listed='马于涛', titles=['副教授'], homepage=None,
             division=None, profile='teacherinfo.aspx?id=206'),
        dict(name_listed='黄华', titles=['助教'], homepage=None,
             division=None, profile='teacherinfo.aspx?id=17'),
    ]
