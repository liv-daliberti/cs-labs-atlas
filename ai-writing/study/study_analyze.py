"""The pre/post-ChatGPT homogenization analysis on a sealed snapshot (README.md). One layer per command; every layer writes CSV + parquet tables.

  study_analyze.py ai          writing style / AI share (detector v3, main body vs main + appendix), IPW, false-positive correction
  study_analyze.py topics      topic mix: LLM-topic share, within-lab topic entropy, cross-lab topic divergence
  study_analyze.py embed       embedding diversity: within-lab, cross-lab (same school) and cross-school mean pairwise distance, 7 models
  study_analyze.py citation    citation novelty (Uzzi z, Rao-Stirling, disruption) pre/post
  study_analyze.py event       lab event study around AI uptake (pre-registered adoption rule, Callaway-Sant'Anna)
  study_analyze.py all
Post = 2023-2025, pre = 2016-2022 (2022 dropped in a sensitivity); window 2016-2025, no 2026. Intervals: lab-cluster bootstrap (stratified by school).
Scopes: ALL (12 schools), EXCL_PARTIAL (9 schools without harvard/jhu/washu), and each school. Samples: all strict membership; period_supported only.
"""
import argparse
import json
import time

import numpy as np
import pandas as pd

import study_common as C
import study_labstats as LS

B = 400
OUT = {}


def setup(snap_id):
    out = C.results_dir(snap_id)
    OUT.update(snap=C.snapshot_dir(snap_id), out=out, tab=out / 'tables')
    OUT['tab'].mkdir(parents=True, exist_ok=True)
    pan = pd.read_parquet(out / 'work' / 'panel.parquet')
    lp = pd.read_parquet(out / 'work' / 'lab_papers.parquet')
    return pan, lp


def save(name, df):
    df.to_csv(OUT['tab'] / f'{name}.csv', index=False)
    df.to_parquet(OUT['tab'] / f'{name}.parquet')
    print(name, df.shape, flush=True)


def scopes():
    """(scope name, school list)."""
    yield 'ALL', C.SCHOOLS
    yield 'EXCL_PARTIAL', [s for s in C.SCHOOLS if s not in C.PARTIAL]
    for s in C.SCHOOLS:
        yield s, [s]


def samples(lp):
    yield 'all', lp
    if 'period_supported' in lp:
        yield 'period_supported', lp[lp['period_supported']]


def ratio_layer(name, d, num, den=None, transform=None, only=None, seed=1):
    """Series and contrasts of sum(num)/sum(den) over every scope and sample. d: lab-paper rows (k, lab_id, school, year, num, den)."""
    sers, cons = [], []
    for sm, dd in samples(d):
        for sc, schools in scopes():
            if only and sc not in only:
                continue
            x = dd[dd['school'].isin(schools)]
            if x.empty or x[num].notna().sum() < 30:
                continue
            x = x[x[num].notna()]
            S, N, labs = LS.lab_year(x, 'lab_id', 'year', num, den)
            strata = pd.Series(x.drop_duplicates('lab_id').set_index('lab_id')['school']).reindex(labs).to_numpy()
            W = LS.weights(strata, B, seed)
            ser, con = LS.tables(dict(measure=name, scope=sc, sample=sm, n_labs=len(labs)), S, N, W, transform)
            sers.append(ser)
            cons.append(con)
    return pd.concat(sers, ignore_index=True), pd.concat(cons, ignore_index=True)


def lab_rows(pan, lp, cols):
    return lp.merge(pan[['k'] + cols], on='k', how='left', suffixes=('', '_p'))


