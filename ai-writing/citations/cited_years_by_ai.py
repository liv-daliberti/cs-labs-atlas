"""When were the cited works published? Per citing year (2022-2025), lab papers split into AI-detected (paragraph
ai_share >= 0.25, the full-text passage detector) and not, and for each group the distribution of the publication
years of the works they cite, oldest to newest.

weights   every citing paper counts once: its references with a known publication year share a weight of 1, so long
          reference lists do not dominate a group
data      references and cited-work years from the citation caches (read-only, /n/fs/resemble/cs-atlas-cache/citations/):
          Semantic Scholar (s2fetch.py: parsed from the PDFs, so arXiv-only papers have them) and OpenAlex (fetch.py:
          mostly publisher deposits); per paper the list with more references of known year is used. Citing year from
          ai-writing/papers.jsonl.gz. Papers with no reference list in either are left out; panel C shows what share of
          each group that leaves in
summary   per group and citing year: papers, the median reference age (citing year - cited year) and the share of
          references from the last two years, with 95% bootstrap intervals over citing papers
-> figures/cited_years_by_ai.png, results/cited_years_by_ai.csv
usage: cited_years_by_ai.py
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import ast, csv, gzip, json, sqlite3, zlib
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent; AIW = HERE.parent
OADB = str(P.CACHE / 'citations/openalex.sqlite')
S2DB = str(P.CACHE / 'citations/s2.sqlite')
YEARS = [2022, 2023, 2024, 2025]   # the owner's figure: 2022-2025 (2026 is a partial year)
LO = 2000    # the curves start here; the share of older references is given in the legend
MIN_N = 30   # a group smaller than this gets no curve
C_LESS, C_MORE = '#2a78d6', '#eb6834'
INK, INK2, MUTED, GRID, SURF = '#1d2a33', '#46525a', '#68747c', '#e3e5e0', '#fcfcfb'
SEED = 20261022
GROUPS = ((False, C_LESS, 'not AI-detected'), (True, C_MORE, 'AI-detected'))


def blob(d):
    try:
        return json.loads(zlib.decompress(d))
    except Exception:
        return json.loads(d)


def as_list(v):
    if isinstance(v, list):
        return v
    try:
        return ast.literal_eval(v) if v else []
    except (ValueError, SyntaxError):
        return []


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
    wy = {}
    for w, d in db.execute('select wid, data from works where status = 1'):
        y = blob(d).get('publication_year')
        if y:
            wy[w.rsplit('/', 1)[-1]] = int(y)
    oa = {}
    for k, d in db.execute('select key, data from citing where status = 1'):
        refs = [r.rsplit('/', 1)[-1] for r in as_list(blob(d).get('referenced_works'))]
        oa[k] = [wy[r] for r in refs if r in wy]
    s2 = {}
    sdb = sqlite3.connect(f'file:{S2DB}?mode=ro', uri=True, timeout=60)
    for k, d in sdb.execute('select key, data from refs where status = 1'):
        s2[k] = [int(r['year']) for r in (blob(d).get('references') or []) if r.get('year')]
    rows, scored = [], defaultdict(int)  # rows: (citing year, flagged, cited years, source)
    for k, f in ai.items():
        if year.get(k) not in YEARS:
            continue
        scored[(year[k], f)] += 1
        a, b = oa.get(k) or [], s2.get(k) or []
        ys, src = (b, 's2') if len(b) >= len(a) else (a, 'oa')
        if ys:
            rows.append((year[k], f, np.array(ys), src))
    return rows, scored, len(s2)


def boot(vals, n=1000):
    r = np.random.default_rng(SEED); vals = np.asarray(vals)
    b = [vals[r.integers(0, len(vals), len(vals))].mean() for _ in range(n)]
    return float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))


def style(ax):
    ax.set_facecolor(SURF); ax.grid(axis='y', color=GRID, lw=0.8); ax.grid(axis='x', visible=False)
    ax.tick_params(labelsize=7.5, colors=INK2)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)


def main():
    rows, scored, n_s2 = load()
    fig = plt.figure(figsize=(16, 9), facecolor=SURF)
    gs = fig.add_gridspec(2, 12, height_ratios=[1.35, 1], hspace=0.45, wspace=1.2, left=0.06, right=0.985, top=0.9, bottom=0.17)
    out, summ = [], defaultdict(dict)
    top = [fig.add_subplot(gs[0, 3 * j:3 * j + 3]) for j in range(len(YEARS))]
    for j, cy in enumerate(YEARS):
        ax = top[j]; style(ax)
        bins = np.arange(LO, cy + 2)
        for flag, col, name in GROUPS:
            g = [ys for y, f, ys, _ in rows if y == cy and f == flag]
            if not g:
                continue
            age = [float(np.median(cy - ys)) for ys in g]
            recent = [float(np.mean(cy - ys <= 2)) for ys in g]
            old = float(np.mean([np.mean(ys < LO) for ys in g]))
            summ[cy][flag] = dict(n=len(g), age=float(np.mean(age)), age_ci=boot(age), recent=float(np.mean(recent)), recent_ci=boot(recent))
            out.append(dict(citing_year=cy, group=name, papers=len(g), papers_scored=scored[(cy, flag)], mean_median_ref_age=round(float(np.mean(age)), 3),
                            age_ci=[round(x, 3) for x in boot(age)], share_refs_last_2y=round(float(np.mean(recent)), 4),
                            recent_ci=[round(x, 4) for x in boot(recent)], share_refs_before_2000=round(old, 4)))
            if len(g) < MIN_N:
                ax.text(0.03, 0.62 if flag else 0.7, f'{name}: only {len(g)} papers, no curve', transform=ax.transAxes, fontsize=7, color=col)
                continue
            h = np.zeros(len(bins) - 1)
            for ys in g:
                h += np.histogram(ys, bins=bins)[0] / len(ys)
            h /= len(g)
            ax.plot(bins[:-1], h, color=col, lw=2, label=f'{name} (n={len(g):,}; {old:.0%} before {LO})')
            ax.fill_between(bins[:-1], h, color=col, alpha=0.12, lw=0)
        ax.set_xlim(LO, cy); ax.set_xticks([x for x in (2000, 2005, 2010, 2015, 2020, 2025) if x <= cy])
        ax.set_title(f'Papers from {cy}', loc='left', fontsize=10, color=INK)
        ax.set_xlabel('publication year of the cited work', fontsize=8, color=INK2)
        if j == 0:
            ax.set_ylabel("share of a paper's references\n(each paper weighted equally)", fontsize=8.5, color=INK2)
        ax.legend(frameon=False, fontsize=6.9, loc='upper left')
    ymax = max(a.get_ylim()[1] for a in top) * 1.12
    for a in top:
        a.set_ylim(0, ymax)
    fig.text(0.06, 0.95, 'A  Publication years of the works cited, AI-detected vs other lab papers, by the year of the citing paper',
             fontsize=11.5, color=INK)
    # B, C, D: summaries by citing year
    panels = (('B  Median reference age (years)', 'age', 'age_ci', gs[1, 0:4]),
              ('C  Share of references from the last 2 years', 'recent', 'recent_ci', gs[1, 4:8]))
    for title, key, ci, spec in panels:
        ax = fig.add_subplot(spec); style(ax)
        for flag, col, name in GROUPS:
            xs = [cy for cy in YEARS if flag in summ[cy] and summ[cy][flag]['n'] >= MIN_N]
            v = np.array([summ[cy][flag][key] for cy in xs]); lo = np.array([summ[cy][flag][ci][0] for cy in xs]); hi = np.array([summ[cy][flag][ci][1] for cy in xs])
            ax.errorbar(np.array(xs) + (0.08 if flag else -0.08), v, yerr=[v - lo, hi - v], fmt='o-', color=col, ms=5, lw=1.6, capsize=2.5, label=name)
        ax.set_xticks(YEARS); ax.set_xlabel('year of the citing paper', fontsize=8, color=INK2); ax.set_title(title, loc='left', fontsize=10, color=INK)
        ax.legend(frameon=False, fontsize=7.5)
    ax = fig.add_subplot(gs[1, 9:12]); style(ax)
    for flag, col, name in GROUPS:
        xs = [cy for cy in YEARS if scored[(cy, flag)] >= MIN_N]
        ax.plot(xs, [summ[cy].get(flag, {}).get('n', 0) / scored[(cy, flag)] for cy in xs], 'o-', color=col, lw=1.6, ms=5, label=name)
    ax.set_ylim(0, 1.05); ax.set_xticks(YEARS); ax.set_xlabel('year of the citing paper', fontsize=8, color=INK2)
    ax.set_title('D  Papers with a reference list', loc='left', fontsize=10, color=INK); ax.legend(frameon=False, fontsize=7.5)
    fig.text(0.06, 0.035, 'AI-detected = paragraph ai_share ≥ 0.25 from the full-text passage detector (the detector flags 0.1–0.3% of pre-2023 papers, so 2022 has almost none). '
             'Reference lists: Semantic Scholar (parsed from the PDF) or OpenAlex,\nwhichever has more references with a known year; '
             f'S2 reference lists: {n_s2:,} (complete). Papers without any list are left out (D). B and C: per-paper median age and share of recent references, '
             'mean over papers with 95% bootstrap intervals.', fontsize=7.6, color=MUTED)
    (HERE / 'figures').mkdir(exist_ok=True); (HERE / 'results').mkdir(exist_ok=True)
    fig.savefig(HERE / 'figures' / 'cited_years_by_ai.png', dpi=160, facecolor=SURF); plt.close(fig)
    with open(HERE / 'results' / 'cited_years_by_ai.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    for r in out:
        print(r['citing_year'], f"{r['group']:16}", r['papers'], '/', r['papers_scored'], 'age', r['mean_median_ref_age'], 'recent', r['share_refs_last_2y'])


if __name__ == '__main__':
    main()
