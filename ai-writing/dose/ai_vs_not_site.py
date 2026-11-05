"""`ai_vs_not.py assemble`: ai_vs_not.json[.gz] (schema: site-data/v2/README.md, section "ai_vs_not.json") from the per-model tables."""
import gzip
import json

import numpy as np
import pandas as pd

import ai_pages as A
import ai_vs_not as V
import dcommon as D

LABEL = {'vendi': 'Vendi score', 'dispersion': 'dispersion', 'mpd': 'mean pairwise distance', 'extent': 'knowledge extent', 'novelty': 'novelty (k = 3)',
         'entropy_bt': 'topic entropy (BERTopic)', 'entropy_oa': 'topic entropy (OpenAlex topics)'}
DEC = {'vendi': 2, 'dispersion': 4, 'mpd': 4, 'extent': 4, 'novelty': 4, 'entropy_bt': 3, 'entropy_oa': 3}
RELEASED = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan']


def rnd(v, d):
    return None if v is None or not np.isfinite(v) else round(float(v), d)


def series(g, field, metric):
    arr = [None] * len(V.YEARS)
    for r in g.itertuples():
        arr[r.year - 2016] = rnd(getattr(r, field), DEC[metric])
    return arr


def model_block(df):
    out = {}
    for (var, t, sc), g in df.groupby(['variant', 't', 'scope']):
        g0 = g[(g['metric'] == 'vendi') & (g['version'] == 'orig')].sort_values('year')
        n = [None] * len(V.YEARS)
        for r in g0.itertuples():
            n[r.year - 2016] = [int(r.nA), int(r.nN)]
        m = {}
        for met in V.METRICS:
            m[met] = {}
            for ver in ('orig', 'rewritten'):
                if met in V.INVARIANT and ver == 'rewritten':
                    continue
                h = g[(g['metric'] == met) & (g['version'] == ver)].sort_values('year')
                m[met][ver] = dict(gap=series(h, 'gap', met), lo=series(h, 'lo', met), hi=series(h, 'hi', met))
        out.setdefault(var, {}).setdefault(str(t), {})[sc] = dict(n=n, m=m)
    return out


def word(lo, hi, hi_word, lo_word):
    return f'{hi_word} than' if lo > 0 else f'{lo_word} than' if hi < 0 else 'not distinguishable from'


def sentence(metric, c, t=25, year=2025, scope='all'):
    """One generated sentence for a metric from the headline cell (variant cut, t, scope, year)."""
    g = c['m'][metric]['orig']
    i = year - 2016
    n = c['n'][i]
    if g['gap'][i] is None or n is None:
        return f'At >= {t}% flagged there are too few papers in {year} to compare AI-written and non-AI papers on {LABEL[metric]}.'
    d = DEC[metric]
    s = (f"At >= {t}% flagged, AI-written papers are {word(g['lo'][i], g['hi'][i], 'higher', 'lower')} non-AI papers on {LABEL[metric]} in {year} "
         f"({g['gap'][i]:+.{d}f} [{g['lo'][i]:+.{d}f}, {g['hi'][i]:+.{d}f}]; {n[0]:,} AI-written vs {n[1]:,} non-AI papers, equal-size draws)")
    if metric in V.INVARIANT:
        return s + '; the topic assignment is fixed, so wording is held constant by construction.'
    r = c['m'][metric]['rewritten']
    if r['gap'][i] is None:
        return s + '.'
    kept = 'the same direction' if np.sign(r['gap'][i]) == np.sign(g['gap'][i]) and (r['lo'][i] > 0 or r['hi'][i] < 0) else 'no distinguishable gap'
    return s + f"; with wording held constant (all abstracts AI-rewritten) the gap is {r['gap'][i]:+.{d}f} [{r['lo'][i]:+.{d}f}, {r['hi'][i]:+.{d}f}], {kept}."


def lab_block(lab_df, boot=300):
    rng = np.random.default_rng(A.SEED)
    out = {}
    for (t, met, ver), g in lab_df.groupby(['t', 'metric', 'version']):
        for sc in ['all'] + D.SCHOOLS:
            h = g if sc == 'all' else g[g['school'] == sc]
            if len(h) < 5:
                continue
            v = h['gap'].to_numpy()
            bs = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(boot)]
            dd = DEC[met]
            out.setdefault(str(t), {}).setdefault(sc, {}).setdefault(met, {})[ver] = dict(
                gap=rnd(v.mean(), dd), lo=rnd(np.percentile(bs, 2.5), dd), hi=rnd(np.percentile(bs, 97.5), dd), labs=int(len(v)))
    return out


