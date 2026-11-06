"""Validation of detector v3 from the saved logits (results/<tag>/scores.npz): thresholds on cal only, every rate with a 95% CI.

threshold   the (1 - alpha) quantile of the cal-split real passages that are NOT abstained (alpha = 0.3% for the headline).
abstain     explicit categories reported separately, never hidden: passages under ABST_WORDS words (short tails) and
            heading/interleaving-heavy passages (mid-sentence-capital share above the cal-set 95th percentile).
FPR         flagged share of the held-out real test passages (2016-2021 papers the model never saw); CI = bootstrap over papers.
TPR / miss  per generator x task on test-split AI outputs; CI = Clopper-Pearson (exact). Claim tasks exclude 'partial'
            (mixed human/AI passages, reported on their own). A held-out family is scored with its leave-one-family-out model.
Nothing here is tuned on test: alpha and the abstain rule are fixed from cal (and v2's own 1% threshold for the baseline).
"""
import gzip, json, sys
from collections import defaultdict
import numpy as np
from scipy.stats import beta
import v3common as C

ABST_WORDS = 100
CLAIM_TASKS = ('polish', 'paraphrase', 'notes', 'continue', 'humanize')


def cp(k, n, a=0.05):
    if n == 0:
        return [None, None]
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return [float(lo), float(hi)]


def boot(flag, keys, n=1000, seed=1):
    by = defaultdict(lambda: [0, 0])
    for f, k in zip(flag, keys):
        by[k][0] += int(f); by[k][1] += 1
    s = np.array([v[0] for v in by.values()], float); c = np.array([v[1] for v in by.values()], float)
    r = np.random.default_rng(seed)
    b = np.array([s[ix].sum() / c[ix].sum() for ix in (r.integers(0, len(s), len(s)) for _ in range(n))])
    return [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))]


class Run:
    def __init__(self, tag):
        self.tag = tag
        d = C.RESULTS / tag
        z = np.load(d / 'scores.npz')
        m = json.loads(gzip.open(d / 'scores_meta.jsonl.gz', 'rt').read())
        self.zc, self.zt, self.za, self.zat = z['cal_real_z'].astype(np.float64), z['test_real_z'].astype(np.float64), z['ai_z'].astype(np.float64), z['ai_train_z'].astype(np.float64)
        self.mc, self.mt, self.ma, self.mat = m['cal_real'], m['test_real'], m['ai'], m['ai_train']

    def arrs(self, meta, k):
        return np.array([x[k] for x in meta])

    def abstain_real(self, meta, cut):
        return (self.arrs(meta, 'words') < ABST_WORDS) | (self.arrs(meta, 'midcap') > cut)

    def abstain_ai(self, meta, cut):
        return (self.arrs(meta, 'words') < ABST_WORDS) | (self.arrs(meta, 'midcap') > cut)

    def evaluate(self, alpha=None, thr=None, apply_abstain=True):
        cut = float(np.quantile(self.arrs(self.mc, 'midcap'), 0.95))
        ac, at = self.abstain_real(self.mc, cut), self.abstain_real(self.mt, cut)
        keep_c = ~ac if apply_abstain else np.ones_like(ac)
        if thr is None:
            thr = float(np.quantile(self.zc[keep_c], 1 - alpha))
        out = dict(tag=self.tag, alpha=alpha, thr_z=thr, midcap_cut=cut, cal_passages=len(self.zc))
        keys = np.array([x['key'] for x in self.mt])
        flag = self.zt >= thr
        kept = ~at if apply_abstain else np.ones_like(at)
        out['abstain_share_test'] = float(at.mean()) if apply_abstain else 0.0
        out['fpr_all_test_passages'] = dict(n=len(flag), k=int(flag.sum()), rate=float(flag.mean()), ci=boot(flag, keys))
        out['fpr'] = dict(n=int(kept.sum()), k=int(flag[kept].sum()), rate=float(flag[kept].mean()), ci=boot(flag[kept], keys[kept]), papers=len(set(keys[kept])))
        y = self.arrs(self.mt, 'year')
        out['fpr_by_year'] = {int(yy): dict(n=int((kept & (y == yy)).sum()), rate=float(flag[kept & (y == yy)].mean()), ci=boot(flag[kept & (y == yy)], keys[kept & (y == yy)]))
                              for yy in sorted(set(y.tolist()))}
        sch = self.arrs(self.mt, 'school')
        out['fpr_by_school'] = {s: dict(n=int((kept & (sch == s)).sum()), rate=float(flag[kept & (sch == s)].mean())) for s in sorted(set(sch.tolist()))}
        w = self.arrs(self.mt, 'words')
        out['fpr_by_words_all'] = {f'{lo}-{hi}': dict(n=int(((w >= lo) & (w < hi)).sum()), rate=float(flag[(w >= lo) & (w < hi)].mean()))
                                   for lo, hi in ((0, 100), (100, 150), (150, 200), (200, 1000))}
        out['abstained_flag_rate'] = float(flag[at].mean()) if at.any() else None
        # AI: test split of every generator x task, plus the held-out family's train/cal outputs
        aa = self.abstain_ai(self.ma, cut)
        g = np.array([x['gen'] for x in self.ma]); t = np.array([x['task'] for x in self.ma]); sp = np.array([x['split'] for x in self.ma])
        fam = np.array([x['family'] for x in self.ma])
        ok = ~aa if apply_abstain else np.ones_like(aa)
        miss = self.za < thr
        out['tpr'] = {}
        for gg in sorted(set(g.tolist())):
            for tt in CLAIM_TASKS + ('partial', 'claim'):
                m = (g == gg) & (sp == 'test') & ok & ((np.isin(t, CLAIM_TASKS)) if tt == 'claim' else (t == tt))
                if m.any():
                    k = int(miss[m].sum()); n = int(m.sum())
                    out['tpr'][f'{gg}/{tt}'] = dict(n=n, miss=k, miss_rate=k / n, miss_ci=cp(k, n))
        out['family'] = {}
        for ff in sorted(set(fam.tolist())):
            for tt in CLAIM_TASKS + ('partial', 'claim'):
                m = (fam == ff) & (sp == 'test') & ok & ((np.isin(t, CLAIM_TASKS)) if tt == 'claim' else (t == tt))
                if m.any():
                    k = int(miss[m].sum()); n = int(m.sum())
                    out['family'][f'{ff}/{tt}'] = dict(n=n, miss=k, miss_rate=k / n, miss_ci=cp(k, n))
        # held-out families' unseen train-split outputs (for leave-one-out models) and abstain share of AI passages
        out['abstain_share_ai'] = float(aa[sp == 'test'].mean())
        gt = np.array([x['gen'] for x in self.mat]); tt_ = np.array([x['task'] for x in self.mat]); ft = np.array([x['family'] for x in self.mat])
        at2 = self.abstain_ai(self.mat, cut); miss2 = self.zat < thr
        out['family_train_split'] = {}
        for ff in sorted(set(ft.tolist())):
            m = (ft == ff) & np.isin(tt_, CLAIM_TASKS) & (~at2 if apply_abstain else True)
            if m.any():
                k = int(miss2[m].sum()); n = int(m.sum())
                out['family_train_split'][ff] = dict(n=n, miss=k, miss_rate=k / n, miss_ci=cp(k, n))
        return out


