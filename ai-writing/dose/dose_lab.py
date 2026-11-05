"""Lab-level and lab-year designs (Part C): diversity of a lab's papers in a year against the lab's AI exposure.

  dose_lab.py panel --model M [--kind abstract] [--m 5 --reps 100]     lab-year panel for one model -> AI_SCORES/results/labyear_<model>_<kind>.parquet
  dose_lab.py did   --model M [--kind abstract]                        difference-in-differences, event study, placebos, within-lab-year dose
                                                                     -> results/did_<model>_<kind>.parquet
Lab-year outcomes (size-matched: `reps` random draws of `m` papers of the lab-year, the mean over draws; lab-years with fewer than m papers are left out):
  disp   mean distance of the draw's papers to its centroid          mpd   mean pairwise cosine distance          vendi  Vendi score (q = 1) of the cosine kernel
  h_oa   Shannon entropy (bits) of OpenAlex primary topics            h_bt   of the model's BERTopic topics (specter2_proximity, qwen3_0p6b only)
  nov_all, nov_lab   mean size-matched nearest-neighbour novelty (k = 3) of the lab-year's papers against all papers / the lab's own history
Exposure: Dose_l = the lab's mean ai_share over its scored 2023-2025 papers (at least `min_scored` of them); AbsDose_l the same with flag_abstract (no full-text
selection). Lab-year ai_share_lt = mean over that year's scored papers (>= 2).
DiD: y_lt = lab FE + year FE + b * Post_t * Dose_l (Post = 2023-2025; 2022 is dropped as the transition year), cluster bootstrap over labs.
Placebo: the same on 2016/17-2021 with the break at 2019, 2020 and 2021 (Post_p = year >= break). Event study: Dose_l x year dummies, 2021 as the base.
"""
import argparse

import numpy as np
import pandas as pd

import dcommon as D
import dose_reg as R

POST = D.POST_YEARS
BREAKS = (2019, 2020, 2021)


def _entropy_bits(counts):
    c = counts[counts > 0].astype(float)
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def draw_metrics(Z, idx, m, reps, rng, labels=None):
    """Size-matched diversity of one group: dict of the mean over `reps` draws of m rows of Z (unit vectors) from `idx`; `labels`: integer topic codes per row of Z."""
    n = len(idx)
    pick = np.argsort(rng.random((reps, n)), axis=1)[:, :m]
    rows = np.asarray(idx)[pick]                                  # reps x m
    V = Z[rows]                                                   # reps x m x d
    c = V.mean(1, keepdims=True)
    disp = np.linalg.norm(V - c, axis=2).mean(1)
    G = np.einsum('rid,rjd->rij', V, V)
    mpd = 1.0 - (G.sum((1, 2)) - m) / (m * (m - 1))
    lam = np.clip(np.linalg.eigvalsh(G / m), 1e-12, None)
    vendi = np.exp(-(lam * np.log(lam)).sum(1))
    out = dict(disp=float(disp.mean()), mpd=float(mpd.mean()), vendi=float(vendi.mean()))
    if labels is not None:
        L = labels[rows]
        out['h_labels'] = float(np.mean([_entropy_bits(np.unique(l, return_counts=True)[1]) for l in L]))
    return out


def lab_year_panel(Z, ids, lp, labels, m, reps, seed=0):
    """Rows (lab_id, year, n, disp, mpd, vendi[, h]) for every lab-year of lp (paper_id, lab_id, year) with at least m papers that have a vector."""
    row = {p: i for i, p in enumerate(ids)}
    lp = lp[lp['paper_id'].isin(row)].copy()
    lp['row'] = lp['paper_id'].map(row)
    rng = np.random.default_rng(seed)
    out = []
    for (lab, year), g in lp.groupby(['lab_id', 'year']):
        idx = g['row'].to_numpy()
        if len(idx) < m:
            continue
        r = draw_metrics(Z, idx, m, reps, rng, labels)
        out.append(dict(lab_id=lab, year=int(year), n=len(idx), **r))
    return pd.DataFrame(out)


