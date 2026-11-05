"""Static PNGs of the AI-pages data (diversity/reports/figures-ai-pages/); same light surface and palette as the October figures (diversity/figures.py)."""
import json

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

import ai_pages as A  # noqa: E402
import dcommon as D  # noqa: E402

C_NOT, C_AI, C_GREEN, C_GOLD, C_PINK, C_PURPLE = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#8a5cc2'
INK, INK2, MUTED, GRID, SURF = '#1d2a33', '#46525a', '#68747c', '#e3e5e0', '#fcfcfb'
SCHOOL_C = dict(zip(D.SCHOOLS, [C_NOT, C_AI, C_GREEN, C_GOLD, C_PINK, C_PURPLE, '#17becf', '#7f7f7f', '#bcbd22']))
SCHOOL_LABEL = dict(princeton='Princeton', cmu='CMU', epfl='EPFL', mit='MIT', berkeley='Berkeley', stanford='Stanford', michigan='Michigan', uchicago='UChicago', gatech='Georgia Tech', all='All')
KIND_C = dict(llm=C_AI, ml=C_NOT, other=MUTED)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.facecolor': SURF,
                     'figure.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.titlecolor': INK,
                     'legend.labelcolor': INK2, 'axes.spines.top': False, 'axes.spines.right': False})


def save(fig, name):
    A.FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(A.FIG / name, dpi=150)
    plt.close(fig)


def fig_map(fr):
    um = pd.read_parquet(A.RES / 'umap.parquet')
    d = fr.merge(um, on='paper_id')
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    lim = (d['ux'].min(), d['ux'].max(), d['uy'].min(), d['uy'].max())
    for ax, (title, sel) in zip(axes[:2], (('2016-2022 (%s papers)', d['year'] <= 2022), ('2023-2025 (%s papers)', d['year'] >= 2023))):
        g = d[sel]
        ax.hexbin(g['ux'], g['uy'], gridsize=90, extent=lim, cmap='Blues', mincnt=1, bins='log', linewidths=0)
        ax.set_title(title % f'{len(g):,}', loc='left', fontsize=9.5)
    ax = axes[2]
    g = d[d['year'] >= 2023]
    ax.scatter(g['ux'], g['uy'], s=0.3, c=GRID, linewidths=0, rasterized=True)
    a = d[(d['year'] == 2025) & (d['ai25'] == 1)]
    ax.scatter(a['ux'], a['uy'], s=1.6, c=C_AI, linewidths=0, alpha=0.7, rasterized=True)
    ax.set_title(f'2025 papers with at least 25% AI passages (orange, {len(a):,})', loc='left', fontsize=9.5)
    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        ax.set_xlim(lim[0], lim[1])
        ax.set_ylim(lim[2], lim[3])
    fig.suptitle(f'Paper map: {len(d):,} lab papers 2016-2025, SPECTER2 proximity abstract vectors, UMAP (seed {A.SEED})', x=0.01, ha='left', fontsize=10.5, color=INK)
    fig.tight_layout()
    save(fig, 'paper_map.png')


