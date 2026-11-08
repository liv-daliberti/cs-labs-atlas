"""Seal the field-300 snapshot studies/homogenization/snapshots/field300-2026-11-08 (same conventions as the 12-school snapshots: MANIFEST.json with sha256, rows and
how each file got there, SEALED, snapshot.json, README.md, every file read-only; `verify` re-hashes).

  field300_snapshot.py build   assemble: corpus (hard links, one copy on disk), papers/paper_inst/institutions/refs tables, roster + map TSVs, detector scores (one parquet),
                               embeddings (one fp16 npz per model: sorted OpenAlex work ids + vectors; the resumable parts are removed afterwards with --drop-parts)
  field300_snapshot.py seal    hash, MANIFEST.json, README.md, SEALED, read-only
  field300_snapshot.py verify  re-hash against MANIFEST.json
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

import field300_common as F
import field300_corpus as K


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def rows_of(p):
    p = Path(p)
    try:
        if p.suffix == '.parquet':
            import pyarrow.parquet as pq
            return pq.ParquetFile(p).metadata.num_rows
        if p.suffix == '.tsv':
            return sum(1 for _ in open(p)) - 1
        if p.suffix == '.npz':
            with np.load(p) as z:
                return int(len(z['ids']))
    except Exception:  # noqa: BLE001
        return None
    return None


def link(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.unlink(missing_ok=True)
    try:
        os.link(src, dst)
        return 'hardlink'
    except OSError:
        shutil.copyfile(src, dst)
        return 'copy'


def merge_embeddings(model, dst, drop_parts):
    import field300_analyze as A
    ids, X = A.load_vectors(model)
    tmp = dst.with_name('.tmp-' + dst.name)
    np.savez(open(tmp, 'wb'), ids=ids, X=X)
    tmp.replace(dst)
    if drop_parts:
        shutil.rmtree(F.work_dir() / 'emb' / 'parts' / model / 'abstract')
    return len(ids)


def build(a):
    w, snap = F.work_dir(), F.snapshot_dir()
    snap.mkdir(parents=True, exist_ok=True)
    files = []

    def add(group, src, rel, how=None):
        dst = snap / rel
        h = how or link(src, dst)
        files.append(dict(group=group, path=rel, source=str(src), how=h, bytes=dst.stat().st_size))

    for f in sorted((w / 'corpus').glob('*.parquet')) + sorted((w / 'corpus').glob('*.csv')):
        add('corpus', f, f'corpus/{f.name}')
    for n in ('papers', 'paper_inst', 'institutions'):
        add('tables', w / f'{n}.parquet', f'tables/{n}.parquet')
    for f in sorted((w / 'refs').glob('*.parquet')):
        add('refs', f, f'refs/{f.name}')
    cd = F.cohort_dir()
    for n in ('gras-2025-cse-roster.tsv', 'gras-2025-cse-openalex-map.tsv'):
        dst = snap / 'cohort' / n
        dst.parent.mkdir(exist_ok=True)
        shutil.copyfile(cd / n, dst)
        files.append(dict(group='cohort', path=f'cohort/{n}', source=str(cd / n), how='copy', bytes=dst.stat().st_size))
    parts = sorted((w / 'ai' / 'parts' / 'abstract').glob('f300-*.parquet'))
    if parts:
        df = pd.concat([pd.read_parquet(f) for f in parts]).drop_duplicates('paper_id')
        dst = snap / 'ai' / 'abstract_scores.parquet'
        dst.parent.mkdir(exist_ok=True)
        df.to_parquet(dst, index=False)
        files.append(dict(group='ai', path='ai/abstract_scores.parquet', source=str(w / 'ai'), how='merged', bytes=dst.stat().st_size))
    for m in a.models.split(','):
        if (w / 'emb' / 'parts' / m / 'abstract').exists():
            dst = snap / 'embeddings' / m / 'abstract.npz'
            dst.parent.mkdir(parents=True, exist_ok=True)
            merge_embeddings(m, dst, a.drop_parts)
            files.append(dict(group='embeddings', path=f'embeddings/{m}/abstract.npz', source=str(w / 'emb'), how='merged', bytes=dst.stat().st_size))
    sm = w / 'sameness' / 'mentions_abstract.parquet'
    if sm.exists():
        add('sameness', sm, 'sameness/mentions_abstract.parquet')
    code = subprocess.run(['git', '-C', str(Path(__file__).resolve().parent), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    (snap / 'snapshot.json').write_text(json.dumps(dict(id=F.ID, built=now(), openalex_snapshot=K.DATE, analysis_code_commit=code, files=files), indent=1))
    print(json.dumps(dict(files=len(files), bytes=sum(f['bytes'] for f in files))))


def seal(a):
    snap = F.snapshot_dir()
    meta = json.loads((snap / 'snapshot.json').read_text())
    for f in meta['files']:
        p = snap / f['path']
        f['sha256'] = sha(p)
        f['rows'] = rows_of(p)
    sealed = now()
    man = dict(snapshot=F.ID, sealed=sealed, openalex_snapshot=meta['openalex_snapshot'], analysis_code_commit=meta['analysis_code_commit'], files=meta['files'])
    for n in ('MANIFEST.json', 'README.md', 'SEALED'):
        if (snap / n).exists():
            (snap / n).chmod(0o644)
    (snap / 'MANIFEST.json').write_text(json.dumps(man, indent=1))
    by = {}
    for f in meta['files']:
        g = by.setdefault(f['group'], [0, 0])
        g[0] += 1
        g[1] += f['bytes']
    tab = '\n'.join(f'| {g} | {n} | {b / 2**20:.1f} |' for g, (n, b) in sorted(by.items()))
    (snap / 'README.md').write_text(f"""# Field-300 snapshot {F.ID}

