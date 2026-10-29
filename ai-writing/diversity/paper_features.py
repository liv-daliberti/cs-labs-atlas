"""Paper-level features for the diversity battery, and the per-paper pieces the lab-level draws need.

text      every usable full text in the local snapshot (common.usable_text: >= 1,000 body words; a PDF must show its
          title on page 1): L1 MATTR, L2 unigram entropy, L5 sentence length mean / SD, Flesch reading ease (for L6),
          L7 Kobak rare-style-word rate, plus
            trigrams  word-trigram hash sets (L4)                       -> LOCAL/trigrams.npz
            excerpt   the body's first 4,000 characters and its zlib size (L8) -> LOCAL/excerpts.pkl
            tf-idf    the first 5,000 tokens (stopwords and words under 3 letters dropped), hashed to 2^22 columns,
                      sublinear tf x smoothed idf over all full texts, terms in < 3 texts dropped, L2-normalized (L3)
                      -> LOCAL/tfidf.npz
abstract  N1: cosine distance (raw SPECTER2 vectors, L2-normalized) to the nearest of the year-before background
          sample (embed_fulltext.py; 10,000 arXiv CS papers per year), skipping cosine > 0.97 (the paper's own preprint)
full text S8: mean pairwise cosine distance between a paper's segment vectors (corpus segment mean subtracted, then
          normalized), papers with >= 5 segments
topics    k-means on the centred, normalized vectors of all lab papers: 50 clusters (S5-S7, N2) and 10 (the lab-level
          topic fixed effect) in the abstract space; 50 in the full-text space -> labels here, centroids in data/topics.npz
refs      S2 reference lists matched by DOI / arXiv id / normalized title (common.match_refs): n_refs
-> data/paper_features.parquet (one row per paper of papers.jsonl.gz)
"""
import os, pickle, sqlite3, time, zlib
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
import common as C
import measures as M

KOB = {w.strip().lower() for w in C.KOBAK.read_text().splitlines()[1:] if w.strip()}
HASH_BITS = 22
TFIDF_TOKENS = 5000


def text_worker(rng_rows):
    lo, hi = rng_rows
    db = sqlite3.connect(C.SNAPSHOT)
    out = []
    for key, kind, body, flags in db.execute('select key, kind, body, flags from texts where rowid >= ? and rowid < ?', (lo, hi)):
        if not body:
            continue
        body = zlib.decompress(body).decode('utf-8', 'ignore')
        if not C.usable_text(kind, body, C.json.loads(flags or '{}')):
            continue
        toks = M.tokens(body)
        ids = M.token_ids(toks)
        sents = M.sentences(body)
        m, sd = M.sentence_stats(sents)
        hits = sum(t in KOB for t in toks)
        feat = dict(key=key, words=len(toks), L1=M.mattr(ids), L2=M.unigram_entropy(ids), L5_mean=m, L5_sd=sd, fre=M.flesch(sents),
                    L7=1000.0 * hits / max(1, len(toks)), L7_hits=hits)
        ex = M.excerpt(body)
        tt = [t for t in toks[:TFIDF_TOKENS] if len(t) >= 3 and t not in ENGLISH_STOP_WORDS]
        h = np.fromiter((zlib.crc32(t.encode()) & ((1 << HASH_BITS) - 1) for t in tt), dtype=np.int64, count=len(tt))
        u, c = np.unique(h, return_counts=True)
        out.append((feat, M.trigram_set(toks), ex, len(zlib.compress(ex, 9)), u.astype(np.int32), c.astype(np.int32)))
    db.close()
    return out


def text_features(workers):
    db = sqlite3.connect(C.SNAPSHOT)
    hi = db.execute('select max(rowid) from texts').fetchone()[0] or 0
    db.close()
    ranges = [(lo, lo + 150) for lo in range(0, hi + 1, 150)]
    feats, tri, exc, rows = [], {}, {}, []
    with ProcessPoolExecutor(workers) as ex:
        for res in ex.map(text_worker, ranges):
            for feat, t, e, ez, u, c in res:
                feats.append(feat); tri[feat['key']] = t; exc[feat['key']] = (e, ez); rows.append((feat['key'], u, c))
    keys = [r[0] for r in rows]
    np.savez(C.LOCAL / 'trigrams.npz', keys=np.array(keys), off=np.concatenate([[0], np.cumsum([len(tri[k]) for k in keys])]),
             tri=np.concatenate([tri[k] for k in keys]) if keys else np.zeros(0, np.uint32))
    with open(C.LOCAL / 'excerpts.pkl', 'wb') as f:
        pickle.dump(exc, f, protocol=4)
    indptr = np.concatenate([[0], np.cumsum([len(r[1]) for r in rows])])
    ind = np.concatenate([r[1] for r in rows]) if rows else np.zeros(0, np.int32)
    tf = np.concatenate([1.0 + np.log(r[2]) for r in rows]).astype(np.float32) if rows else np.zeros(0, np.float32)
    T = sparse.csr_matrix((tf, ind, indptr), shape=(len(rows), 1 << HASH_BITS))
    df = np.bincount(ind, minlength=1 << HASH_BITS)
    idf = (np.log((1 + len(rows)) / (1 + df)) + 1).astype(np.float32)
    idf[df < 3] = 0
    T = T @ sparse.diags(idf)
    T = sparse.csr_matrix(T)
    nrm = np.sqrt(np.asarray(T.multiply(T).sum(1)).ravel()); nrm[nrm == 0] = 1
    T = sparse.diags(1 / nrm) @ T
    T = sparse.csr_matrix(T, dtype=np.float32); T.eliminate_zeros()
    sparse.save_npz(C.LOCAL / 'tfidf.npz', T)
    np.save(C.LOCAL / 'tfidf_keys.npy', np.array(keys))
    C.log(text_features=len(feats), tfidf_nnz=int(T.nnz))
    return pd.DataFrame(feats)


