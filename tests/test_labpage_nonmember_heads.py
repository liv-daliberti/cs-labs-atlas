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
