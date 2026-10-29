"""Figures for the citation analysis, in the diversity battery's style (diversity/figures.py: light surface, recessive
grid, one axis per panel; C_LESS blue / C_MORE orange; grey for the before-ChatGPT baseline).

citations_main.png        A  a distribution-over-citables measure by period x AI group (equal-size draws)
                          B  the same against binned AI dose, 2023-2026 (year mix matched) and 2016-2022 (false-positive dose)
                          C  AI-flagged share of citations to cited works by cited year, published vs preprint-only, with the 2016-2021
                             floor: the full-text passage detector (q2v2.py) when its results exist, else the v1 abstract detector (q2.py)
                          D  within-lab contrasts: flagged vs not flagged papers of the same lab and year (per-paper
                             measures, lab x year fixed effects, standardized), with the 2016-2022 placebo
citations_measures_<src>.png  every pooled measure by period x AI group (oa = OpenAlex references, s2 = Semantic Scholar)
citations_spread_by_year.png  question 2: entropy / Gini over cited works and the spread of cited years by citing year (dist_by_year.py)
usage: figures.py [MEASURE_A]
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
RES, FIG = HERE / 'results', HERE / 'figures'
C_LESS, C_MORE, C_MID = '#2a78d6', '#eb6834', '#1baf7a'
INK, INK2, MUTED, GRID, SURF = '#1d2a33', '#46525a', '#68747c', '#e3e5e0', '#fcfcfb'
BASE = '#9aa1a6'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.facecolor': SURF, 'figure.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.grid': True,
                     'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.titlecolor': INK, 'legend.labelcolor': INK2, 'axes.spines.top': False,
                     'axes.spines.right': False})
GSTYLE = {'none': dict(c=C_LESS, m='o', label='no flagged passages (ai_share = 0)'),
          'some': dict(c=C_MID, m='s', label='some (0 < ai_share < 0.25)'),
          'flagged': dict(c=C_MORE, m='D', label='flagged (ai_share ≥ 0.25)')}
PER = ['base', '2023', '2024', '2025', '2026']
PER_LABEL = {'base': '2016–22', '2023': '2023', '2024': '2024', '2025': '2025', '2026': '2026'}
LABELS = {'H_work': 'entropy over cited works (nats, rarefied)', 'gini': 'Gini of cited-work counts (rarefied)',
          'distinct': 'distinct works per citation (rarefied)', 'H_venue': 'entropy over cited venues (nats)',
          'H_field': 'entropy over cited fields (nats)', 'H_subfield': 'entropy over cited subfields (nats)',
          'top1': 'share of citations to top-1% works (by year)', 'top1g': 'share to top-1% works (one global cut)',
          'logcbc': 'mean log(1 + cited_by_count)', 'logcbc_adj': 'age-adjusted log(1 + cited_by_count)',
          'age': 'mean reference age (years)', 'recent': 'share of references ≤ 2 years old', 'preprint': 'share preprint-only',
          'preprint_strict': 'share preprint-only (strict rule)', 'preprint_s2': 'share preprint-only (S2-corrected)',
          'nrefs': 'references per paper', 'canon': 'canonicality: log(1 + other same-year lab papers citing)',
          'H_work_full': 'entropy over cited works (all citations of the draw)', 'distinct_full': 'distinct works per citation (unrarefied)'}
PP = {'log_nrefs': 'log reference count', 'logcbc_adj': 'age-adjusted log citations of refs', 'top1': 'share of refs in top 1% (by year)',
      'canon': 'canonicality of refs', 'preprint': 'share of refs preprint-only', 'age': 'mean reference age', 'recent': 'share of refs ≤ 2 years old',
      'venue_div': 'distinct venues per reference', 'field_div': 'distinct subfields per reference',
      'year_sd': 'SD of cited publication years', 'lc_sd': 'SD of refs’ age-adj. log citations'}


def period_panel(ax, cells, m, title=True):
    x0 = np.arange(len(PER))
    for j, g in enumerate(GSTYLE):
        xs, ys, lo, hi = [], [], [], []
        for i, p in enumerate(PER):
            r = cells[(cells.family == 'year_group') & (cells.cell == f'{p}|{g}') & (cells.measure == m)]
            if len(r):
                r = r.iloc[0]; xs.append(x0[i] + (j - 1) * 0.2); ys.append(r['mean']); lo.append(r['lo']); hi.append(r['hi'])
        st = GSTYLE[g]
        ax.vlines(xs, lo, hi, color=st['c'], lw=1.6, zorder=2)
        ax.plot(xs, ys, ls='', marker=st['m'], ms=6.5 if st['m'] != 'D' else 5.6, mfc=st['c'], mec=SURF, mew=1.2, zorder=3)
    ax.set_xticks(x0); ax.set_xticklabels([PER_LABEL[p] for p in PER])
    ax.axvspan(-0.5, 0.5, color=GRID, alpha=0.35, lw=0, zorder=0)
    ax.set_xlim(-0.5, len(PER) - 0.5)
    if title:
        ax.set_title(LABELS.get(m, m), loc='left', fontsize=8.6)


def dose_panel(ax, cells, m):
    for fam, col, mk, lab in (('dose_base', BASE, 'o', '2016–22 (flags are false positives)'), ('dose_post', INK, 'o', '2023–26')):
        d = cells[(cells.family == fam) & (cells.measure == m)]
        order = ['0', '0–5%', '5–10%', '10–25%', '25–50%', '≥50%']
        d = d.set_index('cell').reindex([o for o in order if o in set(d.cell)])
        x = np.array([order.index(c) for c in d.index]) + (-0.12 if fam == 'dose_base' else 0.12)
        ax.vlines(x, d['lo'], d['hi'], color=col, lw=1.6, zorder=2)
        ax.plot(x, d['mean'], color=col, lw=1.2, alpha=0.6, zorder=2)
        ax.plot(x, d['mean'], ls='', marker=mk, ms=6, mfc=col, mec=SURF, mew=1.2, zorder=3, label=lab)
    ax.set_xticks(range(6)); ax.set_xticklabels(['0', '0–5', '5–10', '10–25', '25–50', '≥50'])
    ax.axvline(3.5, color=MUTED, lw=0.8, ls=(0, (3, 3)), zorder=1)
    ax.text(3.55, 1.0, 'flag cut', transform=ax.get_xaxis_transform(), ha='left', va='top', fontsize=7, color=MUTED)
    ax.set_xlabel('share of the paper’s passages flagged as AI-written (%)', fontsize=7.8)
    ax.legend(loc='best', frameon=False, fontsize=7.2)


def q2_panel(ax, Q, thr='v1'):
    q = Q[Q.threshold == thr]
    years = ['2016–2021', '2022', '2023', '2024', '2025', '2026']
    for cls, col, mk, off, lab in (('published', INK, 'o', -0.1, 'published (journal / conference version)'),
                                   ('preprint', C_MID, 's', 0.1, 'preprint only (repository / arXiv)')):
        d = q[q.cls == cls].set_index('cited_year').reindex(years)
        x = np.arange(len(years)) + off
        ax.vlines(x, 100 * d['lo'], 100 * d['hi'], color=col, lw=1.6, zorder=2)
        ax.plot(x, 100 * d['share'], ls='', marker=mk, ms=6.2, mfc=col if cls == 'published' else SURF, mec=col, mew=1.4, zorder=3, label=lab)
        fl = d.loc['2016–2021', 'share']
        ax.axhline(100 * fl, color=col, lw=0.8, ls=(0, (3, 3)), zorder=1)
        for xi, (yy, r) in zip(x, d.iterrows()):
            if yy != '2016–2021' and np.isfinite(r['works']):
                pass
    ax.axvspan(-0.5, 0.5, color=GRID, alpha=0.35, lw=0, zorder=0)
    ax.set_xticks(range(len(years))); ax.set_xticklabels(['2016–21\n(floor)', '2022', '2023', '2024', '2025', '2026'])
    ax.set_xlim(-0.5, len(years) - 0.5)
    ax.set_ylabel('cited works flagged AI-written (%)', fontsize=7.8)
    ax.set_xlabel('publication year of the cited work', fontsize=7.8)
    ax.legend(loc='upper left', frameon=False, fontsize=7.2)


def q2v2_panel(ax, R):
    """Full-text passage detector (q2v2.py): share of citations going to AI-flagged cited works, per cited-year stratum.
    Points = the open-full-text PPS sample (Wilson 95%); crosses = sample combined with the corpus's own lab papers."""
    years = ['2016-2021', '2023', '2024', '2025', '2026']
    for cls, col, mk, off, lab in (('published', INK, 'o', -0.1, 'published (journal / conference version)'),
                                   ('preprint', C_MID, 's', 0.1, 'preprint only (repository / arXiv)')):
        d = R[R.stratum.str.endswith('|' + cls)].assign(y=lambda t: t.stratum.str.split('|').str[0]).set_index('y').reindex(years)
        x = np.arange(len(years)) + off
        ax.vlines(x, 100 * d['lo'], 100 * d['hi'], color=col, lw=1.6, zorder=2)
        ax.plot(x, 100 * d['sample_share'], ls='', marker=mk, ms=6.2, mfc=col if cls == 'published' else SURF, mec=col, mew=1.4, zorder=3, label=lab)
        ax.plot(x, 100 * d['combined_share'], ls='', marker='x', ms=5, color=col, zorder=3)
        ax.axhline(100 * d.loc['2016-2021', 'sample_share'], color=col, lw=0.8, ls=(0, (3, 3)), zorder=1)
    ax.plot([], [], ls='', marker='x', color=MUTED, label='with the corpus’s own lab papers')
    ax.axvspan(-0.5, 0.5, color=GRID, alpha=0.35, lw=0, zorder=0)
    ax.set_xticks(range(len(years))); ax.set_xticklabels(['2016–21\n(floor)', '2023', '2024', '2025', '2026'])
    ax.set_xlim(-0.5, len(years) - 0.5)
    ax.set_ylabel('citations to AI-flagged works (%)', fontsize=7.8)
    ax.set_xlabel('publication year of the cited work', fontsize=7.8)
    ax.legend(loc='upper left', frameon=False, fontsize=7.0)


