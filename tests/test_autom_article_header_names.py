"""autom.markers: a <header> is navigation only outside articles; a Genesis people grid (`entry-header` around each name, the page inside an
unclosed `site-header`) keeps its members (Berkeley edg.berkeley.edu/people)."""
import importlib.util
import re
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1].joinpath('hier' + 'archy', 'labpage-tools-princeton-mit')   # route-ok: tracked toolkit code
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location('autom_article_header_test', _DIR / 'autom.py')
autom = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(autom)

GRID = ('<html><body><header class="site-header"><nav class="nav-primary"><a>Research</a></nav><main><div class="wrap"><h2>Doctoral Students</h2>'
        '<article class="people"><header class="entry-header"><h3 class="entry-title"><a>Jadesola Aderibigbe</a></h3></header></article>'
        + ''.join(f'<article class="people"><header class="entry-header"><h3 class="entry-title"><a>{n}</a></h3></header></article>'
                  for n in ('Ben Davis', 'Gia Jeong', 'Deaho Moon', 'Isabel Morales', 'Nimran Shergill')) +
        '</div></main></header></body></html>')


def _markers(monkeypatch, html):
    text = ' '.join(re.sub(r'<[^>]+>', ' ', html).split())
    monkeypatch.setattr(autom.lpev, 'cap', lambda school, src: ({'content': html, 'url': src}, {'html': text}))
    monkeypatch.setattr(autom.lpcap, 'decode', lambda c: c)
    return autom.markers('berkeley', 'https://example.org/people')[2]


def test_entry_header_names_inside_a_header_wrapped_main_are_members(monkeypatch):
    mk = _markers(monkeypatch, GRID)
    assert [m[3] for m in mk if m[2] == 'name'] == ['Jadesola Aderibigbe', 'Ben Davis', 'Gia Jeong', 'Deaho Moon', 'Isabel Morales', 'Nimran Shergill']
    assert [m[3] for m in mk if m[2] == 'head'] == ['Doctoral Students']


def test_a_plain_site_header_stays_navigation(monkeypatch):
    html = '<html><body><header class="site-header"><h3>Hannah Stuart</h3></header><h2>Students</h2><ul><li>Ann Lee</li></ul></body></html>'
    mk = _markers(monkeypatch, html)
    assert [m[3] for m in mk if m[2] == 'name'] == ['Ann Lee']


def test_a_long_bare_header_around_the_roster_keeps_its_members(monkeypatch):
    people = ''.join(f'<div class="person-row"><h3><a>{n}</a></h3><p>PhD student in the lab working on topic number {i}</p></div>'
                     for i, n in enumerate(('Ann Marie Lee', 'Bo Wen Zhang', 'Carlos Ruiz Diaz', 'Dana Whitfield', 'Eli Moskowitz', 'Fatima Al Sayed', 'Greta Lindqvist', 'Hiro Tanabe')))
    html = f'<html><body><nav id="mainNav"><a>Research</a></nav><header><div><h1>Students</h1>{people}{"<p>filler text </p>" * 150}</div></header></body></html>'
    mk = _markers(monkeypatch, html)
    assert [m[3] for m in mk if m[2] == 'name'][:3] == ['Ann Marie Lee', 'Bo Wen Zhang', 'Carlos Ruiz Diaz']
