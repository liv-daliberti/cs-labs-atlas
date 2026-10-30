"""Rules learned onboarding Michigan (2026-10-30): gzip captures, strict names, alumni markers, span gaps, adviser phrases."""
import gzip, sys, zlib

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'listings' / 'scripts'))


def test_wb_body_gunzips_stored_captures():
    import wb
    page = b'<html><p>Chen, Peter M. Professor</p></html>'
    assert wb.body(zlib.compress(gzip.compress(page))) == page
    assert wb.body(zlib.compress(page)) == page


def test_strict_name_needs_the_spelled_out_given_name():
    import cs_related_school as C
    assert C.strict_name('Hun-Seok Kim', 'Hun Seok Kim')
    assert not C.strict_name('Hun-Seok Kim', 'Hyungjin Myra Kim')
    assert not C.strict_name('Minji Kim', 'Michelle M. Kim')
    assert C.strict_name('L. Jay Guo', 'Jay L. Guo')


def test_alumni_marker_in_page_text():
    pytest.importorskip('bs4')  # the lab-page tools run under the collector Python
    import labpage_students_school as L
    t = 'Advisees Ph.D. Students : Tsung-Wei Ke Note : ... Alumni Ph.D. Students Zhongqi Miao : Deep Learning Postdocs : Dong-Jin Kim'
    assert L.alumni_in_text(t, t.find('Ph.D. Students'), t.find('Tsung-Wei Ke')) is None
    assert L.alumni_in_text(t, t.rfind('Ph.D. Students'), t.find('Zhongqi Miao')) is not None
    assert L.alumni_in_text(t, t.rfind('Postdocs'), t.find('Dong-Jin Kim')) is not None
    c = t + ' Current Students Jane Roe'
    assert L.alumni_in_text(c, c.find('Current'), c.find('Jane Roe')) is None


def test_span_gaps_follow_professor_rank():
    import stage_gate as G
    song = dict(years_listed=[2020, 2024, 2025, 2026], ranks_by_year={'2020': ['research'], '2024': ['visiting'], '2025': ['ladder'], '2026': ['ladder']})
    assert G.span_gaps(song) == []
    corso = dict(years_listed=list(range(2016, 2027)), ranks_by_year={str(y): ['adjunct' if y == 2021 else 'ladder'] for y in range(2016, 2027)})
    assert G.span_gaps(corso) == []
    chen = dict(years_listed=[y for y in range(2016, 2027) if y != 2022], ranks_by_year={str(y): ['ladder'] for y in range(2016, 2027) if y != 2022})
    assert G.span_gaps(chen) == [2022]


def test_adviser_phrase_before_the_name():
    pytest.importorskip('bs4')
    import labpage_students_school as L
    assert L.ADVISED.search('PhD student at the University of Michigan, advised by Prof. ')
    assert L.ADVISED.search('under the supervision of ')
    assert L.ADVISED.search('My advisor is ')
    assert not L.ADVISED.search('I am working with ')


def test_ladder_title_core():
    import cs_related_school as C
    pages = [('UMSI', 'u', 's', '20260101', 'Libby Hemphill Associate Professor of Information, School of Information and Research Associate Professor, ICPSR Send Email')]
    ev = C.faculty_evidence(pages, ['Libby Hemphill'])
    assert ev and ev[0]['ladder']
    pages = [('UMSI', 'u', 's', '20260101', 'Mustafa Naseem Clinical Associate Professor of Information Send Email')]
    assert not C.faculty_evidence(pages, ['Mustafa Naseem'])[0]['ladder']
