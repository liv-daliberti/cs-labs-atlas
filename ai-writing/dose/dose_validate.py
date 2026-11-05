"""Re-validate the detectors on the whole universe (owner 2026-11-04, Part B) and cross-check them with the detector-free measures.

  dose_validate.py [--recalibrate]
reads    AI_SCORES/ai_scores.sqlite, results/liang_alpha.parquet, universe, OpenAlex fields
writes   AI_SCORES/results/validation_*.parquet and validation.md (the tables the report includes), figures in --fig-dir,
         with --recalibrate: group thresholds into the container (`thresholds`) and `ai_share_cal` in papers (+ papers.parquet)
Checks
  1. Flagged passage share in 2016-2021 papers (design FPR 1%) per school and per broad field, from all papers and from the out-of-sample subset
     (not `trained_on`). 95% intervals are bootstrap over papers.
  2. The same for the v1 abstract detector (flagged abstract share).
  3. Yearly flagged passage share, mean ai_share and flagged abstract share per school, 2016-2026.
  4. Agreement with the detector-free measures (Kobak style-word rate, Liang alpha) per school and year.
A group is "well above" the design rate when the lower end of its interval exceeds 1.5%; its threshold is then recut at the 99th percentile of its own
out-of-sample 2016-2021 passages (a school's papers use their home school's cut, a field's papers the field's; the larger of the two applies).
"""
import argparse
import os
import sqlite3

import numpy as np
import pandas as pd

import dcommon as D
import dose_data as DD
import dose_md as M
import dose_stats as S

DESIGN = 0.01
TOL = 0.015
MIN_FIELD = 300


def field_groups(df, min_n=MIN_FIELD):
    """Broad field = OpenAlex field of the primary topic; fields with fewer than min_n scored 2016-2021 papers pool into 'Other'; no topic -> 'Unknown'."""
    f = df['oa_field'].fillna('Unknown')
    n = df[df['year'].between(2016, 2021) & df['ai_share'].notna()].groupby(df['oa_field'].fillna('Unknown')).size()
    small = set(n[n < min_n].index) - {'Unknown'}
    return f.where(~f.isin(small), 'Other')


def explode_schools(df):
    e = df.explode('schools').rename(columns={'schools': 'school'})
    return e[e['school'].isin(D.SCHOOLS)]


def share_row(g):
    """Flagged passage share, mean ai_share, ai_any and share(ai_share >= .25) of a group of scored papers, with paper-bootstrap intervals."""
    est, lo, hi = S.boot_ratio(g['n_flagged'], g['n_passages'], B=400)
    ms, mlo, mhi = S.boot_ratio(g['ai_share'], np.ones(len(g)), B=400, seed=1)
    return dict(papers=len(g), passages=int(g['n_passages'].sum()), flagged=est, lo=lo, hi=hi, mean_ai_share=ms, mean_lo=mlo, mean_hi=mhi,
                ai_any=g['ai_any'].mean(), share_ge25=(g['ai_share'] >= 0.25).mean())


def pre_table(df, by, subset):
    d = df[df['year'].between(2016, 2021) & df['ai_share'].notna()]
    if subset == 'out_of_sample':
        d = d[~d['trained_on']]
    if by == 'school':
        d = explode_schools(d)
    rows = []
    for k, g in d.groupby(by):
        rows.append(dict(**{by: k}, subset=subset, **share_row(g)))
    t = pd.DataFrame(rows)
    t['well_above'] = t['lo'] > TOL
    return t


def abstract_pre_table(df, by):
    d = df[df['year'].between(2016, 2021) & df['p_ai_abstract'].notna()]
    if by == 'school':
        d = explode_schools(d)
    rows = []
    for k, g in d.groupby(by):
        est, lo, hi = S.boot_ratio(g['flag_abstract'], np.ones(len(g)), B=400)
        rows.append({by: k, 'abstracts': len(g), 'flagged': est, 'lo': lo, 'hi': hi, 'well_above': lo > 0.015})
    return pd.DataFrame(rows)


def yearly_table(df):
    d = explode_schools(df)
    rows = []
    for (s, y), g in d.groupby(['school', 'year']):
        sc = g[g['ai_share'].notna()]
        a = g[g['p_ai_abstract'].notna()]
        r = dict(school=s, year=int(y), fulltexts=len(sc), abstracts=len(a))
        if len(sc):
            r.update({k: v for k, v in share_row(sc).items() if k in ('flagged', 'lo', 'hi', 'mean_ai_share', 'mean_lo', 'mean_hi', 'share_ge25')})
        if len(a):
            e, l, h = S.boot_ratio(a['flag_abstract'], np.ones(len(a)), B=300)
            r.update(abs_flagged=e, abs_lo=l, abs_hi=h)
        for c in ('kobak_abs', 'kobak_ft'):
            if g[c].notna().any():
                r[c] = g[c].mean()
        rows.append(r)
    return pd.DataFrame(rows)


