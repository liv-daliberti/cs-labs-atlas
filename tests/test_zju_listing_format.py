"""ZJU College of Computer Science teacher directory (csen/27003): names-only anchors inside ul.zuzhi."""
import listing_formats as F

PAGE = """<span class="titl">人工智能研究所</span><ul class="zuzhi"><li><h5>教师列表</h5>
<a href='https://person.zju.edu.cn/min_zhang' target='_blank' title='章敏'>章敏</a>
<a href='https://person.zju.edu.cn/kunkuang' target='_blank' title='况  琨'>况  琨</a>
<a href='http://mypage.zju.edu.cn/xilics/' target='null' title='李　玺'>李　玺</a>
<a href='/csen/2019/0611/c27055a1223691/page.htm' target='_blank' title='徐从富'>徐从富</a>
<a href='http://mypage.zju.edu.cn/dyb' title='董亚波'>董亚波</a></li></ul>"""


def test_zju_cs_zuzhi_names_parse_and_register():
    rows = F.FORMATS['zju_cs_zuzhi_names'][0](PAGE)
    assert [r['name_listed'] for r in rows] == ['章敏', '况琨', '李玺', '徐从富', '董亚波']
    assert rows[0]['profile'] == 'https://person.zju.edu.cn/min_zhang' and rows[0]['division'] == '人工智能研究所' and rows[0]['titles'] == []
    assert F.FORMATS['zju_cs_zuzhi_names'][1].search(PAGE)
    assert F.FORMATS['zju_cs_zuzhi_names'][0]('<html><body>nothing</body></html>') == []
