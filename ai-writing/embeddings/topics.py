"""BERTopic on the abstract embeddings, with readable topic labels, and the topic distributions and their entropy per lab, department, school
and year (also for OpenAlex's own primary topics).

  topics.py bertopic --model specter2_proximity|qwen3_0p6b      fit -> results/topics_<model>.parquet (paper -> topic), topic_labels_<model>.parquet
  topics.py entropy --model M | --model openalex                 distributions and entropy tables from the topic assignments

BERTopic gets the precomputed embeddings (centred and normalized): UMAP (5 dims, cosine, seed) -> HDBSCAN (min_cluster_size) -> c-TF-IDF on title +
abstract (English stop words, unigrams and bigrams, min_df 20). Labels are the top-4 c-TF-IDF keywords, no LLM. Outliers (HDBSCAN noise) are
reassigned to the nearest topic by embedding so that every paper has a topic; `topic_raw` keeps the unreassigned value and the share is reported.
Entropy (bits): plug-in, Miller-Madow corrected, and rarefied (equal numbers of papers compared at the same m) -- a lab with 80 papers would otherwise
look more diverse than one with 20. Labs are described per period (2016-2022 / 2023-2025) since lab-years are too small; school, department and
all-paper entropies are per year.
"""
import argparse
import sqlite3
import sys

import numpy as np
import pandas as pd

import ecommon as C
import emb_load as L
import measures as M
import novelty as N

MIN_CLUSTER = {'specter2_proximity': 60, 'qwen3_0p6b': 60}
RARE_M = {'all': 2000, 'school': 500, 'dept': 100}
LAB_M = 20
OA_LEVELS = ('oa_topic', 'oa_subfield', 'oa_field')


def fit(model):
    C.use_extras()
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP
    papers, _ = L.universe()
    ids, X, meta = L.vectors(model, 'abstract')
    db = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True)
    text = {i: (t or '') + '. ' + a for i, t, a in db.execute('select paper_id, title, abstract from abstracts')}
    keep = [j for j, i in enumerate(ids) if i in set(papers['paper_id']) and i in text]
    ids = [ids[j] for j in keep]
    Z, _ = N.center_normalize(X[keep])
    docs = [text[i] for i in ids]
    C.log(model=model, papers=len(ids))
    tm = BERTopic(embedding_model=None, calculate_probabilities=False, verbose=True, top_n_words=10,
                  umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine', random_state=C.SEED),
                  hdbscan_model=HDBSCAN(min_cluster_size=MIN_CLUSTER[model], min_samples=10, metric='euclidean', cluster_selection_method='eom', prediction_data=True),
                  vectorizer_model=CountVectorizer(stop_words='english', ngram_range=(1, 2), min_df=20, max_df=0.5))
    raw, _ = tm.fit_transform(docs, embeddings=Z)
    raw = np.asarray(raw)
    final = np.asarray(tm.reduce_outliers(docs, raw, strategy='embeddings', embeddings=Z))
    tm.update_topics(docs, topics=final, vectorizer_model=CountVectorizer(stop_words='english', ngram_range=(1, 2), min_df=20, max_df=0.5))
    C.RESULTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(dict(paper_id=ids, topic_raw=raw, topic=final)).to_parquet(C.RESULTS / f'topics_{model}.parquet', index=False)
    info = tm.get_topic_info()
    lab = [dict(topic=int(t), size=int((final == t).sum()), size_raw=int((raw == t).sum()),
                label=', '.join(w for w, _ in (tm.get_topic(t) or [])[:4]), keywords=', '.join(w for w, _ in (tm.get_topic(t) or [])[:10]))
           for t in info['Topic'] if t != -1]
    pd.DataFrame(lab).to_parquet(C.RESULTS / f'topic_labels_{model}.parquet', index=False)
    C.log(model=model, topics=len(lab), outlier_share_before_reassignment=float((raw == -1).mean()), revision=(meta or {}).get('revision'))


