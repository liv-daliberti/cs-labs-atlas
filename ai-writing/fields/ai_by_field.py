"""Where are the AI-detected lab papers? AI detection against OpenAlex's labelled research areas, 2023-2026.

papers    lab papers of 2023-2026 with a full-text passage score (ai-writing/paragraph_scores.jsonl.gz); AI-detected =
          ai_share >= 0.25
labels    OpenAlex primary_topic of each paper (topic < subfield < field < domain), from the citation study's cache
          (/n/fs/resemble/cs-atlas-cache/citations/openalex.sqlite, table citing; read-only)
A         AI-detected rate per subfield (the 20 largest; the rest pooled as 'other'), 95% Wilson intervals
B         the same subfields: share of all AI-detected papers vs share of all other papers that sit there
          (over-represented when the orange dot is right of the blue one)
C         topics (finer labels, >= MIN_TOPIC papers): the highest and the lowest AI-detected rates
D         AI-detected rate by subfield and year
-> figures/ai_by_field.png, results/ai_by_subfield.csv, results/ai_by_topic.csv
usage: ai_by_field.py
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import csv, gzip, json, sqlite3, zlib
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

HERE = Path(__file__).resolve().parent; AIW = HERE.parent
OADB = str(P.CACHE / 'citations/openalex.sqlite')
YEARS = [2023, 2024, 2025, 2026]
N_SUB, MIN_TOPIC, N_TOPIC = 20, 40, 14
C_LESS, C_MORE = '#2a78d6', '#eb6834'
INK, INK2, MUTED, GRID, SURF = '#1d2a33', '#46525a', '#68747c', '#e3e5e0', '#fcfcfb'


def blob(d):
    try:
        return json.loads(zlib.decompress(d))
    except Exception:
        return json.loads(d)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def load():
    ai = {}
    for l in gzip.open(AIW / 'paragraph_scores.jsonl.gz', 'rt'):
        r = json.loads(l); ai[r['key']] = r['ai_share'] >= 0.25
    year = {}
    for l in gzip.open(AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(l)
        try:
            year[p['key']] = int(p.get('year'))
        except (TypeError, ValueError):
            pass
    db = sqlite3.connect(f'file:{OADB}?mode=ro', uri=True, timeout=60)
    rows, n_scored = [], 0
    lab = {k for k in ai if year.get(k) in YEARS}
    n_scored = len(lab)
    for k, d in db.execute('select key, data from citing where status = 1'):
        if k not in lab:
            continue
        pt = blob(d).get('primary_topic') or {}
        if not pt:
            continue
        rows.append(dict(key=k, year=year[k], ai=ai[k], topic=pt['display_name'], subfield=pt['subfield']['display_name'],
                         field=pt['field']['display_name']))
    return rows, n_scored


def style(ax):
    ax.set_facecolor(SURF); ax.tick_params(labelsize=7.6, colors=INK2)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)


def main():
    rows, n_scored = load()
    n, n_ai = len(rows), sum(r['ai'] for r in rows)
    overall = n_ai / n
    cnt = Counter(r['subfield'] for r in rows)
    top = [s for s, _ in cnt.most_common(N_SUB)]
    for r in rows:
        r['sub'] = r['subfield'] if r['subfield'] in top else 'other'
    subs = top + ['other']
    k_ = Counter(r['sub'] for r in rows if r['ai']); n_ = Counter(r['sub'] for r in rows)
    rate = {s: k_[s] / n_[s] for s in subs}
    order = sorted(subs, key=lambda s: rate[s])  # bottom to top: highest rate at the top
    out_sub = [dict(subfield=s, papers=n_[s], ai_detected=k_[s], rate=round(rate[s], 4), ci=[round(x, 4) for x in wilson(k_[s], n_[s])],
                    share_of_ai=round(k_[s] / n_ai, 4), share_of_other=round((n_[s] - k_[s]) / (n - n_ai), 4)) for s in subs]

    fig = plt.figure(figsize=(16, 13.5), facecolor=SURF)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], width_ratios=[1.15, 1], hspace=0.28, wspace=0.62, left=0.235, right=0.97, top=0.93, bottom=0.08)
    y = np.arange(len(order))
    # A: rate per subfield
    ax = fig.add_subplot(gs[0, 0]); style(ax)
    lo = np.array([wilson(k_[s], n_[s])[0] for s in order]); hi = np.array([wilson(k_[s], n_[s])[1] for s in order]); v = np.array([rate[s] for s in order])
    ax.barh(y, v, color=C_MORE, alpha=0.85, height=0.62)
    ax.errorbar(v, y, xerr=[v - lo, hi - v], fmt='none', ecolor=INK2, lw=0.9, capsize=2)
    ax.axvline(overall, color=INK2, ls='--', lw=1); ax.text(overall, len(order) - 0.2, f' all: {overall:.0%}', fontsize=7.5, color=INK2, va='bottom')
    ax.set_yticks(y); ax.set_yticklabels([f'{s}  (n={n_[s]:,})' for s in order], fontsize=7.8)
    ax.set_xlabel('share of papers AI-detected', fontsize=8.5, color=INK2); ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))
    ax.grid(axis='x', color=GRID, lw=0.8); ax.grid(axis='y', visible=False)
    ax.set_title('A  AI-detected rate by research area (OpenAlex subfield)', loc='left', fontsize=10.5, color=INK)
    # B: where each group sits
    ax = fig.add_subplot(gs[0, 1]); style(ax)
    sa = np.array([k_[s] / n_ai for s in order]); so = np.array([(n_[s] - k_[s]) / (n - n_ai) for s in order])
    for i in range(len(order)):
        ax.plot([so[i], sa[i]], [i, i], color=GRID, lw=2.2, zorder=1)
    ax.scatter(so, y, s=42, color=C_LESS, zorder=3, label=f'not AI-detected ({n - n_ai:,})', edgecolors=SURF, linewidths=1)
    ax.scatter(sa, y, s=42, color=C_MORE, zorder=4, label=f'AI-detected ({n_ai:,})', edgecolors=SURF, linewidths=1)
    for i, s in enumerate(order):
        r_ = sa[i] / so[i] if so[i] else np.nan
        ax.text(max(sa[i], so[i]) + 0.004, i, f'×{r_:.1f}', fontsize=7, color=INK if r_ >= 1.25 or r_ <= 0.8 else MUTED, va='center')
    ax.set_yticks(y); ax.set_yticklabels([])
    ax.set_xlabel("share of the group's papers in this area", fontsize=8.5, color=INK2); ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))
    ax.grid(axis='x', color=GRID, lw=0.8); ax.grid(axis='y', visible=False); ax.legend(frameon=False, fontsize=7.6, loc='lower right')
    ax.set_title('B  Where each group sits (×: AI-detected share ÷ other share)', loc='left', fontsize=10.5, color=INK)
    # C: topics with the highest and lowest rates
    tk = Counter(r['topic'] for r in rows if r['ai']); tn = Counter(r['topic'] for r in rows)
    ts = [t for t in tn if tn[t] >= MIN_TOPIC]
    tr = sorted(ts, key=lambda t: tk[t] / tn[t])
    pick = tr[:N_TOPIC // 2] + tr[-N_TOPIC:]
    pick = list(dict.fromkeys(pick))
    out_top = [dict(topic=t, papers=tn[t], ai_detected=tk[t], rate=round(tk[t] / tn[t], 4), ci=[round(x, 4) for x in wilson(tk[t], tn[t])]) for t in sorted(ts, key=lambda t: -tk[t] / tn[t])]
    ax = fig.add_subplot(gs[1, 0]); style(ax)
    v = np.array([tk[t] / tn[t] for t in pick]); lo = np.array([wilson(tk[t], tn[t])[0] for t in pick]); hi = np.array([wilson(tk[t], tn[t])[1] for t in pick])
    yy = np.arange(len(pick))
    ax.barh(yy, v, color=[C_MORE if x >= overall else C_LESS for x in v], alpha=0.85, height=0.62)
    ax.errorbar(v, yy, xerr=[v - lo, hi - v], fmt='none', ecolor=INK2, lw=0.9, capsize=2)
    ax.axvline(overall, color=INK2, ls='--', lw=1)
    ax.axhline(N_TOPIC // 2 - 0.5, color=MUTED, lw=0.8, ls=':')
    ax.set_yticks(yy); ax.set_yticklabels([f'{t[:46]}  (n={tn[t]})' for t in pick], fontsize=7.4)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}')); ax.grid(axis='x', color=GRID, lw=0.8); ax.grid(axis='y', visible=False)
    ax.set_xlabel('share of papers AI-detected', fontsize=8.5, color=INK2)
    ax.set_title(f'C  Topics: the {N_TOPIC} highest and {N_TOPIC // 2} lowest rates (topics with ≥ {MIN_TOPIC} papers)', loc='left', fontsize=10.5, color=INK)
    # D: rate by subfield and year
    ax = fig.add_subplot(gs[1, 1]); style(ax)
    M = np.full((len(order), len(YEARS)), np.nan)
    for i, s in enumerate(order):
        for j, yv in enumerate(YEARS):
            g = [r['ai'] for r in rows if r['sub'] == s and r['year'] == yv]
            if len(g) >= 15:
                M[i, j] = np.mean(g)
    cmap = LinearSegmentedColormap.from_list('ai', ['#fbeee6', '#f3b48f', C_MORE, '#9a3d17'])
    im = ax.imshow(M, aspect='auto', cmap=cmap, vmin=0, vmax=np.nanmax(M), origin='lower')
    for i in range(len(order)):
        for j in range(len(YEARS)):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f'{M[i, j]:.0%}', ha='center', va='center', fontsize=6.8, color=SURF if M[i, j] > 0.6 * np.nanmax(M) else INK)
    ax.set_xticks(range(len(YEARS))); ax.set_xticklabels(YEARS); ax.set_yticks(range(len(order))); ax.set_yticklabels([s[:40] for s in order], fontsize=7)
    ax.grid(False); ax.set_title('D  AI-detected rate by subfield and year (cells with ≥ 15 papers)', loc='left', fontsize=10.5, color=INK)
    fig.text(0.235, 0.965, 'Where are the AI-detected lab papers? AI detection by research area, 2023–2026', fontsize=12.5, color=INK)
    fig.text(0.235, 0.02, f'Lab papers of 2023–2026 with a full-text passage score and an OpenAlex topic label: {n:,} of {n_scored:,}. AI-detected = paragraph ai_share ≥ 0.25 '
             f'({n_ai:,} papers, {overall:.1%}). Labels: OpenAlex primary_topic (topic < subfield < field).\n'
             'Intervals: 95% Wilson. B compares where the two groups sit; × > 1 means AI-detected papers are over-represented in that area.', fontsize=7.6, color=MUTED)
    for d in ('figures', 'results'):
        (HERE / d).mkdir(exist_ok=True)
    fig.savefig(HERE / 'figures' / 'ai_by_field.png', dpi=160, facecolor=SURF); plt.close(fig)
    for name, rows_ in (('ai_by_subfield.csv', out_sub), ('ai_by_topic.csv', out_top)):
        with open(HERE / 'results' / name, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows_[0])); w.writeheader(); w.writerows(rows_)
    print(json.dumps(dict(papers=n, scored=n_scored, ai=n_ai, overall=round(overall, 4))))
    for r in sorted(out_sub, key=lambda r: -r['rate']):
        print(f"{r['rate']:.3f} {r['papers']:6} x{r['share_of_ai'] / max(r['share_of_other'], 1e-9):.2f}  {r['subfield']}")


if __name__ == '__main__':
    main()
