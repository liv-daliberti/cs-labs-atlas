"""School-local rank patterns must recognize the source titles they describe."""
import tomllib
from pathlib import Path

import pytest

from listing_rows import rank_of


@pytest.mark.parametrize(("school", "title", "expected"), [
    ("utaustin", "Associate Professor of Instruction", "teaching"),
    ("utaustin", "Assistant Professor of Instruction", "teaching"),
    ("utaustin", "Professor of Instruction", "teaching"),
    ("utaustin", "Professor of Practice", "adjunct"),
    ("utaustin", "Associate Professor", "ladder"),
    ("utaustin", "Professor Emeritus", "emeritus"),
    ("purdue", "Affiliate Assistant Professor", "adjunct"),
    ("purdue", "Affiliate Associate Professor", "adjunct"),
    ("purdue", "Affiliate Professor", "adjunct"),
    ("purdue", "Assistant Professor", "ladder"),
])
def test_local_rank_words_match_actual_titles(school, title, expected):
    path = Path(__file__).resolve().parents[1] / "schools" / f"{school}.toml"
    config = tomllib.loads(path.read_text())
    assert rank_of([title], config["census"]["rank_words"]) == expected
