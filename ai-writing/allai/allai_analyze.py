"""Diversity and novelty of the original corpus against the all-AI corpus (every abstract rewritten), same papers, same models.

  allai_analyze.py geom    --model M [--style polish]   dispersion, mean pairwise distance, Vendi, topic entropy: per year (all papers, each school) with a
                                                   lab-cluster bootstrap, and per lab and period (pre 2016-2022, post 2023-2026)
  allai_analyze.py novelty --model M [--style polish]   novelty k = 1, 3, 5 (ai-writing/embeddings/novelty.py) on both corpora, paired per paper
Outputs under EMB/allai/results/ (parquet): geom_year_<tag>, geom_lab_<tag>, novelty_trend_<tag>, novelty_contrast_<tag> with tag = <style>_<model>.

Corpora. Set A = the papers whose rewrite passed the preservation filter (build_texts.py) and that have a vector in both stores (original store
`<model>`, rewrite store `<model>__allai` for polish, `<model>__para` for paraphrase). Both corpora are restricted to A, so every difference is the same
papers' original wording against its AI wording. Each corpus is centred on its own mean and L2-normalised before any cosine (SPECTER2 is anisotropic).
Topics. Fixed cluster sets, defined on the ORIGINAL vectors only: `bt` = the BERTopic topics of embeddings/topics.py (specter2_proximity and qwen3_0p6b), a
paper going to the nearest topic centroid (both corpora, the same rule; centroids and the common centring mean come from the originals), and `km` =
k-means with 100 clusters on the originals (every model). The rewrite's cluster is whatever its vector is nearest to.
Size matching. All papers 1,000 per draw (the Vendi eigendecomposition), a school-year 500, a lab-period 20 (topic entropy for 'all' at 2,000 as in the
embeddings report). The draws are paired: the same paper indices are drawn from both corpora. Point estimates average DRAWS draws; intervals are 2.5/97.5
percentiles of BOOT replicates, each resampling whole labs (a paper's first lab) with replacement and drawing once.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
import ecommon as C  # noqa: E402
import emb_load as L  # noqa: E402
import measures as M  # noqa: E402  (embeddings/measures.py: entropy + bootstrap helpers)
import novelty as N  # noqa: E402
from allai_math import draw, entropy_bits, gram_geometry, nearest_centroid  # noqa: E402

ALLAI = C.EMB / 'allai'
RES = ALLAI / 'results'
STYLE_SUFFIX = {'polish': '__allai', 'paraphrase': '__para'}
YEARS = list(range(2016, 2027))
PRE, POST = list(range(2016, 2023)), list(range(2023, 2027))
M_ALL, M_ALL_TOPIC, M_SCHOOL, M_LAB = 1000, 2000, 500, 20
DRAWS, BOOT, LAB_DRAWS = 30, 100, 50
SCHOOLS = C.RELEASED + ['uchicago', 'gatech']
KM_K = 100
BT_MODELS = ('specter2_proximity', 'qwen3_0p6b')


# ---------------------------------------------------------------- data
def load_pair(model, style):
    papers, lp = L.universe()
    ids_o, Xo, meta_o = L.vectors(model, 'abstract')
    ids_a, Xa, meta_a = L.vectors(model + STYLE_SUFFIX[style], 'abstract')
    ro, ra = {p: i for i, p in enumerate(ids_o)}, {p: i for i, p in enumerate(ids_a)}
    papers = papers[papers['paper_id'].isin(ro) & papers['paper_id'].isin(ra)].reset_index(drop=True)
    io = [ro[p] for p in papers['paper_id']]; ia = [ra[p] for p in papers['paper_id']]
    Xo, Xa = Xo[io], Xa[ia]
    return papers, lp[lp['paper_id'].isin(set(papers['paper_id']))].reset_index(drop=True), Xo, Xa, meta_o, meta_a


def label_sets(model, papers, Xo, Xa):
    """{name: (labels_orig, labels_ai, k)}: nearest-centroid assignment in the originals' centred space."""
    mu = Xo.mean(0)
    Zo, _ = N.center_normalize(Xo, mu)
    Za, _ = N.center_normalize(Xa, mu)
    out = {}
    if model in BT_MODELS:
        t = pd.read_parquet(C.RESULTS / f'topics_{model}.parquet').set_index('paper_id')['topic']
        tt = papers['paper_id'].map(t)
        ok = tt.notna().to_numpy()
        tops = np.sort(tt[ok].unique()).astype(int)
        cent = np.stack([Zo[ok][tt[ok].to_numpy() == k].mean(0) for k in tops])
        cent /= np.linalg.norm(cent, axis=1, keepdims=True)
        lo, la = nearest_centroid(Zo, cent), nearest_centroid(Za, cent)
        agree = float((lo[ok] == np.searchsorted(tops, tt[ok].to_numpy().astype(int))).mean())
        out['bt'] = (lo, la, len(tops), dict(agree_with_bertopic=agree))
    from sklearn.cluster import MiniBatchKMeans
    km = MiniBatchKMeans(KM_K, random_state=C.SEED, batch_size=4096, n_init=3).fit(Zo)
    cent = km.cluster_centers_ / np.linalg.norm(km.cluster_centers_, axis=1, keepdims=True)
    out['km'] = (nearest_centroid(Zo, cent), nearest_centroid(Za, cent), KM_K, {})
    return out


