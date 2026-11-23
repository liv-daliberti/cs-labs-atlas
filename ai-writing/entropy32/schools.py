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


def cmd_cosine_fig(a, metric='cosine'):
    """One figure: knowledge entropy (cosine clusters, the all-schools 50) per school, 2023-2025, for papers with 0% AI, some AI (< 25%) and heavy
    AI (>= 25%). Every paper of a group (Miller-Madow), AI groups re-weighted to the school's 0% papers' year mix, +-1.96 bootstrap SE.
    -> WORK/analysis/schools_entropy_<metric>.csv, WORK/figures/schools_entropy_<metric>.png"""
    import figure as FG
    plt = FG.plt
    w, df, X = A.load(a)
    lab, _ = A.clusters(w, df, X, metric)
    r = np.random.default_rng(A.SEED)
    post = df.year.between(2023, 2025).values
    s_ = df.ai_share_main.values
    G = [('0% AI', s_ == 0), ('some AI (< 25%)', (s_ > 0) & (s_ < .25)), ('heavy AI (≥ 25%)', s_ >= .25)]
    sch = json.loads((base(a) / 'schools' / 'SCHOOLS.json').read_text())
    rows = []
    for s in ['ALL'] + list(sch):
        m = post & ((df.home_school.values == s) if s != 'ALL' else True)
        yr = df.year.values
        tgt = pd.Series(yr[m & (s_ == 0)]).value_counts(normalize=True)
        for g, gm in G:
            ix = np.flatnonzero(m & gm)
            if len(ix) < 100:
                continue
            sh = pd.Series(yr[ix]).value_counts(normalize=True)
            wt = np.ones(len(ix)) if g.startswith('0%') else np.nan_to_num(tgt.reindex(yr[ix]).values / sh.reindex(yr[ix]).values)
            mm = A.ent_mm(lab[ix], wt)[1]
            bs = [A.ent_mm(lab[ix][i], wt[i])[1] for i in (r.integers(0, len(ix), len(ix)) for _ in range(200))]
            rows.append(dict(school=s, group=g, papers=len(ix), entropy=mm, se=float(np.std(bs))))
    D = pd.DataFrame(rows)
    D.to_csv(w / 'analysis' / f'schools_entropy_{metric}.csv', index=False)
    piv = D.pivot(index='school', columns='group', values='entropy')
    order = ['ALL'] + piv.drop('ALL').sort_values('0% AI').index.tolist()[::-1]
    C = {'0% AI': FG.BLUE, 'some AI (< 25%)': '#1baf7a', 'heavy AI (≥ 25%)': FG.ORANGE}
    plt.rcParams.update({'font.size': 10.5})
    fig, ax = plt.subplots(figsize=(11, 12.5))
    fig.subplots_adjust(left=0.18, right=0.74, top=0.86, bottom=0.08)
    fig.text(0.03, 0.965, 'Knowledge entropy by school and AI use (cosine)', fontsize=17, fontweight='bold', color=FG.INK)
    fig.text(0.03, 0.935, 'Full-text lab papers 2023–2025. Entropy of every paper in each group over the same 50 cosine topic clusters for all schools\n'
             '(Miller–Madow; AI groups re-weighted to the school\'s 0% papers\' year mix; bars ± 1.96 bootstrap SE). Higher = spread over more topics.',
             fontsize=10, color=FG.INK2, va='top')
    ys = {s: i for i, s in enumerate(order)}
    for s in order:
        d = D[D.school == s].set_index('group')
        y = ys[s]
        if s == 'ALL':
            ax.axhspan(y - 0.5, y + 0.5, color=FG.GRID, alpha=0.6, lw=0)
        if '0% AI' in d.index and 'heavy AI (≥ 25%)' in d.index:
            ax.plot([d.loc['0% AI', 'entropy'], d.loc['heavy AI (≥ 25%)', 'entropy']], [y, y], color=FG.MUTED, lw=2, zorder=1, solid_capstyle='round')
        for g in C:
            if g in d.index:
                e_, h_ = d.loc[g, 'entropy'], 1.96 * d.loc[g, 'se']
                ax.errorbar(e_, y, xerr=[[h_], [min(h_, np.log(50) - e_)]], fmt='o', ms=8 if g != 'some AI (< 25%)' else 6, color=C[g], mec=FG.SURF, mew=1.5,
                            elinewidth=1.2, capsize=0, zorder=3, label=g if s == 'ALL' else None)
        both = {'0% AI', 'heavy AI (≥ 25%)'} <= set(d.index)
        gap = d.loc['heavy AI (≥ 25%)', 'entropy'] - d.loc['0% AI', 'entropy'] if both else np.nan
        gse = float(np.hypot(d.loc['heavy AI (≥ 25%)', 'se'], d.loc['0% AI', 'se'])) if both else np.nan
        sig = both and abs(gap) > 1.96 * gse
        n0 = int(d.loc['0% AI', 'papers']) if '0% AI' in d.index else 0
        nh = int(d.loc['heavy AI (≥ 25%)', 'papers']) if 'heavy AI (≥ 25%)' in d.index else 0
        ax.text(1.03, y, f'{gap:+.2f}' + ('*' if sig else ''), transform=ax.get_yaxis_transform(), va='center', fontsize=10, color=FG.INK if sig else FG.INK2,
                fontweight='bold' if sig else 'normal')
        ax.text(1.17, y, f'{n0:,} / {nh:,}', transform=ax.get_yaxis_transform(), va='center', fontsize=8.5, color=FG.MUTED)
    ax.text(1.03, -1.1, 'heavy − 0%', transform=ax.get_yaxis_transform(), fontsize=9, color=FG.INK2, fontweight='bold')
    ax.text(1.17, -1.1, 'papers\n0% / heavy', transform=ax.get_yaxis_transform(), fontsize=8.5, color=FG.MUTED)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(['All 32 schools' if s == 'ALL' else LABEL.get(s, s.capitalize()) for s in order])
    ax.set_ylim(len(order) - 0.5, -1.6); ax.grid(axis='y', visible=False)
    ax.set_xlabel('knowledge entropy, cosine clusters (nats; max ln 50 = 3.91)')
    fig.legend(*ax.get_legend_handles_labels(), frameon=False, loc='upper left', bbox_to_anchor=(0.18, 0.895), ncol=3, fontsize=10)
    fig.text(0.03, 0.018, 'Schools with ≥ 1,000 full texts in 2023–25, sorted by the entropy of their 0% papers. * = the heavy − 0% gap\'s 95% interval excludes 0.\n'
             'Single schools sit lower than the pooled row because one school covers fewer topics than 32 together. Bars are capped at the maximum, ln 50.',
             fontsize=8.5, color=FG.MUTED)
    out = w / 'figures' / f'schools_entropy_{metric}.png'
    fig.savefig(out, dpi=200); fig.savefig(out.with_suffix('.pdf')); plt.close(fig)
    print(json.dumps(dict(figure=str(out))))


