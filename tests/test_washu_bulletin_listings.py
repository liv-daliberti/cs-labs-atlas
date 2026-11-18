"""WashU Bulletin faculty sections -> listing entries (deep dive 2026-11-09)."""
import washu_bulletin_listings as WB


def test_heading_rank():
    assert WB.heading_rank('Associate Professors')[0] == 'ladder'
    assert WB.heading_rank('Professors Emeriti')[0] == 'emeritus'
    assert WB.heading_rank('Senior Lecturers')[0] == 'lecturer'
    assert WB.heading_rank('Professors of Practice')[0] == 'teaching'
    assert WB.heading_rank('Senior Professors')[0] == 'other'
    assert WB.heading_rank('Chair')[0] == 'chair'


def test_departments_cover_five_units():
    assert set(WB.DEPARTMENTS.values()) == {'CSE', 'ESE', 'BME', 'MEMS', 'EECE'}
