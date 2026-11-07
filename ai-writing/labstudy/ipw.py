"""Inverse-probability weights for full-text selection (analysis 3).

  ipw.py fit        P(scored full text | year, school, venue type, OA status, publisher, field, team size, citations, ...) on every lab paper
                    -> OUT/ipw/ipw_weights.parquet (reusable, keyed by paper_id), OUT/ipw/ipw_meta.json, OUT/ipw/balance_*.parquet, propensity_diag.parquet
Selection indicator S: `has_ft` (a usable local full text that the passage detector scored: ai_share not null). Second table columns for the abstract
(`has_abstract`; p_abs, w_abs) because the abstract-based analyses cover 93% of papers but also with a selection.
Model: cross-fitted (K folds, so a paper's propensity never comes from a model that saw it) gradient boosting (HistGradientBoosting, categorical features) and a
one-hot logistic regression with year x school interactions; the one with the smaller maximum |SMD| after weighting is `model` of the table (both are kept as
columns p_ft_gbm / p_ft_logit). Stabilised weights w = P(S=1) / p, trimmed at the configured quantiles of the selected papers' weights, rescaled to mean 1 among the
selected. Schools without any full text (Georgia Tech: positivity fails) have no weights (NaN) and are listed in the meta. Weight estimation error is not carried
into downstream intervals (they resample labs with the weights fixed).
Balance: standardised mean difference of every dummy/numeric covariate, selected-unweighted and selected-weighted against the whole population.
"""
import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

import frame as FR
import lcommon as L

CAT = ['year', 'home_school', 'source_type', 'work_type', 'oa_status', 'doi_prefix', 'oa_field', 'oa_subfield']
NUM = ['team_log', 'cited_log', 'refs_log', 'n_labs', 'is_oa']


def covariates(df, top=40):
    x = pd.DataFrame(index=df.index)
    x['year'] = df['year'].astype(int).astype(str)
    x['home_school'] = df['home_school'].fillna('unknown')
    x['source_type'] = df['source_type'].fillna('unknown')
    x['work_type'] = df['work_type'].fillna('unknown')
    x['oa_status'] = df['oa_status'].fillna('unknown')
    for c, k in (('doi_prefix', top), ('oa_field', 15), ('oa_subfield', 40)):
        s = df[c].fillna('none')
        keep = s.value_counts().index[:k]
        x[c] = s.where(s.isin(keep), 'other')
    x['team_log'] = np.log(df['n_authors'].fillna(df['n_authors'].median()).clip(lower=1))
    x['cited_log'] = np.log1p(df['cited_by'].fillna(0).clip(lower=0))
    x['refs_log'] = np.log1p(df['n_refs'].fillna(0).clip(lower=0))
    x['n_labs'] = df['n_labs'].fillna(1).clip(upper=5)
    x['is_oa'] = df['is_oa'].fillna(0)
    return x


def dummies(x):
    d = pd.get_dummies(x[CAT], dtype=float)
    return pd.concat([d, x[NUM].astype(float)], axis=1)


def crossfit(x, s, kind, folds, seed):
    n = len(x)
    p = np.zeros(n)
    skf = StratifiedKFold(folds, shuffle=True, random_state=seed)
    if kind == 'gbm':
        X = x[CAT + NUM].copy()
        for c in CAT:
            X[c] = X[c].astype('category')
        for tr, te in skf.split(X, s):
            m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0,
                                               categorical_features='from_dtype', early_stopping=True, validation_fraction=0.1, random_state=seed)
            m.fit(X.iloc[tr], s[tr])
            p[te] = m.predict_proba(X.iloc[te])[:, 1]
    else:
        D = dummies(x)
        ys = pd.get_dummies(x['year'] + '|' + x['home_school'], dtype=float)           # year x school interactions
        D = pd.concat([D, ys], axis=1)
        mu, sd = D.mean(), D.std().replace(0, 1)
        X = ((D - mu) / sd).to_numpy()
        for tr, te in skf.split(X, s):
            m = LogisticRegression(C=0.05, max_iter=400)
            m.fit(X[tr], s[tr])
            p[te] = m.predict_proba(X[te])[:, 1]
    return np.clip(p, 1e-4, 1 - 1e-4)


def stabilized(p, s, trim):
    """Weights of the selected: P(S=1)/p, trimmed at the quantiles of the selected weights, rescaled to mean 1 among the selected."""
    w = np.where(s == 1, s.mean() / p, np.nan)
    sel = w[s == 1]
    lo, hi = np.quantile(sel, trim)
    wt = np.clip(w, lo, hi)
    wt = wt / np.nanmean(wt[s == 1])
    return w, wt, (lo, hi)


def ess(w):
    w = w[np.isfinite(w)]
    return float(w.sum() ** 2 / (w ** 2).sum())


def smd_table(D, s, w):
    """SMD of each column of D (dummies/numerics): selected vs all, unweighted and weighted. Pooled SD of the two unweighted groups (Austin 2009)."""
    sel = s == 1
    all_m, all_v = D.mean(), D.var()
    sel_m, sel_v = D[sel].mean(), D[sel].var()
    sd = np.sqrt((all_v + sel_v) / 2).replace(0, np.nan)
    ww = np.where(sel, w, 0.0)
    wm = (D.mul(ww, axis=0).sum() / ww.sum())
    t = pd.DataFrame({'covariate': D.columns, 'mean_all': all_m.values, 'mean_sel': sel_m.values, 'mean_sel_w': wm.values,
                      'smd_before': ((sel_m - all_m) / sd).values, 'smd_after': ((wm - all_m) / sd).values})
    return t.dropna(subset=['smd_before'])


