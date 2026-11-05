"""Heavy stages of ai_pages.py, part 2: the topic-matched test and Figure 3 for nine schools (see ai_pages.py)."""
import time

import numpy as np
import pandas as pd

import ai_pages as A
import dcommon as D

BOOT = 500
M_SET = 150          # papers per set in the size-matched dispersion / Vendi comparison
DRAWS = 200          # draws of the point estimate
BOOT_SETS, BOOT_DRAWS = 100, 10   # lab resamples x draws per resample for the interval of the size-matched comparison


# ------------------------------------------------------------------ topic-matched test

def cell_effect(v, flag, cell, w):
    """Cell-weighted AI minus non-AI mean of v: within every (topic, year, school) cell that holds both groups, the difference of the weighted means; cells weighted by their
    AI papers (the effect on the AI papers, coarsened exact matching). v NaN rows drop out. Returns (effect, matched AI weight, cells used)."""
    ok = np.isfinite(v)
    w = np.where(ok, w, 0.0)
    v = np.where(ok, v, 0.0)
    n = cell.max() + 1
    wa, wn = np.bincount(cell, w * flag, n), np.bincount(cell, w * (1 - flag), n)
    sa, sn = np.bincount(cell, w * flag * v, n), np.bincount(cell, w * (1 - flag) * v, n)
    use = (wa > 0) & (wn > 0)
    if not use.any():
        return np.nan, 0.0, 0
    diff = sa[use] / wa[use] - sn[use] / wn[use]
    return float((wa[use] * diff).sum() / wa[use].sum()), float(wa[use].sum()), int(use.sum())


def raw_effect(v, flag, w):
    ok = np.isfinite(v) & (w > 0)
    a, n = ok & (flag == 1), ok & (flag == 0)
    return float(np.average(v[a], weights=w[a]) - np.average(v[n], weights=w[n])) if a.any() and n.any() else np.nan


class Matched:
    """One population (period, flag rule): rows of the frame with cell, lab and flag, the 7 models' unit vectors and novelty aligned to them."""

    def __init__(self, rows, flag, models_Z, models_nov):
        self.rows, self.flag = rows, flag.astype(float)
        self.cell = pd.factorize(rows['topic'].astype(int).astype(str) + '|' + rows['year'].astype(str) + '|' + rows['school'])[0]
        self.lab = pd.factorize(rows['lab0'])[0]
        self.Z, self.nov = models_Z, models_nov

    def novelty_rows(self, rng, B):
        out = []
        nl = self.lab.max() + 1
        ws = [np.ones(len(self.flag))] + [rng.multinomial(nl, np.full(nl, 1.0 / nl))[self.lab].astype(float) for _ in range(B)]
        for model in A.MODELS:
            v = self.nov[model]
            est, wa, cells = cell_effect(v, self.flag, self.cell, ws[0])
            bs = np.array([cell_effect(v, self.flag, self.cell, w)[0] for w in ws[1:]])
            lo, hi = np.nanpercentile(bs, [2.5, 97.5])
            ok = np.isfinite(v)
            out.append(dict(model=model, measure='novelty', effect=est, lo=float(lo), hi=float(hi), raw=raw_effect(v, self.flag, ws[0]), n_ai=int((self.flag[ok] == 1).sum()),
                            n_non=int((self.flag[ok] == 0).sum()), n_ai_matched=int(round(wa)), cells=cells, sd=float(np.nanstd(v))))
        return out

    def _groups(self, w):
        """Per cell with both groups: the AI and non-AI row arrays and the sampling weights (lab multiplicities)."""
        ok = w > 0
        ca, cn = {}, {}
        for i in np.flatnonzero(ok):
            (ca if self.flag[i] == 1 else cn).setdefault(self.cell[i], []).append(i)
        cells = [c for c in ca if c in cn]
        return cells, ca, cn

    def draw_sets(self, rng, cells, ca, cn, w, m):
        cap = np.array([min(len(ca[c]), len(cn[c])) for c in cells])
        p = cap / cap.sum()
        k = np.minimum(rng.multinomial(m, p), cap)
        A_, N_ = [], []
        for j in np.flatnonzero(k):
            c = cells[j]
            for src, dst in ((ca[c], A_), (cn[c], N_)):
                idx = np.asarray(src)
                keys = rng.exponential(size=len(idx)) / np.maximum(w[idx], 1e-9)
                dst.append(idx[np.argsort(keys)[:k[j]]])
        return np.concatenate(A_), np.concatenate(N_)

    def size_matched(self, rng):
        """AI minus non-AI dispersion and Vendi on sets with the same (topic, year, school) composition and the same size, per model: estimate over DRAWS draws,
        95% interval from BOOT_SETS lab resamples x BOOT_DRAWS draws."""
        nl = self.lab.max() + 1
        w1 = np.ones(len(self.flag))
        cells, ca, cn = self._groups(w1)
        est = {m: [] for m in A.MODELS}
        for _ in range(DRAWS):
            a, n = self.draw_sets(rng, cells, ca, cn, w1, M_SET)
            for m in A.MODELS:
                est[m].append(set_diff(self.Z[m], a, n))
        boot = {m: [] for m in A.MODELS}
        for _ in range(BOOT_SETS):
            w = rng.multinomial(nl, np.full(nl, 1.0 / nl))[self.lab].astype(float)
            cells_b, ca_b, cn_b = self._groups(w)
            ds = {m: [] for m in A.MODELS}
            for _ in range(BOOT_DRAWS):
                a, n = self.draw_sets(rng, cells_b, ca_b, cn_b, w, M_SET)
                for m in A.MODELS:
                    ds[m].append(set_diff(self.Z[m], a, n))
            for m in A.MODELS:
                boot[m].append(np.mean(ds[m], axis=0))
        out = []
        for m in A.MODELS:
            e = np.mean(est[m], axis=0)
            b = np.array(boot[m])
            for j, name in enumerate(('dispersion', 'vendi')):
                lo, hi = np.percentile(b[:, j], [2.5, 97.5])
                out.append(dict(model=m, measure=name, effect=float(e[j]), lo=float(lo), hi=float(hi), set_size=M_SET, matched_cells=len(cells)))
        return out


