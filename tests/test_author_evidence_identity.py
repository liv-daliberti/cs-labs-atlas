"""Borrowed author evidence needs exact work identity; same titles and DOI collisions do not suffice."""
import gzip
import json
import sqlite3
import subprocess
import zlib

import pytest

import atlas_paths as P
import identity_rule as IR
import review_identity as RI


@pytest.fixture
def sources(tmp_path, monkeypatch):
    monkeypatch.setattr(IR, '_LAB', {})
    monkeypatch.setattr(P, 'data', lambda name, *a, **k: tmp_path / name)
    monkeypatch.setattr(P, 'FT_RAW', tmp_path / 'raw')
    (tmp_path / 'raw').mkdir()

    def write(rows, bodies=()):
        with gzip.open(tmp_path / 'lab_papers.jsonl.gz', 'wt') as f:
            for row in rows:
                f.write(json.dumps(row) + '\n')
        if bodies:
            with sqlite3.connect(tmp_path / 'pi-works.sqlite') as db:
                db.execute('create table works(id text primary key,body blob)')
                db.executemany('insert into works values(?,?)', [(b['id'], zlib.compress(json.dumps(b).encode())) for b in bodies])
        return IR.lab_first_authors(tmp_path, 'school'), RI.byline_index('school')
    return write


def paper(oa='W1', doi='10.1234/one', name='Ada Lovelace', **kw):
    return dict(work=None, oa='https://openalex.org/' + oa, doi=doi, title='A Shared Research Paper Title', byline=[name], **kw)


def catalog(wid='unknown', doi='10.1234/missing', graph=None, oa=None):
    return dict(id=wid, doi=doi, title='A Shared Research Paper Title', graph_json=json.dumps(graph or {}),
                oa_json=json.dumps(dict(id=oa)) if oa else None)


def test_actual_same_title_different_doi_cannot_lend_authors(sources):
    # Actual audit identities: 2017 VLDB target vs 2019 HotNets "Mind the gap".
    row = paper('W2984274416', '10.1145/3365609.3365856', 'Jack Tigar Humphries')
    row['title'] = 'Mind the gap'
    _, byline = sources([row])
    first, authoritative = IR.first_author(None, 'school', 'school_oa_W2753377075', 'Mind the gap', '10.14778/3137765.3137791', graph_json='{}')
    assert (first, authoritative) == ('', False)
    assert RI.authors_of(dict(catalog(doi='10.14778/3137765.3137791'), title='Mind the gap'), byline) == []
    verdict, _ = IR.judge('Mind the gap Jack Tigar Humphries ' + 'research text ' * 30, 'Mind the gap', first,
                          '10.14778/3137765.3137791', None, None, author_authoritative=authoritative)
    assert verdict == 'undecided'


def test_legacy_title_keys_are_ignored_even_when_supplied_by_a_caller(monkeypatch):
    title = 'A Shared Research Paper Title'
    monkeypatch.setattr(IR, 'lab_first_authors', lambda *a: {'t:' + RI.nt(title): 'wrong'})
    assert IR.first_author(None, 'school', 'unknown', title, None, graph_json='{}') == ('', False)
    assert RI.authors_of(catalog(doi=None), {'t:' + RI.nt(title): ['Wrong Person']}) == []


@pytest.mark.parametrize('kind', ['work', 'oa', 'doi', 'graph_oa', 'oa_json'])
def test_exact_source_identities_keep_authors(sources, kind):
    row = paper();row['work'] = 'accepted-work'
    first_index, byline = sources([row])
    assert not any(k.startswith('t:') for k in first_index | byline)
    if kind == 'work':
        result = catalog(wid='accepted-work')
    elif kind == 'oa':
        result = catalog(wid='school_oa_W1')
    elif kind == 'doi':
        result = catalog(doi='HTTPS://DOI.ORG/10.1234/one')
    elif kind == 'graph_oa':
        result = catalog(graph=dict(openalex='https://openalex.org/W1'))
    else:
        result = catalog(oa='https://openalex.org/W1')
    assert RI.authors_of(result, byline) == ['lovelace']
    if kind != 'oa_json':
        assert IR.first_author(None, 'school', result['id'], result['title'], result['doi'], graph_json=result['graph_json']) == ('lovelace', True)


def test_doi_collision_cannot_borrow_but_exact_oa_stays_available(sources):
    # Synthetic author names isolate routing for the observed wrong-DOI pair.
    doi = '10.4230/lipics.approx-random.2018.34'
    _, byline = sources([paper('W2963320196', doi, 'Bob Hidden'), paper('W2964241527', doi, 'Alice Polar')])
    assert 'doi:' + doi not in byline
    assert RI.authors_of(catalog(doi=doi), byline) == []
    assert IR.first_author(None, 'school', 'unknown', '', doi, graph_json='{}') == ('', False)
    result = catalog(doi=doi, graph=dict(openalex='https://openalex.org/W2964241527'))
    assert RI.authors_of(result, byline) == ['polar']
    assert IR.first_author(None, 'school', result['id'], '', doi, graph_json=result['graph_json']) == ('polar', True)


