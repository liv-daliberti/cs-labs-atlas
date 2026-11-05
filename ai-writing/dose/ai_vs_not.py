"""AI-written vs not AI-written papers on every metric, at every slider cutoff (owner 2026-11-05, "All papers AI-written" page): site-data/v2/ai_vs_not.json[.gz].

  ai_vs_not.py model --model M     all cells for one embedding model -> AI_SCORES/results/ai_vs_not/<M>.parquet (and labs_<M>.parquet for the headline model)
  ai_vs_not.py assemble            JSON + sentences from the model tables

Groups (full-text papers; dose x = ai_share_cal else ai_share, as the dose pages): AI-written = x >= t for t in TS (percent of passages flagged); not AI-written = x < min(t, 10%)
(the detector-noise band; the groups never overlap, so below t = 10 the band is the zero-to-t range). Abstract-only papers (no usable full text) form separate groups by their
abstract flag, independent of t. Every (group definition, scope, year) cell compares equal-size draws of m = min(n_AI, n_not, 100) papers; the gap is AI minus not, the mean over
draws; the interval is a cluster bootstrap over labs (first lab; BOOT resamples x BDRAW draws, lab multiplicities as sampling weights); a cell with fewer than MIN_N papers in
the smaller group is blank. Each metric is computed on the ORIGINAL abstract vectors and on the ALL-AI REWRITTEN ones (every abstract rewritten, so wording is constant), on the same
papers and the same draws. Placebo (headline model): 2016-2021 papers with the rate-matched cut (the dose cut that flags the same share of 2017-2021 papers as t does of 2023-2025).
"""
import argparse
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import ai_pages as A
import ai_pages_more as M
import dcommon as D

