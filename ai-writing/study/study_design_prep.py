"""Inputs shared by the three design layers (study_design_panel.py, study_design_exposure.py, study_design_revision.py): PI-level tables from the sealed snapshot.

  study_design_prep.py oa-scan --id ID [--task I --of N]   Slurm array task: scan the local OpenAlex bulk snapshot (external/openalex-snapshot/current) for the panel's works and keep
                                                          each work's authors with the country codes of their affiliation institutions (no names are read or stored beyond the OpenAlex
                                                          author id). Sequential rowid ranges, ids matched before any body is decompressed. Resumable: a finished part is skipped.
  study_design_prep.py build --id ID                       paper x PI table (outcomes, distance to the school centroid), PI-year within-lab distance, PI exposures (style, language)

writes  <results>/designs/work/{oa_scan/part-*.parquet, design_papers.parquet, pi_year_mpd.parquet, pi_exposure.parquet, prep_report.json}
The sealed snapshot carries author ids but no affiliations, so the language exposure reads OpenAlex affiliations from the bulk snapshot it was built from (snapshot date and
coverage are recorded in prep_report.json). The style exposure reads the detector-v3 passage scores of the pre-period papers: the v3 container (the store papers_v3.parquet was built
from) and the snapshot's delta scores. Nothing here uses personal names: the language exposure is the share of a paper's authors whose affiliation institutions sit in countries
outside ANGLO (an institution-country fact, not an inference about any person's language or origin).
"""
import argparse
import json
import re
import sqlite3
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

import study_common as C

OA_DIR = Path(C.P.EXTERNAL) / 'openalex-snapshot' / 'current'
# first hit wins: the main store (the seven original charters), then the extension stores of the partial schools
OA_DBS = ['openalex.sqlite', 'ext-harvard.sqlite', 'ext-jhu.sqlite', 'ext-washu.sqlite']
SPLITS = {'openalex.sqlite': 10, 'ext-harvard.sqlite': 2, 'ext-jhu.sqlite': 2, 'ext-washu.sqlite': 2}
ANGLO = {'US', 'GB', 'CA', 'AU', 'NZ', 'IE'}                                    # primary: countries whose national language of science is English
ANGLO_WIDE = ANGLO | {'SG', 'IN', 'HK', 'ZA', 'PH', 'NG', 'KE', 'GH'}           # sensitivity: adds countries where English is an official working language
MIN_PRE_PAPERS = 3
HEADLINE_MODEL = C.HEADLINE_MODEL
WINDOWS = {'pre': (2016, 2022), 'pre19': (2016, 2019)}                          # actual exposure window; placebo window (fake break at 2020)
_ID = re.compile(r'W\d+$')


def tasks():
    out = []
    for db in OA_DBS:
        for i in range(SPLITS[db]):
            out.append((db, i, SPLITS[db]))
    return out


def work_dir(snap_id):
    d = C.results_dir(snap_id) / 'designs' / 'work'
    d.mkdir(parents=True, exist_ok=True)
    return d


def parse_authors(body):
    """[(author id, [country codes])] of one OpenAlex work record (zlib JSON)."""
    d = json.loads(zlib.decompress(body))
    out = []
    for a in d.get('authorships') or []:
        aid = (a.get('author') or {}).get('id')
        ccs = sorted({i.get('country_code') for i in a.get('institutions') or [] if i.get('country_code')})
        out.append((aid.rsplit('/', 1)[-1] if aid else None, ccs))
    return out


def oa_scan(snap_id, task):
    work = work_dir(snap_id)
    (work / 'oa_scan').mkdir(exist_ok=True)
    db_name, part, of = tasks()[task]
    dst = work / 'oa_scan' / f'part-{task:02d}.parquet'
    if dst.exists():
        print('exists', dst)
        return
    pan = pd.read_parquet(C.results_dir(snap_id) / 'work' / 'panel.parquet', columns=['k'])
    want = {f'https://openalex.org/{k}': k for k in pan['k'] if isinstance(k, str) and _ID.match(k)}
    db = sqlite3.connect(f'file:{OA_DIR / db_name}?mode=ro', uri=True, timeout=600)
    lo, hi = db.execute('select min(rowid), max(rowid) from works').fetchone()
    step = (hi - lo + 1) // of + 1
    a, b = lo + part * step, lo + (part + 1) * step
    rows, seen, t0 = [], 0, time.time()
    for rid, wid in db.execute('select rowid, id from works where rowid >= ? and rowid < ?', (a, b)):
        seen += 1
        k = want.get(wid)
        if k is None:
            continue
        body = db.execute('select body from works where rowid = ?', (rid,)).fetchone()[0]
        rows.append((k, db_name, json.dumps(parse_authors(body))))
    db.close()
    tmp = dst.with_name('.tmp-' + dst.name)
    pd.DataFrame(rows, columns=['k', 'db', 'authors']).to_parquet(tmp, index=False)
    tmp.replace(dst)
    print(json.dumps(dict(task=task, db=db_name, rows_scanned=seen, matched=len(rows), minutes=round((time.time() - t0) / 60, 1))), flush=True)