def fmt(r):
    return f"{100 * r['rate']:.2f}% ({100 * r['ci'][0]:.2f}-{100 * r['ci'][1]:.2f})"


def fmtm(r):
    return f"{100 * r['miss_rate']:.2f}% ({100 * r['miss_ci'][0]:.2f}-{100 * r['miss_ci'][1]:.2f}) n={r['n']}"


if __name__ == '__main__' and sys.argv[1:2] == ['op']:
    pass
elif __name__ == '__main__':
    tag, alpha = sys.argv[1], float(sys.argv[2])
    r = Run(tag).evaluate(alpha)
    print(json.dumps({k: v for k, v in r.items() if k in ('thr_z', 'abstain_share_test', 'abstain_share_ai')}))
    print('FPR', fmt(r['fpr']), 'all', fmt(r['fpr_all_test_passages']))
    for k, v in r['family'].items():
        if k.endswith('/claim'):
            print(k, fmtm(v))


def operating_point(tag='all', alpha=0.003):
    """The deployed rule, fixed on cal only: threshold z (cal 1 - alpha quantile of non-abstained passages), abstain = words < ABST_WORDS or
    mid-sentence-capital share > cal 95th percentile. Written to results/operating_point.json by `eval3.py op`."""
    r = Run(tag)
    ev = r.evaluate(alpha)
    return dict(tag=tag, alpha=alpha, thr_z=ev['thr_z'], midcap_cut=ev['midcap_cut'], abstain_words=ABST_WORDS, cal_passages=ev['cal_passages'],
                test_fpr=ev['fpr'], test_abstain_share=ev['abstain_share_test'])


if __name__ == '__main__' and sys.argv[1:2] == ['op']:
    t = sys.argv[2] if len(sys.argv) > 2 else 'all'
    op = operating_point(t)
    json.dump(op, open(C.RESULTS / ('operating_point.json' if t == 'all' else f'operating_point-{t}.json'), 'w'), indent=1)
    print(json.dumps(op))
