"""Round 1 at Georgia Tech: undated alumni of a PI who arrived inside the window are the previous institution's students."""
import labpage_audit as A


def test_moved_in_alumnus_rule():
    assert A.moved_in_alumnus(2020, None, False, True)          # '(Current: Faculty at Michigan)' on a 2020 arrival's page
    assert A.moved_in_alumnus(2020, None, True, False)           # an undated alumnus
    assert not A.moved_in_alumnus(2020, [2021, None], True, True)  # dated: the year decides
    assert not A.moved_in_alumnus(None, None, True, True)         # a PI whose first listing is the window floor (long at the school): the older-lab rule handles it
    assert not A.moved_in_alumnus(2020, None, False, False)       # a plain undated current member
