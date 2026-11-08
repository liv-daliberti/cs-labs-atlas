"""Design 3: within-paper arXiv revision. The detector's flagged share in a lab paper's arXiv v1 against its later (final) version, main body and main body + appendix.

  study_design_revision.py list    --id ID    pairs of the earlier AI-in-revision run (ai-writing/revision, detector v3) that are still in the strict 12-school membership -> work/revision_texts.parquet
  study_design_revision.py analyze --id ID    cell effects with cluster bootstrap intervals -> tables/revision_effects.csv, revision_cells.csv, revision_pairs.csv, revision_checks.json
The pairs, the arXiv texts and the main-body scores are the 11-05 experiment's (revision/README.md, rv_*.py, reused, not recomputed). Only the appendix passages of the arXiv versions are new
(study_design_revision_gpu.py).
Pair kinds (revision/README.md): S = arXiv v1 against the lab paper's stored full text (the stores' copy, dated by publication date); A = arXiv v1 against the latest arXiv version in the public
cloud mirror (dated by its margin stamp). Cells by version dates: pre_pre (both before 1 Dec 2022; the revision-noise and false-positive baseline), pre_post (v1 before, final after: the design's
treated cell), post_post (both after). Contrasts: pre_post - pre_pre, post_post - pre_pre, post_post - pre_post. Placebo: a fake break at 2020-01-01 among the pre_pre pairs (v1 before 2020 and final in
2020-2022, against both before 2020). Intervals: percentile bootstrap over first PIs (clusters), 1,000 draws.
Mirror finding (study_design_revision.py list writes it to revision_checks.json): the bucket lists prior versions (vN objects exist for papers with several versions), but the late revisions of old
papers are missing, so pre_post pairs of kind A are few; kind S carries most of them.
"""
import argparse
import json
import sqlite3

import numpy as np
import pandas as pd

import study_common as C

DATA = C.Path(C.P.AI_WRITING) / 'data' / 'revision'
CELLS = ['pre_pre', 'pre_post', 'post_post']
CONTRASTS = [('pre_post', 'pre_pre'), ('post_post', 'pre_pre'), ('post_post', 'pre_post')]
HEAVY = 0.25
MIN_PASSAGES = 10        # the 11-05 pair filter: at least 10 scored main-body passages in a version


def work_dir(snap_id):
    d = C.results_dir(snap_id) / 'designs' / 'work'
    d.mkdir(parents=True, exist_ok=True)
    return d


def strict_pairs(snap_id):
    """Valid out-of-sample pairs (valid & valid_pre) of papers still in the strict membership, with the first PI of the paper as cluster."""
    p = pd.read_parquet(DATA / 'results' / 'revision_v3_pairs.parquet')
    p = p[p['valid'] & p['valid_pre'] & p['cell'].isin(CELLS)].copy()
    dp = pd.read_parquet(work_dir(snap_id) / 'design_papers.parquet', columns=['paper_id', 'pi_key', 'school', 'ai_share_main', 'ai_share_main_appendix', 'trained_on_v3'])
    first = dp.dropna(subset=['paper_id']).sort_values('pi_key').drop_duplicates('paper_id')
    p = p.drop(columns=['school']).merge(first.rename(columns={'school': 'school_now'}), on='paper_id', how='inner')
    p['school'] = p['school_now']
    return p


def cmd_list(snap_id):
    p = strict_pairs(snap_id)
    rows = [(a, 'v1') for a in p['arxiv_id'].unique()] + [(a, 'final') for a in p.loc[p['kind'] == 'A', 'arxiv_id'].unique()]
    t = pd.DataFrame(rows, columns=['arxiv_id', 'role']).drop_duplicates()
    t.to_parquet(work_dir(snap_id) / 'revision_texts.parquet', index=False)
    db = sqlite3.connect(f'file:{DATA / "revision.sqlite"}?mode=ro', uri=True)
    nv = pd.read_sql('select n_versions, count(*) as arxiv_ids from versions group by 1 order by 1', db)
    lst = pd.read_sql('select max(time_created) as latest_object, min(time_created) as earliest_object, count(*) as objects from version_list', db)
    late = pd.read_sql("select substr(m.created, 1, 4) as v1_year, count(*) as ids, sum(l.n > 1) as ids_with_prior_versions, sum(l.mx >= '2023') as ids_with_object_uploaded_2023_or_later "
                       "from matches m join (select arxiv_id, max(time_created) as mx, count(*) as n from version_list group by 1) l on l.arxiv_id = m.arxiv_id "
                       "where m.created >= '2016' and m.created < '2023' group by 1 order by 1", db)
    db.close()
    v1 = p[p['kind'] == 'A']
    chk = dict(pairs_in_strict_membership=int(len(p)), by_kind_cell=p.groupby(['kind', 'cell']).size().rename('n').reset_index().to_dict(orient='records'), texts_to_score=int(len(t)),
               mirror_version_counts={int(r.n_versions): int(r.arxiv_ids) for r in nv.itertuples() if r.n_versions <= 6},
               mirror_listing=lst.iloc[0].to_dict(), mirror_late_revisions_by_v1_year=late.to_dict(orient='records'), kindA_pre_post=int(((v1['cell'] == 'pre_post')).sum()), kindA_post_post=int(((v1['cell'] == 'post_post')).sum()),
               partial_school_pairs=int(p['school'].isin(C.PARTIAL).sum()))
    (work_dir(snap_id) / 'revision_list_checks.json').write_text(json.dumps(chk, indent=1, default=str))
    print(json.dumps(chk, default=str))


