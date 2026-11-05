"""How the preservation filter's kept and dropped papers differ (the filter is not random): by home school, year and OpenAlex field.

  kept_dropped.py  -> EMB/allai/results/kept_dropped.json
Population: papers with an ok polish rewrite (112,187). dropped = the filter's verdict (flags_polish.parquet `keep` = 0). Shares are of papers dropped in each group;
`vs_overall` is the group's dropped share minus the overall dropped share. Also the mean source length and the share of abstracts with numbers / named methods.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
import ecommon as C  # noqa: E402
import emb_load as L  # noqa: E402

ALLAI = C.EMB / 'allai'


def table(df, col):
    g = df.groupby(col).agg(papers=('paper_id', 'size'), dropped=('dropped', 'mean')).reset_index()
    g['vs_overall'] = g['dropped'] - df['dropped'].mean()
    return [dict(group=str(r[col]), papers=int(r.papers), dropped_share=round(float(r.dropped), 4), vs_overall=round(float(r.vs_overall), 4)) for r in g.itertuples()] if False else \
        [dict(group=str(getattr(r, col)), papers=int(r.papers), dropped_share=round(float(r.dropped), 4), vs_overall=round(float(r.vs_overall), 4)) for r in g.itertuples()]


def main():
    fl = pd.read_parquet(ALLAI / 'flags_polish.parquet')
    fl = fl[fl['ok'] == 1].assign(dropped=lambda d: 1 - d['keep'])
    papers, _ = L.universe()
    papers = papers[papers['year'] <= 2025]   # 2026 is a partial year
    papers = L.oa_topics(papers)
    df = fl.merge(papers[['paper_id', 'year', 'home_school', 'oa_field']], on='paper_id', how='inner')
    tx = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    words = pd.DataFrame(tx.execute('select paper_id, words from abstracts').fetchall(), columns=['paper_id', 'src_words'])
    tx.close()
    df = df.merge(words, on='paper_id', how='left')
    df['has_numbers'] = df['n_num'] > 0; df['has_terms'] = df['n_term'] > 0
    df['period'] = (df['year'] >= 2023).map({True: 'post (2023-2025)', False: 'pre (2016-2022)'})
    out = dict(papers=int(len(df)), dropped_share=float(df['dropped'].mean()),
               by_school=table(df, 'home_school'), by_year=table(df.dropna(subset=['year']).assign(year=lambda d: d['year'].astype(int)), 'year'),
               by_period=table(df, 'period'),
               by_field=sorted([r for r in table(df.dropna(subset=['oa_field']), 'oa_field') if r['papers'] >= 500], key=lambda r: -r['dropped_share']),
               by_content={k: dict(papers=int(g.shape[0]), dropped_share=round(float(g['dropped'].mean()), 4)) for k, g in
                           (('has numbers', df[df['has_numbers']]), ('no numbers', df[~df['has_numbers']]), ('has named methods', df[df['has_terms']]), ('no named methods', df[~df['has_terms']]))},
               source_words=dict(dropped=float(df[df['dropped'] == 1]['src_words'].mean()), kept=float(df[df['dropped'] == 0]['src_words'].mean())))
    (ALLAI / 'results').mkdir(exist_ok=True)
    (ALLAI / 'results' / 'kept_dropped.json').write_text(json.dumps(out, indent=1))
    C.log(done='kept_dropped', dropped=out['dropped_share'])


if __name__ == '__main__':
    main()
