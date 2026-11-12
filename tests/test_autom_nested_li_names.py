"""autom.markers: a member whose name is the leading text of an <li> with a nested attribute list (ZJU lynnlilu.github.io/students)."""
import sys

import labpage_audit as A  # noqa: E402

sys.path.insert(0, str(A.H / A.PM))
import autom  # noqa: E402

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