Sealed {sealed}. Immutable: every file is read-only and listed with its sha256 in `MANIFEST.json` (`field300_snapshot.py verify` re-hashes them).
Built from the public OpenAlex bulk snapshot {meta['openalex_snapshot']} (streamed, no API credits) by `ai-writing/study/field300_corpus.py`; analysis code commit {meta['analysis_code_commit'][:10]}.

## What is in
- **corpus/** one parquet per publication year 2016-2025: every work of type article, conference paper, preprint, review or book chapter with at least one authorship at one of the 300
  GRAS 2025 Computer Science & Engineering universities (main OpenAlex institution id plus the related ids of the GRAS map, matched through the institution lineage) that is computer
  science: OpenAlex primary topic in the field Computer Science, or primary source one of the 548 reviewed CS venues. Columns: OpenAlex work id, year, title, abstract (rebuilt from the inverted
  index), topics, source, institutions (cohort index 0-299 and authorships per institution), countries, reference list, counts. `counts_by_year.csv` is the size table.
- **tables/** papers (flags: English abstract of >= 50 words, LLM-topic regex, journal), paper x institution (full and fractional weights), institutions (rank, tier, country, region, size quartile).
- **refs/** reference lists by year (papers with a list), **sameness/** dictionary hits in title + abstract, **cohort/** the roster and OpenAlex map this was built from.
- **ai/** abstract detector scores (v1 `p_v1`, v2 `p_v2`); the abstract flag is `p_v1 >= thr_abstract` of the 12-school snapshot 2026-11-08.
- **embeddings/** one fp16 vector per scored abstract (sorted OpenAlex work ids), models as in the 12-school study.

## Attribution
A paper counts in every cohort institution on its byline (full counting); `w_frac` in `tables/paper_inst.parquet` gives the fractional weights used in the sensitivity.

| group | files | MiB |
|---|---|---|
{tab}

2026 works are not in the corpus (window 2016-2025).
""")
    (snap / 'SEALED').write_text(sealed + '\n')
    for p in snap.rglob('*'):
        if p.is_file():
            p.chmod(0o444)
    print(json.dumps(dict(sealed=F.ID, files=len(meta['files']))))


def verify(a):
    snap = F.snapshot_dir()
    man = json.loads((snap / 'MANIFEST.json').read_text())
    bad = [f['path'] for f in man['files'] if sha(snap / f['path']) != f['sha256']]
    print(json.dumps(dict(checked=len(man['files']), changed=bad)))
    raise SystemExit(1 if bad else 0)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'seal', 'verify'])
    ap.add_argument('--models', default='specter2_proximity,scincl')
    ap.add_argument('--drop-parts', action='store_true')
    a = ap.parse_args()
    {'build': build, 'seal': seal, 'verify': verify}[a.cmd](a)
