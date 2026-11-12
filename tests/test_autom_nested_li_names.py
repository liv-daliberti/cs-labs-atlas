"""autom.markers: a member whose name is the leading text of an <li> with a nested attribute list (ZJU lynnlilu.github.io/students)."""
import importlib.util
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1].joinpath('hier' + 'archy', 'labpage-tools-princeton-mit')   # route-ok: tracked toolkit code
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location('autom_nested_li_test', _DIR / 'autom.py')   # this checkout's reader, whatever autom a test imported earlier
autom = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(autom)

HTML = ('<html><body><div class="archive"><h1>Ph.D. Students</h1><ul>'
        '<li>Junhao Wang (王俊皓)<ul><li>Duration: 2021-present</li><li>Research Interests: Biometrics</li></ul></li>'
        '<li>Yihe Zhang (章怿贺)<ul><li>Duration: 2023-present</li></ul></li></ul>'
        '<h1>Master Students</h1><ul><li>Xiaodi Zhao (赵小迪)<ul><li>Duration: 2023-present</li></ul></li></ul></div></body></html>')


def test_nested_list_member_names_are_markers(monkeypatch):
    text = ' '.join(__import__('re').sub(r'<[^>]+>', ' ', HTML).split())
    monkeypatch.setattr(autom.lpev, 'cap', lambda school, src: ({'content': HTML, 'url': src}, {'html': text}))
    monkeypatch.setattr(autom.lpcap, 'decode', lambda c: c)
    _r, _t, mk = autom.markers('zju', 'https://example.org/students/')
    assert [m[3] for m in mk if m[2] == 'name'] == ['Junhao Wang (王俊皓)', 'Yihe Zhang (章怿贺)', 'Xiaodi Zhao (赵小迪)']
    assert [m[3] for m in mk if m[2] == 'head'] == ['Ph.D. Students', 'Master Students']


def test_a_section_label_in_a_nested_li_is_not_a_name(monkeypatch):
    html = '<html><body><ul><li>Research Interests<ul><li>Vision</li></ul></li></ul></body></html>'
    monkeypatch.setattr(autom.lpev, 'cap', lambda school, src: ({'content': html, 'url': src}, {'html': 'Research Interests Vision'}))
    monkeypatch.setattr(autom.lpcap, 'decode', lambda c: c)
    _r, _t, mk = autom.markers('zju', 'https://example.org/')
    assert not [m for m in mk if m[2] == 'name']


def test_cohort_year_item_splits_a_comma_list_of_names():
    assert autom.cohort_year_item('2026: Junjie Cheng, Bingze Li, Wenxin Ruan') == ('2026', ['Junjie Cheng', 'Bingze Li', 'Wenxin Ruan'])
    got = autom.cohort_year_item('2024: Yuqiao Gu (Ph.D. student, CJC 1st Author, 1 * Patent), Yi Jiang (ACNS 3rd Author)')
    assert got == ('2024', ['Yuqiao Gu', 'Yi Jiang'])
    assert autom.cohort_year_item('2023: Jiahui Wang -> Tencent, Mingxiang Shi -> CICO') == ('2023', ['Jiahui Wang', 'Mingxiang Shi'])
    assert autom.cohort_year_item('2023: Deep Learning for Security: a survey of methods') is None   # a publication title is not a name list
    assert autom.cohort_year_item('Junjie Cheng, Bingze Li') is None


def test_cohort_year_li_emits_year_head_and_names(monkeypatch):
    html = '<html><body><h1>Students</h1><ul><li><strong>2026</strong>: Junjie Cheng, Bingze Li</li></ul></body></html>'
    monkeypatch.setattr(autom.lpev, 'cap', lambda school, src: ({'content': html, 'url': src}, {'html': 'Students 2026: Junjie Cheng, Bingze Li'}))
    monkeypatch.setattr(autom.lpcap, 'decode', lambda c: c)
    _r, _t, mk = autom.markers('zju', 'https://example.org/')
    assert [(m[2], m[3]) for m in mk] == [('head', 'Students'), ('head', '2026'), ('name', 'Junjie Cheng'), ('name', 'Bingze Li')]
