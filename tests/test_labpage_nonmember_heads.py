"""Headings that look like member sections but are programme-committee or best-paper lists (Tsinghua 2026-11-11)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import labpage_audit as LA  # noqa: E402


def test_tpc_and_best_paper_heads_are_not_member_lists():
    for head in ('TPC member > Kuiper: Enterprise Cloud Plug-and-Play Network Management Platform', 'TPC Members', 'SPC member', 'PC member 2024',
                 'NLPCC 2020 (Best Student Paper)', 'Best Paper Award'):
        assert LA.NOT_MEMBER_HEAD.search(head), head


def test_real_member_heads_stay_members():
    for head in ('Ph.D. Students', 'Current Members', 'Alumni', 'Postdocs', 'Group Members', 'Master Students'):
        assert not LA.NOT_MEMBER_HEAD.search(head), head


def test_visitors_at_another_institution_and_collaborated_students_are_not_member_lists():
    """CMU round 10 (Pfeffer's 'My Visitors @ TUM'; Kilinc-Karzan's students she collaborated with)."""
    assert LA.nonmember_candidate('Philipp Singer', 'My Visitors @ TUM', 'cmu')
    assert not LA.nonmember_candidate('Ann Lee', 'Visitors @ Carnegie Mellon University', 'cmu')
    assert not LA.nonmember_candidate('Ann Lee', 'Visitors', 'cmu')
    assert LA.nonmember_candidate('Adams Wei Yu', 'I collaborate with the following PhD students', 'cmu')
    assert not LA.nonmember_candidate('Ann Lee', 'PhD students I advise', 'cmu')


def test_page_with_only_old_years_is_stale():
    """CMU round 10 (Brookes's students page: no footer, newest dated item 2008)."""
    old = 'Publications. Concurrency, 1984. Models, 1990. Semantics, 2008. Current students: Carsten Varming'
    assert LA.stale_footer_year(old, None) == 2008
    assert LA.stale_footer_year(old + ' Seminar 2019', None) is None
    assert LA.stale_footer_year('Students 2012', None) is None   # a single year is not enough
