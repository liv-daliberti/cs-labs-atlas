"""Experiment B analysis: change in AI wording share from the arXiv v1 to the final version of the same paper.

  rv_analysis.py --detector v2 [--boot 500]     -> DATA/results/revision_<detector>_*.parquet (rv_report.py renders them)
Inputs: DATA/revision.sqlite (plan, texts), DATA/parts/<detector>/ (rv_score.py), the dose study's frame (school, field, first lab, topic).
Per version: ai_share = flagged passages / passages at the detector's threshold (1% passage FPR by design for v2), ai_strict = passages with p >= `strict` (v2: 0.5, whose
pre-ChatGPT floor is 0.19%); the passages between the two cuts are the 'abstain' band (flagged but not confident) and are reported apart; abstract flag = the legacy abstract
detector at its 1% threshold; kobak = Kobak et al. style words per 1,000 tokens of the abstract (detector-free).
Pair filters (exact pairing): same arXiv id, universe title compatible with the arXiv record title (match step), v1 title found on page 1, >= MIN_PASSAGES passages in both,
>= 1,000 body words in both, 8-gram shingle containment of v1 in final >= 0.2 (the same work), final version dated (margin stamp). Cells by version dates: v1 before / final after 1 Dec 2022.
Contrasts: mean change (final - v1) per cell, the pre_post cell against pre_pre (revision noise and the detector's false-positive floor: both versions are human text) with
coarsened-exact reweighting on school x v1-year bin x revision-lag bin, and a regression with school FE and controls; intervals from a cluster bootstrap over first labs.
"""
import argparse
import json
import re
import sqlite3
import zlib

import numpy as np
import pandas as pd

import rv_common as C

MIN_PASSAGES = 10
MIN_WORDS = 1000


def load_parts(det):
    d = C.DATA / 'parts' / det
    pas = pd.concat([pd.read_parquet(f) for f in sorted(d.glob('*.passages.parquet'))], ignore_index=True)
    ab = pd.concat([pd.read_parquet(f) for f in sorted(d.glob('*.abstracts.parquet'))], ignore_index=True).drop_duplicates(['arxiv_id', 'role'], keep='last')
    meta = json.load(open(d / 'detector.json'))
    return pas, ab, meta


def shingles(body, n=8):
    w = re.findall(r'[a-z0-9]+', body.lower())
    return {hash(' '.join(w[i:i + n])) for i in range(0, max(len(w) - n + 1, 0))}


def kobak_words():
    import dcommon as D
    p = D.P.HOMOGENIZATION_STUDY / 'lit' / 'kobak_reference' / 'kobak_2024_style_words.csv'
    return {w.strip().lower() for w in p.read_text().splitlines()[1:] if w.strip()}


