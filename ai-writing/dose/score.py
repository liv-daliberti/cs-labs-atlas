"""Score every paper of the universe with the AI-writing detectors (GPU, one card, resumable by text hash).

  score.py abstract --shard I --nshards N     v1 detector on `title | abstract` (p_v1) and the v2 paragraph model on the abstract alone (p_v2)
  score.py fulltext --shard I --nshards N     v2 passage model on every passage of the full text (usable bodies only)
inputs   EMB/texts.sqlite (abstracts, fulltext); papers whose text_hash is already in PARTS are skipped, so a re-run scores only the delta
outputs  AI_SCORES/parts/<kind>/<tag>-<i>.parquet        abstract: paper_id, text_hash, p_v1, p_v2
         AI_SCORES/parts/fulltext/<tag>-<i>.papers.parquet   paper_id, text_hash, kind, body_words, n_passages
         AI_SCORES/parts/fulltext/<tag>-<i>.passages.parquet paper_id, pidx, words, p   (every passage, so thresholds can be re-cut)
Precision: DOSE_AMP=bf16 (default; the precision both detectors were trained and calibrated in) or fp16 (RTX 2080 Ti has no bf16; validate against bf16
on a sample with check_precision.py before using). The v2 scores are the fp32 logit difference through a sigmoid; v1 is bf16 autocast softmax, as
ai-writing/detector.py predict.
"""
import argparse
import os
import sqlite3
import time
import zlib

import numpy as np
import pandas as pd

import dcommon as D

AMP = {'bf16': 'bfloat16', 'fp16': 'float16'}[os.environ.get('DOSE_AMP', 'bf16')]
MAXLEN = 512


def load_models(which):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    out = {}
    for name, path in which:
        out[name] = (AutoTokenizer.from_pretrained(path), AutoModelForSequenceClassification.from_pretrained(path).cuda().eval())
    return out, getattr(torch, AMP)


