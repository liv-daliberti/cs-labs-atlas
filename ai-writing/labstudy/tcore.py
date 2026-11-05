"""Engine of the topic-convergence analysis: size-matched, smoothed topic distributions per lab-year, pairwise Jensen-Shannon divergence, distance to the centroid.

A *run* is one labelling of papers (an integer topic code per paper, -1 = none) and a validity mask. For every year, every lab with at least `m` valid papers is
drawn `reps` times (m papers without replacement; the generator is seeded by (year, lab) so two runs on the same papers draw the same rows: the original and
the all-AI-rewritten labelling are exactly paired). A draw's counts become p = (counts + alpha * q) / (m + alpha), q the pooled topic distribution of the run
(a fixed prior: the same shrinkage for every lab and year, so it does not create a trend). Base-2 logs: JSD in [0, 1].
Pairs of labs (all, within school, within department, between schools, within department type) are enumerated per year and capped at `max_pairs` by uniform
sampling; the mean pairwise JSD of the draws is stored per pair, so the lab bootstrap (multinomial lab weights, pair weight w_i w_j) never recomputes a divergence.
"""
import numpy as np
import pandas as pd

import lcommon as L


def entropy_bits(P):
    with np.errstate(divide='ignore', invalid='ignore'):
        return -(np.where(P > 0, P * np.log2(P), 0.0)).sum(-1)


def jsd_pairs(P, H, pi, pj, chunk=1500):
    """Mean over reps of JSD(P[pi, r], P[pj, r]); P: labs x reps x K (float32), H: labs x reps entropies."""
    out = np.empty(len(pi), np.float32)
    for s in range(0, len(pi), chunk):
        a, b = pi[s:s + chunk], pj[s:s + chunk]
        M = (P[a] + P[b]) * 0.5
        out[s:s + chunk] = (entropy_bits(M) - 0.5 * (H[a] + H[b])).mean(1)
    return np.clip(out, 0, 1)


def jsd_to(P, H, c):
    """Mean over reps of JSD(P[i, r], c[r]); c: reps x K."""
    M = (P + c[None]) * 0.5
    Hc = entropy_bits(c)
    return np.clip((entropy_bits(M) - 0.5 * (H + Hc[None])).mean(1), 0, 1)


class Run:
    def __init__(self, name, codes, valid, K, llm_mask=None, genai_mask=None):
        self.name, self.codes, self.valid, self.K = name, np.asarray(codes), np.asarray(valid, bool), int(K)
        self.llm = np.zeros(self.K, bool) if llm_mask is None else np.asarray(llm_mask, bool)
        self.genai = self.llm if genai_mask is None else np.asarray(genai_mask, bool)
        ok = self.valid & (self.codes >= 0)
        self.q = np.bincount(self.codes[ok], minlength=self.K).astype(np.float64)
        self.q = (self.q / max(self.q.sum(), 1)).astype(np.float32)


def groups_of(lp, row_of, run, m):
    """lab-year groups with >= m valid papers: DataFrame lab_id, year, rows (array of frame rows)."""
    d = lp[['paper_id', 'lab_id', 'year']].copy()
    d['row'] = d['paper_id'].map(row_of)
    d = d.dropna(subset=['row'])
    d['row'] = d['row'].astype(int)
    d = d[run.valid[d['row'].to_numpy()] & (run.codes[d['row'].to_numpy()] >= 0)]
    g = d.groupby(['lab_id', 'year'])['row'].apply(np.array).reset_index()
    g['n'] = g['row'].map(len)
    return g[g['n'] >= m].reset_index(drop=True)


def draw_counts(run, rows_list, lab_ids, year, m, reps):
    G = len(rows_list)
    counts = np.zeros((G, reps, run.K), np.float32)
    for gi, (rows, lab) in enumerate(zip(rows_list, lab_ids)):
        rng = np.random.default_rng((L.SEED, int(year), int(lab)))
        pick = rng.random((reps, len(rows))).argsort(1)[:, :m]
        codes = run.codes[rows[pick]]                            # reps x m
        r = np.repeat(np.arange(reps), m)
        np.add.at(counts[gi], (r, codes.ravel()), 1.0)
    return counts