def build_versions(det):
    import excess as E
    pas, ab, meta = load_parts(det)
    thr, strict = meta['threshold'], meta['strict']
    g = pas.assign(flag=pas['p'] >= thr, conf=pas['p'] >= strict).groupby(['arxiv_id', 'role'])
    v = g.agg(n_pass=('p', 'size'), ai_share=('flag', 'mean'), ai_strict=('conf', 'mean'), mean_p=('p', 'mean')).reset_index()
    v['abstain_share'] = v['ai_share'] - v['ai_strict']
    v = v.merge(ab[['arxiv_id', 'role', 'p_abs_v1', 'p_abs_det', 'body_words']], on=['arxiv_id', 'role'], how='outer')
    v['abs_flag_v1'] = np.where(v['p_abs_v1'].notna(), (v['p_abs_v1'] >= meta['v1_threshold']).astype(float), np.nan)
    db = sqlite3.connect(f'file:{C.DB}?mode=ro', uri=True)
    t = pd.read_sql('select arxiv_id, role, v, stamp_v, date, title_found, abstract, words from texts', db)
    plan = pd.read_sql('select * from plan', db)
    sh = {}
    for aid, role, body in db.execute('select arxiv_id, role, body from texts'):
        sh[(aid, role)] = shingles(zlib.decompress(body).decode('utf-8', 'ignore'))
    db.close()
    # stored copies (kind S): abstract (OpenAlex) and body from texts.sqlite
    tx = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    s_ids = dict(zip(plan.loc[plan['kind'] == 'S', 'paper_id'], plan.loc[plan['kind'] == 'S', 'arxiv_id']))
    ab_s = dict(tx.execute('select paper_id, abstract from abstracts'))
    srows = []
    for pid, body, words in tx.execute('select paper_id, body, words from fulltext where usable = 1'):
        if pid in s_ids:
            sh[(s_ids[pid], 'stored')] = shingles(zlib.decompress(body).decode('utf-8', 'ignore'))
            srows.append(dict(arxiv_id=s_ids[pid], role='stored', v=None, stamp_v=None, date=None, title_found=1, abstract=ab_s.get(pid), words=words))
    tx.close()
    t = pd.concat([t, pd.DataFrame(srows)], ignore_index=True)
    kw = kobak_words()
    t['kobak_abs'] = t['abstract'].map(lambda a: E.kobak_rate(a, kw) if a else np.nan)
    v = v.merge(t, on=['arxiv_id', 'role'], how='left')
    return v, plan, sh, meta


def pair_table(det):
    v, plan, sh, meta = build_versions(det)
    byrole = {r: v[v['role'] == r].set_index('arxiv_id') for r in ('v1', 'final', 'stored')}
    rows = []
    for pr in plan.itertuples():
        fin = 'final' if pr.kind == 'A' else 'stored'
        if pr.arxiv_id not in byrole['v1'].index or pr.arxiv_id not in byrole[fin].index:
            continue
        x, y = byrole['v1'].loc[pr.arxiv_id], byrole[fin].loc[pr.arxiv_id]
        s1, s2 = sh.get((pr.arxiv_id, 'v1'), set()), sh.get((pr.arxiv_id, fin), set())
        rows.append(dict(arxiv_id=pr.arxiv_id, kind=pr.kind, n_pass1=x['n_pass'], n_pass2=y['n_pass'], words1=x['words'], words2=y['words'], title_found1=x['title_found'],
                         date1=x['date'], date2=y['date'], stamp1=x['stamp_v'], stamp2=y['stamp_v'], v_final=y['v'],
                         ai1=x['ai_share'], ai2=y['ai_share'], st1=x['ai_strict'], st2=y['ai_strict'], ab1=x['abstain_share'], ab2=y['abstain_share'],
                         mp1=x['mean_p'], mp2=y['mean_p'], af1=x['abs_flag_v1'], af2=y['abs_flag_v1'], pa1=x['p_abs_det'], pa2=y['p_abs_det'],
                         ko1=x['kobak_abs'], ko2=y['kobak_abs'], contain=len(s1 & s2) / max(len(s1), 1), new_share=1 - len(s1 & s2) / max(len(s2), 1)))
    p = pd.DataFrame(rows).merge(plan[['arxiv_id', 'kind', 'paper_id', 'created', 'final_created_ub', 'title', 'pub_date']], on=['arxiv_id', 'kind'])
    return p, meta


