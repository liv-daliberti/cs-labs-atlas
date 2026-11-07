"""`ai_pages.py assemble`: the site JSON (diversity/site-data/v2/) from the stage tables. Schemas: site-data/v2/README.md."""
import glob
import gzip
import json

import numpy as np
import pandas as pd

import ai_pages as A
import dcommon as D

GRID = 4096          # map coordinates are integers 0..4095 over the shared range
DENS = 64            # density grid cells per side
FIELD_MIN = 50
RELEASED = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan']


def r(v, k=4):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), k)


def dump(obj, name, gz=False):
    A.OUT.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, dict) and isinstance(obj.get('meta'), dict) and A.detector_note():
        obj['meta']['detector'] = A.detector_note()
    raw = json.dumps(obj, separators=(',', ':'), allow_nan=False).encode()
    p = A.OUT / (name + ('.gz' if gz else ''))
    if gz:
        with open(p, 'wb') as f:
            f.write(gzip.compress(raw, 9, mtime=0))
    else:
        p.write_bytes(raw)
    return p.stat().st_size


def load():
    fr = pd.read_parquet(A.RES / 'frame.parquet')
    return fr[fr['year'].between(2016, A.LAST)]


# ------------------------------------------------------------------ 1. the paper map

def reader_keys():
    root = D.P.RELEASES / 'latest' / 'reader'
    keys = set()
    for f in glob.glob(str(root / '*.jsonl.gz')):
        for line in gzip.open(f, 'rt'):
            q = json.loads(line)
            if q.get('atlas_work_id'):
                keys.add(q['atlas_work_id'])
    return keys


