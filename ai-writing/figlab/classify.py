"""Can a paper's figures tell which lab wrote it, and does that get harder from 2016 to 2026? And are AI-flagged papers
(the full-text detector) harder to place than unflagged papers of the same labs?

paper vector  the mean of its figures' DINOv2 vectors (embed.py), L2-normalized; papers with < MIN_FIGS figures dropped
by year       for each year: R draws of L labs (school:PI) out of the labs with >= K papers that year, K papers each;
              multinomial logistic regression, stratified K_FOLD-fold cross-validation (folds split papers, never one
              paper's figures); top-1 accuracy per draw. Chance is 1/L in every year, so years compare directly.
              'same labs': the same with the lab pool fixed to labs having >= K papers in every year of the window.
ai            2023-2026, labs with >= 1 flagged and >= 1 unflagged paper and >= K_AI papers in all: 10-fold stratified
              cross-validation over those labs' papers (every lab of the pool in training; leave-one-out was thousands of
              fits and timed out at 6 h on 2026-10-29), accuracy on flagged vs unflagged held-out papers; the gap's
              interval bootstraps labs. Draws run in parallel (--jobs); each result file is written as soon as it is done.
-> results/by_year.csv, results/by_year_same_labs.csv, results/ai_gap.json, figures/by_year.png
usage: classify.py [--L 10] [--K 8] [--draws 50] [--min-figs 1] [--schools a,b] [--years 2016-2026]
"""
import argparse, os, collections, glob, gzip, json
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('FIGLAB_DATA', HERE / 'data'))  # a mini run uses its own folder


def load(min_figs, schools):
    man = {x['key']: x for x in (json.loads(l) for l in gzip.open(DATA / 'manifest.jsonl.gz', 'rt'))
           if not schools or x['school'] in schools}
    vec = collections.defaultdict(list)
    for f in sorted(glob.glob(str(DATA / 'emb-*.npz'))):
        z = np.load(f)
        for k, v in zip(z['keys'], z['X'].astype(np.float32)):
            if k in man:
                vec[k].append(v)
    P = []
    for k, vs in vec.items():
        if len(vs) >= min_figs:
            m = np.mean(vs, 0); m /= np.linalg.norm(m) + 1e-9
            x = man[k]; P.append(dict(key=k, lab=f"{x['school']}:{x['pi']}", year=x['year'], ai=x.get('ai'), v=m, n_figs=len(vs)))
    return P


def cv_accuracy(X, y, folds, seed):
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    hit = 0
    for tr, te in skf.split(X, y):
        clf = LogisticRegression(C=1.0, max_iter=3000).fit(X[tr], y[tr])
        hit += (clf.predict(X[te]) == y[te]).sum()
    return hit / len(y)


def by_year(P, years, L, K, draws, folds, pool=None, seed=0, jobs=1):
    rng = np.random.default_rng(seed); rows = []
    for y in years:
        by_lab = collections.defaultdict(list)
        for p in P:
            if p['year'] == y:
                by_lab[p['lab']].append(p)
        elig = sorted(l for l, ps in by_lab.items() if len(ps) >= K and (pool is None or l in pool))
        if len(elig) < L:
            rows.append(dict(year=y, eligible_labs=len(elig), acc=None)); continue
        tasks = []
        for d in range(draws):
            labs = rng.choice(elig, L, replace=False)
            S = [p for l in labs for p in rng.choice(by_lab[l], K, replace=False)]
            tasks.append((np.stack([p['v'] for p in S]), np.array([p['lab'] for p in S]), d))
        accs = Parallel(n_jobs=jobs)(delayed(cv_accuracy)(X, yy, folds, d) for X, yy, d in tasks)
        a = np.array(accs)
        rows.append(dict(year=y, eligible_labs=len(elig), acc=float(a.mean()), lo=float(np.quantile(a, .025)), hi=float(np.quantile(a, .975)),
                         chance=1 / L, draws=draws))
        print(json.dumps(rows[-1]), flush=True)
    return rows


