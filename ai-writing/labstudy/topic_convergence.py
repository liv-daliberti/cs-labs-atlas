"""Analysis 1: do different labs' topic mixes become more alike over time, and faster after 2023?

  topic_convergence.py run [--levels ...] [--variants main,m5,m20,a0.25,a4,nollm,panel] [--control]    -> OUT/topics/{series,trend,labyear}_*.parquet
  topic_convergence.py report                                                                         -> reports/TOPIC-CONVERGENCE.md   (topic_report.py)
Levels: bt_qwen3_0p6b, bt_specter2_proximity (BERTopic topics of the abstract embeddings), oa_subfield, oa_topic (OpenAlex primary topic of the work).
Measures per year (2016-2025; labs with >= m papers carrying a topic; m-paper size-matched draws, `reps` per lab-year; smoothing alpha toward the pooled mix):
  jsd        mean pairwise Jensen-Shannon divergence between labs: scopes all, between_school, within_school, within_dept, dtype:<department type>
  dist_centroid  each lab's JSD to the year's all-lab centroid (mean over labs); dist_pre_centroid to the fixed 2016-2021 centroid
  top_llm    share of labs whose top topic is LLM-related ("LLM topic" = topic label matches lcommon.LLM_RE); mass_llm the mean share of a lab's papers on LLM topics
Trend statistics (lab bootstrap, B replicates; multinomial lab weights, pair weight w_i w_j; percentile 95% intervals): slope 2016-2025, slope 2016-2021, mean(2023-25) -
mean(2016-21), `dev_2023` = mean(2023-25) - the 2016-21 linear trend projected, and `placebo<b>` = the same deviation for a break at b in 2019/2020/2021 (trend on
2016..b-1, window b..min(b+2, 2021)). A post-2022 effect counts only when dev_2023 is beyond the placebo deviations.
Variants: nollm = the same on papers whose topic is not an LLM topic (labs with < m such papers drop); panel = labs eligible in >= 6 of 10 years with >= 2 pre and >= 2 post
years (a fixed lab panel); m5/m20/a0.25/a4 = minimum-papers rule and smoothing sensitivities.
Wording control (--control): the BERTopic levels on the all-AI (polish) rewritten abstracts: papers go to the nearest topic centroid of the originals in both corpora
(embeddings of the original and of the rewritten abstract; allai_analyze.label_sets), the draws are paired, the gap is `ai - orig` with its own bootstrap interval.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import frame as FR
import lcommon as L
import tcore as T

LEVELS = ['bt_qwen3_0p6b', 'bt_specter2_proximity', 'oa_subfield', 'oa_topic']
SCOPES = ('all', 'within_school', 'within_dept', 'within_dtype')
TCFG = L.CFG['topic']
YEARS = L.YEARS
Y_IDX = {y: i for i, y in enumerate(YEARS)}


# ------------------------------------------------------------------ levels
def level_runs(df, level):
    """(codes, valid, K, llm_mask, genai_mask, labels list) of one level on the frame rows."""
    if level.startswith('bt_'):
        model = level[3:]
        t = df[level].to_numpy(dtype=float)
        valid = ~np.isnan(t)
        codes = np.where(valid, t, -1).astype(int)
        lab = pd.read_parquet(L.EMB / 'results' / f'topic_labels_{model}.parquet').sort_values('topic')
        K = int(max(lab['topic'].max(), codes.max())) + 1
        names = [''] * K
        for tid, lb in zip(lab['topic'], lab['label']):
            names[int(tid)] = lb
    else:
        col = 'oa_topic' if level == 'oa_topic' else 'oa_subfield'
        f, uniq = pd.factorize(df[col])
        codes, valid, K, names = f.astype(int), f >= 0, len(uniq), [str(u) for u in uniq]
    llm = np.array([bool(L.LLM_RE.search(n)) for n in names])
    gen = np.array([bool(L.GENAI_RE.search(n)) for n in names])
    if level == 'oa_subfield':
        llm[:] = False
        gen[:] = False
    return codes, valid, K, llm, gen, names


# ------------------------------------------------------------------ one run
def execute(run, lp, row_of, labs, m, reps, alpha, years, lab_filter=None, jobs=8):
    g = T.groups_of(lp, row_of, run, m)
    if lab_filter is not None:
        g = g[g['lab_id'].isin(lab_filter)]
    lm = T.lab_meta(labs)
    scopes = SCOPES
    args = [(run, g, lm, y, m, reps, alpha, TCFG['max_pairs'], scopes, None) for y in years]
    with ProcessPoolExecutor(min(jobs, len(years))) as ex:
        res = list(ex.map(T.year_job, args))
    ly = [r[0] for r in res if r]
    pairs = [r[1] for r in res if r and r[1] is not None]
    cent = {y: r[2] for y, r in zip(years, res) if r}
    pre = [cent[y] for y in years if y in L.PRE and y in cent]
    cp = np.mean(pre, 0)
    args2 = [(run, g, lm, y, m, reps, alpha, TCFG['max_pairs'], scopes, cp) for y in years if y in cent]
    with ProcessPoolExecutor(min(jobs, len(args2))) as ex:
        d2 = list(ex.map(T.year_job, args2))
    ly = pd.concat(ly, ignore_index=True)
    ly['dist_pre_centroid'] = np.concatenate(d2)
    return ly, pd.concat(pairs, ignore_index=True), lm


# ------------------------------------------------------------------ series and trend statistics
def weights(n, B, seed):
    rng = np.random.default_rng(seed)
    W = np.ones((B + 1, n), np.float32)
    W[1:] = rng.multinomial(n, np.full(n, 1.0 / n), size=B).astype(np.float32)
    return W


def series_matrix(ly, pairs, lm, W, years):
    """{(measure, scope): array (B+1, len(years))} of weighted yearly means (row 0 = unweighted point estimate)."""
    code = lm['code']
    out = {}
    nb = W.shape[0]
    # pair measures
    for (scope, y), d in pairs.groupby(['scope', 'year']):
        ci, cj = d['lab_i'].map(code).to_numpy(), d['lab_j'].map(code).to_numpy()
        w = W[:, ci] * W[:, cj]
        v = (w * d['jsd'].to_numpy()[None]).sum(1) / np.maximum(w.sum(1), 1e-9)
        out.setdefault(('jsd', scope), np.full((nb, len(years)), np.nan))[:, Y_IDX_OF(years)[y]] = v
    # lab measures: scopes all and by department type
    for y, d in ly.groupby('year'):
        c = d['lab_id'].map(code).to_numpy()
        for meas in ('dist_centroid', 'dist_pre_centroid', 'top_llm', 'top_genai', 'mass_llm', 'entropy'):
            for scope in ['all'] + sorted(t for t in d['dtype'].unique() if t not in ('unknown', 'other')):
                sel = np.ones(len(d), bool) if scope == 'all' else (d['dtype'] == scope).to_numpy()
                if sel.sum() < 5:
                    continue
                w = W[:, c[sel]]
                v = (w * d[meas].to_numpy()[sel][None]).sum(1) / np.maximum(w.sum(1), 1e-9)
                out.setdefault((meas, scope if scope == 'all' else 'dtype:' + scope), np.full((nb, len(years)), np.nan))[:, Y_IDX_OF(years)[y]] = v
    return out


def Y_IDX_OF(years):
    return {y: i for i, y in enumerate(years)}


def _trend_fit(ys, S, tr_years):
    """(slope, intercept) per row of S fitted on the years tr_years (list of years in `ys`)."""
    ix = [ys.index(y) for y in tr_years]
    x = np.array(tr_years, float)
    X = S[:, ix]
    xm, ym = x.mean(), X.mean(1, keepdims=True)
    b = ((x - xm)[None] * (X - ym)).sum(1) / ((x - xm) ** 2).sum()
    return b, ym[:, 0] - b * xm


def trend_stats(S, ys):
    """dict stat -> array (B+1) from series matrix S (B+1 x years)."""
    st = {}
    pre = [y for y in ys if y in L.PRE]
    post = [y for y in ys if y in L.POST]
    ix = lambda yy: [ys.index(y) for y in yy]  # noqa: E731
    st['mean_pre'] = S[:, ix(pre)].mean(1)
    st['mean_post'] = S[:, ix(post)].mean(1)
    st['post_minus_pre'] = st['mean_post'] - st['mean_pre']
    b, _ = _trend_fit(ys, S, ys)
    st['slope_all_per_year'] = b
    b, a = _trend_fit(ys, S, pre)
    st['slope_pre_per_year'] = b
    st['dev_2023'] = S[:, ix(post)].mean(1) - (a + b * np.mean(post))
    for br in L.BREAKS:
        tr = [y for y in ys if y < br]
        win = [y for y in ys if br <= y <= min(br + 2, L.CFG['pre_end'])]
        if len(tr) >= 3 and win:
            b2, a2 = _trend_fit(ys, S, tr)
            st[f'placebo{br}'] = S[:, ix(win)].mean(1) - (a2 + b2 * np.mean(win))
    st['last_minus_first'] = S[:, -1] - S[:, 0]
    return st


def ci(a):
    return float(a[0]), float(np.nanpercentile(a[1:], 2.5)), float(np.nanpercentile(a[1:], 97.5))


def tables(tag, S_by, years):
    """series and trend DataFrames from {(measure, scope): matrix}; tag = dict(level, variant, name)."""
    ser, tr = [], []
    stats = {}
    for (meas, scope), S in S_by.items():
        if np.isnan(S[0]).sum() > len(years) - 5:
            continue
        for j, y in enumerate(years):
            if np.isfinite(S[0, j]):
                e, lo, hi = ci(S[:, j])
                ser.append(dict(tag, measure=meas, scope=scope, year=y, est=e, lo=lo, hi=hi))
        Sf = S.copy()
        miss = np.isnan(Sf).any(0)
        if miss.any():                                           # interpolate nothing: trend statistics need every year
            continue
        stats[(meas, scope)] = trend_stats(Sf, years)
        for k, a in stats[(meas, scope)].items():
            e, lo, hi = ci(a)
            tr.append(dict(tag, measure=meas, scope=scope, stat=k, est=e, lo=lo, hi=hi))
    return pd.DataFrame(ser), pd.DataFrame(tr), stats


def gap_tables(tag, stats_a, stats_o, S_a, S_o, years):
    tr, ser = [], []
    for key in stats_a:
        if key not in stats_o:
            continue
        for k in stats_a[key]:
            if k in stats_o[key]:
                e, lo, hi = ci(stats_a[key][k] - stats_o[key][k])
                tr.append(dict(tag, measure=key[0], scope=key[1], stat=k, est=e, lo=lo, hi=hi))
        d = S_a[key] - S_o[key]
        for j, y in enumerate(years):
            if np.isfinite(d[0, j]):
                e, lo, hi = ci(d[:, j])
                ser.append(dict(tag, measure=key[0], scope=key[1], year=y, est=e, lo=lo, hi=hi))
    return pd.DataFrame(ser), pd.DataFrame(tr)


def fe_break(ly, y='dist_centroid', tag=None):
    """Lab-FE regression of a lab-year measure on Post for the real break (2023, 2022 dropped) and the placebo breaks (2016-2021 only); lab-clustered."""
    import dose_reg as R
    rows = []
    d = ly.copy()
    for br in ['real'] + L.BREAKS:
        if br == 'real':
            x = d[d['year'].isin(L.PRE + L.POST)].copy()
            x['post'] = x['year'].isin(L.POST).astype(float)
        else:
            x = d[d['year'].isin(L.PRE)].copy()
            x['post'] = (x['year'] >= br).astype(float)
        r = R.fit(x, y, 'post', fe=['lab_id'], cluster='lab_id')
        rows.append(dict(tag or {}, measure=y, spec=f'fe_post_{br}', est=r['beta'], lo=r['lo'], hi=r['hi'], n=r['n'], labs=r['clusters']))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ driver
def panel_labs(ly_main, years):
    """Labs eligible in >= 6 of the 10 years with >= 2 pre (<= 2021) and >= 2 post (>= 2023) years."""
    c = ly_main.groupby('lab_id')['year'].agg(lambda s: (len(s), sum(y in L.PRE for y in s), sum(y in L.POST for y in s)))
    return {l for l, (a, b, p) in c.items() if a >= 6 and b >= 2 and p >= 2}


VARIANTS = {'main': dict(m=TCFG['min_papers'], alpha=TCFG['alpha']),
            'm5': dict(m=5, alpha=TCFG['alpha']), 'm20': dict(m=20, alpha=TCFG['alpha']),
            'a0.25': dict(m=TCFG['min_papers'], alpha=0.25), 'a4': dict(m=TCFG['min_papers'], alpha=4.0),
            'nollm': dict(m=TCFG['min_papers'], alpha=TCFG['alpha']), 'panel': dict(m=TCFG['min_papers'], alpha=TCFG['alpha'])}


def run_all(levels, variants, control, boot, jobs):
    df, lp, labs = FR.load()
    lp = lp[lp['year'].between(YEARS[0], YEARS[-1])]
    row_of = dict(zip(df['paper_id'], range(len(df))))
    lm = T.lab_meta(labs)
    W = weights(len(lm['code']), boot, L.SEED)
    S_all, T_all, LY_all, FE_all, INFO = [], [], [], [], []
    cache_main = {}
    for level in levels:
        codes, valid, K, llm, gen, names = level_runs(df, level)
        INFO.append(dict(level=level, topics=K, valid_papers=int(valid.sum()), llm_topics=int(llm.sum()), llm_papers=int((valid & llm[np.maximum(codes, 0)]).sum()),
                         genai_topics=int(gen.sum()), llm_labels=' | '.join(n for n, b in zip(names, llm) if b)[:3000]))
        for vname in variants:
            v = VARIANTS[vname]
            if vname in ('m5', 'm20', 'a0.25', 'a4') and level not in ('bt_qwen3_0p6b', 'oa_topic'):
                continue
            if vname == 'nollm' and not llm.any():
                continue
            vmask = valid & ~llm[np.maximum(codes, 0)] if vname == 'nollm' else valid
            run = T.Run('orig', codes, vmask, K, llm, gen)
            lab_filter = None
            if vname == 'panel':
                lab_filter = panel_labs(cache_main[level], YEARS)
            ly, pairs, _ = execute(run, lp, row_of, labs, v['m'], TCFG['reps'], v['alpha'], YEARS, lab_filter, jobs)
            if vname == 'main':
                cache_main[level] = ly
            tag = dict(level=level, variant=vname, name='orig')
            Sm = series_matrix(ly, pairs, lm, W, YEARS)
            s, t, _ = tables(tag, Sm, YEARS)
            S_all.append(s); T_all.append(t)
            LY_all.append(ly.assign(level=level, variant=vname, name='orig'))
            FE_all.append(pd.concat([fe_break(ly, y, tag) for y in ('dist_centroid', 'dist_pre_centroid', 'mass_llm')]))
            L.log(step='topic_run', level=level, variant=vname, labs=int(ly['lab_id'].nunique()), lab_years=len(ly), pairs=len(pairs))
    if control:
        import allai_analyze as AA
        for model in AA.BT_MODELS:
            level = 'bt_' + model
            if levels and level not in levels:
                continue
            papers, _, Xo, Xa, _, _ = AA.load_pair(model, 'polish')
            sets = AA.label_sets(model, papers, Xo, Xa)
            lo, la, K, info = sets['bt']
            pid = papers['paper_id'].to_numpy()
            sub = df[df['paper_id'].isin(set(pid))].reset_index(drop=True)
            row_s = dict(zip(sub['paper_id'], range(len(sub))))
            pos = {p: i for i, p in enumerate(pid)}
            order = np.array([pos[p] for p in sub['paper_id']])
            _, _, Kb, llm_b, gen_b, _ = level_runs(df, level)
            K = max(K, Kb)
            tops = np.sort(pd.read_parquet(L.EMB / 'results' / f'topics_{model}.parquet')['topic'].unique()).astype(int)
            # nearest-centroid indices index the sorted topic ids present among these papers: map back to topic ids for the LLM mask
            tt = pd.read_parquet(L.EMB / 'results' / f'topics_{model}.parquet').set_index('paper_id')['topic']
            present = np.sort(tt[tt.index.isin(set(pid))].unique().astype(int))
            llm_c = llm_b[present]
            gen_c = gen_b[present]
            valid = np.ones(len(sub), bool)
            outs = {}
            for nm, lab in (('orig', lo), ('ai', la)):
                run = T.Run(nm, lab[order], valid, len(present), llm_c, gen_c)
                lp_s = lp[lp['paper_id'].isin(row_s)]
                ly, pairs, _ = execute(run, lp_s, row_s, labs, TCFG['min_papers'], TCFG['reps'], TCFG['alpha'], YEARS, None, jobs)
                Sm = series_matrix(ly, pairs, lm, W, YEARS)
                tag = dict(level=level, variant='control', name=nm)
                s, t, st = tables(tag, Sm, YEARS)
                S_all.append(s); T_all.append(t)
                LY_all.append(ly.assign(level=level, variant='control', name=nm))
                FE_all.append(pd.concat([fe_break(ly, y, tag) for y in ('dist_centroid', 'mass_llm')]))
                outs[nm] = (Sm, st)
            tagg = dict(level=level, variant='control', name='gap_ai_minus_orig')
            gs, gt = gap_tables(tagg, outs['ai'][1], outs['orig'][1], outs['ai'][0], outs['orig'][0], YEARS)
            S_all.append(gs); T_all.append(gt)
            INFO.append(dict(level=level + ':control', topics=len(present), valid_papers=len(sub), agree_with_bertopic=info.get('agree_with_bertopic')))
            L.log(step='topic_control', level=level, papers=len(sub), agree=info.get('agree_with_bertopic'))
    d = L.out('topics')
    tag_files = '_'.join(levels) if len(levels) < len(LEVELS) else 'all'
    suffix = ('' if tag_files == 'all' else '_' + tag_files) + ('_control' if control else '') + ('_' + variants[0] if len(variants) == 1 else '')
    for name, parts in (('series', S_all), ('trend', T_all), ('fe', FE_all)):
        L.write_atomic(pd.concat([p for p in parts if len(p)], ignore_index=True), d / f'{name}{suffix}.parquet')
    L.write_atomic(pd.concat(LY_all, ignore_index=True), d / f'labyear{suffix}.parquet')
    L.write_atomic(pd.DataFrame(INFO), d / f'levels{suffix}.parquet')
    L.log(step='topic_done', suffix=suffix, tag=tag_files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'report'])
    ap.add_argument('--levels', default=','.join(LEVELS))
    ap.add_argument('--variants', default='main,m5,m20,a0.25,a4,nollm,panel')
    ap.add_argument('--control', action='store_true')
    ap.add_argument('--boot', type=int, default=TCFG['boot'])
    ap.add_argument('-j', type=int, default=8)
    a = ap.parse_args()
    if a.cmd == 'report':
        import topic_report
        topic_report.main()
        return
    run_all(a.levels.split(','), [v for v in a.variants.split(',') if v and v != 'none'], a.control, a.boot, a.j)


if __name__ == '__main__':
    main()