def batches(order, texts, tok, max_tokens=60000, max_bs=128):
    """Indices in length order, cut so a batch holds <= max_tokens padded tokens (the short passages go through in big batches)."""
    i = 0
    while i < len(order):
        L = len(texts[order[i]])
        bs = max(8, min(max_bs, max_tokens // max(1, min(MAXLEN, L // 4 + 8))))
        yield order[i:i + bs]
        i += bs


def predict_v1(tok, model, dtype, texts, bs=64):
    """P(AI) of the v1 detector: softmax of bf16-autocast logits (ai-writing/detector.py predict, same batch size)."""
    import torch
    out = np.zeros(len(texts))
    order = np.argsort([len(t) for t in texts], kind='stable')
    with torch.inference_mode():
        for i in range(0, len(order), bs):
            ix = order[i:i + bs]
            enc = tok([texts[j] for j in ix], padding=True, truncation=True, max_length=MAXLEN, return_tensors='pt').to('cuda')
            with torch.autocast('cuda', dtype=dtype):
                out[ix] = torch.softmax(model(**enc).logits.float(), -1)[:, 1].cpu().numpy()
    return out


def predict_v2(tok, model, dtype, texts):
    """P(AI) of the v2 passage model (ai-writing/detector_v2/detector.py: encoder under autocast, pooling/head/classifier in fp32, logit difference in float64)."""
    import torch
    z = np.zeros(len(texts))
    order = np.argsort([len(t) for t in texts], kind='stable')
    pool_cls = model.config.classifier_pooling == 'cls'
    with torch.inference_mode():
        for ix in batches(order, texts, tok):
            enc = tok([texts[j] for j in ix], padding=True, truncation=True, max_length=MAXLEN, return_tensors='pt').to('cuda')
            with torch.autocast('cuda', dtype=dtype):
                h = model.model(input_ids=enc['input_ids'], attention_mask=enc['attention_mask'])[0]
            h, m = h.float(), enc['attention_mask'].float()
            pooled = h[:, 0] if pool_cls else (h * m.unsqueeze(-1)).sum(1) / m.sum(1, keepdim=True)
            lg = model.classifier(model.drop(model.head(pooled))).double()
            z[ix] = (lg[:, 1] - lg[:, 0]).cpu().numpy()
    return 1.0 / (1.0 + np.exp(-z))


def done_hashes(kind):
    d = D.PARTS / kind
    seen = set()
    for f in d.glob('*.parquet'):
        if kind == 'fulltext' and not f.name.endswith('.papers.parquet'):
            continue
        seen |= set(pd.read_parquet(f, columns=['text_hash'])['text_hash'])
    return seen


def write_atomic(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.tmp-' + path.name)
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def run_abstract(shard, nshards, tag, hi):
    seen = done_hashes('abstract')
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    rows = [r for r in db.execute('select paper_id, title, abstract, text_hash from abstracts where rowid % ? = ? and rowid <= ?', (nshards, shard, hi))
            if r[3] not in seen and r[2] and len(r[2].split()) >= 50 and r[1]]
    db.close()
    D.log(kind='abstract', shard=shard, todo=len(rows), already=len(seen), amp=AMP)
    if not rows:
        return
    m, dtype = load_models([('v1', D.V1_MODEL / 'model'), ('v2', D.V2_MODEL)])
    t0 = time.time()
    p1 = predict_v1(*m['v1'], dtype, [D.text1(r[1], r[2]) for r in rows])
    import v2common as V
    p2 = predict_v2(*m['v2'], dtype, [V.norm(r[2]) for r in rows])
    df = pd.DataFrame(dict(paper_id=[r[0] for r in rows], text_hash=[r[3] for r in rows], p_v1=p1, p_v2=p2))
    write_atomic(df, D.PARTS / 'abstract' / f'{tag}-{shard}.parquet')
    D.log(kind='abstract', shard=shard, done=len(rows), minutes=round((time.time() - t0) / 60, 1))


def run_fulltext(shard, nshards, tag, hi):
    import v2common as V
    seen = done_hashes('fulltext')
    db = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    ids, kinds, hashes, bwords, pid, pidx, words, texts = [], [], [], [], [], [], [], []
    t0 = time.time()
    for paper, kind, body, flags, h in db.execute('select paper_id, kind, body, flags, text_hash from fulltext where usable = 1 and rowid % ? = ? and rowid <= ?',
                                                  (nshards, shard, hi)):
        if h in seen or not body:
            continue
        body = zlib.decompress(body).decode('utf-8', 'ignore')
        ps = V.passages(body)
        ids.append(paper); kinds.append(kind); hashes.append(h); bwords.append(len(body.split()))
        for i, t in enumerate(ps):
            pid.append(paper); pidx.append(i); words.append(len(t.split())); texts.append(V.norm(t))
    db.close()
    D.log(kind='fulltext', shard=shard, papers=len(ids), passages=len(texts), already=len(seen), amp=AMP, minutes=round((time.time() - t0) / 60, 1))
    if not texts:
        return
    m, dtype = load_models([('v2', D.V2_MODEL)])
    p = predict_v2(*m['v2'], dtype, texts)
    n = pd.Series(pid).value_counts()
    papers = pd.DataFrame(dict(paper_id=ids, text_hash=hashes, kind=kinds, body_words=bwords))
    papers['n_passages'] = papers['paper_id'].map(n).fillna(0).astype(int)
    passages = pd.DataFrame(dict(paper_id=pid, pidx=np.array(pidx, np.int32), words=np.array(words, np.int32), p=p))
    write_atomic(passages, D.PARTS / 'fulltext' / f'{tag}-{shard}.passages.parquet')
    write_atomic(papers, D.PARTS / 'fulltext' / f'{tag}-{shard}.papers.parquet')   # last: its hashes mark the shard done
    D.log(kind='fulltext', shard=shard, done=len(texts), minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['abstract', 'fulltext'])
    ap.add_argument('--shard', type=int, required=True)
    ap.add_argument('--nshards', type=int, required=True)
    ap.add_argument('--tag', default=time.strftime('%Y%m%d'))
    ap.add_argument('--hi', type=int, default=10 ** 9, help='highest rowid of texts.sqlite to include (fix it at submit time so shards agree)')
    a = ap.parse_args()
    (run_abstract if a.kind == 'abstract' else run_fulltext)(a.shard, a.nshards, a.tag, a.hi)