def cmd_citeage_fig(a):
    """One figure: average citation age by amount of AI, per school (small multiples, shared y), 2023-2025 full-text papers. Five AI bands of the
    main-body share; per band the mean of the papers' average citation age (citeage.py), re-weighted to the school's 0% papers' year mix, 95%
    interval from the weighted SE. Bands with < 30 papers with dated references are left out. -> WORK/analysis/schools_citeage.csv,
    WORK/figures/schools_citeage.png"""
    import figure as FG
    plt = FG.plt
    B = base(a)
    d = pd.read_parquet(B / 'papers_scored.parquet', columns=['k', 'home_school', 'year', 'has_emb', 'ai_share_main'])
    d = d[d.has_emb & d.ai_share_main.notna() & d.year.between(2023, 2025)]
    ca = pd.read_parquet(B / 'citeage' / 'citeage.parquet', columns=['k', 'cite_age_mean'])
    d = d.merge(ca, on='k', how='left').dropna(subset=['cite_age_mean'])
    s_ = d.ai_share_main.values
    band = np.full(len(d), -1)
    for j, (lo, hi, _) in enumerate(A.BANDS):
        band[(s_ == 0) if hi == 0 else ((s_ >= lo) & (s_ <= hi) if j == len(A.BANDS) - 1 else (s_ >= lo) & (s_ < hi))] = j
    d['band'] = band
    sch = json.loads((B / 'schools' / 'SCHOOLS.json').read_text())
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
    order = ['ALL'] + list(sch)
    nc = 6
    nr = int(np.ceil(len(order) / nc))
    plt.rcParams.update({'font.size': 9.5})
    fig, axs = plt.subplots(nr, nc, figsize=(17, 2.9 * nr + 1.6), sharey=True)
    fig.subplots_adjust(left=0.05, right=0.99, top=1 - 1.45 / (2.9 * nr + 1.6), bottom=0.85 / (2.9 * nr + 1.6), hspace=0.55, wspace=0.08)
    fig.text(0.05, 1 - 0.35 / (2.9 * nr + 1.6), 'Average citation age by amount of AI-written text, per school', fontsize=17, fontweight='bold', color=FG.INK)
    fig.text(0.05, 1 - 0.68 / (2.9 * nr + 1.6), 'Full-text lab papers 2023–2025. Years between each paper and the works it cites (OpenAlex), averaged over the papers in each '
             'AI band of the main body;\nbands re-weighted to the school\'s 0% papers\' year mix; bars 95% CI. Lower = cites more recent work.',
             fontsize=10, color=FG.INK2, va='top')
    xl = [b for _, _, b in A.BANDS]
    for i, ax in enumerate(axs.flat):
        if i >= len(order):
            ax.axis('off'); continue
        s = order[i]
        x = D[D.school == s].sort_values('band_i')
        if s == 'ALL':
            ax.set_facecolor('#efefeb')
        ax.errorbar(x.band_i, x.cite_age, yerr=1.96 * x.se, color=FG.BLUE, lw=2, marker='o', ms=5.5, mec=FG.SURF, mew=1.2, elinewidth=1.2, capsize=0)
        if len(x) >= 2 and 0 in x.band_i.values:
            z = x[x.band_i == 0].iloc[0]; h = x.iloc[-1]
            ax.text(0.97, 0.93, f'{h.cite_age - z.cite_age:+.1f} y', transform=ax.transAxes, ha='right', va='top', fontsize=10, fontweight='bold', color=FG.INK)
        n = int(x.papers.sum())
        ax.set_title(('All 32 schools' if s == 'ALL' else LABEL.get(s, s.capitalize())) + f'  ({n:,})', fontsize=10.5)
        ax.set_xticks(range(len(xl))); ax.set_xticklabels(xl, fontsize=7.5, rotation=0)
        ax.set_xlim(-0.4, len(xl) - 0.6); ax.grid(axis='x', visible=False)
        if i % nc == 0:
            ax.set_ylabel('citation age (years)')
    fig.text(0.05, 0.25 / (2.9 * nr + 1.6), 'Number in each corner: the highest AI band minus the 0% band (years). Bands with fewer than 30 papers with dated references are '
             'left out. In parentheses: papers with dated references.', fontsize=8.5, color=FG.MUTED)
    out = B / 'figures' / 'schools_citeage.png'
    fig.savefig(out, dpi=200); fig.savefig(out.with_suffix('.pdf')); plt.close(fig)
    print(json.dumps(dict(figure=str(out))))


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
