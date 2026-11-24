"""A hand-rejected or held lab-page row is never proposed again; a role withheld by hand stays withheld (Harvard 2026-11-10)."""
import labpage_audit as L


def test_recorded_hand_review_reads_every_hand_review_list():
    prev = {'hand_review_20261109': [{'pi': 'A', 'name': 'X', 'decision': 'rejected', 'reason': 'r'}],
            'hand_review_20261110': [{'pi': 'A', 'name': 'Y', 'decision': 'role_withheld'}, {'pi': 'B', 'name': 'Z', 'decision': 'held'},
                                     {'pi': 'B', 'name': 'W', 'decision': 'corrected'}],
            'students': [{'pi': 'A', 'name': 'Q'}]}
    assert L.recorded_hand_review(prev) == {('A', 'X'): 'rejected', ('A', 'Y'): 'role_withheld', ('B', 'Z'): 'held'}
    assert L.recorded_hand_review(None) == {}


def test_a_rejected_or_held_row_is_dropped_and_a_withheld_role_kept_null():
    rows = [{'pi': 'A', 'name': 'X', 'role': 'phd'}, {'pi': 'A', 'name': 'Y', 'role': 'phd'}, {'pi': 'B', 'name': 'Z', 'role': 'postdoc'}, {'pi': 'B', 'name': 'K', 'role': 'phd'}]
    out = L.apply_hand_review(rows, {('A', 'X'): 'rejected', ('A', 'Y'): 'role_withheld', ('B', 'Z'): 'held'})
    assert [(r['pi'], r['name']) for r in out] == [('A', 'Y'), ('B', 'K')]
    assert out[0]['role'] is None and out[0]['role_basis'] == 'withheld_hand_check_20261110' and out[1]['role'] == 'phd'
