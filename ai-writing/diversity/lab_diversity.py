"""Every measure per lab x period (pre 2016-2022, post 2023-2026), per lab x placebo split, and per lab x year, with
the lab's AI usage.

families  a measure is computed on the lab's papers that have its input:
            abs  SPECTER2 title+abstract vector     S1-S7 (_abs), N1, N2
            ft   full-text vector (mean of segments) S1-S7 (_ft), S8
            txt  usable full text                   L1-L8 (L5 as L5_mean, L5_sd), fre (mean Flesch reading ease)
            ref  S2 reference list (>= 5 refs)      C1-C4
draws     set-level measures are means over DRAWS equal-size draws: n = the smaller of the two groups compared (at
          least 5) for a period pair; n = 5 for a lab-year. Paper-level measures are plain means over the group.
groups    main: pre vs post; placebo2019: 2016-2018 vs 2019-2022; placebo2020: 2016-2019 vs 2020-2022
lab-specific paper measures (also written per paper for the within-lab analysis):
          N2   the paper's 50-cluster topic is absent from REF_K papers drawn from the lab's abs papers of the 3 previous
               years (mean over NOV_REPS draws; papers from 2019 on)
          L4   share of the paper's distinct word trigrams absent from REF_K of the lab's full texts of the 3 previous
               years (same draws)
          C4   share of the paper's references that are the lab's own papers (any year)
          dist_abs / dist_ft  distance from the centroid of the lab's other papers of the same period
ai usage  per group: n_ai (papers with a score), ai_mean (mean dose: share flagged for the abstract detector, mean
          ai_share for the paragraph detector), ai_high (share flagged / share with ai_share >= 0.25), p_ai_mean (abstract
          score), llm_share (LLM-topic title/abstract share). topic10: the lab's modal 10-cluster abstract topic.
-> lab_diversity.csv (lab x period), lab_diversity_placebo.csv, lab_diversity_year.csv, results/paper_lab_measures.csv.gz
"""
import os, pickle, time, zlib
from collections import Counter
from multiprocessing import Pool
import numpy as np
import pandas as pd
from scipy import sparse
import common as C
import measures as M

DRAWS = int(os.environ.get('AIW_DRAWS', 1000))
MIN_N, YEAR_N, REF_K, NOV_REPS, C1_M = 5, 5, 3, 10, 40
G = {}
FAMILY_MEASURES = {
    'abs': ['S1_abs', 'S2_abs', 'S3_abs', 'S4_abs', 'S5_abs', 'S6_abs', 'S7_abs', 'N1', 'N2'],
    'ft': ['S1_ft', 'S2_ft', 'S3_ft', 'S4_ft', 'S5_ft', 'S6_ft', 'S7_ft', 'S8_ft'],
    'txt': ['L1', 'L2', 'L3', 'L4', 'L5_mean', 'L5_sd', 'L6', 'L7', 'L8', 'fre'],
    'ref': ['C1', 'C2', 'C3', 'C4'],
}


