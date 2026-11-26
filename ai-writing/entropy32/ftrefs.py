"""Citation age from the papers' own reference lists (owner 2026-11-23: "citation age needs more papers per school").

OpenAlex has a dated reference list for only ~60% of the 2023-2025 full texts (its repository/preprint reference lists thin out after 2022), so
citeage.py leaves the rest out. Every paper we hold has its reference section, so this reads it from the stored copy (fulltext_sections.split_file,
the same splitter as the main/appendix split) and takes the cited works' years from the text:
  years   every 4-digit year 1950..(paper year + 1) in the reference section after removing URLs, DOIs, arXiv identifiers (2012.01234 is not a
          year), ISBN/ISSN and page-like digit runs; a year repeated inside one reference (venue "2018 IEEE ... 2018") counts as often as it appears,
          which barely moves a mean over a reference list
  age     paper year - cited year, negatives (a cited preprint dated later) as 0; per paper: mean, median, share <= 2 years, number of years found
stages (WORK/ftrefs/)  shard I [--dir NAME]  -> refs-<dir>-<i>.parquet   (CPU array over the e32 shards of the base and every delta round)
                       merge                 -> ftrefs.parquet (k, ft_n_years, ft_cite_age_mean, ft_cite_age_median, ft_recent2, refs_chars)
                       check                 -> agreement with the OpenAlex citation age on the papers both have (check.json)
"""
import argparse
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import e32  # noqa: E402

STRIP = [re.compile(p, re.I) for p in (r'https?://\S+', r'\bwww\.\S+', r'\bdoi:?\s*10\.\S+', r'\b10\.\d{4,9}/\S+', r'arxiv:?\s*\d{4}\.\d{4,5}(v\d+)?',
                                       r'\b\d{4}\.\d{4,5}(v\d+)?\b', r'\bISBN[:\s]*[\d\-xX ]{10,20}', r'\bISSN[:\s]*\d{4}-\d{3}[\dxX]', r'\d{5,}')]
YEAR = re.compile(r'(?<![\d.])((?:19[5-9]|20[0-3])\d)(?![\d])')


def years_of(text, paper_year):
    for p in STRIP:
        text = p.sub(' ', text)
    ys = [int(y) for y in YEAR.findall(text)]
    return [y for y in ys if 1950 <= y <= paper_year + 1]


def one(job):
    import fulltext_sections as S
    k, path, kind, year = job
    try:
        r = S.split_file(e32.P.STORES / path, kind)
    except Exception as e:  # noqa: BLE001
        return dict(k=k, err=f'{type(e).__name__}'[:80])
    if r.get('error'):
        return dict(k=k, err=str(r['error'])[:80])
    t = r.get('references') or ''
    ys = years_of(t, int(year))
    age = np.clip(int(year) - np.array(ys, dtype=int), 0, None) if ys else np.array([])
    return dict(k=k, refs_chars=len(t), ft_n_years=len(ys), ft_cite_age_mean=float(age.mean()) if len(age) else np.nan,
                ft_cite_age_median=float(np.median(age)) if len(age) else np.nan, ft_recent2=float((age <= 2).mean()) if len(age) else np.nan)


def out_dir(a):
    d = e32.work_dir(a.id) / 'ftrefs'
    d.mkdir(exist_ok=True)
    return d


def cmd_shard(a):
    import pandas as pd
    dirs = {d.name: d for d in e32.run_dirs(a.id)}
    d = dirs[a.dir] if a.dir else e32.work_dir(a.id)
    dst = out_dir(a) / f'refs-{d.name}-{a.i}.parquet'
    if dst.exists():
        print(json.dumps(dict(skip=str(dst)))); return
    n = json.loads((d / 'RUN.json').read_text())['nshards']
    P = pd.read_parquet(d / 'papers.parquet', columns=['k', 'path', 'kind', 'year', 'shard'])
    P = P[(P['shard'] == a.i % n) & P.path.notna()]
    with ProcessPoolExecutor(a.j) as ex:
        rows = list(ex.map(one, [(r.k, r.path, r.kind, r.year) for r in P.itertuples()], chunksize=4))
    tmp = dst.with_name('.tmp-' + dst.name)
    pd.DataFrame(rows).to_parquet(tmp, index=False); tmp.replace(dst)
    df = pd.DataFrame(rows)
    print(json.dumps(dict(shard=a.i, papers=len(df), with_years=int((df.get('ft_n_years', pd.Series(dtype=float)) > 0).sum()))))


def cmd_merge(a):
    import pandas as pd
    fs = sorted(out_dir(a).glob('refs-*.parquet'))
    df = pd.concat([pd.read_parquet(f) for f in fs]).drop_duplicates('k', keep='last')
    df.to_parquet(out_dir(a) / 'ftrefs.parquet', index=False)
    print(json.dumps(dict(files=len(fs), papers=len(df), with_years=int((df.ft_n_years >= 5).sum()))))


def cmd_check(a):
    import pandas as pd
    W = e32.work_dir(a.id)
    f = pd.read_parquet(out_dir(a) / 'ftrefs.parquet')
    c = pd.read_parquet(W / 'citeage' / 'citeage.parquet', columns=['k', 'cite_age_mean', 'n_refs_dated'])
    m = f.merge(c, on='k').dropna(subset=['ft_cite_age_mean', 'cite_age_mean'])
    m = m[(m.ft_n_years >= 5) & (m.n_refs_dated >= 5)]
    res = dict(overlap=len(m), pearson=float(np.corrcoef(m.ft_cite_age_mean, m.cite_age_mean)[0, 1]),
               mean_fulltext=float(m.ft_cite_age_mean.mean()), mean_openalex=float(m.cite_age_mean.mean()),
               mean_abs_diff=float((m.ft_cite_age_mean - m.cite_age_mean).abs().mean()),
               ft_only=int(((f.ft_n_years >= 5) & ~f.k.isin(c.loc[c.n_refs_dated >= 5, 'k'])).sum()))
    (out_dir(a) / 'check.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['shard', 'merge', 'check'])
    ap.add_argument('i', type=int, nargs='?', default=0)
    ap.add_argument('--dir', default=None)
    ap.add_argument('--id', default='20261123')
    ap.add_argument('-j', type=int, default=8)
    a = ap.parse_args()
    if a.cmd == 'shard' and a.i is not None and 'SLURM_ARRAY_TASK_ID' in __import__('os').environ:
        a.i = int(__import__('os').environ['SLURM_ARRAY_TASK_ID'])
    globals()['cmd_' + a.cmd](a)


if __name__ == '__main__':
    main()