def build_map(fr):
    um = pd.read_parquet(A.RES / 'umap.parquet')
    d = fr.merge(um, on='paper_id')
    d = d.reset_index(drop=True)
    labs = pd.read_parquet(A.RES / 'labs.parquet').set_index('lab_id')
    lo_x, hi_x, lo_y, hi_y = float(d['ux'].min()), float(d['ux'].max()), float(d['uy'].min()), float(d['uy'].max())
    q = lambda v, lo, hi, n=GRID: np.clip(np.floor((v - lo) / (hi - lo) * n), 0, n - 1).astype(int)   # noqa: E731
    d['qx'], d['qy'] = q(d['ux'], lo_x, hi_x), q(d['uy'], lo_y, hi_y)
    used_labs = sorted(d['lab0'].dropna().unique())
    lab_idx = {l: i for i, l in enumerate(used_labs)}
    topics = pd.read_parquet(A.RES / 'topics.parquet').set_index('topic')
    used_topics = sorted(int(t) for t in d['topic'].dropna().unique())
    topic_idx = {t: i for i, t in enumerate(used_topics)}
    fields = sorted(d['oa_field'].dropna().unique())
    field_idx = {f: i for i, f in enumerate(fields)}
    readable = reader_keys()
    sizes = {}
    shards = {}
    for s in D.SCHOOLS:
        g = d[d['school'] == s].sort_values(['year', 'paper_id'])
        if g.empty:
            continue
        shard = dict(school=s, n=len(g), ids=g['paper_id'].tolist(), x=g['qx'].tolist(), y=g['qy'].tolist(), year=(g['year'] - 2016).tolist(),
                     lab=g['lab0'].map(lab_idx).astype(int).tolist(), topic=g['topic'].map(lambda t: topic_idx.get(int(t), -1) if pd.notna(t) else -1).astype(int).tolist(),
                     field=g['oa_field'].map(lambda f: field_idx.get(f, -1) if isinstance(f, str) else -1).astype(int).tolist(),
                     ai=[-1 if not np.isfinite(v) else int(round(100 * v)) for v in g['x']],
                     abf=[-1 if not np.isfinite(v) else int(v) for v in g['flag_abstract']])
        sizes[f'map_{s}.json.gz'] = dump(shard, f'map_{s}.json', gz=True)
        sizes[f'map_titles_{s}.json.gz'] = dump(dict(school=s, n=len(g), titles=[(t or '')[:200] for t in g['title']]), f'map_titles_{s}.json', gz=True)
        shards[s] = len(g)
    # density grid: counts per cell of a 64 x 64 grid, per year, all papers and AI papers (dose >= 25%)
    d['cx'], d['cy'] = q(d['ux'], lo_x, hi_x, DENS), q(d['uy'], lo_y, hi_y, DENS)
    d['cell'] = d['cy'] * DENS + d['cx']

    def sparse(g):
        c = g['cell'].value_counts().sort_index()
        return [[int(i), int(v)] for i, v in c.items()]
    dens = dict(grid=DENS, range=dict(x=[lo_x, hi_x], y=[lo_y, hi_y]), cell='row-major: index = row * 64 + col, col from x, row from y (both increasing)',
                years={str(y): dict(n=sparse(g), ai=sparse(g[g['ai25'] == 1])) for y, g in d.groupby('year')},
                pre=dict(years='2016-2022', n=sparse(d[d['year'] <= 2022]), ai=sparse(d[(d['year'] <= 2022) & (d['ai25'] == 1)])),
                post=dict(years='2023-2025', n=sparse(d[d['year'] >= 2023]), ai=sparse(d[(d['year'] >= 2023) & (d['ai25'] == 1)])))
    sizes['map_density.json'] = dump(dens, 'map_density.json')
    ti = [dict(id=int(t), label=str(topics.loc[t, 'label']), kind=str(topics.loc[t, 'kind']), n=int(topics.loc[t, 'size'])) for t in used_topics]
    index = dict(
        meta=dict(model=A.HEADLINE, projection='PCA(50) of the centred, length-normalised abstract vectors, then UMAP(n_neighbors=15, min_dist=0.1, euclidean, random_state=%d), fitted once on all papers' % A.SEED,
                  years=[2016, A.LAST], papers=len(d), grid=GRID, coord_range=dict(x=[lo_x, hi_x], y=[lo_y, hi_y]), shards=shards,
                  dequantize='x_umap = x_min + (x + 0.5) / 4096 * (x_max - x_min), likewise y',
                  id='paper id = atlas work id (atl:w:...) for the seven released schools, the key of the release reader rows (lookup_keys); gatech and uchicago papers keep their OpenAlex key (oa:W...) and have no reader row',
                  id_in_release_reader=int(d['paper_id'].isin(readable).sum()), ai='percent of passages flagged (dose, the dose pages ai_share_cal else ai_share), -1 = no usable full text',
                  abf='1/0 = the abstract detector flags the abstract, -1 = no abstract score', lab='index into labs (the paper\'s first lab)',
                  topic='index into topics (BERTopic on the proximity vectors, outliers reassigned to the nearest topic), -1 = none', field='index into fields (OpenAlex primary field), -1 = none',
                  sizes=sizes),
        schools=D.SCHOOLS, released={s: s in RELEASED for s in D.SCHOOLS}, fields=fields, topics=ti,
        labs=[dict(id=l, released=bool(labs.loc[l, 'school'] in RELEASED), site=(labs.loc[l, 'site_lab'] if isinstance(labs.loc[l, 'site_lab'], str) else None), pi=labs.loc[l, 'pi'], name=labs.loc[l, 'lab_name'], school=labs.loc[l, 'school']) for l in used_labs])
    sizes['map_index.json'] = dump(index, 'map_index.json')
    index['meta']['sizes'] = sizes
    dump(index, 'map_index.json')
    return dict(papers=len(d), bytes=sum(sizes.values()), sizes=sizes)


# ------------------------------------------------------------------ 2. lab scatter