def setup():
    t0 = time.time()
    papers, meta = C.load_papers()
    F = pd.read_parquet(C.DATA / 'paper_features.parquet').set_index('key')
    ai, src = C.load_ai()
    akeys, AX = C.load_abstract_embeddings()
    Uabs, _ = C.center_normalize(AX)
    G['abs_row'] = {k: i for i, k in enumerate(akeys)}; G['Uabs'] = Uabs
    ft = C.load_fulltext_means()
    fkeys = [k for k in ft if k in F.index and F.at[k, 'has_ft']]
    G['ft_row'] = {k: i for i, k in enumerate(fkeys)}
    G['Uft'] = C.center_normalize(np.vstack([ft[k][2] for k in fkeys]))[0] if fkeys else np.zeros((0, 768), np.float32)
    T = sparse.load_npz(C.LOCAL / 'tfidf.npz')
    G['T'] = T; G['txt_row'] = {str(k): i for i, k in enumerate(np.load(C.LOCAL / 'tfidf_keys.npy'))}
    Z = np.load(C.LOCAL / 'trigrams.npz')
    off, tri = Z['off'], Z['tri']
    G['tri'] = {str(k): tri[off[i]:off[i + 1]] for i, k in enumerate(Z['keys'])}
    with open(C.LOCAL / 'excerpts.pkl', 'rb') as f:
        G['exc'] = pickle.load(f)
    tops = np.load(C.DATA / 'topics.npz')
    G['D_abs'] = M.centroid_distances(tops['c50_abs'])
    G['D_ft'] = M.centroid_distances(tops['c50_ft']) if 'c50_ft' in tops.files else None
    refs = C.match_refs(papers)
    venue_code = {}
    G['ref'] = {}
    for p in papers:
        r = refs.get(p['key'])
        if not r or not r[1] or len(r[1]) < 5:
            continue
        ids = [x[0] for x in r[1]]
        ven = np.array([venue_code.setdefault(x[2], len(venue_code)) for x in r[1] if x[2]], np.int64)
        ages = np.array([p['year'] - x[1] for x in r[1] if x[1] and -1 <= p['year'] - x[1] <= 60], float)
        G['ref'][p['key']] = (r[0], ids, ven, ages)
    G['s2id'] = {k: v[0] for k, v in refs.items() if v[0]}
    G['F'] = F; G['ai'] = ai; G['ai_source'] = src; G['meta'] = meta
    labs = {}
    for p in papers:
        for l in p['labs']:
            labs.setdefault(l, []).append(p)
    G['labs'] = labs
    C.log(setup_seconds=round(time.time() - t0), labs=len(labs), abs=len(akeys), ft=len(fkeys), txt=len(G['txt_row']), ref=len(G['ref']),
          ai_source=src, draws=DRAWS)


def fnum(F, key, col):
    v = F.at[key, col] if key in F.index else np.nan
    return float(v) if v is not None and pd.notna(v) else np.nan