def assemble():
    tabs = {m: pd.read_parquet(V.RES / f'{m}.parquet') for m in A.MODELS if (V.RES / f'{m}.parquet').exists()}
    models = {m: model_block(df) for m, df in tabs.items()}
    head = models[A.HEADLINE]
    sentences = {met: sentence(met, head['cut']['25']['all']) for met in V.METRICS}
    summary = {}
    for m, b in models.items():
        c = b['cut']['25']['all']
        summary[m] = {}
        for met in V.METRICS:
            e = {}
            for ver in ('orig', 'rewritten'):
                if ver in c['m'][met]:
                    x = c['m'][met][ver]
                    e[ver] = dict(gap=x['gap'][-1], lo=x['lo'][-1], hi=x['hi'][-1])
            e['n_2025'] = c['n'][-1]
            summary[m][met] = e
    labs = None
    lp = V.RES / f'labs_{A.HEADLINE}.parquet'
    if lp.exists():
        labs = lab_block(pd.read_parquet(lp))
    cuts = pd.read_parquet(V.RES / f'cuts_{A.HEADLINE}.parquet')
    doc = dict(
        meta=dict(ts=V.TS, years=[2016, A.LAST], pre='2016-2022', post='2023-2025', headline_model=A.HEADLINE, models=list(models), scopes=V.SCOPES,
                  released={s: s in RELEASED for s in D.SCHOOLS}, metrics={k: dict(label=LABEL[k], wording_invariant=k in V.INVARIANT) for k in V.METRICS},
                  topics_not_matched='unlike the topic-matched test (matched_test.json) these groups are NOT matched on topic: AI-written papers sit disproportionately in ML/LLM topics, so a gap can come from topic mix as well as from wording or content; the rewritten series separates wording only',
                  groups='AI-written = full-text papers with dose >= t% of passages flagged (ai_share_cal else ai_share); not AI-written = dose below min(t, 10%) (the detector-noise band; disjoint from the AI group); '
                         'variant "abstract": papers without usable full text by their abstract flag (1 vs 0), independent of t (key "0"); variant "placebo" (headline model, 2016-2021): the rate-matched cut `placebo_cut[t]`',
                  draws=f'equal-size draws of m = min(n_AI, n_not, {V.CAP}) papers, {V.REPS} draws for the gap; interval = cluster bootstrap over labs (first lab), {V.BOOT} resamples x {V.BDRAW} draws; gap = AI minus not',
                  blank='null where the smaller group has fewer than %d papers (n is stored anyway)' % V.MIN_N,
                  versions='orig = original abstract embeddings; rewritten = the same papers with every abstract AI-rewritten (Qwen2.5-7B polish, allai/), same draws; the entropies use fixed original topics so have no rewritten series',
                  layout='models.<model>.<variant>.<t>.<scope> = {n: [[n_ai, n_not] per year 2016..2025], m: {metric: {version: {gap[10], lo[10], hi[10]}}}}',
                  labs='labs.<t>.<scope>.<metric>.<version> = {gap, lo, hi, labs}: mean over labs of the within-lab equal-size gap (>= %d papers in each group, 2023-2025, m <= %d), headline model; interval = bootstrap over labs' % (V.LAB_MIN, V.LAB_M),
                  placebo_cut={str(r.t): rnd(r.cut, 5) for r in cuts.itertuples()}, novelty='paper-level novelty k = 3 against the papers of the previous 3 years (pool capped at 2,000), computed separately on each version'),
        sentences=dict(note='headline model, cutoff 25%, year 2025, all schools; regenerated from the cells by ai_vs_not_site.sentence()', text=sentences),
        summary_t25_2025=summary, models=models, labs=labs)
    raw = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode()
    big = len(raw) > 2 * 1024 * 1024
    p = A.OUT / ('ai_vs_not.json.gz' if big else 'ai_vs_not.json')
    for old in (A.OUT / 'ai_vs_not.json', A.OUT / 'ai_vs_not.json.gz'):
        old.unlink(missing_ok=True)
    p.write_bytes(gzip.compress(raw, 9, mtime=0) if big else raw)
    D.log(stage='ai_vs_not_assemble', file=p.name, bytes=p.stat().st_size, models=len(models))
