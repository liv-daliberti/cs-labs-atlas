"""Assemble ai-writing/diversity/reports/AI-DOSE-NOVELTY-DIVERSITY.md and its figures from the result tables (no numbers are typed by hand).

  dose_report.py [--out DIR]
reads  AI_SCORES/results/{validation_*.parquet, validation.md, liang_*.parquet, paper_*.parquet, did_*.parquet, mech_*.parquet, precision_check_*.json}
       and ai-writing/dose/report_summary.md (the plain-language summary, written once the tables exist)
Every section is skipped, with a one-line note, when its tables are missing.
"""
import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

import dcommon as D
import dose_md as M

SC = {'beta': 'effect of ai_share 0 -> 1'}
HEAD = dict(scope='all', k=3, measure='nov_nn_cap')


def read_all(prefix):
    fs = sorted(glob.glob(str(D.RESULTS / f'{prefix}_*.parquet')))
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True) if fs else None


def mech_delta(mech, model, kind, scope, k, measure='nov_nn_cap'):
    """The mechanical shift of a fully AI-worded text (content kept: polish for abstracts, polish + paraphrase passages averaged for the full-text additive move)."""
    if mech is None:
        return np.nan
    src = {'abstract': ('abstract', 'polish'), 'fulltext': ('fulltext_add', 'mean-shift')}[kind]
    m = mech[(mech['model'] == model) & (mech['kind'] == src[0]) & (mech['task'] == src[1]) & (mech['gen'] == 'all') & (mech['scope'] == scope) & (mech['k'] == k) & (mech['measure'] == measure)]
    return float(m['delta'].iloc[0]) if len(m) else np.nan


def dose_tables(paper, mech):
    out = []
    p = paper[(paper['exposure'] == 'ai_share') & (paper['scope'] == HEAD['scope']) & (paper['k'] == HEAD['k']) & (paper['measure'] == HEAD['measure'])]
    for kind in ('abstract', 'fulltext'):
        for period in ('post', 'pre'):
            q = p[(p['kind'] == kind) & (p['period'] == period)]
            if q.empty:
                continue
            t = q.pivot_table(index='model', columns='design', values='beta')
            lo = q.pivot_table(index='model', columns='design', values='lo')
            hi = q.pivot_table(index='model', columns='design', values='hi')
            rows = []
            for mdl in t.index:
                r = dict(model=mdl)
                for d in ('raw', 'pooled', 'topicyear', 'nollm', 'withinlab', 'author'):
                    if d in t.columns:
                        r[d] = f'{t.loc[mdl, d]:+.4f} [{lo.loc[mdl, d]:+.4f}, {hi.loc[mdl, d]:+.4f}]'
                if period == 'post':
                    dm = mech_delta(mech, mdl, kind, HEAD['scope'], HEAD['k'])
                    r['mechanical shift (AI wording alone)'] = f'{dm:+.4f}' if np.isfinite(dm) else 'n/a'
                    if np.isfinite(dm) and 'pooled' in t.columns:
                        r['pooled minus mechanical'] = f'{t.loc[mdl, "pooled"] - dm:+.4f}'
                rows.append(r)
            out.append((f'{kind} vectors, {period}-period papers' + (' (placebo: the dose is detector noise)' if period == 'pre' else ''), pd.DataFrame(rows)))
    return out


def correction_table(paper, mech):
    """Dose coefficients without and with the mechanical-shift correction (abstract vectors, scope all, k=3, nov_nn_cap, post-period).
    corrected = beta - delta, delta = the novelty shift of a fully AI-polished abstract (polish rewrites); its interval adds the two standard errors in quadrature."""
    if mech is None or paper is None:
        return None
    rows = []
    for expo, label in (('flag_abstract', 'abstract flagged AI (0/1)'), ('ai_share', 'ai_share 0 -> 1 (assumes the abstract is as AI-worded as the body)')):
        for design in ('pooled', 'withinlab'):
            for m in sorted(paper['model'].unique()):
                q = paper[(paper['model'] == m) & (paper['kind'] == 'abstract') & (paper['scope'] == 'all') & (paper['k'] == 3) & (paper['measure'] == 'nov_nn_cap')
                          & (paper['exposure'] == expo) & (paper['design'] == design) & (paper['period'] == 'post')]
                mm = mech[(mech['model'] == m) & (mech['kind'] == 'abstract') & (mech['task'] == 'polish') & (mech['gen'] == 'all') & (mech['scope'] == 'all') & (mech['k'] == 3)
                          & (mech['measure'] == 'nov_nn_cap')]
                if q.empty or mm.empty:
                    continue
                b, se = float(q['beta'].iloc[0]), float((q['hi'].iloc[0] - q['lo'].iloc[0]) / 3.92)
                d, dse = float(mm['delta'].iloc[0]), float((mm['hi'].iloc[0] - mm['lo'].iloc[0]) / 3.92)
                c, cse = b - d, float(np.hypot(se, dse))
                rows.append(dict(exposure=label, design=design, model=m, raw=f'{b:+.4f} [{b - 1.96 * se:+.4f}, {b + 1.96 * se:+.4f}]', mechanical=f'{d:+.4f}',
                                 corrected=f'{c:+.4f} [{c - 1.96 * cse:+.4f}, {c + 1.96 * cse:+.4f}]'))
    return pd.DataFrame(rows)