class Lab:
    """One lab's papers per family, with the matrices its draws index."""

    def __init__(self, lab):
        P = sorted(G['labs'][lab], key=lambda p: (p['year'], p['key']))
        F = G['F']
        self.lab, self.P = lab, P
        self.rng = np.random.default_rng([C.SEED, zlib.crc32(lab.encode())])
        self.fam = {}
        a = [p for p in P if p['key'] in G['abs_row']]
        if a:
            U = G['Uabs'][[G['abs_row'][p['key']] for p in a]]
            self.fam['abs'] = dict(P=a, years=np.array([p['year'] for p in a]), U=U, S=U @ U.T,
                                   lab50=np.array([int(fnum(F, p['key'], 'topic50_abs')) for p in a]))
        f = [p for p in P if p['key'] in G['ft_row']]
        if f and G['D_ft'] is not None:
            U = G['Uft'][[G['ft_row'][p['key']] for p in f]]
            self.fam['ft'] = dict(P=f, years=np.array([p['year'] for p in f]), U=U, S=U @ U.T,
                                  lab50=np.array([int(fnum(F, p['key'], 'topic50_ft')) for p in f]))
        t = [p for p in P if p['key'] in G['txt_row']]
        if t:
            Tl = G['T'][[G['txt_row'][p['key']] for p in t]]
            self.fam['txt'] = dict(P=t, years=np.array([p['year'] for p in t]), S=(Tl @ Tl.T).toarray(),
                                   fre=np.array([fnum(F, p['key'], 'fre') for p in t]),
                                   ex=[G['exc'][p['key']][0] for p in t], exz=[G['exc'][p['key']][1] for p in t])
        r = [p for p in P if p['key'] in G['ref']]
        if r:
            self.fam['ref'] = dict(P=r, years=np.array([p['year'] for p in r]), J=M.jaccard_matrix([G['ref'][p['key']][1] for p in r]),
                                   ven=[G['ref'][p['key']][2] for p in r], ages=[G['ref'][p['key']][3] for p in r])
        self.paper = {p['key']: dict(key=p['key'], lab=lab, year=p['year']) for p in P}
        self._paper_measures()

    def _paper_measures(self):
        F = G['F']
        for p in self.P:
            d = self.paper[p['key']]
            for col in ('N1', 'S8', 'L1', 'L2', 'L5_mean', 'L5_sd', 'L7', 'fre'):
                d[col] = fnum(F, p['key'], col)
            d['S8_ft'] = d.pop('S8')
        if 'abs' in self.fam:
            fa = self.fam['abs']
            for i, p in enumerate(fa['P']):
                pool = [np.array([fa['lab50'][j]]) for j in np.flatnonzero((fa['years'] >= p['year'] - 3) & (fa['years'] < p['year']))]
                self.paper[p['key']]['N2'] = M.reference_novelty(np.array([fa['lab50'][i]]), pool, REF_K, self.rng, NOV_REPS) if p['year'] >= 2019 else np.nan
        if 'txt' in self.fam:
            ft = self.fam['txt']
            for i, p in enumerate(ft['P']):
                pool = [G['tri'][ft['P'][j]['key']] for j in np.flatnonzero((ft['years'] >= p['year'] - 3) & (ft['years'] < p['year']))]
                self.paper[p['key']]['L4'] = M.reference_novelty(G['tri'][p['key']], pool, REF_K, self.rng, NOV_REPS) if p['year'] >= 2019 else np.nan
        if 'ref' in self.fam:
            own = {G['s2id'][p['key']] for p in self.P if p['key'] in G['s2id']}
            for p in self.fam['ref']['P']:
                me = G['s2id'].get(p['key'])
                self.paper[p['key']]['C4'] = M.self_share(G['ref'][p['key']][1], own - {me})
        for fam, col in (('abs', 'dist_abs'), ('ft', 'dist_ft')):
            if fam not in self.fam:
                continue
            fa = self.fam[fam]
            for rng_ in (C.PRE, C.POST):
                idx = np.flatnonzero(np.isin(fa['years'], list(rng_)))
                if len(idx) >= 3:
                    for i, d in zip(idx, M.loo_centroid_distance(fa['U'][idx])):
                        self.paper[fa['P'][i]['key']][col] = float(d)

    def set_measures(self, fam, idx):
        f = self.fam[fam]
        if fam in ('abs', 'ft'):
            S = f['S'][np.ix_(idx, idx)]
            out = {f'{k}_{fam}': v for k, v in M.gram_measures(S).items()}
            out.update({f'{k}_{fam}': v for k, v in M.topic_measures(f['lab50'][idx], G['D_abs'] if fam == 'abs' else G['D_ft']).items()})
            return out
        if fam == 'txt':
            fre = f['fre'][idx]
            return dict(L3=M.mean_offdiag(f['S'][np.ix_(idx, idx)]), L6=float(np.nanstd(fre, ddof=1)) if np.isfinite(fre).sum() >= 3 else np.nan,
                        L8=M.compression_ratio([f['ex'][i] for i in idx], [f['exz'][i] for i in idx]))
        ven = np.concatenate([f['ven'][i] for i in idx]); ages = np.concatenate([f['ages'][i] for i in idx])
        return dict(C1=M.venue_entropy(ven, C1_M, self.rng), C2=M.mean_offdiag(f['J'][np.ix_(idx, idx)]), C3=M.age_spread(ages))

    def paper_means(self, fam, keys):
        cols = {'abs': ['N1', 'N2'], 'ft': ['S8_ft'], 'txt': ['L1', 'L2', 'L4', 'L5_mean', 'L5_sd', 'L7', 'fre'], 'ref': ['C4']}[fam]
        out = {}
        for c in cols:
            v = np.array([self.paper[k].get(c, np.nan) for k in keys], float)
            out[c] = float(np.nanmean(v)) if np.isfinite(v).any() else np.nan
        return out

    def group_info(self, years):
        P = [p for p in self.P if p['year'] in years]
        ai = [G['ai'][p['key']] for p in P if p['key'] in G['ai']]
        pa = [a['p_ai'] for a in ai if a.get('p_ai') is not None]
        return dict(n_papers=len(P), n_ai=len(ai), ai_mean=float(np.mean([a['dose'] for a in ai])) if ai else np.nan,
                    ai_high=float(np.mean([a['flag'] for a in ai])) if ai else np.nan, p_ai_mean=float(np.mean(pa)) if pa else np.nan,
                    llm_share=float(np.mean([p['llm'] for p in P])) if P else np.nan)

    def compare(self, groups, n=None):
        """groups: list of year ranges. -> one dict per group: info, per-family n and draw n, every measure."""
        rows = [dict(self.group_info(g)) for g in groups]
        for fam, f in self.fam.items():
            pos = [np.flatnonzero(np.isin(f['years'], list(g))) for g in groups]
            for r, p in zip(rows, pos):
                r[f'n_{fam}'] = len(p)
            m, vals = M.resample(lambda gi, idx: self.set_measures(fam, pos[gi][idx]), [len(p) for p in pos], DRAWS, MIN_N, n, self.rng)
            if m is None:
                continue
            for r, v, p in zip(rows, vals, pos):
                r[f'ndraw_{fam}'] = m
                r.update(v)
                r.update(self.paper_means(fam, [f['P'][i]['key'] for i in p]))
        return rows


