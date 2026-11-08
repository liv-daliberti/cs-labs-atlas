"""Freeze an analysis snapshot of the homogenization study (immutable inputs + MANIFEST + README).

usage:  study_snapshot.py plan   [--release latest] [--id 2026-11-07]      what would go in (sizes, no copying)
        study_snapshot.py build  [--release latest] [--id 2026-11-07]      link/copy the files, write snapshot.json (the file list)
        study_snapshot.py seal   --id 2026-11-07 [-j N]                     sha256 + row counts of every file, MANIFEST.json, README.md, read-only
        study_snapshot.py verify --id 2026-11-07                            re-hash and compare with MANIFEST.json

A snapshot is a directory under studies/homogenization/snapshots/<id>/ holding everything the analysis reads, so a later run on
the same id gives the same numbers whatever the live data does. Small tables are COPIED; large containers that the pipeline replaces
atomically (embedding .npz, per-paper score tables) are HARD-LINKED (same file system, no extra disk; the old inode survives a
replace); SQLite databases are copied (they can be rewritten in place); PDFs are never touched. Files too large to be useful here
(per-paragraph section scores, full-text embeddings) are listed in the manifest as `referenced` with their size and mtime only.
"""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import study_common as C

COPY_MAX = 600 * 2 ** 20      # a file up to this size is copied (unless `link` is set); larger ones are hard-linked
CHUNK = 8 * 2 ** 20


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def spec(release_dir, src=None, delta_base=None):
    """The inputs as (group, destination relative to the snapshot, source path, mode); mode: copy | link | ref."""
    src = src or C.sources()
    rel = Path(release_dir)
    out = []
    add = lambda g, d, s, m='auto': out.append((g, d, Path(s), m))  # noqa: E731
    for f in ('MANIFEST.json', 'CHANGES.md'):
        add('release', f'release/{f}', rel / f)
    for s in C.SCHOOLS:
        for f in ('lab_papers.jsonl.gz', 'pis.json', 'report.json', 'students.json', 'student_papers.jsonl.gz', 'copies.json'):
            p = rel / 'hierarchy' / s / f
            if p.exists():
                add('release', f'release/hierarchy/{s}/{f}', p, 'copy')
        p = rel / 'periods' / f'{s}-faculty-periods.json'
        if p.exists():
            add('periods', f'release/periods/{s}-faculty-periods.json', p, 'copy')
    for f in ('school-profiles.json', 'cs-venues.json'):
        if (rel / 'hierarchy' / f).exists():
            add('release', f'release/hierarchy/{f}', rel / 'hierarchy' / f, 'copy')
    for p in sorted((rel / 'ai').rglob('*.json')):
        add('release-ai', f'release/ai/{p.relative_to(rel / "ai")}', p, 'copy')
    # AI scores (detector v3) and the section split
    add('ai', 'ai/papers_v3.parquet', src['ai_scores_v3'] / 'papers.parquet', 'copy')
    add('ai', 'ai/paper_ai_v3.parquet', src['detector_v3'] / 'results' / 'paper_ai_v3.parquet', 'copy')
    for f in ('coverage_by_school.csv', 'operating_point.json', 'tables.md'):
        add('ai', f'ai/detector_v3/{f}', src['detector_v3'] / 'results' / f, 'copy')
    add('ai', 'ai/v3_error_table.json', src['ai_scores_v3'] / 'results' / 'v3_error_table.json', 'copy')
    add('ai', 'ai/v3_yearly_school.parquet', src['ai_scores_v3'] / 'results' / 'v3_yearly_school.parquet', 'copy')
    add('ai', 'ai/liang_alpha.parquet', src['ai_scores_v3'] / 'results' / 'liang_alpha.parquet', 'copy')
    add('sections', 'sections/sections.sqlite', src['sections'] / 'sections.sqlite', 'ref')
    # paper universe, abstracts' topics, OpenAlex extras
    for f in ('universe.sqlite', 'oa_fields.sqlite', 'oa_extra.sqlite'):
        add('universe', f'universe/{f}', src['embeddings'] / f, 'copy')
    add('universe', 'universe/texts.sqlite', src['embeddings'] / 'texts.sqlite', 'ref')
    # embeddings of abstracts, all models, plus topic tables
    for m in C.MODELS:
        for s in C.EMB_SCHOOLS:
            for k in ('abstract.npz', 'abstract.index.sqlite'):
                p = src['embeddings'] / m / s / k
                if p.exists():
                    add('embeddings', f'embeddings/{m}/{s}/{k}', p, 'link' if k.endswith('npz') else 'copy')
            p = src['embeddings'] / m / s / 'fulltext.npz'
            if p.exists():
                add('embeddings-fulltext', f'embeddings/{m}/{s}/fulltext.npz', p, 'ref')
    for m in ('qwen3_0p6b', 'specter2_proximity'):
        for f in (f'topics_{m}.parquet', f'topic_labels_{m}.parquet'):
            add('topics', f'topics/{f}', src['embeddings'] / 'results' / f, 'copy')
    # citation novelty, lab study (IPW weights, event study), carry-over reports
    cr = src['citnovelty_v3'] / 'results'
    for f in ('paper_measures.parquet', 'labyear_panel.parquet', 'trends.parquet', 'coverage.parquet', 'did_citation.parquet', 'paper_dose.parquet'):
        add('citation', f'citation/{f}', cr / f, 'copy')
    for f in ('ipw_weights.parquet', 'ipw_meta.json', 'rates.parquet'):
        add('ipw', f'ipw/{f}', src['labstudy'] / 'ipw' / f, 'copy')
    for f in ('LINEAGE-v3.md', 'STYLE-HOMOGENIZATION-v3.md', 'AI-IN-REVISION.md', 'ALL-AI-REWRITE.md', 'V3-SUMMARY.md',
              'AI-DOSE-NOVELTY-DIVERSITY-v3.md', 'CITATION-NOVELTY.md', 'TOPIC-CONVERGENCE.md', 'LAB-EVENT-STUDY.md', 'FULLTEXT-SELECTION-IPW.md'):
        add('carryover', f'carryover/{f}', src['reports'] / f, 'copy')
    add('design', 'design/preregistration.json', src['labstudy_code'] / 'preregistration.json', 'copy')
    if delta_base:    # papers the earlier build never saw, scored and embedded by study_delta_build.py (work/delta-<base>) plus their OpenAlex abstracts/topics
        w = C.STUDY / 'work' / f'delta-{delta_base}'
        add('delta', 'delta/oa_fields_delta.sqlite', C.snapshot_dir(delta_base) / 'delta' / 'oa_fields_delta.sqlite', 'copy')
        for f in ('delta_papers.jsonl.gz', 'delta_scores.parquet', 'copies_held.parquet'):
            add('delta', f'delta/{f}', w / f, 'copy')
        add('delta', 'delta/scores_passages.sqlite', w / 'scores.sqlite', 'copy')
        for m in C.MODELS:
            for p in sorted((w / 'emb' / m).glob('*/abstract.*')):
                add('delta', f'delta/embeddings/{m}/{p.parent.name}/{p.name}', p, 'copy')
    return out


