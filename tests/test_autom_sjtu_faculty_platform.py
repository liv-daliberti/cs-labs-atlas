"""SJTU faculty-homepage platform (faculty.sjtu.edu.cn .../xsxx/...): 'Student Information' lists of lone Han names, one link per student, under
博士研究生 / 硕士研究生 and 在校(n人) / 毕业(n人). Two layouts seen on the live platform (synthetic names, same markup)."""
import importlib.util
import re
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1].joinpath('hier' + 'archy', 'labpage-tools-princeton-mit')   # route-ok: tracked toolkit code
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location('autom_sjtu_platform_test', _DIR / 'autom.py')
autom = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(autom)

HEAD = '<html><body><div class="nav"><ul><li>首页</li><li>科学研究</li></ul></div>'
FOOT = '<div>沪ICP备05052060 版权所有©上海交通大学</div></body></html>'
LAYOUT_H2 = (HEAD + '<div class="listbox"><div><h2>博士研究生</h2></div><div><h2>在校(<span>3</span>人)</h2><div>'
             '<a href="/x/1">赵一丁</a> <a href="/x/2">钱二虎</a> <a href="/x/3">贠三木</a></div></div>'
             '<div><h2>毕业(<span>2</span>人)</h2><div><a href="/x/4">孙四海</a> <a href="/x/5">李五岳</a></div></div>'
             '<div><h2>硕士研究生</h2></div><div><h2>在校(<span>2</span>人)</h2><div><a href="/x/6">周六安</a> <a href="/x/7">吴七郎</a></div></div></div>' + FOOT)
LAYOUT_DIV = (HEAD + '<div class="ixsxx"><div class="ixsxx_bk"><div class="ixsxx_fl2"><h3>博士研究生</h3></div><div class="ixsxx_xh">'
              '<div class="ixsxx_xl1">在校（<span>2</span>）</div><div class="ixsxx_amelist"><a href="/x/1">赵一丁</a> <a href="/x/2">钱二虎</a></div></div>'
              '<div class="ixsxx_xh"><div class="ixsxx_xl1">毕业（<span>2</span>）</div><div class="ixsxx_amelist"><a href="/x/4">孙四海</a> <a href="/x/8">郑八斗</a> <a href="/x/5">Khoua Pholsena</a></div></div></div>'
              '<div class="ixsxx_bk"><div class="ixsxx_fl1"><h3>硕士研究生</h3></div><div class="ixsxx_xh"><div class="ixsxx_xl1">在校（<span>2</span>）</div>'
              '<div class="ixsxx_amelist"><a href="/x/6">周六安</a> <a href="/x/7">吴七郎</a></div></div></div></div>' + FOOT)


def rows_of(monkeypatch, html):
    text = ' '.join(re.sub(r'<[^>]+>', ' ', re.sub(r'(?is)<(script|style).*?</\1>', '', html)).split())
    monkeypatch.setattr(autom.lpev, 'cap', lambda school, src: ({'content': html, 'url': src, 'sha256': 'x'}, {'html': text}))
    monkeypatch.setattr(autom.lpcap, 'decode', lambda c: c)
    autom._all_pis['sjtu'] = []
    return autom.extract('sjtu', 'https://faculty.sjtu.edu.cn/x/zh_CN/xsxx/1/list/index.htm', '某教授', ())


def test_h2_layout_current_and_graduated_lists(monkeypatch):
    by = {r['name']: r for r in rows_of(monkeypatch, LAYOUT_H2) if r['name'] in {'赵一丁', '钱二虎', '贠三木', '孙四海', '李五岳', '周六安', '吴七郎'}}
    assert set(by) == {'赵一丁', '钱二虎', '贠三木', '孙四海', '李五岳', '周六安', '吴七郎'}
    assert [by[n]['role'] for n in ('赵一丁', '周六安')] == ['phd', 'masters']
    assert not by['赵一丁']['alumni'] and not by['吴七郎']['alumni'] and by['孙四海']['alumni'] and by['李五岳']['alumni']


def test_div_layout_roles_survive_the_wrapper_and_the_last_name_loses_the_footer(monkeypatch):
    rows = {r['name']: r for r in rows_of(monkeypatch, LAYOUT_DIV)}
    assert rows['钱二虎']['role'] == 'phd' and rows['周六安']['role'] == 'masters'   # the masters heading is not eaten as the previous name's descriptor
    assert 'ICP' not in rows['吴七郎']['desc'] and '版权' not in rows['吴七郎']['desc']
    assert rows['Khoua Pholsena']['alumni'] and rows['郑八斗']['alumni']   # a Latin name inside a Han roster is a member


def test_navigation_words_are_not_a_roster(monkeypatch):
    rows = rows_of(monkeypatch, '<html><body><div><a href="/a">首页</a> <a href="/b">新闻</a> <a href="/c">联系</a></div></body></html>')
    assert not {r['name'] for r in rows} & {'首页', '新闻', '联系'}


def test_han_role_and_alumni_words():
    assert autom._role('博士研究生')[0] == 'phd' and autom._role('硕士研究生')[0] == 'masters'
    assert autom._role('博士后')[0] == 'postdoc' and autom._role('本科生')[0] == 'undergraduate'
    assert autom.ALUMNI_RX.search('毕业( 3 人)') and not autom.ALUMNI_RX.search('学历： 博士研究生毕业')
    assert autom.HEADWORD.search('在校( 6 人)')


def test_plausible_lone_han_name_under_student_heading():
    import importlib
    la = importlib.import_module('labpage_audit')
    assert la.plausible_under_student_heading('贠三木') and not la.plausible_under_student_heading('研究领域')