def build_lab_scatter():
    lm = pd.read_parquet(A.RES / 'lab_measures.parquet')
    ex = pd.read_parquet(A.RES / 'lab_exposure.parquet')
    labs_all = pd.read_parquet(A.RES / 'labs.parquet')
    labs = labs_all.set_index('lab_id')
    base_t = ex.merge(labs_all[['lab_id', 'school']], on='lab_id').merge(lm.drop_duplicates('lab_id')[['lab_id', 'n_pre', 'n_post']], on='lab_id')
    sl = pd.DataFrame(A.slopes_from(lm, base_t, 500))
    ids = sorted(lm['lab_id'].unique())
    base = lm[lm['model'] == A.HEADLINE].drop_duplicates('lab_id').set_index('lab_id')
    exi = ex.set_index('lab_id')
    values = {}
    for (lab, measure, model), g in lm.groupby(['lab_id', 'measure', 'model']):
        v = g.iloc[0]
        values.setdefault(lab, {}).setdefault(measure, {})[model] = [r(v['pre']), r(v['post']), r(v['change'])]
    rows = []
    for lab in ids:
        e = exi.loc[lab] if lab in exi.index else None
        rows.append(dict(lab_id=lab, released=bool(labs.loc[lab, 'school'] in RELEASED), site_lab=(labs.loc[lab, 'site_lab'] if isinstance(labs.loc[lab, 'site_lab'], str) else None), pi=labs.loc[lab, 'pi'], lab=labs.loc[lab, 'lab_name'],
                         school=labs.loc[lab, 'school'], n_pre=int(base.loc[lab, 'n_pre']) if lab in base.index else None, n_post=int(base.loc[lab, 'n_post']) if lab in base.index else None,
                         m=int(base.loc[lab, 'm']) if lab in base.index else None, n_scored_post=int(e['n_scored_post']) if e is not None else 0,
                         dose=r(e['dose']) if e is not None else None, share25=r(e['share25']) if e is not None else None,
                         abs_flag_share=r(e['abs_flag_share']) if e is not None else None, values=values[lab]))
    slopes = [dict(measure=x.measure, model=x.model, beta=r(x.beta), lo=r(x.lo), hi=r(x.hi), labs=int(x.labs), line_a=r(x.line_a, 5), line_b_per_pct=r(x.line_b_per_pct, 6)) for x in sl.itertuples()]
    out = dict(meta=dict(measures={m: A.MEASURE_LABEL[m] for m in A.MEASURES}, models=A.MODELS, headline_model=A.HEADLINE, pre='2016-2022', post='2023-2025',
                         labs_rule='at least 5 papers with an abstract vector before (2016-2022) and after (2023-2025)',
                         draws='per lab and model: 100 random draws of m = min(papers pre, papers post, 80) papers per period; the value is the mean over draws, so size never makes a lab look more diverse',
                         values='values[measure][model] = [pre, post, change = post - pre]',
                         dose='the lab\'s mean dose (percent of passages flagged / 100) over its 2023-2025 full-text papers; null when fewer than 5 are scored (n_scored_post)',
                         share25='share of those scored 2023-2025 papers with dose >= 25%',
                         slope='beta: standardized Huber slope of the change on the dose (both z-scored) with log n pre, log n post and school dummies; interval = 95% percentile bootstrap over labs (500); line_a + line_b_per_pct * (dose in %) = the raw-unit Huber line of change on dose, no controls',
                         partition='topic entropy, effective topics and new topics use BERTopic topics for specter2_proximity and qwen3_0p6b and 100 k-means clusters of the model\'s own vectors for the other five',
                         dist_field='mean paper-level novelty against all earlier papers (k = 3, the embedding novelty of EMBEDDINGS-TOPICS-NOVELTY.md)',
                         new_topics='share of the draw\'s papers whose topic is absent from the lab\'s papers of the three previous years (window of at least 5 papers)'),
               labs=rows, slopes=slopes)
    return dict(labs=len(rows), bytes=dump(out, 'lab_scatter.json', gz=True))


# ------------------------------------------------------------------ 3. where AI is used

def wilson(k, n, z=1.96):
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return float(c - h), float(c + h)


def series_by(fr, col, keys):
    out = {}
    sc = fr[fr['x'].notna()]
    for key in keys:
        g = sc[sc[col] == key]
        n, a, m = [], [], []
        for y in A.YEARS:
            h = g[g['year'] == y]
            n.append(int(len(h)))
            a.append(int(h['ai25'].sum()))
            m.append(r(h['x'].mean(), 4) if len(h) >= 5 else None)
        out[key] = dict(n=n, a=a, mean=m, share=[r(a_ / n_, 4) if n_ >= 5 else None for a_, n_ in zip(a, n)])
    return out