def load_app(snap_id):
    parts = sorted((work_dir(snap_id) / 'revision_app').glob('*.parquet'))
    if not parts:
        raise SystemExit('no appendix parts: run study_design_revision_gpu.py first')
    return pd.concat([pd.read_parquet(f) for f in parts], ignore_index=True).drop_duplicates(['arxiv_id', 'role'], keep='last')


def pair_table(snap_id):
    p = strict_pairs(snap_id)
    app = load_app(snap_id)
    for role, tag in (('v1', '1'), ('final', '2')):
        a = app[app['role'] == role].set_index('arxiv_id')
        for c in ('ok', 'appendix_found', 'n_main_scored', 'n_main_flagged', 'n_app_scored', 'n_app_flagged'):
            p[f'{c}{tag}'] = p['arxiv_id'].map(a[c])
    S = p['kind'] == 'S'
    # one extraction for main and main + appendix (study_design_revision_fetch.py / _gpu.py): v1 and arXiv finals from it, stored finals from the snapshot (the same splitter and scorer)
    ok1 = p['ok1'].fillna(0).eq(1) & (p['n_main_scored1'] >= MIN_PASSAGES)
    ok2 = np.where(S, True, p['ok2'].fillna(0).eq(1) & (p['n_main_scored2'] >= MIN_PASSAGES))
    p['v1_main'] = np.where(ok1, p['n_main_flagged1'] / p['n_main_scored1'].where(p['n_main_scored1'] > 0), np.nan)
    p['v1_both'] = np.where(ok1, (p['n_main_flagged1'] + p['n_app_flagged1']) / (p['n_main_scored1'] + p['n_app_scored1']).where(p['n_main_scored1'] > 0), np.nan)
    fa_main = p['n_main_flagged2'] / p['n_main_scored2'].where(p['n_main_scored2'] > 0)
    fa_both = (p['n_main_flagged2'] + p['n_app_flagged2']) / (p['n_main_scored2'] + p['n_app_scored2']).where(p['n_main_scored2'] > 0)
    p['fin_main'] = np.where(S, p['ai_share_main'], np.where(ok2, fa_main, np.nan))
    p['fin_both'] = np.where(S, p['ai_share_main_appendix'], np.where(ok2, fa_both, np.nan))
    p['v1_main_1105'] = p['ai1']
    p['d_main'] = p['fin_main'] - p['v1_main']
    p['d_both'] = p['fin_both'] - p['v1_both']
    p['d_heavy_main'] = (p['fin_main'] >= HEAVY).astype(float) - (p['v1_main'] >= HEAVY).astype(float)
    p['d_heavy_both'] = (p['fin_both'] >= HEAVY).astype(float) - (p['v1_both'] >= HEAVY).astype(float)
    p.loc[p['fin_main'].isna() | p['v1_main'].isna(), ['d_main', 'd_heavy_main']] = np.nan
    p.loc[p['fin_both'].isna() | p['v1_both'].isna(), ['d_both', 'd_heavy_both']] = np.nan
    # fake-2020 placebo cells among pre_pre pairs
    pp = p['cell'] == 'pre_pre'
    p['cell_fake'] = np.where(pp & (p['d2'] < '2020-01-01'), 'fake_pre', np.where(pp & (p['d1'] < '2020-01-01') & (p['d2'] >= '2020-01-01'), 'fake_cross', None))
    return p


def boot_stats(x, cl, cell, cells, B, seed):
    """Percentile bootstrap over clusters (resampled with replacement) of the cell means."""
    ok = ~np.isnan(x)
    x, cl, cell = x[ok], cl[ok], cell[ok]
    ucl, ci = np.unique(cl, return_inverse=True)
    G = len(ucl)
    ix = [np.where(ci == g)[0] for g in range(G)]
    rng = np.random.default_rng(seed)

    def stats(idx):
        out = {}
        for c in cells:
            m = cell[idx] == c
            out[c] = x[idx][m].mean() if m.any() else np.nan
        return out
    pt = stats(np.arange(len(x)))
    draws = []
    for _ in range(B):
        idx = np.concatenate([ix[g] for g in rng.integers(0, G, G)])
        draws.append(stats(idx))
    n = {c: int((cell == c).sum()) for c in cells}
    return pt, draws, n, G


