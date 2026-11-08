"""Build the analysis tables from a snapshot: the paper panel and the strict lab membership (no model, CPU only).

reads   <snapshot>/release/hierarchy/<school>/lab_papers.jsonl.gz + pis.json, universe/*, ai/papers_v3.parquet, citation/paper_measures.parquet,
        ipw/ipw_weights.parquet, delta/oa_fields_delta.sqlite (if present)
writes  <out>/work/panel.parquet (one row per work, 2016-2025), <out>/work/lab_papers.parquet (work x strict lab)
A paper is in a lab only when the lab's PI is on the byline (release lab_papers); advisers' labs never count (study-labs-are-strict).
Papers are matched to the earlier build's scores/embeddings by OpenAlex id; a work the build never saw keeps NaN scores (coverage is reported).
"""
import argparse
import gzip
import json
import sqlite3

import pandas as pd

import study_common as C

LLM_RE = r'large language model|\bLLMs?\b|\bGPT[- ]?\d?|ChatGPT|language model|foundation model|in-context|prompt(?:ing)?\b|instruction[- ]tun'


def membership(snap):
    rows = []
    for s in C.SCHOOLS:
        pis = {q['pi']: q for q in json.loads((snap / 'release' / 'hierarchy' / s / 'pis.json').read_text())}
        for line in gzip.open(snap / 'release' / 'hierarchy' / s / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            y = r.get('year')
            if not y or not C.FIRST <= y <= C.LAST:
                continue
            k = C.oa_short(r.get('oa')) or r.get('atlasWorkId')
            if not k:
                continue
            q = pis.get(r['pi'], {})
            rows.append((k, s, q.get('labId') or f'atl:l:{s}:{r["pi"]}', r['pi'], int(y), bool((r.get('appointment') or {}).get('periodId')),
                         r.get('identity'), (q.get('departments') or [None])[0], r.get('title') or ''))
    lp = pd.DataFrame(rows, columns=['k', 'school', 'lab_id', 'pi', 'year', 'period_supported', 'identity', 'dept', 'title'])
    return lp.sort_values('period_supported', ascending=False).drop_duplicates(['k', 'lab_id'])


def topics(snap):
    frames = []
    for name in ('universe/oa_fields.sqlite', 'delta/oa_fields_delta.sqlite'):
        p = snap / name
        if not p.exists():
            continue
        db = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
        d = pd.read_sql('select id as k, title, abstract, primary_topic from works', db)
        db.close()
        frames.append(d)
    d = pd.concat(frames).drop_duplicates('k', keep='last')
    pt = d['primary_topic'].map(lambda x: json.loads(x) if x and x != 'null' else {})
    d['topic_sub'] = pt.map(lambda t: t.get('subfield'))
    d['topic_field'] = pt.map(lambda t: t.get('field'))
    d['topic_name'] = pt.map(lambda t: t.get('name'))
    d['has_abs'] = d['abstract'].fillna('').str.split().str.len().ge(10)
    txt = (d['title'].fillna('') + ' ' + d['abstract'].fillna(''))
    d['llm_text'] = txt.str.contains(LLM_RE, case=False, regex=True)
    return d[['k', 'topic_sub', 'topic_field', 'topic_name', 'has_abs', 'llm_text']]


def build(snap, out):
    lp = membership(snap)
    pan = lp.sort_values('school', key=lambda s: s.map(C.SCHOOLS.index)).groupby('k').agg(
        year=('year', 'first'), school=('school', 'first'), n_labs=('lab_id', 'nunique'), period_supported=('period_supported', 'max')).reset_index()
    db = sqlite3.connect(f'file:{snap / "universe" / "universe.sqlite"}?mode=ro', uri=True)
    u = pd.read_sql('select paper_id, oa from papers', db)
    db.close()
    u['k'] = u['oa'].map(C.oa_short)
    u = u.dropna(subset=['k']).drop_duplicates('k')[['paper_id', 'k']]
    sc = pd.read_parquet(snap / 'ai' / 'papers_v3.parquet', columns=['paper_id', 'flag_abstract', 'kobak_abs', 'ai_share_main', 'ai_share_main_appendix',
                                                                      'abstained_share_main', 'trained_on_v3', 'appendix_found', 'body_words'])
    cm = pd.read_parquet(snap / 'citation' / 'paper_measures.parquet', columns=['paper_id', 'z_med', 'z_p10', 'rs_sub', 'h_sub', 'cd5', 'n_refs'])
    w = pd.read_parquet(snap / 'ipw' / 'ipw_weights.parquet', columns=['paper_id', 'w_ft'])
    u = u.merge(sc, on='paper_id', how='left').merge(cm, on='paper_id', how='left').merge(w, on='paper_id', how='left')
    pan = pan.merge(u, on='k', how='left').merge(topics(snap), on='k', how='left')
    pan['in_universe'] = pan['paper_id'].notna()
    pan['has_ft'] = pan['ai_share_main'].notna()
    pan['trained_on_v3'] = pan['trained_on_v3'].fillna(False).astype(bool)
    pan['llm_text'] = pan['llm_text'].fillna(False).astype(bool)
    pan['has_abs'] = pan['has_abs'].fillna(False).astype(bool)
    (out / 'work').mkdir(parents=True, exist_ok=True)
    pan.to_parquet(out / 'work' / 'panel.parquet')
    lp[['k', 'school', 'lab_id', 'pi', 'year', 'period_supported', 'dept']].to_parquet(out / 'work' / 'lab_papers.parquet')
    return pan, lp


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-07')
    a = ap.parse_args()
    out = C.results_dir(a.id)
    pan, lp = build(C.snapshot_dir(a.id), out)
    print(json.dumps({'works': len(pan), 'lab_work_pairs': len(lp), 'labs': int(lp.lab_id.nunique()), 'with_ft': int(pan.has_ft.sum()),
                      'with_abstract': int(pan.has_abs.sum()), 'with_topic': int(pan.topic_sub.notna().sum())}))
