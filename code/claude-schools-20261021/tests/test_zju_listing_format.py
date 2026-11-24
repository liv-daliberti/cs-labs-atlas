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


CARDS = """<div class="news_list list_tea"><article class="teacher-card"><a href="https://person.zju.edu.cn/bjj"><div class="teacher-avatar"><img alt="卜佳俊"></div></a>
<div class="teacher-info"><a href="https://person.zju.edu.cn/bjj" target="_blank"><h1 class="teacher-name">卜佳俊</h1></a><div class="teacher-badges"><a href="x"><span class="badge badge--primary">教授</span></a></div>
<div class="teacher-meta"><a class="teacher-email" href="mailto:[email removed]">[email removed]</a><span class="teacher-research">智能媒体计算</span></div></div></article>
<article class="teacher-card"><div class="teacher-info"><a href="https://person.zju.edu.cn/0002380"><h1 class="teacher-name">陈　刚</h1></a><div class="teacher-badges"><span class="badge">百人计划研究员</span></div></div></article></div>"""


def test_zju_cs_teacher_cards_name_rank_profile_no_contact():
    rows = F.FORMATS['zju_cs_teacher_cards'][0](CARDS)
    assert [(r['name_listed'], r['titles']) for r in rows] == [('卜佳俊', ['教授']), ('陈刚', ['百人计划研究员'])]
    assert rows[0]['profile'] == 'https://person.zju.edu.cn/bjj' and all('@' not in str(r) for r in rows)
    assert F.FORMATS['zju_cs_teacher_cards'][1].search(CARDS) and F.FORMATS['zju_cs_teacher_cards'][0]('<html></html>') == []


OLD = """<table><th colspan="2">人工智能研究所</th></tr><tr><td align="center" class="szdw"><div><a href="redir.php?catalog_id=22284&object_id=22759" target="_blank">蔡　铭</a></div><div><a href="redir.php?catalog_id=22284&object_id=22743" target="_blank">陈德人</a></div></td></tr></table>
<table><th colspan="2">计算机软件研究所</th></tr><tr><td class="szdw"><div><a href="redir.php?catalog_id=22285&object_id=688156" target="_blank">鲍凌峰</a></div></td></tr></table>"""


def test_zju_cs_old_jiaoshiml_names_by_institute_and_gb_decode():
    rows = F.FORMATS['zju_cs_old_jiaoshiml'][0](OLD)
    assert [(r['name_listed'], r['division']) for r in rows] == [('蔡铭', '人工智能研究所'), ('陈德人', '人工智能研究所'), ('鲍凌峰', '计算机软件研究所')]
    assert F.FORMATS['zju_cs_old_jiaoshiml'][1].search(OLD) and F.FORMATS['zju_cs_old_jiaoshiml'][0]('<html></html>') == []
    import wb
    gb = ('<meta http-equiv="Content-Type" content="text/html; charset=gb2312" />' + OLD).encode('gb18030')
    assert wb.text(gb) == '<meta http-equiv="Content-Type" content="text/html; charset=gb2312" />' + OLD
    assert wb.text('浙江大学'.encode()) == '浙江大学'


CAD = """<div class="zhuwenn"><table><tbody><tr><td><strong>姓名（职称）</strong></td><td><strong>研究方向或专业</strong></td></tr>
<tr><td><p>鲍虎军　教授</p></td><td>计算机图形学<br/>虚拟现实</td></tr>
<tr><td><p>潘云鹤　教授&nbsp;<br />　　　（院士）</p></td><td>人工智能</td></tr>
<tr><td><p>周 昆 教授</p></td><td>x</td></tr>
<tr><td><p>邵天甲 博士</p></td><td>y</td></tr></tbody></table></div>"""


def test_zju_cad_fixed_researchers_name_title_only():
    rows = F.FORMATS['zju_cad_fixed_researchers'][0](CAD)
    assert [(r['name_listed'], r['titles']) for r in rows] == [('鲍虎军', ['教授']), ('潘云鹤', ['教授']), ('周昆', ['教授']), ('邵天甲', ['博士'])]
    assert F.FORMATS['zju_cad_fixed_researchers'][1].search(CAD) and F.FORMATS['zju_cad_fixed_researchers'][0]('<html></html>') == []


