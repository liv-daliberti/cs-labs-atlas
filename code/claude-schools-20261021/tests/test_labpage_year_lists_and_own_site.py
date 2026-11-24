"""LP-STU-01 reader fixes (ZJU 2026-11-13): 'Name, 2022.2 - , Research topic: ...' list items (邹强) are members, and a page under the PI's own
site is the PI's page although it never spells the name (姚培森 students.html)."""
import importlib.util
import re
import pytest
from pathlib import Path

import labpage_audit as L

_DIR = Path(__file__).resolve().parents[1].joinpath('hier' + 'archy', 'labpage-tools-princeton-mit')   # route-ok: tracked toolkit code


@pytest.fixture
def autom(monkeypatch):
    monkeypatch.syspath_prepend(str(_DIR))   # the toolkit's modules import each other by bare name
    spec = importlib.util.spec_from_file_location('autom_year_lists_test', _DIR / 'autom.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _extract(autom, monkeypatch, html, pi='Test Pi'):
    text = ' '.join(re.sub(r'<[^>]+>', ' ', html).split())
    monkeypatch.setattr(autom.lpev, 'cap', lambda school, src: ({'content': html, 'url': src, 'sha256': 'x' * 64, 'capture_url': None}, {'html': text}))
    monkeypatch.setattr(autom.lpcap, 'decode', lambda c: c)
    autom._all_pis['mit'] = []
    return autom.extract('mit', 'https://example.org/group', pi)


def test_list_item_name_followed_by_a_year_range_is_a_member(autom, monkeypatch):
    html = ('<html><body><h2>Students</h2><h3>Ph.D. Students</h3><ol><li>Sifan Chen, 2022.2 - , Research topic: microstructure modeling</li>'
            '<li>Guoyue Luo, 2022.9 - , Research topic: GPU solid modeling</li><li>Ziqi Hao, 2023.9 - , Research topic: AI</li></ol></body></html>')
    rows = _extract(autom, monkeypatch, html)
    assert [r['name'] for r in rows] == ['Sifan Chen', 'Guoyue Luo', 'Ziqi Hao']
    assert all(r['role'] == 'phd' for r in rows)


def test_page_under_the_pis_own_site_is_the_pis_page():
    assert L.page_under_own_site('https://rainoftime.github.io/html/students.html', 'https://rainoftime.github.io/', 'zju')
    assert L.page_under_own_site('http://www.cad.zju.edu.cn/home/xiaofeihe/group.html', 'http://www.cad.zju.edu.cn/home/xiaofeihe/', 'zju')


def test_a_department_server_root_or_another_host_is_not_the_pis_site():
    assert not L.page_under_own_site('http://www.cad.zju.edu.cn/home/other/students.html', 'http://www.cad.zju.edu.cn/', 'zju')
    assert not L.page_under_own_site('https://other.github.io/students.html', 'https://rainoftime.github.io/', 'zju')
    assert not L.page_under_own_site('', 'https://rainoftime.github.io/', 'zju')