def kind_series(fr, B=300):
    sc = fr[fr['x'].notna()].copy()      # 'all' is every scored paper; the kinds need a topic
    rng = np.random.default_rng(A.SEED)
    labs = pd.factorize(sc['lab0'])[0]
    nl = labs.max() + 1
    ws = [rng.multinomial(nl, np.full(nl, 1.0 / nl)) for _ in range(B)]
    out = {}
    for name, sel in (('llm', sc['kind'] == 'llm'), ('ml', sc['kind'] == 'ml'), ('other', sc['kind'] == 'other'), ('non_llm', sc['kind'].notna() & (sc['kind'] != 'llm')), ('all', sc['x'].notna())):
        g, lg = sc[sel], labs[sel.to_numpy()]
        rec = dict(n=[], a=[], share=[], lo=[], hi=[], mean=[])
        for y in A.YEARS:
            h = g['year'].to_numpy() == y
            n, a = int(h.sum()), int(g.loc[h, 'ai25'].sum())
            rec['n'].append(n)
            rec['a'].append(a)
            rec['share'].append(r(a / n, 4) if n else None)
            rec['mean'].append(r(g.loc[h, 'x'].mean(), 4) if n else None)
            if n >= 20:
                num, den = np.bincount(lg[h], g.loc[h, 'ai25'].to_numpy(), nl), np.bincount(lg[h], minlength=nl).astype(float)
                bs = np.array([(w @ num) / max(w @ den, 1) for w in ws])
                rec['lo'].append(r(np.percentile(bs, 2.5), 4))
                rec['hi'].append(r(np.percentile(bs, 97.5), 4))
            else:
                rec['lo'].append(None)
                rec['hi'].append(None)
        out[name] = rec
    return out


def build_ai_use(fr):
    tp = pd.read_parquet(A.RES / 'topics.parquet')
    fr = fr.copy()
    sc = fr[fr['x'].notna()]
    tcount = fr['topic'].value_counts()
    keep = [int(t) for t in tp.loc[tp['size'] >= 50, 'topic']]
    ts = series_by(fr.assign(topic=fr['topic']), 'topic', keep)
    topics = []
    for t in keep:
        row = tp[tp['topic'] == t].iloc[0]
        s = ts[t]
        topics.append(dict(id=t, label=row['label'], keywords=row['keywords'], kind=row['kind'], n_papers=int(tcount.get(t, 0)), n=s['n'], a=s['a'], share=s['share'], mean=s['mean']))
    fcount = fr['oa_field'].value_counts()
    fkeep = [f for f in fcount.index if fcount[f] >= FIELD_MIN]
    fs = series_by(fr, 'oa_field', fkeep)
    fields = [dict(field=f, n_papers=int(fcount[f]), n=fs[f]['n'], a=fs[f]['a'], share=fs[f]['share'], mean=fs[f]['mean']) for f in fkeep]
    top = []
    for t in topics:
        i25, i22 = A.YEARS.index(2025), A.YEARS.index(2022)
        if t['n'][i25] >= 30 and t['n'][i22] >= 30:
            top.append(dict(id=t['id'], label=t['label'], kind=t['kind'], n_2025=t['n'][i25], share_2025=t['share'][i25], n_2022=t['n'][i22], share_2022=t['share'][i22],
                            change=r(t['share'][i25] - t['share'][i22], 4)))
    top_share = sorted(top, key=lambda z: -z['share_2025'])[:30]
    top_change = sorted(top, key=lambda z: -z['change'])[:30]
    ks = kind_series(fr)
    kinds = tp['kind'].value_counts().to_dict()
    # fraction of 2025 AI papers that sit in LLM topics
    s25 = sc[(sc['year'] == 2025) & sc['topic'].notna()]
    llm_share_of_ai = float(s25.loc[s25['ai25'] == 1, 'kind'].eq('llm').mean())
    llm_share_of_all = float(s25['kind'].eq('llm').mean())
    out = dict(meta=dict(years=[2016, A.LAST], threshold=A.THR, share='share of scored (full-text) papers with dose >= 25%; null where n < 5', mean='mean dose', n='scored papers',
                         a='scored papers with dose >= 25%', topics_rule='BERTopic topics of the proximity vectors with at least 50 papers (all of the 309)', fields_rule='OpenAlex primary field with at least %d papers' % FIELD_MIN,
                         kind_rule='topic kind from the topic label (top 4 keywords) and its 10 keywords: llm when the label or at least 2 keywords match language-model terms (llm, language model, GPT, in-context, prompt, instruction, RLHF, pretraining, reasoning model, tokens, transformers, agents, VLM, multimodal, diffusion models ...); '
                                   'ml when the label or at least 3 keywords match machine-learning terms (learning, neural, gradient, reinforcement, adversarial, GNN, causal, vision, speech ...) and it is not llm; other otherwise. Regexes: ai_pages.py LLM_RE and ML_RE',
                         kinds_topics=kinds, kind_series='share by year per kind with a 95% bootstrap interval over labs (300 draws); non_llm = ml + other; only papers with a topic; all = every scored paper',
                         top_rule='topics with at least 30 scored papers in both 2022 and 2025; change = share 2025 - share 2022', llm_share_of_2025_ai_papers=r(llm_share_of_ai), llm_share_of_2025_papers=r(llm_share_of_all)),
               topics=topics, fields=fields, kind_series=ks, top_by_2025_share=top_share, top_by_change=top_change)
    return dict(topics=len(topics), fields=len(fields), bytes=dump(out, 'ai_use.json', gz=True), llm_share_of_ai=llm_share_of_ai, llm_share_of_all=llm_share_of_all)