def fig_lab_scatter():
    lab = json.loads(__import__('gzip').open(A.OUT / 'lab_scatter.json.gz').read())
    sl = {(s['measure'], s['model']): s for s in lab['slopes']}
    fig, axes = plt.subplots(2, 4, figsize=(13.2, 6.4))
    for ax, m in zip(axes.flat, A.MEASURES):
        pts = [(100 * L['dose'], L['values'][m][A.HEADLINE][2], L['school']) for L in lab['labs'] if L['dose'] is not None and m in L['values'] and A.HEADLINE in L['values'][m] and L['values'][m][A.HEADLINE][2] is not None]
        x = np.array([p[0] for p in pts])
        y = np.array([p[1] for p in pts])
        for s in D.SCHOOLS:
            q = np.array([p[2] == s for p in pts])
            if q.any():
                ax.scatter(x[q], y[q], s=9, c=SCHOOL_C[s], alpha=0.75, linewidths=0.3, edgecolors=SURF)
        S = sl[(m, A.HEADLINE)]
        xx = np.linspace(0, np.percentile(x, 99), 40)
        ax.plot(xx, S['line_a'] + S['line_b_per_pct'] * xx, color=INK, lw=1.5)
        ax.axhline(0, color=MUTED, lw=0.8)
        lo, hi = np.percentile(y, [1, 99])
        ax.set_ylim(lo - 0.08 * (hi - lo), hi + 0.08 * (hi - lo))
        ax.set_title(A.MEASURE_LABEL[m], loc='left', fontsize=8.8, pad=14)
        ax.text(0, 1.02, f'beta = {S["beta"]:+.2f} [{S["lo"]:+.2f}, {S["hi"]:+.2f}], {S["labs"]} labs', transform=ax.transAxes, fontsize=7.2, color=MUTED)
        ax.set_xlabel('post-period AI dose (%)', fontsize=7.8)
    axes[0, 0].set_ylabel('change, post - pre')
    axes[1, 0].set_ylabel('change, post - pre')
    fig.suptitle('Lab scatter (SPECTER2 proximity): change in each measure, 2023-2025 minus 2016-2022, against the lab\'s AI dose; Huber fit', x=0.01, ha='left', fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    save(fig, 'lab_scatter.png')
    fig, axes = plt.subplots(1, 8, figsize=(14, 3.4), sharey=True)
    for ax, m in zip(axes, A.MEASURES):
        for j, mod in enumerate(A.MODELS):
            S = sl[(m, mod)]
            ax.errorbar(S['beta'], j, xerr=[[S['beta'] - S['lo']], [S['hi'] - S['beta']]], fmt='o', ms=3.5, color=C_AI if mod == A.HEADLINE else INK2, elinewidth=1.2)
        ax.axvline(0, color=MUTED, lw=0.8)
        ax.set_title(A.MEASURE_LABEL[m], fontsize=7.8, loc='left')
        ax.set_yticks(range(len(A.MODELS)))
        ax.set_yticklabels([A.MODEL_LABEL[x] for x in A.MODELS], fontsize=7.5)
        ax.invert_yaxis()
        ax.tick_params(axis='x', labelsize=7)
    fig.suptitle('Standardized Huber slope of the change on the AI dose, 7 embedding models, 95% bootstrap interval over labs', x=0.01, ha='left', fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    save(fig, 'lab_slopes_forest.png')


def fig_ai_use():
    u = json.loads(__import__('gzip').open(A.OUT / 'ai_use.json.gz').read())
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), gridspec_kw=dict(width_ratios=[1, 1.25, 1.1]))
    ax = axes[0]
    for k, lab in (('llm', 'LLM topics'), ('ml', 'other ML topics'), ('other', 'all other topics')):
        s = u['kind_series'][k]
        y = np.array([np.nan if v is None else 100 * v for v in s['share']])
        ax.plot(A.YEARS, y, color=KIND_C[k], lw=2, marker='o', ms=3.5, label=lab)
        lo = np.array([np.nan if v is None else 100 * v for v in s['lo']])
        hi = np.array([np.nan if v is None else 100 * v for v in s['hi']])
        ax.fill_between(A.YEARS, lo, hi, color=KIND_C[k], alpha=0.15, linewidth=0)
    ax.axvline(2022.9, color=GRID)
    ax.set_xticks(A.YEARS)
    ax.set_xticklabels([str(y)[2:] for y in A.YEARS])
    ax.set_ylabel('% of papers with at least 25% AI passages')
    ax.set_title('A  AI use in vs outside LLM research', loc='left', fontsize=9.5)
    ax.legend(frameon=False, fontsize=8, loc='upper left')
    ax = axes[1]
    top = u['top_by_2025_share'][:18][::-1]
    ax.barh(range(len(top)), [100 * t['share_2025'] for t in top], color=[KIND_C[t['kind']] for t in top], height=0.7)
    ax.scatter([100 * t['share_2022'] for t in top], range(len(top)), c=INK, s=10, zorder=3, label='2022')
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([t['label'][:38] for t in top], fontsize=7)
    ax.set_xlabel('% of 2025 papers with at least 25% AI passages (dot: 2022)')
    ax.set_title('B  Topics with the highest 2025 share (n >= 30)', loc='left', fontsize=9.5)
    ax.grid(axis='y', visible=False)
    ax = axes[2]
    fl = sorted([f for f in u['fields'] if f['n'][-1] >= 30], key=lambda f: -(f['share'][-1] or 0))[:14][::-1]
    ax.barh(range(len(fl)), [100 * f['share'][-1] for f in fl], color=C_GREEN, height=0.7)
    ax.scatter([100 * (f['share'][A.YEARS.index(2022)] or 0) for f in fl], range(len(fl)), c=INK, s=10, zorder=3)
    ax.set_yticks(range(len(fl)))
    ax.set_yticklabels([f['field'][:32] for f in fl], fontsize=7)
    ax.set_xlabel('% of 2025 papers (dot: 2022)')
    ax.set_title('C  OpenAlex fields', loc='left', fontsize=9.5)
    ax.grid(axis='y', visible=False)
    fig.tight_layout()
    save(fig, 'ai_use.png')