def layer_ai(pan, lp):
    d = lab_rows(pan, lp, ['ai_share_main', 'ai_share_main_appendix', 'flag_abstract', 'trained_on_v3', 'w_ft', 'kobak_abs', 'abstained_share_main', 'in_universe', 'has_ft'])
    d = d[~d['trained_on_v3'].astype(bool)].copy()            # detector-training papers are out of every rate (v3 trained_on)
    for tag, col in (('main', 'ai_share_main'), ('main_appendix', 'ai_share_main_appendix')):
        d[f'heavy_{tag}'] = np.where(d[col].notna(), (d[col] >= 0.25).astype(float), np.nan)
        d[f'any_{tag}'] = np.where(d[col].notna(), (d[col] > 0).astype(float), np.nan)
        d[f'dose_{tag}'] = d[col]
    d['abs_flag'] = d['flag_abstract'].astype(float)
    d['kobak'] = d['kobak_abs']
    sers, cons = [], []
    for m in ('heavy_main', 'dose_main', 'any_main', 'heavy_main_appendix', 'dose_main_appendix', 'abs_flag', 'kobak'):
        s, c = ratio_layer(m, d, m)
        sers.append(s); cons.append(c)
    # IPW: full-text selection weights (existing fit): weighted share of heavy papers
    w = d[d['heavy_main'].notna() & d['w_ft'].notna()].copy()
    w['wx'] = w['heavy_main'] * w['w_ft']
    s, c = ratio_layer('heavy_main_ipw', w, 'wx', 'w_ft', only=['ALL', 'EXCL_PARTIAL'])
    sers.append(s); cons.append(c)
    ser, con = pd.concat(sers), pd.concat(cons)
    save('ai_series', ser)
    save('ai_contrasts', con)
    # false-positive correction of the mean AI-passage share: a = (f - fpr) / (1 - miss - fpr)
    op = json.loads((OUT['snap'] / 'ai' / 'detector_v3' / 'operating_point.json').read_text())
    fpr = op['test_fpr']
    rows = []
    for _, r in ser[(ser.measure == 'dose_main') & (ser['sample'] == 'all') & ser.scope.isin(['ALL', 'EXCL_PARTIAL'])].iterrows():
        for miss, lab in ((0.0, 'miss0'), (0.066, 'miss6.6')):
            for fp, fl in ((fpr['rate'], 'fpr'), (fpr['ci'][1], 'fpr_hi')):
                f = lambda x: max((x - fp) / (1 - miss - fp), 0.0)  # noqa: E731
                rows.append(dict(scope=r.scope, year=r.year, observed=r.est, lo=r.lo, hi=r.hi, corrected=f(r.est), corrected_lo=f(r.lo), corrected_hi=f(r.hi), miss=lab, fpr=fl))
    save('ai_fp_corrected', pd.DataFrame(rows))
    # coverage of the scored full-text sample
    cov = pan.groupby(['school', 'year']).agg(papers=('k', 'size'), scored=('has_ft', 'sum'), in_universe=('in_universe', 'sum')).reset_index()
    save('ai_coverage', cov)


