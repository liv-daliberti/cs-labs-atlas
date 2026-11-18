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


ONBOARDING_STANDARD = 'purdue hkust ntu utaustin cambridge hit pku whu cuhk'.split()


def test_onboarding_charters_carry_the_standard_download_channels():
    """2026-11-18 (owner): the Purdue list (bbd04047) is the standard for onboarding charters: CORE, Europe PMC and PMC beside OpenAlex, S2 and the lab
    pages, and no Wayback channel. SEU keeps its longer list and gains core and core_bulk after s2."""
    have = dict(lists())
    for school in ONBOARDING_STANDARD:
        assert have[school] == ['oa_arxiv', 'openalex', 's2', 'core', 'core_bulk', 'europepmc', 'pmc', 'labpages'], school
    for longer in ('seu', 'ustc'):
        ch = have[longer]
        assert ch[ch.index('s2') + 1:ch.index('s2') + 3] == ['core', 'core_bulk'], longer
