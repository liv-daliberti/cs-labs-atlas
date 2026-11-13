"""LP-STU-01 reader fix (NTU Cheng Yu, 2026-11-13): a members heading 'Ph.D. Students @NTU&CUHK' names the school by its abbreviation, which the
charter's full-name regex leaves out; the page must not be read as another institution's because a postdoc line says 'Ph.D. from Zhejiang University'."""
import labpage_audit as L

PAGE = ('Students Postdoc @NTU&CUHK Yafu Li (Ph.D. from Zhejiang University, starting from Fall 2025) '
        'Ph.D. Students @NTU&CUHK Tianle Li (Fall 2024-,BS,HKUST, MS,University of Waterloo)')


def test_abbreviation_after_at_names_the_school():
    assert L.school_abbreviation_at_marker('ntu', PAGE)
    assert L.school_abbreviation_at_marker('zju', 'Master Students @ZJU Ann Lee')


def test_bare_abbreviation_without_an_at_marker_does_not():
    assert not L.school_abbreviation_at_marker('ntu', 'Students NTU Ann Lee, Bo Wu')


def test_the_charters_excluded_name_keeps_the_page_out():
    assert not L.school_abbreviation_at_marker('ntu', PAGE + ' Visiting National Taiwan University')


def test_another_school_at_marker_is_not_this_school():
    assert not L.school_abbreviation_at_marker('ntu', 'Ph.D. Students @Tsinghua University Ann Lee')
