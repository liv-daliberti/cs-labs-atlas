"""AI-detector scores of the rewrites and of the original abstracts: the v1 ABSTRACT detector (ai-writing/detector.py, ModernBERT-large on `title | abstract`).

  detect.py score --style polish|paraphrase
reads   EMB/allai/rewrites_<style>.sqlite (ok rows), EMB/texts.sqlite (originals), universe years; model and threshold of ai-writing/detector/all in the MAIN checkout
writes  EMB/allai/detect_v1_<style>.parquet   paper_id, kind (rewrite | original), year, p (P(AI), bf16-autocast softmax as detector.py predict), flagged (p >= the
        detector's 1%-false-positive threshold on validation human abstracts)
Both sides are scored: every ok rewrite (title | rewrite) and the original abstract (title | abstract) of the same papers (the polish run scores all 112,260
originals; paraphrase only its subsample). The v2 PARAGRAPH detector (detector_v2) must not be used on abstracts: it flags 11-16% of pre-2022 abstracts
(AI-dose finding), which is why an earlier version of this script that used it was replaced.
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
sys.path.insert(0, str(HERE.parent))
import ecommon as C  # noqa: E402

ALLAI = C.EMB / 'allai'
V1 = C.P.CODE / 'ai-writing' / 'detector' / 'all'


def main(style):
    import detector as D1   # ai-writing/detector.py (v1)
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    thr = json.load(open(V1 / 'metrics.json'))['threshold']
    tok = AutoTokenizer.from_pretrained(V1 / 'model')
    model = AutoModelForSequenceClassification.from_pretrained(V1 / 'model').cuda().eval()
    rw = sqlite3.connect(f'file:{ALLAI / f"rewrites_{style}.sqlite"}?mode=ro', uri=True)
    rows = rw.execute('select paper_id, text from rw where ok = 1').fetchall()
    all_ids = [r[0] for r in rw.execute('select paper_id from rw')]
    tx = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    src = {p: (t or '', a) for p, t, a in tx.execute('select paper_id, title, abstract from abstracts')}
    tx.close()
    uni = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True)
    year = dict(uni.execute('select paper_id, year from papers'))
    uni.close()
    out = []
    p = D1.predict(model, tok, [D1.text(src[r[0]][0], r[1]) for r in rows], bs=64)
    out += [dict(paper_id=r[0], kind='rewrite', year=year.get(r[0]), p=float(x), flagged=int(x >= thr)) for r, x in zip(rows, p)]
    p = D1.predict(model, tok, [D1.text(*src[i]) for i in all_ids], bs=64)
    out += [dict(paper_id=i, kind='original', year=year.get(i), p=float(x), flagged=int(x >= thr)) for i, x in zip(all_ids, p)]
    df = pd.DataFrame(out)
    df.to_parquet(ALLAI / f'detect_v1_{style}.parquet', index=False)
    C.log(style=style, threshold=thr, **{f'{k}_flagged': float(g['flagged'].mean()) for k, g in df.groupby('kind')}, n=len(df))
    o = df[df['kind'] == 'original']
    C.log(original_pre2023=float(o[o.year < 2023]['flagged'].mean()), original_post2023=float(o[o.year >= 2023]['flagged'].mean()), median_p_rewrite=float(np.median(df[df.kind == 'rewrite']['p'])))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['score']); ap.add_argument('--style', default='polish')
    main(ap.parse_args().style)
