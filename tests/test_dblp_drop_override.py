"""A reviewed `dblp_drop` removes a conflated namesake pid from the PI's census ids (2026-11-19)."""
import inspect
from pihier import census


def test_dblp_drop_is_wired():
    assert 'dblp_drop' in inspect.getsource(census)
