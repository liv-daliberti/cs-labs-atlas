"""Who do the AI-writing and homogenization changes affect? Pre/post contrasts split by four characteristics (heterogeneity layer of the 12-school study).

  study_hetero.py [--id 2026-11-08] [--boot 1000]
reads   <results>/work/panel.parquet and <results>/heterogeneity/work/hetero_papers.parquet (study_hetero_attr.py), the snapshot's SPECTER2-proximity abstract embeddings
writes  <results>/heterogeneity/tables/*.csv|parquet
Splits: career (PI career-age tier), led (PI-led / student-led / other), field (theory / systems / ml_ai / other), gras (GRAS 2025 CS&E band of the school).
Outcomes (all ratios of sums over lab x year cells, so one lab-cluster bootstrap serves them all; resampling is stratified by school as in the main study):
  heavy_main, heavy_main_appendix   share of papers with >= 25% of passages flagged (detector v3), main body / main body + appendix
  abs_flag                          abstract flagged by the v1 detector
  within_lab                        mean pairwise distance (1 - cosine, SPECTER2 proximity) among a lab's papers of the group in one year
  lab_to_school                     mean distance from a lab's papers of the group to the papers of the school's OTHER labs in the same year
Per group and outcome: pre (2016-22), post (2023-25), post - pre, and the placebo (2019-21 minus 2016-18), each with a 95% percentile interval.
Between groups: the difference of the two groups' post - pre changes (a difference in differences), its interval, a bootstrap-SE normal p-value, and the same for the placebo.
Multiplicity: the PRIMARY family is every group pair x outcome of the four splits under the primary definitions, all 12 schools, post - pre (75 contrasts);
Holm (familywise) and Benjamini-Hochberg (FDR) are applied to it. Sensitivities (excluding harvard/jhu/washu, other cut-offs, field_alt, appointment tiers) are
reported next to it and are not part of the family.
"""
import argparse
import itertools
import json
import time

import numpy as np
import pandas as pd

import study_analyze as A
import study_common as C
import study_labstats as LS

SEED = 20261108
OUTCOMES = ['heavy_main', 'heavy_main_appendix', 'abs_flag', 'within_lab', 'lab_to_school']
SPLITS = {   # name -> (column, ordered groups, kind); kind 'lab' = attribute of the PI/school, 'paper' = attribute of the paper
    'career': ('career', ['early', 'mid', 'senior'], 'lab'),
    'led': ('led', ['pi_led', 'student_led', 'other'], 'paper'),
    'field': ('field', ['theory', 'systems', 'ml_ai', 'other'], 'paper'),
    'gras': ('gras', ['top10', 'r11_50', 'r51_300'], 'lab'),
}
VARIANTS = {   # sensitivity definitions, same machinery (not in the multiplicity family)
    'career:cut_8_18': ('career_cut_8_18', ['early', 'mid', 'senior'], 'lab'),
    'career:cut_12_22': ('career_cut_12_22', ['early', 'mid', 'senior'], 'lab'),
    'career:cut_10_25': ('career_cut_10_25', ['early', 'mid', 'senior'], 'lab'),
    'career:cut_7_15': ('career_cut_7_15', ['early', 'mid', 'senior'], 'lab'),
    'career:second_work': ('career_2plus', ['early', 'mid', 'senior'], 'lab'),
    'career:appointment': ('career_appt', ['early', 'mid', 'senior'], 'lab'),
    'career:tertile': ('career_t3', ['t1_youngest', 't2', 't3_oldest'], 'lab'),
    'career:quartile': ('career_q4', ['q1_youngest', 'q2', 'q3', 'q4_oldest'], 'lab'),
    'field:robotics_in_ml': ('field_alt', ['theory', 'systems', 'ml_ai', 'other'], 'paper'),
    # adjustment for the field mix: the same contrasts inside one field stratum (papers outside the stratum are dropped from the group, not from the school pool)
    'led|ml_ai': ('led_in_ml', ['pi_led', 'student_led', 'other'], 'paper'),
    'led|not_ml_ai': ('led_not_ml', ['pi_led', 'student_led', 'other'], 'paper'),
    'career|ml_ai': ('career_in_ml', ['early', 'mid', 'senior'], 'paper'),
    'career|not_ml_ai': ('career_not_ml', ['early', 'mid', 'senior'], 'paper'),
    'gras|ml_ai': ('gras_in_ml', ['top10', 'r11_50', 'r51_300'], 'paper'),
    'field|student_led': ('field_in_student_led', ['theory', 'systems', 'ml_ai', 'other'], 'paper'),
}
NMIN = {'lab': 5, 'paper': 3}     # papers of a group in a lab-year needed for the embedding outcomes (5 as in the main study; 3 where the group is a share of a lab's papers)
SCOPES = {'ALL': C.SCHOOLS, 'EXCL_PARTIAL': [s for s in C.SCHOOLS if s not in C.PARTIAL]}
PERIOD_CONTRASTS = ['post_minus_pre', 'post_minus_pre_excl2022', 'placebo_2019_21_minus_2016_18']


