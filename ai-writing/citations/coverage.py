"""Coverage of the citation data per citing year x AI group, to print beside every comparison.

Per citing period (2016-2022 base, 2023, 2024, 2025, 2026) and group (flagged = ai_share >= 0.25, not = the rest; also
none / some):
  papers            paragraph-scored lab papers
  oa_list, oa5      share with an OpenAlex reference list (any; >= 5 references, the analysis threshold)
  s2_list, s2_5     the same for Semantic Scholar
  any5              share with >= 5 references in either source
  oa_refs           OpenAlex references of the oa5 papers
  oa_fetched        share of those references whose cited work was fetched (OpenAlex returned it; the rest are deleted or
                    merged ids), pooled over references; oa_fetched_pp = mean of the per-paper share
  s2_refs, s2_year  S2 references of the s2_5 papers; share with a known publication year
Question-3 coverage (OpenAlex references of the oa5 papers to cited works published 2023 or later):
  rec_refs          such references
  rec_v1            share whose cited work has a v1 abstract score (title + >= 50-word OpenAlex abstract)
  rec_v2            share whose cited work has a usable v2 full-text score: an open-full-text sample text (ftsample.py,
                    v2score.py) or a corpus lab paper with a paragraph score (matched on OpenAlex id)
-> results/coverage.csv
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import glob, gzip, json, sqlite3
import numpy as np, pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA, RES = HERE / 'data', HERE / 'results'
CACHE = P.CACHE / 'citations'


def scored_sets():
    v1 = set()
    for f in sorted(CACHE.glob('score_out_*.sqlite')):
        v1 |= {int(i[1:]) for i, in sqlite3.connect(f).execute('select id from scores') if i.startswith('W')}
    v2 = set()
    for f in sorted(glob.glob(str(CACHE / 'v2scores' / 'papers-*.jsonl.gz'))):
        for line in gzip.open(f, 'rt'):
            r = json.loads(line)
            if r['usable'] and r['n_passages']:
                v2.add(int(r['key'][1:]))
    import q2v2
    byw, _ = q2v2.lab_citables(None)
    return v1, v2 | set(byw)


def main():
    C = pd.read_parquet(DATA / 'citing.parquet')
    C['period'] = np.where(C.year <= 2022, '2016-2022', C.year.astype(str))
    C['flag'] = np.where(C.ai_share >= 0.25, 'flagged', 'not')
    C['g3'] = np.where(C.ai_share <= 0, 'none', np.where(C.ai_share < 0.25, 'some', 'flagged'))
    E = pd.read_parquet(DATA / 'edges_oa.parquet')
    W = pd.read_parquet(DATA / 'works_oa.parquet', columns=['wid', 'year'])
    E['fetched'] = E.wid.isin(set(W.wid))
    v1, v2 = scored_sets()
    E['rec'] = E.wid.map(W.set_index('wid').year).fillna(0).values >= 2023
    E['v1'] = E.rec & E.wid.isin(v1); E['v2'] = E.rec & E.wid.isin(v2)
    rq = E.groupby('ci')[['rec', 'v1', 'v2']].sum().reindex(range(len(C)), fill_value=0)
    C['rec_n'], C['rec_v1'], C['rec_v2'] = rq.rec.values, rq.v1.values, rq.v2.values
    pp = E.groupby('ci').fetched.agg(['size', 'sum'])
    C['oa_n'] = pp['size'].reindex(range(len(C)), fill_value=0).values
    C['oa_f'] = pp['sum'].reindex(range(len(C)), fill_value=0).values
    E2 = pd.read_parquet(DATA / 'edges_s2.parquet')
    W2 = pd.read_parquet(DATA / 'works_s2.parquet', columns=['wid', 'year'])
    E2['hasyear'] = W2.set_index('wid').year.reindex(E2.wid.values).notna().values
    p2 = E2.groupby('ci').hasyear.agg(['size', 'sum'])
    C['s2_n'] = p2['size'].reindex(range(len(C)), fill_value=0).values
    C['s2_y'] = p2['sum'].reindex(range(len(C)), fill_value=0).values
    rows = []
    for gcol in ('flag', 'g3'):
        for (per, g), d in C.groupby(['period', gcol]):
            o5 = d[d.oa_n >= 5]; s5 = d[d.s2_n >= 5]
            rows.append(dict(split=gcol, period=per, group=g, papers=len(d), oa_list=(d.oa_n > 0).mean(), oa5=(d.oa_n >= 5).mean(),
                             s2_list=(d.s2_n > 0).mean(), s2_5=(d.s2_n >= 5).mean(), any5=((d.oa_n >= 5) | (d.s2_n >= 5)).mean(),
                             oa_refs=int(o5.oa_n.sum()), oa_fetched=o5.oa_f.sum() / max(o5.oa_n.sum(), 1),
                             oa_fetched_pp=(o5.oa_f / o5.oa_n).mean() if len(o5) else np.nan,
                             s2_refs=int(s5.s2_n.sum()), s2_year=s5.s2_y.sum() / max(s5.s2_n.sum(), 1),
                             rec_refs=int(o5.rec_n.sum()), rec_v1=o5.rec_v1.sum() / max(o5.rec_n.sum(), 1),
                             rec_v2=o5.rec_v2.sum() / max(o5.rec_n.sum(), 1)))
    R = pd.DataFrame(rows)
    R.to_csv(RES / 'coverage.csv', index=False, float_format='%.4f')
    with pd.option_context('display.width', 200, 'display.max_columns', 20):
        print(R[R.split == 'flag'].round(3).to_string(index=False))


if __name__ == '__main__':
    main()
