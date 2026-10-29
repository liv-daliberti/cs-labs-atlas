"""The diversity measures of DESIGN-v2.md section 2, as small functions over a set of papers (or one paper).

Embedding inputs are unit rows: the corpus mean subtracted, then L2-normalized (common.center_normalize), so cosine
similarity is a dot product and the anisotropy of SPECTER2 (random CS papers sit at cosine ~0.8) does not compress
every distance. Set-level measures also have Gram-matrix forms (gram_measures), so a lab's draws index one
precomputed matrix instead of re-multiplying vectors; tests check the two forms agree.

Semantic (set-level unless noted)
  S1 extent        largest Euclidean distance of a paper from the set's centroid (Hao et al. M8)
  S2 dispersion    mean Euclidean distance from the centroid
  S3 pairwise      mean pairwise cosine distance, 1 - mean_{i<j} u_i.u_j
  S4 Vendi         exp(entropy of the eigenvalues of K/n), K the cosine-similarity matrix (Friedman & Dieng 2023):
                   1 for identical papers, k for k orthogonal ones
  S5 topic entropy entropy (nats) of the set's shares over 50 global k-means clusters;  S6 = exp(S5)
  S7 Rao-Stirling  sum_{a != b} d_ab p_a p_b, d_ab the cosine distance between cluster centroids
  S8 within-paper  (paper-level) mean pairwise cosine distance between one paper's own segment embeddings; the mean
                   pairwise distance does not depend on the number of segments, unlike the mean distance to centroid
Lexical / stylistic (full text; paper-level unless noted)
  L1 MATTR         mean type-token ratio over every 1,000-token window (moving by one token)
  L2 unigram entropy  mean entropy (nats) over consecutive non-overlapping 1,000-token windows (a whole-text entropy
                   grows with length)
  L3 homogeneity   (set-level) mean pairwise cosine of TF-IDF vectors; higher = more alike
  L4 n-gram novelty share of a paper's distinct word trigrams absent from a reference set of the lab's earlier papers
  L5 sentence length  mean and SD of words per sentence (sentences of 3-120 words)
  L6 readability spread (set-level) SD of the papers' Flesch reading ease
  L7 LLM-marker rate  Kobak et al.'s excess style words per 1,000 tokens (a check on the detector, not diversity)
  L8 compression   (set-level) zlib size of the concatenated texts / sum of their individual zlib sizes;
                   1 = nothing shared, lower = more alike. Texts are fixed-length excerpts shorter than DEFLATE's 32 KB
                   window, so a text can be matched against the ~7 texts before it
Novelty
  N1               (paper-level) cosine distance to the nearest paper of the previous year in a fixed-size arXiv CS
                   background sample (near-duplicates, cosine > 0.97, are the paper's own preprint and are skipped)
  N2               (paper-level) whether the paper's topic cluster is absent from a reference set of the lab's earlier
                   papers
Citations
  C1               (set-level) venue entropy of a fixed number of references drawn from the set's pooled references
  C2               (set-level) mean pairwise Jaccard overlap of reference lists
  C3               (set-level) SD of reference ages (citing year - cited year) pooled over the set
  C4               (paper-level) share of a paper's references that are the lab's own papers
Resampling: every set-level measure is averaged over equal-size draws (equal_size_n, resample).
"""
import math, re, zlib
from functools import lru_cache
import numpy as np

# ------------------------------------------------------------------ resampling

def equal_size_n(sizes, min_n=5, n=None):
    """The common draw size: n if given, else the smallest group; None when it is below min_n."""
    m = min(sizes) if n is None else n
    if m < min_n or any(s < m for s in sizes):
        return None
    return int(m)


def draws_for(size, n, draws, rng):
    """(draws x n) index matrix of draws without replacement; a single full draw when n == size (every draw would be
    the whole group)."""
    if n == size:
        return np.arange(size)[None, :]
    return np.vstack([rng.choice(size, n, replace=False) for _ in range(draws)])


def resample(fn, sizes, draws=1000, min_n=5, n=None, rng=None):
    """fn(group, idx) -> {measure: value}. Returns (n, [ {measure: mean over draws} per group ]) or (None, None).
    Every group is drawn at the same n, so size alone cannot make one group look more diverse."""
    rng = rng if rng is not None else np.random.default_rng(0)
    n = equal_size_n(sizes, min_n, n)
    if n is None:
        return None, None
    out = []
    for g, s in enumerate(sizes):
        vals = {}
        for idx in draws_for(s, n, draws, rng):
            for k, v in fn(g, idx).items():
                vals.setdefault(k, []).append(v)
        row = {}
        for k, v in vals.items():
            v = np.asarray(v, float)
            row[k] = float(np.nanmean(v)) if np.isfinite(v).any() else float('nan')
        out.append(row)
    return n, out


# ------------------------------------------------------------------ semantic