# ---------------------------------------------------------------- multiplicity
def holm(p):
    """Holm-Bonferroni adjusted p-values (familywise error)."""
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for rank, i in enumerate(o):
        run = max(run, min(1.0, (len(p) - rank) * p[i]))
        adj[i] = run
    return adj


def bh(p):
    """Benjamini-Hochberg adjusted p-values (false discovery rate)."""
    p = np.asarray(p, float)
    o = np.argsort(p)[::-1]
    adj = np.empty_like(p)
    run = 1.0
    n = len(p)
    for rank, i in enumerate(o):
        run = min(run, p[i] * n / (n - rank))
        adj[i] = min(run, 1.0)
    return adj


def normal_p(est, boot):
    """Two-sided p of a bootstrap-SE Wald test (a percentile p cannot go below 1/B; the family has 75 members)."""
    from math import erfc, sqrt
    sd = np.nanstd(boot, ddof=1)
    return float('nan') if not np.isfinite(sd) or sd == 0 else erfc(abs(est / sd) / sqrt(2))


# ---------------------------------------------------------------- data
def frame(pan, hp):
    """Lab-paper rows with the AI outcomes (detector-training papers are out of every AI rate, as in the main study)."""
    d = hp.merge(pan[['k', 'paper_id', 'flag_abstract', 'ai_share_main', 'ai_share_main_appendix', 'trained_on_v3']], on='k', how='left')
    ok = ~d['trained_on_v3'].fillna(False).astype(bool)
    for tag, col in (('heavy_main', 'ai_share_main'), ('heavy_main_appendix', 'ai_share_main_appendix')):
        d[tag] = np.where(ok & d[col].notna(), (d[col] >= 0.25).astype(float), np.nan)
    d['abs_flag'] = np.where(ok & d['flag_abstract'].notna(), d['flag_abstract'].astype(float), np.nan)
    pi = d.drop_duplicates('lab_id').set_index('lab_id')['age_any'].dropna()
    ml = d['field'] == 'ml_ai'
    for new, src, keep in (('led_in_ml', 'led', ml), ('led_not_ml', 'led', ~ml), ('career_in_ml', 'career', ml), ('career_not_ml', 'career', ~ml), ('gras_in_ml', 'gras', ml),
                           ('field_in_student_led', 'field', d['led'] == 'student_led')):
        d[new] = d[src].where(keep)
    for nm, q in (('career_t3', 3), ('career_q4', 4)):
        lab = ['t1_youngest', 't2', 't3_oldest'] if q == 3 else ['q1_youngest', 'q2', 'q3', 'q4_oldest']
        cut = pd.qcut(pi.rank(method='first', ascending=True), q, labels=lab)    # smallest career age = youngest
        d[nm] = d['lab_id'].map(cut.astype(object))
    return d


def composition(d):
    """Share of each field and of each led class within the groups of the other splits, pre and post (how the characteristics co-vary)."""
    rows = []
    d = d.assign(period=np.where(d.year.isin(LS.PRE), 'pre', np.where(d.year.isin(LS.POST), 'post', None)))
    for split, (col, groups, _) in SPLITS.items():
        for other in ('field', 'led'):
            if other == col:
                continue
            x = d[d[col].isin(groups) & d.period.notna()].drop_duplicates(['k', col])
            t = x.groupby([col, 'period', other]).size().rename('n').reset_index()
            t['share'] = t.n / t.groupby([col, 'period']).n.transform('sum')
            rows.append(t.rename(columns={col: 'group', other: 'class'}).assign(split=split, within=other))
    return pd.concat(rows, ignore_index=True)


def group_sums(keys, vecs):
    """{key: (n, vector sum)} by sorting once and reducing (keys: int array)."""
    o = np.argsort(keys, kind='stable')
    k = keys[o]
    starts = np.r_[0, np.flatnonzero(np.diff(k)) + 1]
    sums = np.add.reduceat(vecs[o], starts, axis=0)
    cnt = np.diff(np.r_[starts, len(k)])
    return {int(k[s]): (int(c), v) for s, c, v in zip(starts, cnt, sums)}


