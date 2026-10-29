"""Figures for the diversity battery (matplotlib, light surface #fcfcfb, recessive grid, one axis per panel).

lab_scatter_<family>.png   small multiples, one panel per measure: each lab's change (post 2023-2026 minus pre
                           2016-2022, equal-size draws) against its post-period AI usage, coloured by school, with the
                           Huber line and the standardized slope [95% CI] of the main specification
forest.png                 standardized slopes with 95% CIs: lab level (main, topic fixed effects, placebo breaks at 2019
                           and 2020, the band holding 95% of placebo |slopes|) and within lab (post, post with topic
                           fixed effects, pre-period placebo)
forest_by_school.png       the main lab-level slope per school beside the pooled one
fig3_fulltext.png          Hao et al. Fig. 3 B-D on full texts: post-2023 papers flagged vs not (current AI variable),
                           SPECTER2 full-text vectors (mean of segment vectors), t-SNE, knowledge extent and topic
                           entropy over 1,000 equal-size draws per group; Euclidean on the raw mean vectors
fig3_fulltext_cosine.png   the same figure in cosine geometry: extent = max cosine distance to the centre direction,
                           topic clusters by k-means on length-normalised vectors (spherical), t-SNE with the cosine metric.
                           Both also show lab entropy: the spread of a draw over PI labs (a paper of two labs counts 1/2 to each)
fig3_periods_<metric>.png  before vs after ChatGPT: t-SNE of the papers before only, after only (flagged vs not), all together;
                           extent, topic entropy and lab entropy for before / after not flagged / after flagged by school
flag_share_by_year.png     share flagged per school and year, abstract detector and (when present) paragraph detector
"""
import hashlib, json, pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import common as C
import measures as M
from analyze import LABELS, FAMILY, FAMILY_TITLE, WITHIN_LABELS, huber

C_LESS, C_MORE = '#2a78d6', '#eb6834'          # "less AI" / "more AI"
SCHOOL_C = dict(zip(C.SCHOOLS, ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#8a5cc2']))
INK, INK2, MUTED, GRID, SURF = '#1d2a33', '#46525a', '#68747c', '#e3e5e0', '#fcfcfb'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.facecolor': SURF, 'figure.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.grid': True,
                     'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.titlecolor': INK, 'legend.labelcolor': INK2, 'axes.spines.top': False,
                     'axes.spines.right': False})
rng = np.random.default_rng(C.SEED)


def school_legend(fig, y=0.995, extra=None):
    h = [Line2D([], [], marker='o', ls='', ms=6, mfc=SCHOOL_C[s], mec=SURF, label=C.LABEL[s]) for s in C.SCHOOLS]
    if extra:
        h += extra
    fig.legend(handles=h, loc='upper right', bbox_to_anchor=(0.995, y), ncol=len(h), frameon=False, fontsize=8, handletextpad=0.2, columnspacing=1.0)


def scatters(lw, S, ai_label):
    main = S[(S.school == 'all') & (S.spec == 'main')].set_index('measure')
    for fam in ('abs', 'ft', 'txt', 'ref'):
        ms = [m for m in LABELS if FAMILY[m] == fam and f'd_{m}' in lw and lw[f'd_{m}'].notna().sum() >= 20]
        if not ms:
            continue
        nc = 4 if len(ms) > 4 else len(ms)
        nr = int(np.ceil(len(ms) / nc))
        fig, axes = plt.subplots(nr, nc, figsize=(3.05 * nc, 2.6 * nr + 1.2), squeeze=False)
        for ax, m in zip(axes.flat, ms):
            d = lw.dropna(subset=[f'd_{m}', 'ai_post'])
            d = d[d.n_ai_post >= 5]
            x, y = 100 * d.ai_post.values, d[f'd_{m}'].values
            lo, hi = np.percentile(y, [1, 99])
            pad = 0.08 * (hi - lo)
            for s in C.SCHOOLS:
                q = d.school.values == s
                ax.scatter(x[q], y[q], s=11, c=SCHOOL_C[s], alpha=0.75, linewidths=0.4, edgecolors=SURF, zorder=2)
            b = huber(np.column_stack([np.ones(len(x)), x]), y)
            xx = np.linspace(0, np.percentile(x, 99), 50)
            ax.plot(xx, b[0] + b[1] * xx, color=INK, lw=1.6, zorder=3)
            ax.axhline(0, color=MUTED, lw=0.8, zorder=1)
            ax.set_ylim(lo - pad, hi + pad)
            ax.set_xlim(-2, max(5, np.percentile(x, 99.5)) + 2)
            ax.set_title(LABELS[m], loc='left', fontsize=8.8, pad=13)
            if m in main.index:
                r = main.loc[m]
                ax.text(0, 1.02, f'β = {r.beta:+.2f} [{r.lo:+.2f}, {r.hi:+.2f}], {int(r.n_labs)} labs', transform=ax.transAxes, ha='left', va='bottom',
                        fontsize=7.2, color=MUTED)
            ax.tick_params(labelsize=7.5)
        for ax in axes.flat[len(ms):]:
            ax.set_visible(False)
        for j in range(nc):  # the x label goes under the last visible panel of each column
            col = [ax for ax in axes[:, j] if ax.get_visible()]
            if col:
                col[-1].set_xlabel(f'post-period {ai_label} (%)', fontsize=7.8)
        for ax in axes[:, 0]:
            ax.set_ylabel('change, post − pre', fontsize=7.8)
        H = fig.get_figheight()
        fig.text(0.01, 1 - 0.12 / H, f'{FAMILY_TITLE[fam]}: change per lab against AI usage', ha='left', va='top', fontsize=10, color=INK)
        fig.text(0.01, 1 - 0.36 / H, 'One dot per lab; β is the standardized slope of the main specification (Huber, size and school controls, '
                 '95% bootstrap CI). Axes show the central 98% of labs.', ha='left', va='top', fontsize=7.5, color=MUTED)
        school_legend(fig, y=1 - 0.04 / H, extra=[Line2D([], [], color=INK, lw=1.6, label='Huber fit')])
        fig.subplots_adjust(left=0.065, right=0.99, top=1 - 0.95 / H, bottom=0.55 / H + 0.02, hspace=0.62, wspace=0.28)
        fig.savefig(C.FIG / f'lab_scatter_{fam}.png', dpi=170); plt.close(fig)


WITHIN_SHORT = {'dist_abs': 'centroid distance (abstract)', 'dist_ft': 'centroid distance (full text)'}

SPEC_STYLE = {
    'main': dict(marker='o', mfc=INK, mec=INK, color=INK, label='main (size, school controls)'),
    'topic': dict(marker='D', mfc=MUTED, mec=MUTED, color=MUTED, ms=4.2, label='+ topic fixed effects, Δ LLM-topic share'),
    'placebo2019': dict(marker='o', mfc=SURF, mec=MUTED, color=MUTED, label='placebo break 2019 (no ChatGPT)'),
    'placebo2020': dict(marker='s', mfc=SURF, mec=MUTED, color=MUTED, ms=4.2, label='placebo break 2020 (no ChatGPT)'),
    'post': dict(marker='o', mfc=INK, mec=INK, color=INK, label='2023–2026, lab × year fixed effects'),
    'post_topic': dict(marker='D', mfc=MUTED, mec=MUTED, color=MUTED, ms=4.2, label='+ topic fixed effects'),
    'pre_placebo': dict(marker='o', mfc=SURF, mec=MUTED, color=MUTED, label='2016–2022 (flags are false positives)'),
}


