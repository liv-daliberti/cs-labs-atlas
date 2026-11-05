"""Build the per-paper score container from the scoring parts (CPU).

  dose_build.py                      parts + kobak -> AI_SCORES/ai_scores.sqlite (and papers.parquet next to it)
Container tables (one sqlite file, no per-paper files):
  papers   paper_id PK (atlas id, as embeddings/universe.sqlite), home_school, year,
           p_ai_abstract  v1 detector on `title | abstract` (flag_abstract at its 1% threshold), p_v2_abstract (v2 model on the abstract alone; robustness only),
           ai_share  share of the body's passages with p >= thr_par (the dose), mean_p_par, ai_any, n_passages, n_flagged, body_words, text_kind,
           kobak_abs, kobak_ft (excess style words per 1,000 tokens), abs_hash, ft_hash,
           ai_share_cal  the dose with a group-recalibrated threshold (school and broad field, from dose_validate.py), NULL until that has run
  passages paper_id, pidx, words, p        every scored passage, so thresholds can be re-cut without re-scoring
  thresholds  name, group, value, note     the detector thresholds in use and any recalibrated group threshold
  meta     key, value                      detector versions, precision, built time, counts
Paper-level definitions follow ai-writing/detector_v2/REPORT.md: ai_share = flagged passages / passages, ai_any = at least one flagged passage.
"""
import os
import sqlite3

import numpy as np
import pandas as pd

import dcommon as D


def read_parts(kind, suffix=''):
    fs = sorted((D.PARTS / kind).glob(f'*{suffix}.parquet'))
    fs = [f for f in fs if not f.name.startswith('.tmp-')]
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def paper_dose(passages, thr):
    """Per-paper dose from passage scores: n_passages, n_flagged, ai_share, mean_p_par, ai_any."""
    flag = passages['p'].to_numpy() >= thr
    g = passages.assign(flag=flag).groupby('paper_id', sort=False)
    out = g.agg(n_passages=('p', 'size'), n_flagged=('flag', 'sum'), mean_p_par=('p', 'mean'))
    out['ai_share'] = out['n_flagged'] / out['n_passages']
    out['ai_any'] = (out['n_flagged'] > 0).astype(int)
    return out.reset_index()


def build(thr_par=None, thr_abs=None):
    thr_par = thr_par or D.V2_THRESHOLD
    thr_abs = thr_abs or D.V1_THRESHOLD
    ab = read_parts('abstract').drop_duplicates('paper_id', keep='last')
    pp = read_parts('fulltext', '.papers').drop_duplicates('paper_id', keep='last')
    ps = read_parts('fulltext', '.passages')
    ps = ps[ps['paper_id'].isin(set(pp['paper_id']))].drop_duplicates(['paper_id', 'pidx'], keep='last')
    uni = sqlite3.connect(f'file:{D.UNIVERSE_DB}?mode=ro', uri=True)
    papers = pd.read_sql('select paper_id, home_school, year from papers', uni)
    uni.close()
    dose = paper_dose(ps, thr_par) if len(ps) else pd.DataFrame(columns=['paper_id'])
    df = (papers.merge(ab.rename(columns={'p_v1': 'p_ai_abstract', 'p_v2': 'p_v2_abstract', 'text_hash': 'abs_hash'}), on='paper_id', how='left')
          .merge(pp.rename(columns={'text_hash': 'ft_hash', 'kind': 'text_kind', 'n_passages': 'n_passages_part'}), on='paper_id', how='left')
          .merge(dose, on='paper_id', how='left'))
    df['flag_abstract'] = np.where(df['p_ai_abstract'].notna(), (df['p_ai_abstract'] >= thr_abs).astype(float), np.nan)
    kb = D.PARTS / 'kobak.parquet'
    if kb.exists():
        df = df.merge(pd.read_parquet(kb)[['paper_id', 'kobak_abs', 'kobak_ft']], on='paper_id', how='left')
    df['ai_share_cal'] = np.nan
    df['detector_version'] = D.DETECTOR_VERSION
    df['thr_abstract'] = thr_abs
    df['thr_paragraph'] = thr_par
    df = df.drop(columns=['n_passages_part'])
    D.SCORES.mkdir(parents=True, exist_ok=True)
    tmp = D.local_tmp() / f'ai_scores-{os.getpid()}.sqlite'      # sqlite journals fail on NFS (disk I/O error, 2026-11-04): build locally, copy once
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    df.to_sql('papers', db, index=False)
    ps.to_sql('passages', db, index=False, chunksize=200000)
    pd.DataFrame([('abstract_v1', 'all', thr_abs, 'detector/all/metrics.json: 1% of validation human abstracts (test FPR 1.5%)'),
                  ('paragraph_v2', 'all', thr_par, 'detector_v2/results/all/metrics.json: 99th percentile of 59,838 calibration passages')],
                 columns=['name', 'group', 'value', 'note']).to_sql('thresholds', db, index=False)
    pd.DataFrame([('built', D.now()), ('detector_version', D.DETECTOR_VERSION), ('papers', len(df)), ('abstracts_scored', int(df['p_ai_abstract'].notna().sum())),
                  ('fulltexts_scored', int(df['ai_share'].notna().sum())), ('passages', len(ps))], columns=['key', 'value']).astype(str).to_sql('meta', db, index=False)
    db.execute('create index passages_paper on passages(paper_id)')
    db.execute('create unique index papers_id on papers(paper_id)')
    db.commit(); db.close()
    D.publish(tmp, D.DB)
    df.to_parquet(D.SCORES / 'papers.parquet', index=False)
    D.log(built=str(D.DB), papers=len(df), abstracts=int(df['p_ai_abstract'].notna().sum()), fulltexts=int(df['ai_share'].notna().sum()), passages=len(ps))


if __name__ == '__main__':
    build()