def layer_topics(pan, lp):
    d = lab_rows(pan, lp, ['llm_text', 'has_abs', 'topic_sub'])
    d['llm'] = np.where(d['has_abs'], d['llm_text'].astype(float), np.nan)
    s, c = ratio_layer('llm_topic_share', d, 'llm')
    save('topics_llm_series', s); save('topics_llm_contrasts', c)
    # within-lab entropy of OpenAlex subfields, rarefied to 8 papers per lab-year (bits)
    t = d[d['topic_sub'].notna()].copy()
    rng = np.random.default_rng(7)
    rows = []
    for (lab, y), g in t.groupby(['lab_id', 'year']):
        if len(g) < 8:
            continue
        v = g['topic_sub'].to_numpy()
        h = []
        for _ in range(10):
            _, cnt = np.unique(rng.choice(v, 8, replace=False), return_counts=True)
            p = cnt / 8
            h.append(float(-(p * np.log2(p)).sum()))
        rows.append((lab, g['school'].iloc[0], y, float(np.mean(h))))
    ent = pd.DataFrame(rows, columns=['lab_id', 'school', 'year', 'h'])
    ent['one'] = 1.0
    s, c = ratio_layer('topic_entropy_bits', ent, 'h', 'one')
    save('topics_entropy_series', s); save('topics_entropy_contrasts', c)
    # cross-lab divergence: mean JSD between labs' subfield mixes within school, rarefied to m papers, pre vs post, labs present in both
    subs = sorted(t['topic_sub'].unique())
    si = {x: i for i, x in enumerate(subs)}
    out = []
    for m in (10, 20):
        sers_lab = {}
        for per, yrs in (('pre', LS.PRE), ('post', LS.POST)):
            for lab, g in t[t['year'].isin(yrs)].groupby('lab_id'):
                if len(g) < m:
                    continue
                idx = g['topic_sub'].map(si).to_numpy()
                P = np.zeros(len(subs))
                for _ in range(10):
                    P += np.bincount(rng.choice(idx, m, replace=False), minlength=len(subs)) / m
                sers_lab[(lab, per)] = (P / 10, g['school'].iloc[0])
        labs = sorted({k[0] for k in sers_lab if (k[0], 'pre') in sers_lab and (k[0], 'post') in sers_lab})
        sch = np.array([sers_lab[(l, 'pre')][1] for l in labs])
        D = {}
        for per in ('pre', 'post'):
            P = np.array([sers_lab[(l, per)][0] for l in labs])
            M = (P[:, None, :] + P[None, :, :]) / 2
            with np.errstate(divide='ignore', invalid='ignore'):
                kl = lambda a, b: np.nansum(np.where(a > 0, a * np.log2(a / b), 0), axis=-1)  # noqa: E731
                D[per] = 0.5 * kl(P[:, None, :], M) + 0.5 * kl(P[None, :, :], M)
        for sc, schools in scopes():
            ix = np.where(np.isin(sch, schools))[0]
            if len(ix) < 20:
                continue
            same = (sch[ix][:, None] == sch[ix][None, :]) & ~np.eye(len(ix), dtype=bool)
            Wb = LS.weights(sch[ix], B, 11)
            res = {}
            for per in ('pre', 'post'):
                Dm = D[per][np.ix_(ix, ix)] * same
                num = np.einsum('bi,ij,bj->b', Wb, Dm, Wb) - (Wb ** 2) @ np.diag(Dm)
                den = np.einsum('bi,ij,bj->b', Wb, same.astype(float), Wb) - (Wb ** 2) @ np.diag(same.astype(float))
                res[per] = num / den
            d_ = res['post'] - res['pre']
            lo, hi = LS.ci(d_[1:])
            out.append(dict(measure=f'cross_lab_jsd_m{m}', scope=sc, n_labs=len(ix), pre=res['pre'][0], post=res['post'][0], est=d_[0], lo=lo, hi=hi,
                            contrast='post_minus_pre', sample='all'))
    save('topics_crosslab_jsd', pd.DataFrame(out))


def load_emb(snap, model, panel_pid):
    """Centered, unit-length abstract vectors aligned to panel rows (NaN rows dropped): returns (row index, X float32)."""
    ids, mats = [], []
    for s in C.EMB_SCHOOLS:
        p = snap / 'embeddings' / model / s / 'abstract.npz'
        if p.exists():
            z = np.load(p)
            ids.append(z['ids']); mats.append(z['M'])
    ids = np.concatenate(ids)
    X = np.vstack(mats).astype(np.float32)
    pos = pd.Series(np.arange(len(ids)), index=ids)
    pid = pd.Series(panel_pid)
    ok = pid.isin(pos.index).to_numpy()
    X = X[pos.loc[pid[ok]].to_numpy()]
    X -= X.mean(0)
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    return np.where(ok)[0], X


