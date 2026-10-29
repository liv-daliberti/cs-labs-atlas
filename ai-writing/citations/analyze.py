"""Question 1: do papers with more AI-written text cite a narrower set of works?

Citing papers: paragraph-scored lab papers (2016-2026) whose reference list has >= MIN_REFS works in the source
(OpenAlex by default; --source s2 repeats everything on Semantic Scholar reference lists as a coverage check).
Periods: base = 2016-2022, then 2023, 2024, 2025, 2026. AI groups: none (ai_share = 0), some (0 < ai_share < 0.25),
flagged (ai_share >= 0.25). Every set-level measure is computed on equal-size random draws of citing papers
(DRAWS = 1,000, the battery's SEED); the draw size N is one number for every cell of a family, so neither group nor
year size drives the measures. Intervals are the 2.5-97.5 percentiles over draws (subsampling spread; group sizes
differ, so a group drawn nearly whole has a narrower band).

Pooled measures of one draw (the citations of the N papers pooled; a work cited by k papers counts k times):
  H_work      entropy (nats) of the cited-work counts           } on a fixed-size random subsample of T = 15 N citations
  gini        Gini of the cited-work counts (works in the draw)  } (rarefied, so reference-list length cannot move them)
  distinct    distinct works per citation                        }
  H_venue     entropy over cited works' venues (OpenAlex source; arXiv is one venue)   } resolved citations, same
  H_field / H_subfield  entropy over the cited works' OpenAlex primary_topic field / subfield } T-subsample
  top1        share of citations to works in the top 1% by cited_by_count within their own publication year
  top1g       the same with one global top-1% cut (moves with reference age)
  logcbc      mean log(1 + cited_by_count) of the references
  logcbc_adj  the same minus the mean of works published the same year (age-adjusted popularity)
  age         mean citing year - cited year;  recent: share of references <= 2 years old
  preprint    share of classified references that are preprint-only (build.py rule; _strict and _s2 variants)
  nrefs       mean reference-list length (the control)
  canon       mean log(1 + number of OTHER sample papers of the same citing year citing the work)

Families:
  year_group   period x AI group                      (panel A)
  dose         AI-dose bins, 2023-2026, year mix matched to the period's (panel B); 2016-2022 false-positive dose bins
  school, field  flagged vs not, 2024-2026, per school / per citing field (CS vs other), year-matched
  within_lab   each drawn flagged paper paired with a not-flagged paper of the same lab and year (panel D)
Per-paper regressions (lab x year fixed effects, lab-clustered bootstrap) are in within.py.
-> results/<source>_<family>.csv (one row per cell x measure: mean, lo, hi, n) and results/<source>_diffs.csv
usage: analyze.py [--source oa|s2]
"""
import argparse, json, os
from pathlib import Path
import numpy as np, pandas as pd
from multiprocessing import Pool

HERE = Path(__file__).resolve().parent
DATA, RES = HERE / 'data', HERE / 'results'
SEED, DRAWS, MIN_REFS = 20261022, int(os.environ.get("CIT_DRAWS", 1000)), 5
PERIODS = {'base': range(2016, 2023), '2023': [2023], '2024': [2024], '2025': [2025], '2026': [2026]}
GROUPS = ('none', 'some', 'flagged')
DOSE_BINS = [(0, 0, '0'), (1e-9, 0.05, '0–5%'), (0.05, 0.10, '5–10%'), (0.10, 0.25, '10–25%'), (0.25, 0.50, '25–50%'), (0.50, 1.0, '≥50%')]
POOLED = ['H_work', 'gini', 'distinct', 'H_venue', 'H_field', 'H_subfield', 'top1', 'top1g', 'logcbc', 'logcbc_adj', 'age', 'recent',
          'preprint', 'preprint_strict', 'preprint_s2', 'nrefs', 'canon', 'H_work_full', 'distinct_full']


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def dose_mask(a, lab):
    """0 | (0, 5%] | (5, 10%] | (10, 25%) | [25, 50%) | >= 50%: the flag cut (0.25) is a bin edge."""
    return {'0': a == 0, '0–5%': (a > 0) & (a <= 0.05), '5–10%': (a > 0.05) & (a <= 0.10), '10–25%': (a > 0.10) & (a < 0.25),
            '25–50%': (a >= 0.25) & (a < 0.50), '≥50%': a >= 0.50}[lab]


def group_of(a):
    return np.where(a <= 0, 'none', np.where(a < 0.25, 'some', 'flagged'))


def entropy(codes):
    if len(codes) == 0:
        return np.nan
    _, n = np.unique(codes, return_counts=True)
    p = n / n.sum()
    return float(-(p * np.log(p)).sum())