def group_thresholds(df, passages, school_bad, field_bad, q=0.99):
    """{('school', name): thr, ('field', name): thr}: the q-quantile of out-of-sample 2016-2021 passage scores of each flagged group."""
    pre = df[df['year'].between(2016, 2021) & df['ai_share'].notna() & ~df['trained_on']][['paper_id', 'home_school', 'field_grp']]
    p = passages.merge(pre, on='paper_id')
    out = {}
    for s in school_bad:
        out[('school', s)] = float(np.quantile(p.loc[p['home_school'] == s, 'p'], q))
    for f in field_bad:
        out[('field', f)] = float(np.quantile(p.loc[p['field_grp'] == f, 'p'], q))
    return out


def paper_cuts(df, thr, default=D.V2_THRESHOLD):
    """Per-paper passage threshold: the larger of the global cut and the cuts of the paper's home school and field group (`thr` from group_thresholds)."""
    t = np.full(len(df), default)
    for (kind, name), val in thr.items():
        col = 'home_school' if kind == 'school' else 'field_grp'
        t = np.where(df[col].to_numpy() == name, np.maximum(t, val), t)
    return pd.Series(t, index=df['paper_id'])


def recalibrated_share(df, passages, thr):
    """ai_share_cal per paper: flagged at max(global, school cut, field cut) of the paper's home school and field group."""
    cut = paper_cuts(df, thr)
    p = passages.assign(flag=passages['p'].to_numpy() >= passages['paper_id'].map(cut).to_numpy())
    share = p.groupby('paper_id')['flag'].mean()
    return df['paper_id'].map(share)


def rise_table(df):
    """Where does the 2016-2021 rise of the flagged rates sit? Per group: the 2016-17 and 2020-21 flagged abstract share (v1) and flagged passage share, and the change."""
    d = df[df['year'].between(2016, 2021)].copy()
    d['early'] = d['year'] <= 2017
    rows = []
    for by in ('school', 'field_grp', 'venue_type', 'text_kind'):
        dd = explode_schools(d) if by == 'school' else d
        if by not in dd:
            continue
        for k, g in dd.groupby(by):
            r = dict(by=by, group=str(k))
            for name, col, w in (('abs', 'flag_abstract', None), ('par', 'n_flagged', 'n_passages')):
                for part, m in (('early', g['year'] <= 2017), ('late', g['year'] >= 2020)):
                    x = g[m]
                    if w is None:
                        x = x[x[col].notna()]
                        r[f'{name}_{part}'] = x[col].mean() if len(x) else np.nan
                        r[f'{name}_{part}_n'] = len(x)
                    else:
                        x = x[x[w].notna()]
                        r[f'{name}_{part}'] = x[col].sum() / x[w].sum() if len(x) and x[w].sum() else np.nan
                        r[f'{name}_{part}_n'] = len(x)
                r[f'{name}_change'] = r[f'{name}_late'] - r[f'{name}_early']
            rows.append(r)
    return pd.DataFrame(rows)


def cross_check(yearly, liang):
    """School-year panel: detector, Kobak and Liang; Pearson correlations over the panel and within school (after removing school means)."""
    panel = yearly.merge(liang.rename(columns={'alpha': 'liang_alpha'})[['school', 'year', 'liang_alpha', 'n']].rename(columns={'n': 'liang_n'}), on=['school', 'year'], how='left')
    cols = ['flagged', 'mean_ai_share', 'abs_flagged', 'kobak_abs', 'kobak_ft', 'liang_alpha']
    corr = panel[cols].corr()
    within = panel.copy()
    within[cols] = within[cols] - within.groupby('school')[cols].transform('mean')
    return panel, corr, within[cols].corr()


