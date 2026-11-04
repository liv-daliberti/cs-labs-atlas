"""Detector-free cross-checks of "the amount of AI" (owner 2026-11-04), numpy/scipy only.

kobak_rate(text, words)       occurrences of Kobak et al. (2024) excess style words per 1,000 tokens (the word list is 379 style words:
                              studies/homogenization/lit/kobak_reference/kobak_2024_style_words.csv)
LiangMixture                  the distributional LLM-modified-fraction estimator of Liang et al. (2024, "Mapping the Increasing Use of LLMs in
                              Scientific Papers"): each document is a binary word-occurrence vector over a vocabulary; human documents have word
                              probabilities p, LLM-modified documents q (both estimated on training text, add-half smoothed); a target corpus is the
                              mixture (1 - a) P + a Q and `a` maximizes its log-likelihood. `estimate` returns a with a bootstrap interval over documents.
The independence-over-words likelihood is what Liang et al. use; it is only trusted after `calibration` (synthetic mixtures of held-out human and
LLM documents at known a) shows how far the estimate is off, and the report prints that table.
"""
import re

import numpy as np
import scipy.sparse as sp
from scipy.optimize import minimize_scalar

TOKEN = re.compile(r"[a-z]+(?:'[a-z]+)?")


def tokens(text):
    return TOKEN.findall((text or '').lower())


def kobak_rate(text, words):
    """Occurrences of `words` (a set of lower-case strings) per 1,000 tokens of `text`; NaN for an empty text."""
    toks = tokens(text)
    if not toks:
        return float('nan')
    return 1000.0 * sum(t in words for t in toks) / len(toks)


def build_vocab(docs_tokens, size=5000, min_df=5):
    """The `size` most frequent words by document frequency (a word in fewer than `min_df` documents is dropped). {word: column}."""
    df = {}
    for toks in docs_tokens:
        for w in set(toks):
            df[w] = df.get(w, 0) + 1
    keep = sorted((w for w, c in df.items() if c >= min_df), key=lambda w: (-df[w], w))[:size]
    return {w: i for i, w in enumerate(keep)}


def occurrence_matrix(docs_tokens, vocab):
    """Binary (documents x vocabulary) CSR matrix: word i occurs in document d."""
    rows, cols = [], []
    for d, toks in enumerate(docs_tokens):
        for w in set(toks):
            j = vocab.get(w)
            if j is not None:
                rows.append(d); cols.append(j)
    return sp.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(len(docs_tokens), len(vocab)))


class LiangMixture:
    def __init__(self, X_human, X_llm, smooth=0.5):
        n0, n1 = X_human.shape[0], X_llm.shape[0]
        self.p = (np.asarray(X_human.sum(0)).ravel() + smooth) / (n0 + 2 * smooth)
        self.q = (np.asarray(X_llm.sum(0)).ravel() + smooth) / (n1 + 2 * smooth)
        self.w_p = np.log(self.p / (1 - self.p))
        self.w_q = np.log(self.q / (1 - self.q))
        self.c_p = np.log(1 - self.p).sum()
        self.c_q = np.log(1 - self.q).sum()

    def loglik_parts(self, X):
        """(log P(d), log Q(d)) for every row of X."""
        return X @ self.w_p + self.c_p, X @ self.w_q + self.c_q

    @staticmethod
    def _alpha(lp, lq):
        def nll(a):
            return -np.logaddexp(np.log1p(-a) + lp, np.log(a) + lq).sum()
        r = minimize_scalar(nll, bounds=(1e-6, 1 - 1e-6), method='bounded', options=dict(xatol=1e-5))
        # the optimum can sit at the boundary: compare with a = 0 and a = 1 exactly
        cand = {float(r.x): r.fun, 0.0: -lp.sum(), 1.0: -lq.sum()}
        return min(cand, key=cand.get)

    def estimate(self, X, boot=200, seed=0):
        """(alpha, lo, hi): the maximum-likelihood LLM fraction of the documents X and a 95% bootstrap interval over documents."""
        lp, lq = self.loglik_parts(X)
        a = self._alpha(lp, lq)
        if boot <= 0 or len(lp) < 2:
            return a, float('nan'), float('nan')
        rng = np.random.default_rng(seed)
        bs = [self._alpha(lp[i], lq[i]) for i in (rng.integers(0, len(lp), len(lp)) for _ in range(boot))]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        return a, float(lo), float(hi)


def calibration(model, X_human_test, X_llm_test, alphas=(0, .05, .1, .25, .5, 1.0), n=1000, seed=0):
    """[(true alpha, estimate)] on synthetic corpora of n documents, a share `alpha` drawn from the held-out LLM documents."""
    rng = np.random.default_rng(seed)
    out = []
    for a in alphas:
        k = int(round(a * n))
        h = X_human_test[rng.integers(0, X_human_test.shape[0], n - k)]
        l = X_llm_test[rng.integers(0, X_llm_test.shape[0], k)] if k else None
        X = sp.vstack([h, l]).tocsr() if k else h
        out.append((a, model.estimate(X, boot=0)[0]))
    return out