def forest(S, W, null95, ai_label):
    pooled = S[S.school == 'all']
    rows, ylab, sep = [], [], []
    y = 0
    for fam in ('abs', 'ft', 'txt', 'ref'):
        ms = [m for m in LABELS if FAMILY[m] == fam and m in set(pooled.measure)]
        if not ms:
            continue
        sep.append((y, FAMILY_TITLE[fam]))
        y += 1
        for m in ms:
            rows.append((y, m)); ylab.append((y, LABELS[m])); y += 1
        y += 0.4
    wo = [o for o in WITHIN_LABELS if o in set(W.outcome)] if len(W) else []
    h = max(6.0, 0.24 * y + 1.0)
    fig = plt.figure(figsize=(12.5, h))
    top, bot = 1 - 0.45 / h, 0.6 / h
    ax = fig.add_axes([0.205, bot, 0.42, top - bot])
    if null95:
        ax.axvspan(-null95, null95, color=GRID, alpha=0.6, lw=0, zorder=0)
    ax.axvline(0, color=MUTED, lw=0.9, zorder=1)
    offs = {'main': -0.27, 'topic': -0.09, 'placebo2019': 0.09, 'placebo2020': 0.27}
    for spec, off in offs.items():
        st = SPEC_STYLE[spec]
        for yy, m in rows:
            r = pooled[(pooled.measure == m) & (pooled.spec == spec)]
            if not len(r):
                continue
            r = r.iloc[0]
            ax.plot([r.lo, r.hi], [yy + off] * 2, color=st['color'], lw=1.3, solid_capstyle='round', zorder=2)
            ax.plot([r.beta], [yy + off], marker=st['marker'], ms=st.get('ms', 4.8), mfc=st['mfc'], mec=st['mec'], mew=1.1, ls='', zorder=3)
    ax.set_yticks([yy for yy, _ in ylab]); ax.set_yticklabels([t for _, t in ylab], fontsize=8, color=INK2)
    for yy, t in sep:
        ax.text(-0.01, yy, t, transform=ax.get_yaxis_transform(), ha='right', va='center', fontsize=8.6, color=INK, fontweight='bold')
    ax.set_ylim(y - 0.2, -0.8); ax.grid(axis='y', visible=False)
    ax.set_xlabel(f'standardized slope: SD of change per SD of post-period {ai_label}')
    ax.set_title('Lab level: change post − pre against AI usage (Huber, 95% bootstrap CI)', loc='left', fontsize=9.5)
    hs = [Line2D([], [], marker=SPEC_STYLE[s]['marker'], ms=5, mfc=SPEC_STYLE[s]['mfc'], mec=SPEC_STYLE[s]['mec'], color=SPEC_STYLE[s]['color'], lw=1.2,
                 label=SPEC_STYLE[s]['label']) for s in offs]
    if null95:
        hs.append(plt.Rectangle((0, 0), 1, 1, fc=GRID, ec='none', label=f'95% of placebo |slopes| (±{null95:.2f})'))
    fig.legend(handles=hs, loc='upper left', bbox_to_anchor=(0.645, top + 0.01), frameon=False, fontsize=7.8, title='Lab level', title_fontsize=8.2,
               alignment='left')
    if wo:
        unit = (top - bot) / (y + 1.0)
        hh = unit * (len(wo) + 0.6) * 1.35
        t2 = top - 0.25
        ax2 = fig.add_axes([0.8, t2 - hh, 0.185, hh])
        ax2.axvline(0, color=MUTED, lw=0.9)
        offs2 = {'post': -0.22, 'post_topic': 0.0, 'pre_placebo': 0.22}
        for spec, off in offs2.items():
            st = SPEC_STYLE[spec]
            for i, o in enumerate(wo):
                r = W[(W.outcome == o) & (W.spec == spec) & (W.x == 'flag')]
                if not len(r):
                    continue
                r = r.iloc[0]
                ax2.plot([r.lo, r.hi], [i + off] * 2, color=st['color'], lw=1.3, zorder=2)
                ax2.plot([r.beta], [i + off], marker=st['marker'], ms=st.get('ms', 4.8), mfc=st['mfc'], mec=st['mec'], mew=1.1, ls='', zorder=3)
        ax2.set_yticks(range(len(wo))); ax2.set_yticklabels([WITHIN_SHORT.get(o, WITHIN_LABELS[o]) for o in wo], fontsize=7.8, color=INK2)
        ax2.set_ylim(len(wo) - 0.5, -0.6); ax2.grid(axis='y', visible=False)
        ax2.set_xlabel('flagged − not flagged (SD), same lab and year', fontsize=7.8)
        ax2.set_title('Within lab: papers with more vs less AI', loc='left', fontsize=9.5, x=-0.75)
        hs2 = [Line2D([], [], marker=SPEC_STYLE[s]['marker'], ms=5, mfc=SPEC_STYLE[s]['mfc'], mec=SPEC_STYLE[s]['mec'], color=SPEC_STYLE[s]['color'], lw=1.2,
                      label=SPEC_STYLE[s]['label']) for s in offs2]
        fig.legend(handles=hs2, loc='upper left', bbox_to_anchor=(0.645, t2 - hh - 0.7 / h), frameon=False, fontsize=7.8, title='Within lab',
                   title_fontsize=8.2, alignment='left')
    fig.savefig(C.FIG / 'forest.png', dpi=180); plt.close(fig)