def layer_embed(pan, lp):
    models = C.MODELS
    allcons, allser = [], []
    for mi, model in enumerate(models):
        t0 = time.time()
        rows, X = load_emb(OUT['snap'], model, pan['paper_id'].to_numpy())
        pe = pan.iloc[rows][['k', 'topic_sub']].reset_index(drop=True)
        variants = [('raw', X)]
        if model == C.HEADLINE_MODEL:       # topic-residualised: remove the OpenAlex subfield centroid, then renormalise (spread within topic)
            R = X.copy()
            for sub, ix in pe.groupby('topic_sub').indices.items():
                if len(ix) >= 30:
                    R[ix] -= R[ix].mean(0)
            R /= np.linalg.norm(R, axis=1, keepdims=True) + 1e-9
            variants.append(('topic_residual', R))
        for var, V in variants:
            d = lp.merge(pe.assign(r=np.arange(len(pe))), on='k', how='inner')
            for sm, dd in samples(d):
                ser, con = embed_one(dd, V, model, var, sm, headline=(model == C.HEADLINE_MODEL))
                allser.append(ser); allcons.append(con)
        print(model, round(time.time() - t0), 's', flush=True)
    save('embed_series', pd.concat(allser, ignore_index=True))
    save('embed_contrasts', pd.concat(allcons, ignore_index=True))


def embed_one(d, V, model, var, sm, headline, nmin=5):
    """Within-lab, cross-lab (same school) and cross-school mean pairwise distance, from sufficient statistics."""
    d = d.drop_duplicates(['lab_id', 'k'])
    key = d['lab_id'] + '|' + d['year'].astype(str)
    grp = pd.Series(np.arange(len(d))).groupby(key.to_numpy()).indices
    labs = np.sort(d['lab_id'].unique())
    li = {l: i for i, l in enumerate(labs)}
    sch_of = d.drop_duplicates('lab_id').set_index('lab_id')['school']
    lab_school = sch_of.reindex(labs).to_numpy()
    r = d['r'].to_numpy()
    sums = {}          # (year) -> list of (lab idx, n, vector)
    for kk, ix in grp.items():
        lab, y = kk.rsplit('|', 1)
        if len(ix) >= nmin:
            sums.setdefault(int(y), []).append((li[lab], len(ix), V[r[ix]].sum(0)))
    L, T = len(labs), len(LS.YEARS)
    n = np.zeros((L, T)); ss = np.zeros((L, T))
    for y, lst in sums.items():
        for l, cnt, v in lst:
            n[l, y - LS.YEARS[0]] = cnt
            ss[l, y - LS.YEARS[0]] = float(v @ v)
    out_s, out_c = [], []
    for sc, schools in scopes():
        msk = np.isin(lab_school, schools)
        if msk.sum() < 5:
            continue
        W = LS.weights(lab_school[msk], B if headline else 150, 5)
        meta = dict(model=model, variant=var, scope=sc, sample=sm, n_labs=int(msk.sum()))
        # within lab: 1 - sum(|S|^2 - n) / sum n(n-1)
        Sw, Nw = (ss - n)[msk], (n * (n - 1))[msk]
        s_, c_ = LS.tables(dict(meta, level='within_lab'), Sw, Nw, W, lambda x: 1 - x)
        out_s.append(s_); out_c.append(c_)
        if sc not in ('ALL', 'EXCL_PARTIAL') and not headline:
            continue
        # cross-lab, same school: pairs of papers from different labs of one school, per year
        num = np.zeros((W.shape[0], T)); den = np.zeros_like(num)
        for sname in np.unique(lab_school[msk]):
            sidx = np.where(msk & (lab_school == sname))[0]
            Ws = W[:, np.cumsum(msk)[sidx] - 1]
            for y, lst in sums.items():
                lst = [x for x in lst if x[0] in set(sidx)]
                if len(lst) < 2:
                    continue
                loc = {l: i for i, (l, _, _) in enumerate(lst)}
                col = np.array([np.where(sidx == l)[0][0] for l, _, _ in lst])
                Sv = np.array([v for _, _, v in lst]); nv = np.array([c for _, c, _ in lst], float)
                G = Sv @ Sv.T
                w = Ws[:, col]
                t = y - LS.YEARS[0]
                num[:, t] += np.einsum('bi,ij,bj->b', w, G, w) - (w ** 2) @ np.diag(G)
                den[:, t] += (w @ nv) ** 2 - (w ** 2) @ (nv ** 2)
        s_, c_ = cross_tables(dict(meta, level='cross_lab_same_school'), num, den)
        out_s.append(s_); out_c.append(c_)
        if sc in ('ALL', 'EXCL_PARTIAL'):       # cross school: all pairs from different schools, per year
            numx = np.zeros((W.shape[0], T)); denx = np.zeros_like(numx)
            for y, lst in sums.items():
                t = y - LS.YEARS[0]
                tot = np.zeros((W.shape[0], V.shape[1])); ntot = np.zeros(W.shape[0]); sq = np.zeros(W.shape[0]); nsq = np.zeros(W.shape[0])
                for sname in np.unique(lab_school[msk]):
                    sidx = np.where(msk & (lab_school == sname))[0]
                    lst2 = [x for x in lst if x[0] in set(sidx)]
                    if not lst2:
                        continue
                    col = np.array([np.where(sidx == l)[0][0] for l, _, _ in lst2])
                    Sv = np.array([v for _, _, v in lst2]); nv = np.array([c for _, c, _ in lst2], float)
                    w = W[:, np.cumsum(msk)[sidx] - 1][:, col]
                    Ts = w @ Sv; ns = w @ nv
                    tot += Ts; ntot += ns; sq += (Ts ** 2).sum(1); nsq += ns ** 2
                numx[:, t] = (tot ** 2).sum(1) - sq
                denx[:, t] = ntot ** 2 - nsq
            s_, c_ = cross_tables(dict(meta, level='cross_school'), numx, denx)
            out_s.append(s_); out_c.append(c_)
    return pd.concat(out_s, ignore_index=True), pd.concat(out_c, ignore_index=True)