def add_dates_and_filters(p):
    p = p.copy()
    p['d1'] = np.where(p['stamp1'].eq(1) & p['date1'].notna(), p['date1'], p['created'])
    a_date = np.where(p['stamp2'].eq(p['v_final']) & p['date2'].notna(), p['date2'], np.where(p['final_created_ub'].fillna('9') < C.CHATGPT, p['final_created_ub'], None))
    p['d2'] = np.where(p['kind'] == 'S', p['pub_date'], a_date)
    p['y1'] = p['d1'].str[:4].astype(float); p['y2'] = pd.to_numeric(pd.Series(p['d2']).str[:4], errors='coerce')
    p['lag_m'] = (pd.to_datetime(p['d2'], errors='coerce') - pd.to_datetime(p['d1'], errors='coerce')).dt.days / 30.4
    d2 = pd.Series(p['d2'])
    # the stored copy's text is written before its publication date: a 'post' final needs the publication date on or after 1 Jan 2023 (one month after ChatGPT)
    cut2 = np.where(p['kind'] == 'S', '2023-01-01', C.CHATGPT)
    p['cell'] = np.where(d2.isna(), None, np.where(p['d1'] < C.CHATGPT, 'pre', 'post') + '_' + np.where(d2.fillna('9') < cut2, 'pre', 'post'))
    p['final_in_gap'] = (p['kind'] == 'S') & (d2.fillna('9') >= C.CHATGPT) & (d2.fillna('9') < '2023-01-01')   # published in Dec 2022: dropped from the cells
    p.loc[p['final_in_gap'], 'cell'] = None
    ok = (p['n_pass1'] >= MIN_PASSAGES) & (p['n_pass2'] >= MIN_PASSAGES) & (p['words1'] >= MIN_WORDS) & (p['words2'] >= MIN_WORDS) & p['title_found1'].eq(1) \
        & (p['contain'] >= 0.2) & d2.notna() & p['cell'].notna() & (p['lag_m'] >= 0)
    p['valid'] = ok
    return p


def enrich(p):
    import dose_analysis as A
    df = A.build_frame()[['paper_id', 'school', 'field_grp', 'lab0', 'topic', 'trained_on']]
    p = p.merge(df, on='paper_id', how='left')
    p['trained_on'] = p['trained_on'].fillna(False).astype(bool)
    p['valid_pre'] = ~((p['kind'] == 'S') & p['trained_on'])   # a stored 2016-2021 copy the detector trained on is not an out-of-sample final
    p['dai'] = p['ai2'] - p['ai1']; p['dst'] = p['st2'] - p['st1']; p['dab'] = p['ab2'] - p['ab1']; p['dko'] = p['ko2'] - p['ko1']
    p['daf'] = p['af2'] - p['af1']; p['dpa'] = p['pa2'] - p['pa1']
    p['dwords'] = np.log(p['words2'] / p['words1'])
    p['lag_bin'] = pd.cut(p['lag_m'], [-1, 6, 12, 24, 1e9], labels=['<6', '6-12', '12-24', '>24']).astype(str)
    p['y1_bin'] = pd.cut(p['y1'], [2000, 2018, 2020, 2021, 2022, 2023, 2024, 2030], labels=['<=2018', '2019-20', '2021', '2022', '2023', '2024', '2025+']).astype(str)
    return p