def forest_by_school(S, ai_label):
    d = S[S.spec == 'main']
    ms = [m for m in LABELS if m in set(d.measure)]
    fig, ax = plt.subplots(figsize=(8.6, 0.3 * len(ms) + 1.9))
    ax.axvline(0, color=MUTED, lw=0.9)
    groups = ['all'] + list(C.SCHOOLS)
    offs = dict(zip(groups, np.linspace(-0.33, 0.33, len(groups))))
    for g in groups:
        col = INK if g == 'all' else SCHOOL_C[g]
        for i, m in enumerate(ms):
            r = d[(d.measure == m) & (d.school == g)]
            if not len(r):
                continue
            r = r.iloc[0]
            ax.plot([r.lo, r.hi], [i + offs[g]] * 2, color=col, lw=1.1 if g != 'all' else 1.6, alpha=0.9)
            ax.plot([r.beta], [i + offs[g]], 'o', ms=4 if g != 'all' else 5, mfc=col, mec=SURF, mew=0.8)
    ax.set_yticks(range(len(ms))); ax.set_yticklabels([LABELS[m] + ('' if FAMILY[m] in ('txt', 'ref') else f' ({FAMILY[m]})') for m in ms], fontsize=7.8, color=INK2)
    ax.set_ylim(len(ms) - 0.5, -0.6); ax.grid(axis='y', visible=False)
    ax.set_xlabel(f'standardized slope of change on post-period {ai_label} (95% CI)')
    ax.set_title('Lab-level slopes per school (main specification; schools with ≥ 20 labs)', loc='left', fontsize=9.5)
    h = [Line2D([], [], marker='o', ms=5, mfc=INK, mec=SURF, color=INK, label='All five')]
    h += [Line2D([], [], marker='o', ms=5, mfc=SCHOOL_C[s], mec=SURF, color=SCHOOL_C[s], label=C.LABEL[s]) for s in C.SCHOOLS if s in set(d.school)]
    ax.legend(handles=h, loc='upper left', bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(C.FIG / 'forest_by_school.png', dpi=180); plt.close(fig)


FIG3_PER_GROUP = 500  # owner 2026-10-27: 1,000 papers per school, 500 flagged + 500 not, matched over the years


def fig3_sample(keys, flag, school, year, per_group=FIG3_PER_GROUP):
    """Indices of the Figure 3 sample. Per school: up to per_group flagged papers, spread over the years as evenly as the
    flagged pool allows (a year with few flagged papers gives all it has, the rest go to the other years), and in each year
    the same number of not-flagged papers. Both groups of a school then have the same size and the same year mix."""
    r = np.random.default_rng(C.SEED)
    pick, comp = [], {}
    for sc in C.SCHOOLS:
        ys = sorted(set(year[school == sc]))
        A = {y: r.permutation(np.flatnonzero((school == sc) & flag & (year == y))) for y in ys}
        B = {y: r.permutation(np.flatnonzero((school == sc) & ~flag & (year == y))) for y in ys}
        cap = {y: min(len(A[y]), len(B[y])) for y in ys}
        q, left = dict.fromkeys(ys, 0), per_group
        while left and any(q[y] < cap[y] for y in ys):  # water-filling: one paper per open year per round
            for y in ys:
                if left and q[y] < cap[y]:
                    q[y] += 1; left -= 1
        for y in ys:
            pick += list(A[y][:q[y]]) + list(B[y][:q[y]])
        comp[sc] = {str(int(y)): q[y] for y in ys}
    return np.array(sorted(pick)), comp


def fig3_fulltext(ai, ai_label, metric='euclidean'):
    """Hao et al. Fig. 3 with the full-text vectors on a year-matched sample: knowledge extent and knowledge entropy, each
    on the t-SNE map with how it is computed. metric 'euclidean' (raw means, as fig3.py does for abstracts) or 'cosine'
    (the native geometry of the embedding: Euclidean distances concentrate in 768-D)."""
    from sklearn.cluster import KMeans
    from sklearn.manifold import TSNE
    ft = C.load_fulltext_means()
    F = pd.read_parquet(C.DATA / 'paper_features.parquet').set_index('key')
    keys = [k for k in ft if k in F.index and F.at[k, 'has_ft'] and 2023 <= F.at[k, 'year'] <= 2026 and k in ai]
    if len(keys) < 200:
        C.log(fig3_fulltext='too few full texts', n=len(keys)); return {}
    flag = np.array([bool(ai[k]['flag']) for k in keys]); school = F.loc[keys, 'school'].values; year = F.loc[keys, 'year'].values.astype(int)
    S, comp = fig3_sample(keys, flag, school, year)
    from scipy.sparse import csr_matrix
    labs_of = {q['key']: q['labs'] for q in C.load_papers()[0]}
    lab_names = sorted({l for i in S for l in labs_of.get(keys[i], [])})
    li = {l: j for j, l in enumerate(lab_names)}; rows_, cols_, w_ = [], [], []
    for r_, i in enumerate(S):  # sample paper x lab, weight 1/(number of the paper's labs)
        ls = labs_of.get(keys[i], [])
        for l in ls:
            rows_.append(r_); cols_.append(li[l]); w_.append(1 / len(ls))
    M = csr_matrix((w_, (rows_, cols_)), shape=(len(S), len(lab_names)))
    # k-means and t-SNE take minutes and the draws ~10 min; cache them on the papers, the sample and the flags
    cache = C.RES / ('fig3_fulltext_cache.pkl' if metric == 'euclidean' else f'fig3_fulltext_{metric}_cache.pkl')
    tag = hashlib.sha256(json.dumps([keys, flag.tolist(), S.tolist(), C.SEED, metric, lab_names, 'labs-v1']).encode()).hexdigest()
    hit = pickle.loads(cache.read_bytes()) if cache.exists() else {}
    if hit.get('tag') != tag:
        X = np.vstack([ft[k][2] for k in keys]).astype(np.float32)
        hit = dict(tag=tag, **_fig3_compute(X, flag, school, S, KMeans, TSNE, metric, M), M=M)
        cache.write_bytes(pickle.dumps(hit))
    nums = dict(hit['nums'], sample_per_school_year=comp)
    _fig3_draw(hit, flag[S], school[S], ai_label, metric)
    return nums


def _fig3_compute(X, flag, school, S, KMeans, TSNE, metric, M):
    if metric == 'cosine':
        X = X / np.linalg.norm(X, axis=1, keepdims=True)  # unit vectors: k-means on them is spherical k-means
    km = KMeans(50, n_init=3, random_state=C.SEED).fit(X)  # the topic clusters: fit on every 2023-2026 full text
    cl = km.labels_[S]; Xs, fs_, ss = X[S], flag[S], school[S]

    def ext(V):
        c = V.mean(0)
        if metric == 'cosine':
            return float(1 - (V @ c).min() / np.linalg.norm(c))
        return float(np.sqrt(((V - c) ** 2).sum(1)).max())

    def ent(L):
        p = np.bincount(L, minlength=50) / len(L); p = p[p > 0]; return float(-(p * np.log(p)).sum())

    def ent_lab(i):
        p = np.asarray(M[i].sum(0)).ravel(); p = p[p > 0] / p.sum(); return float(-(p * np.log(p)).sum())

    r = np.random.default_rng(C.SEED)
    draws, nums = {}, dict(papers_all=len(X), flagged_all=int(flag.sum()), sample=len(S))
    for sc in list(C.SCHOOLS) + ['all']:
        sel = np.ones(len(S), bool) if sc == 'all' else ss == sc
        a, b = np.flatnonzero(sel & fs_), np.flatnonzero(sel & ~fs_)
        n = int(min(1000, 0.8 * min(len(a), len(b))))
        if n < 30:
            continue
        d = {'ai': ([], [], []), 'not': ([], [], [])}
        for _ in range(1000):
            for g, ids in (('ai', a), ('not', b)):
                i = r.choice(ids, n, replace=False)
                d[g][0].append(ext(Xs[i])); d[g][1].append(ent(cl[i])); d[g][2].append(ent_lab(i))
        draws[sc] = dict(n=n, d=d)
        nums[sc] = dict(n_per_draw=n, flagged=len(a), not_flagged=len(b), extent_ai_median=float(np.median(d['ai'][0])), extent_not_median=float(np.median(d['not'][0])),
                        extent_ai_lower_share=float(np.mean(np.array(d['ai'][0]) < np.array(d['not'][0]))), entropy_ai_median=float(np.median(d['ai'][1])),
                        entropy_not_median=float(np.median(d['not'][1])), entropy_ai_lower_share=float(np.mean(np.array(d['ai'][1]) < np.array(d['not'][1]))),
                        lab_entropy_ai_median=float(np.median(d['ai'][2])), lab_entropy_not_median=float(np.median(d['not'][2])),
                        lab_entropy_ai_lower_share=float(np.mean(np.array(d['ai'][2]) < np.array(d['not'][2]))))
    Y = TSNE(2, perplexity=30, init='pca', metric=metric, random_state=C.SEED).fit_transform(Xs)
    return dict(draws=draws, nums=nums, Y=Y, cl=cl)


def _fig3_draw(hit, lab, ss, ai_label, metric):
    cos = metric == 'cosine'
    draws, Y, cl = hit['draws'], hit['Y'], hit['cl']
    na, nb = int(lab.sum()), int((~lab).sum())
    cen_all = Y.mean(0); r_all = float(np.sqrt(((Y - cen_all) ** 2).sum(1)).max())  # one circle around every paper
    lim = (cen_all[0] - 1.06 * r_all, cen_all[0] + 1.06 * r_all), (cen_all[1] - 1.06 * r_all, cen_all[1] + 1.06 * r_all)
    FAINT = '#c9cdc6'

    def bare(ax):
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(False)

    def toys(ax, xlab, plab, what):
        for x0, p, name in ((0.0, np.array([5, 4, 4, 3, 3, 3, 2, 2]) / 26, f'spread over {what}'), (0.52, np.array([14, 6, 3, 2, 1, 0, 0, 0]) / 26, 'concentrated')):
            q = p[p > 0]; h = float(-(q * np.log(q)).sum())
            ia = ax.inset_axes([x0 + 0.03, 0.62, 0.40, 0.25]); ia.bar(np.arange(1, 9), p, width=0.72, color=MUTED)
            ia.set_ylim(0, 0.6); ia.set_xticks(range(1, 9)); ia.tick_params(labelsize=6.5, length=0); ia.set_yticks([0, 0.25, 0.5])
            ia.grid(axis='x', visible=False); ia.set_xlabel(xlab, fontsize=7, color=INK2, labelpad=1)
            for sp in ('top', 'right'):
                ia.spines[sp].set_visible(False)
            ia.set_title(f'{name}: H = {h:.2f}', fontsize=7.8, color=INK, loc='left')
            if x0 == 0:
                ia.set_ylabel(plab, fontsize=8, color=INK2)

    def tsne_axes(ax, title, circle=True):
        bare(ax); ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_aspect('equal')
        if circle:
            ax.add_patch(plt.Circle(cen_all, r_all, fill=False, ec=INK2, lw=1.4, ls='--'))
            ax.scatter([cen_all[0]], [cen_all[1]], s=40, marker='x', c=INK, linewidths=1.6, zorder=6)
        ax.set_title(title, loc='left', fontsize=9.5)

    fig = plt.figure(figsize=(15, 20))
    top, mid, low = 0.745, 0.49, 0.235  # bottom edges of the extent, topic entropy and lab entropy rows; the boxplots sit below
    RH, SH = 0.225, 0.108  # row height; height of one small split map

    # A: knowledge extent on the map: every paper, one circle; flagged vs not by colour, then one group at a time
    ax = fig.add_axes([0.015, top, 0.37, RH])
    tsne_axes(ax, f'A  Knowledge extent on the map: {len(Y):,} papers (' + ('cosine ' if cos else '') + 't-SNE)')
    order = np.random.default_rng(C.SEED).permutation(len(Y))  # interleave the colours so neither group paints over the other
    ax.scatter(Y[order, 0], Y[order, 1], s=4, c=np.where(lab[order], C_MORE, C_LESS), alpha=0.55, linewidths=0)
    ax.legend(handles=[Line2D([], [], ls='', marker='o', ms=5, mfc=C_LESS, mec=C_LESS, label=f'not flagged ({nb:,})'),
                       Line2D([], [], ls='', marker='x', ms=6, mec=INK, label='centre = mean of all papers'),
                       Line2D([], [], ls='', marker='o', ms=5, mfc=C_MORE, mec=C_MORE, label=f'flagged ({na:,})'),
                       Line2D([], [], ls='--', color=INK2, lw=1.2, label='one circle: radius = the farthest paper')],
              loc='upper center', bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=7.6, handlelength=2.2)
    for j, (g, c, name) in enumerate(((False, C_LESS, 'not flagged only'), (True, C_MORE, 'flagged only'))):
        ax = fig.add_axes([0.39, top + SH + 0.009 - j * (SH + 0.009), 0.21, SH])
        tsne_axes(ax, name)
        ax.scatter(Y[lab != g, 0], Y[lab != g, 1], s=2, c=FAINT, alpha=0.5, linewidths=0)
        P = Y[lab == g]; ax.scatter(P[:, 0], P[:, 1], s=2.5, c=c, alpha=0.6, linewidths=0)
        cg = P.mean(0); ax.scatter([cg[0]], [cg[1]], s=70, c=c, edgecolors=SURF, linewidths=1.8, zorder=7)

    # B: how knowledge extent is computed
    ax = fig.add_axes([0.63, top, 0.355, RH]); bare(ax); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect('equal', anchor='NW')  # a round circle
    ax.set_title('B  How knowledge extent is computed', loc='left', fontsize=9.5)
    if not cos:
        demo = np.random.default_rng(7).normal(0, 1, (14, 2)) * [0.105, 0.085] + [0.30, 0.68]
        demo[:, 0] = 0.60 - demo[:, 0]  # mirrored so the farthest paper sits on the right, next to its label
        cd = demo.mean(0); dd = np.sqrt(((demo - cd) ** 2).sum(1)); far = int(dd.argmax())
        for i, q in enumerate(demo):
            ax.plot([cd[0], q[0]], [cd[1], q[1]], color=C_MORE if i == far else FAINT, lw=2.0 if i == far else 0.9, zorder=2)
        ax.scatter(demo[:, 0], demo[:, 1], s=26, c=C_LESS, zorder=3, edgecolors=SURF, linewidths=0.8)
        ax.scatter([cd[0]], [cd[1]], s=60, marker='x', c=INK, linewidths=2, zorder=4)
        ax.add_patch(plt.Circle(cd, dd[far], fill=False, ec=C_MORE, lw=1.2, ls='--', zorder=1))
        ax.text(cd[0] + 0.014, cd[1] + 0.022, 'c', fontsize=9.5, color=INK, style='italic', zorder=5, bbox=dict(fc=SURF, ec='none', pad=0.6, alpha=0.9))
        ax.text(demo[far][0] + 0.03, demo[far][1], 'extent = the longest\ndistance to c', fontsize=8, color=INK, va='center')
        ax.text(0.64, 0.95, 'one draw of n papers\n(each dot is a paper;\nreally a point in 768-D)', fontsize=7.6, color=INK2, va='top')
        ax.text(0.0, 0.43, '1  Each paper i is a vector $v_i$: the mean SPECTER2 vector of its\n'
                           '    body passages (768 dimensions).\n'
                           '2  Draw n papers from one group (flagged, or not flagged).\n'
                           '3  Centre: $c = \\frac{1}{n}\\sum_i v_i$.\n'
                           '4  Knowledge extent $= \\max_i$ ‖$v_i - c$‖ (Euclidean): the radius of\n'
                           '    the smallest circle around c that holds every paper.\n'
                           '5  Repeat 1,000 times; panel G shows the 1,000 values per group.\n'
                           "A's circle is a 2-D picture of step 4; t-SNE bends distances, so the\n"
                           'measure itself is computed in the full 768-D space.', fontsize=7.7, color=INK2, va='top', linespacing=1.45)
    else:
        O, R = np.array([0.06, 0.48]), 0.55
        th = np.radians([5, 20, 24, 27, 30, 33, 36, 39, 42, 45, 48, 52])  # one draw: each paper a direction from the origin
        U = np.c_[np.cos(th), np.sin(th)]; cv = U.mean(0); tc = np.arctan2(cv[1], cv[0]); far = int(np.abs(th - tc).argmax())
        arc = np.linspace(th.min() - 0.08, th.max() + 0.08, 60)
        ax.plot(O[0] + R * np.cos(arc), O[1] + R * np.sin(arc), color=FAINT, lw=1, ls='--', zorder=1)
        for i, t in enumerate(th):
            e = O + R * U[i]
            ax.plot([O[0], e[0]], [O[1], e[1]], color=C_MORE if i == far else FAINT, lw=2.0 if i == far else 0.9, zorder=2)
        ax.scatter(O[0] + R * U[:, 0], O[1] + R * U[:, 1], s=26, c=C_LESS, zorder=3, edgecolors=SURF, linewidths=0.8)
        ce = O + R * np.array([np.cos(tc), np.sin(tc)])
        ax.plot([O[0], ce[0]], [O[1], ce[1]], color=INK, lw=1.6, zorder=4)
        ax.scatter([ce[0]], [ce[1]], s=60, marker='x', c=INK, linewidths=2, zorder=4)
        ax.text(ce[0] + 0.02, ce[1] + 0.01, 'c', fontsize=9.5, color=INK, style='italic', zorder=5)
        ax.scatter([O[0]], [O[1]], s=14, c=INK, zorder=4); ax.text(O[0] - 0.01, O[1] - 0.045, 'origin', fontsize=7.3, color=INK2)
        wa = np.linspace(th[far], tc, 30)
        ax.plot(O[0] + 0.2 * np.cos(wa), O[1] + 0.2 * np.sin(wa), color=C_MORE, lw=1.4, zorder=4)
        ax.text(O[0] + 0.235 * np.cos(wa.mean()), O[1] + 0.235 * np.sin(wa.mean()), '$\\theta$', fontsize=10, color=INK, va='center')
        fe = O + R * U[far]
        ax.text(fe[0] + 0.03, fe[1], 'extent = 1 − cos $\\theta$:\nthe widest angle to c', fontsize=8, color=INK, va='center')
        ax.text(0.64, 0.95, 'one draw of n papers\n(each ray is a paper\'s\ndirection; really 768-D)', fontsize=7.6, color=INK2, va='top')
        ax.text(0.0, 0.40, '1  Each paper i is a vector $v_i$: the mean SPECTER2 vector of its\n'
                           '    body passages (768 dimensions); only its direction is used.\n'
                           '2  Draw n papers from one group (flagged, or not flagged).\n'
                           '3  Centre direction: $c = \\frac{1}{n}\\sum_i v_i/$‖$v_i$‖.\n'
                           '4  Knowledge extent $= \\max_i\\,(1 - \\cos(v_i, c))$: the cosine distance\n'
                           '    of the paper at the widest angle from c.\n'
                           '5  Repeat 1,000 times; panel G shows the 1,000 values per group.\n'
                           "A's circle is a 2-D picture; t-SNE (cosine metric) bends distances,\n"
                           'so the measure itself is computed in the full 768-D space.', fontsize=7.7, color=INK2, va='top', linespacing=1.45)

    # C: knowledge entropy on the map: the 50 topic clusters, and each group's share of papers in every cluster
    med = np.array([np.median(Y[cl == c_], 0) if (cl == c_).any() else [np.nan, np.nan] for c_ in range(50)])
    ax = fig.add_axes([0.015, mid, 0.37, RH])
    tsne_axes(ax, 'C  Topic entropy on the map: the same papers in 50 topic clusters', circle=False)
    ax.scatter(Y[:, 0], Y[:, 1], s=3, c=FAINT, alpha=0.7, linewidths=0)
    for c_, (x, y) in enumerate(med):
        if np.isfinite(x):
            ax.text(x, y, str(c_ + 1), fontsize=6.3, color=INK, ha='center', va='center', zorder=5,
                    bbox=dict(boxstyle='circle,pad=0.18', fc=SURF, ec=MUTED, lw=0.5, alpha=0.9))
    ax.text(0.5, -0.02, 'each paper belongs to its nearest of 50 k-means centres (fit in 768-D);\nthe number sits at the middle of that cluster on the map',
            transform=ax.transAxes, ha='center', va='top', fontsize=7.6, color=INK2)
    H = {}
    for j, (g, c, name) in enumerate(((False, C_LESS, 'not flagged'), (True, C_MORE, 'flagged'))):
        p = np.bincount(cl[lab == g], minlength=50) / (lab == g).sum(); q = p[p > 0]; H[g] = float(-(q * np.log(q)).sum())
        ax = fig.add_axes([0.39, mid + SH + 0.009 - j * (SH + 0.009), 0.21, SH])
        tsne_axes(ax, f'{name}: topic H = {H[g]:.2f} nats', circle=False)
        ax.scatter(Y[:, 0], Y[:, 1], s=1.5, c=FAINT, alpha=0.5, linewidths=0)
        ok = np.isfinite(med[:, 0]) & (p > 0)
        ax.scatter(med[ok, 0], med[ok, 1], s=2600 * p[ok], c=c, alpha=0.75, edgecolors=SURF, linewidths=0.8, zorder=5)
    ax.text(0.5, -0.04, 'bubble area = share of the group in that cluster', transform=ax.transAxes, ha='center', va='top', fontsize=7.3, color=INK2)

    # D: how knowledge entropy is computed
    ax = fig.add_axes([0.63, mid, 0.355, RH]); bare(ax); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title('D  How topic entropy is computed', loc='left', fontsize=9.5)
    toys(ax, 'cluster k', '$p_k$', 'topics')
    ax.text(0.03, 0.965, 'two toy draws of 26 papers over 8 clusters', fontsize=7.6, color=INK2, va='top')
    ax.text(0.0, 0.43, (('1  Fit k-means with 50 clusters on the length-normalised 768-D vectors\n'
                         '    of all 2023–2026 full texts (spherical k-means: clusters by cosine);\n'
                         '    each paper belongs to its nearest cluster centre (C).\n') if cos else
                        ('1  Fit k-means with 50 clusters on the 768-D vectors of all 2023–2026\n'
                         '    full texts; each paper belongs to its nearest cluster centre (C).\n')) +
                       '2  Draw n papers from one group (flagged, or not flagged).\n'
                       '3  $p_k$ = the share of the draw in cluster k.\n'
                       '4  Topic entropy $H = -\\sum_k p_k \\ln p_k$ (nats): 0 when every\n'
                       '    paper sits in one cluster, $\\ln 50 = 3.91$ when spread evenly.\n'
                       '5  Repeat 1,000 times; panel H shows the 1,000 values per group.\n'
                       "C's bubbles show $p_k$ for each whole group of the sample, and the H\n"
                       'in their titles is computed from those shares.', fontsize=7.7, color=INK2, va='top', linespacing=1.45)

    # E: lab entropy on the map: each lab at the mean position of its papers, and each group's share of papers in every lab
    M = hit['M']; W = np.asarray(M.sum(0)).ravel()
    LP = np.asarray(M.T @ Y) / np.where(W > 0, W, 1)[:, None]  # weighted mean position of each lab's sample papers
    ax = fig.add_axes([0.015, low, 0.37, RH])
    tsne_axes(ax, f'E  Lab entropy on the map: the same papers in {M.shape[1]:,} PI labs', circle=False)
    ax.scatter(Y[:, 0], Y[:, 1], s=3, c=FAINT, alpha=0.7, linewidths=0)
    ax.scatter(LP[:, 0], LP[:, 1], s=7, c=INK2, linewidths=0, zorder=5)
    ax.text(0.5, -0.02, 'each dark dot is one lab, at the mean map position of its papers in the sample\n(a paper of two labs counts 1/2 to each)',
            transform=ax.transAxes, ha='center', va='top', fontsize=7.6, color=INK2)
    for j, (g, c, name) in enumerate(((False, C_LESS, 'not flagged'), (True, C_MORE, 'flagged'))):
        pl = np.asarray(M[np.flatnonzero(lab == g)].sum(0)).ravel(); pl = pl / pl.sum(); q = pl[pl > 0]
        ax = fig.add_axes([0.39, low + SH + 0.009 - j * (SH + 0.009), 0.21, SH])
        tsne_axes(ax, f'{name}: lab H = {float(-(q * np.log(q)).sum()):.2f} nats ({int((pl > 0).sum()):,} labs)', circle=False)
        ax.scatter(Y[:, 0], Y[:, 1], s=1.5, c=FAINT, alpha=0.5, linewidths=0)
        ok = pl > 0
        ax.scatter(LP[ok, 0], LP[ok, 1], s=9000 * pl[ok], c=c, alpha=0.7, edgecolors=SURF, linewidths=0.5, zorder=5)
    ax.text(0.5, -0.04, 'bubble area = share of the group in that lab', transform=ax.transAxes, ha='center', va='top', fontsize=7.3, color=INK2)

    # F: how lab entropy is computed
    ax = fig.add_axes([0.63, low, 0.355, RH]); bare(ax); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title('F  How lab entropy is computed', loc='left', fontsize=9.5)
    toys(ax, 'lab l', '$p_l$', 'labs')
    ax.text(0.03, 0.965, 'two toy draws of 26 papers over 8 labs', fontsize=7.6, color=INK2, va='top')
    ax.text(0.0, 0.43, '1  Each paper belongs to its PI labs: the labs whose PI is on the byline;\n'
                       '    a paper of m labs counts 1/m to each.\n'
                       '2  Draw n papers from one group (flagged, or not flagged).\n'
                       '3  $p_l$ = the share of the draw in lab l.\n'
                       '4  Lab entropy $H = -\\sum_l p_l \\ln p_l$ (nats): low when a few labs\n'
                       '    write most of the group\'s papers; no embedding is involved.\n'
                       '5  Repeat 1,000 times; panel I shows the 1,000 values per group.\n'
                       "E's bubbles show $p_l$ for each whole group of the sample.", fontsize=7.7, color=INK2, va='top', linespacing=1.45)

    # G, H, I: the measures by school
    for j, (panel, idx, ylab) in enumerate((('G  Knowledge extent', 0, 'max cosine distance to centre' if cos else 'max distance to centre (768-D)'),
                                            ('H  Topic entropy', 1, 'entropy over 50 topic clusters (nats)'), ('I  Lab entropy', 2, 'entropy over PI labs (nats)'))):
        ax = fig.add_axes([0.05 + j * 0.325, 0.06, 0.285, 0.135])
        names = [sc for sc in list(C.SCHOOLS) + ['all'] if sc in draws]
        for i, sc in enumerate(names):
            for off, g, c in ((-0.18, 'not', C_LESS), (0.18, 'ai', C_MORE)):
                bp = ax.boxplot(draws[sc]['d'][g][idx], positions=[i + off], widths=0.3, whis=1.5, showfliers=False, patch_artist=True)
                for bx in bp['boxes']:
                    bx.set(facecolor=c, edgecolor=c, alpha=0.85)
                for part in ('whiskers', 'caps', 'medians'):
                    for l in bp[part]:
                        l.set(color=INK if part == 'medians' else c, linewidth=1.2)
        ax.set_xticks(range(len(names))); ax.set_xticklabels([f"{C.LABEL.get(sc, 'All')}\nn={draws[sc]['n']}" for sc in names], fontsize=7.4)
        lo_, hi_ = ax.get_ylim(); ax.set_ylim(lo_, hi_ + 0.22 * (hi_ - lo_))  # headroom: the legend sits above the whiskers
        ax.set_ylabel(ylab, fontsize=8.5); ax.set_title(panel + ' by school (1,000 draws)', loc='left', fontsize=9.5); ax.grid(axis='x', visible=False)
        ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, fc=C_LESS, label='not flagged'), plt.Rectangle((0, 0), 1, 1, fc=C_MORE, label='flagged')],
                  loc='upper right', frameon=False, fontsize=7.5, ncol=2)
    per = ', '.join(f"{C.LABEL[sc]} {int((ss == sc).sum()) // 2:,}" for sc in C.SCHOOLS)
    fig.text(0.06, 0.012, f'Lab papers of 2023–2026 with a full text; flagged = {ai_label}. Sample per school: up to {FIG3_PER_GROUP} flagged papers spread over the years, '
             f'and as many not-flagged papers from the same years\n(flagged per school: {per}).\nVectors: mean of the SPECTER2 vectors of each paper\'s body passages' + ('; cosine geometry. ' if cos else '; Euclidean geometry. ') +
             'Each draw in G–I takes n papers per group (80% of the group, the same n for both groups of a school).',
             color=MUTED, fontsize=7.6)
    fig.savefig(C.FIG / ('fig3_fulltext_cosine.png' if cos else 'fig3_fulltext.png'), dpi=170); plt.close(fig)


