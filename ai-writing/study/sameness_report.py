"""Collect the four non-text sameness layers into SAMENESS.md, unified tables and figures (results/<id>/sameness/).

  sameness_report.py --id SNAP

Reads sameness/tables/sameness_{overlap,conc,bench,topics}_{series,contrasts}*.csv and the embedding contrasts of the main study (tables/embed_contrasts.csv).
`direction` (+1: a rise means more alike; -1: a fall does) puts every measure on one scale: "alike-ward change" = direction * (post - pre).
Verdict rule: the post-minus-pre interval excludes 0 -> toward sameness / toward diversity by the sign of direction * estimate, else no change detectable; a
verdict is marked "(continues the pre-2023 drift)" when the 2019-21 vs 2016-18 placebo interval excludes 0 with the same alike-ward sign and a size >= the post change.
The hand-written reading is spliced from sameness_reading.md (written on a given run's numbers; re-read it after a re-run).
"""
import argparse
import glob
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

import study_common as C

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

PRIMARY = {'overlap': 'refs10', 'concentration': 'refs10', 'benchmarks': 'abstract', 'topics': 'all'}
INK, MUTE, ACC, GRID = '#1f2933', '#7b8794', '#2b6cb0', '#e4e7eb'


def load(tab):
    S, K = [], []
    for kind, ser, con in (('overlap', 'sameness_overlap_series_*.csv', 'sameness_overlap_contrasts_*.csv'), ('conc', 'sameness_conc_series_*.csv', 'sameness_conc_contrasts_*.csv'),
                           ('bench', 'sameness_bench_series.csv', 'sameness_bench_contrasts.csv'), ('topics', 'sameness_topics_series.csv', 'sameness_topics_contrasts.csv')):
        for f in sorted(glob.glob(str(tab / ser))):
            S.append(pd.read_csv(f))
        for f in sorted(glob.glob(str(tab / con))):
            K.append(pd.read_csv(f))
    return pd.concat(S, ignore_index=True), pd.concat(K, ignore_index=True)


def fmt(e, lo, hi, d=4):
    if not np.isfinite(e):
        return 'n/a'
    return f'{e:+.{d}f} [{lo:+.{d}f}, {hi:+.{d}f}]'


def verdict(post, plc):
    """post, plc: rows (Series) of the post_minus_pre and placebo contrasts of one measure."""
    dr = post['direction']
    lo, hi = sorted([post['lo'] * dr, post['hi'] * dr])
    adj = post['est'] * dr
    if not np.isfinite(adj):
        return 'n/a'
    if lo > 0:
        v = 'toward sameness'
    elif hi < 0:
        v = 'toward diversity'
    else:
        return 'no change detectable'
    if plc is not None and np.isfinite(plc['est']):
        pl, ph = sorted([plc['lo'] * dr, plc['hi'] * dr])
        padj = plc['est'] * dr
        if ((v == 'toward sameness' and pl > 0) or (v == 'toward diversity' and ph < 0)) and abs(padj) >= abs(adj):
            v += ' (continues the pre-2023 drift)'
    return v


def keycols(K):
    return [c for c in ('layer', 'measure', 'variant', 'group', 'level', 'pairs', 'scope', 'sample') if c in K.columns]


def wide(K):
    """One row per measure key with post-minus-pre, placebo, excl-2022 columns and the verdict."""
    kc = keycols(K)
    K = K.copy()
    K[kc] = K[kc].fillna('')
    out = []
    for key, g in K.groupby(kc, sort=False):
        c = g.set_index('contrast')
        if 'post_minus_pre' not in c.index:
            continue
        p = c.loc['post_minus_pre']
        plc = c.loc['placebo_2019_21_minus_2016_18'] if 'placebo_2019_21_minus_2016_18' in c.index else None
        r = dict(zip(kc, key))
        r.update(direction=p['direction'], pre=p['pre'], post=p['post'], est=p['est'], lo=p['lo'], hi=p['hi'],
                 placebo_est=plc['est'] if plc is not None else np.nan, placebo_lo=plc['lo'] if plc is not None else np.nan, placebo_hi=plc['hi'] if plc is not None else np.nan,
                 excl2022_est=c.loc['post_minus_pre_excl2022']['est'] if 'post_minus_pre_excl2022' in c.index else np.nan,
                 verdict=verdict(p, plc))
        out.append(r)
    return pd.DataFrame(out)


