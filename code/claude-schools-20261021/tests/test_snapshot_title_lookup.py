"""Stage 7: titles of unresolved lab-page papers are looked up in the local snapshot's extension stores before any API credit."""
import sqlite3

import labpage_recover as R
import oa_snapshot as O


def test_snapshot_title_works_returns_the_works_with_a_wanted_title():
    db = sqlite3.connect(':memory:')
    db.executescript(O.SCHEMA)
    for wid, title in (('W1', 'Hidden Convexity in Queueing Models'), ('W2', 'Something Else'), ('W3', None)):
        db.execute('insert into works (id, doi, year, type, title, updated_date, body) values (?,?,?,?,?,?,?)',
                   (wid, None, 2025, 'article', title, None, O.pack(dict(id='https://openalex.org/' + wid, title=title, publication_year=2025))))
    got = R.snapshot_title_works({R.norm_title('Hidden convexity in queueing models')}, dbs=[db])
    assert [w['id'] for _, w in got] == ['https://openalex.org/W1']
    assert R.snapshot_title_works({'no such title'}, dbs=[db]) == []
