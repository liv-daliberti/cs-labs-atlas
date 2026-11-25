"""stage_gate.pis_of drops coded census-overrides exclusions (ETH, 2026-11-24) and keeps uncoded ones (other schools' counts stay)."""
import stage_gate as G

CENSUS = [{'name': n, 'is_pi': True, 'pi_basis': {'sha256': n, 'quote': n}} for n in ('A', 'B', 'C')]


def run(monkeypatch, section):
    def read(path, default=None):
        if 'census-faculty' in str(path):
            return {'faculty': CENSUS}
        if 'census-overrides-school' in str(path):
            return section
        return default if default is not None else {}
    monkeypatch.setattr(G, 'read', read)
    return sorted(x['name'] for x in G.pis_of('ethz'))


def test_coded_exclusion_is_dropped(monkeypatch):
    assert run(monkeypatch, {'B': {'exclude': True, 'exclude_reason_code': 'not_computing_applied_test'}}) == ['A', 'C']


def test_uncoded_exclusion_keeps_counting(monkeypatch):
    assert run(monkeypatch, {'B': {'exclude': True, 'why': 'older school'}}) == ['A', 'B', 'C']


def test_no_overrides_unchanged(monkeypatch):
    assert run(monkeypatch, {}) == ['A', 'B', 'C']
