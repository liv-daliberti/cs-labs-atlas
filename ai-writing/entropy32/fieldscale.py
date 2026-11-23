"""AI vs knowledge entropy at field scale (owner 2026-11-23: "can we get more papers with SPECTER2 embeddings so we can get more of this?").

Corpus: the sealed field-300 snapshot (studies/homogenization/snapshots/field300-2026-11-08): every 2016-2025 CS work with an author at one of the
300 GRAS 2025 CS&E universities; 1,210,393 of them have an English abstract that was scored and embedded.
  vectors  SPECTER2 with the proximity adapter (allenai/specter2), title + abstract, fp16, embeddings/specter2_proximity/abstract.npz
  AI       the abstract detector's P(AI) p_v1 (ai/abstract_scores.parquet); the continuous exposure is its log-odds, the flag p_v1 >= 1.246e-6 (the
           12-school snapshot's thr_abstract: 1% false positives on pre-ChatGPT abstracts)
Differences from the lab analysis: abstracts instead of full texts, the proximity adapter instead of SPECTER2 base, a per-abstract probability instead of
the share of flagged full-text passages. Knowledge entropy is computed exactly as before: 50 k-means clusters fitted on the 2023-2025 papers, euclidean
(raw) and cosine (unit vectors), every paper of a group (Miller-Madow) plus 1,000-paper draws.
outputs (WORK = studies/homogenization/work/entropy32-<id>/field/): curve.csv, yearflag.csv, centroid.csv, summary.json, figures/field_*.png
usage: fieldscale.py [--id 20261123]   (Slurm: e32_field.slurm; ~20 GB RAM, 32 cores)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze as A  # noqa: E402  (ent, ent_mm, space, K, SEED)
import e32  # noqa: E402

SNAP = Path(e32.P.HOMOGENIZATION_STUDY) / 'snapshots' / 'field300-2026-11-08'
THR = 1.24603676e-06
GRID, DRAWS = 40, 200


def load():
    z = np.load(SNAP / 'embeddings' / 'specter2_proximity' / 'abstract.npz')
    ids, X = z['ids'], z['X']
    ai = pd.read_parquet(SNAP / 'ai' / 'abstract_scores.parquet', columns=['paper_id', 'p_v1'])
    ai['work'] = ai.paper_id.str[1:].astype('int64')
    P = pd.read_parquet(SNAP / 'tables' / 'papers.parquet', columns=['work', 'year', 'subfield', 'cited_by'])
    df = pd.DataFrame(dict(work=ids, row=np.arange(len(ids)))).merge(ai[['work', 'p_v1']], on='work').merge(P, on='work')
    df['logit'] = np.log(np.clip(df.p_v1, 1e-12, 1 - 1e-12)) - np.log(np.clip(1 - df.p_v1, 1e-12, 1))
    df['flag'] = df.p_v1 >= THR
    return df.reset_index(drop=True), X


def main():
    from sklearn.cluster import KMeans
    ap = argparse.ArgumentParser(); ap.add_argument('--id', default='20261123'); a = ap.parse_args()
    out = e32.work_dir(a.id) / 'field'
    (out / 'figures').mkdir(parents=True, exist_ok=True)
    df, X16 = load()
    r = np.random.default_rng(A.SEED)
    post = df.year.between(2023, 2025).values
    summ = dict(papers=len(df), post=int(post.sum()), flagged_post=float(df.flag[post].mean()))
    print(json.dumps(summ), flush=True)
    curve, yearflag, cent = [], [], []
    for metric in A.METRICS:
        Z = X16[df.row.values].astype(np.float32)
        if metric == 'cosine':
            Z /= np.linalg.norm(Z, axis=1, keepdims=True)
        fit = np.flatnonzero(post)
        fit = r.choice(fit, min(len(fit), 300000), replace=False)   # fit on a 300k sample of 2023-2025, then assign every paper
        km = KMeans(A.K, n_init=2, random_state=A.SEED).fit(Z[fit])
        lab = km.predict(Z)
        np.save(out / f'labels_{metric}.npy', lab)
        # dose-response: the not-flagged papers, then windows over the rank of the log-odds among the flagged
        ix0 = np.flatnonzero(post & ~df.flag.values)
        pos = np.flatnonzero(post & df.flag.values); pos = pos[np.argsort(df.logit.values[pos], kind='stable')]
        win = len(pos) // 12
        centres = np.linspace(win // 2, len(pos) - win // 2 - 1, GRID).round().astype(int)
        yr = df.year.values
        tgt = pd.Series(yr[ix0]).value_counts(normalize=True)
        for name, ix in [('not flagged', ix0)] + [(f'w{j:02d}', pos[max(0, c - win // 2): c + win // 2]) for j, c in enumerate(centres)]:
            sh = pd.Series(yr[ix]).value_counts(normalize=True)
            wt = np.nan_to_num(tgt.reindex(yr[ix]).values / sh.reindex(yr[ix]).values)
            h, mm, _ = A.ent_mm(lab[ix], wt)
            bs = [A.ent_mm(lab[ix][i], wt[i])[1] for i in (r.integers(0, len(ix), len(ix)) for _ in range(100))]
            pr = wt / wt.sum()
            E = [A.ent(lab[r.choice(ix, 1000, replace=False, p=pr)]) for _ in range(DRAWS)]
            curve.append(dict(metric=metric, window=name, papers=len(ix), p_median=float(np.median(df.p_v1.values[ix])), logit_median=float(np.median(df.logit.values[ix])),
                              all_mm=mm, all_lo=mm - 1.96 * float(np.std(bs)), all_hi=mm + 1.96 * float(np.std(bs)), draw1000=float(np.mean(E)),
                              draw_lo=float(np.quantile(E, .025)), draw_hi=float(np.quantile(E, .975))))
        # year x flag, every paper
        for y in range(2016, 2026):
            for fl in (False, True):
                ix = np.flatnonzero((yr == y) & (df.flag.values == fl))
                if len(ix) < 250:
                    continue
                h, mm, cs = A.ent_mm(lab[ix])
                bs = [A.ent_mm(lab[ix][i])[1] for i in (r.integers(0, len(ix), len(ix)) for _ in range(100))]
                yearflag.append(dict(metric=metric, year=y, flagged=fl, papers=len(ix), all_mm=mm, se=float(np.std(bs))))
        # cosine similarity to the year centroid (cosine geometry only)
        if metric == 'cosine':
            cs_ = np.empty(len(df))
            for y in range(2016, 2026):
                m = yr == y
                c = Z[m].mean(0); cs_[m] = Z[m] @ c / np.linalg.norm(c)
            df['cos_centroid'] = cs_
            for name, ix in [('not flagged', ix0)] + [(f'w{j:02d}', pos[max(0, c - win // 2): c + win // 2]) for j, c in enumerate(centres)]:
                v = cs_[ix]
                cent.append(dict(window=name, papers=len(ix), logit_median=float(np.median(df.logit.values[ix])), cos=float(v.mean()), se=float(v.std() / np.sqrt(len(v)))))
        print(json.dumps(dict(metric=metric, done=True)), flush=True)
    C, Y, Ce = pd.DataFrame(curve), pd.DataFrame(yearflag), pd.DataFrame(cent)
    C.to_csv(out / 'curve.csv', index=False); Y.to_csv(out / 'yearflag.csv', index=False); Ce.to_csv(out / 'centroid.csv', index=False)
    for metric in A.METRICS:
        c = C[C.metric == metric]
        summ[metric] = dict(not_flagged=float(c[c.window == 'not flagged'].all_mm.iloc[0]), most_ai_window=float(c[c.window != 'not flagged'].sort_values('logit_median').all_mm.iloc[-1]))
    (out / 'summary.json').write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ))
    figure(out, C, Y, Ce, summ)


def figure(out, C, Y, Ce, summ):
    import figure as FG
    plt = FG.plt
    plt.rcParams.update({'font.size': 10})
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.2, left=0.06, right=0.98, top=0.86, bottom=0.09)
    fig.text(0.06, 0.955, f'Field scale: {summ["papers"]:,} CS papers from 300 universities', fontsize=17, fontweight='bold', color=FG.INK)
    fig.text(0.06, 0.915, 'SPECTER2 (proximity adapter) vectors of titles + abstracts; AI = the abstract detector. Knowledge entropy over 50 k-means clusters fitted on 2023–2025, '
             'from every paper (Miller–Madow) and from 1,000-paper draws.\nAbstract-level, so it complements the lab full-text analysis rather than repeating it.',
             fontsize=10, color=FG.INK2, va='top')
    for j, metric in enumerate(('euclidean', 'cosine')):
        ax = fig.add_subplot(gs[0, j])
        c = C[C.metric == metric]
        z, wv = c[c.window == 'not flagged'].iloc[0], c[c.window != 'not flagged'].sort_values('logit_median')
        x = np.arange(len(wv)) + 1
        ax.fill_between(x, wv.all_lo, wv.all_hi, color=FG.BLUE, alpha=0.18, lw=0)
        ax.plot(x, wv.all_mm, color=FG.BLUE, lw=2.2, label=f'all papers per window (~{int(wv.papers.median()):,})')
        ax.plot(x, wv.draw1000, color=FG.MUTED, lw=1.5, ls=(0, (3, 2)), label='1,000-paper draws')
        ax.errorbar([0], [z.all_mm], yerr=[[z.all_mm - z.all_lo], [z.all_hi - z.all_mm]], fmt='o', ms=8, color=FG.BLUE, mec=FG.SURF, mew=2, label=f'not flagged ({int(z.papers):,})')
        ax.scatter([0], [z.draw1000], color=FG.MUTED, s=30, zorder=4)
        ticks = [0] + list(np.linspace(1, len(wv), 5).round().astype(int))
        ax.set_xticks(ticks); ax.set_xticklabels(['not\nflagged'] + [f'P(AI)\n{wv.p_median.iloc[t - 1]:.2g}' for t in ticks[1:]], fontsize=8.5)
        ax.set_xlabel('flagged abstracts, ordered by the detector\'s AI score (equal-size windows)'); ax.set_ylabel('knowledge entropy (nats)')
        ax.grid(axis='x', visible=False); ax.set_title(f'{"AB"[j]}  {FG.NAME[metric]}: entropy vs AI score, 2023–2025')
        if j == 0:
            ax.legend(frameon=False, fontsize=8.5, loc='lower left')
    ax = fig.add_subplot(gs[1, 0])
    y = Y[Y.metric == 'euclidean']
    for fl, col, lab in ((False, FG.BLUE, 'not flagged'), (True, FG.ORANGE, 'AI-flagged abstract')):
        g = y[y.flagged == fl].sort_values('year')
        ax.fill_between(g.year, g.all_mm - 1.96 * g.se, g.all_mm + 1.96 * g.se, color=col, alpha=0.18, lw=0)
        ax.plot(g.year, g.all_mm, color=col, lw=2, marker='o', ms=5, mec=FG.SURF, label=f'{lab}')
    ax.axvspan(2022.5, 2025.5, color=FG.GRID, alpha=0.35, lw=0, zorder=0)
    ax.set_xticks(range(2016, 2026)); ax.grid(axis='x', visible=False); ax.legend(frameon=False, fontsize=9)
    ax.set_ylabel('knowledge entropy, every paper (nats)'); ax.set_title('C  By year, every paper (Euclidean)')
    ax = fig.add_subplot(gs[1, 1])
    z, wv = Ce[Ce.window == 'not flagged'].iloc[0], Ce[Ce.window != 'not flagged'].sort_values('logit_median')
    x = np.arange(len(wv)) + 1
    ax.fill_between(x, wv.cos - 1.96 * wv.se, wv.cos + 1.96 * wv.se, color=FG.BLUE, alpha=0.18, lw=0)
    ax.plot(x, wv.cos, color=FG.BLUE, lw=2.2)
    ax.errorbar([0], [z.cos], yerr=1.96 * z.se, fmt='o', ms=8, color=FG.BLUE, mec=FG.SURF, mew=2)
    ax.set_xticks([0, len(wv) // 2, len(wv)]); ax.set_xticklabels(['not flagged', 'flagged, mid score', 'flagged, top score'], fontsize=8.5)
    ax.set_ylabel('cosine similarity to the year centroid'); ax.grid(axis='x', visible=False)
    ax.set_title('D  Closeness to the year\'s average abstract, 2023–2025')
    fig.text(0.06, 0.02, 'Flag: P(AI) ≥ 1.2e-6, the threshold giving 1% false positives on pre-ChatGPT abstracts. Windows re-weighted to the not-flagged papers\' year mix. '
             'Full counting: a paper with authors at several of the 300 universities appears once.', fontsize=8.5, color=FG.MUTED)
    fig.savefig(out / 'figures' / 'field_ai_entropy.png', dpi=200); fig.savefig(out / 'figures' / 'field_ai_entropy.pdf'); plt.close(fig)
    print(json.dumps(dict(figure=str(out / 'figures' / 'field_ai_entropy.png'))))


if __name__ == '__main__':
    main()