def write_figures(yearly, liang, fig_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig_dir.mkdir(parents=True, exist_ok=True)
    panels = [('flagged', 'Passage detector: flagged passage share'), ('abs_flagged', 'Abstract detector (v1): flagged abstract share'),
              ('kobak_abs', 'Kobak style words per 1,000 tokens (abstract)'), ('liang_alpha', 'Liang et al. estimate of the LLM fraction (abstracts)')]
    panel = yearly.merge(liang.rename(columns={'alpha': 'liang_alpha'})[['school', 'year', 'liang_alpha']], on=['school', 'year'], how='left')
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    for ax, (c, title) in zip(axes.ravel(), panels):
        for s in D.SCHOOLS:
            g = panel[panel['school'] == s].sort_values('year')
            ax.plot(g['year'], g[c], marker='o', ms=3, lw=1.2, label=s)
        ax.axvline(2022.9, color='0.6', lw=0.8, ls=':')
        ax.set_title(title, fontsize=9)
    axes[0, 0].legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(fig_dir / 'yearly_ai_amount_by_school.png', dpi=130)
    plt.close(fig)


def run(recalibrate, fig_dir):
    df = DD.paper_table()
    df['field_grp'] = field_groups(df)
    if 'source_type' in df:
        df['venue_type'] = df['source_type'].fillna('unknown').astype(str)
    res = D.RESULTS
    res.mkdir(parents=True, exist_ok=True)
    tabs = {}
    for subset in ('all', 'out_of_sample'):
        tabs[f'school_{subset}'] = pre_table(df, 'school', subset)
        tabs[f'field_{subset}'] = pre_table(df, 'field_grp', subset)
    tabs['abstract_school'] = abstract_pre_table(df, 'school')
    tabs['abstract_field'] = abstract_pre_table(df.assign(field_grp=df['field_grp']), 'field_grp')
    yearly = yearly_table(df)
    tabs['yearly'] = yearly
    tabs['rise'] = rise_table(df)
    liang = pd.read_parquet(res / 'liang_alpha.parquet')
    panel, corr, within = cross_check(yearly, liang[liang['school'] != 'all'])
    tabs['panel'] = panel
    for k, v in tabs.items():
        v.to_parquet(res / f'validation_{k}.parquet', index=False)
    corr.to_csv(res / 'validation_corr_panel.csv'); within.to_csv(res / 'validation_corr_within_school.csv')
    write_figures(yearly, liang[liang['school'] != 'all'], fig_dir)
    sb = tabs['school_out_of_sample']; fb = tabs['field_out_of_sample']
    bad_s, bad_f = sorted(sb.loc[sb['well_above'], 'school']), sorted(fb.loc[fb['well_above'], 'field_grp'])
    D.log(schools_well_above=bad_s, fields_well_above=bad_f)
    if recalibrate:
        psg = DD.passages(set(df.loc[df['ai_share'].notna(), 'paper_id']))
        thr = group_thresholds(df, psg, bad_s, bad_f)
        df['ai_share_cal'] = recalibrated_share(df, psg, thr)
        local = D.local_tmp() / f'ai_scores-val-{os.getpid()}.sqlite'
        import shutil
        shutil.copyfile(D.DB, local)
        db = sqlite3.connect(local)
        db.executemany('update papers set ai_share_cal = ? where paper_id = ?', [(None if pd.isna(v) else float(v), k) for k, v in zip(df['paper_id'], df['ai_share_cal'])])
        db.execute("delete from thresholds where name = 'paragraph_v2_group'")
        db.executemany('insert into thresholds values (?,?,?,?)', [('paragraph_v2_group', f'{k[0]}:{k[1]}', v, '99th percentile of the group\'s out-of-sample 2016-2021 passages') for k, v in thr.items()])
        db.commit(); db.close()
        D.publish(local, D.DB)
        D.log(recalibrated=len(thr), groups={f'{k[0]}:{k[1]}': v for k, v in thr.items()})
    md = ['## Validation tables (generated by dose_validate.py)\n']
    for k in ('school_all', 'school_out_of_sample', 'field_out_of_sample', 'abstract_school', 'abstract_field'):
        t = tabs[k]
        pct = ('flagged', 'mean_ai_share', 'ai_any', 'share_ge25')
        cols = [c for c in t.columns if c not in ('subset',)]
        md += [f'\n### {k}\n', M.md_table(t[cols], pct=pct, ci=[('flagged', 'lo', 'hi'), ('mean_ai_share', 'mean_lo', 'mean_hi')] if 'mean_lo' in t.columns else [('flagged', 'lo', 'hi')])]
    (res / 'validation.md').write_text('\n'.join(md))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--recalibrate', action='store_true')
    ap.add_argument('--fig-dir', default=str(D.AIW / 'diversity' / 'reports' / 'figures-ai-dose'))
    a = ap.parse_args()
    from pathlib import Path
    run(a.recalibrate, Path(a.fig_dir))
