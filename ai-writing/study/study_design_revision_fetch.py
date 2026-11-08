"""Design 3, CPU step: main body and appendix of the arXiv versions in the revision pairs, from arXiv's public cloud mirror (storage.googleapis.com, never arxiv.org).

  study_design_revision_fetch.py --id 2026-11-08 --task I --of N

The 11-05 run stored only the body the stores' extractor keeps (Introduction to the last References heading), so its texts carry no appendix. This step downloads each version's PDF again
(one at a time into a temporary directory, deleted at once: nothing is mirrored), extracts it with the splitter the study's own papers went through (fulltext_sections.split_file: pdftotext
up to 400 pages, main / references / appendix) and keeps main and appendix as compressed text in chunk files, so that main body and main body + appendix are scored by the same extraction.
input   <results>/designs/work/revision_texts.parquet (arxiv_id, role); the version number is 1 for v1 and the plan's last version for the final (revision.sqlite `plan`)
output  <results>/designs/work/revision_split/chunk-<task>-<k>.sqlite: split(arxiv_id, role, v, ok, main zlib, appendix zlib, flags json, pdf_bytes). A finished chunk is skipped on a re-run.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

import study_common as C

AIW = Path(C.P.AI_WRITING)
for d in ('', 'revision', 'dose', 'diversity'):
    sys.path.append(str(AIW / d))
CHUNK = 150
THREADS = 6


def work(snap_id):
    d = C.results_dir(snap_id) / 'designs' / 'work' / 'revision_split'
    d.mkdir(parents=True, exist_ok=True)
    return d


def one(args):
    import fulltext_sections as S
    import rv_fetch as RF
    session, aid, role, v = args
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'x.pdf'
        n = RF.get_pdf(session, aid, v, p)
        if not n:
            return aid, role, v, None
        r = S.split_file(p, 'pdf')
        if r.get('error'):
            return aid, role, v, dict(ok=0, main=b'', appendix=b'', flags=json.dumps(dict(error=r['error'])), pdf_bytes=n)
        return aid, role, v, dict(ok=1, main=zlib.compress((r['main'] or '').encode()), appendix=zlib.compress((r['appendix'] or '').encode()),
                                  flags=json.dumps({k: v_ for k, v_ in (r.get('flags') or {}).items() if isinstance(v_, (int, float, str, bool, type(None)))}), pdf_bytes=n)


def run(snap_id, task, of):
    import requests
    import rv_common as RC
    s = requests.Session()
    s.headers['User-Agent'] = RC.UA
    want = pd.read_parquet(C.results_dir(snap_id) / 'designs' / 'work' / 'revision_texts.parquet')
    db = sqlite3.connect(f'file:{AIW / "data" / "revision" / "revision.sqlite"}?mode=ro', uri=True)
    fv = dict(db.execute('select arxiv_id, max(final_v) from plan group by arxiv_id'))
    db.close()
    want = want[want['arxiv_id'].map(lambda a: int(hashlib.md5(a.encode()).hexdigest(), 16) % of) == task].sort_values(['arxiv_id', 'role'])
    jobs = [(s, a, r, 1 if r == 'v1' else int(fv[a])) for a, r in zip(want['arxiv_id'], want['role']) if r == 'v1' or fv.get(a)]
    out = work(snap_id)
    t0 = time.time()
    for c in range(0, len(jobs), CHUNK):
        dst = out / f'chunk-{task:03d}-{c // CHUNK:03d}.sqlite'
        if dst.exists():
            continue
        tmp = Path(tempfile.gettempdir()) / f'sd-split-{os.getpid()}-{task}-{c}.sqlite'
        tmp.unlink(missing_ok=True)
        cdb = sqlite3.connect(tmp)
        cdb.execute('create table split (arxiv_id text, role text, v int, ok int, main blob, appendix blob, flags text, pdf_bytes int, primary key (arxiv_id, role))')
        with ThreadPoolExecutor(THREADS) as ex:
            res = list(ex.map(one, jobs[c:c + CHUNK]))
        k = 0
        for aid, role, v, r in res:
            if r is None:
                continue
            cdb.execute('insert or replace into split values (?,?,?,?,?,?,?,?)', (aid, role, v, r['ok'], r['main'], r['appendix'], r['flags'], r['pdf_bytes']))
            k += 1
        cdb.commit()
        cdb.close()
        dst.write_bytes(tmp.read_bytes())      # /tmp -> the results volume (a copy, not a rename across filesystems)
        tmp.unlink()
        print(json.dumps(dict(task=task, chunk=c // CHUNK, texts=k, of=len(jobs), seconds=int(time.time() - t0))), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('--task', type=int, default=None)
    ap.add_argument('--of', type=int, default=24)
    a = ap.parse_args()
    run(a.id, a.task if a.task is not None else int(os.environ['SLURM_ARRAY_TASK_ID']), a.of)
