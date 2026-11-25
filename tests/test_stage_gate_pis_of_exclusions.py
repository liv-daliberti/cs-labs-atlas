"""stage_gate.pis_of drops coded census-overrides exclusions (ETH, 2026-11-24) and keeps uncoded ones (other schools' counts stay)."""
import stage_gate as G

CENSUS = [{'name': n, 'is_pi': True, 'pi_basis': {'sha256': n, 'quote': n}} for n in ('A', 'B', 'C')]


def run(monkeypatch, section, aliases=None):
    def read(path, default=None):
        if 'census-faculty' in str(path):
            return {'faculty': CENSUS}
        if 'census-overrides-school' in str(path):
            return section
        if 'census-name-aliases' in str(path):
            return aliases or {}
        return default if default is not None else {}
    monkeypatch.setattr(G, 'read', read)
    return sorted(x['name'] for x in G.pis_of('ethz'))


def test_coded_exclusion_is_dropped(monkeypatch):
    assert run(monkeypatch, {'B': {'exclude': True, 'exclude_reason_code': 'not_computing_applied_test'}}) == ['A', 'C']


def test_uncoded_exclusion_keeps_counting(monkeypatch):
    assert run(monkeypatch, {'B': {'exclude': True, 'why': 'older school'}}) == ['A', 'B', 'C']


def test_no_overrides_unchanged(monkeypatch):
    assert run(monkeypatch, {}) == ['A', 'B', 'C']


def test_native_merge_alias_counts_once(monkeypatch):
    merge = {'native_pi_merges': [{'canonical': 'A', 'aliases': ['B'], 'gate_counts_once': True}]}
    assert run(monkeypatch, {}, merge) == ['A', 'C']
    merge['native_pi_merges'][0].pop('gate_counts_once')
    assert run(monkeypatch, {}, merge) == ['A', 'B', 'C']   # without the flag the gate count is unchanged
