"""Design 3, GPU step: detector-v3 scores of the MAIN and APPENDIX passages of the arXiv versions in the revision pairs.

  study_design_revision_gpu.py --id 2026-11-08 --shard I --nshards N

input   <results>/designs/work/revision_split/chunk-*.sqlite from study_design_revision_fetch.py (main and appendix text per version; chunk files are dealt to shards by index)
method  the v3 scoring of the study's own papers: passages cut as common.passages (cap 100 per section), the v3 abstain rule (< 100 words or mid-sentence capitals above the calibration cut), the
        model and flag threshold of the snapshot's operating point. Main and appendix come from ONE extraction, so main body and main body + appendix are nested and comparable; the 11-05
        main-body scores (a different extraction, 60 pages, no appendix) are only used as a check.
output  <results>/designs/work/revision_app/<tag>-<chunk>.parquet per chunk: arxiv_id, role, ok, appendix_found, n_main, n_main_scored, n_main_flagged, n_app, n_app_scored, n_app_flagged.
        A chunk whose file exists is skipped, so a job that hits its time limit is resubmitted unchanged.
"""
import argparse
import importlib.util
import json
import sqlite3
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

import study_common as C

AIW = Path(C.P.AI_WRITING)
for d in ('', 'revision', 'dose', 'embeddings', 'diversity', 'detector_v2'):
    sys.path.append(str(AIW / d))
PASSAGE_CAP = 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--tag', default='app')
    a = ap.parse_args()
    import v2common as V
    work = C.results_dir(a.id) / 'designs' / 'work'
    out = work / 'revision_app'
    out.mkdir(exist_ok=True)
    op = json.loads((Path(C.snapshot_dir(a.id)) / 'ai' / 'detector_v3' / 'operating_point.json').read_text())
    model_dir = AIW / 'detector_v3' / 'models' / 'all' / 'model'
    chunks = sorted((work / 'revision_split').glob('chunk-*.sqlite'))
    mine = [f for i, f in enumerate(chunks) if i % a.nshards == a.shard]
    print(json.dumps(dict(step='todo', shard=a.shard, chunks=len(mine), of=len(chunks))), flush=True)
    model = tok = D2 = None

    def keep(t):
        return not (len(t.split()) < op['abstain_words'] or V.quality(t)['midcap'] > op['midcap_cut'])
    for f in mine:
        dst = out / f'{a.tag}-{f.stem}.parquet'
        if dst.exists():
            continue
        t0 = time.time()
        db = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        recs, ptexts, owners = [], [], []
        for aid, role, v, ok, mb, ab, flags in db.execute('select arxiv_id, role, v, ok, main, appendix, flags from split'):
            mt = zlib.decompress(mb).decode('utf-8', 'ignore') if mb else ''
            at = zlib.decompress(ab).decode('utf-8', 'ignore') if ab else ''
            rec = dict(arxiv_id=aid, role=role, ok=int(ok), appendix_found=bool(at.strip()), n_main=0, n_main_scored=0, n_main_flagged=0, n_app=0, n_app_scored=0, n_app_flagged=0)
            recs.append(rec)
            if not ok:
                continue
            for sec, text in (('main', mt), ('app', at)):
                for t in (V.passages(text, cap=PASSAGE_CAP) if text else []):
                    rec[f'n_{sec}'] += 1
                    if keep(t):
                        ptexts.append(V.norm(t))
                        owners.append((len(recs) - 1, sec))
        db.close()
        if ptexts:
            if model is None:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                sp = importlib.util.spec_from_file_location('detector_v2_predict', str(AIW / 'detector_v2' / 'detector.py'))
                D2 = importlib.util.module_from_spec(sp)
                sp.loader.exec_module(D2)
                tok = AutoTokenizer.from_pretrained(model_dir)
                model = AutoModelForSequenceClassification.from_pretrained(model_dir).cuda().eval()
            pp = D2.predict(model, tok, ptexts, bs=128)
            z = np.log(np.clip(pp, 1e-300, None)) - np.log(np.clip(1 - pp, 1e-300, None))
            for (o, sec), zz in zip(owners, z):
                recs[o][f'n_{sec}_scored'] += 1
                recs[o][f'n_{sec}_flagged'] += int(zz >= op['thr_z'])
        tmp = dst.with_name('.tmp-' + dst.name)
        pd.DataFrame(recs).to_parquet(tmp, index=False)
        tmp.replace(dst)
        print(json.dumps(dict(step='chunk', part=dst.name, texts=len(recs), passages=len(ptexts), minutes=round((time.time() - t0) / 60, 2))), flush=True)


if __name__ == '__main__':
    main()
