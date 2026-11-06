"""Which stored passages of a paper are MAIN-BODY passages (provisional section tags for lab_ai_score.py).

  lab_ai_main_tags.py targets                          choose the papers (all 2025 and 2019 papers with a scored full text, plus a seeded sample of
                                                       the other 2016-2021 years for the false-alarm floor) -> AI_SCORES/results/lab_ai/targets.parquet
  lab_ai_main_tags.py run --shard I --nshards N        split each target copy into main / references / appendix with fulltext_sections.py (branch
                                                       agent/fulltext-sections), cut the main text into passages with the detector's own splitter and
                                                       match them to the stored passage list of the paper by text
                                                       -> AI_SCORES/results/lab_ai/tags-<i>.parquet
Output columns: paper_id, error, main_words, n_old (stored passages), n_main (main passages by the splitter), n_matched (main passages that have a
stored score), main_pidx (comma-separated stored pidx that are main passages), appendix_found, appendix_position, refs_found, truncated.
Stored scores of a main passage that the splitter re-cut (a passage that straddled the old boundary) do not exist: they are counted in n_main, not
in n_matched. When the full run of the splitter lands (ai-writing/sections/sections.sqlite) its tags replace this file: lab_ai_score.py reads any
parquet with these columns (config `sections.tags`).
"""
import argparse
import os
import random
import sqlite3
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

import dcommon as D

OUT = D.RESULTS / 'lab_ai'
FLOOR_PER_YEAR = 1000
SEED = 20261105


def trained_ids(papers):
    """Universe paper ids whose passages were detector-v2 TRAINING negatives: a paper of one of the five original schools whose old key
    f'{school}:{work}' falls in the train split (dose_data.split_of_old_keys reads a field, atlasWorkId, that the package rows no longer carry, so
    it returns nothing; the join here goes through the OpenAlex id). A paper listed by several schools counts as trained when any key is."""
    import gzip
    import json
    import v2common as V
    import dose_data as DD
    oa = {(u or '').rsplit('/', 1)[-1]: p for p, u in zip(papers['paper_id'], papers['oa']) if u}
    out = set()
    for s in DD.ORIGINAL:
        with gzip.open(D.P.data('lab_papers.jsonl.gz', s), 'rt') as f:
            for line in f:
                r = json.loads(line)
                pid = oa.get((r.get('oa') or '').rsplit('/', 1)[-1])
                if pid and r.get('work') and V.split_of(f"{s}:{r['work']}") == 'train':
                    out.add(pid)
    return out


def targets():
    import dose_data as DD
    OUT.mkdir(parents=True, exist_ok=True)
    papers, _ = DD.universe()
    sc = DD.scores()[['paper_id', 'n_passages']]
    df = papers.merge(sc, on='paper_id')
    df = df[df['n_passages'].fillna(0) > 0]
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True)
    ft = pd.read_sql('select paper_id, path, kind from fulltext where usable = 1', db)
    db.close()
    df = df.merge(ft, on='paper_id')
    train = trained_ids(papers)
    df['trained_on'] = [(y <= 2021) and p in train for p, y in zip(df['paper_id'], df['year'])]
    rnd = random.Random(SEED)
    keep = set(df.loc[df['year'].isin([2019, 2025]), 'paper_id'])
    for y in (2016, 2017, 2018, 2020, 2021):
        ids = sorted(df.loc[(df['year'] == y) & ~df['trained_on'], 'paper_id'])
        rnd.shuffle(ids)
        keep |= set(ids[:FLOOR_PER_YEAR])
    out = df[df['paper_id'].isin(keep)][['paper_id', 'year', 'home_school', 'path', 'kind', 'trained_on', 'n_passages']].reset_index(drop=True)
    out.to_parquet(OUT / 'targets.parquet', index=False)
    D.log(stage='targets', papers=len(out), by_year=out['year'].value_counts().sort_index().to_dict(), trained_on=int(out['trained_on'].sum()))