def lab_structure(papers, lp):
    pos = {p: i for i, p in enumerate(papers['paper_id'])}
    first = lp.sort_values('lab_id').drop_duplicates('paper_id').set_index('paper_id')['lab_id']
    cl = papers['paper_id'].map(first).fillna('none').to_numpy()
    uniq, inv = np.unique(cl, return_inverse=True)
    groups = [np.nonzero(inv == i)[0] for i in range(len(uniq))]
    school_mask = {s: papers['schools'].map(lambda x, s=s: s in x).to_numpy() for s in SCHOOLS}
    labs = {}
    for lab, g in lp.groupby('lab_id'):
        labs[lab] = np.array(sorted({pos[p] for p in g['paper_id']}))
    return cl, groups, school_mask, labs


# ---------------------------------------------------------------- geometry + topics per year
def measure_set(Zo, Za, labs_sets, idx, with_vendi=True):
    """{(corpus, measure): value} for the paper indices idx in both corpora."""
    r = {}
    for c, Z in (('orig', Zo), ('ai', Za)):
        d, p, v = gram_geometry(Z[idx]) if with_vendi else (*gram_geometry_nov(Z[idx]), np.nan)
        r[(c, 'dispersion')], r[(c, 'pairwise')], r[(c, 'vendi')] = d, p, v
    for name, (lo, la, k, _) in labs_sets.items():
        r[('orig', 'H_' + name)] = entropy_bits(lo[idx], k)
        r[('ai', 'H_' + name)] = entropy_bits(la[idx], k)
    return r


def gram_geometry_nov(U):
    d, p, _ = gram_geometry(U)
    return d, p


def year_tables(model, papers, Zo, Za, labs_sets, cl, groups, school_mask, rng):
    years = papers['year'].to_numpy()
    scopes = [('all', 'all', np.ones(len(papers), bool))] + [('school', s, school_mask[s]) for s in SCHOOLS]
    rows = []
    # point estimates: DRAWS paired draws per (scope, year)
    for scope, sid, mask in scopes:
        for y in YEARS:
            pool = np.nonzero(mask & (years == y))[0]
            m = M_ALL if scope == 'all' else M_SCHOOL
            if len(pool) < m:
                continue
            acc = {}
            for _ in range(DRAWS):
                for k, v in measure_set(Zo, Za, labs_sets, draw(rng, pool, m)).items():
                    acc.setdefault(k, []).append(v)
            if scope == 'all':   # topic entropy of the all-papers series at the report's m = 2000
                if len(pool) >= M_ALL_TOPIC:
                    for name, (lo, la, k, _) in labs_sets.items():
                        hs = [(entropy_bits(lo[i], k), entropy_bits(la[i], k)) for i in (draw(rng, pool, M_ALL_TOPIC) for _ in range(DRAWS))]
                        acc[('orig', 'H_' + name + '2000')] = [h[0] for h in hs]; acc[('ai', 'H_' + name + '2000')] = [h[1] for h in hs]
            for (c, meas), v in acc.items():
                rows.append(dict(scope=scope, scope_id=sid, year=y, corpus=c, measure=meas, value=float(np.mean(v)), n_pool=int(len(pool)), m=m, point=1))
    pt = pd.DataFrame(rows)
    # bootstrap replicates over labs: one paired draw per (scope, year) per replicate
    boot = []
    brng = np.random.default_rng(C.SEED + 7)
    for b in range(BOOT):
        pick = brng.integers(0, len(groups), len(groups))
        idx_all = np.concatenate([groups[i] for i in pick])
        yb = years[idx_all]
        for scope, sid, mask in scopes:
            ib = idx_all[mask[idx_all]]
            for y in YEARS:
                pool = ib[years[ib] == y]
                m = M_ALL if scope == 'all' else M_SCHOOL
                if len(pool) < m:
                    continue
                for (c, meas), v in measure_set(Zo, Za, labs_sets, draw(brng, pool, m)).items():
                    boot.append((scope, sid, y, c, meas, b, v))
        del yb
        if b % 10 == 0:
            C.log(model=model, boot=b)
    bt = pd.DataFrame(boot, columns=['scope', 'scope_id', 'year', 'corpus', 'measure', 'rep', 'value'])
    return pt, bt


