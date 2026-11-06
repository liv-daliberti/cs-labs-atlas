"""Data for the four upgrades of the AI-writing pages (owner 2026-11-04): paper map, lab scatter, where AI is used, topic-matched test, Figure 3 for
nine schools, headline findings.  Heavy stages write tables under AI_SCORES/results/ai_pages/ (git-ignored); `assemble` turns them into the site JSON
under ai-writing/diversity/site-data/v2/ and the PNGs under ai-writing/diversity/reports/figures-ai-pages/.  README: site-data/v2/README.md.

  ai_pages.py frame       paper table (scores, topics, fields, lab ids incl. the site's lab id) -> frame.parquet, labs.parquet
  ai_pages.py umap        SPECTER2-proximity abstract vectors -> 2-D (PCA 50 + UMAP, fixed seed, all papers) -> umap.parquet
  ai_pages.py labs        lab scatter: size-matched pre/post values of 8 measures x 7 models, Huber slopes -> lab_measures.parquet, lab_slopes.parquet
  ai_pages.py matched     topic-matched AI vs non-AI test (novelty, dispersion, Vendi), post and placebo -> matched_*.parquet
  ai_pages.py fig3        knowledge extent and topic entropy of AI vs non-AI papers, 9 schools -> fig3_draws.parquet
  ai_pages.py assemble    JSON + PNG + headline.json

Rules: no 2026 (series end 2025, post = 2023-2025, pre = 2016-2022); AI paper = dose >= 25% of the passages flagged; the dose is ai_share_cal where the school or
field needed a recut, else ai_share (as the dose pages); full-text papers only for dose, abstract-flag for abstract-only papers where said so.
"""
import argparse
import gzip
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

import dcommon as D

