"""McNemar exact test of two models' misses on the same unseen-family TEST claim passages (both at their own cal 0.3% threshold)."""
import sys
import numpy as np
from scipy.stats import binomtest
import eval4 as E4
import eval3 as E


def misses(tag, fam):
    r = E4.load(tag)
    cut = float(np.quantile(r.arrs(r.mc, 'midcap'), 0.95))
    thr = float(np.quantile(r.zc[~r.abstain_real(r.mc, cut)], 1 - E4.ALPHA))
    ok = ~r.abstain_ai(r.ma, cut)
    sp = np.array([x['split'] for x in r.ma]); t = np.array([x['task'] for x in r.ma]); f = np.array([x['family'] for x in r.ma])
    m = ok & (sp == 'test') & (f == fam) & np.isin(t, E.CLAIM_TASKS)
    sid = np.array([x['sid'] for x in r.ma])[m]
    return dict(zip(sid, (r.za < thr)[m]))


a, b, fam = sys.argv[1:4]
A, B = misses(a, fam), misses(b, fam)
ks = sorted(set(A) & set(B))
x = np.array([A[k] for k in ks]); y = np.array([B[k] for k in ks])
n10, n01 = int((x & ~y).sum()), int((~x & y).sum())
print(a, 'miss', x.mean(), b, 'miss', y.mean(), 'n', len(ks), f'only-{a}-misses', n10, f'only-{b}-misses', n01, 'McNemar p', binomtest(n10, n10 + n01, .5).pvalue)
