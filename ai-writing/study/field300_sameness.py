"""Field-300 non-text sameness: the 12-school measures (sameness_refs.py, sameness_bench.py) with institutions as the labs. Reuses their estimators unchanged.

  field300_sameness.py prep                    work/sameness/{lab_papers,papers_refs}.parquet and the mentions table (dictionary hits in title + abstract)
  field300_sameness.py overlap|concentration --sample refs10|journal [--groups ALL,tier,english]
  field300_sameness.py bench [--groups ...]
Mapping: lab = institution (site_id), the 12-school 'school' = institution too, so every pair of distinct institutions is an 'across' pair; scopes are the
institution groups named by --groups (ALL; tier:*, english:*, region:*, size:*). Pairs that share a paper in the year are dropped (as for labs of two schools).
Primary sample = journal papers with >= 10 references (OpenAlex lists of repository papers vanish from 2022); refs10 (any paper with >= 10 references) is secondary.
"""
import argparse
import multiprocessing as mp
import time

import numpy as np
import pandas as pd

import field300_common as F
import sameness_bench as SB
import sameness_common as SM
import sameness_dictionary as D
import sameness_refs as SR
import study_labstats as LS

B = 400


def sdir():
    d = F.work_dir() / 'sameness'
    d.mkdir(parents=True, exist_ok=True)
    return d


def tab_dir():
    d = F.results_dir() / 'tables'
    d.mkdir(parents=True, exist_ok=True)
    return d


def group_scopes(inst, groups):
    """[(scope name, [site ids])] for the requested groupings: ALL plus the groups of tier, english, region, size."""
    out = []
    for g in groups:
        if g == 'ALL':
            out.append(('ALL', list(inst['site_id'])))
        else:
            col = {'tier': 'tier', 'english': 'english', 'region': 'region', 'size': 'size_q'}[g]
            for v, x in inst.groupby(col):
                out.append((f'{g}:{v}', list(x['site_id'])))
    return out


def _mentions(path):
    m = D.Matcher()
    df = pd.read_parquet(path, columns=['work', 'title', 'abstract', 'lang'])
    df = df[df['abstract'].str.split().str.len().fillna(0) >= 10]
    rows = []
    for w, t, ab in zip(df['work'], df['title'], df['abstract']):
        for i, n in m.counts(f'{t or ""}. {ab}').items():
            rows.append((int(w), i, n))
    return pd.DataFrame(rows, columns=['k', 'e', 'n'])


def cmd_prep(a):
    w = F.work_dir()
    o = sdir()
    inst = pd.read_parquet(w / 'institutions.parquet').sort_values('idx')
    pi = pd.read_parquet(w / 'paper_inst.parquet', columns=['work', 'inst', 'year'])
    lp = pd.DataFrame(dict(k=pi['work'].to_numpy(), lab_id=inst['site_id'].to_numpy()[pi['inst'].to_numpy()], school=inst['site_id'].to_numpy()[pi['inst'].to_numpy()],
                           year=pi['year'].to_numpy().astype(int)))
    lp.to_parquet(o / 'lab_papers.parquet', index=False)
    pap = pd.read_parquet(w / 'papers.parquet', columns=['work', 'year', 'n_refs', 'journal', 'abs_ok', 'has_abs10'])
    parts = []
    for f in sorted((w / 'refs').glob('year=*.parquet')):
        r = pd.read_parquet(f, columns=['work', 'refs', 'n_refs'])
        r = r[r['n_refs'] >= 10]
        parts.append(r)
    r = pd.concat(parts, ignore_index=True).merge(pap[['work', 'journal']], on='work')
    r['source_type'] = np.where(r['journal'], 'journal', 'other')
    r.rename(columns={'work': 'k'})[['k', 'source_type', 'n_refs', 'refs']].to_parquet(o / 'papers_refs.parquet', index=False)
    files = sorted((w / 'corpus').glob('year=*.parquet'))
    with mp.Pool(min(a.j, len(files))) as pool:
        mt = pd.concat(pool.map(_mentions, files), ignore_index=True)
    mt.to_parquet(o / 'mentions_abstract.parquet', index=False)
    print(dict(lab_papers=len(lp), papers_with_refs=len(r), mentions=len(mt)), flush=True)


def load(groups):
    w = F.work_dir()
    inst = pd.read_parquet(w / 'institutions.parquet').sort_values('idx').reset_index(drop=True)
    lp = pd.read_parquet(sdir() / 'lab_papers.parquet')
    labs = np.sort(inst['site_id'].to_numpy())
    tier = inst.set_index('site_id').loc[labs, 'tier'].to_numpy()
    W = LS.weights(tier, B, 20261108)
    scopes = group_scopes(inst, groups)
    SM.scope_schools = lambda: iter(scopes)           # the sameness modules iterate SC.scope_schools()
    SR.ACROSS_SCOPES = tuple(s for s, _ in scopes)
    return inst, lp, labs, W


def cmd_refs(a):
    inst, lp, labs, W = load(a.groups.split(','))
    p = pd.read_parquet(sdir() / 'papers_refs.parquet').rename(columns={'k': 'k'})
    t0 = time.time()
    if a.cmd == 'overlap':
        s, c, dg = SR.run_overlap(lp, p, a.sample, labs, labs, W, tab_dir())
        dg.to_csv(tab_dir() / f'f300_overlap_diag_{a.sample}.csv', index=False)
    else:
        s, c = SR.run_concentration(lp, p, a.sample, labs, labs, W, tab_dir())
    tag = f'{a.cmd}_{a.sample}_{a.groups.replace(",", "-")}'
    s.to_csv(tab_dir() / f'f300_{tag}_series.csv', index=False)
    c.to_csv(tab_dir() / f'f300_{tag}_contrasts.csv', index=False)
    print(a.cmd, a.sample, len(c), round(time.time() - t0), 's', flush=True)


def cmd_bench(a):
    inst, lp, labs, W = load(a.groups.split(','))
    m = D.Matcher()
    mt = pd.read_parquet(sdir() / 'mentions_abstract.parquet')
    pan = pd.read_parquet(F.work_dir() / 'papers.parquet', columns=['work', 'has_abs10', 'abs_ok']).rename(columns={'work': 'k'})
    pan['has_abs'] = pan['has_abs10']
    pan['topic_field'] = 'Computer Science'
    rng = np.random.default_rng(SM.SEED + 9)
    s, c = SB.analyze_sample('abstract', lp, pan, mt, W, labs, np.array(m.kinds), rng)
    tag = a.groups.replace(',', '-')
    s.to_csv(tab_dir() / f'f300_bench_{tag}_series.csv', index=False)
    c.to_csv(tab_dir() / f'f300_bench_{tag}_contrasts.csv', index=False)
    pd.DataFrame({'entry': m.names, 'kind': m.kinds, 'papers': mt.groupby('e')['k'].nunique().reindex(range(len(m.names))).fillna(0).astype(int).to_numpy()}).to_csv(
        tab_dir() / 'f300_bench_dictionary_coverage.csv', index=False)
    print('bench', len(c), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['prep', 'overlap', 'concentration', 'bench'])
    ap.add_argument('--sample', default='journal', choices=['refs10', 'journal'])
    ap.add_argument('--groups', default='ALL,tier,english')
    ap.add_argument('-j', type=int, default=16)
    a = ap.parse_args()
    {'prep': cmd_prep, 'bench': cmd_bench}.get(a.cmd, cmd_refs)(a)


if __name__ == '__main__':
    main()