def figures(paper, did, fig):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig.mkdir(parents=True, exist_ok=True)
    if paper is not None:
        q = paper[(paper['kind'] == 'abstract') & (paper['scope'] == 'all') & (paper['k'] == 3) & (paper['measure'] == 'nov_nn_cap') & (paper['exposure'] == 'ai_share') & (paper['period'] == 'post')]
        models = sorted(q['model'].unique())
        if models:
            f, ax = plt.subplots(2, 4, figsize=(13, 6), sharex=True)
            for a, m in zip(ax.ravel(), models):
                b = q[(q['model'] == m) & q['design'].str.startswith('bin ')]
                x = np.arange(len(b)) + 1
                a.errorbar(x, b['beta'], yerr=[b['beta'] - b['lo'], b['hi'] - b['beta']], fmt='o-', ms=3, capsize=2)
                a.axhline(0, color='0.6', lw=0.7); a.set_title(m, fontsize=8)
                a.set_xticks(x); a.set_xticklabels(b['design'].str.replace('bin ', ''), fontsize=7)
            f.suptitle('Novelty (size-matched, k=3, all papers) by ai_share bin, relative to 0-5% (2023-2025; year, school, topic FE and controls)', fontsize=9)
            f.tight_layout(); f.savefig(fig / 'dose_bins_by_model.png', dpi=120); plt.close(f)
        w = paper[(paper['kind'] == 'abstract') & (paper['scope'] == 'all') & (paper['k'] == 3) & (paper['measure'] == 'nov_nn_cap') & (paper['exposure'] == 'ai_share') & paper['design'].isin(['pooled', 'withinlab'])]
        if len(w):
            f, ax = plt.subplots(figsize=(8, 5))
            ys = []
            for i, (m, d, per) in enumerate(sorted({(r.model, r.design, r.period) for r in w.itertuples()})):
                r = w[(w['model'] == m) & (w['design'] == d) & (w['period'] == per)].iloc[0]
                ax.errorbar(r['beta'], i, xerr=[[r['beta'] - r['lo']], [r['hi'] - r['beta']]], fmt='o' if per == 'post' else 's', ms=3, color='C0' if per == 'post' else 'C1')
                ys.append(f'{m} {d} {per}')
            ax.set_yticks(range(len(ys))); ax.set_yticklabels(ys, fontsize=5); ax.axvline(0, color='0.5', lw=0.7)
            ax.set_title('Dose coefficient on novelty: post (blue) and placebo pre-period (orange)', fontsize=9)
            f.tight_layout(); f.savefig(fig / 'dose_forest.png', dpi=130); plt.close(f)
    if did is not None:
        e = did[(did['spec'] == 'event') & (did['dose'] == 'dose') & (did['outcome'].isin(['mpd', 'nov_all']))]
        if len(e):
            f, ax = plt.subplots(1, 2, figsize=(11, 4))
            for a, y in zip(ax, ['mpd', 'nov_all']):
                for m, g in e[e['outcome'] == y].groupby('model'):
                    g = g.sort_values('year'); a.plot(g['year'], g['beta'], marker='o', ms=3, label=m)
                a.axhline(0, color='0.6', lw=0.7); a.axvline(2022, color='0.6', ls=':'); a.set_title(f'{y}: event-study coefficient on lab AI dose (base 2021)', fontsize=8)
            ax[0].legend(fontsize=5); f.tight_layout(); f.savefig(fig / 'event_study.png', dpi=130); plt.close(f)


