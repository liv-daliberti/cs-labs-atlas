"""sweep_from_snapshot writes oa_sweep's pages layout from a snapshot (main store + extension), with the API sweep's filter."""
import json
import sqlite3
import zlib

import oa_snapshot as O
import sweep_from_snapshot as T

OA = 'https://openalex.org/'


def w(i, year, n_auth=1, inst='I9'):
    ships = [{'author': {'id': OA + f'A{k}'}, 'institutions': [{'id': OA + inst, 'lineage': [OA + inst]}]} for k in range(n_auth)]
    return dict(id=OA + i, doi=None, title=i, publication_year=year, publication_date=f'{year}-01-01', type='article', authorships=ships, ids={}, primary_location=None, abstract='x')


def test_pages_layout_filter_and_counts(tmp_path, monkeypatch):
    d = tmp_path / '2026-10-14'; d.mkdir()
    for name, ws in (('openalex.sqlite', [w('W1', 2020), w('W2', 2020, 101), w('W3', 2021)]), ('ext-newu.sqlite', [w('W1', 2020), w('W4', 2020)])):
        db = sqlite3.connect(d / name); db.executescript(O.SCHEMA)
        for x in ws:
            db.execute('insert or ignore into works values (?,?,?,?,?,?,?)', (x['id'], None, x['publication_year'], 'article', x['title'], None, O.pack(x)))
            db.execute('insert or ignore into work_inst values (?,?)', (x['id'], 'I9'))
        db.commit(); db.close()
    (tmp_path / 'current').symlink_to('2026-10-14')
    monkeypatch.setattr(O, '_conns', {})
    monkeypatch.setattr(T.S, 'get', lambda k: {'window': [2020, 2021]})
    monkeypatch.setattr(T.S, 'sweep_ids', lambda k: ['I9'])
    out = tmp_path / 'sweep.sqlite'
    assert T.build('newu', out, root=tmp_path) == {2020: 2, 2021: 1}     # W2 has 101 authors; W1 is in both stores once
    c = sqlite3.connect(out)
    rows = c.execute('select year, page, n, count, cursor from pages order by year, page').fetchall()
    assert rows == [(2020, 0, 2, 2, 'snapshot:2026-10-14'), (2021, 0, 1, 1, 'snapshot:2026-10-14')]
    body = json.loads(zlib.decompress(c.execute('select body from pages where year=2020').fetchone()[0]))
    assert [x['id'][-2:] for x in body] == ['W1', 'W4'] and 'abstract' not in body[0] and set(body[0]) <= set(T.SELECT)
    assert json.loads(c.execute("select value from meta where key='source'").fetchone()[0])['snapshot_date'] == '2026-10-14'