def within_panel(ax, Wl):
    ms = [m for m in PP if m in set(Wl.measure)]
    y = np.arange(len(ms))[::-1]
    for spec, col, mfc, off, lab in (('post_flag', INK, INK, 0.14, '2023–26: flagged vs not, same lab and year'),
                                     ('base_dose', BASE, SURF, -0.14, '2016–22 placebo: +10 pts false-positive dose')):
        d = Wl[Wl.spec == spec].set_index('measure').reindex(ms)
        b, lo, hi = d.beta / d.sd_y, d.lo / d.sd_y, d.hi / d.sd_y
        ax.hlines(y + off, lo, hi, color=col, lw=1.6, zorder=2)
        ax.plot(b, y + off, ls='', marker='o', ms=6, mfc=mfc, mec=col, mew=1.4, zorder=3, label=lab)
    ax.axvline(0, color=MUTED, lw=0.8, zorder=1)
    ax.set_yticks(y); ax.set_yticklabels([PP[m] for m in ms], fontsize=7.6)
    ax.grid(axis='y', visible=False)
    ax.set_xlabel('difference in SD units (lab × year fixed effects, 95% lab-bootstrap CI)', fontsize=7.4)
    ax.legend(loc='upper left', bbox_to_anchor=(-0.02, -0.15), ncol=1, frameon=False, fontsize=7.0)


