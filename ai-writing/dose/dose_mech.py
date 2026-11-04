"""The mechanical-shift confound: how far does AI wording alone move a text's embedding?  (embedding step, one GPU; `measure` is in dose_analysis.py)

  dose_mech.py embed --model M [--n-psg 1500]
Embeds, with the model exactly as the universe was embedded (embeddings/embed.py Embedder: same formats, pooling, windows, fp16):
  abstracts  each of the 3,000 source abstracts of ai-writing/sources.jsonl (human wording) and every rewrite of it in ai-writing/generated-*.jsonl
             (polish, outline-then-expand; Qwen2.5-3B/7B/72B, Llama-3.3-70B): title [SEP] / blank line + text
  passages   n-psg source passages per generator of detector_v2/data (human) and their rewrites (polish, paraphrase, notes), as one text window
-> AI_SCORES/mech/<model>.npz   abs_h, abs_ai (float16, raw pooled vectors), abs_meta (json), psg_h, psg_ai, psg_meta
The content of a rewrite is the source's (polish, paraphrase) or close to it (outline/notes), so any embedding difference is wording, not research.
"""
import argparse
import hashlib
import json

import numpy as np

import dcommon as D

GEN_ABS = ['qwen3b', 'qwen7b', 'qwen72b', 'llama70b']
GEN_PSG = ['qwen7b', 'qwen72b', 'llama70b']


def pick(sid, n_keep_den=1, salt='mech'):
    return int(hashlib.sha1(f'{salt}|{sid}'.encode()).hexdigest()[:8], 16)


def load_pairs(n_psg):
    aiw = D.MAIN_AIW
    src = {s['key']: s for s in map(json.loads, open(aiw / 'sources.jsonl'))}
    abs_pairs = []
    for g in GEN_ABS:
        for r in map(json.loads, open(aiw / f'generated-{g}.jsonl')):
            s = src.get(r['key'])
            if s and len(r['text'].split()) >= 40:
                abs_pairs.append(dict(key=r['key'], gen=g, task=r['task'], school=s['school'], year=s['year'], title=s['title'], human=s['abstract'], ai=r['text']))
    psrc = {s['sid']: s for s in map(json.loads, open(aiw / 'detector_v2' / 'data' / 'sources.jsonl'))}
    psg_pairs = []
    for g in GEN_PSG:
        rows = [r for r in map(json.loads, open(aiw / 'detector_v2' / 'data' / f'generated-{g}.jsonl')) if r['sid'] in psrc and len(r['text'].split()) >= 40]
        rows = sorted(rows, key=lambda r: pick(r['sid']))[:n_psg]
        for r in rows:
            s = psrc[r['sid']]
            psg_pairs.append(dict(sid=r['sid'], key=s['key'], gen=g, task=r['task'], school=s['school'], year=s['year'], human=s['text'], ai=r['text']))
    return abs_pairs, psg_pairs


def embed(model, n_psg):
    import embed as E
    emb = E.Embedder(model)
    abs_pairs, psg_pairs = load_pairs(n_psg)
    # human abstracts once per key
    keys = sorted({p['key'] for p in abs_pairs})
    first = {p['key']: p for p in abs_pairs}
    h_seq = [emb.encode_abstract(D.norm1(first[k]['title']), D.norm1(first[k]['human'])) for k in keys]
    Hv, _ = emb.embed(h_seq)
    hidx = {k: i for i, k in enumerate(keys)}
    A_seq = [emb.encode_abstract(D.norm1(p['title']), D.norm1(p['ai'])) for p in abs_pairs]
    Av, _ = emb.embed(A_seq)
    D.log(model=model, abstracts_h=len(keys), abstracts_ai=len(abs_pairs))
    # passages: one window per text (a passage is far below every chunk size); mean over windows would be the same
    def seqs(texts):
        return [emb.encode_body(t)[0][0] for t in texts]
    sids = sorted({p['sid'] for p in psg_pairs})
    psh = {p['sid']: p['human'] for p in psg_pairs}
    PH, _ = emb.embed(seqs([psh[s] for s in sids]))
    pidx = {s: i for i, s in enumerate(sids)}
    PA, _ = emb.embed(seqs([p['ai'] for p in psg_pairs]))
    D.log(model=model, passages_h=len(sids), passages_ai=len(psg_pairs))
    out = D.SCORES / 'mech'
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / f'.tmp-{model}.npz'
    np.savez_compressed(tmp, abs_h=Hv.astype(np.float16), abs_ai=Av.astype(np.float16), psg_h=PH.astype(np.float16), psg_ai=PA.astype(np.float16),
                        abs_meta=json.dumps([dict(key=p['key'], gen=p['gen'], task=p['task'], school=p['school'], year=p['year'], h=hidx[p['key']]) for p in abs_pairs]),
                        psg_meta=json.dumps([dict(sid=p['sid'], key=p['key'], gen=p['gen'], task=p['task'], school=p['school'], year=p['year'], h=pidx[p['sid']]) for p in psg_pairs]),
                        revision=emb.revision)
    tmp.replace(out / f'{model}.npz')
    D.log(model=model, wrote=str(out / f'{model}.npz'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['embed'])
    ap.add_argument('--model', required=True)
    ap.add_argument('--n-psg', type=int, default=1500)
    a = ap.parse_args()
    embed(a.model, a.n_psg)