def fit_one(df, s_col, tag, cfg, seed=L.SEED):
    elig = ~df['home_school'].isin(cfg['exclude_schools'])
    d = df[elig].reset_index(drop=True)
    s = d[s_col].astype(int).to_numpy()
    x = covariates(d)
    res = {}
    for kind in ('gbm', 'logit'):
        p = crossfit(x, s, kind, cfg['folds'], seed)
        w, wt, cuts = stabilized(p, s, cfg['trim_quantiles'])
        D = dummies(x)
        bal = smd_table(D, s, np.nan_to_num(wt))
        res[kind] = dict(p=p, w=w, wt=wt, cuts=cuts, bal=bal, auc=float(roc_auc_score(s, p)), max_after=float(bal['smd_after'].abs().max()),
                         max_before=float(bal['smd_before'].abs().max()), ess=ess(wt[s == 1]))
        L.log(step='ipw', tag=tag, kind=kind, auc=res[kind]['auc'], max_smd_before=res[kind]['max_before'], max_smd_after=res[kind]['max_after'], ess=res[kind]['ess'], n_sel=int(s.sum()), n=len(s))
    best = min(res, key=lambda k: res[k]['max_after'])
    r = res[best]
    out = pd.DataFrame({'paper_id': d['paper_id'], f'in_{tag}': s, f'p_{tag}': r['p'], f'p_{tag}_gbm': res['gbm']['p'], f'p_{tag}_logit': res['logit']['p'],
                        f'w_{tag}_raw': r['w'], f'w_{tag}': r['wt']})
    meta = dict(outcome=s_col, model=best, n=len(d), n_selected=int(s.sum()), selected_share=float(s.mean()), excluded_schools=cfg['exclude_schools'],
                trim_cuts=[float(c) for c in r['cuts']], ess=r['ess'], ess_share=r['ess'] / int(s.sum()),
                share_p_below_0p05=float((r['p'] < 0.05).mean()), share_p_below_0p02=float((r['p'] < 0.02).mean()),
                weight_max=float(np.nanmax(r['wt'])), weight_p99=float(np.nanquantile(r['wt'][s == 1], 0.99)),
                **{f'{k}_{m}': res[k][m] for k in res for m in ('auc', 'max_before', 'max_after', 'ess')})
    bals = {k: res[k]['bal'].assign(model=k) for k in res}
    return out, meta, bals, d, s, r


def cell_check(d, s, wt):
    """Weighted share of the selected papers in each year x school cell against the population share: the marginal fit of the weights."""
    t = d[['year', 'home_school']].assign(s=s, w=np.nan_to_num(wt))
    pop = t.groupby(['year', 'home_school']).size() / len(t)
    sel = t[t['s'] == 1].groupby(['year', 'home_school'])['w'].sum()
    sel = sel / sel.sum()
    unw = t[t['s'] == 1].groupby(['year', 'home_school']).size() / (t['s'] == 1).sum()
    c = pd.concat([pop.rename('pop'), unw.rename('sel_unweighted'), sel.rename('sel_weighted')], axis=1).fillna(0).reset_index()
    return c


def fit():
    df, _, _ = FR.load()
    cfg = L.CFG['ipw']
    outs, metas, allbal = [], {}, []
    d_ft = None
    for s_col, tag in (('has_ft', 'ft'), ('has_abstract', 'abs')):
        out, meta, bals, d, s, r = fit_one(df, s_col, tag, cfg)
        outs.append(out)
        metas[tag] = meta
        for k, b in bals.items():
            allbal.append(b.assign(tag=tag))
        if tag == 'ft':
            d_ft = (d, s, r)
            L.write_atomic(cell_check(d, s, r['wt']), L.out('ipw', 'cell_check_ft.parquet'))
            # propensity decile calibration of the chosen model
            dec = pd.qcut(r['p'], 10, labels=False, duplicates='drop')
            L.write_atomic(pd.DataFrame({'decile': dec, 's': s, 'p': r['p']}).groupby('decile').agg(n=('s', 'size'), observed=('s', 'mean'), predicted=('p', 'mean')).reset_index(),
                           L.out('ipw', 'calibration_ft.parquet'))
    w = df[['paper_id', 'home_school', 'year']].merge(outs[0], on='paper_id', how='left').merge(outs[1], on='paper_id', how='left')
    L.write_atomic(w, L.IPW_TABLE)
    L.write_atomic(pd.concat(allbal, ignore_index=True), L.out('ipw', 'balance.parquet'))
    # by-year / by-school summary of weights
    ws = w[w['in_ft'] == 1]
    g = ws.groupby(['year']).agg(n=('w_ft', 'size'), w_mean=('w_ft', 'mean'), w_max=('w_ft', 'max')).reset_index()
    L.write_atomic(g, L.out('ipw', 'weights_by_year.parquet'))
    meta = dict(built=L.now() if hasattr(L, 'now') else None, frame_rows=len(df), config=cfg, tables=metas, scores_db=str(L.SCORES_DB), universe_db=str(L.UNIVERSE_DB))
    L.out('ipw', 'ipw_meta.json').write_text(json.dumps(meta, indent=1, default=str))
    L.log(step='ipw_done', table=str(L.IPW_TABLE), rows=len(w))


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != 'fit':
        sys.exit(__doc__)
    fit()
