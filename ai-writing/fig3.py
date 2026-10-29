"""Hao, Xu, Li & Evans (2024), Fig. 3, for AI-WRITTEN text in the five schools' CS lab papers.

groups   lab papers of 2023-2026 (after ChatGPT) whose title + abstract the detector flags as AI-written (scores.jsonl.gz,
         threshold at a 1% false-positive rate on held-out pre-ChatGPT abstracts) vs. those it does not flag
space    SPECTER2 title + abstract embeddings (embeddings.npz, 768 dimensions), Euclidean, as in the paper
B        t-SNE of up to 10,000 papers, half flagged and half not, with each group's centroid and, for illustration, the
         circle holding 95% of the group's points in the 2-D map
C        knowledge extent (the paper's M8): the largest distance from a sample's centroid; 1,000 papers drawn per group
         (at most 80% of the smaller group, the same n for both groups of a school), 1,000 draws, per school and overall
D        knowledge entropy: the entropy of a sample's spread over 50 k-means topic clusters fitted on all 2023-2026
         papers (the paper does not define its entropy; this is our operationalization), same draws as C
E        the flagged share by publication year, 2016-2026: before ChatGPT it is the detector's false-positive rate
-> figures/fig3_ai_written.png, figures/fig3e_flag_rate.png, figures/fig3_numbers.json
"""
import collections, gzip, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

HERE = Path(__file__).resolve().parent; OUT = HERE / 'figures'; OUT.mkdir(exist_ok=True)
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']
LABEL = {'princeton': 'Princeton', 'cmu': 'CMU', 'epfl': 'EPFL', 'mit': 'MIT', 'berkeley': 'Berkeley', 'stanford': 'Stanford', 'all': 'All six'}
C_NOT, C_AI = '#2a78d6', '#eb6834'  # validated categorical slots 1-2 (dataviz palette, light surface)
INK, MUTED, GRID, SURF = '#1d2a33', '#68747c', '#e3e5e0', '#fcfcfb'
rng = np.random.default_rng(20261022)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': GRID, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.facecolor': SURF, 'figure.facecolor': SURF, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6})

E = np.load(HERE / 'embeddings.npz'); key_idx = {k: i for i, k in enumerate(E['keys'])}; X = E['X'].astype(np.float32)
S = [json.loads(l) for l in gzip.open(HERE / 'scores.jsonl.gz', 'rt')]
S = [s for s in S if s['key'] in key_idx and s.get('year')]
post = [s for s in S if 2023 <= int(s['year']) <= 2026]
nums = dict(papers_scored=len(S), post_chatgpt=len(post))


def extent(V):
    c = V.mean(0); return float(np.sqrt(((V - c) ** 2).sum(1)).max())


km = KMeans(50, n_init=4, random_state=20261022).fit(X[[key_idx[s['key']] for s in post]])


def entropy(V):
    lab = km.predict(V); p = np.bincount(lab, minlength=50) / len(lab); p = p[p > 0]
    return float(-(p * np.log(p)).sum())


draws = {}
for sc in SCHOOLS + ['all']:
    rows = [s for s in post if sc == 'all' or s['school'] == sc]
    ai = np.array([key_idx[s['key']] for s in rows if s['flagged']]); no = np.array([key_idx[s['key']] for s in rows if not s['flagged']])
    n = int(min(1000, 0.8 * min(len(ai), len(no))))  # below both group sizes, so every draw varies in both groups
    if n < 30:
        continue
    d = {'ai': ([], []), 'not': ([], [])}
    for _ in range(1000):
        for g, ids in (('ai', ai), ('not', no)):
            V = X[rng.choice(ids, n, replace=False)]
            d[g][0].append(extent(V)); d[g][1].append(entropy(V))
    draws[sc] = dict(n=n, flagged=len(ai), not_flagged=len(no), d=d)
    nums[sc] = dict(n_per_draw=n, flagged=len(ai), not_flagged=len(no),
                    extent_ai_median=float(np.median(d['ai'][0])), extent_not_median=float(np.median(d['not'][0])),
                    extent_ai_lower_share=float(np.mean(np.array(d['ai'][0]) < np.array(d['not'][0]))),
                    entropy_ai_median=float(np.median(d['ai'][1])), entropy_not_median=float(np.median(d['not'][1])),
                    entropy_ai_lower_share=float(np.mean(np.array(d['ai'][1]) < np.array(d['not'][1]))))

# B: t-SNE
ai_all = [key_idx[s['key']] for s in post if s['flagged']]; no_all = [key_idx[s['key']] for s in post if not s['flagged']]
k = min(5000, len(ai_all), len(no_all))
ids = np.concatenate([rng.choice(ai_all, k, replace=False), rng.choice(no_all, k, replace=False)]); lab = np.array([1] * k + [0] * k)
Y = TSNE(2, perplexity=30, init='pca', random_state=20261022).fit_transform(X[ids])
fig = plt.figure(figsize=(13, 4.6))
ax = fig.add_axes([0.03, 0.1, 0.3, 0.8])
for g, c, name in ((0, C_NOT, 'Not flagged'), (1, C_AI, 'AI-written (flagged)')):
    P = Y[lab == g]; ax.scatter(P[:, 0], P[:, 1], s=2.5, c=c, alpha=0.35, linewidths=0, label=name)