def sample_pairs(idx_groups, max_pairs, rng):
    """All within-group pairs (i<j) of the index groups, uniformly thinned to max_pairs."""
    pi, pj = [], []
    for ix in idx_groups:
        if len(ix) < 2:
            continue
        a, b = np.triu_indices(len(ix), 1)
        pi.append(ix[a]); pj.append(ix[b])
    if not pi:
        return np.zeros(0, int), np.zeros(0, int)
    pi, pj = np.concatenate(pi), np.concatenate(pj)
    if len(pi) > max_pairs:
        k = rng.choice(len(pi), max_pairs, replace=False)
        pi, pj = pi[k], pj[k]
    return pi, pj


def year_job(args):
    """One year of one run. Pass 1 (cent_pre None): (labyear DataFrame, pairs DataFrame, year centroid K-vector); pass 2: the labs' distance to the fixed pre-period centroid."""
    run, g, lm, year, m, reps, alpha, max_pairs, scopes, cent_pre = args
    gy = g[g['year'] == year].reset_index(drop=True)
    if len(gy) < 5:
        return None
    labs = gy['lab_id'].map(lm['code']).to_numpy()
    counts = draw_counts(run, list(gy['row']), labs, year, m, reps)
    P = ((counts + alpha * run.q[None, None, :]) / (m + alpha)).astype(np.float32)
    H = entropy_bits(P)
    if cent_pre is not None:
        return jsd_to(P, H, np.broadcast_to(cent_pre, (reps, run.K)).astype(np.float32))
    cent = P.mean(0)                                             # reps x K: the year's all-lab centroid
    school = gy['lab_id'].map(lm['school']).to_numpy()
    dept = gy['lab_id'].map(lm['deptkey']).to_numpy()
    dtype = gy['lab_id'].map(lm['dtype']).to_numpy()
    noise = 1e-3 * np.random.default_rng((L.SEED, int(year), 3)).random(counts.shape)
    top = (counts + noise).argmax(-1)                            # labs x reps
    mass = P[:, :, run.llm].sum(-1).mean(1) if run.llm.any() else np.zeros(len(gy))
    ly = pd.DataFrame(dict(lab_id=gy['lab_id'], year=year, n=gy['n'], entropy=H.mean(1), dist_centroid=jsd_to(P, H, cent), top_llm=run.llm[top].mean(1),
                           top_genai=run.genai[top].mean(1), mass_llm=mass, school=school, dtype=dtype))
    rng = np.random.default_rng((L.SEED, int(year), 7))
    G = len(gy)
    ii = np.arange(G)
    pairs = []
    if 'all' in scopes:
        a, b = np.triu_indices(G, 1)
        if len(a) > max_pairs:
            k = rng.choice(len(a), max_pairs, replace=False)
            a, b = a[k], b[k]
        pairs.append(('all', a, b))
        x = school[a] != school[b]
        pairs.append(('between_school', a[x], b[x]))
    def by(key):
        return [ii[key == v] for v in pd.unique(key)]
    if 'within_school' in scopes:
        pairs.append(('within_school',) + sample_pairs(by(school), max_pairs, rng))
    if 'within_dept' in scopes:
        pairs.append(('within_dept',) + sample_pairs(by(dept), max_pairs, rng))
    if 'within_dtype' in scopes:
        for t in np.unique(dtype):
            if t not in ('unknown', 'other'):
                pairs.append((f'dtype:{t}',) + sample_pairs([ii[dtype == t]], max_pairs, rng))
    rows = []
    lab_arr = gy['lab_id'].to_numpy()
    for sc, a, b in pairs:
        if len(a):
            rows.append(pd.DataFrame(dict(scope=sc, year=year, lab_i=lab_arr[a], lab_j=lab_arr[b], jsd=jsd_pairs(P, H, a, b))))
    return ly, (pd.concat(rows, ignore_index=True) if rows else None), P.mean((0, 1))


def lab_meta(labs):
    """Per-lab lookups (Series by lab_id): integer code, school, school|dept key, department type."""
    labs = labs.drop_duplicates('lab_id').copy()
    labs['deptkey'] = labs['school'] + '|' + labs['dept'].fillna('?')
    labs = labs.sort_values('lab_id').reset_index(drop=True)
    s = labs.set_index('lab_id')
    return dict(code=pd.Series(np.arange(len(labs)), index=labs['lab_id']), school=s['school'], deptkey=s['deptkey'], dtype=s['dept_type'])