def mean_offdiag(S):
    n = len(S)
    return float((S.sum() - np.trace(S)) / (n * (n - 1))) if n > 1 else float('nan')


def extent(U):
    c = U.mean(0)
    return float(np.sqrt(((U - c) ** 2).sum(1)).max())


def dispersion(U):
    c = U.mean(0)
    return float(np.sqrt(((U - c) ** 2).sum(1)).mean())


def pairwise_distance(U):
    return 1.0 - mean_offdiag(U @ U.T)


def vendi_from_gram(K):
    w = np.linalg.eigvalsh(K / len(K))
    w = w[w > 1e-12]
    return float(np.exp(-(w * np.log(w)).sum()))


def vendi(U):
    return vendi_from_gram(U @ U.T)


def gram_measures(S):
    """S1-S4 from the cosine-similarity matrix of unit rows: |u_i - c|^2 = S_ii - 2 mean_j S_ij + mean_jk S_jk."""
    n = len(S)
    d = np.sqrt(np.clip(np.diag(S) - 2 * S.mean(1) + S.sum() / n ** 2, 0, None))
    return dict(S1=float(d.max()), S2=float(d.mean()), S3=1.0 - mean_offdiag(S), S4=vendi_from_gram(S))


def topic_measures(labels, D):
    """S5 entropy, S6 effective number of topics, S7 Rao-Stirling, for integer cluster labels and the k x k
    centroid distance matrix D (zero diagonal)."""
    p = np.bincount(labels, minlength=len(D)) / len(labels)
    nz = p[p > 0]
    h = float(-(nz * np.log(nz)).sum())
    return dict(S5=h, S6=float(np.exp(h)), S7=float(p @ D @ p))


def centroid_distances(centroids):
    Cn = centroids / np.linalg.norm(centroids, axis=1, keepdims=True)
    D = 1.0 - Cn @ Cn.T
    np.fill_diagonal(D, 0.0)
    return np.clip(D, 0, None)


def loo_centroid_distance(U):
    """Each paper's Euclidean distance from the centroid of the other papers of its set (n >= 3)."""
    n = len(U)
    if n < 3:
        return np.full(n, np.nan)
    C = (U.sum(0)[None, :] - U) / (n - 1)
    return np.sqrt(((U - C) ** 2).sum(1))


def within_paper_spread(P, min_seg=5):
    """S8: mean pairwise cosine distance between a paper's unit segment vectors, (|sum u|^2 - n) / (n(n-1))."""
    n = len(P)
    if n < min_seg:
        return float('nan')
    s = P.sum(0)
    return float(1.0 - (s @ s - n) / (n * (n - 1)))


def nearest_distance(u, B, exclude_above=0.97):
    """N1: 1 - the largest cosine between unit vector u and the unit rows of B, skipping near-duplicates."""
    s = B @ u
    s = s[s <= exclude_above]
    return float(1.0 - s.max()) if len(s) else float('nan')


def set_novelty(own, refs):
    """Share of the distinct items of `own` (a sorted unique array) not in the union of the reference arrays."""
    if len(own) == 0:
        return float('nan')
    pool = np.unique(np.concatenate(refs)) if len(refs) else np.zeros(0, own.dtype)
    return float(1.0 - np.isin(own, pool, assume_unique=True).mean())


def reference_novelty(own, pool, k, rng, reps=10):
    """Novelty of `own` against k papers drawn from `pool` (a list of item arrays), averaged over reps draws; the
    reference set has a fixed size, so a lab with more earlier papers does not look less novel by that alone."""
    if len(pool) < k:
        return float('nan')
    return float(np.mean([set_novelty(own, [pool[i] for i in rng.choice(len(pool), k, replace=False)]) for _ in range(reps)]))


# ------------------------------------------------------------------ lexical

TOKEN = re.compile(r"[a-z]+(?:['\-][a-z]+)*")
SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z(\[])')


def tokens(text):
    return TOKEN.findall(text.lower())


def token_ids(toks):
    vocab = {}
    return np.fromiter((vocab.setdefault(t, len(vocab)) for t in toks), dtype=np.int64, count=len(toks))


def mattr(ids, w=1000):
    """L1. Token i is new to window s (covering s..s+w-1) iff s <= i < s+w and its previous occurrence is before s,
    so it counts in windows max(prev+1, i-w+1) .. min(i, last window): a difference array gives every window's
    number of types in O(n)."""
    ids = np.asarray(ids)
    n = len(ids)
    if n < w:
        return float('nan')
    order = np.lexsort((np.arange(n), ids))
    prev = np.full(n, -1)
    same = ids[order[1:]] == ids[order[:-1]]
    prev[order[1:][same]] = order[:-1][same]
    nwin = n - w + 1
    pos = np.arange(n)
    start = np.maximum(prev + 1, pos - w + 1)
    end = np.minimum(pos, nwin - 1)
    ok = start <= end
    diff = np.bincount(start[ok], minlength=nwin + 1) - np.bincount(end[ok] + 1, minlength=nwin + 1)
    return float(np.cumsum(diff)[:nwin].mean() / w)


