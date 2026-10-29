"""Per-paper reference measures and within-lab regressions (composition control for question 1).

Per-paper measures (OpenAlex references, papers with >= 5 references in OpenAlex):
  nrefs, log_nrefs        reference-list length
  logcbc_adj              mean age-adjusted log(1 + cited_by_count) of the resolved references
  top1                    share of resolved references in the top 1% by cited_by_count of their publication year
  canon                   mean log(1 + number of other sample papers of the same year citing the reference)
  preprint                share of classified references that are preprint-only (build.py rule)
  age, recent             mean reference age; share <= 2 years old
  venue_div               distinct venues / resolved references with a venue (per-paper breadth)
  field_div               distinct OpenAlex subfields / resolved references with a subfield
  year_sd, lc_sd          spread of the paper's resolved references: SD of their publication years and of their age-adjusted
                          log(1 + cited_by_count) (question 2: is the variance of what a paper cites going down)
Model: y = b * x + g * log_nrefs + lab-by-year fixed effects. A paper of k labs enters once per lab with weight 1/k.
Intervals: 1,000 bootstrap resamples of labs (clusters). Specifications:
  post_flag     2023-2026, x = flagged (ai_share >= 0.25)
  post_dose     2023-2026, x = ai_share per 10 percentage points
  base_dose     2016-2022, x = ai_share per 10 points (detector false positives: a placebo; should be ~0)
  post_flag_nofe  2023-2026, x = flagged, year fixed effects only (the raw contrast, for comparison)
  post_flag_sub   2023-2026, x = flagged, citing-subfield x year fixed effects (field composition, e.g. ML/LLM papers cite
                  newer work anyway; subfield = the citing paper's OpenAlex primary_topic subfield)
  post_flag_labsub 2023-2026, x = flagged, lab x year x citing-subfield fixed effects (both at once)
  y<YYYY>_flag    one citing year at a time (2023, 2024, 2025, 2026), x = flagged, lab x year fixed effects
-> data/paper_measures.parquet, results/within_lab.csv (--source s2: the same on S2 reference lists, *_s2 names;
   S2 has no subfields, so field_div is empty there and the citing subfield still comes from OpenAlex)
"""
import json
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
DATA, RES = HERE / 'data', HERE / 'results'
SEED, BOOT = 20261022, 1000
MEASURES = ['log_nrefs', 'logcbc_adj', 'top1', 'canon', 'preprint', 'age', 'recent', 'venue_div', 'field_div', 'year_sd', 'lc_sd']


def paper_measures(source='oa'):
    import analyze as A
    D = A.Data(source)
    rows = []
    for i in range(D.n):
        e = np.arange(D.ptr[i], D.ptr[i + 1]); w = D.ref[e]
        r = D.resolved[w]; wr = w[r]
        age = D.C.year.values[i] - D.wyear[wr]
        v = D.venue[wr]; v = v[v >= 0]; f = D.subfield[wr]; f = f[f >= 0]
        pc = D.pc['pubclass'][wr]
        rows.append(dict(i=i, nrefs=len(e), log_nrefs=np.log(len(e)), n_res=int(r.sum()),
                         logcbc_adj=np.nanmean(D.wlc_adj[wr]) if len(wr) else np.nan, top1=np.nanmean(D.wtop1[wr]) if len(wr) else np.nan,
                         canon=float(D.canon[e].mean()), preprint=np.nanmean(pc) if np.isfinite(pc).any() else np.nan,
                         age=np.nanmean(age) if len(wr) else np.nan, recent=np.nanmean(age <= 2) if len(wr) else np.nan,
                         venue_div=len(np.unique(v)) / len(v) if len(v) >= 3 else np.nan,
                         field_div=len(np.unique(f)) / len(f) if len(f) >= 3 else np.nan,
                         year_sd=float(np.nanstd(D.wyear[wr], ddof=1)) if len(wr) >= 3 else np.nan,
                         lc_sd=float(np.nanstd(D.wlc_adj[wr], ddof=1)) if len(wr) >= 3 else np.nan))
    P = pd.concat([D.C.reset_index(drop=True), pd.DataFrame(rows).drop(columns='i')], axis=1)
    return P


