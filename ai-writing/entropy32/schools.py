"""Every figure, per school (owner 2026-11-23: "for the 1000 per school, make sure we have all the figures from above").

A school qualifies with >= MIN_POST scored and embedded full texts in 2023-2025. Each gets a view directory WORK/schools/<school>/ holding its own
papers_scored.parquet (its home-school papers), links to the shared vectors, run metadata and citation ages, and its own analysis/ and figures/.
Every stage of analyze.py runs on the view with the ALL-schools 50 topic clusters (looked up by paper key), so entropy is on one scale for every
school. A stage a school is too small for is logged and skipped; the rest still run. Each saved figure carries the school's name in its corner.
usage: schools.py prep | run <school> | list | index      (Slurm: e32_schools.slurm, one array task per school)
"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze as A  # noqa: E402
import e32  # noqa: E402

MIN_POST = 1000
STAGES = ['curve', 'paper', 'lab', 'map', 'figure', 'timeband', 'distshift', 'entropy_scale', 'centroid', 'entropy_full', 'fullsample', 'allyears']
LABEL = {'cmu': 'CMU', 'mit': 'MIT', 'epfl': 'EPFL', 'gatech': 'Georgia Tech', 'hkust': 'HKUST', 'ntu': 'NTU', 'nus': 'NUS', 'pku': 'Peking',
         'sjtu': 'SJTU', 'cuhk': 'CUHK', 'zju': 'Zhejiang', 'jhu': 'Johns Hopkins', 'utaustin': 'UT Austin', 'uchicago': 'UChicago', 'vt': 'Virginia Tech'}


def base(a):
    return e32.work_dir(a.id)


def eligible(a):
    d = pd.read_parquet(base(a) / 'papers_scored.parquet', columns=['home_school', 'year', 'has_emb', 'ai_share_main'])
    d = d[d.has_emb & d.ai_share_main.notna() & d.year.between(2023, 2025)]
    n = d.home_school.value_counts()
    return n[n >= MIN_POST].sort_values(ascending=False)


def cmd_prep(a):
    B = base(a)
    P = pd.read_parquet(B / 'papers_scored.parquet')
    w, df, X = A.load(a)                     # refresh the all-schools cluster caches (adds the paper keys)
    for m in A.METRICS:
        A.clusters(w, df, X, m)
    el = eligible(a)
    for s in el.index:
        v = B / 'schools' / s
        (v / 'analysis').mkdir(parents=True, exist_ok=True); (v / 'figures').mkdir(exist_ok=True)
        P[P.home_school == s].to_parquet(v / 'papers_scored.parquet')
        for name in ('X_specter2_base.npy', 'RUN.json', 'citeage'):
            link = v / name
            if not link.exists():
                link.symlink_to(B / name)
    (B / 'schools' / 'SCHOOLS.json').write_text(json.dumps({s: int(n) for s, n in el.items()}, indent=1))
    print(json.dumps(dict(schools=len(el), list=list(el.index))))


def global_clusters(a):
    out = {}
    for m in A.METRICS:
        z = np.load(base(a) / 'analysis' / f'clusters_{m}.npz')
        out[m] = (dict(zip(z['keys'].astype(str), z['labels'])), z['centers'])
    return out


def cmd_run(a):
    import matplotlib.figure as MF
    s = a.school
    if s is None:   # array task beyond the eligible list (the refresh submits a fixed 0-39 range)
        print('no school for this array index'); return
    v = base(a) / 'schools' / s
    A.GLOBAL_CLUSTERS = global_clusters(a)
    # one school is ~1-10k papers: smaller equal-size draws and cell minimums than the all-schools run (still equal within the school)
    A.BAND_N, A.BAND_MIN, A.SCALE_N, A.ALLY_MIN = 50, 60, 300, 60
    e32.work_dir = lambda run_id, _v=v: _v               # every stage reads and writes the school's view
    name = LABEL.get(s, s.capitalize())
    orig = MF.Figure.savefig

    def savefig(self, *x, **k):                            # the school's name on every figure
        if not getattr(self, '_school_banner', False):
            self.text(0.995, 0.995, name, ha='right', va='top', fontsize=15, fontweight='bold', color='#2a78d6')
            self._school_banner = True
        return orig(self, *x, **k)
    MF.Figure.savefig = savefig
    log = {}
    for st in STAGES:
        try:
            if st == 'figure':
                import figure
                figure.main(v)
            else:
                getattr(A, 'stage_' + st)(a)
            log[st] = 'ok'
        except Exception as e:  # noqa: BLE001  a school too small for one stage still gets the others
            log[st] = f'{type(e).__name__}: {e}'[:300]
            traceback.print_exc()
        print(json.dumps(dict(school=s, stage=st, result=log[st])), flush=True)
    (v / 'STAGES.json').write_text(json.dumps(log, indent=1))


def _bands(v):
    band = np.full(len(v), -1)
    for j, (lo, hi, _) in enumerate(A.BANDS):
        band[(v == 0) if hi == 0 else ((v >= lo) & (v <= hi) if j == len(A.BANDS) - 1 else (v >= lo) & (v < hi))] = j
    return band


def _multiples(D, order, value, title, subtitle, ylabel, foot, out, counts, corner_fmt, ylim=None, cap=None):
    """Small multiples by school (the 'All' panel first, shared y): value by AI band with 95% bars; panel title = school and its 2023-25 paper count;
    each x tick = the band and its paper count; corner = highest band minus 0% band."""
    import figure as FG
    plt = FG.plt
    nc = 6
    nr = int(np.ceil(len(order) / nc))
    H = 3.05 * nr + 1.7
    plt.rcParams.update({'font.size': 9.5})
    fig, axs = plt.subplots(nr, nc, figsize=(17, H), sharey=True)
    fig.subplots_adjust(left=0.05, right=0.99, top=1 - 1.45 / H, bottom=0.85 / H, hspace=0.75, wspace=0.08)
    fig.text(0.05, 1 - 0.35 / H, title, fontsize=17, fontweight='bold', color=FG.INK)
    fig.text(0.05, 1 - 0.68 / H, subtitle, fontsize=10, color=FG.INK2, va='top')
    for i, ax in enumerate(axs.flat):
        if i >= len(order):
            ax.axis('off'); continue
        s = order[i]
        x = D[D.school == s].sort_values('band_i')
        if s == 'ALL':
            ax.set_facecolor('#efefeb')
        hi = 1.96 * x.se if cap is None else np.minimum(1.96 * x.se, cap - x[value])
        ax.errorbar(x.band_i, x[value], yerr=[1.96 * x.se, hi], color=FG.BLUE, lw=2, marker='o', ms=5.5, mec=FG.SURF, mew=1.2, elinewidth=1.2, capsize=0)
        if len(x) >= 2 and 0 in x.band_i.values:
            z, h = x[x.band_i == 0].iloc[0], x.iloc[-1]
            ax.text(0.97, 0.93, corner_fmt(h[value] - z[value]), transform=ax.transAxes, ha='right', va='top', fontsize=10, fontweight='bold', color=FG.INK)
        nb = dict(zip(x.band_i, x.papers))
        ax.set_title(('All 32 schools' if s == 'ALL' else LABEL.get(s, s.capitalize())) + f'  ·  {counts[s]:,} papers', fontsize=10.5)
        ax.set_xticks(range(len(A.BANDS)))
        ax.set_xticklabels([f'{b}\n{nb[j]:,}' if j in nb else f'{b}\n<min' for j, (_, _, b) in enumerate(A.BANDS)], fontsize=7.3)
        ax.set_xlim(-0.4, len(A.BANDS) - 0.6); ax.grid(axis='x', visible=False)
        if ylim:
            ax.set_ylim(*ylim)
        if cap is not None:
            ax.axhline(cap, color=FG.MUTED, lw=0.8, ls=(0, (2, 2)))
        if i % nc == 0:
            ax.set_ylabel(ylabel)
    fig.text(0.05, 0.25 / H, foot, fontsize=8.5, color=FG.MUTED)
    fig.savefig(out, dpi=200); fig.savefig(out.with_suffix('.pdf')); plt.close(fig)
    print(json.dumps(dict(figure=str(out))))


def _school_counts(d, sch):
    c = {s: int((d.home_school == s).sum()) for s in sch}
    c['ALL'] = len(d)
    return c


def cmd_cosine_fig(a, metric='cosine'):
    """Knowledge entropy (cosine clusters, the all-schools 50) by amount of AI, per school (small multiples, shared y), 2023-2025 full texts:
    every paper of each AI band (Miller-Madow), bands re-weighted to the school's 0% papers' year mix, +-1.96 bootstrap SE; bands under BAND_FLOOR
    papers left out. -> WORK/analysis/schools_entropy_<metric>.csv, WORK/figures/schools_entropy_<metric>.png"""
    w, df, X = A.load(a)
    lab, _ = A.clusters(w, df, X, metric)
    r = np.random.default_rng(A.SEED)
    post = df.year.between(2023, 2025).values
    d = df[post].reset_index(drop=True)
    lab = lab[post]
    d['band'] = _bands(d.ai_share_main.values)
    sch = json.loads((base(a) / 'schools' / 'SCHOOLS.json').read_text())
    rows = []
    for s in ['ALL'] + list(sch):
        m = np.ones(len(d), bool) if s == 'ALL' else (d.home_school.values == s)
        tgt = d.year[m & (d.band.values == 0)].value_counts(normalize=True)
        for j, (_, _, name) in enumerate(A.BANDS):
            ix = np.flatnonzero(m & (d.band.values == j))
            if len(ix) < BAND_FLOOR:
                continue
            # unweighted: re-weighting a band of 100-300 papers to a year mix shrinks its effective size until the small-sample correction overshoots
            # (UT Austin's 50%+ band came out above ln 50); estimates are capped at the maximum, ln K
            mm = min(A.ent_mm(lab[ix])[1], np.log(A.K))
            bs = [A.ent_mm(lab[ix][i])[1] for i in (r.integers(0, len(ix), len(ix)) for _ in range(200))]
            rows.append(dict(school=s, band=name, band_i=j, papers=len(ix), entropy=mm, se=float(np.std(bs))))
    D = pd.DataFrame(rows)
    D.to_csv(w / 'analysis' / f'schools_entropy_{metric}.csv', index=False)
    order = ['ALL'] + list(sch)
    _multiples(D, order, 'entropy', f'Knowledge entropy by amount of AI-written text, per school ({metric})',
               f'Full-text lab papers 2023–2025. Entropy of EVERY paper in each AI band of the main body over the same 50 {metric} topic clusters for all schools '
               '(Miller–Madow small-sample correction;\nbands of 100+ papers; capped at the maximum ln 50 = 3.91; bars ± 1.96 bootstrap SE). Higher = spread over more topics.',
               'knowledge entropy (nats)',
               f'Number in each corner: the highest AI band minus the 0% band (nats). Under each band: its papers; bands with fewer than {BAND_FLOOR} papers are left out ("<min"). '
               'A single school sits below the pooled panel because one school covers fewer topics.',
               w / 'figures' / f'schools_entropy_{metric}.png', _school_counts(d, sch), lambda v: f'{v:+.2f}', ylim=(2.7, 3.97), cap=np.log(A.K))


BAND_FLOOR = 100


def cmd_citeage_fig(a):
    """Average citation age by amount of AI, per school (small multiples, shared y), 2023-2025 full-text papers: the mean of the papers' average citation age
    per AI band, re-weighted to the school's 0% papers' year mix, 95% interval from the weighted SE; bands with < 30 papers with dated references left out.
    -> WORK/analysis/schools_citeage.csv, WORK/figures/schools_citeage.png"""
    B = base(a)
    d = pd.read_parquet(B / 'papers_scored.parquet', columns=['k', 'home_school', 'year', 'has_emb', 'ai_share_main'])
    d = d[d.has_emb & d.ai_share_main.notna() & d.year.between(2023, 2025)]
    sch = json.loads((B / 'schools' / 'SCHOOLS.json').read_text())
    counts = _school_counts(d, sch)
    ca = pd.read_parquet(B / 'citeage' / 'citeage.parquet', columns=['k', 'cite_age_mean'])
    d = d.merge(ca, on='k', how='left').dropna(subset=['cite_age_mean'])
    d['band'] = _bands(d.ai_share_main.values)
    rows = []
    for s in ['ALL'] + list(sch):
        g = d if s == 'ALL' else d[d.home_school == s]
        tgt = g[g.band == 0].year.value_counts(normalize=True)
        for j, (_, _, name) in enumerate(A.BANDS):
            x = g[g.band == j]
            if len(x) < 30:
                continue
            sh = x.year.value_counts(normalize=True)
            wt = np.nan_to_num(tgt.reindex(x.year).values / sh.reindex(x.year).values) if j else np.ones(len(x))
            if wt.sum() == 0:
                continue
            m = np.average(x.cite_age_mean, weights=wt)
            var = np.average((x.cite_age_mean - m) ** 2, weights=wt)
            neff = wt.sum() ** 2 / (wt ** 2).sum()
            rows.append(dict(school=s, band=name, band_i=j, papers=len(x), cite_age=float(m), se=float(np.sqrt(var / neff))))
    D = pd.DataFrame(rows)
    (B / 'analysis').mkdir(exist_ok=True)
    D.to_csv(B / 'analysis' / 'schools_citeage.csv', index=False)
    _multiples(D, ['ALL'] + list(sch), 'cite_age', 'Average citation age by amount of AI-written text, per school',
               'Full-text lab papers 2023–2025. Years between each paper and the works it cites (OpenAlex), averaged over the papers in each AI band of the main body;\n'
               'bands re-weighted to the school\'s 0% papers\' year mix; bars 95% CI. Lower = cites more recent work.',
               'citation age (years)',
               'Number in each corner: the highest AI band minus the 0% band (years). Under each band: its papers with dated references; bands with fewer than 30 are left out ("<min"). '
               'Title: all 2023–25 full-text papers of the school.',
               B / 'figures' / 'schools_citeage.png', counts, lambda v: f'{v:+.1f} y')


def cmd_list(a):
    for s in json.loads((base(a) / 'schools' / 'SCHOOLS.json').read_text()):
        print(s)


def cmd_index(a):
    """A table of which figure exists for which school -> schools/FIGURES.md"""
    B = base(a) / 'schools'
    sch = json.loads((B / 'SCHOOLS.json').read_text())
    figs = sorted({f.name for s in sch for f in (B / s / 'figures').glob('*.png')})
    lines = ['| school | 2023–25 papers | ' + ' | '.join(f.replace('.png', '') for f in figs) + ' |', '|' + '---|' * (len(figs) + 2)]
    for s, n in sch.items():
        lines.append(f'| {s} | {n:,} | ' + ' | '.join('✓' if (B / s / 'figures' / f).exists() else '—' for f in figs) + ' |')
    (B / 'FIGURES.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['prep', 'run', 'list', 'index', 'cosine_fig', 'citeage_fig'])
    ap.add_argument('school', nargs='?')
    ap.add_argument('--id', default='20261123')
    a = ap.parse_args()
    if a.cmd == 'run' and not a.school:
        a.school = json.loads((base(a) / 'schools' / 'SCHOOLS.json').read_text()).__iter__().__next__() if os.environ.get('SLURM_ARRAY_TASK_ID') is None else \
            (list(json.loads((base(a) / 'schools' / 'SCHOOLS.json').read_text())) + [None] * 64)[int(os.environ['SLURM_ARRAY_TASK_ID'])]
    globals()['cmd_' + a.cmd](a)


if __name__ == '__main__':
    main()