# ------------------------------------------------------------------ 4. matched test and event study

def build_matched():
    m = pd.read_parquet(A.RES / 'matched.parquet')
    rows = []
    for x in m.itertuples():
        rows.append(dict(population=x.population, model=x.model, measure=x.measure, effect=r(x.effect, 5), lo=r(x.lo, 5), hi=r(x.hi, 5),
                         raw=r(getattr(x, 'raw', np.nan), 5), n_ai=None if pd.isna(getattr(x, 'n_ai', np.nan)) else int(x.n_ai), n_non=None if pd.isna(getattr(x, 'n_non', np.nan)) else int(x.n_non),
                         n_ai_matched=None if pd.isna(getattr(x, 'n_ai_matched', np.nan)) else int(x.n_ai_matched), cells=None if pd.isna(getattr(x, 'cells', np.nan)) else int(x.cells),
                         matched_cells=None if pd.isna(getattr(x, 'matched_cells', np.nan)) else int(x.matched_cells), sd=r(getattr(x, 'sd', np.nan), 5)))
    pops = {p: dict(description=g['description'].iloc[0], years=g['years'].iloc[0], papers=int(g['papers'].iloc[0]), ai_papers=int(g['ai_papers'].iloc[0]), threshold=r(g['threshold'].iloc[0], 5))
            for p, g in m.groupby('population')}
    out = dict(meta=dict(set_size=150, design='cells = BERTopic topic x year x school; within a cell with both AI and non-AI papers the difference of mean outcomes, cells weighted by their AI papers (coarsened exact matching / cell-weighted means: the effect on the AI papers); papers with a full-text dose only',
                         novelty='paper-level novelty = 1 - mean cosine to the 5 nearest papers of the previous 3 years (k = 3, all papers, pool capped at 2,000), per model; effect = AI minus non-AI, negative = AI papers less novel',
                         size_matched='dispersion and Vendi of sets of 150 AI and 150 non-AI papers drawn with the same (topic, year, school) composition; effect = AI minus non-AI, mean of 200 draws; interval = 100 lab resamples x 10 draws',
                         interval='cluster bootstrap over labs (the paper\'s first lab), 500 resamples for novelty, percentile 95%',
                         populations=pops, models=A.MODELS, raw='the unmatched difference of means (no cells)', sd='sd of the outcome (novelty)', headline_model=A.HEADLINE,
                         placebo='population placebo: 2017-2021 papers, "AI" = the dose cut that flags as large a share as the 25% cut does in 2023-2025 (these flags are detector noise); placebo25 uses the 25% cut itself (too few papers for a tight interval)'),
               rows=rows)
    wp = A.RES / 'wording.parquet'
    if wp.exists():
        w = pd.read_parquet(wp)
        out['wording'] = [{k: (r(v, 5) if isinstance(v, float) else v) for k, v in x._asdict().items() if k != 'Index'} for x in w.itertuples()]
        out['meta']['wording_control'] = ('the size-matched dispersion / Vendi comparison repeated on the all-AI-rewritten abstracts (every paper\'s abstract rewritten by Qwen2.5-7B, polish style, kept rewrites; allai/): '
                                          'same cells, 25% cut and draws, same papers (those with a kept rewrite in all 7 models, so `original` is recomputed on them); share_wording = 1 - rewritten / original; '
                                          'intervals = 100 lab resamples x 10 draws. A gap that stays on the rewrites is not wording; one that shrinks toward 0 is wording')
    return dict(rows=len(rows), bytes=dump(out, 'matched_test.json'))


