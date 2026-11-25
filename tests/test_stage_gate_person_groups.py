"""stage_gate.pis_of counts persons as the builder groups them (CUHK 2026-11-24: 167 census rows for 133 PIs)."""
import atlas_paths as P
import stage_gate as G


def census_row(name, **kw):
    return dict(name=name, aliases=[], is_pi=True, dblp=kw.pop('dblp', []), orcid=[], sources=[], pi_basis=None, **kw)


def setup(monkeypatch, rows, merges=()):
    files = {'census-faculty.json': dict(faculty=rows), 'census-additions.json': [], 'dblp-ids.json': {},
             'census-name-aliases.json': dict(school='t', rows=[], native_pi_merges=list(merges))}
    monkeypatch.setattr(G, 'read', lambda p, default=None: files.get(p, default))
    monkeypatch.setattr(P, 'data', lambda name, school=None, **kw: name)
    monkeypatch.setattr(G.CO, 'section', lambda *a, **k: {})


def test_shared_dblp_pid_merges_name_order_variants(monkeypatch):
    pid = ['https://dblp.org/pid/c/LeizhenCai']
    setup(monkeypatch, [census_row('CAI Leizhen', dblp=pid, collection_person_id='a'), census_row('Leizhen Cai', dblp=pid, collection_person_id='b')])
    out = G.pis_of('t')
    assert [x['name'] for x in out] == ['CAI Leizhen'] and out[0]['aliases'] == ['Leizhen Cai']


def test_reviewed_native_merge_applies_and_name_only_does_not(monkeypatch):
    ev = [dict(url='u', sha256='a' * 64, quote='q')]
    rows = [census_row('YAO Chi Chih Andrew', collection_person_id='a'), census_row('Andrew Chi Chih Yao', collection_person_id='b'),
            census_row('Wei Chen', collection_person_id='c'), census_row('CHEN Wei Ming', collection_person_id='d')]
    setup(monkeypatch, rows, [dict(canonical='Andrew Chi Chih Yao', aliases=['YAO Chi Chih Andrew'], reviewed_by='r', why='w', evidence=ev)])
    names = sorted(x['name'] for x in G.pis_of('t'))
    assert names == ['Andrew Chi Chih Yao', 'CHEN Wei Ming', 'Wei Chen']


def test_a_broken_reviewed_merge_keeps_census_rows(monkeypatch):
    ev = [dict(url='u', sha256='a' * 64, quote='q')]
    setup(monkeypatch, [census_row('A One', collection_person_id='a')], [dict(canonical='A One', aliases=['Gone Name'], reviewed_by='r', why='w', evidence=ev)])
    assert [x['name'] for x in G.pis_of('t')] == ['A One']
