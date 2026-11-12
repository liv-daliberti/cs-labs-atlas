from tools.listing_formats import hit_cs_current_table


def test_hit_plain_name_table_stays_in_cs_and_keeps_disambiguation_markers():
    html = '''<p><strong>计算机科学与技术学院</strong></p><div><table>
      <tr><td colspan="4">容错与移动计算研究中心</td></tr>
      <tr><td>董剑</td><td>吴晋 <sup>2</sup></td><td>STAMOULIS DIMITRIOS</td><td></td></tr>
      </table></div><p>国家示范性软件学院</p><table><tr><td>其他教师</td></tr></table>'''
    rows = hit_cs_current_table(html)
    assert [r['name_listed'] for r in rows] == ['董剑', '吴晋 2', 'STAMOULIS DIMITRIOS']
    assert all(r['titles'] == ['教师'] and r['division'] == '容错与移动计算研究中心' and r['profile'] is None for r in rows)
    assert hit_cs_current_table('<p>计算机学院导航</p>') == []