def lab_exposure(papers_lab, min_scored=4):
    """Lab-level doses from rows (lab_id, year, ai_share, flag_abstract): Dose_l (post mean ai_share, >= min_scored scored post papers), AbsDose_l (post mean flag_abstract, >= min_scored)."""
    post = papers_lab[papers_lab['year'].isin(POST)]
    a = post.dropna(subset=['ai_share']).groupby('lab_id')['ai_share'].agg(dose='mean', n_scored='size')
    b = post.dropna(subset=['flag_abstract']).groupby('lab_id')['flag_abstract'].agg(abs_dose='mean', n_abs='size')
    t = a.join(b, how='outer')
    t.loc[t['n_scored'].fillna(0) < min_scored, 'dose'] = np.nan
    t.loc[t['n_abs'].fillna(0) < min_scored, 'abs_dose'] = np.nan
    return t.reset_index()


def did_table(panel, y, dose='dose', w=None, boot=200, seed=0):
    """Rows of DiD, placebo and event-study estimates for outcome y of a lab-year panel (columns lab_id, year, y, dose, w). b is per unit of dose (0 -> 1)."""
    rows = []

    def one(d, name, x, fe=('lab_id', 'year'), extra=None):
        est, lo, hi = R.boot_fit(d, y, x, 'lab_id', fe=list(fe), nested=['lab_id'], weights=w, B=boot, seed=seed)
        rows.append(dict(spec=name, beta=est, lo=lo, hi=hi, n=len(d), labs=d['lab_id'].nunique(), outcome=y, dose=dose, **(extra or {})))

    d = panel.dropna(subset=[y, dose]).copy()
    post = d[(d['year'] <= 2021) | d['year'].isin(POST)].copy()
    post['post_x'] = post['year'].isin(POST).astype(float) * post[dose]
    one(post, 'did', 'post_x')
    pre = d[d['year'] <= 2021].copy()
    for b in BREAKS:
        p = pre.copy()
        p['post_x'] = (p['year'] >= b).astype(float) * p[dose]
        one(p, f'placebo{b}', 'post_x')
    ev = d[(d['year'] <= 2021) | d['year'].isin(POST)].copy()
    ys = sorted(ev['year'].unique())
    cols = []
    for t in ys:
        if t == 2021:
            continue
        ev[f'ev{t}'] = (ev['year'] == t) * ev[dose]
        cols.append(f'ev{t}')
    r = R.fit(ev, y, cols, fe=['lab_id', 'year'], cluster='lab_id', weights=w)
    for c in cols:
        rows.append(dict(spec='event', year=int(c[2:]), beta=r['coefs'].get(c, np.nan), lo=r['coefs'].get(c, np.nan) - 1.96 * r['ses'].get(c, np.nan),
                         hi=r['coefs'].get(c, np.nan) + 1.96 * r['ses'].get(c, np.nan), n=r['n'], labs=r['clusters'], outcome=y, dose=dose))
    return pd.DataFrame(rows)


def within_lab_year(panel, y, expo='ai_share_lt', boot=200, seed=0):
    """Post years only: lab-year mean exposure against the outcome with lab and year FE (the lab's busier-AI years against its quieter ones)."""
    d = panel[panel['year'].isin(POST)].dropna(subset=[y, expo])
    est, lo, hi = R.boot_fit(d, y, expo, 'lab_id', fe=['lab_id', 'year'], nested=['lab_id'], B=boot, seed=seed)
    return dict(spec='within_lab_year', beta=est, lo=lo, hi=hi, n=len(d), labs=d['lab_id'].nunique(), outcome=y, dose=expo)