def cross_tables(meta, num, den):
    """Series/contrasts from (B+1, T) numerator and denominator sums of pair similarities (distance = 1 - ratio)."""
    ratio = num / den
    dist = 1 - ratio
    est, lo, hi = LS.describe(dist)
    ser = pd.DataFrame(dict(meta, year=LS.YEARS, est=est, lo=lo, hi=hi, n=den[0]))
    rows = []
    for name, (post, pre) in LS.CONTRASTS.items():
        pi = [y - LS.YEARS[0] for y in pre]; po = [y - LS.YEARS[0] for y in post]
        with np.errstate(invalid='ignore', divide='ignore'):
            dpre = 1 - num[:, pi].sum(1) / den[:, pi].sum(1)
            dpost = 1 - num[:, po].sum(1) / den[:, po].sum(1)
        d = dpost - dpre
        lo_, hi_ = LS.ci(d[1:])
        rows.append(dict(meta, contrast=name, est=float(d[0]), lo=lo_, hi=hi_, pre=float(dpre[0]), post=float(dpost[0])))
    return ser, pd.DataFrame(rows)


def layer_citation(pan, lp):
    d = lab_rows(pan, lp, ['z_med', 'z_p10', 'rs_sub', 'h_sub', 'cd5'])
    sers, cons = [], []
    for m in ('z_med', 'z_p10', 'rs_sub', 'h_sub', 'cd5'):
        s, c = ratio_layer('cit_' + m, d, m)
        sers.append(s); cons.append(c)
    save('citation_series', pd.concat(sers)); save('citation_contrasts', pd.concat(cons))