def summarize_year(pt, bt):
    """Per (scope, id, measure, year): orig, ai, gap = orig - ai with intervals; and per (scope, id, measure): post-minus-pre change for each corpus and the gap."""
    out, chg = [], []
    key = ['scope', 'scope_id', 'measure']
    wide_b = bt.pivot_table(index=key + ['year', 'rep'], columns='corpus', values='value').reset_index()
    wide_b['gap'] = wide_b['orig'] - wide_b['ai']
    for k, g in wide_b.groupby(key + ['year']):
        row = dict(zip(key + ['year'], k))
        for v in ('orig', 'ai', 'gap'):
            row[v + '_lo'], row[v + '_hi'] = np.percentile(g[v], [2.5, 97.5])
        out.append(row)
    ints = pd.DataFrame(out)
    pw = pt.pivot_table(index=key + ['year'], columns='corpus', values='value').reset_index()
    pw['gap'] = pw['orig'] - pw['ai']
    yr = pw.merge(ints, on=key + ['year'], how='left')
    # post minus pre (2023-2026 mean minus 2016-2022 mean), per replicate for the intervals
    def period_change(w):
        pre = w[w['year'].isin(PRE)].groupby(key + (['rep'] if 'rep' in w else []))[['orig', 'ai', 'gap']].mean()
        post = w[w['year'].isin(POST)].groupby(key + (['rep'] if 'rep' in w else []))[['orig', 'ai', 'gap']].mean()
        return (post - pre).dropna()
    est = period_change(pw)
    bch = period_change(wide_b).reset_index()
    for k, row in est.iterrows():
        g = bch[(bch['scope'] == k[0]) & (bch['scope_id'] == k[1]) & (bch['measure'] == k[2])]
        r = dict(zip(key, k))
        for v in ('orig', 'ai', 'gap'):
            r[v] = float(row[v])
            r[v + '_lo'], r[v + '_hi'] = (np.percentile(g[v], [2.5, 97.5]) if len(g) > 5 else (np.nan, np.nan))
        chg.append(r)
    return yr, pd.DataFrame(chg)


# ---------------------------------------------------------------- labs
def lab_tables(papers, Zo, Za, labs_sets, labs, rng):
    years = papers['year'].to_numpy()
    rows = []
    for lab, idx in labs.items():
        pre, post = idx[np.isin(years[idx], PRE)], idx[np.isin(years[idx], POST)]
        if len(pre) < M_LAB or len(post) < M_LAB:
            continue
        for per, pool in (('pre', pre), ('post', post)):
            acc = {}
            for _ in range(LAB_DRAWS):
                for k, v in measure_set(Zo, Za, labs_sets, draw(rng, pool, M_LAB)).items():
                    acc.setdefault(k, []).append(v)
            for (c, meas), v in acc.items():
                rows.append(dict(lab_id=lab, period=per, corpus=c, measure=meas, value=float(np.mean(v)), n=int(len(pool))))
    return pd.DataFrame(rows)


