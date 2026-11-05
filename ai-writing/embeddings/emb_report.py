"""Write ai-writing/diversity/reports/EMBEDDINGS-TOPICS-NOVELTY.md from the tables in EMB/results and the containers' indexes.
Whatever tables exist are reported; a model without vectors yet shows as not embedded. Headline numbers carry 95% cluster-bootstrap
intervals (clusters = labs), never counts of significant domains.   usage: emb_report.py
"""
import sqlite3
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import ecommon as C
import measures as M
import store
from models import MODELS, ORDER

TOPIC_MODELS = ['specter2_proximity', 'qwen3_0p6b']


def f(x, d=3):
    return '' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:.{d}f}'


def ci(est, lo, hi, d=3):
    return f'{f(est, d)} [{f(lo, d)}, {f(hi, d)}]'


def table(rows, head):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---' for _ in head) + '|'] + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows])


def coverage():
    uni = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True)
    papers = dict(uni.execute('select home_school, count(*) from papers group by 1').fetchall())
    txt = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True)
    home = dict(uni.execute('select paper_id, home_school from papers'))
    ab, ft = {}, {}
    for (p,) in txt.execute('select paper_id from abstracts'):
        if p in home:
            ab[home[p]] = ab.get(home[p], 0) + 1
    for (p,) in txt.execute('select paper_id from fulltext where usable=1'):
        if p in home:
            ft[home[p]] = ft.get(home[p], 0) + 1
    rows = [[s + ('' if s in C.RELEASED else ' (unreleased)'), papers.get(s, 0), ab.get(s, 0), ft.get(s, 0)] for s in C.SCHOOLS]
    rows.append(['all', sum(papers.values()), sum(ab.values()), sum(ft.values())])
    emb = []
    for m in ORDER:
        for kind in MODELS[m]['kinds']:
            have = {}
            for s in C.SCHOOLS:
                p = store.container_path(m, s, kind)
                if p.exists():
                    have[s] = store.meta(m, s, kind)
            n = sum(v['papers'] for v in have.values())
            rev = next(iter(have.values()))['revision'] if have else ''
            emb.append([m, kind, n, ', '.join(f'{s} {v["papers"]}' for s, v in have.items()) or 'not embedded yet', rev[:24]])
    return rows, emb


def novelty_section(out):
    out.append('## Novelty\n')
    out.append('Distance of each paper to the papers of the previous k years in the same scope (all papers, school, department, lab): `nov_max` = 1 - cosine to the closest '
               'earlier paper; `nov_nn` = 1 - mean cosine of the 5 nearest. `_cap` columns use a size-matched reference pool (at most 2,000 random earlier papers), because an '
               'uncapped pool grows with output and lowers 1 - max cosine by itself. Vectors are centred on the corpus mean and normalized. k = 3 is the headline; k = 1 and 5 '
               'are in `results/novelty_*.parquet`. Intervals: 95% bootstrap over labs.\n')
    files = sorted(C.RESULTS.glob('novelty_trend_*_abstract.parquet')) + sorted(C.RESULTS.glob('novelty_trend_*_fulltext.parquet'))
    if not files:
        out.append('_No novelty tables yet._\n'); return
    tr = pd.concat([pd.read_parquet(p) for p in files])
    ct = pd.concat([pd.read_parquet(p.with_name(p.name.replace('trend', 'contrast'))) for p in files])
    out.append('### Year by year, all papers (k = 3, size-matched nearest-neighbour novelty `nov_nn_cap`)\n')
    sel = tr[(tr.scope == 'all') & (tr.k == 3) & (tr.measure == 'nov_nn_cap')]
    years = sorted(y for y in sel.year.unique() if y <= 2025)
    rows = []
    for (m, kind), g in sel.groupby(['model', 'kind']):
        d = g.set_index('year')
        rows.append([m, kind] + [ci(d.loc[y, 'mean'], d.loc[y, 'lo'], d.loc[y, 'hi']) if y in d.index else '' for y in years])
    out.append(table(rows, ['model', 'text'] + [str(y) for y in years]) + '\n')
    out.append('### Post (2023-2025) minus pre (2017-2022), difference in mean novelty, 95% interval\n')
    for meas, label in (('nov_max_cap', '1 - max cosine, size-matched'), ('nov_nn_cap', '1 - mean of 5 nearest, size-matched'), ('nov_max', '1 - max cosine, full pool')):
        out.append(f'**{label}, k = 3**\n')
        rows = []
        for (m, kind), g in ct[(ct.k == 3) & (ct.measure == meas)].groupby(['model', 'kind']):
            d = g.set_index(['scope', 'scope_id'])
            cells = [ci(d.loc[(s, i), 'diff'], d.loc[(s, i), 'lo'], d.loc[(s, i), 'hi']) if (s, i) in d.index else '' for s, i in
                     [('all', 'all')] + [('school', x) for x in C.SCHOOLS] + [('dept', 'pooled'), ('lab', 'pooled')]]
            rows.append([m, kind] + cells)
        out.append(table(rows, ['model', 'text', 'all'] + C.SCHOOLS + ['departments (pooled)', 'labs (pooled)']) + '\n')
    out.append('Other windows (k = 1, 5) for all papers, `nov_nn_cap`:\n')
    rows = []
    for (m, kind, k), g in ct[(ct.scope == 'all') & (ct.measure == 'nov_nn_cap')].groupby(['model', 'kind', 'k']):
        r = g.iloc[0]
        rows.append([m, kind, int(k), f(r.mean_pre), f(r.mean_post), ci(r['diff'], r.lo, r.hi)])
    out.append(table(rows, ['model', 'text', 'k', 'mean pre', 'mean post', 'post - pre']) + '\n')


