"""Inputs of lab_ai_score.py for detector v3 (owner 2026-11-05): passages, main-body tags and targets, from the v3 section scores. Run once, then set the config's detector to v3.

  lab_ai_v3_inputs.py [--out DIR]     default DIR = <v3 container>/results/lab_ai (AI_SCORES_V3_DIR, else ai-writing/data/ai-scores-v3)
  passages_v3.parquet   paper_id, pidx, words, p: the MAIN-body passages that were scored (abstained passages are not stored: they are neither flagged nor counted); p = the v3 score z,
                        flag = z >= thr_z (operating_point.json, the 0.3% calibration threshold). pidx = the section container's passage index `i`.
  tags-v3.parquet       paper_id, error, main_words, main_pidx (comma-joined scored main passages), n_main (scored), n_old, appendix_found (the columns lab_ai_score.load_tags reads)
  targets-v3.parquet    paper_id, year, home_school, trained_on (= trained_on_v3: the detector-v3 training split, kept out of the floor and the out-of-sample placebo)
"""
import argparse
import glob
import os
import sqlite3
from pathlib import Path

import pandas as pd

import dcommon as D
import v3ids

V3 = D.MAIN_AIW / 'detector_v3'


def main_words(back):
    rows = []
    for path in [D.MAIN_AIW / 'data' / 'sections' / 'sections.sqlite'] + sorted(glob.glob(str(V3 / 'data' / 'sections_extra' / 'shard-*.sqlite'))):
        d = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        rows += d.execute('select paper_id, main_words from sections').fetchall()
        d.close()
    df = pd.DataFrame(rows, columns=['paper_id', 'main_words'])
    df['paper_id'] = df['paper_id'].map(back)
    return df[df['paper_id'].notna()].drop_duplicates('paper_id')


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    pa = v3ids.v3_table()      # universe ids (the extra-shard papers are keyed otherwise in paper_ai_v3), year and school filled in
    back = dict(zip(pa['paper_id_v3'], pa['paper_id']))
    parts = []
    for f in sorted(glob.glob(str(V3 / 'results' / 'sections-all' / 'scores-*.sqlite'))):
        d = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        parts.append(pd.read_sql("select paper_id, i as pidx, words, z as p from scores where abstain = 0 and section = 'main'", d))
        d.close()
    ps = pd.concat(parts, ignore_index=True)
    ps['paper_id'] = ps['paper_id'].map(back)
    ps = ps[ps['paper_id'].notna()]
    ps.to_parquet(out / 'passages_v3.parquet', index=False)
    g = ps.groupby('paper_id')['pidx'].agg(main_pidx=lambda s: ','.join(map(str, sorted(s))), n_main='size').reset_index()
    t = pa[['paper_id', 'appendix_found', 'split_error']].merge(main_words(back), on='paper_id', how='left').merge(g, on='paper_id', how='left')
    t['error'] = t['split_error']
    t['main_pidx'] = t['main_pidx'].fillna('')
    t['n_main'] = t['n_main'].fillna(0).astype(int)
    t['n_old'] = t['n_main']
    t[['paper_id', 'error', 'main_words', 'main_pidx', 'n_main', 'n_old', 'appendix_found']].to_parquet(out / 'tags-v3.parquet', index=False)
    tg = pa[['paper_id', 'year', 'home_school', 'trained_on_v3']].rename(columns={'trained_on_v3': 'trained_on'})
    tg.to_parquet(out / 'targets-v3.parquet', index=False)
    D.log(out=str(out), passages=len(ps), papers=len(t), with_main=int((t['n_main'] > 0).sum()))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    base = Path(os.environ.get('AI_SCORES_V3_DIR') or (D.P.CODE / 'ai-writing' / 'data' / 'ai-scores-v3'))
    ap.add_argument('--out', default=str(base / 'results' / 'lab_ai'))
    run(Path(ap.parse_args().out))
