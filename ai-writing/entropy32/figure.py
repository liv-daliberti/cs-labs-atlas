"""The AI dose x knowledge entropy figure (analyze.py figure). Palette: the dataviz reference instance (light surface), sequential blue for the
AI share, categorical slot 1 (blue) for the adjusted curve, muted ink for the raw one.

A  t-SNE of 2023-2025 papers (cosine), papers with no flagged passage in muted gray, the rest on the sequential ramp by AI share (heaviest on top)
B  knowledge entropy against the AI share, euclidean (default geometry); C the same, cosine. Window medians with 95% draw bands; the 0% papers as a point
D  labs: change in knowledge entropy 2016-22 -> 2023-25 against the lab's mean AI share after, with binned means
E  per school: paper-level topic surprisal slope per +10 points of AI share (school x year + lab FE), both geometries
"""
import json

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

SURF, INK, INK2, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8984', '#e4e3df'
BLUE, ORANGE, ZERO = '#2a78d6', '#eb6834', '#cfcdc6'
SEQ = LinearSegmentedColormap.from_list('seq', ['#b7d3f6', '#6da7ec', '#2a78d6', '#1c5cab', '#0d366b'])
NAME = {'euclidean': 'Euclidean (default)', 'cosine': 'Cosine'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.facecolor': SURF, 'figure.facecolor': SURF, 'axes.grid': True, 'grid.color': GRID,
                     'grid.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.titlelocation': 'left',
                     'axes.titlesize': 10, 'axes.titlecolor': INK, 'axes.titleweight': 'bold'})


def sq(x):
    return np.sqrt(np.clip(x, 0, None))


def curve_panel(ax, cur, metric, what='entropy'):
    c = cur[cur.metric == metric]
    for mode, col, lw, ls, lab in (('raw', MUTED, 1.4, (0, (3, 2)), 'unadjusted'), ('adjusted', BLUE, 2.0, '-', 'school × year adjusted')):
        d = c[(c['mode'] == mode) & (c.window != 'zero')].sort_values('dose_median')
        x = sq(d.dose_median * 100)
        if mode == 'adjusted':
            ax.fill_between(x, d[f'{what}_lo'], d[f'{what}_hi'], color=col, alpha=0.16, lw=0)
        ax.plot(x, d[what], color=col, lw=lw, ls=ls, label=lab, solid_capstyle='round')
        z = c[(c['mode'] == mode) & (c.window == 'zero')].iloc[0]
        ax.errorbar([0], [z[what]], yerr=[[z[what] - z[f'{what}_lo']], [z[f'{what}_hi'] - z[what]]], fmt='o', ms=7 if mode == 'adjusted' else 5,
                    color=col, mec=SURF, mew=2, capsize=0, elinewidth=2, zorder=5)
    ticks = [0, 1, 5, 10, 25, 50, 75, 100]
    ax.set_xticks(sq(np.array(ticks))); ax.set_xticklabels([f'{t}%' for t in ticks])
    ax.set_xlim(-0.4, sq(100) + 0.2)
    ax.set_xlabel('AI-written share of the main body (detector v3, √ scale)')
    ax.grid(axis='x', visible=False)


