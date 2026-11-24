"""tools/oa_refresh_works.py merge: new records inserted, changed ones updated, a merged id replaced (not duplicated), datasets untouched, backup written."""
import json
import sqlite3
import zlib

import oa_refresh_works as R  # noqa: E402

W = 'https://openalex.org/W'


def work(n, doi=None, typ='article', year=2026, au='A1'):
    return dict(id=f'{W}{n}', doi=doi, title=f't{n}', publication_year=year, type=typ, ids={}, primary_location=None,
                authorships=[dict(author=dict(id=f'https://openalex.org/{au}'), institutions=[])])


def test_merge_reconciles(tmp_path, monkeypatch):
    sweep = tmp_path / 'sweep.sqlite'
    sc = sqlite3.connect(sweep)
    sc.execute('create table pages (year int, page int, cursor text, next_cursor text, n int, count int, fetched_at text, body blob, primary key (year, page))')
    old = [work(1, 'https://doi.org/10.1/a'), work(2, 'https://doi.org/10.1/b'), work(3, typ='dataset'), work(4)]
    sc.execute('insert into pages values (2026,0,"*",null,4,4,"x",?)', (R.pack(old),)); sc.commit(); sc.close()
    pw = tmp_path / 'pw.sqlite'
    pc = sqlite3.connect(pw); pc.execute('create table works (id text primary key, body blob)')
    pc.execute('insert into works values (?,?)', (f'{W}2', R.pack(old[1]))); pc.commit(); pc.close()
    stage = tmp_path / 'stage'; stage.mkdir()
    monkeypatch.setattr(R, 'stage_dir', lambda tag=R.TAG: stage)
    monkeypatch.setattr(R.P, 'data_w', lambda name, school=None, **k: sweep if name.startswith('openalex') else pw)
    monkeypatch.setattr(R, 'pi_author_ids', lambda school: ['A9'])
    monkeypatch.setattr(R, 'sweep_source', lambda sc: None)
    fresh_inst = [dict(work(1, 'https://doi.org/10.1/a'), title='changed'), work(22, 'https://doi.org/10.1/b'), work(5, au='A9')]   # 2 was merged into 22; 4 not returned
    st = R.stage_db('x', 'T'); st.close()
    st = sqlite3.connect(stage / 'x.sqlite')
    st.execute('insert into pages values ("inst","2026",0,null,3,3,"x",?)', (R.pack(fresh_inst),))
    st.execute('insert into pages values ("pi","A9",0,null,1,1,"x",?)', (R.pack([work(5, au='A9')]),))
    st.execute('insert into counts values ("all:2026",5,"x")'); st.execute('insert into done values ("inst","2026",3)'); st.commit(); st.close()
    rep = R.merge('x', [2026], 'T', apply=True)
    y = rep['years']['2026']
    assert y['new'] == 2 and y['changed'] == 1 and y['dropped'] == 1 and y['new_pi_credited'] == 1
    assert y['not_returned_reasons']['unresolved'] == 1           # id 4: no DOI, no lookups allowed
    sc = sqlite3.connect(sweep)
    ids = {w['id'] for (b,) in sc.execute('select body from pages') for w in json.loads(zlib.decompress(b))}
    assert ids == {f'{W}{n}' for n in (1, 22, 3, 4, 5)}          # 2 replaced by 22, dataset 3 kept, 4 kept
    assert sc.execute('select cursor from pages').fetchone()[0] == 'refresh:T'
    pc = sqlite3.connect(pw)
    assert {r[0] for r in pc.execute('select id from works')} == {f'{W}5'}   # the stale merged id 2 left pi-works, 5 came in
    assert (stage / 'backup-x.sqlite').exists() and (stage / 'report-x.json').exists()


def test_fetch_ids_batches_the_filter_stores_pi_pages_lists_the_missing_and_resumes(tmp_path, monkeypatch):
    stage = tmp_path / 'stage'; stage.mkdir()
    monkeypatch.setattr(R, 'stage_dir', lambda tag=R.TAG: stage)
    calls = []

    class Cl:
        used, remaining, requests = 0, 9000, 0

        def get(self, path, params=None, kind=None):
            calls.append(params)
            asked = params['filter'].split(':', 1)[1].split('|')
            res = [dict(work(int(a[1:])), ids={'openalex': f'{W}{a[1:]}'}) for a in asked if a != 'W3']
            return dict(results=res, meta=dict(count=len(res))), {}
    ids = [f'{W}{n}' for n in (1, 2, 3, 4)] + ['W2']        # a duplicate and a URL form are one id
    got, missing = R.fetch_ids('x', ids, Cl(), 'T', batch=3)
    assert len(calls) == 2 and all(c['filter'].startswith('ids.openalex:') for c in calls) and calls[0]['per-page'] == 3
    assert got == 3 and missing == ['W3']
    got2, _ = R.fetch_ids('x', ids, Cl(), 'T', batch=3)       # resumable: stored batches are not asked again
    assert len(calls) == 2 and got2 == 3
    st = sqlite3.connect(stage / 'x.sqlite')
    assert {w['id'] for (b,) in st.execute("select body from pages where kind='pi'") for w in R.unpack(b)} == {f'{W}{n}' for n in (1, 2, 4)}
    # merge --ids-only: the fetched works land in pi-works.sqlite, no sweep year is touched
    sweep = tmp_path / 'sweep.sqlite'
    sc = sqlite3.connect(sweep); sc.execute('create table pages (year int, page int, cursor text, next_cursor text, n int, count int, fetched_at text, body blob)'); sc.commit(); sc.close()
    pw = tmp_path / 'pw.sqlite'
    pc = sqlite3.connect(pw); pc.execute('create table works (id text primary key, body blob)'); pc.commit(); pc.close()
    monkeypatch.setattr(R.P, 'data_w', lambda name, school=None, **k: sweep if name.startswith('openalex') else pw)
    monkeypatch.setattr(R, 'pi_author_ids', lambda school: [])
    monkeypatch.setattr(R, 'sweep_source', lambda sc: None)
    rep = R.merge('x', [], 'T', apply=True)
    assert rep['pi']['new'] == 3 and {r[0] for r in sqlite3.connect(pw).execute('select id from works')} == {f'{W}{n}' for n in (1, 2, 4)}