def set_diff(Z, a, n):
    """(dispersion difference, Vendi difference) of the row sets a minus n."""
    r = []
    for rows in (a, n):
        V = Z[rows]
        m = len(rows)
        disp = np.linalg.norm(V - V.mean(0), axis=1).mean()
        lam = np.clip(np.linalg.eigvalsh(V @ V.T / m), 1e-12, None)
        r.append((disp, float(np.exp(-(lam * np.log(lam)).sum()))))
    return r[0][0] - r[1][0], r[0][1] - r[1][1]


def placebo_threshold(x_pre, x_post):
    """The pre-ChatGPT 'AI' rule: the dose cut that flags the same share of 2017-2021 papers as the 25% cut flags of 2023-2025 papers (the flags are detector noise there)."""
    share = float((x_post >= A.THR - 1e-12).mean())
    t = float(np.quantile(x_pre, 1 - share))
    return (t if t > 0 else 1e-9), share


def stage_matched(args):
    import ecommon as C
    import pyarrow.dataset as pds
    A.ensure_dirs()
    fr = pd.read_parquet(A.RES / 'frame.parquet')
    fr = fr[fr['x'].notna() & fr['topic'].notna() & fr['lab0'].notna() & fr['has_vec']].reset_index(drop=True)
    Zs, ids_of = {}, {}
    for m in A.MODELS:
        ids, Z = A.unit_vectors(m)
        ids_of[m] = {p: i for i, p in enumerate(ids)}
        Zs[m] = (ids, Z)
    common = set(fr['paper_id'])
    for m in A.MODELS:
        common &= set(Zs[m][0])
    fr = fr[fr['paper_id'].isin(common)].reset_index(drop=True)
    D.log(stage='matched', papers=len(fr))
    zs, nov = {}, {}
    for m in A.MODELS:
        pos = np.array([ids_of[m][p] for p in fr['paper_id']])
        zs[m] = Zs[m][1][pos].astype(np.float32)
        nv = pds.dataset(C.RESULTS / f'novelty_{m}_abstract.parquet').to_table(columns=['paper_id', 'nov_nn_cap'], filter=(pds.field('scope') == 'all') & (pds.field('k') == 3)).to_pandas()
        nov[m] = fr['paper_id'].map(nv.set_index('paper_id')['nov_nn_cap']).to_numpy(float)
        del Zs[m]
    rng = np.random.default_rng(A.SEED)
    post = fr['year'].isin(A.POST).to_numpy()
    pre = fr['year'].isin(A.PLACEBO).to_numpy()
    thr_pre, share_post = placebo_threshold(fr.loc[pre, 'x'].to_numpy(), fr.loc[post, 'x'].to_numpy())
    pops = {'post': (post, fr['x'] >= A.THR - 1e-12, f'AI = dose >= {A.THR:.0%}, 2023-2025'),
            'placebo': (pre, fr['x'] >= thr_pre, f'placebo 2017-2021: "AI" = dose >= {thr_pre:.3f} (flags the same share, {share_post:.1%}, as the 25% cut does in 2023-2025; detector noise)'),
            'placebo25': (pre, fr['x'] >= A.THR - 1e-12, 'placebo 2017-2021 at the 25% cut itself (very few papers)')}
    rows = []
    for name, (sel, flag, desc) in pops.items():
        t0 = time.time()
        idx = np.flatnonzero(sel)
        pop = Matched(fr.iloc[idx].reset_index(drop=True), flag.to_numpy()[idx], {m: zs[m][idx] for m in A.MODELS}, {m: nov[m][idx] for m in A.MODELS})
        r = pop.novelty_rows(rng, BOOT)
        if name != 'placebo25':
            r += pop.size_matched(rng)
        for x in r:
            x.update(population=name, description=desc, years=f'{int(fr.loc[idx, "year"].min())}-{int(fr.loc[idx, "year"].max())}',
                     papers=len(idx), ai_papers=int(pop.flag.sum()), threshold=A.THR if name != 'placebo' else thr_pre)
        rows += r
        D.log(stage='matched', population=name, papers=len(idx), ai=int(pop.flag.sum()), seconds=round(time.time() - t0))
    pd.DataFrame(rows).to_parquet(A.RES / 'matched.parquet', index=False)
    D.log(stage='matched', rows=len(rows), placebo_threshold=thr_pre, post_share=share_post)