def gini(codes):
    _, n = np.unique(codes, return_counts=True)
    x = np.sort(n).astype(float); k = len(x)
    if k < 2:
        return np.nan
    return float(((2 * np.arange(1, k + 1) - k - 1) * x).sum() / (k * x.sum()))


class Data:
    def __init__(self, source):
        C = pd.read_parquet(DATA / 'citing.parquet')
        E = pd.read_parquet(DATA / f'edges_{source}.parquet')
        W = pd.read_parquet(DATA / f'works_{source}.parquet')
        if source == 's2':
            for c in ('pubclass_strict', 'pubclass_s2', 'subfield'):
                W[c] = W['pubclass'] if c.startswith('pub') else None
        nres = E.groupby('ci').size().reindex(range(len(C)), fill_value=0).values
        keep = nres >= MIN_REFS
        self.C = C[keep].reset_index(drop=True)
        old = np.flatnonzero(keep); remap = -np.ones(len(C), int); remap[old] = np.arange(len(old))
        E = E[keep[E.ci.values]].copy(); E['ci'] = remap[E.ci.values]
        E = E.sort_values(['ci', 'wid'])
        # dense work codes; attributes for resolved works, NaN / -1 otherwise
        u, code = np.unique(E.wid.values, return_inverse=True)
        self.ref = code.astype(np.int64)
        self.ptr = np.concatenate([[0], np.cumsum(np.bincount(E.ci.values, minlength=len(self.C)))])
        W = W.drop_duplicates('wid').set_index('wid').reindex(u)
        self.resolved = W['year'].notna().values
        yr = W['year'].values.astype(float)
        cbc = W['cbc'].values.astype(float)
        lc = np.log1p(cbc)
        df = pd.DataFrame(dict(y=yr, lc=lc, cbc=cbc))
        ym = df.groupby('y').lc.transform('mean').values
        q99 = df.groupby('y').cbc.transform(lambda s: s.quantile(0.99) if len(s) >= 100 else np.inf).values
        self.wyear, self.wlc, self.wlc_adj = yr, lc, lc - ym
        self.wtop1 = np.where(np.isnan(cbc), np.nan, (cbc >= q99).astype(float))
        g = np.nanquantile(cbc, 0.99)
        self.wtop1g = np.where(np.isnan(cbc), np.nan, (cbc >= g).astype(float))
        self.venue = pd.factorize(W['venue'].fillna('').values)[0]; self.venue[W['venue'].isna().values] = -1
        self.field = pd.factorize(W['field'].fillna('').values)[0]; self.field[W['field'].isna().values] = -1
        sf = W['subfield'] if 'subfield' in W else pd.Series([None] * len(W))
        self.subfield = pd.factorize(sf.fillna('').values)[0]; self.subfield[sf.isna().values] = -1
        self.pc = {}
        for c in ('pubclass', 'pubclass_strict', 'pubclass_s2'):
            v = W[c].values
            self.pc[c] = np.where(v == 'preprint', 1.0, np.where((v == 'published') | (v == 'other'), 0.0, np.nan))
        cy = self.C.year.values
        self.cyear = np.repeat(cy, np.diff(self.ptr))
        # canon: other sample papers of the same citing year citing the work
        key = self.cyear.astype(np.int64) * (len(u) + 1) + self.ref
        _, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        self.canon = np.log1p(cnt[inv] - 1)
        self.n = len(self.C)
        self.group = group_of(self.C.ai_share.values)
        log(source=source, citing=self.n, citations=len(self.ref), works=len(u), resolved=float(self.resolved.mean()))

    def refs(self, idx):
        return np.concatenate([np.arange(self.ptr[i], self.ptr[i + 1]) for i in idx])

    def measures(self, idx, T, rng):
        e = self.refs(idx)
        out = dict(nrefs=float(np.mean(np.diff(self.ptr)[idx])), H_work_full=entropy(self.ref[e]),
                   distinct_full=len(np.unique(self.ref[e])) / len(e))
        s = rng.choice(e, T, replace=False) if len(e) >= T else e
        w = self.ref[s]
        out['H_work'] = entropy(w); out['gini'] = gini(w); out['distinct'] = len(np.unique(w)) / len(w)
        r = s[self.resolved[w]]; wr = self.ref[r]
        v = self.venue[wr]; out['H_venue'] = entropy(v[v >= 0])
        f = self.field[wr]; out['H_field'] = entropy(f[f >= 0])
        f = self.subfield[wr]; out['H_subfield'] = entropy(f[f >= 0]) if (f >= 0).any() else np.nan
        er = e[self.resolved[self.ref[e]]]; we = self.ref[er]
        out['top1'] = np.nanmean(self.wtop1[we]); out['top1g'] = np.nanmean(self.wtop1g[we])
        out['logcbc'] = np.nanmean(self.wlc[we]); out['logcbc_adj'] = np.nanmean(self.wlc_adj[we])
        age = self.cyear[er] - self.wyear[we]
        out['age'] = float(np.nanmean(age)); out['recent'] = float(np.nanmean(age <= 2))
        out['preprint'] = np.nanmean(self.pc['pubclass'][we]); out['preprint_strict'] = np.nanmean(self.pc['pubclass_strict'][we])
        out['preprint_s2'] = np.nanmean(self.pc['pubclass_s2'][we])
        out['canon'] = float(self.canon[e].mean())
        return out


