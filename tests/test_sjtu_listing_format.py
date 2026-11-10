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
    assert [r['name_listed'] for r in rows] == ['Fu, Yuxi', 'Zhu, Qili', 'Dominik', 'Wang, Xinbing']
    assert rows[0]['titles'] == ['Professor'] and rows[0]['division'] == 'Institute of Theoretical Computer Science'
    assert rows[2]['titles'] == ['Assistant Professor']
    assert rows[3]['titles'] == ['Professor', 'Joint'] and rows[3]['division'].endswith('Distributed Computing')
    assert F.FORMATS['sjtu_cs_en_institutes'][1].search(PAGE)


def test_commented_out_people_are_not_listed():
    names = [r['name_listed'] for r in F.FORMATS['sjtu_cs_en_institutes'][0](PAGE)]
    assert 'Deng, Xiaotie' not in names and 'Long, Huan' not in names