def test_distinct_work_claims_are_ambiguous_even_with_identical_author_names(sources):
    index, byline = sources([paper('W1', name='Same Author'), paper('W2', name='Same Author')])
    assert 'doi:10.1234/one' not in index and 'doi:10.1234/one' not in byline
    assert index['school_oa_W1'] == 'author'


def test_rows_without_author_names_still_make_a_shared_doi_ambiguous(sources):
    row = paper('W2');row['byline'] = []
    index, byline = sources([paper(), row])
    assert 'doi:10.1234/one' not in index and 'doi:10.1234/one' not in byline


def test_openalex_cache_conflict_does_not_override_or_lend_by_doi(sources):
    body = dict(id='https://openalex.org/W2', doi='https://doi.org/10.1234/one', title='A Different Work',
                authorships=[dict(author=dict(display_name='Wrong Cached Author'))])
    _, byline = sources([paper()], [body])
    assert 'doi:10.1234/one' not in byline
    assert RI.authors_of(catalog(wid='school_oa_W1'), byline) == ['lovelace']
    assert RI.authors_of(catalog(doi='10.1234/one'), byline) == []


def test_explicit_accepted_edition_groups_cache_without_inventing_a_title_join(sources):
    row = paper(editions=[dict(work=None, oa='https://openalex.org/W2', doi='10.1234/one')])
    body = dict(id='https://openalex.org/W2', doi='10.1234/one', title='A Changed Edition Title',
                authorships=[dict(author=dict(display_name='Ada Lovelace'))])
    _, byline = sources([row], [body])
    assert byline['doi:10.1234/one'] == ['Ada Lovelace']
    assert RI.authors_of(catalog(oa=body['id']), byline) == ['lovelace']


def test_own_ordered_graph_authors_beat_borrowed_doi_evidence(sources):
    _, byline = sources([paper()])
    result = catalog(doi='10.1234/one', graph=dict(authors=[dict(name='Grace Hopper')]))
    assert IR.first_author(None, 'school', result['id'], '', result['doi'], graph_json=result['graph_json']) == ('hopper', True)
    assert RI.authors_of(result, byline) == ['hopper']


def test_non_latin_own_author_is_not_replaced_with_a_borrowed_latin_family(sources):
    _, byline = sources([paper()])
    result = catalog(doi='10.1234/one', graph=dict(authors=[dict(name='张三')]))
    assert IR.first_author(None, 'school', result['id'], '', result['doi'], graph_json=result['graph_json']) == ('', True)
    assert RI.authors_of(result, byline) == []


def test_lab_pi_is_not_invented_as_authoritative_first_author(sources):
    row = paper();row['byline'] = [];row['pis'] = ['Ada Lovelace']
    sources([row])
    assert IR.first_author(None, 'school', 'school_oa_W1', '', row['doi'], graph_json='{}') == ('', False)
    graph = dict(school_faculty=[dict(name='Ada Lovelace')])
    assert IR.first_author(None, 'school', 'school_oa_W1', '', row['doi'], graph_json=json.dumps(graph)) == ('lovelace', False)


def test_own_byline_and_read_only_catalog_lookup_remain_available(sources, tmp_path):
    sources([])
    graph = json.dumps(dict(byline=['Grace Hopper', 'Ada Lovelace']))
    path = tmp_path / 'catalog.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('create table works(id text primary key, graph_json text)')
        db.execute('insert into works values(?,?)', ('own-work', graph))
    before = path.read_bytes()
    assert IR.first_author(None, 'school', 'own-work', '', None, catalog=path) == ('hopper', True)
    assert path.read_bytes() == before


def test_duplicate_lab_relations_do_not_make_a_single_work_ambiguous(sources):
    row = paper();other = dict(row, pi='Another PI')
    index, byline = sources([row, other])
    assert index['doi:10.1234/one'] == 'lovelace'
    assert byline['doi:10.1234/one'] == ['Ada Lovelace']


def test_exact_own_oa_beats_legacy_doi_evidence(monkeypatch):
    first = {'oa:W1': 'correct', 'doi:10.1234/collision': 'wrong'}
    monkeypatch.setattr(IR, 'lab_first_authors', lambda *a: first)
    graph = json.dumps(dict(openalex='https://openalex.org/W1'))
    assert IR.first_author(None, 'school', 'unknown', '', '10.1234/collision', graph_json=graph) == ('correct', True)
    byline = {'oa:W1': ['Correct Person'], 'doi:10.1234/collision': ['Wrong Person']}
    assert RI.authors_of(catalog(doi='10.1234/collision', graph=json.loads(graph)), byline) == ['person']


def test_legacy_entry_imports_under_isolated_python_without_new_path_edits():
    result = subprocess.run([str(P.PY), '-I', '-c',
                             'import runpy; runpy.run_path(' + repr(RI.__file__) + ', run_name="isolated_import")'],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
