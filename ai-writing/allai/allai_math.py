"""The numpy-only helpers of allai_analyze.py (tested on fixtures in tests/test_allai.py)."""
import numpy as np

import measures as M


def gram_geometry(U):
    """(dispersion, mean pairwise cosine distance, Vendi score) of unit rows U."""
    S = U @ U.T
    n = len(S)
    d = np.sqrt(np.clip(np.diag(S) - 2 * S.mean(1) + S.sum() / n ** 2, 0, None))
    pw = 1.0 - (S.sum() - np.trace(S)) / (n * (n - 1))
    w = np.linalg.eigvalsh(S / n)
    w = w[w > 1e-12]
    return float(d.mean()), float(pw), float(np.exp(-(w * np.log(w)).sum()))


def entropy_bits(labels, k):
    c = np.bincount(labels, minlength=k)
    return M.shannon(c)


def nearest_centroid(Z, cent, chunk=20000):
    out = np.empty(len(Z), np.int32)
    for i in range(0, len(Z), chunk):
        out[i:i + chunk] = (Z[i:i + chunk] @ cent.T).argmax(1)
    return out


def draw(rng, pool, m):
    return pool[rng.choice(len(pool), m, replace=False)]