def country_table(snap_id):
    """k -> authors with country codes (first store in OA_DBS order wins)."""
    parts = sorted((work_dir(snap_id) / 'oa_scan').glob('part-*.parquet'))
    if len(parts) < len(tasks()):
        raise SystemExit(f'oa-scan incomplete: {len(parts)} of {len(tasks())} parts')
    d = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    d['rank'] = d['db'].map({n: i for i, n in enumerate(OA_DBS)})
    return d.sort_values('rank').drop_duplicates('k')[['k', 'db', 'authors']]


def paper_language(ct):
    """Per paper: authors with any affiliation country, and how many of them have no affiliation in ANGLO / ANGLO_WIDE (an institution-country fact only)."""
    rows = []
    for k, js in zip(ct['k'], ct['authors']):
        au = json.loads(js)
        known = [(aid, ccs) for aid, ccs in au if ccs]
        rows.append((k, len(au), len(known), sum(1 for _, c in known if not set(c) & ANGLO), sum(1 for _, c in known if not set(c) & ANGLO_WIDE)))
    return pd.DataFrame(rows, columns=['k', 'n_authors', 'n_known', 'n_nonang', 'n_nonang_wide'])


def style_scores(snap, pan):
    """Per paper mean detector-v3 z over its main-body passages that are not abstained (words >= 100); NaN when unscored. The v3 container, then the snapshot's delta scores."""
    out = {}
    cpath = Path(C.P.AI_WRITING) / 'data' / 'ai-scores-v3' / 'ai_scores.sqlite'
    pa = pd.read_parquet(snap / 'ai' / 'paper_ai_v3.parquet', columns=['paper_id', 'n_main'])
    nmain = dict(zip(pa['paper_id'], pa['n_main']))
    want = set(pan.loc[pan['paper_id'].notna() & ~pan['trained_on_v3'] & pan['year'].le(2022) & pan['has_ft'], 'paper_id'])
    db = sqlite3.connect(f'file:{cpath}?mode=ro', uri=True, timeout=600)
    for pid, pidx, words, z in db.execute('select paper_id, pidx, words, p from passages'):
        if pid in want and words >= 100 and pidx < (nmain.get(pid) or 0):
            s = out.setdefault(pid, [0.0, 0])
            s[0] += z
            s[1] += 1
    db.close()
    dp = snap / 'delta' / 'scores_passages.sqlite'
    if dp.exists():
        db = sqlite3.connect(f'file:{dp}?mode=ro', uri=True)
        acc = {}
        for pid, z in db.execute("select paper_id, z from scores where section = 'main' and abstain = 0"):
            if pid in want:
                s = acc.setdefault(pid, [0.0, 0])
                s[0] += z
                s[1] += 1
        db.close()
        for pid, s in acc.items():       # the delta rescored some papers: its scores replace the container's
            out[pid] = s
    return pd.Series({p: s[0] / s[1] for p, s in out.items() if s[1] >= 5}, name='z_mean')


