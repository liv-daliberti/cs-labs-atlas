"""Georgia Tech friction 15: listed_not_in_census read <work>/hierarchy/<school>/openalex-sweep.sqlite, which does not exist in the raw/reviewed/derived layout."""
from pathlib import Path


def test_the_sweep_path_comes_from_atlas_paths():
    src = (Path(__file__).resolve().parents[1] / 'tools' / 'listed_not_in_census.py').read_text()
    assert '{HERE}/hierarchy/' not in src and "P.data(\"openalex-sweep.sqlite\", school)" in src


def test_it_imports_the_listings_scripts_of_its_own_checkout():
    """P.WORK is the main checkout: a worktree's test run then imported the main checkout's older plan_fetch/wb (Georgia Tech friction 17)."""
    src = (Path(__file__).resolve().parents[1] / 'tools' / 'listed_not_in_census.py').read_text()
    assert 'HERE' not in src and "parents[1] / 'listings/scripts'" in src


def test_school_web_imports_its_own_checkouts_wb():
    src = (Path(__file__).resolve().parents[1] / 'tools' / 'school_web.py').read_text()
    line = next(l for l in src.splitlines() if l.startswith('sys.' + 'path.insert') and 'listings' in l)
    assert 'P.LISTINGS' not in line and 'parents[1]' in line
