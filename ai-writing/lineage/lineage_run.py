"""Step 2: lineage measures and estimates for one embedding model and text kind.

usage: lineage_run.py --model M --kind abstract|fulltext [--no-allai]
reads  RUN/{student_papers,pi_papers,students}.parquet (lineage_build.py), the model's vectors, the detector table (LINEAGE_AI)
writes RUN/effects_<model>_<kind>.parquet, RUN/yearly_<model>_<kind>.parquet
Measures (per student paper, cosine on centred unit vectors; PI pool = strict lab papers of the PI in the 3 previous years,
papers the student co-authored with the PI excluded, pool size-matched to M_POOL papers, mean over REPS random pools):
  sa  similarity to the PI: mean of the 3 nearest pool papers      cd  distance from the pool's centroid (1 - cos)
  ss  within-lab student-student similarity (lab-year, 4 papers of 4 different students, mean pairwise cosine)
With the abstract kind the same measures are computed on the all-AI rewritten abstracts (`<model>__allai`) for the same papers.
"""
import argparse
import time

import numpy as np
import pandas as pd

import lineage_common as L
import lineage_fit as F

SETS = {'verified': ['verified'], 'candidate': ['candidate'], 'all': ['verified', 'candidate']}
DESIGNS = [('post', None)] + [(f'placebo{b}', b) for b in (2019, 2020, 2021)]


_G = {}


def _chunk(k):
    sp, Zs, idx = (_G[x] for x in ('sp', 'Zs', 'idx'))
    labs = _G['chunks'][k]
    return _pair_measures(sp[sp['lab'].isin(labs)], _G['pre'], Zs, idx, rng_seed=k)


def pair_measures(sp, pp, stu, Zs, idx, procs=8):
    """Parallel over labs (fork shares the vectors); every chunk has its own fixed seed."""
    import multiprocessing as mp
    labs = np.array(sorted(sp['lab'].unique()))
    n = max(1, min(4 * procs, len(labs)))
    _G.update(sp=sp, pre=_prep(sp, pp, stu, idx), Zs=Zs, idx=idx, chunks=[set(c) for c in np.array_split(labs, n)])
    with mp.get_context('fork').Pool(procs) as pool:
        parts = pool.map(_chunk, range(n))
    return pd.concat(parts, ignore_index=True)


def _prep(sp, pp, stu, idx):
    namesof = stu.drop_duplicates('student').set_index('student')['name'].map(L.norm_name).to_dict()
    pool = {}
    for lab, g in pp.groupby('lab'):
        ok = g[g['paper_id'].isin(idx)]
        pool[lab] = (ok['paper_id'].to_numpy(), ok['year'].to_numpy(), ok['byline'].to_numpy())
    return namesof, pool, sp.groupby('student')['paper_id'].agg(set).to_dict()


def _pair_measures(sp, pre, Zs, idx, rng_seed=0):
    """One row per (student, paper, lab) of sp with a pool: sa_/cd_ per variant name in Zs (dict name -> unit matrix)."""
    namesof, pool, own = pre
    rows = []
    rng = np.random.default_rng(rng_seed)
    for r in sp.itertuples(index=False):
        if r.paper_id not in idx or r.lab not in pool or not (L.Y0 + 1 <= r.year <= L.Y1):
            continue
        pid, py, pb = pool[r.lab]
        m = (py >= r.year - L.HIST) & (py <= r.year - 1)
        cand = [i for i in np.flatnonzero(m) if pid[i] not in own[r.student] and namesof.get(r.student, '#') not in pb[i].split('|')]
        if len(cand) < L.M_POOL:
            continue
        cidx = np.array([idx[pid[i]] for i in cand])
        draws = np.array([rng.choice(len(cidx), L.M_POOL, replace=False) for _ in range(L.REPS)])
        row = dict(school=r.school, lab=r.lab, student=r.student, paper_id=r.paper_id, year=r.year, status=r.status, n_pool=len(cand))
        si = idx[r.paper_id]
        for name, Z in Zs.items():
            V = Z[cidx[draws]]                                    # REPS x M x d
            sims = V @ Z[si]
            row['sa_' + name] = float(np.sort(sims, axis=1)[:, -L.K_NN:].mean())
            c = V.mean(1)
            row['cd_' + name] = float(1 - np.mean((c @ Z[si]) / np.clip(np.linalg.norm(c, axis=1), 1e-9, None)))
        rows.append(row)
    return pd.DataFrame(rows)