def topics_section(out):
    out.append('## Topics\n')
    out.append('BERTopic on the abstract embeddings (UMAP 5 dims, cosine; HDBSCAN min_cluster_size 60; c-TF-IDF labels from title + abstract, unigrams and bigrams, no LLM). '
               'HDBSCAN noise is reassigned to the nearest topic so every paper has one; the share is below. Entropy in bits. Plug-in entropy rises with the number of papers, so the '
               'headline is entropy **rarefied** to the same number of papers (all papers 2,000 per year, a school 500, a department 100, a lab 20 per period). OpenAlex rows use '
               'the primary topic of each paper from the snapshot (4,516 topics; the subfield and field levels are the same papers coarsened).\n')
    any_ = False
    for m in TOPIC_MODELS + ['oa']:
        p = C.RESULTS / f'topic_entropy_{m}.parquet'
        if not p.exists():
            continue
        any_ = True
        e = pd.read_parquet(p)
        lab = pd.read_parquet(C.RESULTS / f'topic_labels_{m}.parquet') if m != 'oa' else None
        name = {'oa': 'OpenAlex primary topics'}.get(m, m)
        out.append(f'### {name}\n')
        if lab is not None:
            tp = pd.read_parquet(C.RESULTS / f'topics_{m}.parquet')
            out.append(f'{len(lab)} topics over {len(tp):,} papers; {float((tp.topic_raw == -1).mean()):.1%} were HDBSCAN noise before reassignment. Largest topics: '
                       + '; '.join(f'{r.label} ({r["size"]:,})' for _, r in lab.sort_values('size', ascending=False).head(8).iterrows()) + '.\n')
        for level, g in e.groupby('level'):
            a = g[(g.scope == 'all') & g.h_rare.notna() & (g.year <= 2025)].sort_values('year') if 'h_rare' in g else pd.DataFrame()
            if a.empty:
                continue
            out.append(f'**All papers, entropy by year ({level}, rarefied to {int(a.rare_m.iloc[0]):,} papers)**\n')
            out.append(table([[int(r.year), int(r.n), int(r.k_present), f(r.h, 2), ci(r.h_rare, r.h_rare_lo, r.h_rare_hi, 2)] for _, r in a.iterrows()],
                             ['year', 'papers', 'topics present', 'plug-in', 'rarefied [95%]']) + '\n')
            s = g[(g.scope == 'school') & g.h_rare.notna()]
            if not s.empty:
                rows = []
                for sid, gg in s.groupby('scope_id'):
                    pre, post = gg[gg.year.between(2016, 2022)], gg[gg.year.between(2023, 2025)]
                    if len(pre) and len(post):
                        rows.append([sid, f(pre.h_rare.mean(), 2), f(post.h_rare.mean(), 2), f(post.h_rare.mean() - pre.h_rare.mean(), 2)])
                out.append(f'**By school, mean yearly rarefied entropy, pre (2016-2022) and post (2023-2025), {level}**\n')
                out.append(table(rows, ['school', 'pre', 'post', 'post - pre']) + '\n')
        lp = pd.read_parquet(C.RESULTS / f'topic_entropy_labperiod_{m}.parquet')
        rows = []
        for level, g in lp.groupby('level'):
            w = g.pivot(index='lab_id', columns='period', values='h_rare').dropna()
            if len(w) >= 10:
                d = (w['post'] - w['pre']).to_numpy()
                est, lo, hi = M.cluster_bootstrap(d, np.arange(len(d)), np.nanmean, reps=2000)
                rows.append([level, len(w), f(w['pre'].mean(), 2), f(w['post'].mean(), 2), ci(est, lo, hi, 2)])
        if rows:
            out.append('**Labs with >= 20 papers in both periods: entropy rarefied to 20 papers, mean over labs, post minus pre [95%, bootstrap over labs]**\n')
            out.append(table(rows, ['level', 'labs', 'pre', 'post', 'change']) + '\n')
    if not any_:
        out.append('_No topic tables yet._\n')