def long_by_lab(P):
    """One row per (paper, lab), weight 1/number of labs."""
    L = P.assign(lab=P.labs.map(json.loads)).explode('lab')
    L['w'] = 1.0 / L.groupby('key').lab.transform('size')
    return L.reset_index(drop=True)


def fe_boot(L, y, xcols, fe, boot=BOOT, seed=SEED):
    """WLS of y on xcols after weighted demeaning within `fe` cells; lab-cluster bootstrap. Returns (beta, lo, hi, n_papers, n_labs)
    for the first x column."""
    d = L.dropna(subset=[y] + xcols).copy()
    d = d[d.groupby(fe)[y].transform('size') >= 2]
    if len(d) < 30:
        return [np.nan] * 5
    cols = [y] + xcols
    for c in cols:
        m = (d[c] * d.w).groupby([d[f] for f in fe]).transform('sum') / d.w.groupby([d[f] for f in fe]).transform('sum')
        d[c] = d[c] - m
    labs, li = np.unique(d.lab.values, return_inverse=True)
    X, Y, Wt = d[xcols].values, d[y].values, d.w.values
    k = len(xcols)
    XX = np.zeros((len(labs), k, k)); XY = np.zeros((len(labs), k))
    np.add.at(XX, li, (X[:, :, None] * X[:, None, :]) * Wt[:, None, None]); np.add.at(XY, li, X * (Wt * Y)[:, None])

    def solve(c):
        A = np.tensordot(c, XX, 1); b = c @ XY
        try:
            return np.linalg.solve(A, b)[0]
        except np.linalg.LinAlgError:
            return np.nan
    b0 = solve(np.ones(len(labs)))
    rng = np.random.default_rng(seed)
    bs = np.array([solve(np.bincount(rng.integers(0, len(labs), len(labs)), minlength=len(labs)).astype(float)) for _ in range(boot)])
    return b0, np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5), d.key.nunique(), len(labs)


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--source', default='oa'); src = ap.parse_args().source
    sfx = '' if src == 'oa' else f'_{src}'
    P = paper_measures(src)
    P.to_parquet(DATA / f'paper_measures{sfx}.parquet')
    L = long_by_lab(P)
    L['flag'] = (L.ai_share >= 0.25).astype(float); L['dose10'] = L.ai_share * 10
    L['labyear'] = L.lab + '|' + L.year.astype(str)
    L['subyear'] = L.subfield.fillna('?') + '|' + L.year.astype(str)
    L['labsub'] = L.labyear + '|' + L.subfield.fillna('?')
    post, base = L[L.year >= 2023], L[L.year <= 2022]
    out = []
    for m in MEASURES:
        xs_ctrl = [] if m == 'log_nrefs' else ['log_nrefs']
        for spec, d, x, fe in (('post_flag', post, 'flag', ['labyear']), ('post_dose', post, 'dose10', ['labyear']),
                               ('base_dose', base, 'dose10', ['labyear']), ('post_flag_nofe', post, 'flag', ['year']),
                               ('post_flag_sub', post, 'flag', ['subyear']), ('post_flag_labsub', post, 'flag', ['labsub']),
                               *[(f'y{yy}_flag', L[L.year == yy], 'flag', ['labyear']) for yy in (2023, 2024, 2025, 2026)]):
            b, lo, hi, n, nl = fe_boot(d, m, [x] + xs_ctrl, fe)
            sd = P.loc[P.year >= 2023, m].std() if spec.startswith(('post', 'y')) else P.loc[P.year <= 2022, m].std()
            out.append(dict(measure=m, spec=spec, beta=b, lo=lo, hi=hi, sd_y=sd, papers=n, labs=nl))
            print(json.dumps(out[-1], default=float), flush=True)
    pd.DataFrame(out).to_csv(RES / f'within_lab{sfx}.csv', index=False)


if __name__ == '__main__':
    main()