def lab_summary(df, lab_school):
    """Mean over labs of post - pre (per corpus and the gap) with a cluster bootstrap over labs, overall and per school."""
    out = []
    w = df.pivot_table(index=['lab_id', 'measure', 'period'], columns='corpus', values='value').reset_index()
    p = w.pivot_table(index=['lab_id', 'measure'], columns='period', values=['orig', 'ai']).dropna()
    for meas in sorted(df['measure'].unique()):
        q = p.xs(meas, level='measure')
        d_o = (q[('orig', 'post')] - q[('orig', 'pre')]).to_numpy(); d_a = (q[('ai', 'post')] - q[('ai', 'pre')]).to_numpy()
        labs = q.index.to_numpy()
        sch = np.array([lab_school.get(x, '?') for x in labs])
        for name, sel in [('all', np.ones(len(labs), bool))] + [(s, sch == s) for s in sorted(set(sch))]:
            if sel.sum() < 5:
                continue
            row = dict(measure=meas, scope=name, labs=int(sel.sum()))
            rng = np.random.default_rng(C.SEED)
            bi = rng.integers(0, sel.sum(), (1000, sel.sum()))
            for tag, v in (('orig', d_o[sel]), ('ai', d_a[sel]), ('gap', d_o[sel] - d_a[sel])):
                bs = v[bi].mean(1)
                row[tag + '_change'] = float(v.mean()); row[tag + '_lo'], row[tag + '_hi'] = np.percentile(bs, [2.5, 97.5])
            for c in ('orig', 'ai'):
                row[c + '_pre'] = float(q[(c, 'pre')].to_numpy()[sel].mean()); row[c + '_post'] = float(q[(c, 'post')].to_numpy()[sel].mean())
            out.append(row)
    return pd.DataFrame(out)


def run_geom(model, style):
    papers, lp, Xo, Xa, meta_o, meta_a = load_pair(model, style)
    C.log(model=model, style=style, papers=len(papers))
    labs_sets = label_sets(model, papers, Xo, Xa)
    Zo, _ = N.center_normalize(Xo); Za, _ = N.center_normalize(Xa)
    cl, groups, school_mask, labs = lab_structure(papers, lp)
    rng = np.random.default_rng(C.SEED)
    pt, bt = year_tables(model, papers, Zo, Za, labs_sets, cl, groups, school_mask, rng)
    yr, chg = summarize_year(pt, bt)
    tag = f'{style}_{model}'
    RES.mkdir(parents=True, exist_ok=True)
    yr.assign(model=model, style=style).to_parquet(RES / f'geom_year_{tag}.parquet', index=False)
    chg.assign(model=model, style=style).to_parquet(RES / f'geom_change_{tag}.parquet', index=False)
    lab_school = lp.drop_duplicates('lab_id').set_index('lab_id')['school'].to_dict()
    ld = lab_tables(papers, Zo, Za, labs_sets, labs, rng)
    ls = lab_summary(ld, lab_school)
    ld.assign(model=model, style=style).to_parquet(RES / f'geom_lab_{tag}.parquet', index=False)
    ls.assign(model=model, style=style).to_parquet(RES / f'geom_labsummary_{tag}.parquet', index=False)
    info = {n: v[3] | dict(k=v[2]) for n, v in labs_sets.items()}
    # how much a paper's topic moves under rewriting
    info['topic_stability'] = {n: float((v[0] == v[1]).mean()) for n, v in labs_sets.items()}
    cs = (Zo * Za).sum(1)
    info['cos_centred'] = dict(mean=float(cs.mean()), p05=float(np.percentile(cs, 5)), median=float(np.median(cs)))
    (RES / f'geom_info_{tag}.json').write_text(json.dumps(dict(model=model, style=style, papers=len(papers), orig_revision=(meta_o or {}).get('revision'),
                                                              ai_revision=(meta_a or {}).get('revision'), **info), default=str))
    C.log(done=tag, year_rows=len(yr), labs=int(ls[ls.scope == 'all']['labs'].max()) if len(ls) else 0)