def unigram_entropy(ids, w=1000):
    """L2: mean entropy over consecutive non-overlapping w-token windows."""
    ids = np.asarray(ids)
    k = len(ids) // w
    if k == 0:
        return float('nan')
    h = []
    for j in range(k):
        c = np.bincount(ids[j * w:(j + 1) * w])
        p = c[c > 0] / w
        h.append(-(p * np.log(p)).sum())
    return float(np.mean(h))


def sentences(text, lo=3, hi=120):
    return [s for s in SENT.split(text) if lo <= len(s.split()) <= hi]


def sentence_stats(sents):
    """L5: (mean, SD) of sentence length in words."""
    if len(sents) < 5:
        return float('nan'), float('nan')
    L = np.array([len(s.split()) for s in sents], float)
    return float(L.mean()), float(L.std(ddof=1))


@lru_cache(maxsize=200000)
def syllables(word):
    w = re.sub(r'[^a-z]', '', word.lower())
    if not w:
        return 0
    n = len(re.findall(r'[aeiouy]+', w))
    if w.endswith('e') and not w.endswith(('le', 'ee')) and n > 1:
        n -= 1
    return max(1, n)


def flesch(sents):
    """Flesch reading ease, 206.835 - 1.015 words/sentence - 84.6 syllables/word, over alphabetic words."""
    words = [w for s in sents for w in s.split() if any(c.isalpha() for c in w)]
    if len(sents) < 5 or not words:
        return float('nan')
    return float(206.835 - 1.015 * len(words) / len(sents) - 84.6 * sum(syllables(w) for w in words) / len(words))


def marker_rate(toks, words):
    """L7: occurrences of the marker words per 1,000 tokens."""
    return 1000.0 * sum(t in words for t in toks) / len(toks) if toks else float('nan')


def trigram_set(toks):
    """Sorted unique 32-bit hashes of the word trigrams (CRC32 per token, mixed; collisions are negligible at the
    ~10^4 trigrams compared at a time)."""
    if len(toks) < 3:
        return np.zeros(0, np.uint32)
    cache = {}
    h = np.fromiter((cache.setdefault(t, zlib.crc32(t.encode())) for t in toks), dtype=np.uint64, count=len(toks))
    tri = ((h[:-2] * np.uint64(1000003)) ^ h[1:-1]) * np.uint64(1000033) ^ h[2:]
    return np.unique((tri & np.uint64(0xFFFFFFFF)).astype(np.uint32))


def compression_ratio(blobs, sizes=None):
    """L8: len(zlib(concatenation)) / sum(len(zlib(each))); sizes are the precomputed individual sizes."""
    sizes = [len(zlib.compress(b, 9)) for b in blobs] if sizes is None else sizes
    return len(zlib.compress(b''.join(blobs), 9)) / float(sum(sizes))


def excerpt(text, chars=4000):
    """A fixed-length excerpt for L8, cut at a word boundary."""
    t = text[:chars]
    k = t.rfind(' ')
    return (t[:k] if k > chars * 0.8 else t).encode('utf-8', 'ignore')


# ------------------------------------------------------------------ citations

def entropy_of(items):
    _, c = np.unique(np.asarray(items), return_counts=True)
    p = c / c.sum()
    return float(-(p * np.log(p)).sum())


def venue_entropy(venues, m, rng):
    """C1: entropy of m references drawn from the pooled venue list (fixed m: entropy grows with sample size)."""
    if len(venues) < m:
        return float('nan')
    return entropy_of(np.asarray(venues)[rng.choice(len(venues), m, replace=False)])


def jaccard_matrix(sets):
    """Pairwise Jaccard overlap of reference sets (lists of hashable ids)."""
    from scipy import sparse
    vocab, r, c = {}, [], []
    for i, s in enumerate(sets):
        for x in set(s):
            r.append(i); c.append(vocab.setdefault(x, len(vocab)))
    P = sparse.csr_matrix((np.ones(len(r)), (r, c)), shape=(len(sets), max(1, len(vocab))))
    inter = (P @ P.T).toarray()
    size = np.asarray(P.sum(1)).ravel()
    union = size[:, None] + size[None, :] - inter
    return np.where(union > 0, inter / np.maximum(union, 1), 0.0)


def age_spread(ages):
    """C3: SD of reference ages (ddof 1)."""
    a = np.asarray(ages, float)
    return float(a.std(ddof=1)) if len(a) >= 10 else float('nan')


def self_share(ref_ids, own_ids):
    """C4: share of a paper's references that are in own_ids (the lab's papers)."""
    return float(np.mean([r in own_ids for r in ref_ids])) if ref_ids else float('nan')