def lab_year_ss(sp, Zs, idx, seed=1, m=4, reps=30):
    """Within-lab student-student similarity per lab-year, per status set."""
    rng = np.random.default_rng(seed)
    out = []
    d = sp[sp['paper_id'].isin(idx) & sp['year'].between(L.Y0 + 1, L.Y1)]
    for (lab, yr), g in d.groupby(['lab', 'year']):
        by = {s: sorted(set(x)) for s, x in g.groupby('student')['paper_id']}
        if len(by) < m:
            continue
        stud = list(by)
        vals = {k: [] for k in Zs}
        for _ in range(reps):
            pick, used = [], set()
            for s in rng.permutation(len(stud)):
                cands = [p for p in by[stud[s]] if p not in used]
                if cands:
                    p = cands[rng.integers(len(cands))]
                    pick.append(idx[p]); used.add(p)
                if len(pick) == m:
                    break
            if len(pick) < m:
                continue
            for k, Z in Zs.items():
                G = Z[pick] @ Z[pick].T
                vals[k].append((G.sum() - m) / (m * (m - 1)))
        if vals[next(iter(Zs))]:
            out.append(dict(lab=lab, school=g['school'].iloc[0], year=yr, n_students=len(by), **{'ss_' + k: float(np.mean(v)) for k, v in vals.items()}))
    return pd.DataFrame(out)


def estimate(d, ycols, tag, extra):
    """All designs of one table: d has year, lab, student(optional), weights, exposures. Yields dict rows."""
    rows = []
    has_student = 'student' in d
    for ycol, yname in ycols:
        for design, b in DESIGNS:
            if b is None:
                s = d[d['year'].between(2017, 2021) | d['year'].between(*L.POST)].copy()
                s['x'] = (s['year'] >= L.POST[0]).astype(float)
            else:
                s = d[d['year'].between(2017, 2021)].copy()
                s['x'] = (s['year'] >= b).astype(float)
            rows.append(_one(s, ycol, 'x', design, yname, tag, extra, has_student))
        for expo in ('ai_share', 'flag_abstract'):
            for dsg, lo, hi in (('dose_post', L.POST[0], L.POST[1]), ('dose_pre', 2017, 2021)):
                s = d[d['year'].between(lo, hi) & d[expo].notna()].copy()
                s['x'] = s[expo].astype(float)
                rows.append(_one(s, ycol, 'x', f'{dsg}:{expo}', yname, tag, extra, has_student, year_fe=True))
    return rows