# ---------------------------------------------------------------- novelty
def run_novelty(model, style):
    papers, lp, Xo, Xa, meta_o, meta_a = load_pair(model, style)
    years = papers['year'].to_numpy()
    first = lp.sort_values('lab_id').drop_duplicates('paper_id').set_index('paper_id')['lab_id']
    cluster = papers['paper_id'].map(first).fillna('none').to_numpy()
    pos = {p: i for i, p in enumerate(papers['paper_id'])}
    mem = L.memberships(lp)
    mem['idx'] = mem['paper_id'].map(pos)
    scopes = [('all', 'all', np.arange(len(papers)))] + [(s, i, g['idx'].to_numpy()) for (s, i), g in mem.groupby(['scope', 'scope_id'])]
    res = {}
    for c, X in (('orig', Xo), ('ai', Xa)):
        Z, _ = N.center_normalize(X)
        r = N.novelty_scopes(Z, years, scopes, ks=(1, 3, 5), nn=5, cap=2000, seed=C.SEED, dev=None)
        res[c] = pd.DataFrame(dict(scope=r['scope'], scope_id=r['scope_id'], paper=r['paper'].astype(int), k=r['k'].astype(int), n_ref=r['n_ref'].astype(int),
                                   nov_max_cap=r['nov_max_cap'], nov_nn_cap=r['nov_nn_cap'], nov_max=r['nov_max'], nov_nn=r['nov_nn']))
    d = res['orig'].merge(res['ai'], on=['scope', 'scope_id', 'paper', 'k', 'n_ref'], suffixes=('_o', '_a'))
    d['year'] = years[d['paper']]; d['cluster'] = cluster[d['paper']]
    min_ref = {'all': 100, 'school': 100, 'dept': 20, 'lab': 5}
    trend, contrast = [], []
    for scope in ('all', 'school', 'dept', 'lab'):
        g0 = d[(d['scope'] == scope) & (d['n_ref'] >= min_ref[scope]) & (d['year'] >= 2017)]
        groups = [(sid, g) for sid, g in g0.groupby('scope_id')] if scope == 'school' else [('all' if scope == 'all' else 'pooled', g0)]
        for sid, g1 in groups:
            for k, g in g1.groupby('k'):
                for meas in ('nov_nn_cap', 'nov_max_cap'):
                    vo, va = g[meas + '_o'].to_numpy(), g[meas + '_a'].to_numpy()
                    cl, yr = g['cluster'].to_numpy(), g['year'].to_numpy()
                    ok = ~(np.isnan(vo) | np.isnan(va))
                    vo, va, cl, yr = vo[ok], va[ok], cl[ok], yr[ok]
                    if len(vo) < 50:
                        continue
                    byo = M.mean_by_year(vo, yr, cl, reps=200); bya = M.mean_by_year(va, yr, cl, reps=200); byg = M.mean_by_year(vo - va, yr, cl, reps=200)
                    for y in byo:
                        trend.append(dict(model=model, style=style, scope=scope, scope_id=sid, k=int(k), measure=meas, year=y, orig=byo[y][0], orig_lo=byo[y][1], orig_hi=byo[y][2],
                                          ai=bya[y][0], ai_lo=bya[y][1], ai_hi=bya[y][2], gap=byg[y][0], gap_lo=byg[y][1], gap_hi=byg[y][2], n=byo[y][3]))
                    post = yr >= 2023
                    row = dict(model=model, style=style, scope=scope, scope_id=sid, k=int(k), measure=meas, n=int(len(vo)))
                    for tag, v in (('orig', vo), ('ai', va), ('gap', vo - va)):
                        est, lo, hi, nc = M.diff_ci(v, cl, post, reps=500)
                        row[tag + '_change'], row[tag + '_lo'], row[tag + '_hi'], row['clusters'] = est, lo, hi, nc
                    # the part of the original's change that the AI corpus does not show: orig change - ai change (paired per paper)
                    contrast.append(row)
    RES.mkdir(parents=True, exist_ok=True)
    tag = f'{style}_{model}'
    pd.DataFrame(trend).to_parquet(RES / f'novelty_trend_{tag}.parquet', index=False)
    pd.DataFrame(contrast).to_parquet(RES / f'novelty_contrast_{tag}.parquet', index=False)
    C.log(done=f'novelty_{tag}', trend=len(trend), contrast=len(contrast))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['geom', 'novelty'])
    ap.add_argument('--model', required=True); ap.add_argument('--style', default='polish', choices=list(STYLE_SUFFIX))
    a = ap.parse_args()
    (run_geom if a.cmd == 'geom' else run_novelty)(a.model, a.style)
    sys.stdout.flush()