# ------------------------------------------------------------------ Figure 3 for all schools

def box_stats(v):
    v = np.asarray(v, float)
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    iqr = q3 - q1
    lo, hi = v[v >= q1 - 1.5 * iqr].min(), v[v <= q3 + 1.5 * iqr].max()
    return dict(whislo=float(lo), q1=float(q1), med=float(med), q3=float(q3), whishi=float(hi), mean=float(v.mean()), n_outliers=int(((v < lo) | (v > hi)).sum()))


def stage_fig3(args, draws=1000, per_group=1000):
    import ecommon as C
    C.use_extras()
    from sklearn.cluster import KMeans
    A.ensure_dirs()
    fr = pd.read_parquet(A.RES / 'frame.parquet')
    ids, Z = A.unit_vectors(A.HEADLINE)
    pos = pd.Series(np.arange(len(ids)), index=ids)
    fr = fr[fr['paper_id'].isin(pos.index)].reset_index(drop=True)
    fr['row'] = pos.loc[fr['paper_id']].to_numpy()
    post = fr[fr['year'].isin(A.POST)]
    km = KMeans(50, n_init=4, random_state=A.SEED).fit(Z[post['row'].to_numpy()])
    code = np.full(len(ids), -1)
    code[post['row'].to_numpy()] = km.labels_
    rng = np.random.default_rng(A.SEED)
    out = dict(meta=dict(model=A.HEADLINE, clusters=50, geometry='unit vectors centred on the corpus mean (cosine geometry); entropy in bits over 50 k-means clusters fitted on all 2023-2025 papers',
                         years=A.POST, draws=draws, per_group_cap=per_group, rule='n per draw = min(1000, 0.8 x the smaller group); groups with n < 30 are skipped'), groups=[])
    for variant, col, desc in (('ft25', 'ai25', 'AI = dose >= 25% (full-text papers)'), ('abstract', 'flag_abstract', 'AI = the abstract detector flags the abstract (all papers with an abstract score)')):
        d = post[post[col].notna()]
        for sc in ['all'] + D.SCHOOLS:
            g = d if sc == 'all' else d[d['schools'].str.split(',').map(lambda s, sc=sc: sc in s)]
            ai, no = g.loc[g[col] == 1, 'row'].to_numpy(), g.loc[g[col] == 0, 'row'].to_numpy()
            n = int(min(per_group, 0.8 * min(len(ai), len(no))))
            rec = dict(variant=variant, school=sc, flagged=len(ai), not_flagged=len(no), n_per_draw=n, description=desc)
            if n < 30:
                rec['skipped'] = f'fewer than 30 papers per draw ({len(ai)} flagged, {len(no)} not flagged)'
                out['groups'].append(rec)
                continue
            res = {}
            for gname, rows_ in (('ai', ai), ('not', no)):
                ext, ent = np.empty(draws), np.empty(draws)
                for k in range(draws):
                    pick = rows_[rng.choice(len(rows_), n, replace=False)]
                    V = Z[pick]
                    ext[k] = np.linalg.norm(V - V.mean(0), axis=1).max()
                    p = np.bincount(code[pick], minlength=50) / n
                    p = p[p > 0]
                    ent[k] = -(p * np.log2(p)).sum()
                res[gname] = dict(extent=ext, entropy=ent)
            for meas in ('extent', 'entropy'):
                a_, n_ = res['ai'][meas], res['not'][meas]
                rec[meas] = dict(ai=box_stats(a_), **{'not': box_stats(n_)}, ai_lower_share=float((a_ < n_).mean()), diff_median=float(np.median(a_) - np.median(n_)))
            out['groups'].append(rec)
            D.log(stage='fig3', variant=variant, school=sc, n=n, extent_diff=rec['extent']['diff_median'], entropy_diff=rec['entropy']['diff_median'])
    import json
    (A.RES / 'fig3.json').write_text(json.dumps(out))


