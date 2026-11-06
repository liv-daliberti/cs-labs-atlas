"""Join the detector-v3 paper table to the universe (owner 2026-11-05).

paper_ai_v3.parquet keys the 12,834 papers whose copies were added after the universe was built (Georgia Tech 9,211, UChicago 2,895, a few hundred of the other schools: the
`sections_extra` shards) by the package's current atlas work id (`atl:w:<hash>`) or an `oa:` id, with year / home_school / oa_id empty; the universe (embeddings/universe.sqlite) keys
the same works by `oa:W...`. `to_universe(paper_ids)` maps each v3 id to its universe paper id: itself when it is one, else through the OpenAlex id (the package `lab_papers`
atlasWorkId -> oa, or the id's own `oa:W...`), else None. Ids that map to the same universe paper keep the first.
"""
import gzip
import json
import sqlite3

import dcommon as D


def universe_oa():
    db = sqlite3.connect(f'file:{D.UNIVERSE_DB}?mode=ro', uri=True)
    rows = db.execute('select paper_id, oa from papers').fetchall()
    db.close()
    ids = {p for p, _ in rows}
    by_oa = {(o or '').rsplit('/', 1)[-1]: p for p, o in rows if o}
    return ids, by_oa


def to_universe(paper_ids):
    ids, by_oa = universe_oa()
    need = {p for p in paper_ids if p not in ids}
    atl_oa = {}
    for s in D.SCHOOLS:
        path = D.P.data('lab_papers.jsonl.gz', s)
        if not path.exists():
            continue
        with gzip.open(path, 'rt') as f:
            for line in f:
                r = json.loads(line)
                a = r.get('atlasWorkId')
                if a in need and r.get('oa'):
                    atl_oa.setdefault(a, r['oa'].rsplit('/', 1)[-1])
    out = {}
    for p in paper_ids:
        if p in ids:
            out[p] = p
        else:
            oa = atl_oa.get(p) or (p[3:] if p.startswith('oa:W') else None)
            out[p] = by_oa.get(oa) if oa else None
    return out


def v3_table():
    """paper_ai_v3 with `paper_id` = the universe id (rows that map nowhere are dropped; duplicates keep the row with the most scored main passages), `paper_id_v3` = the original id,
    and year / home_school / oa_id filled from the universe where the v3 table has none."""
    import pandas as pd
    pa = pd.read_parquet(D.MAIN_AIW / 'detector_v3' / 'results' / 'paper_ai_v3.parquet').drop_duplicates('paper_id')
    pa['paper_id_v3'] = pa['paper_id']
    pa['paper_id'] = pa['paper_id'].map(to_universe(pa['paper_id'].tolist()))
    pa = pa[pa['paper_id'].notna()].sort_values('n_main_scored', ascending=False).drop_duplicates('paper_id')
    db = sqlite3.connect(f'file:{D.UNIVERSE_DB}?mode=ro', uri=True)
    un = pd.read_sql('select paper_id, year as u_year, home_school as u_home from papers', db)
    db.close()
    pa = pa.merge(un, on='paper_id', how='left')
    pa['year'] = pa['year'].fillna(pa['u_year'])
    pa['home_school'] = pa['home_school'].fillna(pa['u_home'])
    pa['trained_on_v3'] = pa['trained_on_v3'].fillna(False).astype(bool) | (pa['split_v3'].eq('train') & pa['year'].between(2016, 2021))      # the table's flag needs the year
    return pa.drop(columns=['u_year', 'u_home'])