def emb_matrices(d, V, labs, col, groups, nmin):
    """{group: {'within_lab': (S, N), 'lab_to_school': (S, N)}} as lab x year matrices; d rows have 'r' (row of V), lab_id, school, year, k, group column col."""
    T, L = len(LS.YEARS), len(labs)
    li = pd.Series(np.arange(L), index=labs)
    de = d[d['r'].notna() & d['year'].between(LS.YEARS[0], LS.YEARS[-1])]
    lab_i = li.loc[de['lab_id']].to_numpy()
    yi = de['year'].to_numpy().astype(int) - LS.YEARS[0]
    X = V[de['r'].to_numpy().astype(int)]
    sch = pd.Series(np.arange(len(C.SCHOOLS)), index=C.SCHOOLS).loc[de['school']].to_numpy()
    uq = ~de.duplicated(['school', 'year', 'k']).to_numpy()
    sy = group_sums((sch * T + yi)[uq], X[uq])                      # school-year pool: every paper once
    ly = group_sums(lab_i * T + yi, X)                              # lab-year, all groups
    lab_school = np.zeros(L, int)
    lab_school[lab_i] = sch
    out = {}
    for g in groups:
        m = (de[col] == g).to_numpy()
        Sw = np.zeros((L, T)); Nw = np.zeros((L, T)); Ss = np.zeros((L, T)); Ns = np.zeros((L, T))
        if m.any():
            for key, (n, v) in group_sums(lab_i[m] * T + yi[m], X[m]).items():
                l, t = divmod(key, T)
                if n < nmin:
                    continue
                Sw[l, t] = float(v @ v) - n
                Nw[l, t] = n * (n - 1)
                nl, vl = ly[key]
                nsy, vsy = sy[int(lab_school[l]) * T + t]
                if nsy - nl > 0:
                    Ss[l, t] = float(v @ (vsy - vl))
                    Ns[l, t] = n * (nsy - nl)
        out[g] = {'within_lab': (Sw, Nw), 'lab_to_school': (Ss, Ns)}
    return out


def ratio_matrices(d, labs, col, groups, outcome):
    out = {}
    for g in groups:
        x = d[(d[col] == g) & d[outcome].notna()]
        S, N, _ = LS.lab_year(x, 'lab_id', 'year', outcome, labs=labs) if len(x) else (np.zeros((len(labs), len(LS.YEARS))),) * 2 + (labs,)
        out[g] = (S, N)
    return out


# ---------------------------------------------------------------- estimation
def estimate(mats, W, tf, meta):
    """mats {group: (S, N)} on the rows of W's labs. Returns (series, group effects, pair differences) as DataFrames."""
    ser, eff, per = [], [], {}
    for g, (S, N) in mats.items():
        M = tf(LS.series(S, N, W))
        est, lo, hi = LS.describe(M)
        ser.append(pd.DataFrame(dict(meta, group=g, year=LS.YEARS, est=est, lo=lo, hi=hi, n=N.sum(0))))
        for name, (post, pre) in LS.CONTRASTS.items():
            if name not in PERIOD_CONTRASTS:
                continue
            a, b = tf(LS.pooled(S, N, W, post)), tf(LS.pooled(S, N, W, pre))
            dd = a - b
            per[(g, name)] = dd
            lo_, hi_ = LS.ci(dd[1:])
            eff.append(dict(meta, group=g, contrast=name, pre=float(b[0]), post=float(a[0]), est=float(dd[0]), lo=lo_, hi=hi_,
                            n_pre=float(sum(N[:, y - LS.YEARS[0]].sum() for y in LS.CONTRASTS[name][1])), n_post=float(sum(N[:, y - LS.YEARS[0]].sum() for y in LS.POST))))
    pairs = []
    for g1, g2 in itertools.combinations(mats, 2):
        for name in PERIOD_CONTRASTS:
            dd = per[(g1, name)] - per[(g2, name)]
            lo_, hi_ = LS.ci(dd[1:])
            pairs.append(dict(meta, g1=g1, g2=g2, contrast=name, est=float(dd[0]), lo=lo_, hi=hi_, se=float(np.nanstd(dd[1:], ddof=1)), p=normal_p(dd[0], dd[1:])))
    return pd.concat(ser, ignore_index=True), pd.DataFrame(eff), pd.DataFrame(pairs)