CHATGPT = '2022-11-30'
C_PRE = '#8a949b'  # before ChatGPT: the neutral baseline beside the two after-groups


def fig3_periods(ai, ai_label, metric='cosine'):
    """Before vs after ChatGPT (30 Nov 2022) on three t-SNE maps: the papers before only, the papers after only (flagged
    vs not), and all of them in one map; then knowledge extent, topic entropy and lab entropy for the three groups by
    school. The after sample is Figure 3's (fig3_sample); the before sample has the same size per school, spread as
    evenly as possible over 2016-2022 (to 29 Nov 2022). December 2022 is left out as the changeover month."""
    from sklearn.cluster import KMeans
    from sklearn.manifold import TSNE
    from scipy.sparse import csr_matrix
    import gzip
    ft = C.load_fulltext_means()
    F = pd.read_parquet(C.DATA / 'paper_features.parquet').set_index('key')
    date = {}
    with gzip.open(C.AIW / 'papers.jsonl.gz', 'rt') as f:
        for line in f:
            q = json.loads(line); date[q['key']] = q.get('date') or ''
    allk = [k for k in ft if k in F.index and F.at[k, 'has_ft']]
    post = [k for k in allk if 2023 <= F.at[k, 'year'] <= 2026 and k in ai]
    if len(post) < 200:
        return {}
    flag = np.array([bool(ai[k]['flag']) for k in post]); school = F.loc[post, 'school'].values
    S, _ = fig3_sample(post, flag, school, F.loc[post, 'year'].values.astype(int))

    def is_pre(k):
        d = date.get(k) or ''
        return d[:10] < CHATGPT if d[:4].isdigit() else F.at[k, 'year'] <= 2021
    pre = [k for k in allk if F.at[k, 'year'] <= 2022 and is_pre(k)]
    r = np.random.default_rng(C.SEED); pick = []
    for sc in C.SCHOOLS:
        want = int((school[S] == sc).sum())
        by = {}
        for k in pre:
            if F.at[k, 'school'] == sc:
                by.setdefault(int(F.at[k, 'year']), []).append(k)
        ys = sorted(by); by = {y: list(r.permutation(by[y])) for y in ys}
        q, left = dict.fromkeys(ys, 0), want
        while left and any(q[y] < len(by[y]) for y in ys):
            for y in ys:
                if left and q[y] < len(by[y]):
                    q[y] += 1; left -= 1
        pick += [k for y in ys for k in by[y][:q[y]]]
    keys = pick + [post[i] for i in S]
    grp = np.array([0] * len(pick) + [2 if flag[i] else 1 for i in S]); sch = F.loc[keys, 'school'].values
    labs_of = {q['key']: q['labs'] for q in C.load_papers()[0]}
    lab_names = sorted({l for k in keys for l in labs_of.get(k, [])}); li = {l: j for j, l in enumerate(lab_names)}
    rows_, cols_, w_ = [], [], []
    for r_, k in enumerate(keys):
        ls = labs_of.get(k, [])
        for l in ls:
            rows_.append(r_); cols_.append(li[l]); w_.append(1 / len(ls))
    M_ = csr_matrix((w_, (rows_, cols_)), shape=(len(keys), len(lab_names)))
    cache = C.RES / f'fig3_periods_{metric}_cache.pkl'
    tag = hashlib.sha256(json.dumps([keys, grp.tolist(), C.SEED, metric, len(allk), 'periods-v1']).encode()).hexdigest()
    hit = pickle.loads(cache.read_bytes()) if cache.exists() else {}
    if hit.get('tag') != tag:
        XA = np.vstack([ft[k][2] for k in allk]).astype(np.float32)
        if metric == 'cosine':
            XA /= np.linalg.norm(XA, axis=1, keepdims=True)
        km = KMeans(50, n_init=3, random_state=C.SEED).fit(XA)  # topic clusters over every 2016-2026 full text
        pos = {k: i for i, k in enumerate(allk)}; ix = np.array([pos[k] for k in keys])
        X, cl = XA[ix], km.labels_[ix]; del XA

        def ext(V):
            c = V.mean(0)
            return float(1 - (V @ c).min() / np.linalg.norm(c)) if metric == 'cosine' else float(np.sqrt(((V - c) ** 2).sum(1)).max())

        def ent(p):
            p = p[p > 0] / p.sum(); return float(-(p * np.log(p)).sum())
        draws = {}
        for sc in list(C.SCHOOLS) + ['all']:
            sel = np.ones(len(keys), bool) if sc == 'all' else sch == sc
            ids = [np.flatnonzero(sel & (grp == g)) for g in range(3)]
            n = int(min(1000, 0.8 * min(len(x) for x in ids)))
            if n < 30:
                continue
            d = [([], [], []) for _ in range(3)]
            for _ in range(1000):
                for g in range(3):
                    i = r.choice(ids[g], n, replace=False)
                    d[g][0].append(ext(X[i])); d[g][1].append(ent(np.bincount(cl[i], minlength=50).astype(float)))
                    d[g][2].append(ent(np.asarray(M_[i].sum(0)).ravel()))
            draws[sc] = dict(n=n, d=d)
        maps = {}
        for name, m in (('pre', grp == 0), ('post', grp > 0), ('all', np.ones(len(keys), bool))):
            maps[name] = (np.flatnonzero(m), TSNE(2, perplexity=30, init='pca', metric=metric, random_state=C.SEED).fit_transform(X[m]))
        hit = dict(tag=tag, draws=draws, maps=maps)
        cache.write_bytes(pickle.dumps(hit))
    draws, maps = hit['draws'], hit['maps']
    names = ('before Nov 2022', 'after, not flagged', 'after, flagged'); cols = (C_PRE, C_LESS, C_MORE)

    fig = plt.figure(figsize=(16, 11.5))
    for j, (m, title) in enumerate((('pre', '1  Before ChatGPT: t-SNE of these papers only'), ('post', '2  After ChatGPT (2023–2026): t-SNE of these papers only'),
                                    ('all', '3  All papers in one t-SNE'))):
        ix, Y = maps[m]; g = grp[ix]
        ax = fig.add_axes([0.01 + j * 0.33, 0.47, 0.31, 0.46])
        cen = Y.mean(0); rad = float(np.sqrt(((Y - cen) ** 2).sum(1)).max())
        ax.set_xlim(cen[0] - 1.06 * rad, cen[0] + 1.06 * rad); ax.set_ylim(cen[1] - 1.06 * rad, cen[1] + 1.06 * rad); ax.set_aspect('equal')
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(False)
        o = np.random.default_rng(C.SEED).permutation(len(Y))
        ax.scatter(Y[o, 0], Y[o, 1], s=3.5, c=np.array(cols)[g[o]], alpha=0.55, linewidths=0)
        ax.add_patch(plt.Circle(cen, rad, fill=False, ec=INK2, lw=1.3, ls='--'))
        hs = []
        for gg in sorted(set(g)):
            cg = Y[g == gg].mean(0)
            ax.scatter([cg[0]], [cg[1]], s=80, c=cols[gg], edgecolors=SURF, linewidths=2, zorder=7)
            hs.append(Line2D([], [], ls='', marker='o', ms=6, mfc=cols[gg], mec=cols[gg], label=f'{names[gg]} ({int((g == gg).sum()):,})'))
        hs.append(Line2D([], [], ls='--', color=INK2, lw=1.2, label='one circle around every paper; big dots = group centres'))
        ax.legend(handles=hs, loc='upper center', bbox_to_anchor=(0.5, 0.0), ncol=1, frameon=False, fontsize=7.6)
        ax.set_title(title, loc='left', fontsize=9.5)
    for j, (panel, idx, ylab) in enumerate((('4  Knowledge extent', 0, 'max cosine distance to centre' if metric == 'cosine' else 'max distance to centre (768-D)'),
                                            ('5  Topic entropy', 1, 'entropy over 50 topic clusters (nats)'), ('6  Lab entropy', 2, 'entropy over PI labs (nats)'))):
        ax = fig.add_axes([0.05 + j * 0.325, 0.08, 0.285, 0.24])
        scs = [sc for sc in list(C.SCHOOLS) + ['all'] if sc in draws]
        for i, sc in enumerate(scs):
            for gg, off in ((0, -0.25), (1, 0), (2, 0.25)):
                bp = ax.boxplot(draws[sc]['d'][gg][idx], positions=[i + off], widths=0.2, whis=1.5, showfliers=False, patch_artist=True)
                for bx in bp['boxes']:
                    bx.set(facecolor=cols[gg], edgecolor=cols[gg], alpha=0.85)
                for part in ('whiskers', 'caps', 'medians'):
                    for l in bp[part]:
                        l.set(color=INK if part == 'medians' else cols[gg], linewidth=1.1)
        ax.set_xticks(range(len(scs))); ax.set_xticklabels([f"{C.LABEL.get(sc, 'All')}\nn={draws[sc]['n']}" for sc in scs], fontsize=7.4)
        lo_, hi_ = ax.get_ylim(); ax.set_ylim(lo_, hi_ + 0.25 * (hi_ - lo_))
        ax.set_ylabel(ylab, fontsize=8.5); ax.set_title(panel + ' by school (1,000 draws)', loc='left', fontsize=9.5); ax.grid(axis='x', visible=False)
        ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, fc=c, label=nm) for c, nm in zip(cols, names)], loc='upper center', frameon=False, fontsize=7.2, ncol=3)
    fig.text(0.05, 0.012, f'Full-text lab papers; flagged = {ai_label}. After: Figure 3\'s year-matched sample (up to {FIG3_PER_GROUP} flagged + as many not flagged per school). '
             'Before: the same number per school, spread over 2016 – 29 Nov 2022 (Dec 2022 left out).\n'
             f'Geometry: {metric}. Each map is its own t-SNE, so positions are not comparable between maps 1, 2 and 3; the circle and centres are drawn per map. '
             'Measures as in Figure 3 (B, D, F); each draw takes n papers per group.', color=MUTED, fontsize=7.6)
    fig.savefig(C.FIG / f'fig3_periods_{metric}.png', dpi=160); plt.close(fig)
    out = {}
    for sc, v in draws.items():
        out[sc] = dict(n=v['n'], **{f'{meas}_{names[g]}_median': float(np.median(v['d'][g][i])) for g in range(3) for i, meas in enumerate(('extent', 'topic_entropy', 'lab_entropy'))})
    return out


