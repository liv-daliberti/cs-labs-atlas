"""Consistency of the field-300 abstract-level estimates with the 12 deep schools (owner 2026-11-08, item 4).

  field300_consistency.py run  -> tables/f300_consistency_{estimates,papers}.csv

(a) Estimates: the field-300 post-minus-pre change restricted to the 12 deep schools' institutions, to the other 288, and their difference, next to the lab-level estimate of the
    12-school snapshot 2026-11-08 (the units differ: institution-level here, lab-level there; the papers differ: all CS papers of the institution here, PI-authored papers there).
(b) Papers: the abstract flag of the papers both studies scored (same detector, same operating point): agreement of the flags, which checks the pipeline rather than the science.
"""
import json
import sqlite3

import numpy as np
import pandas as pd

import field300_analyze as A
import field300_hetero as H
import study_common as SC

DEEP = {'princeton': 'I20089843', 'cmu': 'I74973139', 'epfl': 'I5124864', 'mit': 'I63966007', 'berkeley': 'I95457486', 'stanford': 'I97018004', 'michigan': 'I27837315',
        'uchicago': 'I40347166', 'gatech': 'I130701444', 'harvard': 'I136199984', 'jhu': 'I145311948', 'washu': 'I204465549'}
DEEP_RES = SC.results_dir('2026-11-08')


def deep_mask(inst):
    return inst['oa_id'].isin(DEEP.values()).to_numpy()


def deep_reference():
    """{measure: (est, lo, hi)} of the 12-school study (post minus pre) for the measures that have a counterpart."""
    t = DEEP_RES / 'tables'
    out = {}
    c = pd.read_csv(t / 'ai_contrasts.csv')
    r = c[(c.measure == 'abs_flag') & (c.scope == 'ALL') & (c['sample'] == 'all') & (c.contrast == 'post_minus_pre')]
    if len(r):
        out['abs_flag'] = (r.iloc[0].est, r.iloc[0].lo, r.iloc[0].hi)
    c = pd.read_csv(t / 'topics_llm_contrasts.csv')
    r = c[(c.scope == 'ALL') & (c.contrast == 'post_minus_pre')]
    if len(r):
        out['llm_topic'] = (r.iloc[0].est, r.iloc[0].lo, r.iloc[0].hi)
    c = pd.read_csv(t / 'embed_contrasts.csv')
    for lv, name in (('within_lab', 'emb_within_specter2_proximity_raw'), ('cross_school', 'emb_cross_specter2_proximity_raw')):
        r = c[(c.model == SC.HEADLINE_MODEL) & (c.variant == 'raw') & (c.scope == 'ALL') & (c['sample'] == 'all') & (c.level == lv) & (c.contrast == 'post_minus_pre')]
        if len(r):
            out[name] = (r.iloc[0].est, r.iloc[0].lo, r.iloc[0].hi)
    return out


def estimates():
    inst = A.institutions()
    W = A.draws(inst)
    ms = H.load_measures(['specter2_proximity'])
    m = deep_mask(inst)
    ref = deep_reference()
    rows = []
    for name, (kind, x, y) in ms.items():
        if name not in ('abs_flag', 'llm_topic', 'emb_within_specter2_proximity_raw', 'emb_cross_specter2_proximity_raw', 'entropy_subfield'):
            continue
        cd, _ = H.effects(kind, x, y, W, m)
        co, _ = H.effects(kind, x, y, W, ~m)
        ca, _ = H.effects(kind, x, y, W, np.ones_like(m))
        for lab, d in (('field300: all 300', ca), ('field300: the 12 deep institutions', cd), ('field300: the other 288', co), ('deep minus other 288', cd - co)):
            e, lo, hi = H.summ(d)
            rows.append(dict(measure=name, estimate=lab, est=e, lo=lo, hi=hi))
        if name in ref:
            e, lo, hi = ref[name]
            rows.append(dict(measure=name, estimate='12-school study (lab level)', est=e, lo=lo, hi=hi))
    return pd.DataFrame(rows)


def paper_agreement():
    """Flags of papers scored by both studies. The 12-school scores are keyed by atlas paper ids; the universe maps them to OpenAlex works."""
    snap = SC.snapshot_dir('2026-11-08')
    a = pd.read_parquet(snap / 'ai' / 'papers_v3.parquet', columns=['paper_id', 'flag_abstract', 'thr_abstract'])
    db = sqlite3.connect(f'file:{snap / "universe" / "universe.sqlite"}?mode=ro', uri=True)
    u = pd.read_sql('select paper_id, oa from papers', db)
    db.close()
    a = a.merge(u, on='paper_id')
    a = a[a['oa'].fillna('').str.contains(r'W\d+$', regex=True)].copy()
    a['work'] = a['oa'].str.extract(r'W(\d+)$')[0].astype('int64')
    sc, thr = A.abstract_scores()
    j = a.dropna(subset=['flag_abstract']).merge(sc, on='work')
    both = len(j)
    agree = float((j['flag_abstract'].astype(float) == j['flag']).mean()) if both else np.nan
    return pd.DataFrame([dict(papers_scored_by_both=both, flag_agreement=agree, deep_flag_rate=float(j['flag_abstract'].mean()) if both else np.nan,
                              field300_flag_rate=float(j['flag'].mean()) if both else np.nan, threshold_deep=float(a['thr_abstract'].dropna().iloc[0]), threshold_field300=thr)])


def main():
    tab, _ = A.out_dirs()
    e = estimates()
    e.to_csv(tab / 'f300_consistency_estimates.csv', index=False)
    p = paper_agreement()
    p.to_csv(tab / 'f300_consistency_papers.csv', index=False)
    print(json.dumps(p.iloc[0].to_dict()), flush=True)


if __name__ == '__main__':
    main()
