"""ROADMAP #28: DOI sibling works alias onto one canonical work; nothing is deleted; the alias can only merge."""
import sqlite3

import catalog_alias as A


def W(i, title, doi, status='queued', fp=None, ic=None, year=2020):
    return dict(id=i, title=title, doi=doi, year=year, status=status, file_path=fp, identity_check=ic)


def test_canonical_is_the_downloaded_checked_work_then_the_smallest_id():
    ws = [W('b_hash', 'T one two three', '10.1/x'), W('a_oa', 'T one two three', '10.1/x', 'downloaded', '/f', 'title_in_first_three_pages'),
          W('c', 'T one two three', '10.1/x', 'downloaded', '/g')]
    assert A.choose_canonical(ws) == 'a_oa'
    assert A.choose_canonical([W('z', 't', 'd'), W('y', 't', 'd')]) == 'y'


def test_plan_groups_by_normalised_doi_and_never_loses_a_download():
    ws = [W('a', 'Learning deep features for localization', '10.1/X'), W('b', 'Learning deep features for localization', 'https://doi.org/10.1/x', 'downloaded', '/f'),
          W('c', 'Something else entirely different', '10.2/y'), W('d', 'BikeMate', '10.3/z'), W('e', 'BikeMate: bike riding monitoring', '10.3/z')]
    p = A.plan(ws)
    assert p['groups'] == [('10.1/x', 'b', ['a']), ('10.3/z', 'd', ['e'])]
    assert p['stats']['groups_whose_canonical_lost_a_download'] == 0 and p['stats']['aliases'] == 2 and p['stats']['canonical_works'] == 3


def test_doi_group_with_unrelated_titles_is_a_conflict_not_an_alias():
    ws = [W('a', 'Proceedings of the workshop on robotics', '10.9/p'), W('b', 'A study of cache replacement policies', '10.9/p')]
    p = A.plan(ws)
    assert p['groups'] == [] and p['conflicts'] == ['10.9/p']


def test_title_year_groups_are_reported_never_aliased():
    ws = [W('a', 'A fairly long shared title for the preprint', None), W('b', 'A fairly long shared title for the preprint', '10.1/pub')]
    p = A.plan(ws)
    assert p['groups'] == [] and p['title_year'] == [['a', 'b']]


def test_alias_resolution_through_the_view(tmp_path):
    db = sqlite3.connect(tmp_path / 'catalog.sqlite')
    db.execute('create table works (id text primary key, title text)')
    db.executemany('insert into works values (?,?)', [('a', 't'), ('b', 't'), ('c', 'u')])
    assert A.resolve(db) == {} and A.canonical_of(db, 'a') == 'a'   # no table yet: every work is its own canonical
    db.executescript(A.SCHEMA)
    db.execute("insert into work_alias values ('a','b','doi','10.1/x','2026-11-02T00:00:00Z')")
    assert A.canonical_of(db, 'a') == 'b' and A.canonical_of(db, 'c') == 'c'
    assert sorted(db.execute('select id, canonical_id from work_canonical')) == [('a', 'b'), ('b', 'b'), ('c', 'c')]
    assert db.execute('select count(*) from works').fetchone()[0] == 3   # nothing deleted


def make_store(tmp_path):
    store = tmp_path / 'mit'
    store.mkdir()
    db = sqlite3.connect(store / 'catalog.sqlite')
    db.executescript("""create table works (id text primary key, title text, doi text, year integer, graph_json text not null default '{}', oa_json text,
        metadata_source text, status text not null default 'queued', file_path text, sha256 text, byte_count integer, pages integer, download_url text,
        downloaded_at text, identity_check text);
        create table candidates (work_id text, url text, landing_url text, license text, version text, metadata_source text, primary key(work_id, url));
        create table attempts (id integer primary key, work_id text, url text, observed_at text, status text, detail text);""")
    t = 'Learning deep features for localization'
    db.executemany('insert into works (id, title, doi, year, status, file_path, identity_check) values (?,?,?,?,?,?,?)',
                   [('mit_oa_W1', t, '10.1/x', 2016, 'downloaded', '/f.pdf', 'ok'), ('mit_hash1', t, '10.1/X', 2016, 'queued', None, None), ('mit_other', 'Other paper entirely different', '10.2/y', 2017, 'queued', None, None)])
    db.executemany('insert into candidates values (?,?,?,?,?,?)', [('mit_hash1', 'https://a/1.pdf', None, 'cc-by', None, None), ('mit_oa_W1', 'https://a/2.pdf', None, None, None, None)])
    db.commit()
    db.close()
    return store