CAD25 = """<h2 class="elementor-heading-title">院士</h2><div class="elementor-widget-text-editor"><p style="text-align: center;">潘云鹤</p></div>
<h2 class="elementor-heading-title">教授/长聘教授</h2><div class="elementor-widget-text-editor"><p><a href="http://kunzhou.net/"><span>周昆</span></a></p></div><div class="elementor-widget-text-editor"><p>|</p></div>
<div class="elementor-widget-text-editor"><p>陈为</p></div><h2 class="elementor-heading-title">百人计划研究员</h2><div class="elementor-widget-text-editor"><p>邵天甲</p></div>"""


def test_zju_cad_fixed_researchers_2025_rank_bands():
    rows = F.FORMATS['zju_cad_fixed_researchers_2025'][0](CAD25)
    assert [(r['name_listed'], r['titles']) for r in rows] == [('潘云鹤', ['院士']), ('周昆', ['教授/长聘教授']), ('陈为', ['教授/长聘教授']), ('邵天甲', ['百人计划研究员'])]
    assert rows[1]['quote_parts'] == ['周昆', '教授/长聘教授'] and rows[1]['profile'] == 'http://kunzhou.net/'
    assert F.FORMATS['zju_cad_fixed_researchers_2025'][1].search(CAD25) and F.FORMATS['zju_cad_fixed_researchers_2025'][0]('<html></html>') == []


CST = """<div class="wp_articlecontent"> <div id="wp_content_w15_0" class="paging_content"><table><tbody><tr><td><a href="https://person.zju.edu.cn/0001038" title="尹建伟"><span>尹建伟</span></a></td>
<td><a href="https://person.zju.edu.cn/0011057" title="伍赛"><span>伍　赛</span></a></td><td><a href="/x/page.htm"><span>新闻标题很长</span></a></td></tr></tbody></table></div></div>"""


def test_zju_cst_szdw_names_collapse_wide_space_keep_printed_quote():
    rows = F.FORMATS['zju_cst_szdw_names'][0](CST)
    assert [(r['name_listed'], r['quote_name']) for r in rows] == [('尹建伟', '尹建伟'), ('伍赛', '伍 赛')]
    assert F.FORMATS['zju_cst_szdw_names'][1].search(CST) and F.FORMATS['zju_cst_szdw_names'][0]('<html></html>') == []


ISEE = """<table><tbody><tr><td width="15%"><img src="/a_s.jpg" alt="蔡云龙" class="zp"><div>蔡云龙
 </div></td><td>副教授</td><td>信息与通信工程系</td><td>通信信号处理</td><td><p>邮箱：[email removed]</p></td></tr>
<tr><td><img src="/b_s.jpg" alt="蔡超" class="zp"><div>蔡超</div></td><td>未填写</td><td>院机关</td><td>综合办公室</td><td>x</td></tr></tbody></table>"""


def test_zju_isee_table_name_rank_division_no_contact():
    rows = F.FORMATS['zju_isee_table'][0](ISEE)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('蔡云龙', ['副教授'], '信息与通信工程系'), ('蔡超', [], '院机关')]
    assert all('@' not in str(r) for r in rows)
    assert F.FORMATS['zju_isee_table'][1].search(ISEE) and F.FORMATS['zju_isee_table'][0]('<html></html>') == []


EE = """<div class="teach-title">学院教职工</div><div class="teach-title">电机及其控制研究所</div><ul class="teach-list"><li><a class="teach-wrap" href="https://person.zju.edu.cn/xcl"><h3>夏长亮</h3></a></li>
<li><a class="teach-wrap" href="https://person.zju.edu.cn/a"><h3>黄 进</h3></a></li></ul><div class="teach-title">博士后</div><ul class="teach-list"><li><a class="teach-wrap" href="x"><h3>陈小元</h3></a></li></ul>"""


def test_zju_ee_teach_list_institutes_skip_postdocs():
    rows = F.FORMATS['zju_ee_teach_list'][0](EE)
    assert [(r['name_listed'], r['division']) for r in rows] == [('夏长亮', '电机及其控制研究所'), ('黄进', '电机及其控制研究所')]
    assert F.FORMATS['zju_ee_teach_list'][1].search(EE) and F.FORMATS['zju_ee_teach_list'][0]('<html></html>') == []


MATH = """<td align=center valign=middle height=27 style="font-size: 16px; font-weight: bold">数学研究所</td><table><tr><td><a href=teacher_intro.asp?userid=35 target=_blank>蔡天新</a></td>
<td><a href=teacher_intro.asp?userid=71 target=_blank>陈志国</a></td></tr></table><td style="font-weight: bold">应用数学研究所</td><a href=teacher_intro.asp?userid=9>王伟</a>"""


