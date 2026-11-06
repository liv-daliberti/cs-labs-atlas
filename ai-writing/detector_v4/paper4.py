"""Route 4: paper-level aggregation of v3's passage scores (no new model; CPU only).

Papers: the held-out TEST real papers (2016-21, never trained on); their non-abstained passages. A "synthetic AI paper" replaces a share f of a
paper's passages with random test-split AI passages (claim tasks: polish/paraphrase/notes/continue/humanize), scored by the same model.
Aggregators (all thresholds fixed on CAL papers only, at paper-level FPR alpha = 0.3%; papers with < MIN_N scored passages are not classified):
  share   flagged/scored >= tau                        (the deployed ai_share_main)
  binom   -log10 P(Bin(n, p0) >= k)  k = flagged passages, p0 = the cal passage FPR   (accounts for paper length)
  fisher  sum_i min(-ln p_i, CAP)  p_i = cal-null empirical upper tail of passage z_i  (uses the score, not only the flag)
Reported: test paper FPR (paper bootstrap CI), and detection of synthetic papers per f (Clopper-Pearson CI), seen and unseen family.
usage: paper4.py   (writes results/paper4_v3.json and .md)
"""
import json
import numpy as np
from scipy.stats import binom
import v4common as K
import eval4 as E4
import eval3 as E

ALPHA, MIN_N, CAP, NSIM = 0.003, 10, 12.0, 4
FRACS = (0.05, 0.1, 0.25, 0.5, 1.0)
CLAIM = E.CLAIM_TASKS


def papers(z, meta, ok):
    by = {}
    for zi, m, o in zip(z, meta, ok):
        if o:
            by.setdefault(m['key'], []).append(zi)
    return {k: np.array(v) for k, v in by.items() if len(v) >= MIN_N}


def stat_fns(thr, null_sorted, p0):
    def share(z):
        return float((z >= thr).mean())

    def bn(z):
        return float(-binom.logsf((z >= thr).sum() - 1, len(z), p0) / np.log(10))

    def fisher(z):
        p = (len(null_sorted) - np.searchsorted(null_sorted, z, side='left') + 1) / (len(null_sorted) + 1)
        return float(np.minimum(-np.log(p), CAP).sum())
    return dict(share=share, binom=bn, fisher=fisher)


def run(tag, family=None, tasks=CLAIM, seed=7):
    r = E4.load(tag)
    cut = float(np.quantile(r.arrs(r.mc, 'midcap'), 0.95))
    ac, at = r.abstain_real(r.mc, cut), r.abstain_real(r.mt, cut)
    thr = float(np.quantile(r.zc[~ac], 1 - ALPHA))
    null = np.sort(r.zc[~ac])
    fns = stat_fns(thr, null, ALPHA)
    cal_p, test_p = papers(r.zc, r.mc, ~ac), papers(r.zt, r.mt, ~at)
    # AI pools (split cal / test), claim tasks, non-abstained; for the unseen family only that family
    aa = r.abstain_ai(r.ma, cut)
    sp = np.array([x['split'] for x in r.ma]); tk = np.array([x['task'] for x in r.ma]); fm = np.array([x['family'] for x in r.ma])
    base = ~aa & np.isin(tk, tasks) & ((fm == family) if family else True)
    pool = {s: r.za[base & (sp == s)] for s in ('cal', 'test')}
    rng = np.random.default_rng(seed)

    def synth(ps, ai, f):
        out = []
        for z in ps.values():
            for _ in range(NSIM):
                n = len(z); m = max(1, round(f * n)); zz = z.copy()
                zz[rng.choice(n, m, replace=False)] = rng.choice(ai, m)
                out.append(zz)
        return out
    res = dict(tag=tag + ('' if tasks == CLAIM else '/light-edits-only'), family=family, thr_z=thr, cal_papers=len(cal_p), test_papers=len(test_p), ai_pool_test=len(pool['test']), results={})
    for name, fn in fns.items():
        cs = np.array([fn(z) for z in cal_p.values()])
        tau = float(np.quantile(cs, 1 - ALPHA))
        ts = np.array([fn(z) for z in test_p.values()])
        flag = ts > tau
        k = int(flag.sum()); n = len(flag)
        b = np.random.default_rng(1)
        bs = [flag[b.integers(0, n, n)].mean() for _ in range(2000)]
        d = dict(tau=tau, fpr=dict(k=k, n=n, rate=k / n, ci=[float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]), det={})
        for f in FRACS:
            s = np.array([fn(z) for z in synth(test_p, pool['test'], f)])
            fl = s > tau
            kk, nn = int(fl.sum()), len(fl)
            d['det'][str(f)] = dict(k=kk, n=nn, rate=kk / nn, ci=E.cp(kk, nn))
        res['results'][name] = d
    return res


def md(rs):
    out = []
    for r in rs:
        out += [f"\n**{r['tag']}** family={r['family']} (cal papers {r['cal_papers']}, test papers {r['test_papers']}, passage thr z={r['thr_z']:.2f})\n",
                '| aggregator | paper FPR (95% CI) | ' + ' | '.join(f'detect f={f}' for f in FRACS) + ' |', '|' + '---|' * (2 + len(FRACS))]
        for name, d in r['results'].items():
            f = d['fpr']
            out.append(f"| {name} | {100 * f['rate']:.2f}% ({100 * f['ci'][0]:.2f}-{100 * f['ci'][1]:.2f}) k={f['k']}/{f['n']} | " +
                       ' | '.join(f"{100 * d['det'][str(x)]['rate']:.1f}% ({100 * d['det'][str(x)]['ci'][0]:.1f}-{100 * d['det'][str(x)]['ci'][1]:.1f})" for x in FRACS) + ' |')
    return '\n'.join(out)


if __name__ == '__main__':
    runs = [run('v3:all'), run('v3:lofo-qwen', family='qwen'), run('v3:lofo-llama', family='llama'), run('v3:lofo-gemma', family='gemma'),
            run('v3:lofo-qwen', family='qwen', tasks=('polish', 'paraphrase', 'humanize'))]
    json.dump(runs, open(K.RESULTS / 'paper4_v3.json', 'w'), indent=1)
    t = md(runs); (K.RESULTS / 'paper4_v3.md').write_text(t); print(t)
