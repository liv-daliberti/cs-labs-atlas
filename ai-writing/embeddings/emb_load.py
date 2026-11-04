"""Loaders for the analyses (pandas, pyarrow): the universe tables, a model's vectors across the school containers, OpenAlex topics."""
import json
import sqlite3

import numpy as np
import pandas as pd

import ecommon as C
import store
from models import MODELS

PRE, POST = range(2016, 2023), range(2023, 2027)
YEARS = range(2016, 2027)


def universe():
    """(papers df: paper_id, year, home_school, schools(list), oa; lab_papers df: paper_id, school, lab_id, pi, lab_name, dept, year)."""
    db = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True)
    papers = pd.read_sql('select paper_id, oa, title, year, home_school, schools from papers', db)
    papers['schools'] = papers['schools'].map(json.loads)
    lp = pd.read_sql('select * from lab_papers', db)
    db.close()
    papers = papers[papers['year'].between(YEARS.start, YEARS.stop - 1)].reset_index(drop=True)
    return papers, lp[lp['paper_id'].isin(set(papers['paper_id']))].reset_index(drop=True)


def vectors(model, kind):
    """(ids list, float32 matrix of the per-paper vectors, meta of one container) over every school's container of the model."""
    ids, mats, meta = [], [], None
    for s in C.SCHOOLS:
        if not store.container_path(model, s, kind).exists():
            continue
        c = store.load(model, s, kind)
        ids += [str(i) for i in c['ids']]
        mats.append(c['M'].astype(np.float32))
        meta = meta or store.meta(model, s, kind)
    if not mats:
        return [], np.zeros((0, MODELS[model]['dim']), np.float32), None
    return ids, np.vstack(mats), meta


def oa_topics(papers):
    """papers df with columns oa_topic, oa_subfield, oa_field, oa_domain (primary topic from the OpenAlex snapshot; None where absent)."""
    db = sqlite3.connect(f'file:{C.OA_FIELDS}?mode=ro', uri=True)
    rows = db.execute("select id, primary_topic from works where primary_topic != 'null'").fetchall()
    db.close()
    t = {i: json.loads(p) for i, p in rows}
    key = papers['oa'].fillna('').str.rsplit('/', n=1).str[-1]
    out = papers.copy()
    for col, f in (('oa_topic', 'name'), ('oa_subfield', 'subfield'), ('oa_field', 'field'), ('oa_domain', 'domain')):
        out[col] = key.map(lambda k, f=f: (t.get(k) or {}).get(f))
    return out


def memberships(lp):
    """(scope, scope_id, paper_id) rows: lab, dept (school|dept), school; the 'all' scope is every paper and is added by the callers."""
    lab = lp[['paper_id', 'lab_id']].drop_duplicates().rename(columns={'lab_id': 'scope_id'}).assign(scope='lab')
    d = lp.dropna(subset=['dept']).assign(scope_id=lambda x: x['school'] + '|' + x['dept'])[['paper_id', 'scope_id']].drop_duplicates().assign(scope='dept')
    s = lp[['paper_id', 'school']].drop_duplicates().rename(columns={'school': 'scope_id'}).assign(scope='school')
    return pd.concat([lab, d, s], ignore_index=True)[['scope', 'scope_id', 'paper_id']]