LAST = D.LAST_FULL_YEAR
YEARS = list(range(2016, LAST + 1))
PRE, POST = list(range(2016, 2023)), list(range(2023, LAST + 1))
PLACEBO = list(range(2017, 2022))
THR = 0.25
HEADLINE = 'specter2_proximity'
MODELS = ['specter2_proximity', 'specter2_base', 'scincl', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']
MODEL_LABEL = {'specter2_proximity': 'SPECTER2 (proximity)', 'specter2_base': 'SPECTER2 base', 'scincl': 'SciNCL', 'qwen3_0p6b': 'Qwen3-0.6B',
               'gte_qwen2_1p5b': 'GTE-Qwen2-1.5B', 'bge_m3': 'BGE-M3', 'nomic_v15': 'Nomic v1.5'}
SEED = 20261104
RES = D.SCORES / 'results' / 'ai_pages'
OUT = Path(os.environ.get('AI_SITE_OUT') or (Path(__file__).resolve().parents[1] / 'diversity' / 'site-data' / 'v2'))      # AI_SITE_OUT: a new site-data directory (the v3 rerun)
FIG = Path(os.environ.get('AI_SITE_FIG') or (Path(__file__).resolve().parents[1] / 'diversity' / 'reports' / 'figures-ai-pages'))
MEASURES = ['dispersion', 'mpd', 'vendi', 'topic_entropy', 'effective_topics', 'extent', 'dist_field', 'new_topics']
MEASURE_LABEL = {'dispersion': 'Dispersion', 'mpd': 'Mean pairwise distance', 'vendi': 'Vendi score', 'topic_entropy': 'Topic entropy (bits)',
                 'effective_topics': 'Effective topics', 'extent': 'Knowledge extent', 'dist_field': 'Distance to field (novelty)', 'new_topics': 'New topics'}
LLM_RE = (r'\bllms?\b|language model|\bgpt|chatgpt|in-?context|\bprompt|instruction[- ]?tun|rlhf|human feedback|preference optim|pretrain|reasoning model|\bcot\b|chain of thought|'
          r'\btokens\b|\bkv\b|speculative|code generation|\bagents?\b|retrieval augmented|\brag\b|vlms?\b|visionlanguage|multimodal|foundation model|generative ai|\bgenai\b')
ML_RE = (r'(?<!social )learning|neural|\bdeep\b|gradient descent|reinforcement|classification|adversarial|\bgnns?\b|\bdnn|generalization|embedding|classifier|supervised|bandit|'
         r'optimization problems|nonconvex|convex optim|bayesian|causal|fairness|\brl\b|imitation|domain adaptation|transfer learning|federated|explainab|interpretab|\bxai\b|'
         r'computer vision|object detection|anomaly detection|outlier|speech|recognition|machine translation|autonomous driving|slam|segmentation|diffusion models|\bgans?\b|\brnns?\b|contrastive')


def detector_note():
    """meta.detector of every v3 site JSON (None for v2): the one-paragraph method note; the full error table is detector.json beside the files."""
    if not D.DETECTOR_VERSION.startswith('v3'):
        return None
    return dict(version='v3', file='detector.json', condition='main body only; abstained passages excluded (share shown on the how-much page)',
                note='Detector v3 (0.3% operating point). Human passages wrongly flagged: 0.30% (0.27-0.32%); unseen-family misses 0.9-6.6%; partial edits are reported separately in detector.json. '
                     'Shares are not comparable with the earlier (v2, 1% threshold) pages.')


def ensure_dirs():
    RES.mkdir(parents=True, exist_ok=True)


def dose_of(df):
    return df['ai_share_cal'].where(df['ai_share_cal'].notna(), df['ai_share'])


def kind_of(label, keywords):
    """'llm' | 'ml' | 'other' from a BERTopic topic's label (top 4 keywords) and its 10 keywords: LLM when the label matches or >= 2 keywords do."""
    import re
    lab = str(label or '').lower()
    kws = [k.strip().lower() for k in str(keywords or '').split(',')][:10]
    hit = sum(bool(re.search(LLM_RE, k)) for k in kws)
    if re.search(LLM_RE, lab) or hit >= 2:
        return 'llm'
    if re.search(ML_RE, lab) or sum(bool(re.search(ML_RE, k)) for k in kws) >= 3:
        return 'ml'
    return 'other'


def site_lab_ids(labs):
    """{universe lab id (atl:l:<school>:<slug>): the site's hierarchy lab id}. The site's lab pages (cs-hierarchy/<school>.json.gz of the live site checkout, built from the
    release) carry ids lab_cs_pi_... or lab_pi_...; a universe lab is the PI's own lab, so the two meet on (school, PI name), unique at every released school (checked
    in `frame`: the lab's papers are also the site lab's papers). Schools without a site hierarchy (gatech, uchicago: not released) get None."""
    root = D.P.SITE / 'atlas' / 'data' / 'cs-hierarchy'
    by = {}
    for s in D.SCHOOLS:
        p = root / f'{s}.json.gz'
        if not p.exists():
            continue
        names = {}
        for l in json.load(gzip.open(p, 'rt'))['labs']:
            names.setdefault(l['pi']['name'], []).append(l['id'])
        for n, ids in names.items():
            if len(ids) == 1:
                by[(s, n)] = ids[0]
    return {r.lab_id: by.get((r.school, r.pi)) for r in labs.itertuples()}


# ------------------------------------------------------------------ frame

def stage_frame():
    ensure_dirs()
    import dose_data as DD
    import emb_load as L
    df = DD.paper_table(with_split=True)
    _, lp = DD.universe()
    lp = lp[lp['year'].between(2016, LAST)]
    first = lp.drop_duplicates('paper_id').set_index('paper_id')['lab_id']
    df['lab0'] = df['paper_id'].map(first)
    df['school'] = df['home_school']
    df['x'] = dose_of(df)
    df['ai25'] = np.where(df['x'].notna(), (df['x'] >= THR - 1e-12).astype(float), np.nan)
    tp = pd.read_parquet(L.C.RESULTS / f'topics_{HEADLINE}.parquet')[['paper_id', 'topic']]
    lb = pd.read_parquet(L.C.RESULTS / f'topic_labels_{HEADLINE}.parquet')
    lb['kind'] = [kind_of(a, b) for a, b in zip(lb['label'], lb['keywords'])]
    df = df.merge(tp, on='paper_id', how='left').merge(lb[['topic', 'label', 'keywords', 'kind', 'size']].rename(columns={'label': 'topic_label', 'size': 'topic_size'}), on='topic', how='left')
    ids, _, _ = L.vectors(HEADLINE, 'abstract')
    df['has_vec'] = df['paper_id'].isin(set(ids))
    labs = lp.drop_duplicates(['lab_id']).copy()
    labs['site_lab'] = labs['lab_id'].map(site_lab_ids(labs))
    df['site_lab'] = df['lab0'].map(dict(zip(labs['lab_id'], labs['site_lab'])))
    df.drop(columns=['schools', 'author_ids']).assign(schools=df['schools'].map(lambda s: ','.join(s))).to_parquet(RES / 'frame.parquet', index=False)
    labs[['lab_id', 'school', 'pi', 'lab_name', 'site_lab']].to_parquet(RES / 'labs.parquet', index=False)
    lp[['paper_id', 'lab_id', 'school', 'year']].to_parquet(RES / 'lab_papers.parquet', index=False)
    lb.to_parquet(RES / 'topics.parquet', index=False)
    D.log(stage='frame', papers=len(df), with_vec=int(df['has_vec'].sum()), scored=int(df['x'].notna().sum()), labs=len(labs), labs_with_site_id=int(labs['site_lab'].notna().sum()),
          topic_kinds=lb['kind'].value_counts().to_dict(), site_lab_paper_overlap=site_overlap(labs, lp))


def site_overlap(labs, lp):
    """Check of the PI-name join: the share of a universe lab's 2016-2025 papers that the matched site lab also lists (median, minimum over matched labs)."""
    root = D.P.SITE / 'atlas' / 'data' / 'cs-hierarchy'
    mine = lp.groupby('lab_id')['paper_id'].agg(set)
    share = []
    for s in D.SCHOOLS:
        p = root / f'{s}.json.gz'
        if not p.exists():
            continue
        d = json.load(gzip.open(p, 'rt'))
        site = {l['id']: {d['papers'][i[0]]['atlasId'] if isinstance(i, list) else d['papers'][i]['atlasId'] for i in l['papers']} for l in d['labs']}
        for r in labs[(labs['school'] == s) & labs['site_lab'].notna()].itertuples():
            a, b = mine.get(r.lab_id, set()), site.get(r.site_lab, set())
            if a:
                share.append(len(a & b) / len(a))
    return dict(labs=len(share), median=float(np.median(share)) if share else None, p10=float(np.percentile(share, 10)) if share else None, min=float(min(share)) if share else None)


# ------------------------------------------------------------------ vectors

def unit_vectors(model, keep_ids=None):
    """(ids array, unit float32 matrix of the corpus-centred abstract vectors) for the papers 2016-2025 of the universe; centred on the mean of those papers."""
    import emb_load as L
    papers, _ = L.universe()
    ids, X, _ = L.vectors(model, 'abstract')
    ids = np.array(ids)
    ok = pd.Series(ids).isin(set(papers['paper_id'])).to_numpy()   # np.isin on string arrays took minutes
    ids, X = ids[ok], X[ok]
    X = X - X.mean(0)
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    return ids, X


def stage_umap():
    import ecommon as _e  # noqa: F401
    import ecommon as C
    C.use_extras()
    from sklearn.decomposition import PCA
    from umap import UMAP
    ensure_dirs()
    ids, Z = unit_vectors(HEADLINE)
    t = time.time()
    P50 = PCA(50, random_state=SEED).fit_transform(Z)
    Y = UMAP(n_components=2, n_neighbors=15, min_dist=0.1, metric='euclidean', random_state=SEED).fit_transform(P50)
    pd.DataFrame(dict(paper_id=ids, ux=Y[:, 0].astype(np.float32), uy=Y[:, 1].astype(np.float32))).to_parquet(RES / 'umap.parquet', index=False)
    D.log(stage='umap', papers=len(ids), seconds=round(time.time() - t), x=[float(Y[:, 0].min()), float(Y[:, 0].max())], y=[float(Y[:, 1].min()), float(Y[:, 1].max())])


# ------------------------------------------------------------------ lab scatter

def huber(X, y, c=1.345, iters=50):
    """Huber M-estimator (IRLS, MAD scale), as diversity/analyze.py."""
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(iters):
        r = y - X @ b
        s = np.median(np.abs(r - np.median(r))) / 0.6745
        if s <= 1e-12:
            break
        u = np.abs(r) / (c * s)
        w = np.where(u <= 1, 1.0, 1.0 / np.maximum(u, 1e-12))
        sw = np.sqrt(w)
        nb = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
        if np.max(np.abs(nb - b)) < 1e-7:
            return nb
        b = nb
    return b


def zs(v):
    v = np.asarray(v, float)
    sd = v.std()
    return (v - v.mean()) / sd if sd > 0 else v * 0


def slope_design(d, x, controls, school_col='school'):
    cols = [np.ones(len(d)), zs(d[x])] + [zs(d[c]) for c in controls]
    lv = sorted(d[school_col].unique())
    cols += [(d[school_col] == v).astype(float).to_numpy() for v in lv[1:]]
    return np.column_stack(cols)


def huber_slope(d, y, x='dose', controls=('log_n_pre', 'log_n_post'), B=500, seed=0):
    """Standardized Huber slope of z(y) on z(x) with size and school controls and a 95% percentile bootstrap over labs: (beta, lo, hi, n)."""
    d = d.dropna(subset=[y, x]).reset_index(drop=True)
    if len(d) < 20:
        return np.nan, np.nan, np.nan, len(d)
    X = slope_design(d, x, controls)
    yy = zs(d[y])
    beta = float(huber(X, yy)[1])
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(B):
        i = rng.integers(0, len(d), len(d))
        s = d.iloc[i].reset_index(drop=True)
        if s[x].std() == 0 or s[y].std() == 0:
            continue
        bs.append(huber(slope_design(s, x, controls), zs(s[y]))[1])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return beta, float(lo), float(hi), len(d)


def lab_measures_model(model, fr, lpap, labsel, reps, cap, seed):
    import ecommon as C
    ids, Z = unit_vectors(model)
    row = {p: i for i, p in enumerate(ids)}
    # topic partition: BERTopic where the study has one (two models), else 100 k-means clusters of the model's own vectors
    tp = C.RESULTS / f'topics_{model}.parquet'
    if tp.exists():
        t = pd.read_parquet(tp).set_index('paper_id')['topic']
        topic = pd.Series(ids).map(t).fillna(-1).astype(int).to_numpy()
        part = 'bertopic'
    else:
        from sklearn.cluster import MiniBatchKMeans
        topic = MiniBatchKMeans(100, random_state=SEED, n_init=3, batch_size=4096).fit_predict(Z).astype(int)
        part = 'kmeans100'
    import pyarrow.dataset as pds
    nv = pds.dataset(C.RESULTS / f'novelty_{model}_abstract.parquet').to_table(columns=['paper_id', 'nov_nn_cap'], filter=(pds.field('scope') == 'all') & (pds.field('k') == 3)).to_pandas()
    nov = pd.Series(ids).map(nv.set_index('paper_id')['nov_nn_cap']).to_numpy(float)
    year_of = fr.set_index('paper_id')['year']
    yr = pd.Series(ids).map(year_of).to_numpy()
    lp = lpap[lpap['paper_id'].isin(row)].copy()
    lp['row'] = lp['paper_id'].map(row)
    rng = np.random.default_rng(seed)
    out = []
    for lab, g in lp.groupby('lab_id'):
        if lab not in labsel:
            continue
        r_all, y_all = g['row'].to_numpy(), g['year'].to_numpy()
        # new topics: the paper's topic is absent from the lab's papers of the three previous years (window >= 5 papers), as N2 of the October battery
        new = np.full(len(g), np.nan)
        for i, (y0, t0) in enumerate(zip(y_all, topic[r_all])):
            w = (y_all >= y0 - 3) & (y_all < y0)
            if w.sum() >= 5:
                new[i] = float(t0 not in set(topic[r_all[w]]))
        res = {}
        pre_i, post_i = np.flatnonzero(np.isin(y_all, PRE)), np.flatnonzero(np.isin(y_all, POST))
        m = min(len(pre_i), len(post_i), cap)
        for name, ii in (('pre', pre_i), ('post', post_i)):
            pick = np.argsort(rng.random((reps, len(ii))), axis=1)[:, :m]
            sel = ii[pick]                                      # reps x m indices into g
            rr = r_all[sel]
            V = Z[rr]
            c = V.mean(1, keepdims=True)
            dist = np.linalg.norm(V - c, axis=2)
            G = np.einsum('rid,rjd->rij', V, V)
            lam = np.clip(np.linalg.eigvalsh(G / m), 1e-12, None)
            tt = topic[rr]
            H = np.empty(reps)
            for k in range(reps):
                cnt = np.unique(tt[k], return_counts=True)[1] / m
                H[k] = -(cnt * np.log2(cnt)).sum()
            nv_ = nov[rr]
            nw_ = new[sel]
            res[name] = dict(dispersion=dist.mean(), mpd=(1.0 - (G.sum((1, 2)) - m) / (m * (m - 1))).mean(), vendi=np.exp(-(lam * np.log(lam)).sum(1)).mean(),
                             topic_entropy=H.mean(), effective_topics=(2.0 ** H).mean(), extent=dist.max(1).mean(),
                             dist_field=float(np.nanmean(nv_)) if np.isfinite(nv_).any() else np.nan,
                             new_topics=float(np.nanmean(nw_)) if np.isfinite(nw_).any() else np.nan)
        for ms in MEASURES:
            out.append(dict(model=model, partition=part, lab_id=lab, measure=ms, m=m, n_pre=len(pre_i), n_post=len(post_i), pre=float(res['pre'][ms]), post=float(res['post'][ms])))
    return pd.DataFrame(out)


def slopes_from(lm, base, boot):
    """Huber slope rows per (model, measure) from lab_measures `lm` and the lab table `base` (lab_id, school, dose, n_pre, n_post)."""
    rows = []
    for (model, measure), g in lm.groupby(['model', 'measure']):
        d = g.drop(columns=['n_pre', 'n_post']).merge(base[['lab_id', 'school', 'dose', 'n_pre', 'n_post']], on='lab_id')
        d['log_n_pre'], d['log_n_post'] = np.log(d['n_pre']), np.log(d['n_post'])
        d = d.dropna(subset=['change', 'dose'])
        b, lo, hi, n = huber_slope(d, 'change', 'dose', B=boot, seed=7)
        line = huber(np.column_stack([np.ones(len(d)), 100 * d['dose'].to_numpy()]), d['change'].to_numpy()) if len(d) > 5 else [np.nan, np.nan]
        rows.append(dict(model=model, measure=measure, beta=b, lo=lo, hi=hi, labs=n, line_a=float(line[0]), line_b_per_pct=float(line[1])))
    return rows


def stage_labs(models, reps=100, cap=80, boot=500):
    from concurrent.futures import ProcessPoolExecutor
    ensure_dirs()
    fr = pd.read_parquet(RES / 'frame.parquet')
    lpap = pd.read_parquet(RES / 'lab_papers.parquet')
    lpap = lpap[lpap['paper_id'].isin(set(fr.loc[fr['has_vec'], 'paper_id']))]
    npre = lpap[lpap['year'].isin(PRE)].groupby('lab_id').size()
    npost = lpap[lpap['year'].isin(POST)].groupby('lab_id').size()
    labsel = set(npre[npre >= 5].index) & set(npost[npost >= 5].index)
    D.log(stage='labs', labs_selected=len(labsel))
    with ProcessPoolExecutor(min(len(models), 7)) as ex:
        futs = [ex.submit(lab_measures_model, m, fr, lpap, labsel, reps, cap, SEED + i) for i, m in enumerate(models)]
        parts = [f.result() for f in futs]
    lm = pd.concat(parts, ignore_index=True)
    lm['change'] = lm['post'] - lm['pre']
    lm.to_parquet(RES / 'lab_measures.parquet', index=False)
    # exposure per lab
    paper_lab = lpap.merge(fr[['paper_id', 'x', 'ai25', 'flag_abstract']], on='paper_id')
    post = paper_lab[paper_lab['year'].isin(POST)]
    ex_ = post.groupby('lab_id').agg(n_post_papers=('paper_id', 'size'), n_scored_post=('x', 'count'), dose=('x', 'mean'), share25=('ai25', 'mean'),
                                     n_abs_post=('flag_abstract', 'count'), abs_flag_share=('flag_abstract', 'mean')).reset_index()
    ex_.loc[ex_['n_scored_post'] < 5, ['dose', 'share25']] = np.nan
    ex_.to_parquet(RES / 'lab_exposure.parquet', index=False)
    labs = pd.read_parquet(RES / 'labs.parquet')
    base = ex_.merge(labs, on='lab_id').merge(pd.DataFrame(dict(n_pre=npre, n_post=npost)).reset_index().rename(columns={'index': 'lab_id'}), on='lab_id')
    rows = slopes_from(lm, base, boot)
    pd.DataFrame(rows).to_parquet(RES / 'lab_slopes.parquet', index=False)
    D.log(stage='labs', rows=len(lm), slopes=len(rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['frame', 'umap', 'labs', 'matched', 'wording', 'fig3', 'assemble'])
    ap.add_argument('--model', action='append')
    ap.add_argument('--reps', type=int, default=100)
    ap.add_argument('--boot', type=int, default=500)
    a = ap.parse_args()
    if a.cmd == 'frame':
        stage_frame()
    elif a.cmd == 'umap':
        stage_umap()
    elif a.cmd == 'labs':
        stage_labs(a.model or MODELS, a.reps, boot=a.boot)
    elif a.cmd == 'assemble':
        import ai_pages_site as S
        S.assemble(a)
    else:
        import ai_pages_more as M
        getattr(M, 'stage_' + a.cmd)(a)


if __name__ == '__main__':
    main()
