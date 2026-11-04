"""AI-detector scores of the rewrites (detector_v2's final ModernBERT model, ai-writing/detector_v2/detector.py `predict`) and of the original abstracts.

  detect.py score --style polish|paraphrase [--originals N]
reads   EMB/allai/rewrites_<style>.sqlite (ok rows), EMB/texts.sqlite (originals); the model detector_v2/models/all/model in the MAIN checkout (git-ignored data)
writes  EMB/allai/detect_<style>.parquet   paper_id, kind (rewrite | original), p (P(AI)), flagged (p > the detector's 1%-false-positive threshold)
Each abstract is scored as one passage (detector_v2's V.norm: LaTeX, tags, 'Abstract:' prefix, citation markers removed; truncated at 512 tokens). The
detector was trained on ~150-word BODY passages of 2016-2021 papers; an abstract is a different register, so the ORIGINAL abstracts (a sample of N
per year, 2016-2021 = before ChatGPT, and 2023-2026) are scored too: their flagged share is the baseline the rewrites' share is read against.
Run on a GPU through detect.slurm.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
sys.path.insert(0, str(HERE.parent / 'detector_v2'))
import ecommon as C  # noqa: E402

ALLAI = C.EMB / 'allai'
MODEL_DIR = C.P.CODE / 'ai-writing' / 'detector_v2' / 'models' / 'all' / 'model'
METRICS = C.P.CODE / 'ai-writing' / 'detector_v2' / 'results' / 'all' / 'metrics.json'


def main(style, n_orig):
    import torch  # noqa: F401
    import detector as D
    import v2common as V
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    thr = json.load(open(METRICS))['threshold']
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).cuda().eval()
    rw = sqlite3.connect(f'file:{ALLAI / f"rewrites_{style}.sqlite"}?mode=ro', uri=True)
    rows = rw.execute('select paper_id, text from rw where ok = 1').fetchall()
    tx = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    src = {p: a for p, a in tx.execute('select paper_id, abstract from abstracts')}
    tx.close()
    uni = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True)
    year = dict(uni.execute('select paper_id, year from papers'))
    uni.close()
    out = []
    ids = [r[0] for r in rows]
    p = D.predict(model, tok, [V.norm(r[1]) for r in rows], bs=128)
    out += [dict(paper_id=i, kind='rewrite', year=year.get(i), p=float(x), flagged=int(x > thr)) for i, x in zip(ids, p)]
    rng = np.random.default_rng(C.SEED)
    sel = []
    for y in range(2016, 2027):
        pool = sorted(i for i in src if year.get(i) == y)
        sel += list(rng.choice(pool, min(n_orig, len(pool)), replace=False)) if pool else []
    p = D.predict(model, tok, [V.norm(src[i]) for i in sel], bs=128)
    out += [dict(paper_id=i, kind='original', year=year.get(i), p=float(x), flagged=int(x > thr)) for i, x in zip(sel, p)]
    df = pd.DataFrame(out)
    df.to_parquet(ALLAI / f'detect_{style}.parquet', index=False)
    C.log(style=style, threshold=thr, **{f'{k}_flagged': float(g['flagged'].mean()) for k, g in df.groupby('kind')}, n=len(df))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['score']); ap.add_argument('--style', default='polish'); ap.add_argument('--originals', type=int, default=1000)
    a = ap.parse_args()
    main(a.style, a.originals)
