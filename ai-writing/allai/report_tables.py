"""Markdown tables of ALL-AI-REWRITE.md from the analysis tables.  usage: report_tables.py > tables.md"""
import glob
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
import ecommon as C  # noqa: E402

R = C.EMB / 'allai' / 'results'
MODELS = ['specter2_proximity', 'specter2_base', 'scincl', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']


def ld(prefix, tag='polish'):
    return pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(R / f'{prefix}_{tag}_*.parquet')))], ignore_index=True)


def f(v, d=3):
    return 'n/a' if pd.isna(v) else f'{v:.{d}f}'


def iv(a, lo, hi, d=3):
    return f'{f(a, d)} [{f(lo, d)}, {f(hi, d)}]'


def md(rows, head):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows]) + '\n'


def change_table(g, scope='all', measures=('vendi', 'H_bt', 'H_km', 'dispersion'), d=3):
    rows = []
    for meas in measures:
        for m in MODELS:
            r = g[(g.scope == scope) & (g.scope_id == scope) & (g.measure == meas) & (g.model == m)] if scope == 'all' else g[(g.scope == 'school') & (g.measure == meas) & (g.model == m)]
            if len(r) == 1:
                r = r.iloc[0]
                rows.append([meas, m, iv(r.orig, r.orig_lo, r.orig_hi, d), iv(r.ai, r.ai_lo, r.ai_hi, d), iv(r.gap, r.gap_lo, r.gap_hi, d)])
    return md(rows, ['measure', 'model', 'original post - pre', 'all-AI post - pre', 'gap (orig - AI)'])


def main():
    out = []
    pres = json.load(open(R / 'preservation_polish.json'))
    out.append('### cosine\n' + md([[m, f(v['centred']['mean']), f(v['centred']['p05']), f(v['raw']['mean'], 4), f(v['random_centred']['mean'], 3), f(v['retrieval_at_1'], 4)] for m, v in pres['cosine'].items()],
                                   ['model', 'centred cosine, mean', '5th percentile', 'raw cosine, mean', 'unrelated pair (centred)', 'own rewrite is nearest of 2,000']))
    y = ld('geom_year')
    rows = []
    for meas in ('vendi', 'H_bt', 'H_km'):
        for m in ('specter2_proximity', 'qwen3_0p6b', 'bge_m3'):
            g = y[(y.scope == 'all') & (y.measure == meas) & (y.model == m)].set_index('year')
            if len(g):
                rows.append([meas, m] + [f'{f(g.loc[yr, "orig"], 2)} / {f(g.loc[yr, "ai"], 2)}' for yr in (2016, 2019, 2022, 2024, 2025)])
    out.append('### levels\n' + md(rows, ['measure', 'model', '2016', '2019', '2022', '2024', '2025']))
    chg = ld('geom_change')
    out.append('### change all\n' + change_table(chg))
    labs = ld('geom_labsummary')
    rows = []
    for meas in ('vendi', 'H_bt', 'H_km', 'dispersion'):
        for m in MODELS:
            r = labs[(labs.scope == 'all') & (labs.measure == meas) & (labs.model == m)]
            if len(r):
                r = r.iloc[0]
                rows.append([meas, m, int(r.labs), iv(r.orig_change, r.orig_lo, r.orig_hi), iv(r.ai_change, r.ai_lo, r.ai_hi), iv(r.gap_change, r.gap_lo, r.gap_hi)])
    out.append('### labs\n' + md(rows, ['measure', 'model', 'labs', 'original post - pre', 'all-AI post - pre', 'gap']))
    nc = ld('novelty_contrast')
    rows = []
    for k in (1, 3, 5):
        for m in MODELS:
            r = nc[(nc.scope == 'all') & (nc.k == k) & (nc.measure == 'nov_nn_cap') & (nc.model == m)]
            if len(r):
                r = r.iloc[0]
                rows.append([k, m, iv(r.orig_change, r.orig_lo, r.orig_hi, 4), iv(r.ai_change, r.ai_lo, r.ai_hi, 4), iv(r.gap_change, r.gap_lo, r.gap_hi, 4)])
    out.append('### novelty all\n' + md(rows, ['k', 'model', 'original post - pre', 'all-AI post - pre', 'gap']))
    rows = []
    for sc in ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan']:
        for meas in ('vendi', 'H_bt'):
            r = chg[(chg.scope == 'school') & (chg.scope_id == sc) & (chg.measure == meas) & (chg.model == 'specter2_proximity')]
            if len(r):
                r = r.iloc[0]
                rows.append([sc, meas, iv(r.orig, r.orig_lo, r.orig_hi, 2), iv(r.ai, r.ai_lo, r.ai_hi, 2), iv(r.gap, r.gap_lo, r.gap_hi, 2)])
    out.append('### schools (specter2_proximity)\n' + md(rows, ['school', 'measure', 'original post - pre', 'all-AI post - pre', 'gap']))
    rows = []
    for tag in ('paraphrase', 'polish-sub'):
        try:
            g = ld('geom_change', tag)
        except ValueError:
            continue
        for meas in ('vendi', 'H_bt', 'H_km'):
            for m in ('specter2_proximity', 'qwen3_0p6b', 'nomic_v15'):
                r = g[(g.scope == 'all') & (g.measure == meas) & (g.model == m)]
                if len(r):
                    r = r.iloc[0]
                    rows.append([tag, meas, m, iv(r.orig, r.orig_lo, r.orig_hi, 2), iv(r.ai, r.ai_lo, r.ai_hi, 2), iv(r.gap, r.gap_lo, r.gap_hi, 2)])
    out.append('### robustness\n' + md(rows, ['rewrite', 'measure', 'model', 'original post - pre', 'rewrite post - pre', 'gap']))
    print('\n'.join(out))


if __name__ == '__main__':
    main()