def flag_share_by_year(F):
    import gzip
    abs_ = {}
    for line in gzip.open(C.AIW / 'scores.jsonl.gz', 'rt'):
        s = json.loads(line); abs_[s['key']] = bool(s['flagged'])
    para = {}
    pp = C.AIW / 'paragraph_scores.jsonl.gz'
    if pp.exists():
        for line in gzip.open(pp, 'rt'):
            s = json.loads(line)
            if s.get('n_paragraphs') and s.get('ai_share') is not None:
                para[s['key']] = float(s['ai_share']) >= 0.25
    years = list(C.YEARS)
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    out = {}
    for s in C.SCHOOLS:
        sub = F[F.school == s]
        for det, d, ls in (('abstract', abs_, '-'), ('paragraph', para, '--')):
            if not d:
                continue
            r = [100 * np.mean([d[k] for k in sub[sub.year == y].index if k in d]) if any(k in d for k in sub[sub.year == y].index) else np.nan for y in years]
            out[f'{s}_{det}'] = dict(zip(years, [None if np.isnan(v) else round(float(v), 2) for v in r]))
            ax.plot(years, r, color=SCHOOL_C[s], lw=2, ls=ls, marker='o' if det == 'abstract' else None, ms=3.5)
    ax.axhline(1, color=MUTED, lw=0.9, ls=':')
    ax.axvline(2022.9, color=MUTED, lw=0.8, alpha=0.6)
    ax.annotate('ChatGPT (Nov 2022)', (2022.9, 1), xycoords=('data', 'axes fraction'), xytext=(-4, -4), textcoords='offset points',
                ha='right', va='top', color=MUTED, fontsize=7.5)
    ax.set_xticks(years); ax.set_xticklabels([str(y) for y in years], fontsize=7.5)
    ax.set_ylabel('% of lab papers flagged')
    ax.set_title('Flagged share by year (2026 is a partial year)', loc='left', fontsize=9.5)
    h = [Line2D([], [], color=SCHOOL_C[s], lw=2, label=C.LABEL[s]) for s in C.SCHOOLS]
    h += [Line2D([], [], color=INK2, lw=2, ls='-', marker='o', ms=3.5, label='abstract detector (v1)')]
    if para:
        h += [Line2D([], [], color=INK2, lw=2, ls='--', label='paragraph detector, ai_share ≥ 0.25')]
    else:
        h += [Line2D([], [], color=SURF, lw=0, label='paragraph detector: not yet available')]
    h += [Line2D([], [], color=MUTED, lw=0.9, ls=':', label='design false-positive rate (1%)')]
    ax.legend(handles=h, frameon=False, fontsize=7.5, loc='upper left', ncol=2)
    fig.tight_layout(); fig.savefig(C.FIG / 'flag_share_by_year.png', dpi=180); plt.close(fig)
    return out