def from_sections():
    """Final tags: the full run of the splitter (AI_SCORES/../sections/sections.sqlite, ai-writing/sections/SCHEMA.md) for the target papers.
    Main passages = passage_tags(src='ai_scores', section='main') (they join to ai_scores.sqlite.passages(paper_id, pidx)); unknown, appendix and
    references are left out. -> OUT/tags-final.parquet with the columns of the provisional files."""
    t = pd.read_parquet(OUT / 'targets.parquet')
    ids = set(t['paper_id'])
    db = sqlite3.connect(f"file:{D.SCORES.parent / 'sections' / 'sections.sqlite'}?mode=ro", uri=True, timeout=600)
    sec = pd.read_sql('select paper_id, main_words, split_error, appendix_found, appendix_position, truncated, n_main_passages, n_old_passages from sections', db)
    sec = sec[sec['paper_id'].isin(ids)]
    pt = pd.read_sql("select id as paper_id, pidx from passage_tags where src = 'ai_scores' and section = 'main'", db)
    db.close()
    pt = pt[pt['paper_id'].isin(ids)]
    main = pt.groupby('paper_id')['pidx'].agg(lambda x: ','.join(map(str, sorted(x))))
    sec['main_pidx'] = sec['paper_id'].map(main).fillna('')
    sec['error'] = sec['split_error']
    sec['n_main'] = sec['n_main_passages']
    sec['n_old'] = sec['n_old_passages']
    sec['n_matched'] = [len(x.split(',')) if x else 0 for x in sec['main_pidx']]
    sec['refs_found'] = None
    sec = sec.drop(columns=['split_error', 'n_main_passages', 'n_old_passages'])
    sec.to_parquet(OUT / 'tags-final.parquet', index=False)
    D.log(stage='from_sections', targets=len(ids), tagged=len(sec), with_main=int((sec['main_pidx'] != '').sum()), errors=int(sec['error'].notna().sum()))


def one(job):
    paper_id, path, kind, body_z = job
    import fulltext_sections as S
    import v2common as V
    base = dict(paper_id=paper_id, error=None, main_words=None, n_old=None, n_main=None, n_matched=None, main_pidx='',
                appendix_found=None, appendix_position=None, refs_found=None, truncated=None)
    res = S.split_file(D.P.STORES / path, kind)
    if 'error' in res:
        return {**base, 'error': res['error']}
    old = V.passages(zlib.decompress(body_z).decode('utf-8', 'ignore'))
    where = {}
    for i, t in enumerate(old):
        where.setdefault(t, i)
    new = V.passages(res['main'])
    hit = sorted({where[t] for t in new if t in where})
    f = res['flags']
    return {**base, 'main_words': len(res['main'].split()), 'n_old': len(old), 'n_main': len(new), 'n_matched': len(hit),
            'main_pidx': ','.join(map(str, hit)), 'appendix_found': f.get('appendix_found'), 'appendix_position': f.get('appendix_position'),
            'refs_found': f.get('refs_found'), 'truncated': f.get('truncated')}


def run(shard, nshards, tag):
    t = pd.read_parquet(OUT / 'targets.parquet')
    t = t.sort_values('paper_id').reset_index(drop=True)
    t = t[t.index % nshards == shard]
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    jobs = []
    for r in t.itertuples():
        row = db.execute('select body from fulltext where paper_id = ?', (r.paper_id,)).fetchone()
        if row and row[0]:
            jobs.append((r.paper_id, r.path, r.kind, row[0]))
    db.close()
    D.log(stage='run', shard=shard, papers=len(jobs))
    rows = []
    with ProcessPoolExecutor(int(os.environ.get('SLURM_CPUS_PER_TASK', 4))) as ex:
        for i, r in enumerate(ex.map(one, jobs, chunksize=4)):
            rows.append(r)
            if i % 500 == 0:
                D.log(stage='progress', shard=shard, done=i)
    df = pd.DataFrame(rows)
    loc = D.local_tmp() / f'tags-{tag}-{shard}.parquet'
    df.to_parquet(loc, index=False)
    D.publish(loc, OUT / f'tags-{tag}-{shard}.parquet')
    D.log(stage='done', shard=shard, papers=len(df), errors=df['error'].value_counts().to_dict())


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['targets', 'run', 'from-sections'])
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--tag', default='v1')
    a = ap.parse_args()
    sys.path.insert(0, os.environ.get('AIW_SECTIONS_DIR', str(D.AIW)))
    {'targets': targets, 'from-sections': from_sections}.get(a.cmd, lambda: run(a.shard, a.nshards, a.tag))()