def _one(s, ycol, xcol, design, yname, tag, extra, has_student, year_fe=False):
    base = dict(design=design, measure=yname, **tag, **extra)
    if len(s) < 30 or s['lab'].nunique() < 5:
        return dict(base, beta=np.nan, lo=np.nan, hi=np.nan, n=len(s))
    if has_student:
        w = 1.0 / s.groupby('student')['student'].transform('size').to_numpy()
    else:
        w = np.ones(len(s))
    r = F.fit(s[ycol].to_numpy(), s[xcol].to_numpy(), w, s['lab'].to_numpy(), s['year'].to_numpy() if year_fe else None)
    pre = s[s['year'] <= 2021]
    return dict(base, **r, n=len(s), n_students=int(s['student'].nunique()) if has_student else None,
                y_pre_mean=float(pre[ycol].mean()) if len(pre) else np.nan, y_sd=float(s[ycol].std()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--kind', default='abstract')
    ap.add_argument('--no-allai', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='test: keep only the first N student-paper rows per school')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    if (L.RUN / f'effects_{a.model}_{a.kind}.parquet').exists() and not a.force:
        L.log(skip='done', model=a.model, kind=a.kind)
        return
    sp = pd.read_parquet(L.RUN / 'student_papers.parquet')
    pp = pd.read_parquet(L.RUN / 'pi_papers.parquet')
    stu = pd.read_parquet(L.RUN / 'students.parquet')
    if a.limit:
        sp = sp.groupby('school').head(a.limit)
    ids, X = L.load_vectors(a.model, a.kind)
    variants = {'orig': (ids, X)}
    if a.kind == 'abstract' and not a.no_allai:
        variants['allai'] = L.load_vectors(a.model + '__allai', 'abstract')
    common = set(ids)
    for v in variants.values():
        common &= set(v[0])
    uni = L.universe_index()
    common &= set(uni[uni['year'].between(L.Y0, L.Y1)]['paper_id'])
    order = sorted(common)
    idx = {p: i for i, p in enumerate(order)}
    Zs = {}
    for name, (vid, VX) in variants.items():
        pos = {p: i for i, p in enumerate(vid)}
        Zs[name] = L.unit(VX[[pos[p] for p in order]])        # centred on the common set, so original and rewrite are compared on the same papers
    L.log(model=a.model, kind=a.kind, papers=len(order), variants=list(Zs), secs=round(time.time() - t0))
    ai = pd.read_parquet(L.AI_TABLE)[['paper_id', 'ai_share', 'flag_abstract']].drop_duplicates('paper_id')
    pm = pair_measures(sp, pp, stu, Zs, idx)
    pm = pm.merge(ai, on='paper_id', how='left').merge(stu.drop_duplicates('student')[['student', 'role']], on='student', how='left')
    L.log(pair_rows=len(pm), secs=round(time.time() - t0))
    tag = dict(model=a.model, kind=a.kind)
    names = list(Zs)
    rows, yearly = [], []
    for setname, sts in SETS.items():
        d = pm[pm['status'].isin(sts)].copy()
        if d.empty:
            continue
        for m_ in ('sa', 'cd'):
            if len(names) == 2:
                d[f'{m_}_gap'] = d[f'{m_}_orig'] - d[f'{m_}_allai']     # linear: the gap's interval is the interval of the difference
        ycols = [(f'{m_}_{n}', m_ + ':' + n) for m_ in ('sa', 'cd') for n in names + (['gap'] if len(names) == 2 else [])]
        rows += estimate(d, ycols, tag, dict(set=setname, group='all'))
        for col in ('school', 'role'):
            for g, sub in d.groupby(col):
                if g == 'unspecified':
                    continue
                post_only = [x for x in ycols if x[1].endswith('orig') or x[1].endswith('gap')]
                est = estimate(sub, post_only, tag, dict(set=setname, group=f'{col}={g}'))
                rows += [r for r in est if r['design'] in ('post', 'placebo2021', 'dose_post:ai_share', 'dose_pre:ai_share')]
        # lab-year student-student similarity
        spx = sp[sp['status'].isin(sts)]
        ss = lab_year_ss(spx, Zs, idx)
        if len(ss):
            if len(names) == 2:
                ss['ss_gap'] = ss['ss_orig'] - ss['ss_allai']
            la = spx.merge(ai, on='paper_id', how='left').groupby(['lab', 'year'], as_index=False)[['ai_share', 'flag_abstract']].mean()
            ss = ss.merge(la, on=['lab', 'year'], how='left')
            rows += estimate(ss, [(f'ss_{n}', 'ss:' + n) for n in names + (['gap'] if len(names) == 2 else [])], tag, dict(set=setname, group='all'))
        for col, nm in (('sa_orig', 'sa'), ('cd_orig', 'cd')):
            for yr, g in d.groupby('year'):
                w = 1.0 / g.groupby('student')['student'].transform('size')
                yearly.append(dict(model=a.model, kind=a.kind, set=setname, measure=nm, year=yr, n=len(g), students=g['student'].nunique(),
                                   mean=float(np.average(g[col], weights=w)),
                                   mean_allai=float(np.average(g[col.replace('orig', 'allai')], weights=w)) if 'allai' in names else np.nan))
        if len(ss):
            for yr, g in ss.groupby('year'):
                yearly.append(dict(model=a.model, kind=a.kind, set=setname, measure='ss', year=yr, n=len(g), students=int(g['n_students'].sum()),
                                   mean=float(g['ss_orig'].mean()), mean_allai=float(g['ss_allai'].mean()) if 'allai' in names else np.nan))
        L.log(set=setname, rows=len(d), secs=round(time.time() - t0))
    pd.DataFrame(rows).to_parquet(L.RUN / f'effects_{a.model}_{a.kind}.parquet')
    pd.DataFrame(yearly).to_parquet(L.RUN / f'yearly_{a.model}_{a.kind}.parquet')
    L.log(done=f'{a.model}_{a.kind}', rows=len(rows), secs=round(time.time() - t0))


if __name__ == '__main__':
    main()
