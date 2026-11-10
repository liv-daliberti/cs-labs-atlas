"""2026-11-10 owner decision: discovery channels back on for every loop; wayback_acm off; OpenAlex spend stops at 4,000 credits left."""
import tomllib
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
LOOP_SCHOOLS = 'harvard jhu oxford uchicago washu cmu mit stanford berkeley princeton epfl gatech michigan'.split()
NEED = {'oa_arxiv', 'openalex', 'proceedings', 'arxiv_title', 'dblp_ee', 's2', 'europepmc', 'pmc', 'figshare', 'labpages', 'pihomes'}


def test_every_loop_charter_runs_discovery_without_wayback_or_core():
    for s in LOOP_SCHOOLS:
        ch = tomllib.loads((CODE / 'schools' / f'{s}.toml').read_text())['collector']['channels']
        assert NEED <= set(ch), s
        assert 'wayback_acm' not in ch and not any(c.startswith('core') for c in ch), s


def test_school_collector_reads_the_charter_not_a_stale_environment():
    t = (CODE / 'fulltext-push' / 'school-collector.slurm').read_text()
    assert 'CHANNELS_FORCE' in t and 'OA_RESERVE' in t and 'wayback_acm}' not in t


def test_openalex_reserve_is_configurable(monkeypatch):
    import importlib
    monkeypatch.setenv('OA_RESERVE', '4000')
    import oa_refresh
    assert importlib.reload(oa_refresh).RESERVE == 4000
    monkeypatch.delenv('OA_RESERVE')
    assert importlib.reload(oa_refresh).RESERVE == 800