def main():
    C.FIG.mkdir(exist_ok=True)
    S = pd.read_csv(C.RES / 'slopes.csv')
    W = pd.read_csv(C.RES / 'within.csv') if (C.RES / 'within.csv').stat().st_size > 1 else pd.DataFrame()
    lw = pd.read_csv(C.RES / 'lab_wide.csv')
    summ = json.loads((C.RES / 'analysis.json').read_text())
    ai, src = C.load_ai()
    ai_label = 'share flagged (abstract detector)' if src == 'abstract' else 'mean paragraph ai_share'
    scatters(lw, S, 'AI share, abstract detector' if src == 'abstract' else 'mean paragraph ai_share')
    forest(S, W, summ.get('null_abs_slope_95'), 'AI usage')
    forest_by_school(S, 'AI usage')
    F = pd.read_parquet(C.DATA / 'paper_features.parquet').set_index('key')
    fl = 'flagged by the abstract detector' if src == 'abstract' else 'paragraph ai_share ≥ 0.25'
    nums = dict(fig3_fulltext=fig3_fulltext(ai, fl), fig3_fulltext_cosine=fig3_fulltext(ai, fl, 'cosine'),
                fig3_periods_cosine=fig3_periods(ai, fl, 'cosine'), fig3_periods_euclidean=fig3_periods(ai, fl, 'euclidean'),
                flag_share_by_year=flag_share_by_year(F), ai_source=src)
    (C.RES / 'figure_numbers.json').write_text(json.dumps(nums, indent=1))
    C.log(figures=sorted(p.name for p in C.FIG.glob('*.png')))


if __name__ == '__main__':
    main()
