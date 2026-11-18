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
