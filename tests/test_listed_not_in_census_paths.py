"""Georgia Tech friction 15: listed_not_in_census read <work>/hierarchy/<school>/openalex-sweep.sqlite, which does not exist in the raw/reviewed/derived layout."""
from pathlib import Path


def test_the_sweep_path_comes_from_atlas_paths():
    src = (Path(__file__).resolve().parents[1] / 'tools' / 'listed_not_in_census.py').read_text()
    assert '{HERE}/hierarchy/' not in src and "P.data(\"openalex-sweep.sqlite\", school)" in src
