"""Figures of the 12-school study (matplotlib; the py310 env). Palette and type follow ai-writing/diversity/study_figures.py. Series end at 2025; no 2026.
usage: study_figures.py [--id 2026-11-07]   -> <results>/figures/*.png
"""
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import study_common as C  # noqa: E402

BLUE, ORANGE, GREEN, AMBER, PINK, PURPLE = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#8a5cc2'
INK, INK2, MUTED, GRID, SURF = '#1d2a33', '#46525a', '#68747c', '#e3e5e0', '#fcfcfb'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.facecolor': SURF, 'figure.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.grid': True,
                     'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.titlecolor': INK, 'legend.labelcolor': INK2, 'axes.spines.top': False,
                     'axes.spines.right': False})


def line(ax, d, color, label, scale=1.0):
    d = d[d.year <= C.LAST]
    ax.plot(d.year, scale * d.est, color=color, lw=1.6, label=label, marker='o', ms=3)
    ax.fill_between(d.year, scale * d.lo, scale * d.hi, color=color, alpha=0.18, lw=0)


def chatgpt(ax):
    ax.axvline(2022.92, color=MUTED, lw=0.8, ls=':')
    ax.set_xticks(range(2016, 2026, 1)); ax.set_xticklabels([str(y)[2:] for y in range(2016, 2026)])


def fig_ai(T, out):
    s = pd.read_csv(T / 'ai_series.csv')
    f = s[(s.scope == 'ALL') & (s['sample'] == 'all')]
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.1))
    for m, c, lab in (('heavy_main', BLUE, 'main body'), ('heavy_main_appendix', ORANGE, 'main body + appendix')):
        line(ax[0], f[f.measure == m], c, lab, 100)
    ax[0].set_title('Papers with at least 25% of passages flagged (%)'); ax[0].legend(frameon=False)
    for m, c, lab in (('dose_main', BLUE, 'flagged passage share, full text'), ('abs_flag', GREEN, 'abstract flag (v1)')):
        line(ax[1], f[f.measure == m], c, lab, 100)
    ax[1].set_title('Mean AI share (%)'); ax[1].legend(frameon=False)
    for sc in C.SCHOOLS[:9]:
        d = s[(s.scope == sc) & (s['sample'] == 'all') & (s.measure == 'heavy_main')]
        ax[2].plot(d.year, 100 * d.est, lw=1, label=sc)
    ax[2].set_title('Heavy share by school (%)'); ax[2].legend(frameon=False, fontsize=6.5, ncol=2)
    for a in ax:
        chatgpt(a)
    fig.tight_layout(); fig.savefig(out / 'fig1_ai_share.png', dpi=170); plt.close(fig)


def fig_embed(T, out):
    s = pd.read_csv(T / 'embed_series.csv')
    f = s[(s.model == C.HEADLINE_MODEL) & (s.variant == 'raw') & (s.scope == 'ALL') & (s['sample'] == 'all')]
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.0))
    for a, lv, c, t in zip(ax, ('within_lab', 'cross_lab_same_school', 'cross_school'), (BLUE, ORANGE, GREEN),
                           ('Within lab', 'Across labs, same school', 'Across schools')):
        line(a, f[f.level == lv], c, t); a.set_title(t + ': mean pairwise distance'); chatgpt(a)
    fig.tight_layout(); fig.savefig(out / 'fig2_embedding_diversity.png', dpi=170); plt.close(fig)


def forest(ax, d, labels, title):
    y = np.arange(len(d))[::-1]
    ax.errorbar(d.est, y, xerr=[d.est - d.lo, d.hi - d.est], fmt='o', color=BLUE, ms=4, lw=1.2, capsize=2)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_title(title)