def boot_mean(x, cl, B, seed=0):
    """Mean of x with a percentile interval from a cluster bootstrap over `cl`."""
    d = pd.DataFrame(dict(x=x.to_numpy(float), c=cl.astype(str).to_numpy())).dropna(subset=['x'])
    if len(d) < 5:
        return np.nan, np.nan, np.nan, len(d)
    g = d.groupby('c')['x'].agg(['sum', 'count'])
    rng = np.random.default_rng(seed)
    s, n = g['sum'].to_numpy(), g['count'].to_numpy()
    idx = rng.integers(0, len(g), (B, len(g)))
    bs = s[idx].sum(1) / np.maximum(n[idx].sum(1), 1)
    return float(d['x'].mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(d)


def cell_table(v, B):
    rows = []
    for outcome in ('dai', 'dst', 'dab', 'daf', 'dpa', 'dko'):
        for cell, g in list(v.groupby('cell')) + [('all', v)]:
            m, lo, hi, n = boot_mean(g[outcome], g['lab0'].fillna(g['arxiv_id']), B)
            rows.append(dict(outcome=outcome, cell=cell, mean=m, lo=lo, hi=hi, n=n, v1_mean={'dai': g['ai1'].mean(), 'dst': g['st1'].mean(), 'dab': g['ab1'].mean(),
                                                                                              'daf': g['af1'].mean(), 'dpa': g['pa1'].mean(), 'dko': g['ko1'].mean()}[outcome]))
    return pd.DataFrame(rows)


def matched_weights(v, treat='pre_post', ctrl='pre_pre', keys=('school', 'y1_bin', 'lag_bin')):
    """Coarsened exact weights: control pairs reweighted to the treated pairs' distribution over `keys` (strata with no control are dropped)."""
    t, c = v[v['cell'] == treat], v[v['cell'] == ctrl]
    kt = t.groupby(list(keys)).size(); kc = c.groupby(list(keys)).size()
    common = kt.index.intersection(kc.index)
    w = (kt[common] / kt[common].sum()) / (kc[common] / kc[common].sum())
    c = c.set_index(list(keys)).loc[common].copy(); c['w'] = w.reindex(c.index).to_numpy()
    t = t.set_index(list(keys)).loc[common].copy(); t['w'] = 1.0
    return t.reset_index(), c.reset_index(), int(kt[common].sum()), int(kt.sum())


def contrast(v, outcome, B, seed=0, treat='pre_post', ctrl='pre_pre', matched=True, keys=('school', 'y1_bin', 'lag_bin')):
    """treat minus control mean change, with a cluster bootstrap over labs (resampling labs of both cells together)."""
    if matched:
        t, c, kept, tot = matched_weights(v, treat, ctrl, keys)
    else:
        t, c = v[v['cell'] == treat].assign(w=1.0), v[v['cell'] == ctrl].assign(w=1.0)
        kept, tot = len(t), len(t)
    d = pd.concat([t.assign(tr=1), c.assign(tr=0)], ignore_index=True).dropna(subset=[outcome])
    d['cl'] = d['lab0'].fillna(d['arxiv_id']).astype(str)

    def est(x):
        a = x[x['tr'] == 1]; b = x[x['tr'] == 0]
        if a.empty or b.empty or b['w'].sum() == 0:
            return np.nan
        return np.average(a[outcome], weights=a['w']) - np.average(b[outcome], weights=b['w'])
    e = est(d)
    groups = {k: g for k, g in d.groupby('cl')}
    keys_l = list(groups)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(B):
        pick = rng.integers(0, len(keys_l), len(keys_l))
        x = pd.concat([groups[keys_l[i]] for i in pick], ignore_index=True)
        r = est(x)
        if np.isfinite(r):
            bs.append(r)
    lo, hi = np.percentile(bs, [2.5, 97.5]) if len(bs) > 20 else (np.nan, np.nan)
    return dict(outcome=outcome, treat=treat, ctrl=ctrl, matched=matched, diff=float(e), lo=float(lo), hi=float(hi), n_treat=int((d['tr'] == 1).sum()), n_ctrl=int((d['tr'] == 0).sum()),
                treat_kept=kept, treat_total=tot)


def regression(v, outcome):
    import dose_reg as R
    d = v[v['cell'].isin(['pre_pre', 'pre_post', 'post_post'])].copy()
    d['pre_post'] = (d['cell'] == 'pre_post').astype(float); d['post_post'] = (d['cell'] == 'post_post').astype(float)
    rows = []
    for name, fe, ctl in (('cells', [], []), ('school_fe', ['school'], ['lag_m', 'dwords']), ('school_field_fe', ['school', 'field_grp'], ['lag_m', 'dwords']),
                          ('start_level', ['school', 'field_grp'], ['lag_m', 'dwords', 'ai1'])):
        dd = d.copy(); dd['field_grp'] = dd['field_grp'].fillna('Unknown')
        r = R.fit(dd, outcome, ['pre_post', 'post_post'], controls=ctl, fe=fe, cluster='lab0' if dd['lab0'].notna().all() else None)
        for k in ('pre_post', 'post_post'):
            rows.append(dict(outcome=outcome, spec=name, term=k, beta=r['coefs'].get(k, np.nan), lo=r['coefs'].get(k, np.nan) - 1.96 * r['ses'].get(k, np.nan),
                             hi=r['coefs'].get(k, np.nan) + 1.96 * r['ses'].get(k, np.nan), n=r['n'], clusters=r['clusters']))
    return pd.DataFrame(rows)


def pivot_table(v):
    g = v.groupby(['y1', 'y2'])['dai'].agg(['mean', 'count']).reset_index()
    return g


def added_rates(v, B):
    """Share of pairs whose v1 looks human (ai_strict < 5%... via ai_share < 0.05) and whose final has >= 25% flagged passages ('AI added in revision')."""
    rows = []
    for cell, g in v.groupby('cell'):
        for name, flag in (('final>=25% flagged, v1<5%', (g['ai2'] >= 0.25) & (g['ai1'] < 0.05)), ('final>=25% strict, v1<5% strict', (g['st2'] >= 0.25) & (g['st1'] < 0.05))):
            m, lo, hi, n = boot_mean(flag.astype(float), g['lab0'].fillna(g['arxiv_id']), B)
            rows.append(dict(cell=cell, rule=name, share=m, lo=lo, hi=hi, n=n))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detector', default='v2', choices=['v2', 'v3'])
    ap.add_argument('--boot', type=int, default=500)
    a = ap.parse_args()
    C.RESULTS.mkdir(parents=True, exist_ok=True)
    p, meta = pair_table(a.detector)
    p = enrich(add_dates_and_filters(p))
    pref = C.RESULTS / f'revision_{a.detector}'
    p.to_parquet(f'{pref}_pairs.parquet', index=False)
    funnel = {}
    for kind in ('S', 'A'):
        k = p[p['kind'] == kind]
        f = dict(pairs_scored=len(k), title_found_v1=int(k['title_found1'].eq(1).sum()), same_work=int((k['contain'] >= 0.2).sum()), dated=int(k['d2'].notna().sum()), valid=int(k['valid'].sum()))
        v = k[k['valid'] & k['valid_pre']].copy()
        v = v[(v['y1'] <= C.LAST_YEAR) & (v['y2'] <= C.LAST_YEAR)].copy()   # owner rule: no 2026
        f['valid_to_2025'] = len(v); f['cells'] = v['cell'].value_counts().to_dict(); funnel[kind] = f
        cell_table(v, a.boot).assign(kind=kind).to_parquet(f'{pref}_{kind}_cells.parquet', index=False)
        rows = []
        for outcome in ('dai', 'dst', 'dab', 'daf', 'dpa', 'dko'):
            for matched in (False, True):
                for treat, ctrl in (('pre_post', 'pre_pre'), ('post_post', 'pre_pre'), ('pre_post', 'post_post')):
                    if (v['cell'] == treat).sum() >= 20 and (v['cell'] == ctrl).sum() >= 20:
                        rows.append(contrast(v, outcome, a.boot, treat=treat, ctrl=ctrl, matched=matched))
        pd.DataFrame(rows).assign(kind=kind).to_parquet(f'{pref}_{kind}_contrasts.parquet', index=False)
        if v['cell'].nunique() >= 2:
            pd.concat([regression(v, o) for o in ('dai', 'dst', 'dko')]).assign(kind=kind).to_parquet(f'{pref}_{kind}_regression.parquet', index=False)
        pivot_table(v).assign(kind=kind).to_parquet(f'{pref}_{kind}_pivot.parquet', index=False)
        added_rates(v, a.boot).assign(kind=kind).to_parquet(f'{pref}_{kind}_added.parquet', index=False)
    json.dump(dict(funnel=funnel, detector=meta), open(f'{pref}_funnel.json', 'w'), default=str, indent=1)
    C.log(**{k: v for k, v in funnel.items()})


if __name__ == '__main__':
    main()
