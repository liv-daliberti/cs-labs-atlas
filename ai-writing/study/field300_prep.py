"""Field-300 preparation: the analysis tables and the GPU text store from the merged corpus (CPU; run after `field300_corpus.py merge`).

  field300_prep.py build        work/papers.parquet (one row per paper, no text), work/paper_inst.parquet (paper x institution, full + fractional weights),
                                work/institutions.parquet (roster + size), work/refs/year=Y.parquet (reference lists, journal-or-not flag), work/emb/texts.sqlite (abstracts of
                                the papers the GPU layers read: >= 50 words, English; the layout embed.py and dose_score.py read via CS_ATLAS_EMBEDDINGS=work/emb)
Attribution (stated in FIELD300.md): a paper counts in EACH institution that appears on its byline (full counting, the unit of the 12-school lab layers); the fractional
weight w_frac = authorships of the institution / sum of cohort-attributed authorships is kept for the sensitivity. Institution size = papers per year 2016-2025 (median).
"""
import argparse
import hashlib
import json
import sqlite3

import numpy as np
import pandas as pd

import field300_common as F
import study_prep as SP

MIN_WORDS_DETECTOR = 50
ASCII_MIN = 0.97


def english(lang, abstract):
    """OpenAlex language 'en'; a missing language counts as English only for a (nearly) pure ASCII abstract. Names and countries are never used."""
    if lang == 'en':
        return True
    if lang is None or (isinstance(lang, float) and np.isnan(lang)):
        a = abstract or ''
        return bool(a) and sum(c < '\x80' for c in a) / len(a) >= ASCII_MIN
    return False


def paper_table(df):
    """Per-paper flags from the corpus frame (columns of K.load_corpus)."""
    words = df['abstract'].str.split().str.len().fillna(0).astype(int)
    p = pd.DataFrame(dict(work=df['work'], year=df['year'], abs_words=words, venue_type=df['venue_type'], type=df['type'], topic=df['topic'], subfield=df['subfield'],
                          cs_primary=df['cs_primary'], cs_venue=df['cs_venue'], n_refs=df['n_refs'], n_auth=df['n_auth'], cited_by=df['cited_by'], retracted=df['retracted']))
    p['en'] = [english(a, b) for a, b in zip(df['lang'], df['abstract'])]
    p['abs_ok'] = (words >= MIN_WORDS_DETECTOR) & p['en']
    txt = df['title'].fillna('') + ' ' + df['abstract'].fillna('')
    p['llm_text'] = txt.str.contains(SP.LLM_RE, case=False, regex=True)
    p['has_abs10'] = words >= 10
    p['journal'] = df['venue_type'].eq('journal')
    return p


def paper_inst(df):
    n = df['inst'].map(len)
    w = df['work'].repeat(n).to_numpy()
    inst = np.concatenate(df['inst'].to_numpy()) if len(df) else np.empty(0, int)
    cnt = np.concatenate(df['inst_n'].to_numpy()) if len(df) else np.empty(0, int)
    tot = np.repeat(df['inst_n'].map(lambda a: int(np.sum(a))).to_numpy(), n.to_numpy())
    out = pd.DataFrame(dict(work=w, inst=inst.astype(np.int16), n_auth_inst=cnt.astype(np.int16), w_frac=(cnt / np.maximum(tot, 1)).astype(np.float32)))
    out['year'] = np.repeat(df['year'].to_numpy(), n.to_numpy()).astype(np.int16)
    return out


def institutions(pi, roster):
    r = pd.DataFrame(roster).drop(columns=['oa_ids'])
    sz = pi.groupby(['inst', 'year']).size().groupby('inst').median().rename('median_papers_per_year')
    tot = pi.groupby('inst').size().rename('papers_2016_2025')
    r = r.merge(sz, left_on='idx', right_index=True, how='left').merge(tot, left_on='idx', right_index=True, how='left').fillna({'median_papers_per_year': 0, 'papers_2016_2025': 0})
    q = r['median_papers_per_year']
    r['size_q'] = pd.qcut(q.rank(method='first'), 4, labels=['Q1 small', 'Q2', 'Q3', 'Q4 large']).astype(str)
    return r


def cmd_build(a):
    w = F.work_dir()
    w.mkdir(parents=True, exist_ok=True)
    (w / 'refs').mkdir(exist_ok=True)
    (w / 'emb').mkdir(exist_ok=True)
    frames, pis, pap = [], [], []
    texts = []
    for f in sorted((w / 'corpus').glob('year=*.parquet')):
        df = pd.read_parquet(f)
        y = int(f.stem.split('=')[1])
        df['year'] = y
        p = paper_table(df)
        pap.append(p)
        pis.append(paper_inst(df))
        pd.DataFrame(dict(work=df['work'], refs=df['refs'], journal=p['journal'], n_refs=p['n_refs'])).to_parquet(w / 'refs' / f'year={y}.parquet', index=False, compression='zstd')
        ok = p['abs_ok'].to_numpy()
        texts.append(pd.DataFrame(dict(paper_id='W' + df.loc[ok, 'work'].astype(str), title=df.loc[ok, 'title'], abstract=df.loc[ok, 'abstract'])))
        print(y, len(df), int(ok.sum()), flush=True)
    papers = pd.concat(pap, ignore_index=True)
    pi = pd.concat(pis, ignore_index=True)
    papers.to_parquet(w / 'papers.parquet', index=False)
    pi.to_parquet(w / 'paper_inst.parquet', index=False)
    inst = institutions(pi, F.load_roster())
    inst.to_parquet(w / 'institutions.parquet', index=False)
    t = pd.concat(texts, ignore_index=True)
    dbp = w / 'emb' / 'texts.sqlite'
    dbp.unlink(missing_ok=True)
    db = sqlite3.connect(dbp)
    db.execute('create table abstracts (paper_id text primary key, title text, abstract text, src text, words int, text_hash text)')
    db.execute('create table fulltext (paper_id text primary key, school text, path text, kind text, chars int, words int, usable int, body blob, flags text, text_hash text)')
    rows = ((r.paper_id, r.title or '', r.abstract, 'openalex-snapshot', len(r.abstract.split()),
             hashlib.sha1(((r.title or '') + ' ' + r.abstract).encode('utf-8', 'ignore')).hexdigest()[:16]) for r in t.itertuples(index=False))
    db.executemany('insert into abstracts values (?,?,?,?,?,?)', rows)
    db.commit()
    db.close()
    print(json.dumps(dict(papers=len(papers), paper_inst=len(pi), abstracts_for_gpu=len(t), institutions=len(inst), texts_bytes=dbp.stat().st_size)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build'])
    cmd_build(ap.parse_args())
