"""Paper-level dose designs (Part C): AI exposure against embedding novelty, post-2022 with the 2016-2021 placebo.

  dose_analysis.py paper --model M --kind abstract|fulltext [--exposure ai_share ...]    one (model, kind): every design, scope, k
-> AI_SCORES/results/paper_<model>_<kind>.parquet   one row per fit: design, exposure, period, scope, k, measure, beta/se/lo/hi (per unit of exposure,
   i.e. 0 -> 1 for a share), n, clusters, y_sd, plus the dose-bin coefficients
Outcome: nov_nn_cap (size-matched mean cosine distance to the 5 nearest earlier papers of the scope, previous k years) and nov_max_cap; scopes all,
school, dept, lab (embeddings/novelty_run.py tables). Exposure: ai_share (the dose; full-text papers), flag_abstract and p_ai_abstract (all papers
with an abstract), kobak_abs (detector-free).
Designs (every one clusters by the paper's first lab):
  raw       year FE
  pooled    year + home-school + OpenAlex primary-topic FE, controls: log team size, venue type, open-access status
  topicyear primary-topic x year FE (topic-matched: papers of the same topic and year), the same controls, school FE
  nollm     pooled on papers that are not about LLMs (title/abstract regex)
  withinlab lab x year FE (the same lab's high- against low-AI papers in the same year)
  author    first-author FE + year FE (the writer held fixed; OpenAlex author ids)
  bins      pooled with dose-bin dummies (0-5% is the base)
Periods: post (2023-2026) and pre (2017-2021, the placebo: there the "dose" is detector noise).
"""
import argparse
import json
import re
import sqlite3
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import dcommon as D
import dose_data as DD
import dose_reg as R
import dose_stats as S
import dose_validate as V

LLM_RE = re.compile(r'large language model|\bLLMs?\b|\bGPT[- ]?\d?|ChatGPT|language model|foundation model|in-context|prompt(?:ing)?\b|instruction[- ]tun', re.I)
CONTROLS = ['team_log', 'venue_type', 'oa_status']
MIN_REF = {'all': 100, 'school': 100, 'dept': 20, 'lab': 5}
MEASURES = ('nov_nn_cap', 'nov_max_cap')
PERIODS = {'post': range(2023, 2027), 'pre': range(2017, 2022)}
SCOPES = ('all', 'school', 'dept', 'lab')
KS = (1, 3, 5)
BIN_LABELS = ('5-25%', '25-50%', '50-100%')


def llm_flags(papers):
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True)
    ab = dict(db.execute('select paper_id, title || " " || abstract from abstracts'))
    db.close()
    return papers['paper_id'].map(lambda p: bool(LLM_RE.search((ab.get(p) or ''))))


def build_frame():
    df = DD.paper_table()
    _, lp = DD.universe()
    first = lp.drop_duplicates('paper_id').set_index('paper_id')['lab_id']
    df['lab0'] = df['paper_id'].map(first)
    df['school'] = df['home_school']
    df['field_grp'] = V.field_groups(df)
    df['team_log'] = np.log(df['team_size'].clip(lower=1)) if 'team_size' in df else np.nan
    st = df['source_type'] if 'source_type' in df else pd.Series(index=df.index, dtype=object)
    df['venue_type'] = st.fillna('unknown').astype(str)
    df['oa_status'] = (df['oa_status'] if 'oa_status' in df else pd.Series('unknown', index=df.index)).fillna('unknown').astype(str)
    df['topic'] = df['oa_topic'].fillna('none')
    df['topic_year'] = df['topic'] + '|' + df['year'].astype(str)
    df['llm_topic'] = llm_flags(df)
    if 'author_ids' in df:
        df['first_author'] = df['author_ids'].map(lambda s: (json.loads(s)[0] if isinstance(s, str) and s and json.loads(s) else '') or None)
    else:
        df['first_author'] = None
    df['dose_bin'] = S.dose_bins(df['ai_share'].fillna(-1).clip(lower=0)).astype(object).where(df['ai_share'].notna())
    for b in BIN_LABELS:
        df[f'bin_{b}'] = (df['dose_bin'] == b).astype(float)
    return df


def novelty_rows(model, kind, scope, ks=KS):
    import pyarrow.dataset as pds
    p = D.EMB / 'results' / f'novelty_{model}_{kind}.parquet'
    if not p.exists():
        return None
    cols = ['scope_id', 'paper_id', 'k', 'n_ref', *MEASURES]
    t = pds.dataset(p).to_table(columns=cols, filter=(pds.field('scope') == scope) & pds.field('k').isin(list(ks))).to_pandas()
    return t[t['n_ref'] >= MIN_REF[scope]]