def topic10(P):
    F = G['F']
    t = [fnum(F, p['key'], 'topic10_abs') for p in P]
    t = [int(x) for x in t if np.isfinite(x)]
    return Counter(t).most_common(1)[0][0] if t else -1


def lab_job(lab):
    L = Lab(lab)
    base = dict(lab=lab, school=G['meta'][lab]['school'], pi=G['meta'][lab]['pi'], name=G['meta'][lab]['name'], dept=G['meta'][lab]['dept'],
                topic10=topic10(L.P))
    main, plac, year = [], [], []
    for comp, (a, b) in C.COMPARISONS.items():
        if sum(p['year'] in a for p in L.P) < MIN_N or sum(p['year'] in b for p in L.P) < MIN_N:
            continue
        ra, rb = L.compare([a, b])
        names = ('pre', 'post') if comp == 'main' else ('early', 'late')
        for nm, r, yrs in ((names[0], ra, a), (names[1], rb, b)):
            row = dict(base, period=nm, years=f'{yrs[0]}-{yrs[-1]}', **r)
            (main if comp == 'main' else plac).append(row if comp == 'main' else dict(row, comparison=comp))
    for y in C.YEARS:
        if sum(p['year'] == y for p in L.P) >= YEAR_N:
            (r,) = L.compare([range(y, y + 1)], n=YEAR_N)
            year.append(dict(base, year=y, **r))
    period = {k: ('pre' if y in C.PRE else 'post') for k, y in ((p['key'], p['year']) for p in L.P)}
    papers = [dict(d, period=period[k], school=base['school']) for k, d in L.paper.items()]
    return main, plac, year, papers


def main(workers):
    t0 = time.time()
    setup()
    labs = sorted(G['labs'], key=lambda l: -len(G['labs'][l]))
    labs = [l for l in labs if len(G['labs'][l]) >= MIN_N]
    out = [[], [], [], []]
    with Pool(workers) as pool:
        for i, res in enumerate(pool.imap_unordered(lab_job, labs, chunksize=1)):
            for o, r in zip(out, res):
                o.extend(r)
            if i % 100 == 0:
                C.log(labs_done=i, of=len(labs), seconds=round(time.time() - t0))
    order = ['lab', 'school', 'pi', 'name', 'dept', 'topic10']
    for rows, path in ((out[0], C.ROOT / 'lab_diversity.csv'), (out[1], C.ROOT / 'lab_diversity_placebo.csv'),
                       (out[2], C.ROOT / 'lab_diversity_year.csv'), (out[3], C.RES / 'paper_lab_measures.csv.gz')):
        df = pd.DataFrame(rows)
        if len(df):
            df = df[[c for c in order if c in df] + [c for c in df if c not in order]]
            sort = [c for c in ('school', 'lab', 'comparison', 'period', 'year') if c in df]
            df = df.sort_values(sort)
        df.to_csv(path, index=False)
        C.log(wrote=str(path.name), rows=len(df))
    C.log(lab_diversity_seconds=round(time.time() - t0), ai_source=G['ai_source'])


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('-j', type=int, default=32)
    main(ap.parse_args().j)
