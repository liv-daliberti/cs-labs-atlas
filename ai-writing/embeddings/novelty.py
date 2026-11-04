"""Novelty of each paper against the papers of the previous k years in the same scope.

For a paper of year y in a scope (a lab, a department, a school, or everything) the reference pool is the scope's papers of years y-k .. y-1
(the paper's own year is never in it, so a paper is not compared with its contemporaries or itself). On L2-normalized vectors:
  nov_max  = 1 - max cosine to the pool                       (distance to the closest earlier paper)
  nov_nn   = 1 - mean cosine of the `nn` nearest pool papers   (nn = 5; a pool smaller than nn uses all of it; n_ref says how many)
and the same two on a pool capped at `cap` papers drawn at random (fixed seed, one draw per scope and year, shared by all that year's papers),
nov_max_cap and nov_nn_cap: the uncapped pool grows with the output of the scope, which alone lowers 1 - max cosine, so the size-matched
columns are the ones to compare across years in big scopes. Papers with an empty pool get NaN and n_ref = 0.
Vectors are centred on the corpus mean and normalized before the cosines (SPECTER2 is anisotropic: ai-writing/diversity/common.center_normalize).
numpy only; torch (GPU) is used for the matrix products when present and asked for.
"""
import numpy as np


def center_normalize(X, mu=None):
    X = np.asarray(X, np.float32)
    mu = X.mean(0) if mu is None else mu
    Y = X - mu
    return Y / (np.linalg.norm(Y, axis=1, keepdims=True) + 1e-9), mu


def _sims(A, B, dev):
    if dev is None:
        return A @ B.T
    import torch
    return (torch.as_tensor(A, device=dev) @ torch.as_tensor(B, device=dev).T).float().cpu().numpy()


def _stats(S, ok, nn):
    """(1 - max, 1 - mean of the top-nn) per row of S over the columns where `ok` (a boolean row mask shared by all rows)."""
    S = S[:, ok]
    if S.shape[1] == 0:
        return np.full(S.shape[0], np.nan), np.full(S.shape[0], np.nan), 0
    m = min(nn, S.shape[1])
    top = np.partition(S, S.shape[1] - m, axis=1)[:, -m:] if S.shape[1] > m else S
    return 1 - S.max(1), 1 - top.mean(1), S.shape[1]


def novelty_group(Z, years, idx, ks=(1, 3, 5), nn=5, cap=2000, seed=0, dev=None, row_chunk=2048):
    """Rows for the papers `idx` (indices into Z/years) of one scope: dict of arrays
    paper (index), k, n_ref, nov_max, nov_nn, n_ref_cap, nov_max_cap, nov_nn_cap, all of length len(idx) * len(ks)."""
    idx = np.asarray(idx)
    yrs = years[idx]
    out = {k: [] for k in ('paper', 'k', 'n_ref', 'nov_max', 'nov_nn', 'n_ref_cap', 'nov_max_cap', 'nov_nn_cap')}
    kmax = max(ks)
    rng = np.random.default_rng(seed)
    for y in np.unique(yrs):
        T = idx[yrs == y]
        pool_mask = (yrs >= y - kmax) & (yrs < y)
        pool = idx[pool_mask]
        pyears = years[pool]
        capped = {}
        for k in ks:
            sel = np.nonzero((pyears >= y - k))[0]
            if cap and len(sel) > cap:
                sel = np.sort(rng.choice(sel, cap, replace=False))
            capped[k] = sel
        for c0 in range(0, len(T), row_chunk):
            Tc = T[c0:c0 + row_chunk]
            S = _sims(Z[Tc], Z[pool], dev) if len(pool) else np.zeros((len(Tc), 0), np.float32)
            for k in ks:
                ok = pyears >= y - k
                a, b, n = _stats(S, ok, nn)
                col = np.zeros(len(pool), bool); col[capped[k]] = True
                a2, b2, n2 = _stats(S, col, nn)
                for key, v in (('paper', Tc), ('k', np.full(len(Tc), k)), ('n_ref', np.full(len(Tc), n)), ('nov_max', a), ('nov_nn', b),
                               ('n_ref_cap', np.full(len(Tc), n2)), ('nov_max_cap', a2), ('nov_nn_cap', b2)):
                    out[key].append(v)
    return {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in out.items()}


def novelty_scopes(Z, years, scopes, **kw):
    """scopes: iterable of (scope, scope_id, member indices). Rows of every group with scope / scope_id columns added (lists of str)."""
    parts, sc, sid = [], [], []
    for scope, scope_id, members in scopes:
        if len(members) == 0:
            continue
        r = novelty_group(Z, years, members, **kw)
        parts.append(r)
        sc += [scope] * len(r['paper']); sid += [scope_id] * len(r['paper'])
    keys = ('paper', 'k', 'n_ref', 'nov_max', 'nov_nn', 'n_ref_cap', 'nov_max_cap', 'nov_nn_cap')
    out = {k: np.concatenate([p[k] for p in parts]) if parts else np.zeros(0) for k in keys}
    out['scope'] = np.array(sc); out['scope_id'] = np.array(sid)
    return out


def brute(Z, years, idx, k, nn):
    """Reference implementation for the tests: per paper, 1 - max and 1 - mean top-nn over the previous k years' papers of `idx`."""
    res = {}
    for i in idx:
        pool = [j for j in idx if years[i] - k <= years[j] < years[i]]
        if not pool:
            res[i] = (np.nan, np.nan, 0); continue
        s = np.sort(Z[pool] @ Z[i])[::-1]
        res[i] = (1 - s[0], 1 - s[:min(nn, len(s))].mean(), len(pool))
    return res
