"""SJTU School of Computer Science English faculty list format (archived cs.sjtu.edu.cn/en/Faculty.aspx)."""
import listing_formats as F

PAGE = """<div class="lh250"><p class="tc f14 fb red">Institute of Theoretical Computer Science</p>
<div class="Faculty"><h3>Professor:</h3><ul>
<!--<li><a href="PeopleDetail.aspx?id=175" class="red">Deng Xiaotie</a></li>-->
<li><a href="PeopleDetail.aspx?id=171" class="red">Fu Yuxi</a></li><li><a href="PeopleDetail.aspx?id=129" class="red">Zhu Qili</a></li><div class="cb"></div></ul>
<!--<h3>Lecturer:</h3><ul><li><a href="PeopleDetail.aspx?id=269" class="red">Long Huan</a></li></ul>-->
<h3>Assistant Professor:</h3><ul><li><a href="PeopleDetail.aspx?id=305" class="red">Dominik</a></li></ul></div>
<p class="tc f14 fb red">Institute of Parallel and Distributed Computing</p>
<div class="Faculty"><h3>Professor:</h3><ul><li><a href="PeopleDetail.aspx?id=1" class="red">Wang Xinbing (Joint)</a></li></ul></div></div>"""


def test_sjtu_cs_en_institutes_parse_and_register():
    rows = F.FORMATS['sjtu_cs_en_institutes'][0](PAGE)
    assert [r['name_listed'] for r in rows] == ['Fu Yuxi', 'Zhu Qili', 'Dominik', 'Wang Xinbing']
    assert rows[0]['titles'] == ['Professor'] and rows[0]['division'] == 'Institute of Theoretical Computer Science'
    assert rows[2]['titles'] == ['Assistant Professor']
    assert rows[3]['titles'] == ['Professor', 'Joint'] and rows[3]['division'].endswith('Distributed Computing')
    assert F.FORMATS['sjtu_cs_en_institutes'][1].search(PAGE)


def test_commented_out_people_are_not_listed():
    names = [r['name_listed'] for r in F.FORMATS['sjtu_cs_en_institutes'][0](PAGE)]
    assert 'Deng Xiaotie' not in names and 'Long Huan' not in names


ZH_PAGE = """<div class="lh250"><p class="tc f14 fb red">高可靠软件与理论研究所</p>
<div class="Faculty"><h3>教授：</h3><ul><li><a href="PeopleDetail.aspx?id=437" class="red">陈 翌佳</a></li></ul>
<h3>副教授：</h3><ul><li><a href="PeopleDetail.aspx?id=304" class="red">Dominik</a></li></ul></div></div>"""


def test_chinese_list_reads_with_the_english_format():
    rows = F.FORMATS['sjtu_cs_en_institutes'][0](ZH_PAGE)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [
        ('陈 翌佳', ['教授'], '高可靠软件与理论研究所'), ('Dominik', ['副教授'], '高可靠软件与理论研究所')]


AJAX = ('{"tab_html":"<li>全部</li>","content":"<div class=\\"rc-item\\"><div class=\\"tit\\"><div class=\\"name\\">机器智能研究所</div></div>'
        '<div class=\\"dt\\"><p>所　长：<a href=\\"https://www.cs.sjtu.edu.cn/jiaoshiml/yukai.html\\">俞 凯</a></p></div>'
        '<div class=\\"name-list\\"><span><a href=\\"https://www.cs.sjtu.edu.cn/jiaoshiml/chenlu.html\\">陈 露</a></span>'
        '<span><a href=\\"https://www.cs.sjtu.edu.cn/jiaoshiml/shenliping.html\\">申丽萍</a></span></div></div>"}')


def test_ajax_teacher_feed_lists_leaders_and_teachers_names_only():
    rows = F.FORMATS['sjtu_cs_ajax_teachers'][0](AJAX)
    assert [(r['name_listed'], r['titles'], r['division']) for r in rows] == [
        ('俞 凯', [], '机器智能研究所'), ('陈 露', [], '机器智能研究所'), ('申丽萍', [], '机器智能研究所')]
    assert F.FORMATS['sjtu_cs_ajax_teachers'][1].search(AJAX)
    assert F.FORMATS['sjtu_cs_ajax_teachers'][0]('<html>not json</html>') == []


def test_ajax_feed_text_blocks_contain_every_listed_name():
    import importlib.util
    import pathlib
    path = pathlib.Path(__file__).resolve().parents[1] / 'listings' / 'scripts' / 'json_people.py'
    spec = importlib.util.spec_from_file_location('json_people_under_test', path)
    jp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jp)
    flat = ' '.join(t for _, t in jp.blocks(AJAX.encode('utf-8')))
    assert all(r['name_listed'] in flat for r in F.FORMATS['sjtu_cs_ajax_teachers'][0](AJAX)) and '机器智能研究所' in flat