def embedding_rows(res):
    e = pd.read_csv(res / 'tables' / 'embed_contrasts.csv')
    e = e[(e.scope.isin(['ALL', 'EXCL_PARTIAL'])) & (e['sample'] == 'all') & (e.variant == 'raw')]
    rows = []
    names = {'within_lab': 'within lab', 'cross_lab_same_school': 'across labs, same school', 'cross_school': 'across schools'}
    for (model, level, scope), g in e.groupby(['model', 'level', 'scope']):
        c = g.set_index('contrast')
        p, plc = c.loc['post_minus_pre'], c.loc['placebo_2019_21_minus_2016_18']
        q = pd.Series(dict(direction=-1, est=p.est, lo=p.lo, hi=p.hi))
        z = pd.Series(dict(est=plc.est, lo=plc.lo, hi=plc.hi))
        rows.append(dict(layer='embeddings', measure=f'distance, {names[level]}', model=model, scope=scope, direction=-1, pre=p.pre, post=p.post, est=p.est, lo=p.lo, hi=p.hi,
                         placebo_est=plc.est, placebo_lo=plc.lo, placebo_hi=plc.hi, verdict=verdict(q, z)))
    return pd.DataFrame(rows)


def series_fig(S, panels, path, title):
    """panels: list of (title, dict of filters, ylabel). One small multiple each; line = point estimate, ribbon = 95% lab-cluster interval, band = post period."""
    n = len(panels)
    cols = 3 if n > 4 else 2
    rows = int(np.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(4.3 * cols, 2.9 * rows), squeeze=False)
    for ax, (ttl, flt, yl) in zip(axs.ravel(), panels):
        m = np.ones(len(S), bool)
        for k, v in flt.items():
            m &= (S[k].fillna('') == v).to_numpy() if k in S else False
        g = S[m].sort_values('year')
        ax.axvspan(2022.9, 2025.3, color=GRID, zorder=0)
        for line, (sc, col, ls) in enumerate((('ALL', ACC, '-'), ('EXCL_PARTIAL', INK, ':'))):
            h = g[g.scope == sc]
            if h.empty:
                continue
            ax.plot(h.year, h.est, color=col, lw=2 if line == 0 else 1.4, ls=ls, label=sc.replace('_', ' ').lower() if line else 'all 12 schools')
            if line == 0:
                ax.fill_between(h.year, h.lo, h.hi, color=col, alpha=.18, lw=0)
        ax.set_title(ttl, fontsize=9.5, color=INK, loc='left')
        ax.set_ylabel(yl, fontsize=8, color=MUTE)
        ax.set_xticks([2016, 2019, 2022, 2025])
        ax.tick_params(labelsize=8, colors=MUTE)
        ax.grid(axis='y', color=GRID, lw=.6)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
    for ax in axs.ravel()[n:]:
        ax.axis('off')
    h, l = axs.ravel()[0].get_legend_handles_labels()
    if h:
        fig.legend(h, l, loc='upper right', fontsize=8, frameon=False, ncol=2)
    fig.suptitle(title + '  (shaded: 2023-2025)', fontsize=10.5, color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(path, dpi=140)
    plt.close(fig)


def mega_titles(snap, tab, sample='refs10', top=25):
    import sqlite3
    m = pd.read_csv(tab / f'ref_mega_works_{sample}.csv').head(top)
    db = sqlite3.connect(f'file:{snap / "universe" / "oa_fields.sqlite"}?mode=ro', uri=True)
    t = []
    for w in m['work']:
        r = db.execute('select title, year from works where id=?', (f'W{w}',)).fetchone()
        t.append(f'{r[0]} ({r[1]})' if r else '')
    db.close()
    m['title_if_in_store'] = t
    m.to_csv(tab / 'ref_mega_works_titles.csv', index=False)
    return m


def md_table(df, cols, heads):
    out = ['| ' + ' | '.join(heads) + ' |', '|' + '---|' * len(heads)]
    for _, r in df.iterrows():
        out.append('| ' + ' | '.join(str(r[c]) for c in cols) + ' |')
    return '\n'.join(out)


def row_fmt(w, d=4):
    w = w.copy()
    w['pre_post'] = [f'{a:.{d}g} to {b:.{d}g}' for a, b in zip(w.pre, w.post)]
    w['change'] = [fmt(e, l, h, d) for e, l, h in zip(w.est, w.lo, w.hi)]
    w['placebo'] = [fmt(e, l, h, d) for e, l, h in zip(w.placebo_est, w.placebo_lo, w.placebo_hi)]
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    a = ap.parse_args()
    res = C.results_dir(a.id)
    out = res / 'sameness'
    tab, fig = out / 'tables', out / 'figures'
    fig.mkdir(exist_ok=True)
    S, K = load(tab)
    W = wide(K)
    W.to_csv(tab / 'sameness_all_contrasts_wide.csv', index=False)
    S.to_csv(tab / 'sameness_all_series.csv', index=False)
    E = embedding_rows(res)
    E.to_csv(tab / 'embedding_reference_contrasts.csv', index=False)
    for c in ('variant', 'group', 'pairs', 'level'):
        if c not in W:
            W[c] = ''
    W = W.fillna({'variant': '', 'group': '', 'pairs': '', 'level': ''})

    def pick(layer, measure, scope='ALL', **kw):
        m = (W.layer == layer) & (W.measure == measure) & (W.scope == scope)
        for k, v in kw.items():
            m &= W[k] == v
        g = W[m]
        return g.iloc[0] if len(g) else None

    H = []          # headline rows: (family, label, row)

    def add(family, label, layer, measure, **kw):
        r = pick(layer, measure, **kw)
        if r is not None:
            r2 = r.copy()
            pe = pick(layer, measure, scope='EXCL_PARTIAL', **kw)
            r2['excl_partial_est'] = pe['est'] if pe is not None else np.nan
            H.append((family, label, r2))
    s_ref = dict(sample='refs10')
    add('1 Reference overlap', 'Jaccard ratio obs/null, labs of one school', 'overlap', 'ref_jac_ratio', pairs='within', **s_ref)
    add('1 Reference overlap', 'Jaccard ratio obs/null, labs of different schools', 'overlap', 'ref_jac_ratio', pairs='across', **s_ref)
    add('1 Reference overlap', 'Jaccard excess (obs - null), one school', 'overlap', 'ref_jac_excess', pairs='within', **s_ref)
    add('1 Reference overlap', 'bibliographic coupling cosine ratio obs/null, one school', 'overlap', 'ref_cos_ratio', pairs='within', **s_ref)
    add('1 Reference overlap', 'bibliographic coupling cosine ratio obs/null, different schools', 'overlap', 'ref_cos_ratio', pairs='across', **s_ref)
    for v, lab in (('full', 'all cited works'), ('rise100', 'without the 100 works that rose most'), ('top100', 'without the 100 most cited works')):
        add('2 Citation concentration', f'share of references on the top 1% of cited works ({lab})', 'concentration', 'cite_top1pct', variant=v, **s_ref)
        add('2 Citation concentration', f'Gini of cited-work frequency ({lab})', 'concentration', 'cite_gini', variant=v, **s_ref)
    for m_, lab in (('cite_top1pct', 'share of references on the top 1% of cited works'), ('cite_gini', 'Gini of cited-work frequency'), ('cite_canon5_share', 'share of references on works cited by >= 5% of labs')):
        add('2 Citation concentration', f'{lab} (journal papers only, stable coverage)', 'concentration', m_, variant='full', sample='journal')
        add('2 Citation concentration', f'{lab} (journal papers only, 100 rising works removed)', 'concentration', m_, variant='rise100', sample='journal')
    add('1 Reference overlap', 'Jaccard ratio obs/null, one school (journal papers only)', 'overlap', 'ref_jac_ratio', pairs='within', sample='journal')
    add('1 Reference overlap', 'Jaccard ratio obs/null, different schools (journal papers only)', 'overlap', 'ref_jac_ratio', pairs='across', sample='journal')
    add('2 Citation concentration', 'share of references on works cited by >= 5% of labs (all cited works)', 'concentration', 'cite_canon5_share', variant='full', **s_ref)
    add('2 Citation concentration', 'same, without the 100 works that rose most', 'concentration', 'cite_canon5_share', variant='rise100', **s_ref)
    add('2 Citation concentration', 'share of references on the 100 most cited works', 'concentration', 'cite_top100', variant='full', **s_ref)
    for g, lab in (('bench_data', 'benchmarks + datasets'), ('meth', 'methods')):
        for k, kl in (('hhi', 'HHI'), ('entropy', 'entropy (bits)'), ('top5_cond', 'share of entry-using labs that use a top-5 entry'), ('top10_cond', 'share of entry-using labs that use a top-10 entry'), ('top5_labs', 'share of all labs using a top-5 entry'), ('any_labs', 'share of labs using any entry')):
            add('3 Benchmarks and methods', f'{lab}: {kl} (abstracts)', 'benchmarks', f'bench_{g}_{k}', sample='abstract', group=g)
    add('3 Benchmarks and methods', 'benchmarks + datasets: HHI (full-text main body, papers with a copy)', 'benchmarks', 'bench_bench_data_hhi', sample='fulltext', group='bench_data')
    add('3 Benchmarks and methods', 'methods: HHI (full-text main body, papers with a copy)', 'benchmarks', 'bench_meth_hhi', sample='fulltext', group='meth')
    for lv in ('topic', 'subfield'):
        for k, kl in (('hhi', 'HHI'), ('entropy', 'entropy (bits)'), ('eff_n', 'effective number')):
            add('4 Topics', f'primary {lv}: {kl}', 'topics', f'topic_{lv}_{k}', level=lv, sample='all')
    add('4 Topics', 'cross-lab JSD of subfield mixes, one school (yearly extension)', 'topics', 'topic_jsd_subfield', pairs='within', sample='all')
    add('4 Topics', 'cross-lab JSD of subfield mixes, different schools', 'topics', 'topic_jsd_subfield', pairs='across', sample='all')
    add('4 Topics', 'cross-lab JSD, one school, fixed lab set (>= 10 papers in >= 6 years)', 'topics', 'topic_jsd_subfield', pairs='within', sample='stable')
    add('4 Topics', 'cross-lab JSD, different schools, fixed lab set', 'topics', 'topic_jsd_subfield', pairs='across', sample='stable')
    hd = pd.DataFrame([dict(r.to_dict(), family=f, measure_id=r['measure'], measure=l) for f, l, r in H])
    hd.to_csv(tab / 'sameness_headline.csv', index=False)

    # embedding reference
    emb = E[(E.model == 'specter2_proximity') & (E.scope == 'ALL')]
    # figures
    series_fig(S, [('Jaccard obs/null, one school', dict(layer='overlap', measure='ref_jac_ratio', pairs='within', sample='refs10'), 'ratio'),
                   ('Jaccard obs/null, different schools', dict(layer='overlap', measure='ref_jac_ratio', pairs='across', sample='refs10'), 'ratio'),
                   ('coupling cosine obs/null, one school', dict(layer='overlap', measure='ref_cos_ratio', pairs='within', sample='refs10'), 'ratio'),
                   ('Jaccard raw, one school', dict(layer='overlap', measure='ref_jac_raw', pairs='within', sample='refs10'), 'Jaccard'),
                   ('Jaccard null, one school', dict(layer='overlap', measure='ref_jac_null', pairs='within', sample='refs10'), 'Jaccard'),
                   ('Jaccard obs/null, journal papers only', dict(layer='overlap', measure='ref_jac_ratio', pairs='within', sample='journal'), 'ratio')],
               fig / 'fig1_reference_overlap.png', '1. Reference-list overlap between labs')
    series_fig(S, [('top 1% of cited works: share of references', dict(layer='concentration', measure='cite_top1pct', variant='full', sample='refs10'), 'share'),
                   ('same, 100 rising works removed', dict(layer='concentration', measure='cite_top1pct', variant='rise100', sample='refs10'), 'share'),
                   ('Gini of cited-work frequency', dict(layer='concentration', measure='cite_gini', variant='full', sample='refs10'), 'Gini'),
                   ('Gini, 100 rising works removed', dict(layer='concentration', measure='cite_gini', variant='rise100', sample='refs10'), 'Gini'),
                   ('references on works cited by >= 5% of labs', dict(layer='concentration', measure='cite_canon5_share', variant='full', sample='refs10'), 'share'),
                   ('same, 100 rising works removed', dict(layer='concentration', measure='cite_canon5_share', variant='rise100', sample='refs10'), 'share')],
               fig / 'fig2_citation_concentration.png', '2. Citation concentration')
    series_fig(S, [('benchmarks + datasets: HHI', dict(measure='bench_bench_data_hhi', sample='abstract'), 'HHI'),
                   ('benchmarks + datasets: top-5 share among users', dict(measure='bench_bench_data_top5_cond', sample='abstract'), 'share of labs'),
                   ('benchmarks + datasets: entropy (bits)', dict(measure='bench_bench_data_entropy', sample='abstract'), 'bits'),
                   ('methods: HHI', dict(measure='bench_meth_hhi', sample='abstract'), 'HHI'),
                   ('methods: top-5 share among users', dict(measure='bench_meth_top5_cond', sample='abstract'), 'share of labs'),
                   ('methods: HHI, full text', dict(measure='bench_meth_hhi', sample='fulltext'), 'HHI')],
               fig / 'fig3_benchmarks_methods.png', '3. Benchmark, dataset and method clustering')
    series_fig(S, [('primary topic: HHI', dict(measure='topic_topic_hhi', sample='all'), 'HHI'),
                   ('primary topic: entropy (bits)', dict(measure='topic_topic_entropy', sample='all'), 'bits'),
                   ('subfield: HHI', dict(measure='topic_subfield_hhi', sample='all'), 'HHI'),
                   ('cross-lab JSD, one school', dict(measure='topic_jsd_subfield', pairs='within', sample='all'), 'JSD (bits)'),
                   ('cross-lab JSD, different schools', dict(measure='topic_jsd_subfield', pairs='across', sample='all'), 'JSD (bits)'),
                   ('primary topic: HHI, computer science only', dict(measure='topic_topic_hhi', sample='cs'), 'HHI')],
               fig / 'fig4_topic_concentration.png', '4. Topic concentration across labs')

    # comparison figure: alike-ward change of the headline measures with intervals
    h = hd.copy()
    h['adj'] = h.est * h.direction
    h['alo'] = np.where(h.direction > 0, h.lo, -h.hi)
    h['ahi'] = np.where(h.direction > 0, h.hi, -h.lo)
    h['scale'] = h.pre.abs().replace(0, np.nan)
    h = h[h['sample'].isin(['refs10', 'journal', 'abstract', 'all', 'stable']) | h.measure.str.contains('full-text')]
    h = h[~h.measure.str.contains('excess')]
    fig2, ax = plt.subplots(figsize=(8, 0.3 * len(h) + 1.2))
    y = np.arange(len(h))[::-1]
    for yy, (_, r) in zip(y, h.iterrows()):
        sc = r.scale if np.isfinite(r.scale) else 1.0
        ax.plot([r.alo / sc * 100, r.ahi / sc * 100], [yy, yy], color=ACC, lw=2)
        ax.plot(r.adj / sc * 100, yy, 'o', color=ACC, ms=4)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_yticks(y)
    ax.set_yticklabels([m[:78] for m in h.measure], fontsize=6.5)
    ax.set_xlabel('alike-ward change (post minus pre) as % of pre level; right = labs more alike', fontsize=7)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.set_title('Headline measures, 95% lab-cluster intervals', fontsize=10, loc='left')
    fig2.tight_layout()
    fig2.subplots_adjust(left=0.5)
    fig2.savefig(fig / 'fig5_alikeward_change.png', dpi=140)
    plt.close(fig2)

    # mega works
    try:
        mt = mega_titles(C.snapshot_dir(a.id), tab)
        resolved = int((mt.title_if_in_store != '').sum())
    except Exception as e:  # noqa: BLE001
        mt, resolved = None, 0
        print('mega titles failed', e)

    # coverage
    ovd = pd.read_csv(tab / 'sameness_overlap_diag_refs10.csv')
    cov = pd.read_csv(tab / 'bench_sample_coverage.csv') if (tab / 'bench_sample_coverage.csv').exists() else None
    hc = pd.read_csv(tab / 'bench_handcheck_verdicts.csv') if (tab / 'bench_handcheck_verdicts.csv').exists() else None
    dc = pd.read_csv(tab / 'bench_dictionary_coverage.csv')

    L = []
    L.append(f'# Non-text sameness: do labs converge in what they cite, use and work on? (snapshot {a.id})\n')
    L.append('Owner decision 2026-11-08. The embedding result (study RESULTS.md) says labs became slightly more alike in SPECTER2 and six other embeddings after 2022 (across labs -0.011, across schools -0.010 in distance). '
             'That could be prose drifting toward ChatGPT style. This page measures sameness with things that are not wording: reference lists, cited works, benchmark/dataset/method names, and OpenAlex topics. '
             'Window 2016-2025, post = 2023-2025, pre = 2016-2022, no 2026. Every interval is a 95% percentile interval of a lab-cluster bootstrap stratified by school (400 draws; seeds in `sameness_common.py`). '
             'A period value is the mean of its year values. Placebo = 2019-21 minus 2016-18. Labs are strict (PI on the byline).\n')
    L.append('## 1. Headline\n')
    L.append('"Alike-ward" is the direction in which labs get more alike (overlap and concentration up, distance and entropy down). Verdict rule in `sameness_report.py`.\n')
    L.append('### Reference for comparison: embeddings (SPECTER2 proximity, abstracts)\n')
    r = emb.assign(pre_post=[f'{a_:.3f} to {b_:.3f}' for a_, b_ in zip(emb.pre, emb.post)], change=[fmt(e, l, h_, 4) for e, l, h_ in zip(emb.est, emb.lo, emb.hi)],
                   placebo=[fmt(e, l, h_, 4) for e, l, h_ in zip(emb.placebo_est, emb.placebo_lo, emb.placebo_hi)])
    L.append(md_table(r, ['measure', 'pre_post', 'change', 'placebo', 'verdict'], ['embedding measure (distance)', 'pre to post', 'post minus pre [95% CI]', 'placebo [95% CI]', 'verdict']) + '\n')
    L.append('### Non-text measures, all 12 schools\n')
    for fam, g in hd.groupby('family', sort=True):
        L.append(f'**{fam}**\n')
        g = row_fmt(g)
        g['excl'] = [f'{x:+.4g}' if np.isfinite(x) else 'n/a' for x in g.excl_partial_est]
        L.append(md_table(g, ['measure', 'direction', 'pre_post', 'change', 'placebo', 'excl', 'verdict'],
                          ['measure', 'dir', 'pre to post', 'post minus pre [95% CI]', 'placebo [95% CI]', 'est. without harvard/jhu/washu', 'verdict']) + '\n')
    L.append('Directions: +1 = a rise means labs are more alike; -1 = a fall does. Harvard, JHU and WashU have no reference lists in the local store, so for layers 1 and 2 the sensitivity is identical by construction (see caveats).\n')
    L.append('## 2. Reading\n')
    rp = Path(__file__).with_name('sameness_reading.md')
    L.append(rp.read_text() if rp.exists() else '(reading not written)\n')
    L.append('\n## 3. Method notes\n')
    L.append('**Reference overlap.** Lab set = union of the references of the lab\'s papers in the year (papers with >= 10 listed references; labs with >= 2 such papers). Pairs of labs sharing a paper that year are dropped. '
             'Null: the (lab, reference) memberships of the year are permuted across labs, each lab keeping its list size, 5 replicates; the null keeps popularity of works and lab size, so obs/null and obs-null are overlap beyond popularity and size. '
             'Bibliographic coupling = shared references; reported as cosine (normalised) and raw count in the tables. Mean null list size over observed: ' + f'{ovd.null_size_ratio.min():.3f} to {ovd.null_size_ratio.max():.3f}' + ' (duplicates inside a lab collapse).\n')
    L.append('**Citation concentration.** Per scope-year each work is counted once per citing lab; counts are thinned binomially to a fixed number of lab-work memberships per scope so list-size growth cannot move them. '
             'Top 1% = the top 1% of distinct cited works in the year; canonical = cited by >= 5% of the year\'s labs (unthinned). Variants: `rise100` removes the 100 works whose lab-frequency share rose most from pre to post; `top100` removes the 100 most cited overall. '
             'The store has no cited_by counts for works outside the study corpus, so "most-cited" means most cited by these labs in that year, not globally.\n')
    if mt is not None:
        L.append(f'The 25 fastest-rising works are listed in `tables/ref_mega_works_titles.csv`; {resolved} of 25 have a title in the store (the rest are outside the study corpus; their OpenAlex ids are given).\n')
    L.append('**Benchmarks and methods.** Dictionary `sameness_dictionary.py`: ' + f'{len(dc)} entries ({(dc.kind == "bench").sum()} benchmarks, {(dc.kind == "data").sum()} datasets, {(dc.kind == "meth").sum()} methods/families)' +
             ', built from OpenAlex keywords and mined capitalised names of the 47k computer-science abstracts (candidate lists in `tables/bench_candidates_*.csv`), reviewed by hand. Papers with Code is defunct (shut down 2025) and nothing was scraped. '
             'Abstract mentions use title + abstract of every lab paper with an abstract. Full text: main body of papers with a stored copy after its first quarter (the store has no section headings, so "methods/experiments" is a proxy), >= 2 mentions. '
             'The full-text sample covers different shares of papers in different years (`tables/bench_sample_coverage.csv`), so it is secondary.\n')
    if cov is not None:
        L.append(md_table(cov.round(3).astype(str), list(cov.columns), list(cov.columns)) + '\n')
    if hc is not None:
        okn = int((hc.verdict == 'correct').sum())
        L.append(f'**Hand check (seed 20261108, 30 random title+abstract extractions).** {okn} of {len(hc)} correct; the incorrect: ' + '; '.join(f'{r_.entry} ({r_.note})' for r_ in hc[hc.verdict != "correct"].itertuples()) +
                 '. Checked by the agent that wrote the dictionary, not independently; `tables/bench_handcheck_verdicts.csv`. A hit means the paper names the entry, not that it evaluates on it, and several entries are families (e.g. WMT also catches IWSLT).\n')
    L.append('**Topics.** Concentration of OpenAlex primary topics and subfields over strict lab-paper rows, thinned to a fixed row count; cross-lab JSD = the existing design of `topics_crosslab_jsd` (rarefied to 10 papers, 10 replicates) made yearly, adding across-school pairs and the placebo. '
             'The existing pooled-period table is reproduced in `tables/topics_crosslab_jsd.csv` of the main results (post minus pre -0.0068 [-0.0135, +0.0008]).\n')
    L.append('## 4. Caveats\n')
    L.append('- **Reference lists vanish for recent repository papers** in OpenAlex (>= 10 references: 19% of repository papers in 2022, 8% from 2023; conferences 0.83 to 0.57 by 2025; journals stable at 0.88-0.94). Coverage by year is in `tables/sameness_overlap_diag_refs10.csv`. The primary sample keeps papers with >= 10 references; the `journal` sample (stable coverage) is the sensitivity, and both are in the tables.\n'
             '- **Harvard, JHU and WashU have no reference lists** in the local OpenAlex store (the store keeps counts, not lists, for them) and `referenced_works` is not in the stored work bodies at all; layers 1 and 2 use the 130k-work universe table. For those schools the lists could be fetched with about 160 API calls; not done (instruction: store only).\n'
             '- Mentions are not use, the dictionary is closed (new benchmarks after its construction enter only if listed), and abstracts of 2023-25 are partly AI-written, which can change how often names appear.\n')
    L.append('## 5. Files\n')
    L.append('Tables: `tables/sameness_headline.csv`, `tables/sameness_all_contrasts_wide.csv` (every scope, sample and variant), `tables/sameness_all_series.csv`, per-layer series and contrasts, `tables/embedding_reference_contrasts.csv`. '
             'Figures: `figures/fig1`..`fig5` (series by year, 95% ribbon, 2023-25 shaded). Code: `ai-writing/study/sameness_*.py`, `run_study.sh sameness`.\n')
    (out / 'SAMENESS.md').write_text('\n'.join(L))
    print(json.dumps({'headline_rows': len(hd), 'wide_rows': len(W)}))


if __name__ == '__main__':
    main()