D = None


def _init(source):
    global D
    D = Data(source)


def run_cell(args):
    """args: (family, cell label, candidate idx, weights or None, N, seed, paired idx-map or None)"""
    fam, cell, cand, wts, N, seed, pair = args
    rng = np.random.default_rng(seed)
    T = 15 * N
    rows = []
    for d in range(DRAWS):
        if pair is None:
            idx = rng.choice(cand, N, replace=False, p=wts)
            rows.append(D.measures(idx, T, rng))
        else:  # within-lab: pair[i] is the array of same-lab, same-year not-flagged partners of cand[i]
            pick = rng.choice(len(cand), N, replace=False)
            a = cand[pick]; b = np.array([rng.choice(pair[i]) for i in pick])
            ma, mb = D.measures(a, T, rng), D.measures(b, T, rng)
            rows.append({**{f'{k}': ma[k] for k in ma}, **{f'{k}__ctrl': mb[k] for k in mb}})
    return fam, cell, N, pd.DataFrame(rows)


def year_weights(idx, target):
    """Sampling weights over idx so the expected year mix equals `target` ({year: share})."""
    y = D.C.year.values[idx]
    w = np.zeros(len(idx))
    for yy, sh in target.items():
        m = y == yy
        if m.any():
            w[m] = sh / m.sum()
    return w / w.sum()