def place(src, dst, mode):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.chmod(0o644)
        dst.unlink()
    size = src.stat().st_size
    if mode == 'ref':
        return 'ref'
    if mode in ('link', 'auto') and (mode == 'link' or size > COPY_MAX):
        try:
            os.link(src, dst)
            return 'link'
        except OSError:
            pass
    shutil.copy2(src, dst)
    return 'copy'


def build(args):
    snap = C.snapshot_dir(args.id)
    items = spec(C.release_dir(args.release), delta_base=args.delta_base)
    snap.mkdir(parents=True, exist_ok=True)
    files, missing = [], []
    for g, d, s, m in items:
        if not s.exists():
            missing.append({'group': g, 'dest': d, 'source': str(s)})
            continue
        st = s.stat()
        how = place(s, snap / d, m) if m != 'ref' else 'ref'
        files.append({'group': g, 'path': d, 'source': str(s.resolve()), 'how': how, 'bytes': st.st_size,
                      'source_mtime': datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
    (snap / 'snapshot.json').write_text(json.dumps({'id': args.id, 'release_dir': str(C.release_dir(args.release).resolve()), 'built': now(),
                                                    'files': files, 'missing': missing}, indent=1))
    print(json.dumps({'files': len(files), 'missing': len(missing), 'bytes': sum(f['bytes'] for f in files if f['how'] != 'ref')}))
    for x in missing:
        print('MISSING', x['source'])


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def rows_of(path):
    """Row count of a table-like file, or None."""
    p = str(path)
    try:
        if p.endswith('.parquet'):
            import pyarrow.parquet as pq
            return pq.ParquetFile(p).metadata.num_rows
        if p.endswith('.jsonl.gz'):
            with gzip.open(p, 'rt') as f:
                return sum(1 for _ in f)
        if p.endswith('.json'):
            d = json.load(open(p))
            return len(d) if isinstance(d, (list, dict)) else None
        if p.endswith('.sqlite'):
            db = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
            tabs = [r[0] for r in db.execute("select name from sqlite_master where type='table'")]
            out = {t: db.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tabs}
            db.close()
            return out
        if p.endswith('.npz'):
            import numpy as np
            with np.load(p) as z:
                return int(len(z['ids'])) if 'ids' in z.files else None
        if p.endswith('.csv') or p.endswith('.md') or p.endswith('.tsv'):
            with open(p, errors='replace') as f:
                return sum(1 for _ in f)
    except Exception as e:  # noqa: BLE001 - a count that cannot be read is recorded, not fatal
        return f'error: {type(e).__name__}'
    return None


def describe(snap, f):
    p = snap / f['path']
    if f['how'] == 'ref':
        src = Path(f['source'])
        return dict(f, sha256=None, rows=None, note='referenced, not copied (too large; derived columns are in the copied tables)',
                    bytes=src.stat().st_size)
    return dict(f, sha256=sha256(p), rows=rows_of(p), bytes=p.stat().st_size)


def seal(args):
    snap = C.snapshot_dir(args.id)
    meta = json.loads((snap / 'snapshot.json').read_text())
    listed = {f['path'] for f in meta['files']}
    for p in sorted((snap / 'delta').glob('*')) if (snap / 'delta').exists() else []:      # fetched after build (study_delta_oa.py): abstracts and topics of papers the earlier build never saw
        if f'delta/{p.name}' not in listed:
            meta['files'].append({'group': 'delta', 'path': f'delta/{p.name}', 'source': 'api.openalex.org via tools/oa_api.py', 'how': 'fetched',
                                  'bytes': p.stat().st_size, 'source_mtime': now()})
    with ThreadPoolExecutor(args.jobs) as ex:
        files = list(ex.map(lambda f: describe(snap, f), meta['files']))
    rel = json.loads((snap / 'release' / 'MANIFEST.json').read_text())
    cov = C.coverage(snap)
    man = {'snapshot': args.id, 'sealed': now(), 'release_id': rel.get('release'), 'release_code_commit': (rel.get('code') or {}).get('commit'),
           'release_dir': meta['release_dir'], 'schools': C.SCHOOLS, 'partial_schools': C.PARTIAL, 'files': files, 'missing': meta['missing'],
           'coverage': cov, 'analysis_code_commit': C.git_commit()}
    (snap / 'MANIFEST.json').write_text(json.dumps(man, indent=1, default=str))
    (snap / 'README.md').write_text(readme(man))
    for f in snap.rglob('*'):
        if f.is_file() and not f.is_symlink() and f.stat().st_nlink == 1:
            f.chmod(0o444)
    (snap / 'SEALED').write_text(man['sealed'] + '\n')
    print(json.dumps({'sealed': args.id, 'files': len(files), 'sha256': sum(1 for f in files if f['sha256'])}))


def verify(args):
    snap = C.snapshot_dir(args.id)
    man = json.loads((snap / 'MANIFEST.json').read_text())
    bad = []
    with ThreadPoolExecutor(args.jobs) as ex:
        for f, h in zip([f for f in man['files'] if f['sha256']], ex.map(lambda f: sha256(snap / f['path']), [f for f in man['files'] if f['sha256']])):
            if h != f['sha256']:
                bad.append(f['path'])
    print(json.dumps({'checked': sum(1 for f in man['files'] if f['sha256']), 'changed': bad}))
    return 1 if bad else 0


def readme(man):
    cov = man['coverage']
    rows = '\n'.join(f"| {s} | {c['lab_papers_2016_2025']} | {c['pis']} | {c['in_universe']:.0%} | {c['abstract_embedded']:.0%} | {c['abstract_flag']:.0%} | {('n/a' if c.get('held') is None else format(c['held'], '.0%'))} | {c['fulltext_v3']:.0%} | {c['period_supported']:.0%} |"
                     for s, c in cov['by_school'].items())
    groups = {}
    for f in man['files']:
        groups.setdefault(f['group'], [0, 0])
        groups[f['group']][0] += 1
        groups[f['group']][1] += f['bytes'] if f['how'] != 'ref' else 0
    grows = '\n'.join(f'| {g} | {n} | {b / 2 ** 20:.1f} |' for g, (n, b) in sorted(groups.items()))
    return f"""# Homogenization study snapshot {man['snapshot']}

Sealed {man['sealed']}. Immutable: every file is read-only and listed with its sha256 in `MANIFEST.json` (`study_snapshot.py verify --id {man['snapshot']}` re-hashes them).
Built from release `{man['release_id']}` (`{man['release_dir']}`, code commit `{(man['release_code_commit'] or '')[:10]}`); snapshot tooling at commit `{(man['analysis_code_commit'] or '')[:10]}`.

## What is in
- **Membership** (release `hierarchy/<school>/`): `lab_papers.jsonl.gz` (a paper is in a lab only when the lab's PI is on the byline: the strict rule), `pis.json`, `students.json`, `student_papers.jsonl.gz`, `report.json`, `copies.json`, and the faculty periods, for the 12 schools: {', '.join(man['schools'])}.
- **Release AI tables** (`release/ai/`): lab AI scores, histograms and the AI-words tables as published with the release.
- **AI scores, detector v3** (`ai/`): `papers_v3.parquet` (one row per universe paper: abstract flag, full-text `ai_share` over main body, over main + appendix, abstained share, `trained_on_v3`, Kobak words), `paper_ai_v3.parquet` (the section split per full-text paper), the operating point and the error table. v3 false-positive rate 0.30% per passage (CI 0.27 to 0.32%); unseen-generator misses 0.9 to 6.6%.
- **Universe and OpenAlex fields** (`universe/`): `universe.sqlite` (paper list with OpenAlex ids, labs), `oa_fields.sqlite` (abstracts, primary topics), `oa_extra.sqlite` (references count, venue type).
- **Delta** (`delta/`, present when built with `--delta-base`): OpenAlex abstracts/topics, detector-v3 scores (`delta_scores.parquet`, passage scores in `scores_passages.sqlite`) and abstract embeddings of papers the earlier build never saw. They have no citation measures and no IPW weights.
- **Embeddings of abstracts** (`embeddings/<model>/<school>/abstract.npz`, hard-linked): seven models (SPECTER2 base and proximity, SciNCL, Qwen3-0.6B, GTE-Qwen2-1.5B, BGE-M3, Nomic v1.5), one vector per paper under its home school, plus BERTopic topic ids (`topics/`).
- **Citation measures** (`citation/`): Uzzi atypicality, Rao-Stirling and related per paper (detector-v3 build), **IPW weights** (`ipw/`), the lab-event-study pre-registration (`design/preregistration.json`), and the earlier reports for the experiments that are carried over unchanged (`carryover/`).

| group | files | MiB (copied or linked) |
|---|---|---|
{grows}

## What is out
- PDFs and extracted full texts: never copied. Per-paragraph section scores (`sections/sections.sqlite`, {next((f['bytes'] for f in man['files'] if f['path'].startswith('sections/')), 0) / 2 ** 30:.1f} GiB), `universe/texts.sqlite` and full-text embeddings are listed in the manifest as `referenced` (size only); the analysis does not read them (the main-body and main+appendix shares are columns of `ai/papers_v3.parquet`).
- 2026 papers are in the tables but no figure or estimate uses them (window 2016 to 2025). ChatGPT launched 2022-11-30; post = 2023 onward.
- Anything built after the sealing time. The AI scores and embeddings were built on 2026-11-04 to 11-06 from the earlier paper universe (9 schools); the release is 2026-11-07. A release paper that is not in that universe has no AI score and no embedding (see coverage).

## Coverage of the 12 schools (papers 2016 to 2025, release membership)
Partial-coverage schools: **{', '.join(man['partial_schools'])}**. They were onboarded after the earlier AI scores and embeddings were built; where `delta/` is present, the papers the earlier build never saw (these schools' and about 3% of the others') were scored with detector v3 and embedded afterwards (`delta/delta_scores.parquet`, `delta/embeddings/`), and the shares below include them. Most of their PIs carry appointment evidence from 2026 listings only, so their period gaps are open (papers are attributed to the PI at every year, `period_supported` is the share with a dated appointment period).

| school | lab papers | PIs | in universe | abstract embedded | abstract flag | full text held | full-text scored (v3) | period-supported |
|---|---|---|---|---|---|---|---|---|
{rows}

"in universe", "abstract embedded", "abstract flag" and "full-text scored" are shares of the school's release papers (matched by OpenAlex id) that the earlier build covered.
Missing files: {len(man['missing'])}.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['plan', 'build', 'seal', 'verify'])
    ap.add_argument('--release', default='latest')
    ap.add_argument('--id', default='2026-11-07')
    ap.add_argument('-j', '--jobs', type=int, default=8)
    ap.add_argument('--delta-base', default=None, help='build: also take the scored/embedded delta of this earlier snapshot (work/delta-<base>)')
    a = ap.parse_args()
    if a.cmd == 'plan':
        tot = 0
        for g, d, s, m in spec(C.release_dir(a.release), delta_base=a.delta_base):
            sz = s.stat().st_size if s.exists() else -1
            tot += max(sz, 0) if m != 'ref' else 0
            print(f'{g:20s} {m:5s} {sz / 2 ** 20:9.1f} MiB {d}' + ('' if sz >= 0 else '  MISSING'))
        print('total MiB (copied+linked)', round(tot / 2 ** 20))
    elif a.cmd == 'build':
        build(a)
    elif a.cmd == 'seal':
        seal(a)
    else:
        sys.exit(verify(a))


if __name__ == '__main__':
    t = time.time()
    main()