def build_panel(model, kind, m, reps):
    import emb_load as L
    import ecommon as C
    import dose_analysis as A
    df = A.build_frame()
    papers, lp = L.universe()
    ids, X, meta = L.vectors(model, kind)
    keep = np.isin(ids, list(set(papers['paper_id'])))
    mu = X[keep].mean(0)
    Y = X - mu
    Z = Y / (np.linalg.norm(Y, axis=1, keepdims=True) + 1e-9)
    topic = df.set_index('paper_id')['topic']
    lab_codes = pd.factorize(pd.Series(ids).map(topic).fillna('none'))[0]
    panel = lab_year_panel(Z, ids, lp, lab_codes, m, reps).rename(columns={'h_labels': 'h_oa'})
    bt = C.EMB / 'results' / f'topics_{model}.parquet'
    if bt.exists():
        t = pd.read_parquet(bt).set_index('paper_id')['topic']
        codes = pd.factorize(pd.Series(ids).map(t).fillna(-1))[0]
        pb = lab_year_panel(Z, ids, lp, codes, m, reps)[['lab_id', 'year', 'h_labels']].rename(columns={'h_labels': 'h_bt'})
        panel = panel.merge(pb, on=['lab_id', 'year'], how='left')
    pl = lp[['paper_id', 'lab_id', 'year']].merge(df[['paper_id', 'ai_share', 'flag_abstract', 'ai_share_cal']], on='paper_id', how='left')
    lt = pl.groupby(['lab_id', 'year']).agg(ai_share_lt=('ai_share', 'mean'), n_scored=('ai_share', 'count'), flag_abs_lt=('flag_abstract', 'mean'), n_papers=('paper_id', 'size')).reset_index()
    lt.loc[lt['n_scored'] < 2, 'ai_share_lt'] = np.nan
    panel = panel.merge(lt, on=['lab_id', 'year'], how='left').merge(lab_exposure(pl), on='lab_id', how='left')
    for kk, name in ((3, 'nov_all'),):
        n = A.novelty_rows(model, kind, 'all', ks=(kk,))
        if n is not None:
            n = n.merge(pl[['paper_id', 'lab_id', 'year']], on='paper_id')
            panel = panel.merge(n[n['k'] == kk].groupby(['lab_id', 'year'])['nov_nn_cap'].mean().rename(name).reset_index(), on=['lab_id', 'year'], how='left')
    n = A.novelty_rows(model, kind, 'lab', ks=(3,))
    if n is not None:
        n = n.merge(pl[['paper_id', 'year']].drop_duplicates('paper_id'), on='paper_id')
        panel = panel.merge(n[n['k'] == 3].groupby(['scope_id', 'year'])['nov_nn_cap'].mean().rename('nov_lab').reset_index().rename(columns={'scope_id': 'lab_id'}),
                            on=['lab_id', 'year'], how='left')
    D.RESULTS.mkdir(parents=True, exist_ok=True)
    panel = panel[panel['year'] <= D.LAST_FULL_YEAR].reset_index(drop=True)
    panel.to_parquet(D.RESULTS / f'labyear_{model}_{kind}.parquet', index=False)
    D.log(model=model, kind=kind, lab_years=len(panel), labs=panel['lab_id'].nunique(), with_dose=int(panel['dose'].notna().sum()))


def run_did(model, kind, boot):
    panel = pd.read_parquet(D.RESULTS / f'labyear_{model}_{kind}.parquet')
    outs = []
    for y in ('disp', 'mpd', 'vendi', 'h_oa', 'h_bt', 'nov_all', 'nov_lab'):
        if y not in panel or panel[y].notna().sum() < 100:
            continue
        for dose in ('dose', 'abs_dose'):
            t = did_table(panel, y, dose, boot=boot)
            t['model'], t['kind'] = model, kind
            outs.append(t)
        w = pd.DataFrame([within_lab_year(panel, y, boot=boot)]); w['model'], w['kind'] = model, kind
        outs.append(w)
    pd.concat(outs, ignore_index=True).to_parquet(D.RESULTS / f'did_{model}_{kind}.parquet', index=False)
    D.log(model=model, kind=kind, did_rows=sum(len(o) for o in outs))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['panel', 'did'])
    ap.add_argument('--model', required=True)
    ap.add_argument('--kind', default='abstract')
    ap.add_argument('--m', type=int, default=5)
    ap.add_argument('--reps', type=int, default=100)
    ap.add_argument('--boot', type=int, default=200)
    a = ap.parse_args()
    build_panel(a.model, a.kind, a.m, a.reps) if a.cmd == 'panel' else run_did(a.model, a.kind, a.boot)