def main(w):
    a = w / 'analysis'
    out = w / 'figures'
    out.mkdir(exist_ok=True)
    cur = pd.read_csv(a / 'curve.csv')
    mp = pd.read_parquet(a / 'map.parquet')
    paper = json.loads((a / 'paper.json').read_text())
    lab = json.loads((a / 'lab.json').read_text())
    run = json.loads((w / 'RUN.json').read_text())
    n_sch = int(pd.read_parquet(w / 'papers_scored.parquet', columns=['home_school', 'has_emb']).query('has_emb').home_school.nunique())

    fig = plt.figure(figsize=(17, 10.2))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.25, 1, 1], height_ratios=[1, 1], wspace=0.24, hspace=0.36, left=0.03, right=0.985, top=0.885, bottom=0.085)
    fig.text(0.03, 0.965, 'More AI-written text, narrower knowledge?', fontsize=17, fontweight='bold', color=INK)
    n_post = int(cur[(cur.metric == 'euclidean') & (cur['mode'] == 'raw')].n_papers.sum() - 0)
    fig.text(0.03, 0.93, f'Lab papers of 2023–2025 at {n_sch} schools with a stored full text. Knowledge entropy as in our Hao et al. Fig. 3 replication: '
             f'SPECTER2 full-text vectors, 50 k-means topic clusters, entropy of equal-size draws ({int(cur.n_draw.iloc[0]):,} papers each).',
             fontsize=9.5, color=INK2)

    # A map
    ax = fig.add_subplot(gs[:, 0])
    z = mp[mp.ai == 0]; p = mp[mp.ai > 0].sort_values('ai')
    ax.scatter(z.x, z.y, s=1.6, c=ZERO, lw=0, rasterized=True)
    sc = ax.scatter(p.x, p.y, s=2.2 + 10 * p.ai, c=p.ai * 100, cmap=SEQ, vmin=0, vmax=60, lw=0, rasterized=True)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(f'A  The 2023–2025 papers in SPECTER2 space (t-SNE, {len(mp):,} papers)')
    cb = fig.colorbar(sc, ax=ax, orientation='horizontal', fraction=0.035, pad=0.01, aspect=40, extend='max')
    cb.set_label('AI-written share of the main body (%) · gray: no flagged passage', color=INK2); cb.outline.set_visible(False)
    cb.ax.tick_params(colors=MUTED)

    # B, C curves
    for j, metric in enumerate(('euclidean', 'cosine')):
        ax = fig.add_subplot(gs[0, 1 + j])
        curve_panel(ax, cur, metric)
        ax.set_ylabel('knowledge entropy (nats, 50 clusters)')
        ax.set_title(f'{"BC"[j]}  Knowledge entropy vs AI share · {NAME[metric]}')
        pj = paper[metric]
        ax.text(0.98, 0.04, f'paper level, +10 pts AI → topic surprisal {pj["slope_per_10pts_school_year_lab_fe"]:+.3f}\n'
                f'[{pj["ci"][0]:+.3f}, {pj["ci"][1]:+.3f}] nats (school×year + lab FE)', transform=ax.transAxes, ha='right', va='bottom', fontsize=8, color=INK2)
        if j == 0:
            ax.legend(loc='upper right', frameon=False, fontsize=8)

    # D labs
    ax = fig.add_subplot(gs[1, 1])
    L = pd.read_csv(a / 'labs_euclidean.csv')
    ax.scatter(L.ai_post * 100, L.dh, s=9, color=BLUE, alpha=0.28, lw=0)
    q = pd.qcut(L.ai_post, 10, duplicates='drop')
    B = L.groupby(q, observed=True).agg(x=('ai_post', 'mean'), y=('dh', 'mean'), se=('dh', lambda v: v.std() / np.sqrt(len(v))))
    ax.errorbar(B.x * 100, B.y, yerr=1.96 * B.se, color=INK, marker='o', ms=6, mec=SURF, mew=1.5, lw=1.6, capsize=0, zorder=5, label='decile means, 95% CI')
    ax.axhline(0, color=MUTED, lw=1)
    lj = lab['euclidean']
    ax.set_title('D  Labs: entropy change vs their AI share')
    ax.set_xlabel('lab mean AI-written share, 2023–2025 (%)'); ax.set_ylabel('Δ knowledge entropy, 2016–22 → 2023–25 (nats)')
    ax.text(0.98, 0.96, f'{lj["labs"]:,} labs · slope {lj["slope_dh_per_10pts"]:+.3f} per +10 pts\n[{lj["boot_ci"][0]:+.3f}, {lj["boot_ci"][1]:+.3f}] (school FE, lab bootstrap)',
            transform=ax.transAxes, ha='right', va='top', fontsize=8, color=INK2)
    ax.legend(loc='lower left', frameon=False, fontsize=8)

    # E schools
    ax = fig.add_subplot(gs[1, 2])
    S = {m: pd.read_csv(a / f'school_slopes_{m}.csv').set_index('school') for m in ('euclidean', 'cosine')}
    order = S['euclidean'].sort_values('slope').index.tolist()
    y = np.arange(len(order))
    for off, m, col in ((-0.17, 'euclidean', BLUE), (0.17, 'cosine', ORANGE)):
        d = S[m].reindex(order)
        ax.errorbar(d.slope, y + off, xerr=[d.slope - d.lo, d.hi - d.slope], fmt='o', ms=4.5, color=col, elinewidth=1.4, capsize=0, label=NAME[m])
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(y); ax.set_yticklabels(order, fontsize=7.5); ax.grid(axis='y', visible=False)
    ax.set_xlabel('topic surprisal per +10 pts AI share (nats); < 0 = more crowded topics')
    ax.set_title('E  By school (school\'s own year + lab FE)')
    ax.legend(loc='lower right', frameon=False, fontsize=8)

    fig.text(0.03, 0.012, 'Detector v3 (≤0.3% false positives per passage; misses some light edits, so shares are lower bounds). Adjusted curves re-weight every AI-share window\n'
             'to the pooled school × year mix. Topic surprisal = −log share of the paper\'s cluster among all 2023–2025 papers; its group mean is the cross-entropy that bounds entropy.',
             fontsize=7.8, color=MUTED)
    fig.savefig(out / 'ai_dose_entropy.png', dpi=200); fig.savefig(out / 'ai_dose_entropy.pdf')
    plt.close(fig)

    # detail: entropy and extent, both geometries
    fig, axs = plt.subplots(2, 2, figsize=(12, 8.2))
    for j, metric in enumerate(('euclidean', 'cosine')):
        for i, what in enumerate(('entropy', 'extent')):
            curve_panel(axs[i, j], cur, metric, what)
            axs[i, j].set_title(f'{NAME[metric]} · knowledge {what}')
            axs[i, j].set_ylabel('entropy (nats)' if what == 'entropy' else ('max distance to centroid' if metric == 'euclidean' else '1 − min cosine to centroid'))
    axs[0, 0].legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(out / 'ai_dose_entropy_detail.png', dpi=180); plt.close(fig)
    print(json.dumps(dict(figures=[str(out / 'ai_dose_entropy.png'), str(out / 'ai_dose_entropy_detail.png')], schools=n_sch, run=run['id'])))