def build_event_study():
    out = dict(meta=dict(design='lab-year panel, y_lt = lab FE + year FE + sum_t b_t * Dose_l * 1[year = t]; 2021 is the base year, 2022 is dropped (transition); Dose_l = the lab\'s mean dose over 2023-2025 full-text papers (0 -> 1); '
                                'AbsDose_l = the lab\'s share of 2023-2025 abstracts the abstract detector flags; outcomes are size-matched lab-year values (5 papers, 100 draws); interval = estimate +- 1.96 cluster-robust se (labs)',
                         shade_pre_chatgpt='years <= 2022 (ChatGPT: 30 Nov 2022); coefficients before 2021 should be 0 if there are no pre-trends', base_year=2021, years=[2016, 2017, 2018, 2019, 2020, 2023, 2024, 2025],
                         outcomes=dict(disp='dispersion', mpd='mean pairwise distance', vendi='Vendi score', h_oa='topic entropy over OpenAlex topics (bits)', h_bt='topic entropy over BERTopic topics (bits)',
                                       nov_all='novelty against all papers (k = 3)', nov_lab='novelty against the lab\'s own history (k = 3)'),
                         dose_kinds=dict(dose='full-text dose', abs_dose='abstract flag share')), models={})
    for model in A.MODELS:
        d = pd.read_parquet(D.RESULTS / f'did_{model}_abstract.parquet')
        rec = {}
        for (outcome, dose), g in d.groupby(['outcome', 'dose']):
            ev = g[g['spec'] == 'event'].sort_values('year')
            est = g[g['spec'].isin(['did', 'placebo2019', 'placebo2020', 'placebo2021'])]
            rec.setdefault(outcome, {})[dose] = dict(
                event=[dict(year=int(x.year), beta=r(x.beta, 5), lo=r(x.lo, 5), hi=r(x.hi, 5)) for x in ev.itertuples()],
                estimates={x.spec: dict(beta=r(x.beta, 5), lo=r(x.lo, 5), hi=r(x.hi, 5), n=int(x.n), labs=int(x.labs)) for x in est.itertuples()},
                n=int(ev['n'].iloc[0]) if len(ev) else None, labs=int(ev['labs'].iloc[0]) if len(ev) else None)
        out['models'][model] = rec
    return dict(bytes=dump(out, 'event_study.json'))


# ------------------------------------------------------------------ 5. Figure 3

def build_fig3():
    f = json.loads((A.RES / 'fig3.json').read_text())
    f['meta']['schools'] = {s: s for s in ['all'] + D.SCHOOLS}
    f['meta']['box'] = 'whislo/whishi = the most extreme draw within 1.5 IQR; med, q1, q3; mean; n_outliers = draws beyond the whiskers'
    f['meta']['ai_lower_share'] = 'share of the 1,000 paired draws in which the AI group\'s value is below the non-AI group\'s'
    f['meta']['variants'] = dict(ft25='AI = dose >= 25% (full-text papers only)', abstract='AI = the abstract detector flags the abstract (all papers with an abstract score; covers schools with little full text)')
    return dict(bytes=dump(f, 'fig3_nine_schools.json'))


def assemble(args):
    fr = load()
    res = {}
    if (A.RES / 'umap.parquet').exists():
        res['map'] = build_map(fr)
    if (A.RES / 'lab_measures.parquet').exists():
        res['lab_scatter'] = build_lab_scatter()
    res['ai_use'] = build_ai_use(fr)
    if (A.RES / 'matched.parquet').exists():
        res['matched'] = build_matched()
    res['event_study'] = build_event_study()
    if (A.RES / 'fig3.json').exists():
        res['fig3'] = build_fig3()
    D.log(stage='assemble', **{k: {a: b for a, b in v.items() if a != 'sizes'} for k, v in res.items()})
    import ai_pages_figs as F
    F.figures(fr)
    import ai_pages_headline as H
    H.headline(fr, res)