def group_legend(fig, y):
    h = [Line2D([], [], marker=s['m'], ls='', ms=6, mfc=s['c'], mec=SURF, label=s['label']) for s in GSTYLE.values()]
    fig.legend(handles=h, loc='upper right', bbox_to_anchor=(0.995, y), ncol=3, frameon=False, fontsize=7.6, handletextpad=0.2, columnspacing=1.0)


def main_figure(mA):
    cells = pd.read_csv(RES / 'oa_cells.csv')
    Q = pd.read_csv(RES / 'q2_by_cited_year.csv') if (RES / 'q2_by_cited_year.csv').exists() else None
    Wl = pd.read_csv(RES / 'within_lab.csv')
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.6))
    a, b, c, d = axes.flat
    period_panel(a, cells, mA, title=False)
    a.set_title(f'A  {LABELS[mA]}, by year and AI group', loc='left', fontsize=9)
    a.set_xlabel('publication year of the citing lab paper', fontsize=7.8)
    dose_panel(b, cells, mA)
    b.set_title(f'B  the same against the paper’s AI dose', loc='left', fontsize=9)
    if (RES / 'q2v2_strata.csv').exists():
        q2v2_panel(c, pd.read_csv(RES / 'q2v2_strata.csv'))
        c.set_title('C  how many cited works are themselves AI-written (full-text detector)', loc='left', fontsize=9)
    elif Q is not None:
        q2_panel(c, Q)
        c.set_title('C  how many of the cited works are themselves AI-written (abstract detector)', loc='left', fontsize=9)
    within_panel(d, Wl)
    d.set_title('D  within lab: flagged vs not, same lab and year', loc='left', fontsize=9)
    H = fig.get_figheight()
    fig.text(0.01, 1 - 0.1 / H, 'What AI-written lab papers cite', ha='left', va='top', fontsize=10.5, color=INK)
    fig.text(0.01, 1 - 0.34 / H, 'OpenAlex reference lists of paragraph-scored lab papers (≥ 5 references). A–B: 1,000 equal-size draws of '
             'citing papers per cell, 95% draw intervals (a cell drawn whole has none).\nC: citation-weighted open-full-text sample, Wilson 95%; '
             'dashed = 2016–21 floor per class.', ha='left', va='top', fontsize=7.4, color=MUTED)
    group_legend(fig, 1 - 0.72 / H)
    fig.subplots_adjust(left=0.065, right=0.99, top=1 - 1.15 / H, bottom=0.15, hspace=0.42, wspace=0.42)
    d.set_position([d.get_position().x0 + 0.06, d.get_position().y0, d.get_position().width - 0.06, d.get_position().height])
    fig.savefig(FIG / 'citations_main.png', dpi=170); plt.close(fig)


