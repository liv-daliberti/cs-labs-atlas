"""Build the detector-v3 score container (CPU, owner decision 2026-11-05: "rescore everything with v3"). The v2 container is left untouched.

  AI_SCORES_V3_DIR=<dir> dose_build_v3.py [--condition main|main_appendix]
Writes <dir>/ai_scores.sqlite (+ papers.parquet, mech -> the v2 mech embeddings, results/liang_alpha.parquet copied) with the SAME schema as dose_build.py,
so the dose, ai_pages, ai_vs_not and lab scripts run unchanged against it with  CS_ATLAS_AI_SCORES=<dir> AI_DETECTOR=v3:
  ai_share / n_passages / n_flagged  main-body passages (condition `main`, the headline) or main + appendix, abstained passages excluded; NULL when none scored or the main
                                     body is under 1,000 words (`usable`)
  passages(paper_id, pidx, words, p) p = the detector-v3 score z (flag = z >= thr_z); the abstained passages are not stored
  extra papers columns  abstained_share, ai_share_main_appendix, trained_on_v3 (training-split papers: kept out of every false-positive/placebo floor), n_abstained
Abstract-level columns (p_ai_abstract, flag_abstract: the v1 abstract detector; kobak_*) are carried over unchanged: v3 scores body passages only.
v3 shares are NOT comparable with v2's (threshold 0.3% vs 1%, abstain rule): never mix the two containers in one series.
"""
import argparse
import glob
import json
import os
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

import dcommon as D

V3 = D.MAIN_AIW / 'detector_v3' / 'results'
OUT = Path(os.environ.get('AI_SCORES_V3_DIR') or (D.P.CODE / 'ai-writing' / 'data' / 'ai-scores-v3'))


def main(condition):
    op = json.load(open(V3 / 'operating_point.json'))
    pa = pd.read_parquet(V3 / 'paper_ai_v3.parquet')
    v2 = sqlite3.connect(f"file:{D.P.CODE / 'ai-writing' / 'data' / 'ai-scores' / 'ai_scores.sqlite'}?mode=ro", uri=True)
    old = pd.read_sql('select * from papers', v2)
    v2.close()
    keep = ['paper_id', 'home_school', 'year', 'abs_hash', 'p_ai_abstract', 'p_v2_abstract', 'flag_abstract', 'kobak_abs', 'kobak_ft', 'thr_abstract']
    df = old[keep].copy()
    pa = pa.drop_duplicates('paper_id')
    sec_main = condition == 'main'
    n_sc = pa['n_main_scored'] if sec_main else pa['n_scored']
    n_fl = pa['n_main_flagged'] if sec_main else pa['n_main_flagged'] + pa['n_app_flagged']
    ok = pa['usable'] & (n_sc > 0)
    t = pd.DataFrame({'paper_id': pa['paper_id'], 'ft_hash': pa['key'], 'text_kind': pa['kind'], 'n_passages': n_sc.where(ok), 'n_flagged': n_fl.where(ok),
                      'ai_share': (n_fl / n_sc).where(ok), 'abstained_share': pa['abstained_share'], 'n_abstained': pa['n_abstained'],
                      'ai_share_main_appendix': pa['ai_share_main_appendix'], 'ai_share_main': pa['ai_share_main'].where(pa['usable']),
                      'trained_on_v3': pa['trained_on_v3'], 'split_v3': pa['split_v3'], 'appendix_found': pa['appendix_found']})
    t['ai_any'] = np.where(t['ai_share'].notna(), (t['n_flagged'] > 0).astype(float), np.nan)
    df = df.merge(t, on='paper_id', how='left')
    df['mean_p_par'] = np.nan
    df['ai_share_cal'] = np.nan
    df['body_words'] = df['paper_id'].map(old.set_index('paper_id')['body_words'])
    df['detector_version'] = 'v3-' + condition
    df['thr_paragraph'] = op['thr_z']
    fs = sorted(glob.glob(str(V3 / 'sections-all' / 'scores-*.sqlite')))
    parts = []
    for f in fs:
        d = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        parts.append(pd.read_sql("select paper_id, i as pidx, section, words, z as p from scores where abstain = 0", d))
        d.close()
    ps = pd.concat(parts, ignore_index=True)
    if sec_main:
        ps = ps[ps['section'] == 'main']
    ps = ps[ps['paper_id'].isin(set(df.loc[df['ai_share'].notna(), 'paper_id']))].drop(columns='section')
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = D.local_tmp() / f'ai_scores_v3-{os.getpid()}.sqlite'
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    df.to_sql('papers', db, index=False)
    ps.to_sql('passages', db, index=False, chunksize=200000)
    pd.DataFrame([('paragraph_v3', 'all', op['thr_z'], 'detector_v3/results/operating_point.json: z threshold at 0.3% calibration FPR, abstain < 100 words or midcap > cut')],
                 columns=['name', 'group', 'value', 'note']).to_sql('thresholds', db, index=False)
    pd.DataFrame([('built', D.now()), ('detector_version', 'v3-' + condition), ('papers', len(df)), ('fulltexts_scored', int(df['ai_share'].notna().sum())), ('passages', len(ps)),
                  ('test_fpr', json.dumps(op['test_fpr']))], columns=['key', 'value']).astype(str).to_sql('meta', db, index=False)
    db.execute('create index passages_paper on passages(paper_id)')
    db.execute('create unique index papers_id on papers(paper_id)')
    db.commit(); db.close()
    shutil.copyfile(tmp, OUT / 'ai_scores.sqlite'); tmp.unlink()
    df.to_parquet(OUT / 'papers.parquet', index=False)
    v2dir = D.P.CODE / 'ai-writing' / 'data' / 'ai-scores'
    (OUT / 'results').mkdir(exist_ok=True)
    if not (OUT / 'mech').exists():
        (OUT / 'mech').symlink_to(v2dir / 'mech')      # generator-text embeddings: detector-free
    shutil.copyfile(v2dir / 'results' / 'liang_alpha.parquet', OUT / 'results' / 'liang_alpha.parquet')
    D.log(built=str(OUT), papers=len(df), fulltexts=int(df['ai_share'].notna().sum()), passages=len(ps), condition=condition)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--condition', default='main', choices=['main', 'main_appendix'])
    main(ap.parse_args().condition)
