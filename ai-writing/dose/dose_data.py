"""Loaders for the AI-dose analyses (pandas): the paper table (scores + universe + OpenAlex fields + controls) and lab membership.

paper_table()     one row per universe paper 2016-2026 with the scores, school(s), OpenAlex primary topic (topic, subfield, field, domain), type, team size,
                  venue type, open-access status (oa_extra.sqlite, when it exists), the PI's OpenAlex author id per lab (hier_pairs), and `trained_on`
                  (True for a 2016-2021 paper of the five detector-v2 schools whose old key falls in the detector's training split: its passages were
                  negatives in training, so its false-positive rate is not an out-of-sample figure)
lab_pairs()       (paper_id, lab_id, school, pi, year) membership rows
hier_pairs()      (paper_id, lab_id, pi_author_id, first_author_id): from the school packages (authorship.author_id is the PI's)
"""
import gzip
import json
import sqlite3

import numpy as np
import pandas as pd

import dcommon as D

ORIGINAL = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley']      # the schools of the detector's training pool


def universe():
    db = sqlite3.connect(f'file:{D.UNIVERSE_DB}?mode=ro', uri=True)
    papers = pd.read_sql('select paper_id, oa, title, year, home_school, schools, n_labs from papers', db)
    lp = pd.read_sql('select * from lab_papers', db)
    db.close()
    papers['schools'] = papers['schools'].map(json.loads)
    papers = papers[papers['year'].between(2016, 2026)].reset_index(drop=True)
    return papers, lp[lp['paper_id'].isin(set(papers['paper_id']))].reset_index(drop=True)


def scores():
    db = sqlite3.connect(f'file:{D.DB}?mode=ro', uri=True)
    df = pd.read_sql('select * from papers', db)
    db.close()
    return df


def passages(paper_ids=None):
    db = sqlite3.connect(f'file:{D.DB}?mode=ro', uri=True)
    df = pd.read_sql('select paper_id, pidx, words, p from passages', db)
    db.close()
    return df if paper_ids is None else df[df['paper_id'].isin(paper_ids)]


def split_of_old_keys():
    """{paper_id: 'train'|'cal'|'test'} for papers of the five original schools, by the detector's old key f'{school}:{work}'."""
    import v2common as V
    out = {}
    for s in ORIGINAL:
        p = D.P.data('lab_papers.jsonl.gz', s)
        if not p.exists():
            continue
        with gzip.open(p, 'rt') as f:
            for line in f:
                r = json.loads(line)
                if r.get('atlasWorkId') and r.get('work'):
                    out.setdefault(r['atlasWorkId'], V.split_of(f"{s}:{r['work']}"))
    return out


def hier_pairs(schools=None):
    rows = []
    for s in schools or D.SCHOOLS:
        p = D.P.data('lab_papers.jsonl.gz', s)
        if not p.exists():
            continue
        tab = {q['pi']: (q.get('labId') or f'atl:l:{s}:{q["pi"]}') for q in json.load(open(D.P.data('pis.json', s)))}
        with gzip.open(p, 'rt') as f:
            for line in f:
                r = json.loads(line)
                pid = r.get('atlasWorkId') or (('oa:' + r['oa'].rsplit('/', 1)[-1]) if r.get('oa') else None)
                if not pid:
                    continue
                by = r.get('byline') or []
                a = (r.get('authorship') or {}).get('author_id') or ''
                rows.append((pid, tab.get(r['pi'], f'atl:l:{s}:{r["pi"]}'), a.rsplit('/', 1)[-1], len(by), r.get('type'), r.get('venue')))
    return pd.DataFrame(rows, columns=['paper_id', 'lab_id', 'pi_author_id', 'n_byline', 'type', 'venue']).drop_duplicates(['paper_id', 'lab_id'])


def oa_fields_table():
    db = sqlite3.connect(f'file:{D.OA_FIELDS}?mode=ro', uri=True)
    rows = db.execute("select id, type, language, primary_topic from works").fetchall()
    db.close()
    out = []
    for i, ty, lang, pt in rows:
        t = json.loads(pt) if pt and pt != 'null' else {}
        out.append((i, ty, lang, t.get('name'), t.get('subfield'), t.get('field'), t.get('domain')))
    return pd.DataFrame(out, columns=['oa_id', 'work_type', 'language', 'oa_topic', 'oa_subfield', 'oa_field', 'oa_domain'])


def extra_table():
    p = D.EMB / 'oa_extra.sqlite'
    if not p.exists():
        return None
    db = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
    df = pd.read_sql('select id as oa_id, oa_status, is_oa, source_type, source_name, n_authors, author_ids, n_refs, cited_by from works', db)
    db.close()
    return df


def paper_table(with_split=True):
    papers, lp = universe()
    sc = scores().drop(columns=['home_school', 'year'])
    df = papers.merge(sc, on='paper_id', how='left')
    df['oa_id'] = df['oa'].fillna('').str.rsplit('/', n=1).str[-1]
    df = df.merge(oa_fields_table(), on='oa_id', how='left')
    ex = extra_table()
    if ex is not None:
        df = df.merge(ex, on='oa_id', how='left')
        df['team_size'] = df['n_authors']
    df['period'] = np.where(df['year'] <= 2021, 'pre', np.where(df['year'] >= 2023, 'post', 'transition'))
    if with_split:
        sp = split_of_old_keys()
        df['old_split'] = df['paper_id'].map(sp)
        df['trained_on'] = df['old_split'].eq('train') & df['year'].between(2016, 2021) & df['home_school'].isin(ORIGINAL) & df['ai_share'].notna()
    return df


def lab_pairs():
    papers, lp = universe()
    return lp[['paper_id', 'lab_id', 'school', 'pi', 'lab_name', 'dept', 'year']]