def spread_figure():
    """Question 2: the distribution over cited works by citing year (dist_by_year.py), all papers and flagged vs not, both sources."""
    ms = [('H_work', 'entropy over cited works (nats, 900 citations)'), ('gini', 'Gini of cited-work counts'),
          ('iqr_year', 'IQR of cited publication years (pooled)'), ('pp_year_sd', 'per-paper SD of cited years')]
    srcs = [s for s in ('s2', 'oa') if (RES / f'dist_by_year_{s}.csv').exists()]
    if not srcs:
        return
    fig, axes = plt.subplots(len(srcs), len(ms), figsize=(12.4, 3.0 * len(srcs) + 0.9), squeeze=False)
    sty = {'all': (MUTED, 'o', 'all lab papers'), 'not': (C_LESS, 'o', 'not flagged'), 'flagged': (C_MORE, 'D', 'AI-flagged (ai_share ≥ 0.25)')}
    for i, src in enumerate(srcs):
        R = pd.read_csv(RES / f'dist_by_year_{src}.csv')
        R = R[R.year <= 2025]
        for j, (m, lab) in enumerate(ms):
            ax = axes[i, j]
            for g, off in (('all', -0.15), ('not', 0.0), ('flagged', 0.15)):
                d = R[(R.group == g) & (R.measure == m)].sort_values('year')
                c, mk, _ = sty[g]
                ax.vlines(d.year + off, d.lo, d.hi, color=c, lw=1.3, zorder=2)
                ax.plot(d.year + off, d['mean'], ls='-' if g == 'all' else '', lw=0.9, marker=mk, ms=4.6, color=c, mec=SURF, mew=0.8, zorder=3)
            ax.axvspan(2015.5, 2022.5, color=GRID, alpha=0.35, lw=0, zorder=0)
            ax.set_xticks(range(2016, 2026, 2)); ax.tick_params(labelsize=7.2)
            ax.set_title(f"{lab}\n{'Semantic Scholar' if src == 's2' else 'OpenAlex'} references", loc='left', fontsize=7.8)
    h = [Line2D([], [], marker=v[1], ls='', ms=6, mfc=v[0], mec=SURF, label=v[2]) for v in sty.values()]
    H = fig.get_figheight()
    fig.text(0.01, 1 - 0.1 / H, 'Is the distribution over cited works narrowing? (60 citing papers per draw, 500 draws, 95% draw intervals; '
             'per-paper SD: bootstrap over papers)', ha='left', va='top', fontsize=9.5, color=INK)
    fig.legend(handles=h, loc='upper right', bbox_to_anchor=(0.995, 1 - 0.32 / H), ncol=3, frameon=False, fontsize=7.6)
    fig.subplots_adjust(left=0.05, right=0.99, top=1 - 1.05 / H, bottom=0.06, hspace=0.55, wspace=0.28)
    fig.savefig(FIG / 'citations_spread_by_year.png', dpi=160); plt.close(fig)


def measures_figure(src):
    f = RES / f'{src}_cells.csv'
    if not f.exists():
        return
    cells = pd.read_csv(f)
    ms = [m for m in LABELS if m in set(cells[cells.family == 'year_group'].measure) and cells[(cells.family == 'year_group') & (cells.measure == m)]['mean'].notna().any()]
    nc = 4; nr = int(np.ceil(len(ms) / nc))
    fig, axes = plt.subplots(nr, nc, figsize=(3.0 * nc, 2.35 * nr + 1.0), squeeze=False)
    for ax, m in zip(axes.flat, ms):
        period_panel(ax, cells, m); ax.tick_params(labelsize=7.2); ax.title.set_fontsize(7.6)
    for ax in axes.flat[len(ms):]:
        ax.set_visible(False)
    H = fig.get_figheight()
    name = {'oa': 'OpenAlex', 's2': 'Semantic Scholar'}[src]
    fig.text(0.01, 1 - 0.1 / H, f'Every reference measure by year and AI group ({name} reference lists)', ha='left', va='top', fontsize=10, color=INK)
    fig.text(0.01, 1 - 0.32 / H, '1,000 equal-size draws of citing papers per cell; 95% draw intervals; grey band = before ChatGPT.', ha='left',
             va='top', fontsize=7.4, color=MUTED)
    group_legend(fig, 1 - 0.5 / H)
    fig.subplots_adjust(left=0.05, right=0.99, top=1 - 0.95 / H, bottom=0.04, hspace=0.55, wspace=0.3)
    fig.savefig(FIG / f'citations_measures_{src}.png', dpi=150); plt.close(fig)


if __name__ == '__main__':
    FIG.mkdir(exist_ok=True)
    main_figure(sys.argv[1] if len(sys.argv) > 1 else 'canon')
    for s in ('oa', 's2'):
        measures_figure(s)
    spread_figure()