def entropy_rows(df, col, cluster_col='cluster', reps=60):
    """Rows (scope, scope_id, year, level=col, n, k_present, h, h_mm, h_rare, lo, hi) per (scope, scope_id, year) for school/dept/all, from a
    frame with scope, scope_id, year, `col` (the topic label), `cluster` (home lab, the bootstrap unit)."""
    out = []
    for (scope, sid, year), g in df.groupby(['scope', 'scope_id', 'year']):
        lab = g[col].dropna()
        if lab.empty:
            continue
        counts = lab.value_counts().to_numpy()
        row = dict(scope=scope, scope_id=sid, year=int(year), level=col, n=int(len(lab)), k_present=int(len(counts)), h=M.shannon(counts), h_mm=M.miller_madow(counts))
        m = RARE_M.get(scope)
        if m and len(lab) >= m:
            est, lo, hi = M.entropy_bootstrap(lab.to_numpy(), g.loc[lab.index, cluster_col].to_numpy(), m, reps=reps)
            row.update(h_rare=est, h_rare_lo=lo, h_rare_hi=hi, rare_m=m)
        out.append(row)
    return out


def lab_period_rows(df, col):
    """Per lab and period (pre 2016-2022, post 2023-2025): n, Miller-Madow entropy, entropy rarefied to LAB_M papers (NaN below it)."""
    out = []
    d = df[df['scope'] == 'lab'].dropna(subset=[col])
    for (sid, per), g in d.assign(period=np.where(d['year'] >= 2023, 'post', 'pre')).groupby(['scope_id', 'period']):
        counts = g[col].value_counts().to_numpy()
        out.append(dict(lab_id=sid, period=per, level=col, n=int(len(g)), k_present=int(len(counts)), h_mm=M.miller_madow(counts), h_rare=M.rarefied(counts, LAB_M, reps=50)))
    return out


def entropy(model):
    papers, lp = L.universe()
    mem = L.memberships(lp)
    allp = papers[['paper_id']].assign(scope='all', scope_id='all')[['scope', 'scope_id', 'paper_id']]
    mem = pd.concat([mem, allp], ignore_index=True)
    first_lab = lp.sort_values('lab_id').drop_duplicates('paper_id').set_index('paper_id')['lab_id']
    base = papers[['paper_id', 'year', 'oa']].copy()
    if model == 'openalex':
        base = L.oa_topics(papers)[['paper_id', 'year', 'oa_topic', 'oa_subfield', 'oa_field']]
        cols = list(OA_LEVELS)
    else:
        t = pd.read_parquet(C.RESULTS / f'topics_{model}.parquet')[['paper_id', 'topic']].rename(columns={'topic': 'topic_id'})
        base = base.merge(t, on='paper_id', how='inner')
        lab = pd.read_parquet(C.RESULTS / f'topic_labels_{model}.parquet').set_index('topic')['label']
        base['topic_label'] = base['topic_id'].map(lambda x: f'{x}: {lab.get(x, "")}')
        cols = ['topic_label']
    df = mem.merge(base, on='paper_id', how='inner')
    df['cluster'] = df['paper_id'].map(first_lab).fillna('none')
    rows, labrows = [], []
    for col in cols:
        rows += entropy_rows(df[df['scope'] != 'lab'], col)
        labrows += lab_period_rows(df, col)
        # lab-year distributions are kept too (counts only; entropy of 5-30 papers is reported with its n)
        lyr = df[df['scope'] == 'lab'].dropna(subset=[col])
        for (sid, year), g in lyr.groupby(['scope_id', 'year']):
            counts = g[col].value_counts().to_numpy()
            rows.append(dict(scope='lab', scope_id=sid, year=int(year), level=col, n=int(len(g)), k_present=int(len(counts)), h=M.shannon(counts), h_mm=M.miller_madow(counts)))
    tag = 'oa' if model == 'openalex' else model
    pd.DataFrame(rows).to_parquet(C.RESULTS / f'topic_entropy_{tag}.parquet', index=False)
    pd.DataFrame(labrows).to_parquet(C.RESULTS / f'topic_entropy_labperiod_{tag}.parquet', index=False)
    # topic distributions (counts) per scope and year, for the plots and for readers who want the distributions themselves
    keep = df[df['scope'].isin(['school', 'all'])]
    dist = pd.concat([keep.groupby(['scope', 'scope_id', 'year', c]).size().rename('papers').reset_index().rename(columns={c: 'topic'}).assign(level=c) for c in cols])
    dist.to_parquet(C.RESULTS / f'topic_distribution_{tag}.parquet', index=False)
    C.log(entropy=tag, rows=len(rows), lab_period_rows=len(labrows), distribution_rows=len(dist))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['bertopic', 'entropy'])
    ap.add_argument('--model', required=True)
    a = ap.parse_args()
    fit(a.model) if a.cmd == 'bertopic' else entropy(a.model)
    sys.stdout.flush()