def run(d, V, boot, log=print):
    labs_all = np.sort(d['lab_id'].unique())
    lab_school = d.drop_duplicates('lab_id').set_index('lab_id')['school'].reindex(labs_all).to_numpy()
    sers, effs, prs, sizes = [], [], [], []
    specs = list(SPLITS.items()) + list(VARIANTS.items())
    for name, (col, groups, kind) in specs:
        t0 = time.time()
        dd = d[d[col].isin(groups)]
        base = name.split(':')[0]
        fam = 'primary' if name in SPLITS else 'sensitivity'
        for out in OUTCOMES:
            if out in ('within_lab', 'lab_to_school'):
                continue
            mats = ratio_matrices(dd, labs_all, col, groups, out)
            _fit(mats, out, name, base, fam, labs_all, lab_school, boot, lambda x: x, sers, effs, prs)
        em = emb_matrices(dd, V, labs_all, col, groups, NMIN[kind])
        for out in ('within_lab', 'lab_to_school'):
            mats = {g: em[g][out] for g in groups}
            _fit(mats, out, name, base, fam, labs_all, lab_school, boot, lambda x: 1 - x, sers, effs, prs)
        for g in groups:
            x = dd[dd[col] == g]
            sizes.append(dict(split=name, group=g, labs=x['lab_id'].nunique(), pis=x[['school', 'pi']].drop_duplicates().shape[0], papers=x['k'].nunique(),
                              papers_pre=x[x.year.isin(LS.PRE)]['k'].nunique(), papers_post=x[x.year.isin(LS.POST)]['k'].nunique(),
                              schools=x['school'].nunique()))
        log(name, round(time.time() - t0), 's', flush=True)
    ser, eff, pr = pd.concat(sers, ignore_index=True), pd.concat(effs, ignore_index=True), pd.concat(prs, ignore_index=True)
    return ser, eff, pr, pd.DataFrame(sizes)


def _fit(mats, out, name, base, fam, labs_all, lab_school, boot, tf, sers, effs, prs):
    for scope, schools in SCOPES.items():
        msk = np.isin(lab_school, schools)
        W = LS.weights(lab_school[msk], boot, SEED)
        sub = {g: (S[msk], N[msk]) for g, (S, N) in mats.items()}
        meta = dict(split=name, family=fam, scope=scope, outcome=out, n_labs=int(msk.sum()))
        s, e, p = estimate(sub, W, tf, meta)
        sers.append(s); effs.append(e); prs.append(p)


def add_multiplicity(pr):
    """Primary family = primary-definition splits, all 12 schools, post_minus_pre: Holm and BH over it; the placebo difference rides along."""
    pr = pr.copy()
    plc = pr[pr.contrast == 'placebo_2019_21_minus_2016_18'].set_index(['split', 'scope', 'outcome', 'g1', 'g2'])
    key = pr.set_index(['split', 'scope', 'outcome', 'g1', 'g2']).index
    for c in ('est', 'lo', 'hi', 'p'):
        pr['placebo_' + c] = plc[c].reindex(key).to_numpy()
    fam = (pr.family == 'primary') & (pr.scope == 'ALL') & (pr.contrast == 'post_minus_pre')
    pr['in_family'] = fam
    pr['p_holm'] = np.nan
    pr['p_bh'] = np.nan
    ok = fam & pr.p.notna()
    pr.loc[ok, 'p_holm'] = holm(pr.loc[ok, 'p'])
    pr.loc[ok, 'p_bh'] = bh(pr.loc[ok, 'p'])
    pr['excludes_zero'] = (pr.lo > 0) | (pr.hi < 0)
    pr['placebo_excludes_zero'] = (pr.placebo_lo > 0) | (pr.placebo_hi < 0)
    return pr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('--boot', type=int, default=1000)
    a = ap.parse_args()
    out = C.results_dir(a.id)
    tab = out / 'heterogeneity' / 'tables'
    tab.mkdir(parents=True, exist_ok=True)
    snap = C.snapshot_dir(a.id)
    pan = pd.read_parquet(out / 'work' / 'panel.parquet')
    hp = pd.read_parquet(out / 'heterogeneity' / 'work' / 'hetero_papers.parquet')
    d = frame(pan, hp)
    rows, V = A.load_emb(snap, C.HEADLINE_MODEL, pan['paper_id'].to_numpy())
    pos = pd.Series(np.arange(len(rows)), index=pan['k'].to_numpy()[rows])
    d['r'] = d['k'].map(pos)
    print('papers with an abstract embedding', int(d['r'].notna().sum()), 'of', len(d), flush=True)
    ser, eff, pr, sizes = run(d, V, a.boot)
    pr = add_multiplicity(pr)
    for nm, df in (('hetero_series', ser), ('hetero_group_effects', eff), ('hetero_pair_diffs', pr), ('hetero_group_sizes', sizes)):
        df.to_csv(tab / f'{nm}.csv', index=False)
        df.to_parquet(tab / f'{nm}.parquet')
        print(nm, df.shape)
    fam = pr[pr.in_family]
    comp = composition(d)
    comp.to_csv(tab / 'hetero_composition.csv', index=False)
    summary = dict(boot=a.boot, seed=SEED, embedding_model=C.HEADLINE_MODEL, primary_family=len(fam), pair_contrasts_total=len(pr), group_effects_total=len(eff),
                   holm_survivors=int((fam.p_holm < 0.05).sum()), bh_survivors=int((fam.p_bh < 0.05).sum()),
                   excludes_zero_uncorrected=int(fam.excludes_zero.sum()), nominal_p05=int((fam.p < 0.05).sum()))
    (tab / 'hetero_summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