def cell_effects(p, y, cluster='pi_key', B=1000, seed=7, cells=None, contrasts=None, cell_col='cell'):
    """Cell means and contrasts of y (the change final minus v1) with cluster-bootstrap percentile intervals. p needs columns cell_col, cluster, y."""
    cells = cells or CELLS
    contrasts = contrasts or CONTRASTS
    d = p[[cell_col, cluster, y]].dropna(subset=[cell_col])
    x = d[y].to_numpy(float)
    pt, draws, n, G = boot_stats(x, d[cluster].to_numpy(), d[cell_col].to_numpy(), cells, B, seed)
    rows = []
    for c in cells:
        v = np.array([dr[c] for dr in draws], float)
        rows.append(dict(contrast=f'mean {c}', est=pt[c], lo=np.nanpercentile(v, 2.5), hi=np.nanpercentile(v, 97.5), n_a=n[c], n_b=0, clusters=G))
    for a, b in contrasts:
        v = np.array([dr[a] - dr[b] for dr in draws], float)
        rows.append(dict(contrast=f'{a} - {b}', est=pt[a] - pt[b], lo=np.nanpercentile(v, 2.5), hi=np.nanpercentile(v, 97.5), n_a=n[a], n_b=n[b], clusters=G))
    return pd.DataFrame(rows)


def analyze(snap_id, B=1000):
    p = pair_table(snap_id)
    T = C.results_dir(snap_id) / 'designs' / 'tables'
    T.mkdir(parents=True, exist_ok=True)
    out, cells = [], []
    scopes = [('main', 'd_main', 'd_heavy_main'), ('main_appendix', 'd_both', 'd_heavy_both')]
    for kind in ('A', 'S', 'A+S'):
        pk = p if kind == 'A+S' else p[p['kind'] == kind]
        for sample, q in (('all', pk), ('excl_partial', pk[~pk['school'].isin(C.PARTIAL)]), ('appendix_found', pk[pk['appendix_found1'].fillna(False).astype(bool)]),
                          ('lag_6m_plus', pk[pk['lag_m'] >= 6])):
            for scope, ycol, hcol in scopes:
                for ometric, col in (('flagged_share', ycol), ('heavy_indicator', hcol)):
                    e = cell_effects(q, col, B=B)
                    out.append(e.assign(kind=kind, sample=sample, scope=scope, outcome=ometric, design='real'))
                    f = cell_effects(q, col, B=B, cells=['fake_pre', 'fake_cross'], contrasts=[('fake_cross', 'fake_pre')], cell_col='cell_fake')
                    out.append(f.assign(kind=kind, sample=sample, scope=scope, outcome=ometric, design='fake2020'))
    eff = pd.concat(out, ignore_index=True)
    cl = p.groupby(['kind', 'cell']).agg(n=('arxiv_id', 'size'), v1_main=('v1_main', 'mean'), fin_main=('fin_main', 'mean'), v1_both=('v1_both', 'mean'), fin_both=('fin_both', 'mean'),
                                         lag_m=('lag_m', 'median'), appendix_found_v1=('appendix_found1', 'mean')).reset_index()
    eff.to_csv(T / 'revision_effects.csv', index=False)
    eff.to_parquet(T / 'revision_effects.parquet')
    cl.to_csv(T / 'revision_cells.csv', index=False)
    keep = ['arxiv_id', 'paper_id', 'kind', 'cell', 'school', 'pi_key', 'd1', 'd2', 'lag_m', 'v1_main', 'fin_main', 'v1_both', 'fin_both', 'd_main', 'd_both', 'cell_fake', 'v1_main_1105']
    p[keep].to_parquet(T / 'revision_pairs.parquet')
    # new extraction against the 11-05 main-body scores of the same arXiv versions
    A = p[p['v1_main'].notna() & p['v1_main_1105'].notna()]
    chk = dict(pairs=int(len(p)), pairs_with_new_scores=int(p['v1_main'].notna().sum()),
               v1_main_share_new_vs_1105_corr=float(np.corrcoef(A['v1_main'], A['v1_main_1105'])[0, 1]), v1_main_share_mean_abs_diff=float((A['v1_main'] - A['v1_main_1105']).abs().mean()),
               v1_main_passages_new_vs_1105_equal=float((A['n_main_scored1'] == A['n_pass1']).mean()), v1_main_passages_within2=float(((A['n_main_scored1'] - A['n_pass1']).abs() <= 2).mean()),
               stored_final_main_share_snapshot_vs_1105_mean_abs_diff=float(np.nanmean(np.abs(p.loc[p['kind'] == 'S', 'ai_share_main'] - p.loc[p['kind'] == 'S', 'ai2']))),
               appendix_found_v1=float(p['appendix_found1'].fillna(False).astype(bool).mean()), partial_school_pairs=int(p['school'].isin(C.PARTIAL).sum()))
    (T / 'revision_checks.json').write_text(json.dumps(chk, indent=1))
    print(json.dumps(chk))
    print(eff[(eff['sample'] == 'all') & (eff.outcome == 'flagged_share') & eff.contrast.str.contains(' - ')][['kind', 'scope', 'design', 'contrast', 'est', 'lo', 'hi', 'n_a', 'n_b']].round(4).to_string())
    return eff


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['list', 'analyze'])
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('--boot', type=int, default=1000)
    a = ap.parse_args()
    cmd_list(a.id) if a.cmd == 'list' else analyze(a.id, a.boot)