def jobs(source):
    C, g, a, y = D.C, D.group, D.C.ai_share.values, D.C.year.values
    per = np.array(['base' if yy <= 2022 else str(yy) for yy in y])
    J = []
    # panel A: period x group, one N for all cells (base 'flagged' are false positives and too few; reported if >= N)
    cells = {(p, gg): np.flatnonzero((per == p) & (g == gg)) for p in PERIODS for gg in GROUPS}
    sizes = {k: len(v) for k, v in cells.items()}
    N = min(v for (p, gg), v in sizes.items() if not (p == 'base' and gg == 'flagged'))
    N = int(max(20, min(N, 400)))
    log(family='year_group', N=N, sizes={f'{p}/{gg}': v for (p, gg), v in sizes.items()})
    for i, ((p, gg), idx) in enumerate(cells.items()):
        if len(idx) >= N:
            J.append(('year_group', f'{p}|{gg}', idx, None, N, SEED + i, None))
    # panel B: dose bins, 2023-2026 (year mix matched) and 2016-2022 (false-positive dose)
    for span, ys in (('post', range(2023, 2027)), ('base', range(2016, 2023))):
        inspan = np.isin(y, list(ys))
        target = pd.Series(y[inspan]).value_counts(normalize=True).to_dict()
        bins = {lab: np.flatnonzero(inspan & dose_mask(a, lab)) for _, _, lab in DOSE_BINS}
        nb = {k: len(v) for k, v in bins.items()}
        ok = {k: v for k, v in bins.items() if len(v) >= 60}
        Nb = int(max(20, min(min(len(v) for v in ok.values()) // 2, 300)))  # weighted draws need headroom
        log(family=f'dose_{span}', N=Nb, sizes=nb)
        for j, (lab, idx) in enumerate(ok.items()):
            J.append((f'dose_{span}', lab, idx, year_weights(idx, target), Nb, SEED + 100 + j + (50 if span == 'base' else 0), None))
    # school and citing-field strata: flagged vs not flagged, 2024-2026, year mix matched within stratum
    post = np.isin(y, [2024, 2025, 2026])
    strata = [('school', s, C.school.values == s) for s in ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')]
    cs = C.field.fillna('').values == 'Computer Science'
    strata += [('field', 'Computer Science', cs), ('field', 'other fields', ~cs)]
    for k, (fam, s, m) in enumerate(strata):
        f_idx, n_idx = np.flatnonzero(post & m & (g == 'flagged')), np.flatnonzero(post & m & (g != 'flagged'))
        if len(f_idx) < 40:
            continue
        target = pd.Series(y[f_idx]).value_counts(normalize=True).to_dict()
        Ns = int(min(len(f_idx), 300) * 0.8)
        J.append((fam, f'{s}|flagged', f_idx, None, Ns, SEED + 200 + 2 * k, None))
        J.append((fam, f'{s}|not', n_idx, year_weights(n_idx, target), Ns, SEED + 201 + 2 * k, None))
    # within lab: flagged 2023-2026 papers with a not-flagged partner in the same lab and year
    labs = [json.loads(x)[0] for x in C.labs.values]  # the first lab (as listed) pairs the paper
    from collections import defaultdict
    pool = defaultdict(list)
    for i, (l, yy, gg) in enumerate(zip(labs, y, g)):
        if yy >= 2023 and gg != 'flagged':
            pool[(l, yy)].append(i)
    cand, pair = [], []
    for i, (l, yy, gg) in enumerate(zip(labs, y, g)):
        if yy >= 2023 and gg == 'flagged' and pool.get((l, yy)):
            cand.append(i); pair.append(np.array(pool[(l, yy)]))
    cand = np.array(cand)
    Nw = int(min(300, len(cand) * 0.6))
    log(family='within_lab', eligible_flagged=len(cand), N=Nw, labs=len({labs[i] for i in cand}))
    J.append(('within_lab', 'flagged vs same lab-year', cand, None, Nw, SEED + 300, pair))
    return J


def summarize(results):
    rows, diffs = [], []
    store = {}
    for fam, cell, N, df in results:
        store[(fam, cell)] = df
        for m in df.columns:
            v = df[m].values.astype(float)
            rows.append(dict(family=fam, cell=cell, N=N, measure=m, mean=np.nanmean(v), lo=np.nanpercentile(v, 2.5), hi=np.nanpercentile(v, 97.5)))
        if fam == 'within_lab':
            for m in POOLED:
                if m in df and f'{m}__ctrl' in df:
                    d = df[m].values - df[f'{m}__ctrl'].values
                    diffs.append(dict(family=fam, contrast='flagged - same lab-year not flagged', measure=m, N=N, mean=np.nanmean(d),
                                      lo=np.nanpercentile(d, 2.5), hi=np.nanpercentile(d, 97.5), p_le0=float(np.mean(d <= 0))))
    # paired-by-draw-index differences (draws are independent, so this is the difference of two independent spreads)
    def diff(fam, a, b, label):
        if (fam, a) in store and (fam, b) in store:
            A, B = store[(fam, a)], store[(fam, b)]
            for m in POOLED:
                if m in A and m in B:
                    d = A[m].values - B[m].values
                    diffs.append(dict(family=fam, contrast=label, measure=m, N=None, mean=np.nanmean(d), lo=np.nanpercentile(d, 2.5),
                                      hi=np.nanpercentile(d, 97.5), p_le0=float(np.mean(d <= 0))))
    for p in PERIODS:
        diff('year_group', f'{p}|flagged', f'{p}|none', f'{p}: flagged - none')
        diff('year_group', f'{p}|some', f'{p}|none', f'{p}: some - none')
    for p in ('2023', '2024', '2025', '2026'):
        diff('year_group', f'{p}|none', 'base|none', f'none: {p} - base')
    diff('dose_post', '≥50%', '0', 'post: dose >=50% - 0')
    diff('dose_post', '25–50%', '0', 'post: dose 25-50% - 0')
    diff('dose_base', '0–5%', '0', 'base: dose 0-5% - 0 (false-positive dose)')
    diff('dose_base', '5–10%', '0', 'base: dose 5-10% - 0 (false-positive dose)')
    for s in ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford'):
        diff('school', f'{s}|flagged', f'{s}|not', f'{s}: flagged - not')
    for s in ('Computer Science', 'other fields'):
        diff('field', f'{s}|flagged', f'{s}|not', f'{s}: flagged - not')
    return pd.DataFrame(rows), pd.DataFrame(diffs)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--source', default='oa'); ap.add_argument('--procs', type=int, default=24)
    a = ap.parse_args()
    RES.mkdir(exist_ok=True)
    _init(a.source)
    J = jobs(a.source)
    with Pool(a.procs, initializer=_init, initargs=(a.source,)) as pool:
        out = pool.map(run_cell, J, chunksize=1)
    S, Dd = summarize(out)
    S.to_csv(RES / f'{a.source}_cells.csv', index=False); Dd.to_csv(RES / f'{a.source}_diffs.csv', index=False)
    cov = D.C.assign(period=np.where(D.C.year <= 2022, 'base', D.C.year.astype(str)), group=D.group).groupby(['period', 'group']).size()
    cov.rename('papers').to_csv(RES / f'{a.source}_sample_sizes.csv')
    log(done=a.source, cells=len(S), diffs=len(Dd))


if __name__ == '__main__':
    main()