TS = [1, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
NOT_CAP = 0.10
MIN_N, CAP = 20, 100
REPS, BOOT, BDRAW = 40, 24, 3
LAB_MIN, LAB_M, LAB_REPS = 5, 30, 30
METRICS = ['vendi', 'dispersion', 'mpd', 'extent', 'novelty', 'entropy_bt', 'entropy_oa']
INVARIANT = {'entropy_bt', 'entropy_oa'}         # entropies use the fixed original topics, so the rewritten value is the same
SCOPES = ['all'] + D.SCHOOLS
YEARS = A.YEARS
RES = A.RES / 'ai_vs_not'
OUT = A.OUT
G = {}                                              # per-process globals (fork)


def entropy_bits(codes):
    c = np.unique(codes, return_counts=True)[1] / len(codes)
    return float(-(c * np.log2(c)).sum())


def metrics(Z, nov, bt, oa, rows):
    V = Z[rows]
    m = len(rows)
    c = V.mean(0)
    dist = np.linalg.norm(V - c, axis=1)
    Gm = V @ V.T
    lam = np.clip(np.linalg.eigvalsh(Gm / m), 1e-12, None)
    nv = nov[rows]
    return [float(np.exp(-(lam * np.log(lam)).sum())), float(dist.mean()), float(1.0 - (Gm.sum() - m) / (m * (m - 1))), float(dist.max()),
            float(np.nanmean(nv)) if np.isfinite(nv).any() else np.nan, entropy_bits(bt[rows]), entropy_bits(oa[rows])]


def draw_gap(ia, inn, w, m, rng):
    """One draw: (versions x metrics) array of AI minus not, equal-size m, papers sampled with weights w (lab multiplicities; None = equal)."""
    out = []
    picks = []
    for idx in (ia, inn):
        if w is None:
            picks.append(idx[rng.choice(len(idx), m, replace=False)])
        else:
            keys = rng.exponential(size=len(idx)) / np.maximum(w[idx], 1e-9)
            picks.append(idx[np.argsort(keys)[:m]])
    for v in ('o', 'r'):
        a = metrics(G['Z' + v], G['nov' + v], G['bt'], G['oa'], picks[0])
        n = metrics(G['Z' + v], G['nov' + v], G['bt'], G['oa'], picks[1])
        out.append(np.array(a) - np.array(n))
    return np.array(out)


def cell(args):
    key, ia, inn, seed = args
    rng = np.random.default_rng(seed)
    nA, nN = len(ia), len(inn)
    rec = dict(key=key, nA=nA, nN=nN, gap=None)
    if min(nA, nN) < MIN_N:
        return rec
    m = min(nA, nN, CAP)
    pts = np.array([draw_gap(ia, inn, None, m, rng) for _ in range(REPS)])
    boots = []
    for b in range(BOOT):
        w = G['W'][b][G['lab']].astype(float)
        wa, wn = (w[ia] > 0).sum(), (w[inn] > 0).sum()
        mb = min(m, wa, wn)
        if mb < 5:
            continue
        boots.append(np.nanmean([draw_gap(ia, inn, w, mb, rng) for _ in range(BDRAW)], axis=0))
    rec['gap'] = np.nanmean(pts, axis=0)
    if len(boots) >= 8:
        b = np.array(boots)
        rec['lo'], rec['hi'] = np.nanpercentile(b, 2.5, axis=0), np.nanpercentile(b, 97.5, axis=0)
    return rec


def lab_cell(args):
    """Within-lab counterpart at cutoff t over 2023-2025: per lab with >= LAB_MIN papers in each group, the equal-size gap (m <= LAB_M, LAB_REPS draws); returns lab rows."""
    t, lab, ia, inn, seed = args
    rng = np.random.default_rng(seed)
    m = min(len(ia), len(inn), LAB_M)
    g = np.nanmean([draw_gap(ia, inn, None, m, rng) for _ in range(LAB_REPS)], axis=0)
    return dict(t=t, lab=lab, school=G['lab_school'][lab], nA=len(ia), nN=len(inn), gap=g)


def load(model):
    fr = pd.read_parquet(A.RES / 'frame.parquet')
    fr = fr[fr['year'].between(2016, A.LAST) & fr['has_vec']].reset_index(drop=True)
    ido, Zo = A.unit_vectors(model)
    idr, Zr = M.rewrite_unit_vectors(model)
    common = set(ido) & set(idr) & set(fr['paper_id'])
    fr = fr[fr['paper_id'].isin(common)].reset_index(drop=True)
    po, pr = {p: i for i, p in enumerate(ido)}, {p: i for i, p in enumerate(idr)}
    Zo = Zo[[po[p] for p in fr['paper_id']]].astype(np.float32)
    Zr = Zr[[pr[p] for p in fr['paper_id']]].astype(np.float32)
    years = fr['year'].to_numpy()
    import novelty as N
    nov = {}
    for v, Z in (('o', Zo), ('r', Zr)):
        r = N.novelty_group(Z, years, np.arange(len(fr)), ks=(3,), nn=5, cap=2000, seed=A.SEED, dev=None)
        x = np.full(len(fr), np.nan)
        x[r['paper']] = np.where(r['n_ref'] >= 100, r['nov_nn_cap'], np.nan)
        nov[v] = x
    G.update(Zo=Zo, Zr=Zr, novo=nov['o'], novr=nov['r'], bt=pd.factorize(fr['topic'].fillna(-1))[0], oa=pd.factorize(fr['oa_topic'].fillna('none'))[0],
             lab=pd.factorize(fr['lab0'])[0])
    nl = G['lab'].max() + 1
    rng = np.random.default_rng(A.SEED)
    G['W'] = [rng.multinomial(nl, np.full(nl, 1.0 / nl)) for _ in range(BOOT)]
    return fr


def run_model(model, procs):
    A.ensure_dirs()
    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fr = load(model)
    D.log(stage='ai_vs_not', model=model, papers=len(fr), seconds=round(time.time() - t0))
    x = fr['x'].to_numpy()
    scored = np.isfinite(x)
    flag = fr['flag_abstract'].to_numpy()
    yr = fr['year'].to_numpy()
    member = {'all': np.ones(len(fr), bool)}
    sc = fr['schools'].str.split(',')
    for s in D.SCHOOLS:
        member[s] = sc.map(lambda z, s=s: s in z).to_numpy()
    post = scored & np.isin(yr, A.POST)
    pre = scored & np.isin(yr, A.PLACEBO)
    cuts = {}
    for t in TS:
        share = float((x[post] >= t / 100 - 1e-12).mean())
        q = float(np.quantile(x[pre], 1 - share)) if pre.any() else 0.0
        cuts[t] = q if q > 0 else 1e-9
    jobs, seed = [], 0
    for sname, mem in member.items():
        for y in YEARS:
            base = mem & (yr == y)
            for t in TS:
                a = np.flatnonzero(base & scored & (x >= t / 100 - 1e-12))
                n = np.flatnonzero(base & scored & (x < min(t / 100, NOT_CAP)))
                seed += 1
                jobs.append((('cut', t, sname, y), a, n, seed))
                if model == A.HEADLINE and y <= 2021:
                    tp = cuts[t]
                    a = np.flatnonzero(base & scored & (x >= tp))
                    n = np.flatnonzero(base & scored & (x < min(tp, NOT_CAP)))
                    seed += 1
                    jobs.append((('placebo', t, sname, y), a, n, seed))
            a = np.flatnonzero(base & ~scored & (flag == 1))
            n = np.flatnonzero(base & ~scored & (flag == 0))
            seed += 1
            jobs.append((('abstract', 0, sname, y), a, n, seed))
    with ProcessPoolExecutor(procs) as ex:
        recs = list(ex.map(cell, jobs, chunksize=8))
    rows = []
    for r in recs:
        var, t, sname, y = r['key']
        for vi, ver in enumerate(('orig', 'rewritten')):
            for mi, met in enumerate(METRICS):
                rows.append(dict(model=model, variant=var, t=t, scope=sname, year=y, metric=met, version=ver, nA=r['nA'], nN=r['nN'],
                                 gap=None if r['gap'] is None else float(r['gap'][vi, mi]),
                                 lo=None if 'lo' not in r else float(r['lo'][vi, mi]), hi=None if 'hi' not in r else float(r['hi'][vi, mi])))
    df = pd.DataFrame(rows)
    df.attrs = {}
    df.to_parquet(RES / f'{model}.parquet', index=False)
    pd.DataFrame([dict(t=t, cut=c) for t, c in cuts.items()]).to_parquet(RES / f'cuts_{model}.parquet', index=False)
    D.log(stage='ai_vs_not', model=model, cells=len(recs), nonblank=sum(r['gap'] is not None for r in recs), seconds=round(time.time() - t0))
    if model == A.HEADLINE:
        run_labs(fr, x, scored, yr, procs)


def run_labs(fr, x, scored, yr, procs):
    lab = G['lab']
    labs = fr.groupby(lab)['lab0'].first()
    G['lab_school'] = dict(zip(range(len(labs)), fr.groupby(lab)['school'].first()))
    names = dict(zip(range(len(labs)), labs))
    jobs, seed = [], 10 ** 6
    post = scored & np.isin(yr, A.POST)
    for t in TS:
        a_all = post & (x >= t / 100 - 1e-12)
        n_all = post & (x < min(t / 100, NOT_CAP))
        for li in np.unique(lab[a_all]):
            a = np.flatnonzero(a_all & (lab == li))
            n = np.flatnonzero(n_all & (lab == li))
            if len(a) >= LAB_MIN and len(n) >= LAB_MIN:
                seed += 1
                jobs.append((t, int(li), a, n, seed))
    with ProcessPoolExecutor(procs) as ex:
        out = list(ex.map(lab_cell, jobs, chunksize=4))
    rows = []
    for r in out:
        for vi, ver in enumerate(('orig', 'rewritten')):
            for mi, met in enumerate(METRICS):
                rows.append(dict(t=r['t'], lab_id=names[r['lab']], school=r['school'], nA=r['nA'], nN=r['nN'], metric=met, version=ver, gap=float(r['gap'][vi, mi])))
    pd.DataFrame(rows).to_parquet(RES / f'labs_{A.HEADLINE}.parquet', index=False)
    D.log(stage='ai_vs_not', lab_rows=len(rows), lab_jobs=len(jobs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['model', 'assemble'])
    ap.add_argument('--model')
    ap.add_argument('--procs', type=int, default=14)
    a = ap.parse_args()
    if a.cmd == 'model':
        run_model(a.model, a.procs)
    else:
        import ai_vs_not_site as S
        S.assemble()


if __name__ == '__main__':
    main()
