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
