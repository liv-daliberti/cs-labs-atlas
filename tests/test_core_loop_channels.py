"""Loop channel lists (schools/*.toml [collector].channels): core and core_bulk ride every full loop list (owner 2026-11-15, 'CORE is allowed
everywhere'; docs/DECISIONS.md), and every listed name is a real channel plugin."""
import tomllib
from pathlib import Path

import channels as CH

SCHOOLS = Path(__file__).resolve().parents[1] / 'schools'


def lists():
    for p in sorted(SCHOOLS.glob('*.toml')):
        if p.stem == 'TEMPLATE':
            continue
        yield p.stem, (tomllib.loads(p.read_text()).get('collector') or {}).get('channels') or []


def test_every_listed_channel_exists():
    for school, ch in lists():
        assert set(ch) <= set(CH.NAMES), (school, set(ch) - set(CH.NAMES))


def test_full_loop_lists_carry_core_after_s2():
    full = [(s, c) for s, c in lists() if 'proceedings' in c and 'europepmc' in c and 'figshare' in c]
    assert len(full) >= 15
    for school, ch in full:
        assert ch[ch.index('s2') + 1:ch.index('s2') + 3] == ['core', 'core_bulk'], school
