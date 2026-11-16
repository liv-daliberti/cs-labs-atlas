"""2026-11-10 owner decision: discovery channels back on for every loop; wayback_acm off; OpenAlex spend stops at 4,000 credits left.
2026-11-16 owner decision: core and core_bulk are also run in the loops (after s2), to raise today's download count."""
import tomllib
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
LOOP_SCHOOLS = 'harvard jhu oxford uchicago washu cmu mit stanford berkeley princeton epfl gatech michigan toronto tsinghua sjtu'.split()
NEED = {'oa_arxiv', 'openalex', 'proceedings', 'arxiv_title', 'dblp_ee', 's2', 'europepmc', 'pmc', 'figshare', 'labpages', 'pihomes'}


def test_every_loop_charter_runs_discovery_without_wayback():
    for s in LOOP_SCHOOLS:
        ch = tomllib.loads((CODE / 'schools' / f'{s}.toml').read_text())['collector']['channels']
        assert NEED <= set(ch), s
        assert 'wayback_acm' not in ch, s


def test_school_collector_reads_the_charter_not_a_stale_environment():
    t = (CODE / 'fulltext-push' / 'school-collector.slurm').read_text()
    assert 'CHANNELS_FORCE' in t and 'OA_RESERVE' in t and 'wayback_acm}' not in t


def test_openalex_reserve_is_configurable(monkeypatch):
    import importlib.util
    monkeypatch.syspath_prepend(str(CODE / 'fulltext-push'))   # this checkout's copy, whatever CS_ATLAS_CODE says

    def load():
        spec = importlib.util.spec_from_file_location('oa_refresh_probe', CODE / 'fulltext-push' / 'oa_refresh.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    monkeypatch.setenv('OA_RESERVE', '4000')
    assert load().RESERVE == 4000
    monkeypatch.delenv('OA_RESERVE')
    assert load().RESERVE == 800


def test_onboarding_loop_reads_the_package_copy_until_admission():
    t = (CODE / 'fulltext-push' / 'school-collector.slurm').read_text()
    assert 'hierarchy-onboard' in t and 'LIVE_H="$CS_ATLAS_CODE/hierarchy"' in t
    # the live hierarchy wins as soon as the school has its own lab_papers file
    assert t.index('if [ -e "$LIVE_H/$SCHOOL/derived/lab_papers.jsonl.gz" ]') < t.index('elif [ -e "$ONBOARD/')