def distances(snap, pan, dp):
    """Paper-level distance to the leave-PI-out school-year centroid, and PI-year within-lab mean pairwise distance (SPECTER2 proximity, centred unit vectors)."""
    import study_analyze as A
    rows, X = A.load_emb(snap, HEADLINE_MODEL, pan['paper_id'].to_numpy())
    pe = pan.iloc[rows][['k']].reset_index(drop=True).assign(r=np.arange(len(rows)))
    d = dp.merge(pe, on='k', how='inner').drop_duplicates(['pi_key', 'k'])
    # school-year sums over unique (school, paper)
    sk = d.drop_duplicates(['school', 'k'])
    D = X.shape[1]
    key_sy = sk['school'] + '|' + sk['year'].astype(str)
    codes_sy, uniq_sy = pd.factorize(key_sy)
    S_sy = np.zeros((len(uniq_sy), D), np.float64)
    np.add.at(S_sy, codes_sy, X[sk['r'].to_numpy()])
    n_sy = np.bincount(codes_sy, minlength=len(uniq_sy)).astype(float)
    sy_index = dict(zip(uniq_sy, range(len(uniq_sy))))
    key_py = d['pi_key'] + '|' + d['year'].astype(str)
    codes_py, uniq_py = pd.factorize(key_py)
    S_py = np.zeros((len(uniq_py), D), np.float64)
    np.add.at(S_py, codes_py, X[d['r'].to_numpy()])
    n_py = np.bincount(codes_py, minlength=len(uniq_py)).astype(float)
    first = pd.Series(np.arange(len(d))).groupby(codes_py).first().to_numpy()
    sy_of_py = np.array([sy_index[d['school'].iloc[i] + '|' + str(d['year'].iloc[i])] for i in first])
    # leave-PI-out centroid per (pi, year); the PI's own papers are removed from the school sum (a co-owned paper stays in the school once, so it is removed only via its PI's rows)
    Cn = S_sy[sy_of_py] - S_py
    Nn = n_sy[sy_of_py] - n_py
    ok = Nn >= 20
    norm = np.linalg.norm(Cn, axis=1)
    Cu = Cn / np.where(norm > 0, norm, 1.0)[:, None]
    cos = np.einsum('ij,ij->i', X[d['r'].to_numpy()], Cu[codes_py])
    d['dist_centroid'] = np.where(ok[codes_py], 1.0 - cos, np.nan)
    # PI-year within-lab mean pairwise distance, cells of >= 5 papers
    g = n_py >= 5
    mpd = 1.0 - ((S_py ** 2).sum(1) - n_py) / np.where(n_py > 1, n_py * (n_py - 1), np.nan)
    pm = pd.DataFrame({'pi_key': [u.rsplit('|', 1)[0] for u in uniq_py], 'year': [int(u.rsplit('|', 1)[1]) for u in uniq_py],
                       'n': n_py, 'mpd': mpd})[g]
    pm['school'] = pm['pi_key'].str.split('|').str[0]
    return d[['k', 'pi_key', 'dist_centroid']], pm