def test_apply_writes_aliases_copies_candidates_and_keeps_every_work(tmp_path):
    store = make_store(tmp_path)
    db = sqlite3.connect(store / 'catalog.sqlite')
    p = A.plan(A.load(db))
    db.close()
    assert p['groups'] == [('10.1/x', 'mit_oa_W1', ['mit_hash1'])]
    assert A.apply(store, p['groups']) == 1
    db = sqlite3.connect(store / 'catalog.sqlite')
    assert A.resolve(db) == {'mit_hash1': 'mit_oa_W1'}
    assert sorted(r[0] for r in db.execute("select url from candidates where work_id='mit_oa_W1'")) == ['https://a/1.pdf', 'https://a/2.pdf']
    assert db.execute('select count(*) from works').fetchone()[0] == 3
    assert A.apply(store, p['groups']) == 0   # idempotent
    assert list((store / 'backups').glob('catalog.before-alias-*.sqlite'))


def test_readers_resolve_through_the_alias_view(tmp_path, monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path
    import lab_paper_copies as LPC
    fp = Path(__file__).resolve().parents[1] / 'fulltext-push'   # this checkout's ftp_common, whatever else is on sys.path
    sys.path.insert(0, str(fp))
    spec = importlib.util.spec_from_file_location('ftp_common_under_test', fp / 'ftp_common.py')
    F = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(F)
    sys.path.remove(str(fp))
    store = make_store(tmp_path)
    db = sqlite3.connect(store / 'catalog.sqlite')
    A.apply(store, A.plan(A.load(db))['groups'])
    db.close()
    monkeypatch.setattr(F, 'FT', tmp_path)
    cs = F.catalog_state('mit')
    assert cs['alias'] == {'mit_hash1': 'mit_oa_W1'}
    assert cs['status']['mit_hash1'] == 'downloaded' and cs['doi']['10.1/x'] == 'mit_oa_W1'
    assert cs['urls']['mit_oa_W1'] >= {'https://a/1.pdf', 'https://a/2.pdf'} and 'mit_hash1' not in cs['urls']
    assert F.match_work('mit', dict(work='mit_hash1', oa='W9'), cs) == 'mit_oa_W1'
    ro = sqlite3.connect(f'file:{store}/catalog.sqlite?mode=ro', uri=True)
    assert [r[0] for r in F.works_rows(ro, 'id', canonical=True)] == ['mit_oa_W1', 'mit_other']
    assert len(list(F.works_rows(ro, 'id'))) == 3
    out, n = LPC.resolve('mit', [dict(work='mit_hash1', oa='W1', doi=None, title='x', year=2016)], dict(cs['status']), cs['doi'], set(), alias=cs['alias'])
    assert out['mit_hash1']['catalog'] == 'mit_oa_W1' and n['local'] == 1


def test_alias_candidate_lands_once_on_a_canonical_without_candidates_and_a_second_apply_is_a_noop(tmp_path):
    store = make_store(tmp_path)
    db = sqlite3.connect(store / 'catalog.sqlite')
    db.execute("delete from candidates where work_id='mit_oa_W1'")   # the canonical has none; its alias has exactly one
    db.commit()
    groups = A.plan(A.load(db))['groups']
    db.close()
    A.apply(store, groups)
    A.apply(store, groups)
    db = sqlite3.connect(store / 'catalog.sqlite')
    assert list(db.execute("select work_id, url from candidates where work_id='mit_oa_W1'")) == [('mit_oa_W1', 'https://a/1.pdf')]
    assert list(db.execute("select work_id, url from candidates where work_id='mit_hash1'")) == [('mit_hash1', 'https://a/1.pdf')]   # the alias keeps its own row
    assert db.execute('select count(*) from work_alias').fetchone()[0] == 1