def test_zju_math_teachers_asp_names_by_institute():
    rows = F.FORMATS['zju_math_teachers_asp'][0](MATH)
    assert [(r['name_listed'], r['division']) for r in rows] == [('蔡天新', '数学研究所'), ('陈志国', '数学研究所'), ('王伟', '应用数学研究所')]
    assert F.FORMATS['zju_math_teachers_asp'][1].search(MATH) and F.FORMATS['zju_math_teachers_asp'][0]('<html></html>') == []


CSE = """<div class="teacher-box1"><h3 class="research-name">工业控制研究所</h3><ul class="teacher-list"><li class="teacher-item"><a href="/2022/0706/c72508a2660272/page.htm">柴利</a></li>
<li class="teacher-item"><a href="/x">程鹏</a></li></ul><h3 class="research-name">智能感知与检测研究所</h3><ul class="teacher-list"><li class="teacher-item"><a href="/y">曹云琦</a></li></ul>"""


def test_zju_cse_teacher_list_names_by_institute():
    rows = F.FORMATS['zju_cse_teacher_list'][0](CSE)
    assert [(r['name_listed'], r['division']) for r in rows] == [('柴利', '工业控制研究所'), ('程鹏', '工业控制研究所'), ('曹云琦', '智能感知与检测研究所')]
    assert F.FORMATS['zju_cse_teacher_list'][1].search(CSE) and F.FORMATS['zju_cse_teacher_list'][0]('<html></html>') == []


EE18 = """<div class="items"><div class="introduce"><h3>宋永华</h3><dd>电机工程学系</dd><dd>英国皇家工程院院士、教授、博士生导师</dd><dd><a href="/x">[查看详情]</a></dd></div></div>
<div class="items"><div class="introduce"><h3>Pierre-Daniel Pfister (福义涛)</h3><dd>电机工程学系</dd><dd>副教授</dd><dd><a href="/y">[查看详情]</a></dd></div></div>"""


def test_zju_ee_teach_list_2018_template_keeps_printed_title():
    rows = F.FORMATS['zju_ee_teach_list'][0](EE18)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [('宋永华', ['英国皇家工程院院士、教授、博士生导师'], '电机工程学系'), ('福义涛', ['副教授'], '电机工程学系')]
    assert F.FORMATS['zju_ee_teach_list'][1].search(EE18)


EN = """<div class="tearch_class">Institute of Industrial Design</div><ul class="wp_article_list"><li class="list_item i1"><div class="fields pr_fields"><span class='Article_Index'>1</span>
<span class='Article_Title'><a href='/_redirect?siteId=416&columnId=22160&articleId=1' target='_blank' title='Zheng Linfeng'>Zheng Linfeng</a></span></div></li>
<li class="list_item i2"><span class='Article_Index'>2</span><span class='Article_Title'><a href='/x' title='Zhang  Xusheng'>Zhang  Xusheng</a></span></li></ul>"""


def test_zju_cs_en_faculty_list_names_and_institute():
    rows = F.FORMATS['zju_cs_en_faculty_list'][0](EN)
    assert [r['name_listed'] for r in rows] == ['Zheng Linfeng', 'Zhang Xusheng']
    assert rows[0]['division'] == 'Institute of Industrial Design' and rows[0]['titles'] == []
    assert F.FORMATS['zju_cs_en_faculty_list'][1].search(EN) and F.FORMATS['zju_cs_en_faculty_list'][0]('<html></html>') == []


def test_zju_charter_english_directory_is_coverage_only_and_in_no_group():
    import pathlib
    import tomllib
    import school_config as S
    cfg = tomllib.loads((pathlib.Path(__file__).resolve().parents[1] / 'schools' / 'zju.toml').read_text())
    dept = next(d for d in cfg['departments'] if d['code'] == 'CS_MAIN')
    assert S.listing_group_errors(dept) == []
    en = [s for s in dept['listings'] if s['slot'].startswith('CS_MAIN EN ')]
    assert len(en) == 6 and all(s.get('coverage_only') and s['format'] == 'zju_cs_en_faculty_list' for s in en)
    assert not any('English' in g['name'] for g in dept['listing_groups'])  # no group may let a partial source close gate 1