def build(snap_id):
    snap = C.snapshot_dir(snap_id)
    res = C.results_dir(snap_id)
    work = work_dir(snap_id)
    pan = pd.read_parquet(res / 'work' / 'panel.parquet')
    lp = pd.read_parquet(res / 'work' / 'lab_papers.parquet')
    lp = lp.assign(pi_key=lp['school'] + '|' + lp['pi'])
    dp = lp.drop_duplicates(['pi_key', 'k'])[['k', 'pi_key', 'school', 'lab_id', 'year', 'period_supported']]
    cols = ['k', 'paper_id', 'flag_abstract', 'kobak_abs', 'ai_share_main', 'ai_share_main_appendix', 'trained_on_v3', 'has_ft', 'has_abs', 'in_universe', 'w_ft', 'topic_sub']
    dp = dp.merge(pan[cols], on='k', how='left')
    dp['heavy_main'] = np.where(dp['ai_share_main'].notna() & ~dp['trained_on_v3'].fillna(False).astype(bool), (dp['ai_share_main'] >= 0.25).astype(float), np.nan)
    dp['heavy_main_appendix'] = np.where(dp['ai_share_main_appendix'].notna() & ~dp['trained_on_v3'].fillna(False).astype(bool), (dp['ai_share_main_appendix'] >= 0.25).astype(float), np.nan)
    dp['abs_flag'] = np.where(dp['trained_on_v3'].fillna(False).astype(bool), np.nan, dp['flag_abstract'].astype(float))
    pre_sub = dp[dp['year'] <= 2022].dropna(subset=['topic_sub']).groupby('pi_key')['topic_sub'].agg(lambda x: x.value_counts().index[0])
    top = dp.drop_duplicates('pi_key')['pi_key'].map(pre_sub).value_counts().index[:12]
    dp['pi_sub'] = dp['pi_key'].map(pre_sub).where(dp['pi_key'].map(pre_sub).isin(top), 'other').fillna('other')      # the PI's modal pre-2023 OpenAlex subfield (12 largest, else other)
    dp['half'] = dp['k'].map(lambda s: int(zlib.crc32(s.encode()) % 2))      # deterministic split-half of papers (cross-fitting of the style exposure)
    dist, pm = distances(snap, pan, dp)
    dp = dp.merge(dist, on=['k', 'pi_key'], how='left')
    ct = country_table(snap_id)
    lang = paper_language(ct)
    dp = dp.merge(lang, on='k', how='left').merge(ct[['k', 'authors']], on='k', how='left')
    z = style_scores(snap, pan)
    dp['style_z'] = dp['paper_id'].map(z)
    # PI exposure: mean over the PI's papers in the window (all papers, or split half 0 only: the cross-fit exposure)
    exp = []
    for wname, (y0, y1) in WINDOWS.items():
        for split in ('all', 'half0'):
            q = dp[dp['year'].between(y0, y1)]
            if split == 'half0':
                q = q[q['half'] == 0]
            g = q.groupby('pi_key')
            e = pd.DataFrame({'n_papers': g.size(),
                              'n_style': g['style_z'].count(), 'style_z': g['style_z'].mean(),
                              'n_kobak': g['kobak_abs'].count(), 'kobak_abs': g['kobak_abs'].mean(),
                              'n_lang': g['n_known'].apply(lambda s: int((s > 0).sum()))})
            qq = q[q['n_known'] > 0]
            gg = qq.groupby('pi_key')
            e['lang_share'] = gg['n_nonang'].sum() / gg['n_known'].sum()                    # author-weighted pooled share over the PI's papers
            e['lang_share_paper'] = (qq['n_nonang'] / qq['n_known']).groupby(qq['pi_key']).mean()   # mean of the per-paper shares
            e['lang_share_wide'] = gg['n_nonang_wide'].sum() / gg['n_known'].sum()
            e['lang_share_team'] = unique_team(qq)
            e['window'], e['split'] = wname, split
            exp.append(e.reset_index())
    exp = pd.concat(exp, ignore_index=True)
    exp['school'] = exp['pi_key'].str.split('|').str[0]
    dp.drop(columns=['authors']).to_parquet(work / 'design_papers.parquet', index=False)
    pm.to_parquet(work / 'pi_year_mpd.parquet', index=False)
    exp.to_parquet(work / 'pi_exposure.parquet', index=False)
    manifest = json.loads((OA_DIR / 'manifest.json').read_text()) if (OA_DIR / 'manifest.json').exists() else {}
    cov = dp.assign(has_oa=dp['n_authors'].notna(), has_aff=dp['n_known'].fillna(0) > 0).groupby('year')[['has_oa', 'has_aff']].mean()
    rep = dict(papers=int(len(dp)), pis=int(dp['pi_key'].nunique()), oa_snapshot_date=manifest.get('snapshot_date'), oa_dbs=OA_DBS,
               anglo=sorted(ANGLO), anglo_wide=sorted(ANGLO_WIDE), coverage_by_year=cov.round(4).to_dict(orient='index'),
               pis_with_style_exposure=int(exp[(exp.window == 'pre') & (exp.split == 'all') & (exp.n_style >= MIN_PRE_PAPERS)].shape[0]),
               pis_with_language_exposure=int(exp[(exp.window == 'pre') & (exp.split == 'all') & (exp.n_lang >= MIN_PRE_PAPERS)].shape[0]),
               note='language exposure = share of authors with no affiliation institution in ANGLO; an institution-country fact, never inferred from names')
    (work / 'prep_report.json').write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({k: v for k, v in rep.items() if k != 'coverage_by_year'}, default=str))


def unique_team(q):
    """Per PI: share of distinct co-authors (the most frequent author, the PI, removed) whose affiliation countries on the PI's papers are mostly outside ANGLO."""
    votes = {}
    for pk, js in zip(q['pi_key'], q['authors']):
        if not isinstance(js, str):
            continue
        for aid, ccs in json.loads(js):
            if aid and ccs:
                v = votes.setdefault(pk, {}).setdefault(aid, [0, 0])
                v[0] += 1
                v[1] += int(not set(ccs) & ANGLO)
    out = {}
    for pk, m in votes.items():
        if len(m) < 2:
            continue
        top = max(m, key=lambda a: m[a][0])
        rest = [v for a, v in m.items() if a != top]
        out[pk] = float(np.mean([v[1] / v[0] > 0.5 for v in rest]))
    return pd.Series(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['oa-scan', 'build', 'ntasks'])
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('--task', type=int)
    a = ap.parse_args()
    if a.cmd == 'ntasks':
        print(len(tasks()))
    elif a.cmd == 'oa-scan':
        import os
        t = a.task if a.task is not None else int(os.environ['SLURM_ARRAY_TASK_ID'])
        oa_scan(a.id, t)
    else:
        build(a.id)


if __name__ == '__main__':
    main()