def fig_matched():
    m = json.loads((A.OUT / 'matched_test.json').read_text())
    rows = m['rows']
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2))
    for ax, (meas, title) in zip(axes, (('novelty', 'Paper novelty (k = 3)'), ('dispersion', 'Dispersion of size-matched sets'), ('vendi', 'Vendi score of size-matched sets'))):
        for j, mod in enumerate(A.MODELS):
            for off, pop, c, lab in ((-0.17, 'post', C_AI, 'AI vs not, 2023-2025'), (0.17, 'placebo', MUTED, 'placebo 2017-2021 (detector noise)')):
                x = [q for q in rows if q['population'] == pop and q['model'] == mod and q['measure'] == meas]
                if x:
                    x = x[0]
                    ax.errorbar(x['effect'], j + off, xerr=[[x['effect'] - x['lo']], [x['hi'] - x['effect']]], fmt='o', ms=4, color=c, elinewidth=1.3, label=lab if j == 0 else None)
        ax.axvline(0, color=MUTED, lw=0.8)
        ax.set_yticks(range(len(A.MODELS)))
        ax.set_yticklabels([A.MODEL_LABEL[x] for x in A.MODELS], fontsize=8)
        ax.invert_yaxis()
        ax.set_title(title, loc='left', fontsize=9.5)
        ax.set_xlabel('AI minus non-AI papers, same topic, year and school', fontsize=7.5)
        ax.locator_params(axis='x', nbins=5)
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, fontsize=8, loc='upper right', ncol=2)
    fig.suptitle('Topic-matched test: cell-weighted differences with 95% cluster-bootstrap intervals over labs', x=0.01, ha='left', fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, 'matched_test.png')


def fig_event():
    e = json.loads((A.OUT / 'event_study.json').read_text())
    outs = ['disp', 'mpd', 'vendi', 'h_oa', 'nov_all', 'nov_lab']
    fig, axes = plt.subplots(2, 3, figsize=(12.5, 6))
    for ax, o in zip(axes.flat, outs):
        for j, mod in enumerate(A.MODELS):
            rec = e['models'][mod].get(o, {}).get('dose')
            if not rec:
                continue
            yrs = [x['year'] for x in rec['event']]
            ax.plot(yrs, [x['beta'] for x in rec['event']], color=C_AI if mod == A.HEADLINE else MUTED, lw=1.6 if mod == A.HEADLINE else 0.8, marker='o', ms=3 if mod == A.HEADLINE else 0, alpha=1 if mod == A.HEADLINE else 0.6)
            if mod == A.HEADLINE:
                ax.fill_between(yrs, [x['lo'] for x in rec['event']], [x['hi'] for x in rec['event']], color=C_AI, alpha=0.15, linewidth=0)
        ax.axvspan(2015.5, 2022.5, color=GRID, alpha=0.35, linewidth=0)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_title(e['meta']['outcomes'][o], loc='left', fontsize=9)
        ax.set_xticks([2016, 2018, 2020, 2021, 2023, 2025])
    fig.suptitle('Event study: coefficient of (lab AI dose x year), 2021 = 0; SPECTER2 proximity in orange with 95% band, other six models in grey; grey = before ChatGPT', x=0.01, ha='left', fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, 'event_study.png')


def fig_fig3():
    f = json.loads((A.OUT / 'fig3_nine_schools.json').read_text())
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 7.4))
    for r_, variant in enumerate(('ft25', 'abstract')):
        gs = [g for g in f['groups'] if g['variant'] == variant and 'skipped' not in g]
        for c_, (meas, ylab) in enumerate((('extent', 'knowledge extent (max distance to centroid)'), ('entropy', 'topic entropy (bits, 50 clusters)'))):
            ax = axes[r_, c_]
            for i, g in enumerate(gs):
                for off, k, col in ((-0.19, 'not', C_NOT), (0.19, 'ai', C_AI)):
                    b = g[meas][k]
                    ax.bxp([dict(whislo=b['whislo'], q1=b['q1'], med=b['med'], q3=b['q3'], whishi=b['whishi'], fliers=[])], positions=[i + off], widths=0.32, showfliers=False, patch_artist=True,
                           boxprops=dict(facecolor=col, edgecolor=col, alpha=0.85), medianprops=dict(color=INK, lw=1.2), whiskerprops=dict(color=col), capprops=dict(color=col))
            ax.set_xticks(range(len(gs)))
            ax.set_xticklabels([f"{SCHOOL_LABEL[g['school']]}\nn={g['n_per_draw']}" for g in gs], fontsize=7.5)
            ax.set_ylabel(ylab)
            ax.grid(axis='x', visible=False)
            ax.set_title(('Full-text dose >= 25%' if variant == 'ft25' else 'Abstract flagged') + ' vs not, 2023-2025, 1,000 equal-size draws per group', loc='left', fontsize=9)
    skipped = [g['school'] for g in f['groups'] if g['variant'] == 'ft25' and 'skipped' in g]
    fig.text(0.01, 0.01, 'Blue: not AI; orange: AI. Top row skips schools with fewer than 30 papers per draw: ' + (', '.join(SCHOOL_LABEL[s] for s in skipped) or 'none') + ' (see the abstract row).', color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, 'fig3_nine_schools.png')


def figures(fr):
    if (A.RES / 'umap.parquet').exists():
        fig_map(fr)
    if (A.OUT / 'lab_scatter.json.gz').exists():
        fig_lab_scatter()
    if (A.OUT / 'ai_use.json.gz').exists():
        fig_ai_use()
    if (A.OUT / 'matched_test.json').exists():
        fig_matched()
    if (A.OUT / 'event_study.json').exists():
        fig_event()
    if (A.OUT / 'fig3_nine_schools.json').exists():
        fig_fig3()