def main():
    out = ['# Embeddings, topics and novelty for every paper\n',
           f'Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `ai-writing/embeddings/emb_report.py`. Code, layout and models: `ai-writing/embeddings/README.md`. '
           'Tables: `ai-writing/data/embeddings/results/*.parquet` (slot `EMBEDDINGS`).\n']
    out.append('## Method\n')
    out.append('- **Papers.** Every lab paper of the seven released schools plus Georgia Tech and UChicago (their packages exist, both unreleased), one row per work (atlas id), '
               'years 2016-2025 in the analyses (2026 is a partial year and stays out of every series and estimate). A paper of several labs counts in each of its labs, departments and schools; its vectors are stored once under its home school.\n'
               '- **Abstracts.** The OpenAlex abstract (rebuilt from `abstract_inverted_index` in the 2026-10-14 bulk snapshot, one more S3 pass: the local filtered snapshot kept no abstracts or topics), '
               'else the cached API abstract; at least 10 words. **Full text.** Every local copy: the existing body-text extraction, usable texts only (>= 1000 words, a PDF must show the title).\n'
               '- **Models.** One vector set each, model id and revision recorded in every container (`index.sqlite` meta): ' + ', '.join(f'`{MODELS[m]["hf"]}`' + (' + proximity adapter' if m == 'specter2_proximity' else '') for m in ORDER) + '. '
               'Qwen3-Embedding-4B needs about 8 GB in fp16, the whole of an RTX 2080: not run. fp16, no flash-attention, windows of 512 (SPECTER2) or 8,192 tokens, chunk vectors kept with their mean.\n')
    rows, emb = coverage()
    out.append('## Coverage\n')
    out.append('Papers per school (home school; a paper of two schools is counted once), with an abstract, and with a usable full text:\n')
    out.append(table(rows, ['school', 'papers', 'abstract', 'usable full text']) + '\n')
    out.append('Embedded papers per model and text kind:\n')
    out.append(table(emb, ['model', 'text', 'papers', 'by school', 'revision']) + '\n')
    topics_section(out)
    novelty_section(out)
    out.append('## Reading the results (as of 2026-11-04)\n')
    out.append('- Novelty: the direction of the post-2023 change depends on the embedding model, so there is no model-agnostic trend. The SPECTER2 family (trained on citation structure) shows '
               'lower novelty after 2022 on abstracts (size-matched 1 - mean-of-5-nearest, k = 3, all papers: SPECTER2 base about -0.02, proximity about -0.01); BGE-M3, Nomic and SciNCL show a '
               'small rise (about +0.004 to +0.006); gte-Qwen2 and Qwen3 are near zero. EPFL rises under every model; UChicago falls under every model (its 2016-2018 pool is small). '
               'Full-text vectors move less than abstract vectors. The size-matched and full-pool columns differ because a growing pool lowers 1 - max cosine by itself.\n'
               '- Topics: entropy over BERTopic topics is flat from 2016 to 2023 and lower in 2025; per school the post-pre change has opposite signs (CMU and Stanford down, '
               'EPFL and Princeton up). Labs with >= 20 papers in both periods are slightly more spread over topics after 2022 (interval in the lab table). Topics are model-dependent (309 and 379 topics; '
               '37-39% of papers are HDBSCAN noise before reassignment), so compare the two models and the OpenAlex rows rather than trust one.\n'
               '- Full-text vectors of the 8k-token models (Qwen3, GTE-Qwen2, BGE-M3, Nomic) are produced by queued resumable jobs; the coverage table shows what has been merged so far.\n')
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    (C.REPORTS / 'EMBEDDINGS-TOPICS-NOVELTY.md').write_text('\n'.join(out) + '\n')
    C.log(report=str(C.REPORTS / 'EMBEDDINGS-TOPICS-NOVELTY.md'), lines=len(out))


if __name__ == '__main__':
    main()