for g, c in ((0, C_NOT), (1, C_AI)):
    P = Y[lab == g]; cen = P.mean(0); r = np.quantile(np.sqrt(((P - cen) ** 2).sum(1)), 0.95)
    ax.add_patch(plt.Circle(cen, r, fill=False, ec=c, lw=2, ls='--'))
    ax.scatter([cen[0]], [cen[1]], s=90, c=c, edgecolors=SURF, linewidths=2, zorder=5)
ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
ax.set_title(f'B  SPECTER2 space, t-SNE (2023–2026, {k:,} + {k:,} papers)', loc='left', color=INK, fontsize=9.5)
ax.legend(loc='lower left', frameon=False, markerscale=5, fontsize=8)
for j, (panel, idx, ylab) in enumerate((('C  Knowledge extent', 0, 'max distance to centroid'), ('D  Knowledge entropy', 1, 'entropy over 50 topic clusters (nats)'))):
    ax = fig.add_axes([0.39 + j * 0.31, 0.16, 0.27, 0.72]); names = [sc for sc in SCHOOLS + ['all'] if sc in draws]
    for i, sc in enumerate(names):
        for off, g, c in ((-0.18, 'not', C_NOT), (0.18, 'ai', C_AI)):
            bp = ax.boxplot(draws[sc]['d'][g][idx], positions=[i + off], widths=0.3, whis=1.5, showfliers=False, patch_artist=True)
            for b in bp['boxes']:
                b.set(facecolor=c, edgecolor=c, alpha=0.85)
            for part in ('whiskers', 'caps', 'medians'):
                for l in bp[part]:
                    l.set(color=INK if part == 'medians' else c, linewidth=1.2)
    ax.set_xticks(range(len(names))); ax.set_xticklabels([f"{LABEL[sc]}\nn={draws[sc]['n']}" for sc in names], fontsize=8)
    ax.set_ylabel(ylab); ax.set_title(panel + ' (1,000 equal-size draws per group)', loc='left', color=INK, fontsize=9.5); ax.grid(axis='x', visible=False)
fig.text(0.39, 0.015, 'Blue: not flagged · Orange: flagged as AI-written. Lab papers of 2023–2026; detector threshold at a 1% false-positive\nrate on pre-ChatGPT abstracts. Each draw takes n papers per group (at most 80% of the smaller group).',
         color=MUTED, fontsize=8)
fig.savefig(OUT / 'fig3_ai_written.png', dpi=200); plt.close(fig)

# E: flagged share by year (pre-ChatGPT = false-positive rate)
fig, ax = plt.subplots(figsize=(6.4, 3.4))
years = list(range(2016, 2027)); CAT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4']
rate = {}
for sc, c in zip(SCHOOLS, CAT):
    by = collections.defaultdict(list)
    for s in S:
        if s['school'] == sc:
            by[int(s['year'])].append(s['flagged'])
    r = [100 * np.mean(by[y]) if by[y] else np.nan for y in years]; rate[sc] = r
    ax.plot(years, r, color=c, lw=2, marker='o', ms=4, label=LABEL[sc])
ends = sorted(((rate[sc][-1], sc) for sc in SCHOOLS), reverse=True); placed = []  # direct end labels, nudged apart
for v, sc in ends:
    y = v
    while any(abs(y - q) < 2.2 for q in placed):
        y -= 2.2
    placed.append(y); ax.annotate(LABEL[sc], (years[-1], v), xytext=(years[-1] + 0.25, y), textcoords='data', color=INK, fontsize=8, va='center')
ax.set_xlim(2015.6, 2027.6)
ax.axhline(1, color=MUTED, lw=1, ls=':'); ax.annotate('design false-positive rate (1%)', (2016.6, 1), xytext=(0, -11), textcoords='offset points', color=MUTED, fontsize=7.5)
ax.axvline(2022.9, color=GRID, lw=1); ax.annotate('ChatGPT (Nov 2022)', (2022.9, 12), xytext=(-4, 0), textcoords='offset points', color=MUTED, fontsize=7.5, ha='right')
ax.set_ylabel('% of lab papers flagged as AI-written'); ax.set_xticks(years); ax.set_xticklabels([str(y)[2:] for y in years])
ax.set_title('E  Flagged share by year (2026 is a partial year)', loc='left', color=INK, fontsize=9.5); ax.legend(frameon=False, fontsize=7.5, loc='upper left')
fig.tight_layout(); fig.savefig(OUT / 'fig3e_flag_rate.png', dpi=200); plt.close(fig)
nums['flag_rate_by_year'] = {sc: dict(zip(years, [None if np.isnan(v) else round(float(v), 2) for v in r])) for sc, r in rate.items()}
json.dump(nums, open(OUT / 'fig3_numbers.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in nums.items() if k != 'flag_rate_by_year'}, indent=1))