def build(out_dir):
    out_dir = Path(out_dir)
    fig = out_dir / 'figures-ai-dose'
    res = D.RESULTS
    paper, did, mech = read_all('paper'), read_all('did'), read_all('mech')
    figures(paper, did, fig)
    L = ['# AI amount in papers, and novelty and diversity (the dose question)\n', f'Generated {D.now()} by `ai-writing/dose/dose_report.py`; all numbers come from the tables in `ai-writing/data/ai-scores/results`.\n']
    sm = Path(__file__).parent / 'report_summary.md'
    L.append(sm.read_text() if sm.exists() else '## Summary\n\n(The plain-language summary is written once the tables exist.)\n')
    L.append('\n## 1. Detector validation\n')
    v = res / 'validation.md'
    L.append(v.read_text() if v.exists() else 'Not run yet.\n')
    for name, title in (('rise', 'Where the 2016-2021 rise sits (flagged share, 2016-17 against 2020-21)'), ('yearly', 'Yearly flagged share and mean ai_share per school')):
        p = res / f'validation_{name}.parquet'
        if p.exists():
            t = pd.read_parquet(p)
            L.append(f'\n### {title}\n\n' + M.md_table(t, pct=tuple(c for c in t.columns if t[c].dtype.kind == 'f' and t[c].abs().max() <= 1.0)))
    L.append('\n![yearly](figures-ai-dose/yearly_ai_amount_by_school.png)\n')
    for f, title in (('validation_corr_panel.csv', 'Correlation of the four "amount of AI" measures over school-years'), ('validation_corr_within_school.csv', 'The same within school (school means removed)')):
        p = res / f
        if p.exists():
            L.append(f'\n### {title}\n\n' + M.md_table(pd.read_csv(p, index_col=0).reset_index().rename(columns={'index': ''}), floatfmt='{:.2f}'))
    p = res / 'liang_calibration.parquet'
    if p.exists():
        L.append('\n### Liang et al. estimator on synthetic mixtures\n\n' + M.md_table(pd.read_parquet(p)))
    for f in sorted(glob.glob(str(res / 'precision_check_*.json'))):
        L.append(f'\n### fp16 against bf16: {Path(f).name}\n\n```\n{Path(f).read_text()}\n```\n')
    L.append('\n## 2. Mechanical shift from AI wording\n')
    if mech is not None:
        t = mech[(mech['measure'].isin(['cos', 'nov_nn_cap'])) & (mech['scope'].isin(['-', 'all'])) & (mech['k'].isin([0, 3])) & (mech['gen'] == 'all')]
        L.append(M.md_table(t[['model', 'kind', 'task', 'measure', 'delta', 'lo', 'hi', 'n']].round(4).assign(delta=lambda x: x['delta'])))
    else:
        L.append('Not run yet.\n')
    L.append('\n## 3. Dose and novelty (paper level)\n')
    if paper is not None:
        for title, t in dose_tables(paper, mech):
            L.append(f'\n### {title}\n\nscope all, k=3, nov_nn_cap; effect of ai_share going 0 -> 1, 95% interval (cluster-robust over labs)\n\n' + M.md_table(t))
        L.append('\n![bins](figures-ai-dose/dose_bins_by_model.png)\n\n![forest](figures-ai-dose/dose_forest.png)\n')
        paper.to_csv(res / 'paper_all_fits.csv', index=False)
    else:
        L.append('Not run yet.\n')
    ct = correction_table(paper, mech)
    if ct is not None and len(ct):
        L.append('\n### Dose effect on abstract novelty with and without the mechanical-shift correction\n\nscope all, k=3, nov_nn_cap, 2023-2025 papers; mechanical = shift of a fully AI-polished abstract (same content), measured from rewrites\n\n' + M.md_table(ct))
    bt = read_all('boot')
    if bt is not None:
        L.append('\n### Headline effects with cluster-bootstrap intervals over labs (ai_share 0 -> 1, nov_nn_cap, k=3)\n\n' + M.md_table(
            bt.assign(est=lambda x: x['beta'].round(4), lo_=lambda x: x['lo'].round(4), hi_=lambda x: x['hi'].round(4))[['model', 'scope', 'period', 'design', 'est', 'lo_', 'hi_', 'n']], floatfmt='{:+.4f}'))
    L.append('\n## 4. Lab level (difference-in-differences, placebos, event study)\n')
    if did is not None:
        t = did[did['spec'].isin(['did', 'placebo2019', 'placebo2020', 'placebo2021', 'within_lab_year']) & (did['dose'].isin(['dose', 'ai_share_lt']))]
        t = t.pivot_table(index=['model', 'outcome'], columns='spec', values='beta').reset_index()
        L.append(M.md_table(t, floatfmt='{:+.3f}') + '\n![event](figures-ai-dose/event_study.png)\n')
        did.to_csv(res / 'did_all_fits.csv', index=False)
    else:
        L.append('Not run yet.\n')
    L.append('\n## Method notes\n\nSee `ai-writing/dose/README.md` and the module docstrings (dose_analysis.py, dose_lab.py, dose_mechanical.py, dose_validate.py).\n')
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'AI-DOSE-NOVELTY-DIVERSITY.md').write_text('\n'.join(L))
    D.log(report=str(out_dir / 'AI-DOSE-NOVELTY-DIVERSITY.md'), json=json.dumps(dict(paper=paper is not None, did=did is not None, mech=mech is not None)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(D.AIW / 'diversity' / 'reports'))
    build(ap.parse_args().out)
