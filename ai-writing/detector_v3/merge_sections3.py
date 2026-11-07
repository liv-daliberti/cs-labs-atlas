"""Paper-level table of the v3 section rescoring: results/paper_ai_v3.jsonl.gz (+ .parquet).

Reads results/sections-<tag>/scores-*.sqlite (score_sections.py) and the sections containers (sections.sqlite, sections_extra/).
One row per paper_id (the id of embeddings/texts.sqlite / ai_scores.sqlite / the universe; joins to the dose and atlas tables):
  paper_id, key, school (school of the stored copy), home_school, year, oa_id, kind, usable (main body >= 1,000 words), appendix_found, appendix_rule, split_error
  n_main, n_appendix                        passages cut (sections.sqlite `passages`)
  n_main_scored / n_main_abstained / n_main_flagged, n_app_scored / n_app_abstained / n_app_flagged
  n_scored, n_abstained, abstained_share    main + appendix; abstained_share = n_abstained / (n_scored + n_abstained)
  ai_share_main            flagged / scored over main passages (None when nothing was scored)
  ai_share_main_appendix   flagged / scored over main + appendix passages
  split_v3, trained_on_v3  detector-v3 training split of the paper (train / cal / test / None) and True for a 2016-2021 paper in the train split
                           (its passages were negatives in training): by the paper's fulltext key AND by dose_data.split_of_old_keys' OpenAlex-id
                           join (the fix of branch agent/exp-citation-revision, all schools), either one suffices
Abstained passages (under 100 words, or heading/interleaving-heavy; eval3.operating_point) are neither flagged nor scored.
usage: merge_sections3.py [--tag all]
"""
import argparse, glob, gzip, json, sqlite3, sys
from collections import Counter
import pandas as pd
import v3common as C

DOSE = '/n/fs/resemble/homogenizing-science/worktrees/exp-citation-revision/ai-writing/dose'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--tag', default='all'); a = ap.parse_args()
    rd = C.RESULTS / f'sections-{a.tag}'
    agg = {}
    for f in sorted(glob.glob(str(rd / 'scores-*.sqlite'))):
        d = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        for pid, sec, n, ab, fl in d.execute('select paper_id, section, count(*), sum(abstain), sum(flagged) from scores group by paper_id, section'):
            r = agg.setdefault(pid, dict(n_main_scored=0, n_main_abstained=0, n_main_flagged=0, n_app_scored=0, n_app_abstained=0, n_app_flagged=0))
            k = 'main' if sec == 'main' else 'app'
            r[f'n_{k}_scored'] += n - ab; r[f'n_{k}_abstained'] += ab; r[f'n_{k}_flagged'] += fl
        d.close()
    rows = []
    for path in [str(C.AIW / 'data' / 'sections' / 'sections.sqlite')] + sorted(glob.glob(str(C.DATA / 'sections_extra' / 'shard-*.sqlite'))):
        d = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for r in d.execute('select paper_id, key, school, kind, main_words, appendix_found, appendix_rule, split_error, n_main_passages, n_appendix_passages from sections'):
            rows.append(r)
        d.close()
    df = pd.DataFrame(rows, columns=['paper_id', 'key', 'school', 'kind', 'main_words', 'appendix_found', 'appendix_rule', 'split_error', 'n_main', 'n_appendix'])
    df = df.drop_duplicates('paper_id')
    df['usable'] = df['main_words'] >= 1000
    df = df.drop(columns=['main_words'])
    df['appendix_found'] = df['appendix_found'].astype(bool)
    u = sqlite3.connect(f'file:{C.AIW}/data/embeddings/universe.sqlite?mode=ro', uri=True)
    un = pd.read_sql('select paper_id, oa, year, home_school from papers', u)
    un['oa_id'] = un['oa'].fillna('').str.rsplit('/', n=1).str[-1].replace('', None)
    df = df.merge(un.drop(columns=['oa']), on='paper_id', how='left')
    sc = pd.DataFrame.from_dict(agg, orient='index').rename_axis('paper_id').reset_index()
    df = df.merge(sc, on='paper_id', how='left')
    for c in ('n_main_scored', 'n_main_abstained', 'n_main_flagged', 'n_app_scored', 'n_app_abstained', 'n_app_flagged'):
        df[c] = df[c].fillna(0).astype(int)
    df['n_scored'] = df['n_main_scored'] + df['n_app_scored']; df['n_abstained'] = df['n_main_abstained'] + df['n_app_abstained']
    tot = df['n_scored'] + df['n_abstained']
    df['abstained_share'] = (df['n_abstained'] / tot).where(tot > 0)
    df['ai_share_main'] = (df['n_main_flagged'] / df['n_main_scored']).where(df['n_main_scored'] > 0)
    df['ai_share_main_appendix'] = ((df['n_main_flagged'] + df['n_app_flagged']) / df['n_scored']).where(df['n_scored'] > 0)
    # training split: by the paper's fulltext key, and by the OpenAlex-id join of dose_data.split_of_old_keys (all schools)
    df['split_key'] = df['key'].map(lambda k: C.SPLIT_OF(k) if isinstance(k, str) else None)
    sys.path.insert(0, DOSE)
    import dose_data as DD
    DD.ORIGINAL = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech']
    df['split_map'] = df['paper_id'].map(DD.split_of_old_keys())
    df['split_v3'] = df['split_key'].where(df['split_key'].notna(), df['split_map'])
    df['trained_on_v3'] = df['year'].between(2016, 2021) & ((df['split_key'] == 'train') | (df['split_map'] == 'train'))
    df = df.drop(columns=['split_key', 'split_map'])
    out = C.RESULTS
    df.to_parquet(out / 'paper_ai_v3.parquet', index=False)
    with gzip.open(out / 'paper_ai_v3.jsonl.gz', 'wt') as f:
        for r in df.to_dict('records'):
            f.write(json.dumps({k: (None if (isinstance(v, float) and v != v) else v) for k, v in r.items()}, default=str) + '\n')
    cov = df.groupby('school').agg(papers=('paper_id', 'size'), usable=('usable', 'sum'), scored=('n_scored', lambda s: int((s > 0).sum())),
                                   passages=('n_scored', 'sum'), abstained=('n_abstained', 'sum'), trained_on=('trained_on_v3', 'sum')).reset_index()
    cov.to_csv(out / 'coverage_by_school.csv', index=False)
    print(cov.to_string()); print(json.dumps(dict(papers=len(df), scored_papers=int((df['n_scored'] > 0).sum()), passages=int(df['n_scored'].sum()),
                                                  abstained=int(df['n_abstained'].sum()), trained_on=int(df['trained_on_v3'].sum()), split=Counter(map(str, df['split_v3'])))))


if __name__ == '__main__':
    main()
