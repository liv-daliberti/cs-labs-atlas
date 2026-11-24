import hashlib

import period_proofs as PP


def test_ladder_ranks():
    assert PP.ladder('Associate Professor') and PP.ladder('Professor of Electrical and Computer Engineering') and PP.ladder('Assoc. Prof. of Statistics')
    assert not PP.ladder('Research Associate Professor') and not PP.ladder('Professor Emeritus') and not PP.ladder('Professional Lecturer')


def test_proofs_need_a_spelled_given_name_and_ladder_rank():
    person = dict(name='A. Lynn Abbott', aliases=['Amos Lynn Abbott', 'Amos Abbott'])
    rows = [(2018, 'Abbott', 'Amos', 'Associate Professor', 'Abbott, Amos Associate Professor', 'u', 's'),
            (2018, 'Abbott', 'Jonathan', 'Associate Professor', 'x', 'u', 's'),
            (2019, 'Abbott', 'A.', 'Professor', 'x', 'u', 's'),
            (2021, 'Abbott', 'Amos', 'Research Associate Professor', 'x', 'u', 's')]
    assert list(PP.proofs(person, rows)) == [2018]


def test_salary_layout_documents_come_from_the_charter_entry(tmp_path):
    (tmp_path / 'bov-x.layout.txt').write_text('  Reed, Jeffrey         Professor                         182,994   AY\n  Reed, Jeffrey         Professor Emeritus   1,000   AY\nnoise line\n')
    (tmp_path / 'bov-x.pdf').write_bytes(b'pdf')
    doc = dict(kind='salary_layout', year=2018, file='bov-x', url='https://x/bov-x.pdf')
    rows = list(PP.salary_rows(doc, tmp_path))
    assert [r[:4] for r in rows] == [(2018, 'Reed', 'Jeffrey', 'Professor'), (2018, 'Reed', 'Jeffrey', 'Professor Emeritus')]
    assert rows[0][6] == hashlib.sha256(b'pdf').hexdigest()
    p = dict(name='Jeffrey H. Reed', aliases=[], sources=[dict(observed='20261110')], years_listed=[2026])
    assert sorted(PP.add_to(p, rows)) == [2018] and p['years_listed'] == [2018, 2026]
    assert PP.add_to(p, rows) == {}   # idempotent


def test_merge_year_proofs_into_census_rows(monkeypatch):
    import census_overrides as CO
    proof = dict(url='u', sha256='s', quote='Midkiff, Scott Professor', kind='stored_official_document', observed='2018')
    monkeypatch.setattr(CO, 'section', lambda key, resolve=None: {'Scott F. Midkiff': {'year_proofs': [proof]}})
    census = [dict(name='Scott F. Midkiff', sources=[dict(observed='20261107')], years_listed=[2026]), dict(name='Other', sources=[], years_listed=[])]
    PP.merge_year_proofs(census, 'vt')
    assert census[0]['years_listed'] == [2018, 2026] and len(census[0]['sources']) == 2 and census[1]['sources'] == []
    PP.merge_year_proofs(census, 'vt')
    assert len(census[0]['sources']) == 2


def test_vt_charter_lists_its_documents():
    import school_config as S
    docs = (S.get('vt').get('period_proofs') or {}).get('documents') or []
    assert {d['kind'] for d in docs} == {'salary_layout', 'catalog_directory'} and len(docs) == 8


def test_reviewed_override_period_without_id_gets_a_stable_one():
    from pihier.periods import pi_periods
    q = dict(start='2021', end='2026', why='x', evidence=[])
    out = pi_periods([], dict(periods=[q, dict(q, id='kept')]), 'Seth Neel')
    assert out[0]['id'] == 'override_period_seth_neel_2021_2026' and out[1]['id'] == 'kept'


def test_before_window_catches_a_pre_2016_date_on_any_route():
    from pihier.periods import before_window
    assert before_window('2012-05-01') and before_window('2009') and before_window('2015-12-31')
    assert not before_window('2016') and not before_window('2016-01-01') and not before_window(None) and not before_window('2024-03')


def test_native_rebuild_reads_reviewed_year_proofs_without_regenerating_census():
    from collections import Counter, defaultdict
    from types import SimpleNamespace

    from pihier.census import pi_records

    proof = dict(url='https://school.example/roster-2018', sha256='a' * 64,
                 quote='Ada Example Professor', observed='2018-08-01',
                 kind='dept_listing:CS', rank='Professor', emeritus=False, visiting=False)
    row = dict(name='Ada Example', is_pi=True, sources=[], years_listed=[2026])
    ctx = SimpleNamespace(census=[row], ov={'Ada Example': {'year_proofs': [proof]}},
                          yearly=defaultdict(list), Pid={}, units={}, periods=[], n=Counter())
    pi_records(ctx)
    assert [s['year'] for s in ctx.pis[0]['listings']] == [2018]
    assert ctx.pis[0]['listings'][0]['rank'] == 'Professor'
    assert row['sources'] == []  # The generated census is unchanged.
    # Missing hashes, wrong names and future/student claims remain inadmissible.
    ctx.ov['Ada Example']['year_proofs'] = [dict(proof, sha256=''),
        dict(proof, quote='Someone Else Professor'), dict(proof, quote='Ada Example PhD student'),
        dict(proof, quote='Ada Example will join as Professor')]
    pi_records(ctx)
    assert ctx.pis[0]['listings'] == []


def test_reviewed_year_proof_does_not_override_a_source_or_reopen_departure():
    from collections import Counter, defaultdict
    from types import SimpleNamespace

    from pihier.census import pi_records

    proof = dict(url='https://school.example/roster-2020', sha256='a' * 64,
                 quote='Ada Example Professor', observed='2020', kind='dept_listing:CS')
    row = dict(name='Ada Example', is_pi=True, sources=[dict(proof, url='https://school.example/original')])
    moved = dict(start='2016', end='2019', evidence=[dict(kind='faculty_end_moved', url='u', quote='left')])
    ctx = SimpleNamespace(census=[row], ov={'Ada Example': {'year_proofs': [proof], 'periods': [moved]}},
                          yearly=defaultdict(list), Pid={}, units={}, periods=[], n=Counter())
    pi_records(ctx)
    assert ctx.pis[0]['listings'] == []
    assert ctx.pis[0]['listingsAfterMove'][0]['url'] == 'https://school.example/original'
