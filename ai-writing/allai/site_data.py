"""Small JSON files for the 'all papers AI-written' page, from the analysis tables (schema: ai-writing/diversity/site-data/all-ai/README.md).

  site_data.py build [--out DIR]    default DIR = ai-writing/diversity/site-data/all-ai (in this checkout)
reads EMB/allai/results/*.parquet and preservation_<style>.json; writes methods.json, overall.json, schools.json, trend.json, novelty.json, labs.json,
preservation.json. Numbers are rounded to 4 significant decimals; NaN becomes null.
"""
import argparse
import glob
import json
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
import ecommon as C  # noqa: E402

RES = C.EMB / 'allai' / 'results'
MODELS = ['specter2_proximity', 'specter2_base', 'scincl', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']
MEASURE_NAMES = {'vendi': 'Vendi score (effective number of distinct papers)', 'dispersion': 'dispersion (mean distance from the centroid)',
                 'pairwise': 'mean pairwise cosine distance', 'H_bt': 'topic entropy over BERTopic topics (bits)',
                 'H_km': 'topic entropy over 100 k-means clusters (bits)', 'H_bt2000': 'topic entropy, BERTopic topics, 2,000 papers per year (bits)',
                 'H_km2000': 'topic entropy, k-means, 2,000 papers per year (bits)'}


def num(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), 5)


def rows(df, cols):
    return [{c: (num(v) if isinstance(v, float) else (int(v) if hasattr(v, 'item') and isinstance(v.item(), int) else v)) for c, v in zip(cols, r)}
            for r in df[cols].itertuples(index=False, name=None)]


def load(prefix):
    fs = sorted(glob.glob(str(RES / f'{prefix}_polish_*.parquet')))
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    yr, chg, labs = load('geom_year'), load('geom_change'), load('geom_labsummary')
    ntr, nco = load('novelty_trend'), load('novelty_contrast')
    ycols = ['year', 'orig', 'orig_lo', 'orig_hi', 'ai', 'ai_lo', 'ai_hi', 'gap', 'gap_lo', 'gap_hi']
    overall = {'scope': 'all papers; each point is a size-matched draw (1,000 papers; 2,000 for the *2000 entropies), interval = 95%, bootstrap over labs',
               'measures': {}}
    for meas, g in yr[yr['scope'] == 'all'].groupby('measure'):
        overall['measures'][meas] = {'label': MEASURE_NAMES.get(meas, meas), 'models': {m: rows(h.sort_values('year'), ycols) for m, h in g.groupby('model')}}
    schools = {'scope': 'each school, 500 papers per draw; intervals as overall.json', 'schools': {}}
    for (sid, meas), g in yr[yr['scope'] == 'school'].groupby(['scope_id', 'measure']):
        schools['schools'].setdefault(sid, {})[meas] = {m: rows(h.sort_values('year'), ycols) for m, h in g.groupby('model')}
    ccols = ['orig', 'orig_lo', 'orig_hi', 'ai', 'ai_lo', 'ai_hi', 'gap', 'gap_lo', 'gap_hi']
    trend = {'definition': 'mean of 2023-2026 minus mean of 2016-2022; orig = original abstracts, ai = every abstract rewritten, gap = orig - ai (the part of the change due to wording)', 'rows': []}
    for r in chg.itertuples(index=False):
        trend['rows'].append(dict(model=r.model, scope=r.scope, scope_id=r.scope_id, measure=r.measure, **{c: num(getattr(r, c)) for c in ccols}))
    lcols = ['orig_change', 'orig_lo', 'orig_hi', 'ai_change', 'ai_lo', 'ai_hi', 'gap_change', 'gap_lo', 'gap_hi', 'orig_pre', 'orig_post', 'ai_pre', 'ai_post']
    labs_out = {'definition': 'labs with >= 20 papers in both periods (pre 2016-2022, post 2023-2026); 20-paper draws; change = post - pre averaged over labs, 95% interval by bootstrap over labs',
                'rows': [dict(model=r.model, measure=r.measure, scope=r.scope, labs=int(r.labs), **{c: num(getattr(r, c)) for c in lcols}) for r in labs.itertuples(index=False)]}
    nov = {'definition': 'novelty = 1 - mean cosine to the 5 nearest papers of the previous k years (size-matched pool of 2,000), paired per paper; trend by year and post (2023-2026) minus pre (2017-2022)',
           'trend': [], 'contrast': []}
    if len(ntr):
        t = ntr[(ntr['measure'] == 'nov_nn_cap') & (ntr['scope'].isin(['all', 'school'])) & (ntr['k'] == 3)]
        for r in t.itertuples(index=False):
            nov['trend'].append(dict(model=r.model, scope=r.scope, scope_id=r.scope_id, k=int(r.k), year=int(r.year), **{c: num(getattr(r, c)) for c in ycols[1:]}))
        ncols = ['orig_change', 'orig_lo', 'orig_hi', 'ai_change', 'ai_lo', 'ai_hi', 'gap_change', 'gap_lo', 'gap_hi']
        for r in nco.itertuples(index=False):
            nov['contrast'].append(dict(model=r.model, scope=r.scope, scope_id=r.scope_id, k=int(r.k), measure=r.measure, **{c: num(getattr(r, c)) for c in ncols}))
    pres = {s: json.load(open(RES / f'preservation_{s}.json')) for s in ('polish', 'paraphrase') if (RES / f'preservation_{s}.json').exists()}
    methods = json.load(open(HERE / 'site_methods.json'))
    for name, obj in (('methods', methods), ('overall', overall), ('schools', schools), ('trend', trend), ('labs', labs_out), ('novelty', nov), ('preservation', pres)):
        (out / f'{name}.json').write_text(json.dumps(obj, separators=(',', ':'), ensure_ascii=False))
        C.log(wrote=name, bytes=(out / f'{name}.json').stat().st_size)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['build']); ap.add_argument('--out', default=str(HERE.parent / 'diversity' / 'site-data' / 'all-ai'))
    build(Path(ap.parse_args().out))