def ai_gap(P, K_ai, boots, seed=0, folds=10, jobs=1):
    Q = [p for p in P if p['year'] >= 2023 and p['ai'] is not None]
    by_lab = collections.defaultdict(list)
    for p in Q:
        by_lab[p['lab']].append(p)
    labs = [l for l, ps in by_lab.items() if len(ps) >= K_ai and any(p['ai'] for p in ps) and any(not p['ai'] for p in ps)]
    S = [p for l in labs for p in by_lab[l]]
    if len(labs) < 3:
        return dict(labs=len(labs), note='too few labs with both flagged and unflagged papers')
    X = np.stack([p['v'] for p in S]); y = np.array([p['lab'] for p in S]); ai = np.array([p['ai'] for p in S])
    correct = np.zeros(len(S), bool)
    skf = StratifiedKFold(n_splits=min(folds, min(collections.Counter(y).values())), shuffle=True, random_state=seed)
    def fold(tr, te):
        return te, LogisticRegression(C=1.0, max_iter=3000).fit(X[tr], y[tr]).predict(X[te]) == y[te]
    for te, ok in Parallel(n_jobs=jobs)(delayed(fold)(tr, te) for tr, te in skf.split(X, y)):
        correct[te] = ok
    lab_ix = collections.defaultdict(list)
    for i, l in enumerate(y):
        lab_ix[l].append(i)
    def gap(ls):
        ii = np.concatenate([lab_ix[l] for l in ls])
        return correct[ii][ai[ii] == 1].mean() - correct[ii][ai[ii] == 0].mean()
    rng = np.random.default_rng(seed); L = list(lab_ix)
    bs = [gap(rng.choice(L, len(L), replace=True)) for _ in range(boots)]
    return dict(labs=len(labs), papers=len(S), flagged=int(ai.sum()), chance=1 / len(labs),
                acc_flagged=float(correct[ai == 1].mean()), acc_unflagged=float(correct[ai == 0].mean()),
                gap=float(gap(L)), gap_lo=float(np.nanquantile(bs, .025)), gap_hi=float(np.nanquantile(bs, .975)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L', type=int, default=10); ap.add_argument('--K', type=int, default=8); ap.add_argument('--draws', type=int, default=50)
    ap.add_argument('--folds', type=int, default=4); ap.add_argument('--min-figs', type=int, default=1); ap.add_argument('--K-ai', type=int, default=6)
    ap.add_argument('--jobs', type=int, default=int(os.environ.get('SLURM_CPUS_PER_TASK', 1)))
    ap.add_argument('--schools', default=''); ap.add_argument('--years', default='2016-2026'); ap.add_argument('--tag', default='')
    a = ap.parse_args()
    lo, hi = map(int, a.years.split('-')); years = list(range(lo, hi + 1))
    P = load(a.min_figs, set(filter(None, a.schools.split(','))))
    print(json.dumps(dict(papers=len(P), labs=len({p['lab'] for p in P}), figures=sum(p['n_figs'] for p in P))), flush=True)
    (DATA / 'results').mkdir(exist_ok=True); (DATA / 'figures').mkdir(exist_ok=True)
    t = a.tag
    import pandas as pd
    rows = by_year(P, years, a.L, a.K, a.draws, a.folds, jobs=a.jobs)
    pd.DataFrame(rows).to_csv(DATA / 'results' / f'by_year{t}.csv', index=False)
    cnt = collections.Counter((p['lab'], p['year']) for p in P)
    pool = {l for l in {p['lab'] for p in P} if all(cnt[(l, y)] >= a.K for y in years)}
    print(json.dumps(dict(same_lab_pool=len(pool))), flush=True)
    same = by_year(P, years, a.L, a.K, a.draws, a.folds, pool=pool, jobs=a.jobs) if len(pool) >= a.L else []
    pd.DataFrame(same).to_csv(DATA / 'results' / f'by_year_same_labs{t}.csv', index=False)
    gap = ai_gap(P, a.K_ai, 1000, jobs=a.jobs)
    (DATA / 'results' / f'ai_gap{t}.json').write_text(json.dumps(dict(gap, same_lab_pool=len(pool), L=a.L, K=a.K), indent=1))
    print(json.dumps(dict(ai_gap=gap, same_lab_pool=len(pool))), flush=True)
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4))
    for rs, lab, c in ((rows, f'all eligible labs', '#2b6cb0'), (same, 'same labs every year', '#c05621')):
        rs = [r for r in rs if r.get('acc') is not None]
        if rs:
            ax.errorbar([r['year'] for r in rs], [r['acc'] for r in rs], yerr=[[r['acc'] - r['lo'] for r in rs], [r['hi'] - r['acc'] for r in rs]],
                        marker='o', capsize=3, label=lab, color=c)
    ax.axhline(1 / a.L, ls='--', color='gray', label=f'chance (1/{a.L})')
    ax.set_xlabel('publication year'); ax.set_ylabel(f'lab top-1 accuracy ({a.L} labs x {a.K} papers)')
    ax.set_title('Which lab made these figures? (DINOv2, logistic regression)'); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(DATA / 'figures' / f'by_year{t}.png', dpi=150)


if __name__ == '__main__':
    main()