def fig_models(T, out):
    c = pd.read_csv(T / 'embed_contrasts.csv')
    c = c[(c.scope == 'ALL') & (c['sample'] == 'all') & (c.variant == 'raw')]
    fig, ax = plt.subplots(1, 3, figsize=(11, 3.2))
    for a, lv in zip(ax, ('within_lab', 'cross_lab_same_school', 'cross_school')):
        d = c[(c.level == lv) & (c.contrast == 'post_minus_pre')]
        forest(a, d, d.model, lv.replace('_', ' ') + ': post minus pre')
    fig.tight_layout(); fig.savefig(out / 'fig3_embedding_models.png', dpi=170); plt.close(fig)


def fig_schools(T, out):
    c = pd.read_csv(T / 'embed_contrasts.csv')
    c = c[(c.model == C.HEADLINE_MODEL) & (c.variant == 'raw') & (c.level == 'within_lab') & (c['sample'] == 'all') & (c.contrast == 'post_minus_pre')]
    a = pd.read_csv(T / 'ai_contrasts.csv')
    a = a[(a.measure == 'heavy_main') & (a['sample'] == 'all') & (a.contrast == 'post_minus_pre')]
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    for a_, d, t in ((ax[0], a, 'Heavy-AI paper share, post minus pre'), (ax[1], c, 'Within-lab distance (SPECTER2), post minus pre')):
        d = d[d.scope.isin(['ALL', 'EXCL_PARTIAL'] + C.SCHOOLS)].set_index('scope').reindex(['ALL', 'EXCL_PARTIAL'] + C.SCHOOLS).dropna(subset=['est']).reset_index()
        forest(a_, d, d.scope, t)
    fig.tight_layout(); fig.savefig(out / 'fig4_by_school.png', dpi=170); plt.close(fig)


def fig_topics_cit(T, out):
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.0))
    s = pd.read_csv(T / 'topics_llm_series.csv'); f = s[(s.scope == 'ALL') & (s['sample'] == 'all')]
    line(ax[0], f, BLUE, 'LLM-topic share', 100); ax[0].set_title('Papers on LLM topics (%)')
    s = pd.read_csv(T / 'topics_entropy_series.csv'); f = s[(s.scope == 'ALL') & (s['sample'] == 'all')]
    line(ax[1], f, ORANGE, 'entropy'); ax[1].set_title('Within-lab topic entropy (bits, 8 papers)')
    s = pd.read_csv(T / 'citation_series.csv'); f = s[(s.scope == 'ALL') & (s['sample'] == 'all') & (s.measure == 'cit_z_med')]
    line(ax[2], f, GREEN, 'Uzzi z'); ax[2].set_title('Median Uzzi z (lower = more conventional)')
    for a in ax:
        chatgpt(a)
    fig.tight_layout(); fig.savefig(out / 'fig5_topics_citations.png', dpi=170); plt.close(fig)


def fig_event(T, out):
    r = pd.read_csv(T / 'event_results.csv')
    r = r[(r.kind == 'event') & (r['sample'] == 'all')]
    outs = list(r.outcome.unique())
    fig, ax = plt.subplots(1, len(outs), figsize=(3.6 * len(outs), 3.0), squeeze=False)
    for a, o in zip(ax[0], outs):
        d = r[r.outcome == o].sort_values('e')
        a.errorbar(d.e, d.est, yerr=[d.est - d.lo, d.hi - d.est], fmt='o', color=BLUE, ms=4, lw=1.1, capsize=2)
        a.axhline(0, color=MUTED, lw=0.8); a.axvline(-0.5, color=MUTED, ls=':', lw=0.8); a.set_title(o); a.set_xlabel('years from adoption')
    fig.tight_layout(); fig.savefig(out / 'fig6_event_study.png', dpi=170); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--id', default='2026-11-07'); a = ap.parse_args()
    res = C.results_dir(a.id); T = res / 'tables'; out = res / 'figures'; out.mkdir(exist_ok=True)
    for fn in (fig_ai, fig_embed, fig_models, fig_schools, fig_topics_cit, fig_event):
        try:
            fn(T, out); print(fn.__name__, 'ok')
        except FileNotFoundError as e:
            print(fn.__name__, 'skipped', e.filename)


if __name__ == '__main__':
    main()