# ------------------------------------------------------------------ wording control: the same test on the all-AI-rewritten abstracts

def rewrite_unit_vectors(model):
    """Unit vectors of the kept polish rewrites (<model>__allai, every paper's abstract in AI wording), centred on their own mean as allai_analyze.py does."""
    import emb_load as L
    papers, _ = L.universe()
    ids, X, _ = L.vectors(model + '__allai', 'abstract')
    ids = np.array(ids)
    ok = pd.Series(ids).isin(set(papers['paper_id'])).to_numpy()
    ids, X = ids[ok], X[ok]
    X = X - X.mean(0)
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    return ids, X


def stage_wording(args):
    """Size-matched dispersion and Vendi gap, AI minus non-AI, on the original abstracts and on their AI rewrites, with the SAME cells, rate-free 25% cut and draws (the same sets of
    papers, only the vectors differ), on the papers with a kept rewrite in all 7 models. share explained by wording = 1 - rewritten gap / original gap."""
    A.ensure_dirs()
    fr = pd.read_parquet(A.RES / 'frame.parquet')
    fr = fr[fr['x'].notna() & fr['topic'].notna() & fr['lab0'].notna() & fr['has_vec'] & fr['year'].isin(A.POST)].reset_index(drop=True)
    O, R = {}, {}
    for m in A.MODELS:
        O[m] = dict(zip(*[v for v in A.unit_vectors(m)]))
        ids, X = rewrite_unit_vectors(m)
        R[m] = dict(zip(ids, X))
    common = set(fr['paper_id'])
    for m in A.MODELS:
        common &= set(R[m]) & set(O[m])
    fr = fr[fr['paper_id'].isin(common)].reset_index(drop=True)
    D.log(stage='wording', papers=len(fr), with_rewrite_share=len(fr) / max(1, len(common)))
    Zo = {m: np.stack([O[m][p] for p in fr['paper_id']]).astype(np.float32) for m in A.MODELS}
    Zr = {m: np.stack([R[m][p] for p in fr['paper_id']]).astype(np.float32) for m in A.MODELS}
    flag = (fr['x'] >= A.THR - 1e-12).to_numpy()
    pop = Matched(fr, flag, Zo, {m: np.full(len(fr), np.nan) for m in A.MODELS})
    rng = np.random.default_rng(A.SEED)
    nl = pop.lab.max() + 1
    w1 = np.ones(len(fr))
    cells, ca, cn = pop._groups(w1)

    def both(a, n, m):
        return set_diff(Zo[m], a, n), set_diff(Zr[m], a, n)
    est = {m: [] for m in A.MODELS}
    for _ in range(DRAWS):
        a, n = pop.draw_sets(rng, cells, ca, cn, w1, M_SET)
        for m in A.MODELS:
            est[m].append(both(a, n, m))
    boot = {m: [] for m in A.MODELS}
    for _ in range(BOOT_SETS):
        w = rng.multinomial(nl, np.full(nl, 1.0 / nl))[pop.lab].astype(float)
        cb, ab, nb = pop._groups(w)
        ds = {m: [] for m in A.MODELS}
        for _ in range(BOOT_DRAWS):
            a, n = pop.draw_sets(rng, cb, ab, nb, w, M_SET)
            for m in A.MODELS:
                ds[m].append(both(a, n, m))
        for m in A.MODELS:
            boot[m].append(np.mean(np.array(ds[m]), axis=0))      # 2 (orig, rewritten) x 2 (dispersion, vendi)
    rows = []
    for m in A.MODELS:
        e = np.mean(np.array(est[m]), axis=0)
        b = np.array(boot[m])
        for j, name in enumerate(('dispersion', 'vendi')):
            o, r_ = e[0][j], e[1][j]
            bo, br = b[:, 0, j], b[:, 1, j]
            sh = 1 - br / bo
            q = lambda v: [float(x) for x in np.percentile(v, [2.5, 97.5])]   # noqa: E731
            rows.append(dict(model=m, measure=name, original=float(o), original_lo=q(bo)[0], original_hi=q(bo)[1], rewritten=float(r_), rewritten_lo=q(br)[0], rewritten_hi=q(br)[1],
                             share_wording=float(1 - r_ / o), share_lo=q(sh)[0], share_hi=q(sh)[1], papers=len(fr), ai_papers=int(flag.sum()), set_size=M_SET, matched_cells=len(cells)))
    pd.DataFrame(rows).to_parquet(A.RES / 'wording.parquet', index=False)
    D.log(stage='wording', rows=len(rows))