def fit_row(d, y, x, design, extra, **kw):
    r = R.fit(d, y, x, **kw)
    out = dict(design=design, n=r['n'], clusters=r['clusters'], beta=r['beta'], se=r['se'], lo=r['lo'], hi=r['hi'], y_sd=float(d[y].std()) if len(d) > 1 else np.nan, **extra)
    return out, r


def designs_for(d, y, expo, scope, extra):
    rows = []
    d = d.copy()
    d['lab_year'] = np.where(d['scope_id'].astype(str).str.startswith('atl:l:'), d['scope_id'].astype(str), d['lab0'].astype(str)) + '|' + d['year'].astype(str)
    d['_unit'] = d['lab0']
    kw = dict(cluster='lab0')
    rows.append(fit_row(d, y, expo, 'raw', extra, fe=['year'], **kw)[0])
    rows.append(fit_row(d, y, expo, 'pooled', extra, controls=CONTROLS, fe=['year', 'school', 'topic'], **kw)[0])
    rows.append(fit_row(d, y, expo, 'topicyear', extra, controls=CONTROLS, fe=['topic_year', 'school'], **kw)[0])
    rows.append(fit_row(d[~d['llm_topic']], y, expo, 'nollm', extra, controls=CONTROLS, fe=['year', 'school', 'topic'], **kw)[0])
    rows.append(fit_row(d, y, expo, 'withinlab', extra, controls=CONTROLS, fe=['lab_year'], **kw)[0])
    rows.append(fit_row(d.dropna(subset=['first_author']), y, expo, 'author', extra, controls=CONTROLS, fe=['year', 'first_author'], **kw)[0])
    if expo == 'ai_share':
        row, r = fit_row(d, y, [f'bin_{b}' for b in BIN_LABELS], 'bins', extra, controls=CONTROLS, fe=['year', 'school', 'topic'], **kw)
        for b in BIN_LABELS:
            rows.append(dict(row, design=f'bin {b}', beta=r['coefs'].get(f'bin_{b}', np.nan), se=r['ses'].get(f'bin_{b}', np.nan),
                             lo=r['coefs'].get(f'bin_{b}', np.nan) - 1.96 * r['ses'].get(f'bin_{b}', np.nan),
                             hi=r['coefs'].get(f'bin_{b}', np.nan) + 1.96 * r['ses'].get(f'bin_{b}', np.nan)))
    return rows


_FRAME = None


def run_one(args):
    model, kind, exposures, scopes = args
    df = _FRAME
    rows = []
    for scope in scopes:
        nov = novelty_rows(model, kind, scope)
        if nov is None:
            continue
        base = df.merge(nov, on='paper_id')
        for k in KS:
            bk = base[base['k'] == k]
            for period, years in PERIODS.items():
                bp = bk[bk['year'].isin(years)]
                for expo in exposures:
                    be = bp[bp[expo].notna()]
                    if len(be) < 200:
                        continue
                    for y in MEASURES:
                        extra = dict(model=model, kind=kind, scope=scope, k=k, measure=y, exposure=expo, period=period)
                        rows += designs_for(be[be[y].notna()], y, expo, scope, extra)
    out = pd.DataFrame(rows)
    D.RESULTS.mkdir(parents=True, exist_ok=True)
    out.to_parquet(D.RESULTS / f'paper_{model}_{kind}.parquet', index=False)
    D.log(model=model, kind=kind, fits=len(out))
    return len(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['paper'])
    ap.add_argument('--model', action='append')
    ap.add_argument('--kind', default='abstract')
    ap.add_argument('--exposure', action='append')
    ap.add_argument('--scope', action='append')
    ap.add_argument('-j', type=int, default=4)
    a = ap.parse_args()
    from models import MODELS, ORDER
    global _FRAME
    _FRAME = build_frame()
    jobs = []
    for m in a.model or ORDER:
        for kind in ([a.kind] if a.kind != 'both' else ['abstract', 'fulltext']):
            if kind in MODELS[m]['kinds']:
                jobs.append((m, kind, a.exposure or ['ai_share', 'flag_abstract'], a.scope or list(SCOPES)))
    with ProcessPoolExecutor(min(a.j, len(jobs))) as ex:
        list(ex.map(run_one, jobs))


if __name__ == '__main__':
    main()