def layer_event(pan, lp):
    import event_study as ES
    d = lab_rows(pan, lp, ['ai_share_main', 'trained_on_v3'])
    d = d[d['ai_share_main'].notna()].copy()
    d['ge25'] = (d['ai_share_main'] >= 0.25).astype(float)
    g = d.groupby(['lab_id', 'year'])
    dose = g.agg(n_scored=('ge25', 'size'), share_ge25=('ge25', 'mean')).reset_index()
    oos = d[~d['trained_on_v3']].groupby(['lab_id', 'year']).agg(n_scored_oos=('ge25', 'size'), share_ge25_oos=('ge25', 'mean')).reset_index()
    dose = dose.merge(oos, on=['lab_id', 'year'], how='left')
    spec = ES.PRE['adoption']['specs']['S1_primary']
    ad, info = ES.adoption_spec(dose[dose.year <= C.LAST], 'S1_primary', spec)
    save('event_adoption', ad.assign(**{k: v for k, v in info.items() if k != 'spec'}))
    lab_school = lp.drop_duplicates('lab_id').set_index('lab_id')['school']
    # outcomes: lab-year within-lab MPD (SPECTER2 proximity), citation z_med, LLM-topic share
    rows, X = load_emb(OUT['snap'], C.HEADLINE_MODEL, pan['paper_id'].to_numpy())
    pe = pan.iloc[rows][['k']].reset_index(drop=True).assign(r=np.arange(len(rows)))
    e = lp.merge(pe, on='k').drop_duplicates(['lab_id', 'k'])
    mp = {}
    for (lab, y), gg in e.groupby(['lab_id', 'year']):
        if len(gg) >= 5:
            v = X[gg['r'].to_numpy()].sum(0)
            n = len(gg)
            mp[(lab, y)] = 1 - (float(v @ v) - n) / (n * (n - 1))
    pa = lab_rows(pan, lp, ['z_med', 'llm_text', 'has_abs'])
    zm = pa.groupby(['lab_id', 'year'])['z_med'].agg(['mean', 'size']).query('size >= 5')['mean'].to_dict()
    pa = pa[pa['has_abs']]
    ll = pa.groupby(['lab_id', 'year'])['llm_text'].agg(['mean', 'size']).query('size >= 5')['mean'].to_dict()
    adm = ad[ad.status.isin(['adopter', 'never'])].copy()
    adm['G'] = adm['adopt_year'].fillna(0).astype(int)
    labs = adm['lab_id'].to_numpy()
    G = adm['G'].to_numpy()
    res = []
    for oname, dct, head in (('mpd_specter2_proximity', mp, True), ('uzzi_z_med', zm, False), ('llm_topic_share', ll, False)):
        Y = np.full((len(labs), len(C_Y)), np.nan)
        pos = {l: i for i, l in enumerate(labs)}
        for (l, y), v in dct.items():
            if l in pos and C.FIRST <= y <= C.LAST:
                Y[pos[l], y - C.FIRST] = v
        for sample in ('all', 'excl_partial'):
            sel = np.ones(len(labs), bool) if sample == 'all' else ~lab_school.reindex(labs).isin(C.PARTIAL).to_numpy()
            res += ES.run_one((oname, 'orig', 'S1_primary', sample, Y[sel], G[sel], labs[sel], head and sample == 'all', 300, 200 if head and sample == 'all' else 0))
    save('event_results', pd.DataFrame(res))
    save('event_adoption_summary', ad.groupby('status').size().rename('labs').reset_index().assign(school='ALL'))
    sm = ad.assign(school=ad.lab_id.map(lab_school)).groupby(['school', 'status']).size().rename('labs').reset_index()
    save('event_adoption_by_school', sm)


C_Y = list(range(C.FIRST, C.LAST + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('layer', choices=['ai', 'topics', 'embed', 'citation', 'event', 'all'])
    ap.add_argument('--id', default='2026-11-07')
    a = ap.parse_args()
    pan, lp = setup(a.id)
    todo = ['ai', 'topics', 'citation', 'embed', 'event'] if a.layer == 'all' else [a.layer]
    for l in todo:
        t0 = time.time()
        {'ai': layer_ai, 'topics': layer_topics, 'embed': layer_embed, 'citation': layer_citation, 'event': layer_event}[l](pan, lp)
        print(l, 'done', round(time.time() - t0), 's', flush=True)


if __name__ == '__main__':
    main()