def n1(papers, keys, X):
    bg = C.load_background()
    if bg is None:
        C.log(n1='background not embedded yet; N1 left empty'); return {}
    ids, years, B = bg
    B = C.normalize(B)
    year = {p['key']: p['year'] for p in papers}
    U = C.normalize(X); out = {}
    by = {}
    for i, k in enumerate(keys):
        if k in year:
            by.setdefault(year[k], []).append(i)
    for y, rows in by.items():
        sel = years == y - 1
        if sel.sum() < 1000:
            continue
        S = U[rows] @ B[sel].T
        S[S > 0.97] = -1
        for i, s in zip(rows, S.max(1)):
            out[keys[i]] = float(1 - s)
    C.log(n1_papers=len(out))
    return out


def s8():
    means = C.load_fulltext_means()
    if not means:
        return {}
    tot = sum(n for n, _, _ in means.values())
    mu = sum(n * m.astype(np.float64) for n, _, m in means.values()) / tot
    out = {}
    for k, P in C.iter_fulltext_segments():
        out[k] = M.within_paper_spread(C.normalize(P - mu))
    C.log(s8_papers=int(sum(np.isfinite(v) for v in out.values())))
    return out


def topics(keys, X, k, seed):
    U, _ = C.center_normalize(X)
    km = KMeans(k, n_init=3, random_state=seed).fit(U)
    return dict(zip(keys, km.labels_.astype(int))), km.cluster_centers_


def main(workers):
    t0 = time.time()
    C.LOCAL.mkdir(parents=True, exist_ok=True)
    papers, _ = C.load_papers()
    df = pd.DataFrame([dict(key=p['key'], school=p['school'], year=p['year'], llm=p['llm']) for p in papers])
    akeys, AX = C.load_abstract_embeddings()
    inpapers = set(df.key)
    sel = [i for i, k in enumerate(akeys) if k in inpapers]
    akeys, AX = [akeys[i] for i in sel], AX[sel]
    df['has_abs'] = df.key.isin(set(akeys))
    t50, c50 = topics(akeys, AX, 50, C.SEED)
    t10, c10 = topics(akeys, AX, 10, C.SEED)
    df['topic50_abs'] = df.key.map(t50); df['topic10_abs'] = df.key.map(t10)
    nn = n1(papers, akeys, AX)
    df['N1'] = df.key.map(nn)
    tf = text_features(workers)
    df = df.merge(tf, on='key', how='left')
    df['has_txt'] = df.words.notna()
    ft = C.load_fulltext_means()
    fkeys = [k for k in ft if k in inpapers and k in set(tf.key)]
    df['has_ft'] = df.key.isin(set(fkeys))
    df['n_seg'] = df.key.map({k: ft[k][0] for k in fkeys}); df['seg_src'] = df.key.map({k: ft[k][1] for k in fkeys})
    tops = dict(c50_abs=c50, c10_abs=c10)
    if len(fkeys) >= 500:
        f50, cf = topics(fkeys, np.vstack([ft[k][2] for k in fkeys]), 50, C.SEED)
        df['topic50_ft'] = df.key.map(f50); tops['c50_ft'] = cf
    else:
        df['topic50_ft'] = np.nan
    np.savez(C.DATA / 'topics.npz', **tops)
    df['S8'] = df.key.map(s8()) if fkeys else np.nan
    refs = C.match_refs(papers)
    df['s2_id'] = df.key.map({k: v[0] for k, v in refs.items()})
    df['n_refs'] = df.key.map({k: len(v[1]) if v[1] else 0 for k, v in refs.items()}).fillna(0).astype(int)
    df['has_refs'] = df.n_refs >= 5
    tmp = C.DATA / 'tmp_paper_features.parquet'
    df.to_parquet(tmp, index=False); os.replace(tmp, C.DATA / 'paper_features.parquet')
    C.log(papers=len(df), has_abs=int(df.has_abs.sum()), has_txt=int(df.has_txt.sum()), has_ft=int(df.has_ft.sum()),
          has_refs=int(df.has_refs.sum()), n1=int(df.N1.notna().sum()), seconds=round(time.time() - t0))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('-j', type=int, default=32)
    main(ap.parse_args().j)
