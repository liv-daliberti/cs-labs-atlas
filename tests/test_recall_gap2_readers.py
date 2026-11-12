"""Recall-gap repairs (2026-11-12): 'Surname, Given' member tables (Berkeley Tomizuka), an <h3>PhD</h3> after a co-mentor's link (MIT Podimata), a member's own link in the section
chain (Princeton Verma), 'EECS PhD student' under a heading that names the PI (Berkeley Sojoudi), a degree line read as a location (Princeton Houck)."""
import importlib.util
import re
import sys
from pathlib import Path

import labpage_audit as L

_DIR = Path(__file__).resolve().parents[1].joinpath('hier' + 'archy', 'labpage-tools-princeton-mit')   # route-ok: tracked toolkit code
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location('autom_recall_gap2_test', _DIR / 'autom.py')
autom = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(autom)


def _extract(monkeypatch, html, pi='Test Pi'):
    text = ' '.join(re.sub(r'<[^>]+>', ' ', html).split())
    monkeypatch.setattr(autom.lpev, 'cap', lambda school, src: ({'content': html, 'url': src, 'sha256': 'x' * 64, 'capture_url': None}, {'html': text}))
    monkeypatch.setattr(autom.lpcap, 'decode', lambda c: c)
    autom._all_pis['mit'] = []
    return autom.extract('mit', 'https://example.org/people', pi)


def test_surname_given_table_is_inverted(monkeypatch):
    html = ('<html><body><h1>PhD Students</h1><table>'
            '<tr><td>Qian, Qiyang</td><td>Robotics</td></tr><tr><td>Kobashi, Keita</td><td>Robotics</td></tr>'
            '<tr><td>Viljoen, John</td><td>Robotics</td></tr><tr><td>Zhao, Shuqi</td><td>Robotics</td></tr></table></body></html>')
    rows = _extract(monkeypatch, html)
    assert [r['name'] for r in rows] == ['Qiyang Qian', 'Keita Kobashi', 'John Viljoen', 'Shuqi Zhao']
    assert all(r['role'] == 'phd' for r in rows)


def test_a_single_comma_name_on_an_ordinary_page_is_kept_as_written(monkeypatch):
    html = '<html><body><h1>Students</h1><ul><li>Ben Silverman, Tracer</li><li>Ann Lee</li><li>Bo Wu</li></ul></body></html>'
    rows = _extract(monkeypatch, html)
    assert rows[0]['name'] == 'Ben Silverman'


def test_bare_role_h3_after_a_comentor_link_is_a_section(monkeypatch):
    html = ('<html><body><h2>Current Students</h2><h3>Postdoc</h3><div><div class="person-name"><a href="/ce">Ce Li</a></div>'
            '<div>Starting Fall 2026 co-mentored with <a href="/o">Asu Ozdaglar</a></div></div>'
            '<h3>PhD</h3><div><div class="person-name"><a href="/e">Valia Efthymiou</a></div><div>MIT ORC, 2024-present</div></div></body></html>')
    rows = {r['name']: r for r in _extract(monkeypatch, html, 'Chara Podimata')}
    assert rows['Valia Efthymiou']['role'] == 'phd'


def test_a_card_role_label_after_the_name_is_still_a_descriptor(monkeypatch):
    html = '<html><body><h2>People</h2><h3>Ann Lee</h3><h4>PhD Student</h4><h3>Bo Wu</h3><h4>PhD Student</h4></body></html>'
    rows = _extract(monkeypatch, html)
    assert [r['role'] for r in rows] == ['phd', 'phd']


def test_own_link_segments_do_not_hide_the_current_heading():
    x = {'head': 'Current Graduate Students > https://scholar.princeton.edu/hongyangjia/', 'desc': 'I received my B.E.'}
    assert L.current_marker(x)
    assert L.current_marker({'head': 'Current Graduate Students > Website Google Scholar', 'desc': ''})
    assert not L.current_marker({'head': 'Graduate Students > https://scholar.princeton.edu/x', 'desc': ''})
    assert not L.current_marker({'head': 'Current and Former Students > https://x.org/a', 'desc': ''})


def test_degree_line_is_not_a_location():
    assert not L.other_institution_entry('Ph.D Physics, University of Colorado Boulder (2024) B.S.', '', 'princeton')
    assert not L.other_institution_entry('B.S. Physics, University of Notre Dame', '', 'princeton')
    assert L.other_institution_entry('M.S. student, ECE@Rice University, Sept. 2017 - Sept. 2019', '', 'gatech')
    assert L.other_institution_entry('PhD Student, University of Toronto', '', 'princeton')


def test_own_student_role_exception_for_faculty_heading():
    assert L.OWN_STUDENT_ROLE_RX.search('EECS PhD student B.S.: University of Pittsburgh')
    assert L.OWN_STUDENT_ROLE_RX.search('ME PhD student')
    assert not L.OWN_STUDENT_ROLE_RX.search('Professor of EE, PhD Stanford')
